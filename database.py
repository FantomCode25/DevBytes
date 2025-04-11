import sqlite3
import json

DATABASE_NAME = "data.db"



initial_count = json.dumps({
    'total_comments': 0,
    'total_spam_comments': 0,
    'spam_discussions': 0,
    'total_discussion_comments': 0,
    'spam_discussion_comments': {},
    'spam_issues': 0,
    'total_issue_comments': 0,
    'spam_issues_comments': {},
    'spam_pull_requests': 0,
    'total_pull_request_comments': 0,
    'spam_pull_requests_comments': {}
})

def create_table():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(39) NOT NULL,
                token VARCHAR(40) NOT NULL,
                repos INTEGER NOT NULL
            )
        """
    )
    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner INTEGER,
                name VARCHAR(100) NOT NULL,
                last_discussion_cursor VARCHAR(64) NOT NULL,
                last_issue_cursor VARCHAR(64) NOT NULL,
                last_pullrequest_cursor VARCHAR(64) NOT NULL,
                counts TEXT NOT NULL,
                FOREIGN KEY(owner)  REFERENCES users(id)
            );
        """
    )
    cursor.execute(
        """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id VARCHAR(100) NOT NULL Unique,
                repo INTEGER,
                content Text,
                isSpam int,
                FOREIGN KEY(repo)  REFERENCES repositories(id)
            );
        """
    )
    
    conn.commit()
    conn.close()

def add_user(username, token, repos):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, token, repos) VALUES (?, ?, ?)", (username, token, repos))
    id = cursor.lastrowid
    conn.commit()
    conn.close()
    return id


def get_userid(username):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    userid = cursor.fetchone()
    conn.close()
    return -1 if userid is None else userid[0]

def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users")
    user = cursor.fetchall()
    conn.close()
    return user

def update_username(user_id, new_username):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute( "UPDATE users SET username = ? WHERE id = ?", (new_username, user_id) )
    conn.commit()
    conn.close()

def update_token(user_id, new_token):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute( "UPDATE users SET token = ? WHERE id = ?", (new_token, user_id) )
    conn.commit()
    conn.close()

def update_repos(user_id, repos):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute( "UPDATE users SET repos = ? WHERE id = ?", (repos, user_id) )
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()    
    cursor.execute("DELETE FROM repositories WHERE owner = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_repository(owner_id, repo_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO repositories (
            owner, name, last_discussion_cursor, 
            last_issue_cursor, last_pullrequest_cursor, 
            counts
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ( owner_id, repo_name, "", "", "", initial_count)
    )
    id = cursor.lastrowid
    conn.commit()
    conn.close()
    return id
    
def delete_repository(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
    conn.commit()
    conn.close()

def get_repository(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    conn.close()
    return repo

def get_repo_for_discussion(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, owner, name, last_discussion_cursor FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    conn.close()
    return repo

def get_repo_for_issues(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, owner, name, last_issue_cursor FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    conn.close()
    return repo

def get_repo_for_pullrequests(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, owner, name, last_pullrequest_cursor FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    conn.close()
    return repo

def get_user_repositories(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM repositories WHERE owner = ?", (user_id,))
    repos = cursor.fetchall()
    conn.close()
    return repos

def update_discussion_cursor(repo_id, new_cursor):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE repositories SET last_discussion_cursor = ? WHERE id = ?",
        (new_cursor, repo_id)
    )
    conn.commit()
    conn.close()

def update_issue_cursor(repo_id, new_cursor):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE repositories SET last_issue_cursor = ? WHERE id = ?",
        (new_cursor, repo_id)
    )
    conn.commit()
    conn.close()

def update_pullrequest_cursor(repo_id, new_cursor):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE repositories SET last_pullrequest_cursor = ? WHERE id = ?",
        (new_cursor, repo_id)
    )
    conn.commit()
    conn.close()

def update_discussion_counts(repo_id, spam_comments: dict, spam_discussions, total_comments):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("Select counts from repositories where id =?", (repo_id,))
    counts = json.loads(cursor.fetchall()[-1][0])
    counts['spam_discussions'] += spam_discussions
    keys = counts['spam_discussion_comments'].keys()
    total_new = 0
    for k,y in spam_comments.items():
        total_new += y
        if k in keys:
            counts['spam_discussion_comments'][k] += y
        else:
            counts['spam_discussion_comments'][k] = y
    counts['total_spam_comments'] += total_new
    counts['spam_discussions']  += spam_discussions
    counts['total_comments'] += total_comments
    counts['total_discussion_comments'] += total_comments
    cursor.execute(
    "UPDATE repositories SET counts = ? WHERE id = ?",
    (json.dumps(counts), repo_id)
    )
    conn.commit()
    conn.close()

def update_issues_counts(repo_id, spam_comments: dict, spam_issues, total_comments):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("Select counts from repositories where id =?", (repo_id,))
    counts = json.loads(cursor.fetchall()[-1][0])
    counts['spam_issues'] += spam_issues
    keys = counts['spam_issues_comments'].keys()
    total_new = 0
    for k,y in spam_comments.items():
        total_new += y
        if k in keys:
            counts['spam_issues_comments'][k] += y
        else:
            counts['spam_issues_comments'][k] = y

    counts['total_spam_comments'] += total_new
    counts['spam_issues']  += spam_issues
    counts['total_issue_comments'] += total_comments
    counts['total_comments'] += total_comments

    cursor.execute(
    "UPDATE repositories SET counts = ? WHERE id = ?",
    (json.dumps(counts), repo_id)
    )
    conn.commit()
    conn.close()

def update_pr_counts(repo_id, spam_comments: dict, spam_pr, total_comments):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("Select counts from repositories where id =?", (repo_id,))
    counts = json.loads(cursor.fetchall()[-1][0])
    keys = counts['spam_pull_requests_comments'].keys()
    total_new = 0
    for k,y in spam_comments.items():
        total_new += y
        if k in keys:
            counts['spam_pull_requests_comments'][k] += y
        else:
            counts['spam_pull_requests_comments'][k] = y

    counts['total_spam_comments'] += total_new
    counts['spam_pull_requests']  += spam_pr
    counts['total_pull_request_comments'] += total_comments
    counts['total_comments'] += total_comments
    cursor.execute(
    "UPDATE repositories SET counts = ? WHERE id = ?",
    (json.dumps(counts), repo_id)
    )
    conn.commit()
    conn.close()

def get_counts(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("Select counts from repositories where id =?", (repo_id,))
    counts = json.loads(cursor.fetchall()[-1][0])
    conn.commit()
    conn.close()
    return counts
    

def reset_counts(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE repositories SET counts = ? WHERE id = ?",
        (initial_count, repo_id)
    )
    conn.commit()
    conn.close()

def add_comment(repo_id, content, comment_id, is_spam):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO comments (repo, content, comment_id, isSpam)
            VALUES (?, ?, ?, ?)
            """,
            (repo_id, content, comment_id, int(is_spam))
        )
    except Exception as e:
        print(e)


    conn.commit()
    conn.close()

def get_comments(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM comments WHERE repo = ?", (repo_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_comments(repo_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comments WHERE repo = ?", (repo_id,))
    conn.commit()
    conn.close()


create_table()

if __name__ == '__main__':
    print("Database")
    # print(get_userid('Rahul-Samedavar'))
    # print(get_all_comments())
