# 🚀 Jeevithaya (ජීවිතය) — Team Setup & Onboarding Guide

> **MIT Group Assignment (2025/2026 Batch) — Group 5**  
> Welcome to the team repository! Follow this guide to set up the project on your machine in under **5 minutes**.

---

## 📋 Prerequisites

Before you begin, ensure you have:
1. **Python 3.10+** installed:
   - Check by opening terminal / PowerShell: `python --version`
   - If not installed, download from [python.org](https://www.python.org/) (ensure **"Add Python to PATH"** is checked).
2. **Git** installed:
   - Check with: `git --version`
   - If not installed, download from [git-scm.com](https://git-scm.com/).
3. *(Optional)* **WAMP / XAMPP Server** if you want to run with live MySQL. (If you don't have WAMP/MySQL, don't worry! You can run in **SQLite mode** with zero setup).

---

## ⚡ Quick 5-Minute Setup

### Step 1: Clone the Repository

Open **PowerShell** or **Command Prompt** in the folder where you want to keep the project (e.g. `c:\projects` or `c:\wamp64\www`):

```powershell
git clone https://github.com/walakulu7/jeevithaya-mit.git
cd jeevithaya-mit
```

---

### Step 2: Create & Activate Virtual Environment (Recommended)

```powershell
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# (If PowerShell gives an execution policy error, run this once):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Step 3: Install Required Dependencies

```powershell
pip install -r requirements.txt
```

---

### Step 4: Choose Your Database Mode

You have two choices:

#### 🟢 Option A: SQLite (Fastest — No MySQL Required)
If you don't have WAMP / MySQL installed, or want to test immediately:

```powershell
# In PowerShell:
$env:DB_ENGINE="sqlite"

# In standard CMD (if using Command Prompt):
# set DB_ENGINE=sqlite
```

#### 🟡 Option B: MySQL (WAMP / XAMPP Server)
1. Start your **WAMP** or **XAMPP** service.
2. Open **phpMyAdmin** (`http://localhost/phpmyadmin`).
3. Click **New** and create a database named: `jeevithaya_mit` (Collation: `utf8mb4_general_ci`).
4. By default, Django connects with user `root` and blank password `""`. If you have a password, set it in PowerShell:
   ```powershell
   $env:DB_ENGINE="mysql"
   $env:DB_NAME="jeevithaya_mit"
   $env:DB_USER="root"
   $env:DB_PASSWORD=""  # Put your MySQL password here if you have one
   ```

---

### Step 5: Run Migrations & Seed Sample Data

Run these two commands to create all database tables and populate sample data (donors, patients, blood units, users, and requisitions):

```powershell
# Apply database schema
python manage.py migrate

# Seed sample hospital & blood bank records
python manage.py seed_db
```

Output should show:
```
Seeding Jeevithaya database...
Created 5 donors.
Created 3 patients.
Created 5 inventory blood units.
Created 3 blood requisitions.
Created 4 user accounts.
Database successfully seeded!
```

---

### Step 6: Start the Development Server

```powershell
python manage.py runserver
```

Now open your web browser and navigate to:  
👉 **`http://127.0.0.1:8000/`**

---

## 🔐 Default Demo Accounts

Use any of these 4 pre-configured accounts to test different roles and permissions:

| Role | Email | Password | Permissions & Available Pages |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@jeevithaya.com` | `admin123` | **Full access**: Dashboard, Donors, Patients, Requests, Inventory, Donation, Verification, Disposal, Reports, Create User. |
| **Hospital Admin** | `hospital@jeevithaya.com` | `hospital123` | Patient management, clinical request approvals, inventory view, executive reports. |
| **Front Office** | `frontoffice@jeevithaya.com` | `front123` | Donor registrations, patient admissions, new blood requisitions. |
| **Lab Assistant** | `lab@jeevithaya.com` | `lab123` | Phlebotomy intake, TTID screening (HIV/HBV/HCV/Syphilis), cold-chain inventory & disposal. |

---

## 🧪 Running the Automated Test Suite

To verify that the Object-Oriented Architecture, services, and API endpoints are working properly:

```powershell
python manage.py test bloodbank
```

Expected result:
```
Ran 8 tests in 1.1s
OK
```

---

## 📚 Essential Assignment Resources for Team Members

All assignment deliverables are prepared and located in the [`docs/`](docs/) directory:

1. **📖 User Manual:** [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)  
   Complete walkthrough of every module with screenshots and step-by-step guides.

2. **📊 Presentation Slides & Speaker Notes:** [`docs/PRESENTATION_SLIDES.md`](docs/PRESENTATION_SLIDES.md)  
   15-slide deck outline. **The presentation has been divided into 5 equal parts** with allocated member roles and word-for-word speaker notes!

3. **🖥️ Live Interactive Slides Deck:**  
   When running the server, visit: **`http://127.0.0.1:8000/presentation.html`** (or click **Slides Deck ↗** in the dashboard sidebar) for a full-screen, keyboard-navigable slide deck.

4. **🎓 Codebase Study Guide & Viva Defense:** [`docs/CODEBASE_STUDY_GUIDE.md`](docs/CODEBASE_STUDY_GUIDE.md)  
   Explains the request lifecycle, code references, and top 10 questions the lecturer/examiner will ask during viva defense with exact answers.

5. **📐 System Architecture & UML Diagrams:** [`docs/SYSTEM_DIAGRAMS.md`](docs/SYSTEM_DIAGRAMS.md)  
   Mermaid diagrams including UML Class Diagram, Entity-Relationship Diagram (ERD), and Sequence Diagrams.

---

## ❓ Troubleshooting & FAQs

### Q1: PowerShell says `Activate.ps1 cannot be loaded because running scripts is disabled`
**Fix:** Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2: Error `OperationalError: (1045, "Access denied for user 'root'@'localhost'")`
**Fix:** Your MySQL root user has a password set. Run:
```powershell
$env:DB_PASSWORD="your_actual_mysql_password"
python manage.py migrate
```
Or switch to SQLite by running:
```powershell
$env:DB_ENGINE="sqlite"
python manage.py migrate
```

### Q3: `Port 8000 is already in use`
**Fix:** Run Django on another port:
```powershell
python manage.py runserver 8080
```
Then visit `http://127.0.0.1:8080/`.

---

**Happy Coding! If you have any questions or get stuck, ping the group chat! 🤝**
