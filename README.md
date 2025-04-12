# 🚀 Project Name

**Team Name:** DevBytes  
**Hackathon:** FantomCode '25  
**Date:** 12-04-2025

---

## 📖 Table of Contents

1. [Introduction](#-introduction)
2. [Problem Statement](#-problem-statement)
3. [Solution Overview](#-solution-overview)
4. [Tech Stack](#-tech-stack)
5. [Architecture / Diagram (if any)](#-architecture--diagram-if-any)
6. [Installation & Usage](#-installation--usage)
7. [Team Members](#-team-members)

---

## 🧠 Introduction

**Git-Guardian** is a secure and adaptive spam moderation tool for GitHub repositories.  
It’s designed for **open-source maintainers** who want to keep their discussions, issues, and pull requests clean from spam, while maintaining control and flexibility.  
The project is impactful as it empowers maintainers to **automatically moderate**, **fine-tune spam models**, and **ensure token security**, improving collaboration and reducing manual effort.

---

## ❗ Problem Statement

- Open-source repos face frequent **spam attacks** in issues, discussions, and pull requests.
- Manual moderation is **time-consuming**, especially for large or popular projects.
- No current solution offers **adaptive learning** based on maintainer feedback.
- Using server-side moderation tools raises **security concerns** due to GitHub token handling.
- Maintainers lack **customizable** tools to define what constitutes spam in their context.

---

## ✅ Solution Overview


**Git-Guardian** solves the problem with two powerful tools:

1. **GUI Application (CustomTkinter-based)**
   - Runs locally for **maximum security** (tokens stay on the device).
   - Lets users:
     - Select repos and moderation targets (issues, PRs, discussions)
     - Choose actions (delete, hide, close).
     - Tracks Realtime changes to comment status to learn users behavior.
     - Automatically fine-tune the model based on user behavior.
     - Get detailed statistics on spam activity in your repo.
     - Penalize the spammers by blocking them directly from application.
   - Multi-Threaded: Can moderate multiple repositories simultaneously. 
   - Autonomous: once started, Moderation is done autonomously.
   - Multi-Account: Switch between multiple accounts seemlessly.

2. **GitHub Workflow Tool**
   - Lightweight bot to auto-moderate low-activity repos via GitHub Actions
   - Easy to add from **GitHub Marketplace**

**Key Features:**
- 🧠 AI-based Spam Detection trained on 80K+ messages  
- 🔐 Local token usage for enhanced security  
- 🔁 Self-improving model through fine-tuning  
- ⚙️ Full moderation control for maintainers  
---

## 🛠️ Tech Stack

1. **GUI Application**
- **Frontend:** CustomTkinter.
- **Database:** SQLite3
- **APIs:** GraphQL, GitHub
- **Libraries:** requests, joblib
- **Tools:** Figma, Git

2. **WorkFlow Version**
- **Frontend:** HTML, CSS, JS.
- **Database:** Supabase
- **APIs:** GraphQL
- **Tools:** Github Actions

---

## 🧩 Architecture / Diagram

![](Images/Sequence_Diagram.png)


---

## 🧪 Installation & Usage

### Prerequisites

- python, pip
- Dependencies listed in `requirements.txt`

### Steps

- Clone the repository
    ```bash
    git clone https://github.com/FantomCode25/DevBytes.git
    ```
- Navigate into the project directory
    ```bash
    cd DevBytes
    ```

- Install dependencies
    ```bash
    pip install -r .\requirements.txt
    ```

- Get Your OAuth Client ID and Secret from GITHUB. [learn more.](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
- create a file names keys.py and add Client ID and Secret.
    ```python
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    ```

- Start the Application
    ```bash
    python app.py
    ```

### Steps
- Open The Application.
- If not Logged in already, Click Login with Github for Oauth or paste username and token manually.
- Select your username from the list.
- Select the repository.
- Select Moderation options.
- click run moderation.
- Moderation is Autonomous, You can do other works while moderation is in progresss.
- You can track the Progress in the popup.
- As Moderation is Multithreaded, You can moderate multiple comments simultenously.