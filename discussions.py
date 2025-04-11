from database import *
import joblib
import requests
import json
from collections import defaultdict
from util import detect_spam, callback

GITHUB_API_URL = "https://api.github.com/graphql"


def fetch_discussions_comments(owner, repo, headers, after_cursor=None, lastpage=''):

    query = """
    query($owner: String!, $repo: String!, $first: Int, $after: String, $lastpage: String) {
      repository(owner: $owner, name: $repo) {
        discussions(first: 1, after: $lastpage) {
          edges {
            node {
              id
              title
              body
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
    mutation($id: ID!, $clientMutationId: String) {
      deleteDiscussionComment(input: {
        id: $id, clientMutationId: $clientMutationId
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
      data = response.json()
      return data
  else:
      print(f"Failed to delete discussion comment with ID {comment_id}. Status code: {response.status_code}")
      return False

def delete_discussion(discussion_id, headers):
  mutation = """
    mutation($id: ID!, $clientMutationId: String) {
      deleteDiscussion(input: {
        id: $id, clientMutationId: $clientMutationId
      }) {
        clientMutationId
      }
    }
  """
  variables = {
      "id": discussion_id,
      'clientMutationId': "Discussion Deleted"
  }
  response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
  if response.status_code == 200:
      return True
  else:
      print(f"Failed to delete Discussion with ID {discussion_id}. Status code: {response.status_code}")
      print("Error:", response.json())
      return False


def moderate_discussion_comments(repo_id, from_begining=False, delete_comments=False, delete_discussions=False, callback:callable = callback):
    repo_id, owner_id, repo, last_processed_cursor = get_repo_for_discussion(repo_id)
    owner_id, owner, token, _ = get_user(owner_id)
    spam_comments = defaultdict(int)
    spam_comments_count = 0
    spam_discussions_count = 0
    total_comments = 0
    message="Starting........"
    last_processed_cursor = '' if from_begining else last_processed_cursor        
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    latest_cursor = last_processed_cursor
    lastpage = ''
    callback(total_comments, spam_comments_count, spam_discussions_count, message=message,  done=False)
    try:
      while True:
        latest_cursor = last_processed_cursor
        comments_remaining = True
        while comments_remaining:
            data = fetch_discussions_comments(owner, repo, headers, latest_cursor, lastpage)
            # print(json.dumps(data, indent=2))

            for discussion in data['data']['repository']['discussions']['edges']:
                
                discussion_body = discussion['node']['body']
                if delete_discussions and  discussion_body and detect_spam(discussion_body):
                    delete_discussion(discussion['node']['id'], headers)
                    message = f"discussion deleted.\nbody:{discussion_body}\n"
                    spam_discussions_count += 1
                    callback(total_comments, spam_comments_count, spam_discussions_count, message=message, done=False)
                    continue

                for comment_edge in discussion['node']['comments']['edges']:
                    comment_body = comment_edge['node']['body']
                    is_minimized = comment_edge['node']['isMinimized']
                    total_comments += 1
                    if not is_minimized or delete_comments:
                        if detect_spam(comment_body):
                            spam_comments_count += 1
                            comment_id = comment_edge['node']['id']
                            if delete_comments and comment_body:
                              delete_comment(comment_id, headers)
                              message = f"Comment deleted\nbody:{comment_body}"
                            else:
                              minimize_comment(comment_id, headers)
                              add_comment(repo_id, comment_body, comment_id, True)
                              message = f"Comment Hidden\nbody:{comment_body}"
                            spam_comments[comment_edge['node']['author']['login']] += 1
                        else:
                          add_comment(repo_id, comment_body, comment_edge['node']['id'], False)
                        
                    callback(total_comments, spam_comments_count, spam_discussions_count, message=message, done=False)                            

                    latest_cursor = comment_edge['cursor']

                page_info = discussion['node']['comments']['pageInfo']
                if not page_info['hasNextPage']:
                    comments_remaining = False
            
            if not data['data']['repository']['discussions']['edges']:
                break

        if not data['data']['repository']['discussions']['pageInfo']['hasNextPage']:
          break
        lastpage = data['data']['repository']['discussions']['pageInfo']["endCursor"]
    
      message = "Moderation Completed without any Errors"
    except Exception as e:
      message = f"Error\n{str(e)}"
      print("Error processing: " + str(e))
      
    print("Moderation Results:")
    print("comments moderated:", sum(spam_comments.values()), "\tdiscussions moderated:", spam_discussions_count)
    callback(total_comments, spam_comments_count, spam_discussions_count, message=message, done=True)
    if from_begining:
        reset_counts(repo_id)
    update_discussion_counts(repo_id, spam_comments, spam_discussions_count, total_comments)
    update_discussion_cursor(repo_id, latest_cursor)

if __name__ == "__main__":
    moderate_discussion_comments(26, from_begining=True, delete_discussions=True, delete_comments=False)