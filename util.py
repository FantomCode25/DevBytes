import requests
import json
from database import *
GITHUB_API_URL = "https://api.github.com/graphql"
import joblib
import requests
from tkinter import messagebox

GITHUB_API_URL = "https://api.github.com/graphql"

def username_exists(username):
    response = requests.get(f"https://api.github.com/users/{username}")

    if response.status_code == 404:
        return False
    elif response.status_code == 200:
        return True
    else:
        raise Exception(f"Failed to check username: {response.status_code} {response.text}")

def fetch_user_repositories(username, token):
    if not username_exists(username):
        raise ValueError(f"User '{username}' does not exist.")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    query = """
    query($username: String!) {
      user(login: $username) {
        repositories(first: 100) {
          nodes {
            name
          }
        }
      }
    }
    """
    variables = {"username": username}
    
    response = requests.post(GITHUB_API_URL, headers=headers, json={"query": query, "variables": variables})
    
    if response.status_code == 401:
        raise PermissionError("Invalid or missing GitHub token.")
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code} {response.text}")
    
    data = response.json()
    
    if "errors" in data:
        error_message = data["errors"][0].get("message", "Unknown error.")
        raise Exception(f"GitHub API error: {error_message}")
    
    return data["data"]["user"]["repositories"]["nodes"]

def new_user_register(username, token):
    try:
        repos = fetch_user_repositories(username, token)

    except PermissionError as e:
        print(f"Permission error: {e}")
        return -1
    
    except ValueError as e:
        print(f"Value error: {e}")
        return 0
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return -2
    
    else:
        
        repos = [x['name'] for x in repos]
        user_id =  add_user(username, token, '{}')
        repo_dict = {name: add_repository(user_id, name) for name in repos}
        update_repos(user_id, json.dumps(repo_dict))
        return user_id

#exception not handled here. raises PermissionError if token is expired. prompt to change token.........
def load_repos_sub(id, username, token, initial_repos):
    repos = [x['name'] for x in fetch_user_repositories(username, token)]
    modified = False
    keys = list(initial_repos.keys())
    for repo in keys:
        if repo not in repos:
            delete_repository(initial_repos[repo])
            print("delete repository", repo)
            initial_repos.pop(repo)
            modified = True
    for repo in repos:
        if repo not in initial_repos.keys():
            repo_id = add_repository(id, repo)
            print("add repository", repo)
            initial_repos[repo] = repo_id
            modified = True
    if modified:
        update_repos(id, json.dumps(initial_repos))
    return initial_repos


def load_repos(id):
    _ , username, token, initial_repos = get_user(id)
    initial_repos = json.loads(initial_repos)
    return load_repos_sub(id, username, token, initial_repos)

def block_user(username, token):
    url = f"https://api.github.com/user/blocks/{username}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.put(url, headers=headers)
    if response.status_code == 204:
        print(f"User {username} has been blocked successfully.")
        messagebox.showinfo("Success", f"Blocked {username}.")
    else:
        messagebox.showinfo("Failure", f"Couldn't Blocked {username}.")
        print(f"block failed. {response.text}")

def is_user_blocked(username, token):
    url = f"https://api.github.com/user/blocks/{username}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 204:
        return True
    elif response.status_code == 404:
        return False
    else:
        print(f"Error checking block status: {response.json()}")
        return None

def unblock_user(username, token):
    url = f"https://api.github.com/user/blocks/{username}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.delete(url, headers=headers)

    if response.status_code == 204:
        messagebox.showinfo("Failure", f"Unblocked {username}.")
    else:
        messagebox.showinfo("Failure", f"Couldn't Blocked {username}.")

def toggle_block(username, token):
    if is_user_blocked(username, token):
        unblock_user(username, token)
    else:
        block_user(username, token)

def check_minimized_mismatches(comment_list, token):
    headers = {"Authorization": f"Bearer {token}"}
    mismatches = []

    # GitHub allows batching up to 100 at once
    batch_size = 50
    for i in range(0, len(comment_list), batch_size):
        batch = comment_list[i:i+batch_size]

        # Build the dynamic query
        query_parts = []
        for idx, item in enumerate(batch):
            cid = item[1]
            query_parts.append(f'''
                comment{idx}: node(id: "{cid}") {{
                    ... on DiscussionComment {{
                        id
                        isMinimized
                    }}
                }}
            ''')

        full_query = f"query {{\n{''.join(query_parts)}\n}}"

        response = requests.post(GITHUB_API_URL, json={"query": full_query}, headers=headers)
        data = response.json()["data"]
        for idx, item in enumerate(batch):
            node = data.get(f"comment{idx}")
            if node is None:
                continue 
            github_minimized = node["isMinimized"]
            local_spam = bool(item[4])
            if github_minimized != local_spam:
                mismatches.append({
                    "text": item[3],
                    "isMinimized": github_minimized,
                })
    return mismatches


def shorten(str, n=18):
    if len(str) <= n or n == 0:
        return str
    return str[:n] + "\n" + shorten(str[n:], n)

def callback(total_comments, spam_comments_count, spam_discussions_count, message, done=True):
    print()
    print(f"Total: {total_comments} Spam: {spam_comments_count}")
    print(f"Msg: {message}")
    if done: print("===============done===============")

model = joblib.load(r"Models\spam_detector.pkl")
def detect_spam(comment_body):
    return model.predict([comment_body])[0] == 1

if __name__ == "__main__":
    print("Util")
    # print(load_repos(1))