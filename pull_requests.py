from database import *
import joblib
import requests
import json
from collections import defaultdict
from util import detect_spam, callback
GITHUB_API_URL = "https://api.github.com/graphql"


def fetch_pr_comments(owner, repo, headers, after_cursor=None, lastpage=''):
    query = """
    query($owner: String!, $repo: String!, $first: Int, $after: String, $lastpage: String) {
      repository(owner: $owner, name: $repo) {
        pullRequests(first: 1, after: $lastpage) {
          edges {
            node {
              id
              title
              body
              state
              comments(first: $first, after: $after) {
                edges {
                  node {
                    author{
                      login
                    }
                    id
                    body
                    isMinimized
                  }
                  cursor
                }
                pageInfo {
                  endCursor
                  hasNextPage
                }
              }
            }
          }
          pageInfo{
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    variables = {
        "owner": owner,
        "repo": repo,
        "first": 10,
        "after": after_cursor,
        "lastpage": lastpage,
    }

    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": query, "variables": variables})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed with code {response.status_code}. Response: {response.json()}")

def minimize_comment(comment_id, headers):
    mutation = """
    mutation($commentId: ID!) {
      minimizeComment(input: {subjectId: $commentId, classifier: SPAM}) {
        minimizedComment {
          isMinimized
          minimizedReason
        }
      }
    }
    """
    variables = {
        "commentId": comment_id
    }
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
    if response.status_code == 200:
        data = response.json()
        return data["data"]["minimizeComment"]["minimizedComment"]["isMinimized"]
    else:
        print(f"Failed to minimize comment with ID {comment_id}. Status code: {response.status_code}")
        return False
    
def delete_comment(comment_id, headers):
  mutation = """
    mutation($id: ID!) {
      deletePullRequestReviewComment(input: {
        id: $id, clientMutationId: "pullRequestComment delete"
      }) {
        clientMutationId
      }
    }
  """
  variables = {
      "id": comment_id,
  }
  response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
  if response.status_code == 200:
      data = response.json()
      print(json.dumps(data, indent=2))
      return data
  else:
      print(f"Failed to delete Pull Request comment with ID {comment_id}. Status code: {response.status_code}")
      return False

def close_pull_request(pr_id, headers):
  mutation = """
    mutation($id: ID!) {
      closePullRequest(input: {
        pullRequestId: $id
      }) {
        pullRequest {
          id
          state
        }
      }
    }
  """
  variables = {
      "id": pr_id,
  }
  response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
  if response.status_code == 200:
      return True
  else:
      print(f"Failed to delete Pull Request with ID {pr_id}. Status code: {response.status_code}")
      print("Error:", response.json())
      return False


def moderate_pull_request_comments(repo_id, from_begining=False, delete_comments=False, delete_pr=False, callback: callable=callback):
    repo_id, owner_id, repo, last_processed_cursor = get_repo_for_pullrequests(repo_id)
    owner_id, owner, token, _ = get_user(owner_id)
    spam_comments = defaultdict(int)
    spam_comments_count = 0
    spam_pr_count = 0
    total_comments = 0
    message = "Starting......"
    last_processed_cursor = '' if from_begining else last_processed_cursor        
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    latest_cursor = last_processed_cursor
    lastpage = ''
    callback(total_comments, spam_comments_count, spam_pr_count, message=message,  done=False)
    try:
      while True:
        latest_cursor = last_processed_cursor
        comments_remaining = True
        while comments_remaining:
            data = fetch_pr_comments(owner, repo, headers, latest_cursor, lastpage)
            # print(json.dumps(data, indent=2))

            for pr in data['data']['repository']['pullRequests']['edges']:
                if pr['node']['state'] in ['CLOSED', 'MERGED']:
                  lastpage = data['data']['repository']['pullRequests']['pageInfo']["endCursor"]
                  continue
                   
                pr_body = pr['node']['body']
                if delete_pr and  pr_body and detect_spam(pr_body):
                  close_pull_request(pr['node']['id'], headers)
                  spam_pr_count += 1
                  message = f"Pull Request closed\ndescription: {pr_body}"
                  callback(total_comments, spam_comments_count, spam_pr_count, message=message,  done=False)
                  
                  lastpage = data['data']['repository']['pullRequests']['pageInfo']["endCursor"]
                  continue
                    
                
                for comment_edge in pr['node']['comments']['edges']:
                    comment_body = comment_edge['node']['body']
                    is_minimized = comment_edge['node']['isMinimized']
                    total_comments += 1
                    if not is_minimized or delete_comments:
                        if detect_spam(comment_body):
                            comment_id = comment_edge['node']['id']
                            if delete_comments and comment_body:
                              delete_comment(comment_id, headers)
                              message = f"Comment deleted:\nbody: {comment_body}"
                            else:
                              minimize_comment(comment_id, headers)
                              message = f"Comment hidden:\nbody: {comment_body}"
                            spam_comments[comment_edge['node']['author']['login']] += 1
                    callback(total_comments, spam_comments_count, spam_pr_count, message=message,  done=False)

                    latest_cursor = comment_edge['cursor']

                page_info = pr['node']['comments']['pageInfo']
                if not page_info['hasNextPage']:
                    comments_remaining = False
            
            if not data['data']['repository']['pullRequests']['edges']:
                break
        if not data['data']['repository']['pullRequests']['pageInfo']['hasNextPage']:
          break
        lastpage = data['data']['repository']['pullRequests']['pageInfo']["endCursor"]
      message = "Moderation Completed without any Errors"
    except Exception as e:
      message = f"Error\n{str(e)}"
      print("Error processing: " + str(e))
      
    print("Moderation Results:")
    print("comments moderated:", sum(spam_comments.values()), "\tpull requests moderated:", spam_pr_count)
    callback(total_comments, spam_comments_count, spam_pr_count, message=message,  done=True)
    if from_begining:
        reset_counts(repo_id)
    update_pr_counts(repo_id, spam_comments, spam_pr_count, total_comments)
    update_pullrequest_cursor(repo_id, latest_cursor)

if __name__ == "__main__":
  moderate_pull_request_comments(8, from_begining=True, delete_comments=True, delete_pr=True)