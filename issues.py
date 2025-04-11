import requests
from collections import defaultdict
from keys import *

GITHUB_API_URL = "https://api.github.com/graphql"

def callback(total_comments, spam_comments_count, spam_issues_count, message, done=True):
    print()
    print(f"Total Com: {total_comments} Spam: {spam_comments_count} Spam Issues: {spam_issues_count}\n Message: {message}")

def fetch_issues_comments(owner, repo, headers, issue_cursor=None, comment_cursor=None):
    query = """
    query($owner: String!, $repo: String!, $issueCursor: String, $commentCursor: String) {
      repository(owner: $owner, name: $repo) {
        issues(first: 1, after: $issueCursor) {
          edges {
            node {
              id
              title
              body
              comments(first: 10, after: $commentCursor) {
                edges {
                  node {
                    id
                    body
                    isMinimized
                    author {
                      login
                    }
                  }
                  cursor
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
          pageInfo {
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
        "issueCursor": issue_cursor,
        "commentCursor": comment_cursor
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
    variables = {"commentId": comment_id}
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
    if response.status_code == 200:
        return response.json()["data"]["minimizeComment"]["minimizedComment"]["isMinimized"]
    else:
        print(f"Failed to minimize comment ID {comment_id}. Status: {response.status_code}")
        return False

def delete_comment(comment_id, headers):
    mutation = """
    mutation($id: ID!) {
      deleteIssueComment(input: {id: $id}) {
        clientMutationId
      }
    }
    """
    variables = {"id": comment_id}
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to delete issue comment ID {comment_id}. Status: {response.status_code}")
        return False

def delete_issue(issue_id, headers):
    mutation = """
    mutation($id: ID!) {
      deleteIssue(input: {id: $id}) {
        clientMutationId
      }
    }
    """
    variables = {"id": issue_id}
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": mutation, "variables": variables})
    if response.status_code == 200:
        return True
    else:
        print(f"Failed to delete issue ID {issue_id}. Status: {response.status_code}")
        print("Response:", response.json())
        return False

def moderate_issue_comments(owner, repo, from_beginning=False, delete_comments=False, delete_issues=False, callback=callback):
    headers = {
        'Authorization': f'Bearer {GITHUB_KEY}',
        'Content-Type': 'application/json'
    }

    spam_comments = defaultdict(int)
    spam_comments_count = 0
    spam_issues_count = 0
    total_comments = 0
    message = "Starting..."
    issue_cursor = ''
    
    callback(total_comments, spam_comments_count, spam_issues_count, message=message, done=False)

    try:
        while True:
            comment_cursor = None
            data = fetch_issues_comments(owner, repo, headers, issue_cursor, comment_cursor)

            issues = data['data']['repository']['issues']['edges']
            if not issues:
                break

            for issue_edge in issues:
                issue = issue_edge['node']
                issue_id = issue['id']
                issue_body = issue['body']
                issue_author = issue.get('author', {}).get('login', 'unknown')

                comments_page = issue['comments']
                while True:
                    for comment_edge in comments_page['edges']:
                        comment = comment_edge['node']
                        comment_id = comment['id']
                        comment_body = comment['body']
                        is_minimized = comment['isMinimized']
                        author = comment['author']['login']

                        total_comments += 1
                        if not is_minimized or delete_comments:
                            spam_comments_count += 1
                            if delete_comments:
                                delete_comment(comment_id, headers)
                                message = f"Deleted Comment by {author}: {comment_body[:50]}"
                            else:
                                minimize_comment(comment_id, headers)
                                message = f"Minimized Comment by {author}: {comment_body[:50]}"
                            spam_comments[author] += 1

                        callback(total_comments, spam_comments_count, spam_issues_count, message=message, done=False)
                        comment_cursor = comment_edge['cursor']

                    if comments_page['pageInfo']['hasNextPage']:
                        comments_page = fetch_issues_comments(owner, repo, headers, issue_cursor, comment_cursor)['data']['repository']['issues']['edges'][0]['node']['comments']
                    else:
                        break

                if delete_issues:
                    delete_issue(issue_id, headers)
                    spam_issues_count += 1
                    message = f"Issue deleted: {issue_body[:60]}"
                    callback(total_comments, spam_comments_count, spam_issues_count, message=message, done=False)

                issue_cursor = data['data']['repository']['issues']['pageInfo']['endCursor']

            if not data['data']['repository']['issues']['pageInfo']['hasNextPage']:
                break

        message = "Moderation Completed."
    except Exception as e:
        message = f"Error occurred: {str(e)}"
        print(message)

    print("Moderation Results:")
    print("Comments Moderated:", spam_comments_count)
    print("Issues Deleted:", spam_issues_count)
    callback(total_comments, spam_comments_count, spam_issues_count, message=message, done=True)

if __name__ == "__main__":
    moderate_issue_comments("Rahul-Samedavar", "Nexus2.0", from_beginning=True, delete_issues=False, delete_comments=False)
