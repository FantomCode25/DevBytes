from database import *
import joblib
import requests
import json
from collections import defaultdict
from util import detect_spam, callback
GITHUB_API_URL = "https://api.github.com/graphql"


def fetch_issues_comments(owner, repo, headers, after_cursor=None, lastpage=''):

    query = """
    query($owner: String!, $repo: String!, $first: Int, $after: String, $lastpage: String) {
      repository(owner: $owner, name: $repo) {
        issues(first: 1, after: $lastpage) {
          edges {
            node {
              id
              title
              body
              comments(first: $first, after: $after) {
                edges {
                  node {
                    author{ login }
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
      deleteIssueComment(input: {
        id: $id, clientMutationId: "comment-delete"
      }) {
        clientMutationId
      }
    }
  """
  variables = {
      "id": comment_id,
      'clientMutationId': "comment Deleted"
  }
  response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
  if response.status_code == 200:
      return True
  else:
      print(f"Failed to delete Issue comment with ID {comment_id}. Status code: {response.status_code}")
      return False

def delete_issue(issue_id, headers):
  mutation = """
  mutation($issueId: ID!) {
    deleteIssue(input: {
      issueId: $issueId,
      clientMutationId: "deleted Issue"
    }) {
      clientMutationId
    }
  }
  """

  variables = {
      "issueId": issue_id,
  }
  response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
  if response.status_code == 200:
      return True
  else:
      print(f"Failed to delete Issue with ID {issue_id}. Status code: {response.status_code}")
      print("Error:", response.json())
      return False


def moderate_issues_comments(repo_id, from_begining=False,  delete_comments=False, delete_issues=False, callback:callable = callback):
    repo_id, owner_id, repo, last_processed_cursor = get_repo_for_issues(repo_id)
    owner_id, owner, token, _ = get_user(owner_id)
    spam_comments = defaultdict(int)
    spam_comments_count = 0
    spam_issues_count = 0
    total_comments = 0
    message = "Starting......"
    last_processed_cursor = '' if from_begining else last_processed_cursor      
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    callback(total_comments, spam_comments_count, spam_issues_count, message=message,  done=False)
    
    latest_cursor = last_processed_cursor
    lastpage = ''
    try:
      while True:
        latest_cursor = last_processed_cursor
        comments_remaining = True
        while comments_remaining:
            data = fetch_issues_comments(owner, repo, headers, latest_cursor, lastpage)
            # print(json.dumps(data, indent=2))
            for issue in data['data']['repository']['issues']['edges']:
                if delete_issues and issue['node']['body'] and detect_spam(issue['node']['body']):
                    delete_issue(issue['node']['id'], headers)
                    message = f"Deleted Issues\nbody:{issue['node']['body']}"
                    spam_issues_count += 1
                    callback(total_comments, spam_comments_count, spam_issues_count, message=message,  done=False)
                    continue
                
                for comment_edge in issue['node']['comments']['edges']:
                    comment_body = comment_edge['node']['body']
                    is_minimized = comment_edge['node']['isMinimized']
                    total_comments += 1
                    if not is_minimized or delete_comments:
                        comment_id = comment_edge['node']['id']
                        if detect_spam(comment_body):
                          spam_comments_count += 1
                          if delete_comments and comment_body:
                            delete_comment(comment_id, headers)
                            message = f"Comment Deleted\nbody:{comment_body}"
                          else:
                            minimize_comment(comment_id, headers)
                            add_comment(repo_id, comment_body, comment_id, True)
                            message = f"Comment Hidden\nbody:{comment_body}"
                          spam_comments[comment_edge['node']['author']['login']] += 1
                        else:
                          add_comment(repo_id, comment_body, comment_edge['node']['id'], False)
                    callback(total_comments, spam_comments_count, spam_issues_count, message=message,  done=False)

                    latest_cursor = comment_edge['cursor']

                page_info = issue['node']['comments']['pageInfo']
                if not page_info['hasNextPage']:
                    comments_remaining = False

            if not data['data']['repository']['issues']['edges']:
                break

        if not data['data']['repository']['issues']['pageInfo']['hasNextPage']:
          break
        lastpage = data['data']['repository']['issues']['pageInfo']["endCursor"]
      message = "Moderation Completed without any Errors"
    except Exception as e:
      message = f"Error\n{str(e)}"
      print("Error processing: " + str(e))
      
    print("Moderation Results:")
    print("comments moderated:", sum(spam_comments.values()),  "\tissues moderated:", spam_issues_count)
    callback(total_comments, spam_comments_count, spam_issues_count, message=message, done=True)

    if from_begining:
        reset_counts(repo_id)
    update_issues_counts(repo_id, spam_comments, spam_issues_count,  total_comments)
    update_issue_cursor(repo_id, latest_cursor)

if __name__ == "__main__":
  print("Issues")
  moderate_issues_comments(1, from_begining=True, delete_comments=True, delete_issues=True)