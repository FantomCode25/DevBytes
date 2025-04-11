from customtkinter import CTk, CTkButton, CTkFrame, CTkLabel, CTkImage, CTkEntry, CTkScrollableFrame, CTkCheckBox, CTkToplevel
from tkinter import messagebox
from PIL import Image
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser

from database import *
from discussions import moderate_discussion_comments
from issues import moderate_issues_comments
from pull_requests import moderate_pull_request_comments
from util import *
from meter import meter_fig

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from keys import CLIENT_ID, CLIENT_SECRET

#colors
L1 ='#ffffff'
L2 = '#fafbfc'
B1 =  '#E3E8EC'
D1 = '#1F2328'
H1 = '#1F883D'
NAVBAR_CLR = '#F6F8FA'
NH = '#EAEDF1'

import os

REDIRECT_URI = "http://localhost:8080/callback"

ACCESS_TOKEN = None
USERNAME = None


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global ACCESS_TOKEN, USERNAME

        if "/callback" in self.path:
            # Extract the "code" from the query parameters
            query = self.path.split("?")[1]
            params = dict(qc.split("=") for qc in query.split("&"))
            code = params.get("code")

            # Exchange the code for an access token
            ACCESS_TOKEN = exchange_code_for_token(code)

            # Fetch the username
            if ACCESS_TOKEN:
                USERNAME = fetch_username(ACCESS_TOKEN)

                # Respond to the browser
                self.send_response(200)
                self.end_headers()
                if USERNAME:
                    self.wfile.write(
                        f"Authentication successful! Hello, {USERNAME}. You can close this tab.".encode()
                    )

                    # Show success in the Tkinter app
                    messagebox.showinfo("Success", f"GitHub authentication successful!\nWelcome, {USERNAME}.")
                else:
                    self.wfile.write(b"Authentication failed. Could not fetch username.")
                    messagebox.showerror("Error", "GitHub authentication failed!")
                    USERNAME = "Failed"
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authentication failed. Check logs for details.")
                messagebox.showerror("Error", "GitHub authentication failed!")
                USERNAME = "Failed"

            # Shutdown the server
            threading.Thread(target=self.server.shutdown).start()

def exchange_code_for_token(code):
    url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Accept": "application/json"}

    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("Error exchanging code for token:", response.text)
        return None

def fetch_username(token):
    url = "https://api.github.com/user"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        return user_data.get("login")
    else:
        return None

def open_github_login():
    SCOPES = "repo user"
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}"
    )
    webbrowser.open(auth_url)

