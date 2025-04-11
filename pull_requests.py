import requests
import csv
from collections import defaultdict
from keys import GITHUB_KEY

GITHUB_API_URL = "https://api.github.com/graphql"

def fetch_pr_comments(owner, repo, headers, pr_cursor=None):
    query = """
    query($owner: String!, $repo: String!, $prCursor: String) {
      repository(owner: $owner, name: $repo) {
        pullRequests(first: 1, after: $prCursor) {
          edges {
            node {
              id
              title
              comments(first: 100) {
                edges {
                  node {
                    id
                    body
                    isMinimized
                    author {
                      login
                    }
                  }
                }
              }
            }
            cursor
          }
        }
      }
    }
    """
    variables = {
        "owner": owner,
        "repo": repo,
        "prCursor": pr_cursor
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
        return True
    else:
        print(f"Failed to delete comment ID {comment_id}. Status: {response.status_code}")
        return False

def moderate_pr_comments(owner, repo, delete_comments=False):
    headers = {
        'Authorization': f'Bearer {GITHUB_KEY}',
        'Content-Type': 'application/json'
    }

    pr_cursor = None
    total_comments = 0
    spam_comments_count = 0
    spam_authors = defaultdict(int)

    with open(f"{repo}_pr_comments.csv", mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['text', 'label'])

        while True:
            data = fetch_pr_comments(owner, repo, headers, pr_cursor)
            pr_edges = data['data']['repository']['pullRequests']['edges']

            if not pr_edges:
                break

            for pr_edge in pr_edges:
                pr_node = pr_edge['node']
                comments = pr_node['comments']['edges']

                for comment_edge in comments:
                    comment = comment_edge['node']
                    comment_id = comment['id']
                    body = comment['body']
                    is_minimized = comment['isMinimized']
                    author = comment['author']['login'] if comment['author'] else 'unknown'

                    label = 1 if is_minimized else 0
                    writer.writerow([body.replace('\n', ' ').strip(), label])
                    total_comments += 1

                    if not is_minimized:
                        spam_comments_count += 1
                        spam_authors[author] += 1
                        if delete_comments:
                            delete_comment(comment_id, headers)
                        else:
                            minimize_comment(comment_id, headers)

                pr_cursor = pr_edge['cursor']

    print(f"Total Comments Processed: {total_comments}")
    print(f"Spam Comments Moderated: {spam_comments_count}")
    print(f"Spam Authors: {dict(spam_authors)}")

if __name__ == "__main__":
    moderate_pr_comments("Rahul-Samedavar", "Nexus2.0", delete_comments=False)
