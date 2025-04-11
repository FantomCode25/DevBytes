import requests
import csv
from keys import *

GITHUB_API_URL = "https://api.github.com/graphql"

def run_query(query, variables, headers):
    response = requests.post(GITHUB_API_URL, json={"query": query, "variables": variables}, headers=headers)
    return response.json()

def fetch_discussion_comments(owner, repo, token, max_comments, collected):
    query = '''
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        discussions(first: 50, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            number
            comments(first: 100) {
              nodes {
                bodyText
                isMinimized
              }
            }
          }
        }
      }
    }
    '''

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    cursor = None
    results = []

    while collected < max_comments:
        variables = {"owner": owner, "repo": repo, "cursor": cursor}
        data = run_query(query, variables, headers)
        discussions = data['data']['repository']['discussions']['nodes']

        for d in discussions:
            for c in d['comments']['nodes']:
                if c['bodyText'].strip():
                    results.append({
                        "text": c['bodyText'].strip(),
                        "label": 1 if c['isMinimized'] else 0
                    })
                    collected += 1
                    if collected >= max_comments:
                        return results, collected

        page_info = data['data']['repository']['discussions']['pageInfo']
        if not page_info['hasNextPage']:
            break
        cursor = page_info['endCursor']

    return results, collected

def fetch_issue_and_pr_comments(owner, repo, token, max_comments, collected):
    query = '''
    query($owner: String!, $repo: String!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        issues(first: 50, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            number
            comments(first: 100) {
              nodes {
                bodyText
              }
            }
          }
        }
      }
    }
    '''

    pr_query = query.replace("issues", "pullRequests")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    results = []

    # Helper for both Issues and PRs
    def scrape(query):
        nonlocal collected
        cursor = None
        while collected < max_comments:
            variables = {"owner": owner, "repo": repo, "cursor": cursor}
            data = run_query(query, variables, headers)
            nodes = data['data']['repository']['issues']['nodes'] if 'issues' in query else data['data']['repository']['pullRequests']['nodes']

            for node in nodes:
                for c in node['comments']['nodes']:
                    if c['bodyText'].strip():
                        results.append({
                            "text": c['bodyText'].strip(),
                            "label": 0  # No isMinimized in issues/PRs
                        })
                        collected += 1
                        if collected >= max_comments:
                            return

            page_info = data['data']['repository']['issues']['pageInfo'] if 'issues' in query else data['data']['repository']['pullRequests']['pageInfo']
            if not page_info['hasNextPage']:
                break
            cursor = page_info['endCursor']

    scrape(query)       # Issues
    scrape(pr_query)    # PRs

    return results, collected

def fetch_all_comments(owner, repo, token, max_comments=10000):
    all_comments = []
    collected = 0

    # Discussions
    disc_comments, collected = fetch_discussion_comments(owner, repo, token, max_comments, collected)
    all_comments.extend(disc_comments)

    if collected < max_comments:
        issue_pr_comments, collected = fetch_issue_and_pr_comments(owner, repo, token, max_comments, collected)
        all_comments.extend(issue_pr_comments)

    # Save to CSV
    filename = f"{owner}-{repo}.csv"
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(all_comments)

    print(f"✅ Saved {len(all_comments)} comments to {filename}")

fetch_all_comments("opencv", "opencv", GITHUB_KEY)