class App(CTk):
    def __init__(self, *args, **kwargs):
        CTk.__init__(self, fg_color=L1, *args, **kwargs)
        self.title("Git guardian")
        self.geometry("1000x550")
        self.initialize()
        self.add_navbar()
        self.partition()

    def initialize(self):
        self.loading = False
        self.online = True
        self.users = []
        self.repos = {}
        self.repo_btns = []
        self.user_id = 0
        self.repo_id = 0
        self.token = None
        self.user_name = None
        self.repo_name = None
        self.summary_sections = []

    def add_navbar(self):
        self.title_img = CTkImage(Image.open('./assets/title.jpg'), size=(190, 50))
        navbar = CTkFrame(self, fg_color=NAVBAR_CLR, height=70, corner_radius=0)
        navbar.grid(row=0,  column=0,  columnspan=2, sticky="NSEW")

        title = CTkLabel(navbar, text="", image=self.title_img)
        title.pack(side="left", padx=6,  fill='y',  anchor='center')

        change_user_btn = CTkButton(navbar, text="Change User", font=("Mona-Sans", 22, "bold"), command=self.logout,
                                    fg_color='transparent', hover_color=NH, border_color=B1, text_color=D1,
                                    border_width=2, corner_radius=30,  anchor="center")
        change_user_btn.pack(fill="y", side="right", pady=4, padx=10)

    def partition(self):
        self.left = CTkFrame(self, fg_color=L1, corner_radius=0, bg_color=L1,  width=130,
                             border_color=B1, border_width=1)
        self.left.grid(row=1,  column=0, sticky="NSEW")

        self.right = CTkFrame(self, fg_color=L1,  corner_radius=0, bg_color=B1, width=420,
                             border_color=B1, border_width=1)
        self.right.grid(row=1, column=1, sticky="NSEW")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=8)
        self.rowconfigure(0,  weight=0, minsize=70)
        self.rowconfigure(1,  weight=1)

        self.left.rowconfigure(0, weight=1)
        self.right.rowconfigure(0, weight=1)
        self.left.columnconfigure(0, weight=1)
        self.right.columnconfigure(0, weight=1)

        self.search_icon = CTkImage(Image.open('assets/search.png'), size=(28, 28))
        self.offline_icon = CTkImage(Image.open('assets/offline.png'), size=(70, 70))
        
        self.repos_list_container = CTkFrame(self.left, fg_color="transparent", corner_radius=0)
        self.repos_list_container.grid(row=0, column=0, stick='NSEW', pady=8)

        self.repos_search_frame = CTkFrame(self.repos_list_container, fg_color='transparent', corner_radius=0)
        self.repos_search_frame.pack(side='top', fill='x', padx=7, pady=2)
        self.repo_search_entry = CTkEntry(self.repos_search_frame, fg_color='transparent',  font=("Mona-Sans", 16, 'italic'), placeholder_text="search repository")
        self.repo_search_entry.pack(side='left', fill='both', expand=True, padx=5)
        self.repo_search_btn = CTkButton(self.repos_search_frame, text="", command=self.filter_repos,
                                         image=self.search_icon, width=0, border_spacing=0,
                                         corner_radius=0, fg_color="transparent", hover="transparent")
        self.repo_search_btn.pack(side='right', padx=2, fill="y")

        self.repos_list_frame = CTkScrollableFrame(self.repos_list_container, fg_color="transparent", corner_radius=0,
                                                   scrollbar_button_color=L1, scrollbar_button_hover_color=NH)
        self.repos_list_frame.pack(side='top', fill='both', padx=5, pady=10, expand=True)
        
        self.users_list_container = CTkFrame(self.left, fg_color="transparent", corner_radius=0)
        self.users_list_container.grid(row=0, column=0, stick='NSEW', pady=8)

        self.users_search_frame = CTkFrame(self.users_list_container, fg_color='transparent', corner_radius=0)
        self.users_search_frame.pack(side='top', fill='x', padx=7, pady=2)
        self.user_search_entry = CTkEntry(self.users_search_frame, fg_color='transparent',  font=("Mona-Sans", 16, "italic"), placeholder_text="search username")
        self.user_search_entry.pack(side='left', fill='both', expand=True, padx=5)
        self.user_search_btn = CTkButton(self.users_search_frame, text="", command=self.filter_users,
                                         image=self.search_icon, width=0, border_spacing=0,
                                         corner_radius=0, fg_color="transparent", hover="transparent")
        self.user_search_btn.pack(side='right', padx=2, fill="y")

        self.users_list_frame = CTkScrollableFrame(self.users_list_container, fg_color="transparent", corner_radius=0,
                                                   scrollbar_button_color=L1, scrollbar_button_hover_color=NH)
        self.users_list_frame.pack(side='top', fill='both', padx=5, pady=10, expand=True)

        self.add_profile()
        self.add_repo_page()

        self.add_error_pages()

        self.user_form = CTkFrame(self.right, fg_color=L1, corner_radius=0, bg_color=B1, border_color=B1, border_width=1)
        self.user_form.grid(row=0, column=0, sticky="NSEW")

        self.list_users ()
        self.filter_users()
        self.add_signup_page()

    def list_users(self):
        for user in self.users:
            user.destroy()
        users = get_all_users()
        for id, username in users:
            user_btn = CTkButton(master = self.users_list_frame, text=shorten(username), command= lambda id=id: self.set_user(id),
                                    fg_color='transparent', hover_color=NH, border_color=B1, text_color=D1,
                                    border_width=2, corner_radius=7, font=("Mona-Sans", 20))
            user_btn.name = username.lower()
            self.users.append(user_btn)

    def filter_users(self):
        key = self.user_search_entry.get().lower()
        for user in self.users:
            user.pack_forget()
            if key in user.name:
                user.pack(side="top", fill='x', padx=7, pady=2)

    def list_repos(self):
        for repo in self.repo_btns:
            repo.destroy()
        self.repo_btns = []
        for reponame, id in list(self.repos.items())[::-1]:
            repo_btn = CTkButton(master = self.repos_list_frame, text=shorten(reponame), command= lambda id=id, reponame=reponame: self.set_repo(id, reponame),
                                    fg_color='transparent', hover_color=NH, border_color=B1, text_color=D1,
                                    border_width=2, corner_radius=7, font=("Mona-Sans", 20), width=110)
            repo_btn.name = reponame.lower()
            self.repo_btns.append(repo_btn)

    def filter_repos(self):
        key = self.repo_search_entry.get().lower()
        for repo in self.repo_btns:
            repo.pack_forget()
            if key in repo.name:
                repo.pack(side="top", fill='x', padx=7, pady=2)

    def set_user(self, id):
        if not self.loading:
            self.loading = True
            self.user_id, self.user_name, self.token,  self.repos= get_user(id)
            self.user_page_title.configure(text=self.user_name)
            self.repos = json.loads(self.repos or '{}')
            try: 
                if self.online:
                    self.repos = load_repos_sub(self.user_id, self.user_name, self.token, self.repos)
            
            except ValueError as e:
                print("Username Changed")
                self.is_username_valid = False
                self.change_username_page.tkraise()

            except PermissionError as e:
                self.is_token_valid = False
                print("token Expired")
                self.change_token_page.tkraise()
            
            except Exception as e:
                self.online = False
                print("Network Error")
                self.network_error_page.tkraise()

            else:
                self.user_page.tkraise()
                self.list_repos()
                self.filter_repos() 
                self.repos_list_container.tkraise()
            self.loading = False
        
    def set_repo(self, id, name):
        self.repo_id = id
        self.repo_name = name
        self.remove_summary()
        self.repo_page_title.configure(text=name)
        self.repo_page_owner.configure(text=self.user_name)
        self.repo_page.tkraise()

    def add_signup_page(self):
        title = CTkLabel(self.user_form, text="New User",  font=("Mona-Sans-Black", 40), text_color = D1)
        title.grid(row=1, column=1, columnspan=2, pady=10)

        username_label = CTkLabel(self.user_form, text="GitHub Username", font=("Mona-Sans", 28))
        username_label.grid(row=2, column=1, sticky="NSEW", pady=10, padx=10)

        token_label = CTkLabel(self.user_form, text="GitHub Token       ", font=("Mona-Sans", 28))
        token_label.grid(row=3, column=1, sticky="NSEW", pady=10, padx=10)

        self.username_inp = CTkEntry(self.user_form, placeholder_text="username", font=("Mona-Sans", 24), border_color=B1, corner_radius=10)
        self.username_inp.grid(row=2, column=2, sticky="NSEW", pady=10, padx=10)

        self.token_inp = CTkEntry(self.user_form, placeholder_text="secret token", font=("Mona-Sans", 24), border_color=B1, corner_radius=10)
        self.token_inp.grid(row=3, column=2, sticky="NSEW", pady=10, padx=10)

        self.user_form_error = CTkLabel(self.user_form, text="", font=("Mona-Sans", 12), text_color='red')
        self.user_form_error.grid(row=4, column=1,  columnspan =2)

        btn = CTkButton(self.user_form,  text="Add User", font=("Roboto bold", 26), width=200, height=44, command=self.add_user,
                        fg_color=H1, hover_color=D1, corner_radius=12,  text_color=L1, border_color=B1, border_width=2)
        btn.grid(row=5, column=1, pady=5, sticky="N")

        CTkButton(self.user_form,  text="Login With Github", font=("Roboto bold", 26), width=200, height=44, command=self.start_auth_flow,
                        fg_color=H1, hover_color=D1, corner_radius=12,  text_color=L1, border_color=B1, border_width=2
        ).grid(row=5, column=2, pady=5, sticky="N")
        
        self.user_form.columnconfigure([1, 2], weight=2)
        self.user_form.columnconfigure([0, 3], weight=1, minsize=2)
        self.user_form.rowconfigure([ 1, 2, 3, 5], weight=1)
        self.user_form.rowconfigure([0, 5], weight=4, minsize=2)

    def add_user(self):
        username = self.username_inp.get()
        token = self.token_inp.get()
        
        self.username_inp.configure(border_color=B1 if username else 'red')
        self.token_inp.configure(border_color=B1 if token else 'red')
        if not username:
            self.user_form_error.configure(text="Please enter GitHub Username")
            return
        
        if not token:
            self.user_form_error.configure(text="Please enter GitHub token")
            return
        
        id = new_user_register(username, token)
        if id == 0:
            self.user_form_error.configure(text="Username doesn't exist")
        elif id == -1:
            self.user_form_error.configure(text="Invalid Token")
        elif id == -2:
            self.user_form_error.configure(text="Network Error")
        else:

            self.list_users ()
            self.filter_users()
            self.set_user(id)

            self.user_form_error.configure(text="")
        print(username,  token)

    def logout(self):
        self.user_id = 0
        self.repo_id = 0
        self.token = None
        self.online = True
        self.user_name = None
        self.repo_name = None
        self.repos = {}
        for repo in self.repo_btns:
            repo.destroy()
        self.users_list_container.tkraise()
        self.user_form.tkraise()

    def add_profile(self):
        self.user_page = CTkFrame(self.right, fg_color=L1, corner_radius=0, bg_color=B1, border_color=B1, border_width=1)
        self.user_page.grid(row=0, column=0, sticky="NSEW")

        sub = CTkFrame(self.user_page, fg_color=L1, corner_radius=10, border_color=B1, border_width=2)
        sub.pack(fill="both",  expand=True, padx=20, pady=20)

        self.user_page_title = CTkLabel(sub, text="User Profile", font=("Mona-Sans-Black", 40), text_color=D1)
        self.user_page_title.grid(row=0, column=0, sticky="NSEW")

        sub.rowconfigure([0], weight=1)
        sub.columnconfigure([0], weight= 1)

    def show_profile(self):
        print(self.repo_id, self.repo_name)
        self.user_page.tkraise()

    def add_repo_page(self):
        self.repo_page = CTkFrame(self.right, fg_color=L1, corner_radius=0, bg_color=B1, border_color=B1, border_width=1)
        self.repo_page.grid(row=0, column=0, sticky="NSEW")

        sub = CTkScrollableFrame(self.repo_page, corner_radius=0, fg_color=L1,
                                 scrollbar_button_color=B1, scrollbar_button_hover_color=NH)
        sub.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.repo_canvas = sub._parent_canvas

        self.repo_page_tools = CTkFrame(sub, fg_color=L2, border_color=B1, border_width=2)
        self.repo_page_tools.grid(row=1, column=1, sticky="NSEW", pady=10, ipadx=10, ipady=20)
        self.repo_page_tools.rowconfigure([0, 1],  weight=1)
        self.repo_page_tools.columnconfigure([0, 1, 2], weight=1)
        
        self.repo_page_title = CTkLabel(self.repo_page_tools, text="Repository Name", wraplength=600,font=("Mona-Sans-Black", 40), text_color=D1)
        self.repo_page_title.grid(row=0, column=0, columnspan=3, sticky="NSEW", pady=10, padx=10)
        self.repo_page_owner = CTkButton(self.repo_page_tools, text="Repository owner",command=self.show_profile,font=("Mona-Sans", 20),
                                    fg_color='transparent', hover_color=NH, border_color=B1, text_color=D1, border_width=2, corner_radius=30)
        self.repo_page_owner.grid(row=1, column=0, columnspan=3, sticky="NSE", pady=2, padx=10)

        CTkLabel(self.repo_page_tools, text="Issues", wraplength=600,font=("Mona-Sans-Bold", 24), text_color=D1
        ).grid(row=2, column=0, sticky="NSEW", pady=10, padx=10)

        CTkLabel(self.repo_page_tools, text="Discussion", wraplength=600,font=("Mona-Sans-Bold", 24), text_color=D1
        ).grid(row=2, column=1, sticky="NSEW", pady=10, padx=10)

        CTkLabel(self.repo_page_tools, text="Pull Requests", wraplength=600,font=("Mona-Sans-Bold", 24), text_color=D1
        ).grid(row=2, column=2, sticky="NSEW", pady=10, padx=10)

        self.issue_hide = CTkCheckBox(self.repo_page_tools, text="hide spam comments", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.issue_hide.grid(row=3, column=0, sticky="NSEW", padx=10,  pady=5)
        
        self.issue_dlt_com = CTkCheckBox(self.repo_page_tools, text="delete spam comments", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.issue_dlt_com.grid(row=4, column=0, sticky="NSEW", padx=10,  pady=5)
        
        self.issue_dlt = CTkCheckBox(self.repo_page_tools, text="delete spam issues", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.issue_dlt.grid(row=5, column=0, sticky="NSEW", padx=10,  pady=5)

        
        self.disc_hide = CTkCheckBox(self.repo_page_tools, text="hide spam comments", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.disc_hide.grid(row=3, column=1, sticky="NSEW", padx=10,  pady=5)
        
        self.disc_dlt_com = CTkCheckBox(self.repo_page_tools, text="delete spam comments", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.disc_dlt_com.grid(row=4, column=1, sticky="NSEW", padx=10,  pady=5)
        
        self.disc_dlt = CTkCheckBox(self.repo_page_tools, text="delete Spam discussions", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.disc_dlt.grid(row=5, column=1, sticky="NSEW", padx=10,  pady=5)
        

        self.pr_hide = CTkCheckBox(self.repo_page_tools, text="hide spam comments", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.pr_hide.grid(row=3, column=2, sticky="NSEW", padx=10,  pady=5)
        
        self.pr_dlt_com = CTkCheckBox(self.repo_page_tools, text="delete spam comments", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.pr_dlt_com.grid(row=4, column=2, sticky="NSEW", padx=10,  pady=5)
        
        self.pr_dlt = CTkCheckBox(self.repo_page_tools, text="close spam pull-requests", font=("Roboto", 16), text_color=D1,
                                     checkbox_height=22, checkbox_width=22,  border_width=2, corner_radius=8,
                                     border_color=D1, hover_color=H1, fg_color=H1)
        self.pr_dlt.grid(row=5, column=2, sticky="NSEW", padx=10,  pady=5)

        CTkButton(self.repo_page_tools,  text="Moderate", font=("Roboto bold", 28), command=self.moderate,
                    fg_color=H1, hover_color=D1, corner_radius=12,  text_color=NH
                ).grid(row=6, column=1, padx=20, pady=15, ipady=3)

        self.disc_spammers = None;
        self.iss_spammers = None;
        self.pr_spammers = None;

        self.repo_page_summary = CTkFrame(sub, fg_color=L2, border_color=B1, border_width=2)
        self.repo_page_summary.grid(row=2, column=1, sticky="NSEW", pady=10)
        self.repo_page_summary.rowconfigure([0, 1, 2],  weight=1)
        self.repo_page_summary.columnconfigure([0, 1], weight=1)

        
        CTkLabel(self.repo_page_summary, text="Repository Spam History", font=("Mona-Sans-Bold", 40),
                                    fg_color='transparent', text_color=D1
        ).grid(row=0, column=0, columnspan=2, sticky="NSEW", pady=20, padx=10)
        CTkButton(self.repo_page_summary, text="Get Summary", font=("Roboto bold", 28), command=self.get_summary,
                    fg_color=H1, hover_color=D1, corner_radius=12,  text_color=NH
        ).grid(row=1, column=0, columnspan=2, pady=10, padx=10, ipady=3)

        CTkButton(self.repo_page_tools,  text="Moderate", font=("Roboto bold", 28), command=self.moderate,
                    fg_color=H1, hover_color=D1, corner_radius=12,  text_color=NH
                ).grid(row=6, column=1, padx=20, pady=15, sticky="NSEW")
        

        self.spammer_list = CTkFrame(sub, fg_color=L2, border_color=B1, border_width=2)
        self.spammer_list.grid(row=3, column=1, sticky="NSEW", pady=10)
        self.spammer_list.columnconfigure([0], weight=1)

        CTkLabel(self.spammer_list, text="Who is Spamming in your Repository?", font=("Mona-Sans-Bold", 30),
                                    fg_color='transparent', text_color=D1
        ).grid(row=0, column=0, sticky="NSEW", pady=20, padx=10)
        CTkButton(self.spammer_list, text="get spammers", font=("Roboto bold", 28), command=self.get_spammers,
                    fg_color=H1, hover_color=D1, corner_radius=12,  text_color=NH
        ).grid(row=1, column=0, pady=10, padx=10, ipady=3)


        # self.repo_page_spammers = CTkFrame(sub, fg_color=L2, border_color=B1, border_width=2)
        # self.repo_page_spammers.grid(row=3, column=1, sticky="NSEW", pady=10)

        
        sub.rowconfigure([1, 2, 3],  weight=4, minsize=10)
        sub.rowconfigure([0, 4],  weight=1, minsize=10)
        sub.columnconfigure(1, weight=10,minsize=10)
        sub.columnconfigure([0,2], weight=1,minsize=10)

    def get_summary(self):
        self.counts = get_counts(self.repo_id)
        # self.counts = {
        #     'total_comments': 1231244,
        #     'total_spam_comments': 1813,
        #     'spam_discussions': 76,
        #     'total_discussion_comments': 4123,
        #     'spam_discussion_comments': {
        #         'prateek': 112,
        #         'catlover': 128,
        #         'code geek': 28,
        #         'professor': 651
        #     },
        #     'spam_issues': 51,
        #     'total_issue_comments': 33312,
        #     'spam_issues_comments': {
        #         'lone walker': 321,
        #         'catlover': 128,
        #         'code geek': 28,
        #         'professor': 651
        #     },
        #     'spam_pull_requests': 42,
        #     'total_pull_request_comments': 23231,
        #     'spam_pull_requests_comments': {
        #         'prateek': 322,
        #         'catlover': 128,
        #         'code geek': 28,
        #         'professor': 651
        #     }
        # }

        tot_com = self.counts['total_comments']
        spam_com = self.counts['total_spam_comments']
        disc_com = self.counts['total_discussion_comments']
        spam_disc_com = sum(self.counts['spam_discussion_comments'].values())
        iss_com = self.counts['total_issue_comments']
        spam_iss_com = sum(self.counts['spam_issues_comments'].values())
        pr_com = self.counts['total_pull_request_comments']
        spam_pr_com = sum(self.counts['spam_pull_requests_comments'].values())
        
        

        meter_sec = CTkFrame(self.repo_page_summary, fg_color=L2, border_color=B1, border_width=2,)
        meter_sec.grid(row=1, column=0, columnspan=2, sticky="NSEW", pady=2, padx=15)
        meter_sec.columnconfigure([0, 1, 2], weight=1)

        if iss_com or disc_com or pr_com:
            CTkLabel(meter_sec, text="Spam Comment Rates", font=("Mona-Sans", 28), anchor="s"
            ).grid(row=0, column=0, columnspan=3, sticky="SEW", padx=20, pady=10)

            if iss_com:
                issue_meter = meter_fig(meter_sec, spam_iss_com *100 / iss_com, lbl="Issues")
                issue_meter.get_tk_widget().grid(row=1, column=0, sticky="NSE", padx=10)
                CTkLabel(meter_sec, text=f"{spam_iss_com}/{iss_com}", font=("Mona-Sans", 16), anchor="s"
                ).grid(row=2, column=0, sticky="NSEW", padx=5)
            
            if disc_com:
                issue_meter = meter_fig(meter_sec, spam_disc_com *100 / disc_com, lbl="Disussions")
                issue_meter.get_tk_widget().grid(row=1, column=1, sticky="NSE", padx=10)
                CTkLabel(meter_sec, text=f"{spam_disc_com}/{disc_com}", font=("Mona-Sans", 16), anchor="s"
                ).grid(row=2, column=1, sticky="NSEW", padx=5)
            
            if pr_com:
                pr_meter = meter_fig(meter_sec, spam_pr_com *100 / pr_com, lbl="Pull Requests")
                pr_meter.get_tk_widget().grid(row=1, column=2, sticky="NSE", padx=10)
                CTkLabel(meter_sec, text=f"{spam_pr_com}/{pr_com}", font=("Mona-Sans", 16), anchor="s"
                ).grid(row=2, column=2, sticky="NSEW", padx=5)

        total_summary_sec = CTkFrame(self.repo_page_summary, fg_color=L2)
        total_summary_sec.grid(row=2, column=0, sticky="NSE", pady=10, padx=15)

        CTkLabel(total_summary_sec, text=f"Total Comments: {tot_com}", font=("Mona-Sans", 18), text_color=D1
        ).grid(row=1, column=0, sticky="NSW", padx=10, pady=3)
        CTkLabel(total_summary_sec, text=f"Spam Comments: {spam_com}", font=("Mona-Sans", 18), text_color=D1
        ).grid(row=2, column=0, sticky="NSW", padx=10, pady=3)
        CTkLabel(total_summary_sec, text=f"Spam Isssues: {self.counts['spam_issues']}", font=("Mona-Sans", 18), text_color=D1
        ).grid(row=3, column=0, sticky="NSW", padx=10, pady=3)
        CTkLabel(total_summary_sec, text=f"Spam Discussions: {self.counts['spam_discussions']}", font=("Mona-Sans", 18), text_color=D1
        ).grid(row=4, column=0, sticky="NSW", padx=10, pady=3)
        CTkLabel(total_summary_sec, text=f"Spam Pull Requests: {self.counts['spam_pull_requests']}", font=("Mona-Sans", 18), text_color=D1
        ).grid(row=5, column=0, sticky="NSW", padx=10, pady=3)

        total_summary_sec.rowconfigure([0, 6], weight=1, minsize=10)
        self.repo_page_summary.columnconfigure([0, 1], weight=1)

        total_pi_graph_sec = CTkFrame(self.repo_page_summary, fg_color=L2, border_color=B1, border_width=2)
        total_pi_graph_sec.grid(row=2, column=1, sticky="NSEW", pady=10, padx=15)
        if spam_disc_com+spam_iss_com+spam_pr_com > 0:
            fig = Figure(figsize = (3.2, 3), dpi=100, facecolor=L2, layout="constrained")
            plot = fig.add_subplot(111)
            categories = ["Discussions", "Issues", "Pull requests"]
            amounts = [spam_disc_com, spam_iss_com, spam_pr_com]
            plot.pie(amounts, autopct='%1.2f%%', textprops={'color': 'White'},  colors=['#1f883d', '#50a069', '#81b894'])
            plot.text(0, -1.25, "Spam Comments Distribution", color=D1, fontsize=16, ha="center",  va="top", )
            plot.legend(labels=categories, loc='lower left')
            canvas = FigureCanvasTkAgg(fig, total_pi_graph_sec)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)




        self.summary_sections = [total_summary_sec, total_pi_graph_sec,  meter_sec]
        
    def remove_summary(self):
        self.counts = None
        for section in self.summary_sections:
            section.destroy()
        self.summary_sections.clear()

        for frame in [self.disc_spammers, self.iss_spammers, self.pr_spammers]:
            if not frame is None:
                frame.destroy()
                frame = None

    def get_spammers(self):

        self.counts = get_counts(self.repo_id)

        self.disc_spammers = CTkFrame(self.spammer_list, fg_color="transparent", border_color=B1, border_width=2)
        self.disc_spammers.grid(row=1, column=0, sticky="NSEW", pady=3, padx=15)
        CTkLabel(self.disc_spammers, text="Discussions", font=("Roboto bold", 28)).grid(row=0, column=0, columnspan=3, sticky="NSEW", pady=7, padx=5)
        self.disc_spammers.columnconfigure([0, 1, 2], weight=1)

        self.iss_spammers = CTkFrame(self.spammer_list, fg_color="transparent", border_color=B1, border_width=2)
        self.iss_spammers.grid(row=2, column=0, sticky="NSEW", pady=3, padx=15)
        CTkLabel(self.iss_spammers, text="Issues", font=("Roboto bold", 28)).grid(row=0, column=0, columnspan=3, sticky="NSEW", pady=7, padx=5)
        self.iss_spammers.columnconfigure([0, 1, 2], weight=1)

        self.pr_spammers = CTkFrame(self.spammer_list, fg_color="transparent", border_color=B1, border_width=2)
        self.pr_spammers.grid(row=3, column=0, sticky="NSEW", pady=3, padx=15)
        CTkLabel(self.pr_spammers, text="Pull Requests", font=("Roboto bold", 28)).grid(row=0, column=0, columnspan=3, sticky="NSEW", pady=7, padx=5)
        self.pr_spammers.columnconfigure([0, 1, 2], weight=1)


        CTkLabel(self.disc_spammers, text="Username", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=0, padx=10, pady=5, sticky="NSEW")
        CTkLabel(self.disc_spammers, text="Spam Count", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=1, padx=10, pady=5, sticky="NSEW")
        CTkLabel(self.disc_spammers, text="Actions", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=2, padx=10, pady=5, sticky="NSEW")

        for i, username in enumerate(self.counts['spam_discussion_comments'].keys(), start=1):
            username_label = CTkLabel(self.disc_spammers, text=username, font=("Roboto", 20), fg_color=L2, cursor="hand2")
            username_label.grid(row=i+1, column=0, padx=10, pady=5, sticky="NSEW")
            username_label.bind("<Button-1>", lambda e, user=username: webbrowser.open(f"https://github.com/{user}"))

            CTkLabel(self.disc_spammers, text=str(self.counts['spam_discussion_comments'][username]), font=("Roboto", 20)).grid(row=i+1, column=1, padx=10, pady=5)

            block_button = CTkButton(
                self.disc_spammers, 
                text="Block", 
                command=lambda user=username: toggle_block(user, self.token), 
                fg_color=L2, 
                font=("Roboto", 20),
                text_color=D1,
                hover_color="red"
            )
            block_button.grid(row=i+1, column=2, padx=10, pady=5, sticky='NS')


        CTkLabel(self.iss_spammers, text="Username", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=0, padx=10, pady=5, sticky="NSEW")
        CTkLabel(self.iss_spammers, text="Spam Count", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=1, padx=10, pady=5, sticky="NSEW")
        CTkLabel(self.iss_spammers, text="Actions", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=2, padx=10, pady=5, sticky="NSEW")

        for i, username in enumerate(self.counts['spam_issues_comments'].keys(), start=1):
            username_label = CTkLabel(self.iss_spammers, text=username, font=("Roboto", 20), fg_color=L2, cursor="hand2")
            username_label.grid(row=i+1, column=0, padx=10, pady=5, sticky="NSEW")
            username_label.bind("<Button-1>", lambda e, user=username: webbrowser.open(f"https://github.com/{user}"))

            CTkLabel(self.iss_spammers, text=str(self.counts['spam_issues_comments'][username]), font=("Roboto", 20)).grid(row=i+1, column=1, padx=10, pady=5)

            block_button = CTkButton(
                self.iss_spammers, 
                text="Block", 
                command=lambda user=username: toggle_block(user, self.token), 
                fg_color=L2, 
                font=("Roboto", 20),
                text_color=D1,
                hover_color="red"
            )
            block_button.grid(row=i+1, column=2, padx=10, pady=5, sticky='NS')

        CTkLabel(self.pr_spammers, text="Username", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=0, padx=10, pady=5, sticky="NSEW")
        CTkLabel(self.pr_spammers, text="Spam Count", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=1, padx=10, pady=5, sticky="NSEW")
        CTkLabel(self.pr_spammers, text="Actions", font=("Robot", 20, "bold"), anchor="center").grid(row=1, column=2, padx=10, pady=5, sticky="NSEW")

        for i, username in enumerate(self.counts['spam_pull_requests_comments'].keys(), start=1):
            username_label = CTkLabel(self.pr_spammers, text=username, font=("Roboto", 20), fg_color=L2, cursor="hand2")
            username_label.grid(row=i+1, column=0, padx=10, pady=5, sticky="NSEW")
            username_label.bind("<Button-1>", lambda e, user=username: webbrowser.open(f"https://github.com/{user}"))

            CTkLabel(self.pr_spammers, text=str(self.counts['spam_pull_requests_comments'][username]), font=("Roboto", 20)).grid(row=i+1, column=1, padx=10, pady=5)

            block_button = CTkButton(
                self.pr_spammers, 
                text="Block", 
                command=lambda user=username: toggle_block(user, self.token), 
                fg_color=L2, 
                font=("Roboto", 20),
                text_color=D1,
                hover_color="red"
            )
            block_button.grid(row=i+1, column=2, padx=10, pady=5, sticky='NS')


    def add_error_pages(self):
        self.change_token_page = CTkFrame(self.right, fg_color=L1, corner_radius=0, bg_color=B1, border_color=B1, border_width=1)
        self.change_token_page.grid(row=0, column=0, sticky="NSEW")
        CTkLabel(self.change_token_page, text="Your GitHub token has expired", font=("Mona-Sans", 18), text_color=D1).grid(row=1, column=1, sticky="NSEW")
        CTkLabel(self.change_token_page, text="Update Token", font=("Mona-Sans-Black", 40), text_color=D1).grid(row=2, column=1, sticky="NSEW", pady=5)
        self.token_upd_inp = CTkEntry(self.change_token_page, placeholder_text="new token", font=("Roboto", 30), text_color=D1,width=300, justify="center")
        self.token_upd_inp.grid(row=3, column=1, sticky="NS", pady=5)

        CTkLabel(self.change_token_page, text="Invalid token", font=("Mona-Sans", 14), text_color='red').grid(row=4, column=1, sticky="NSEW")
        CTkButton(self.change_token_page,  text="Update", font=("Roboto bold", 28), width=200, height=44, command=self.change_token,
                        fg_color=H1, hover_color=D1, corner_radius=12,  text_color=NH
                        ).grid(row=5, column=1, pady=5)
        self.change_token_page.rowconfigure([0, 6], weight=1)
        self.change_token_page.columnconfigure([0, 2], weight=1)



        self.change_username_page = CTkFrame(self.right, fg_color=L1, corner_radius=0, bg_color=B1, border_color=B1, border_width=1)
        self.change_username_page.grid(row=0, column=0, sticky="NSEW")
        CTkLabel(self.change_username_page, text="looks like your GitHub username has changed", font=("Mona-Sans", 18), text_color=D1).grid(row=1, column=1, sticky="NSEW")
        CTkLabel(self.change_username_page, text="Update Username", font=("Mona-Sans-Black", 40), text_color=D1).grid(row=2, column=1, sticky="NSEW", pady=0)
        self.username_upd_inp = CTkEntry(self.change_username_page, placeholder_text="new username", font=("Roboto", 30), text_color=D1,width=300, justify="center")
        self.username_upd_inp.grid(row=3, column=1, sticky="NS", pady=5)

        self.username_upd_err_msg = CTkLabel(self.change_username_page, text="Enter Github username", font=("Roboto bold", 14), text_color=D1)
        self.username_upd_err_msg.grid(row=4, column=1, sticky="NSEW")
        CTkButton(self.change_username_page,  text="Update", font=("Roboto bold", 28), width=200, height=44, command=self.change_username,
                        fg_color=H1, hover_color=D1, corner_radius=12,  text_color=NH
                        ).grid(row=5, column=1, pady=5)
        self.change_username_page.rowconfigure([0, 6], weight=1)
        self.change_username_page.columnconfigure([0, 2], weight=1)


        self.network_error_page = CTkFrame(self.right, fg_color=L1, corner_radius=0, bg_color=B1, border_color=B1, border_width=1)
        self.network_error_page.grid(row=0, column=0, sticky="NSEW")
        CTkLabel(self.network_error_page, text="",image=self.offline_icon).grid(row=0, column=0, sticky="NSE", padx=5)
        CTkLabel(self.network_error_page, text="Network Error", font=("Mona-Sans", 44)).grid(row=0, column=1, sticky="NSW", padx=5)
        self.network_error_page.rowconfigure(0, weight=1)
        self.network_error_page.columnconfigure([0, 1], weight=1)

    def change_username(self):
        if not self.loading:
            self.loading = True
            new_username = self.username_upd_inp.get()
            if (username_exists(new_username)):
                if (self.user_id):
                    update_username(self.user_id, new_username)
                    self.set_user(self.user_id)
            else:
                self.username_upd_err_msg.configure(text="Username doesn't exist",  text_color='red')
            self.loading = False
            
    def change_token(self):
        new_token= self.token_upd_inp.get()
        update_token(self.user_id, new_token)
        self.set_user(self.user_id)

    def moderate(self):
        progress_window = CTkToplevel(self.master,  fg_color=L1)
        progress_window.title(f"Moderating {self.repo_name}")
        progress_window.attributes("-topmost", True)
        progress_window.focus()

        progress_window.columnconfigure([0, 1, 2], weight=1)

        CTkLabel(progress_window, text=self.repo_name, font=("Mona-Sans-Black", 40, "bold")).grid(row=0, column=0, columnspan=3, sticky="nsew",  pady=10)

        sections = ["Issues", "Discussions", "Pull Requests"]
        section_progress = {}
        frames = {}

        for id, name in enumerate(sections):
            frame = CTkFrame(progress_window,  fg_color=L1, border_color=B1, border_width=2)
            frame.grid(row=1, column=id, padx=10, pady=10,  sticky="nsew", ipadx=5, ipady=10)
            CTkLabel(frame, text=f"{name}", font=("Mona-Sans-Bold", 24, "bold"), text_color=D1).grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
            comments_label = CTkLabel(frame, text="Comments Fetched: 0", font=("Roboto", 16))
            comments_label.grid(row=1, column=0, sticky="w", padx=15)
            spam_label = CTkLabel(frame, text="Spam Comments: 0", font=("Roboto", 16))
            spam_label.grid(row=2, column=0, sticky="w", padx=15)
            deleted_label = CTkLabel(frame, text=f"{name} Deleted/Closed: 0", font=("Roboto", 16))
            deleted_label.grid(row=3, column=0, sticky="w", padx=15)
            status_label = CTkLabel(frame, text=f"Starting..", font=("Roboto", 16))
            status_label.grid(row=4, column=0, sticky="ew", padx=15)
            msg_frame = CTkFrame(frame, fg_color=L1, border_color=B1, border_width=1, width=300, height=50)
            msg_frame.grid(row=5, column=0, sticky="nsew", padx=15, pady=15)
            message_label = CTkLabel(msg_frame, text=f"Not Yet Started",  wraplength=300,  font=("Roboto Italic", 14))
            message_label.pack(fill="both", expand=True, padx=5, pady=5)
            #   Starting...              .
# Moderation Completed without any Errors
            frame.rowconfigure([0,1,2,3,4,5], weight=1)
            frame.columnconfigure(0, weight=1, minsize=380)

            frames[name] = frame
            section_progress[name] = {
                "comments_label": comments_label,
                "spam_label": spam_label,
                "deleted_label": deleted_label,
                "status_label": status_label,
                "message_label": message_label
            }

        moderation_thread = threading.Thread( target=self._run_moderation, args=(section_progress, frames), daemon=True)
        moderation_thread.start()

    def _run_moderation(self, section_progress,  frames):
        repo_id = self.repo_id
        iss_h = self.issue_hide.get()
        iss_dc = self.issue_dlt_com.get()
        iss_d = self.issue_dlt.get()
        disc_h = self.disc_hide.get()
        disc_dc = self.disc_dlt_com.get()
        disc_d = self.disc_dlt.get()
        pr_h = self.pr_hide.get()
        pr_dc = self.pr_dlt_com.get()
        pr_d = self.pr_dlt.get()

        def update_section(section, comments, spam, deleted, message, done):
            section_progress[section]["comments_label"].configure(text=f"Comments Fetched: {comments}")
            section_progress[section]["spam_label"].configure(text=spam)
            section_progress[section]["deleted_label"].configure(text=deleted)
            section_progress[section]["status_label"].configure(text=f"{"Completed" if done else "Moderating"}")
            section_progress[section]["message_label"].configure(text=message)


        if iss_h or iss_dc or iss_d:
            i_l = 'Comments Deleted: ' if iss_dc else 'Comments Hidden: '
            update_callback = lambda comments, spam, deleted, message="", done=False: update_section("Issues", comments, f"{i_l}{spam}", f"Issues deleted: {deleted}", message, done)
            moderate_issues_comments(repo_id, delete_comments=iss_dc, delete_issues=iss_d, callback=update_callback)
        else:
            frames["Issues"].destroy()


        if disc_h or disc_dc or disc_d:
            d_l  = 'Comments Deleted: ' if disc_dc else 'Comments Hidden: '
            update_callback = lambda comments, spam, deleted, message="", done=False: update_section("Discussions", comments, f"{d_l}{spam}", f"Discussions deleted: {deleted}", message, done )
            moderate_discussion_comments(repo_id, delete_comments=disc_dc, delete_discussions=disc_d, callback=update_callback)
        else:
            frames["Discussions"].destroy()

        if pr_h or pr_dc or pr_d:
            p_l = 'Comments Deleted: ' if pr_dc else 'Comments Hidden: '
            update_callback = lambda comments, spam, closed, message="", done=False: update_section("Pull Requests", comments, f"{p_l}{spam}", f"Pull Requests Closed: {closed}",  message, done )
            moderate_pull_request_comments(repo_id, delete_comments=pr_dc, delete_pr=pr_d, callback=update_callback)
        else:
            frames["Pull Requests"].destroy()

    def start_http_server(self):
        server = HTTPServer(("localhost", 8080), OAuthHandler)
        print("Server running at http://localhost:8080...")
        server.serve_forever()



    def start_auth_flow(self):
        global ACCESS_TOKEN, USERNAME
        t = threading.Thread(target=self.start_http_server, daemon=True)
        t.start()
        open_github_login();
        while USERNAME is None:
            time.sleep(0.24)

        
        if USERNAME is None or USERNAME == "Failed":
            messagebox.showerror("Error", "GitHub authentication failed!")
            return
        user_id = get_userid(USERNAME)
        if user_id == -1:
            user_id = new_user_register(USERNAME, ACCESS_TOKEN)
        else:
            update_token(user_id, ACCESS_TOKEN)
        self.set_user(user_id)

        ACCESS_TOKEN = None
        USERNAME = None



app = App()
app.mainloop()