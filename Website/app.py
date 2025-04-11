from flask import Flask, request, redirect, session, render_template, jsonify
import requests
import base64
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Change this to a secure secret key

with open('config.json') as config_file:
    config = json.load(config_file)

# GitHub OAuth settings
GITHUB_CLIENT_ID = config['GITHUB_CLIENT_ID']
GITHUB_CLIENT_SECRET = config['GITHUB_CLIENT_SECRET']
GITHUB_REDIRECT_URI = 'http://localhost:5000/callback'

# Your workflow YAML content
WORKFLOW_CONTENT = '''
name: Spam Detection
on:
  schedule:
    - cron: '0 * * * *'
  workflow_dispatch: # Allows you to manually trigger the workflow as needed. 

jobs:
  detect-spam:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
      discussions: write
      contents: read
    steps:
      - uses: actions/checkout@v3
      - name: Cache cursor
        uses: actions/cache@v3
        with:
          path: .github/cursor_cache
          key: ${{ runner.os }}-cursor-${{ github.run_id }}
          restore-keys: |
            ${{ runner.os }}-cursor-
      - name: Spam Detection
        uses: Sambhaji-Patil/Auto-Hide-Spam-Comments@v1.2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'''

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    """Redirect users to GitHub for authentication with correct scopes"""
    scopes = [
        'repo',            # Full control of private repositories
        'workflow',        # Update GitHub Action workflows
        'admin:repo_hook'  # Full control of repository hooks
    ]
    github_auth_url = (
        f'https://github.com/login/oauth/authorize'
        f'?client_id={GITHUB_CLIENT_ID}'
        f'&scope={"%20".join(scopes)}'  # Space-separated scopes
        f'&redirect_uri={GITHUB_REDIRECT_URI}'
    )
    return redirect(github_auth_url)

@app.route('/delete-workflow', methods=['POST'])
def delete_workflow():
    repo_full_name = request.json.get('repository')
    workflow_path = '.github/workflows/spam-detection.yml'

    headers = {
        'Authorization': f'token {session.get("access_token")}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Step 1: Get the file's SHA
    file_info_response = requests.get(
        f'https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}',
        headers=headers
    )

    if file_info_response.status_code != 200:
        return jsonify({'error': 'Failed to fetch workflow file info', 'details': file_info_response.json()}), file_info_response.status_code

    file_info = file_info_response.json()
    sha = file_info.get('sha')
    if not sha:
        return jsonify({'error': 'File SHA not found'}), 400

    # Step 2: Delete the file
    delete_data = {
        'message': 'Delete Spam Detection workflow',
        'sha': sha
    }

    delete_response = requests.delete(
        f'https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}',
        headers=headers,
        json=delete_data
    )

    if delete_response.status_code == 200:
        return jsonify({'success': True, 'message': 'Workflow deleted successfully'})
    return jsonify({'error': delete_response.json()}), delete_response.status_code

@app.route('/check-feature-status', methods=['GET'])
def check_feature_status():
    repo_full_name = request.args.get('repository')
    workflow_path = '.github/workflows/spam-detection.yml'

    headers = {
        'Authorization': f'token {session.get("access_token")}',
        'Accept': 'application/vnd.github.v3+json'
    }

    response = requests.get(
        f'https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}',
        headers=headers
    )
    
    return jsonify({'enabled': response.status_code == 200})

@app.route('/callback')
def callback():
    """Handle GitHub OAuth callback"""
    code = request.args.get('code')
    
    response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': GITHUB_CLIENT_ID,
            'client_secret': GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': GITHUB_REDIRECT_URI
        },
        headers={'Accept': 'application/json'}
    )
    
    access_token = response.json().get('access_token')
    if not access_token:
        return "Failed to get access token", 400
        
    # Verify token and scopes
    verify_response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'token {access_token}'}
    )
    
    if verify_response.status_code != 200:
        return "Failed to verify token", 400
        
    session['access_token'] = access_token
    return redirect('/repositories')

@app.route('/repositories')
def list_repositories():
    """List user's repositories"""
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/login')
    
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Fetch user data (name and profile image)
    user_response = requests.get(
        'https://api.github.com/user',
        headers=headers
    )
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        user_name = (user_data['name'] or user_data['login']).split()[0]
        user_avatar_url = user_data['avatar_url']
    else:
        return f"Error fetching user data: {user_response.text}", 500

    # Fetch repositories
    repos_response = requests.get(
        'https://api.github.com/user/repos',
        headers=headers
    )
    
    if repos_response.status_code == 200:
        repos = repos_response.json()
        return render_template('repositories.html', repos=repos, user_name=user_name, user_avatar_url=user_avatar_url)
    else:
        return f"Error fetching repositories: {repos_response.text}", 500

def create_file(repo_full_name, path, content, headers, commit_message):
    """Create a file in the repository"""
    url = f'https://api.github.com/repos/{repo_full_name}/contents/{path}'
    
    data = {
        'message': commit_message,
        'content': base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    
    response = requests.put(url, headers=headers, json=data)
    return response.status_code in [201, 200]

@app.route('/add-workflow', methods=['POST'])
def add_workflow():
    repo_full_name = request.json.get('repository')
    cron_expression = request.json.get('cron', '0 * * * *')  # Default: hourly
    workflow_content = WORKFLOW_CONTENT.replace(
        '- cron: \'0 * * * *\'', f'- cron: \'{cron_expression}\''
    )
    """Add workflow file to specified repository"""
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'Not authenticated'}), 401
    
    repo_full_name = request.json.get('repository')
    if not repo_full_name:
        return jsonify({'error': 'Repository not specified'}), 400
    
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Create the workflow file directly
    workflow_path = '.github/workflows/spam-detection.yml'
    
    # Check if workflow file already exists
    get_response = requests.get(
        f'https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}',
        headers=headers
    )
    
    try:
        if get_response.status_code == 200:
            # File exists, update it
            current_file = get_response.json()
            update_data = {
                'message': 'Update Spam Detection workflow',
                'content': base64.b64encode(workflow_content.encode('utf-8')).decode('utf-8'),
                'sha': current_file['sha']
            }
            
            response = requests.put(
                f'https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}',
                headers=headers,
                json=update_data
            )
        else:
            # File doesn't exist, create it
            create_data = {
                'message': 'Add Spam Detection workflow',
                'content': base64.b64encode(workflow_content.encode('utf-8')).decode('utf-8')
            }
            
            response = requests.put(
                f'https://api.github.com/repos/{repo_full_name}/contents/{workflow_path}',
                headers=headers,
                json=create_data
            )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Workflow added successfully'})
        else:
            error_message = response.json().get('message', 'Unknown error occurred')
            return jsonify({'error': error_message}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
