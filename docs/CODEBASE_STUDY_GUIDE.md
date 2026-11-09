# Jeevithaya Source Code Study Guide & Viva Preparation Handbook
**For:** Group 5 Members (MIT 2025/2026 Batch)  
**Objective:** Master the codebase, understand full-stack data flows, and prepare for oral defense / viva examinations.  

---

## 1. Project Directory Structure & Component Roles

```
c:\wamp64\www\Jeevithaya-mit\
│
├── manage.py                     # Django CLI entrypoint for running servers & migrations
├── requirements.txt              # Python library dependencies (Django, mysqlclient, python-dotenv)
├── .env.example                  # Environment configuration template (DB credentials, secret keys)
├── db.sqlite3                    # Local SQLite database (used when MySQL is offline)
│
├── jeevithaya/                   # ROOT PROJECT CONFIGURATION
│   ├── settings.py               # Core Django config: DB engines, installed apps, static dirs
│   ├── urls.py                   # Master URL routing (maps web pages & includes bloodbank/urls.py)
│   ├── wsgi.py / asgi.py         # Web server gateway interfaces for production hosting
│   ├── views.py                  # Page-rendering views (renders login.html, dashboard.html, etc.)
│   │
│   ├── templates/                # HTML5 PRESENTATION TEMPLATES
│   │   ├── login.html            # Authentication gateway
│   │   ├── dashboard.html        # Main KPI metrics and recent requisitions
│   │   ├── donors.html           # Donor registration and eligibility directory
│   │   ├── patients.html         # Patient records and clinical transfusion needs
│   │   ├── requests.html         # Hospital blood and plasma requisitions
│   │   ├── inventory.html        # Cold-chain blood units and shelf-life tracker
│   │   ├── donation.html         # Intake donation session logs
│   │   ├── verification.html     # Laboratory screening (HIV, Hep B/C, Syphilis)
│   │   ├── disposal.html         # Bio-hazardous waste destruction logs
│   │   ├── reports.html          # Operational intelligence and statutory audits
│   │   ├── create_user.html      # System Admin user provisioner
│   │   ├── profile.html          # User account settings
│   │   └── logout.html           # Clean session invalidation page
│   │
│   └── static/                   # CLIENT-SIDE ASSETS
│       ├── css/style.css         # Modern responsive CSS styling (CSS Grid, Flexbox, Cards)
│       └── js/                   # FRONTEND JAVASCRIPT CONTROLLERS
│           ├── api.js            # Unified REST client with global window.*API helpers
│           ├── rbac.js           # Role-Based Access Control and menu display engine
│           ├── login.js          # Authentication form controller
│           ├── dashboard.js      # Dashboard KPI fetching & live stat counters
│           ├── donors.js         # Donor CRUD controller with search/filtering
│           ├── patients.js       # Patient registration controller
│           ├── requests.js       # Requisition management controller
│           ├── inventory.js      # Inventory shelf-life controller
│           ├── donation.js       # Phlebotomy intake controller
│           ├── verification.js   # Lab screening controller
│           ├── disposal.js       # Bio-waste disposal controller
│           ├── reports.js        # Analytics calculations and CSV export
│           ├── create_user.js    # User account creation controller
│           └── profile.js        # Profile updater
│
└── bloodbank/                    # CORE BACKEND DJANGO APP
    ├── models.py                 # OOP Domain Entities (BasePerson, Donor, Inventory, User, etc.)
    ├── services.py               # OOP Service Layer (InventoryService, RequestFulfillmentService, Strategies)
    ├── views.py                  # REST API Endpoints (CRUD handlers, Auth, Stats, Normalizers)
    ├── urls.py                   # REST API routing endpoints (/donors/, /inventory/, etc.)
    └── admin.py                  # Django administrative portal registrations
```

---

## 2. The Life of a Request (End-to-End Trace)

Understanding how data travels through the system is the #1 question professors ask in oral examinations.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant JS as donors.js / api.js
    participant URL as jeevithaya/urls.py & bloodbank/urls.py
    participant View as bloodbank/views.py (api_donors)
    participant Service as bloodbank/services.py
    participant Model as bloodbank/models.py (Donor)
    participant DB as MySQL / SQLite

    User->>JS: Enters donor details and clicks "Register Donor"
    JS->>JS: Validates inputs; calls window.donorAPI.create(payload)
    JS->>URL: HTTP POST /api/donors/ with JSON payload
    URL->>View: Routes to api_donors(request)
    View->>View: normalize_payload(Donor, data) [Handles camelCase/PascalCase]
    View->>Model: Donor.objects.create(**normalized)
    Model->>DB: INSERT INTO Donor (DonorID, Name, BloodGroup, ...) VALUES (...)
    DB-->>Model: Success confirmation
    Model-->>View: Returns saved Donor instance
    View-->>JS: HTTP 201 Created with JSON model_to_dict(donor)
    JS->>JS: Appends new donor to table and updates UI in real-time!
```

---

## 3. Where are the OOP Concepts in the Code?

If an examiner asks: *"Show me where your project uses OOP principles"*, point directly to these files and lines:

### 1. Abstraction
* **Location:** `bloodbank/models.py` (`BaseAuditableEntity`, `BasePerson`) and `bloodbank/services.py` (`BaseService`, `BaseReportStrategy`).
* **Explanation:** `BasePerson` abstracts common human attributes (`Name`, `BloodGroup`, `Gender`, `Address`) without being instantiated directly (`abstract = True`). `BaseService` abstracts database querying from the rest of the application.

### 2. Inheritance
* **Location:** `bloodbank/models.py`
  * `class Donor(BasePerson):` inherits demographic fields and age-calculation methods from `BasePerson`.
  * `class Patient(BasePerson):` also inherits from `BasePerson`, adding hospital-specific attributes like `HospitalID` and `Urgency`.

### 3. Encapsulation
* **Location:** `bloodbank/models.py`
  * `User.set_password()` and `User.check_password()`: Password hashing logic is kept private to the `User` class.
  * `Inventory.is_expired()`: Calculates shelf-life validity based on internal `ExpiryDate`.
  * `Verification.is_safe()`: Determines safety compliance by inspecting all 4 test attributes.
  * `BloodRequest.approve()`, `.fulfill()`, `.reject()`: Encapsulates state transitions directly on the model.

### 4. Polymorphism
* **Location:** `bloodbank/services.py`
  * Strategy Pattern: `BaseReportStrategy` defines an abstract method `generate(days)`.
  * Concrete classes `InventoryReportStrategy`, `DonationReportStrategy`, and `RequestReportStrategy` each implement `.generate(days)` with completely different mathematical logic.
  * `AnalyticsContext` executes them polymorphically using the exact same interface call: `context.execute()`.

---

## 4. Top 10 Viva / Defense Questions & Model Answers

### Q1: Why did you choose a decoupled REST API rather than standard Django template form submissions?
> **Answer:** *"A decoupled REST API separates data management from presentation. It allows our frontend to dynamically update tables, apply filters, and refresh KPI statistics without triggering full-page browser reloads. Furthermore, it makes our backend ready to support mobile apps or external hospital integration in the future."*

### Q2: How did you implement Role-Based Access Control (RBAC)?
> **Answer:** *"We implemented a defense-in-depth model. On the client side, `rbac.js` dynamically inspects the user's authenticated role and hides menu links that the user is not entitled to see. On the server side, our Django session authentication tracks `user_role` and our API endpoints validate access before executing sensitive operations."*

### Q3: What happens when a laboratory screening test fails?
> **Answer:** *"When a Lab Assistant records a failed verification in `verification.html`, the `InventoryService` intercepts the record. It automatically flags the physical unit as `Expired` / quarantined so it can never be issued to a patient, and automatically logs a bio-hazardous waste record in `Disposal` with the reason 'Failed Verification' for legal audit compliance."*

### Q4: How are passwords stored and secured?
> **Answer:** *"Passwords are never stored in plain text. We utilize Django's `make_password()` function which implements PBKDF2 with a SHA-256 hash algorithm and cryptographic salt. Even if the database were compromised, the passwords cannot be reverse-engineered."*

### Q5: How does your system prevent expired blood from being transfused?
> **Answer:** *"In `bloodbank/models.py`, each `Inventory` unit has an `is_expired()` method and an `ExpiryDate`. Units past their expiration date are visually highlighted in red, disabled from being selected, and excluded from active requisition matching queries."*

### Q6: What was the main purpose of your `normalize_payload` function in `views.py`?
> **Answer:** *"JavaScript idioms favor camelCase (e.g. `patientId`, `bloodGroup`), whereas Python and our Django ORM models use PascalCase (`PatientID`, `BloodGroup`). To prevent runtime `TypeError: unexpected keyword argument` exceptions, we built a normalization utility that dynamically maps incoming client keys to the model's actual fields."*

### Q7: What design pattern did you use in the codebase?
> **Answer:** *"We implemented two primary design patterns:  
> 1. The **Service Layer Pattern** (`services.py`) to decouple business rules (e.g. verification status triggers and request fulfillment) from HTTP request/response views.  
> 2. The **Strategy Pattern** for analytical reporting, where different report algorithms implement a common `BaseReportStrategy` polymorphically."*

### Q8: What happens if MySQL is not installed on an examiner's machine?
> **Answer:** *"We designed our configuration in `jeevithaya/settings.py` to be environment-resilient. By setting the environment variable `DB_ENGINE=sqlite`, the system immediately and transparently runs on a zero-configuration SQLite database (`db.sqlite3`) without requiring MySQL."*

### Q9: How do you handle concurrency or double-allocation if two hospitals request the same blood unit?
> **Answer:** *"In `RequestFulfillmentService`, units transition through a `Reserved` state before being marked `Issued`. The allocation query filters strictly for `Status='Available'`, ensuring already allocated units are excluded from subsequent query sets."*

### Q10: How can this system be scaled in the future?
> **Answer:** *"Because the backend uses Django's modular app structure and standard REST endpoints, we can easily containerize it with Docker, add Redis for caching session states, deploy behind an Nginx reverse proxy, and connect to automated SMS gateways for urgent donor recall alerts."*

---

## 5. Quick Team Setup Cheat Sheet

```powershell
# 1. Open Terminal in Project Directory
cd c:\wamp64\www\Jeevithaya-mit

# 2. Install Python Requirements
pip install -r requirements.txt

# 3. Choose your database:
# Option A: MySQL (ensure WAMP MySQL is running)
# Option B: SQLite (Quick start):
$env:DB_ENGINE="sqlite"

# 4. Apply Database Migrations
python manage.py makemigrations
python manage.py migrate

# 5. Start the Server
python manage.py runserver

# 6. Test Login
# URL: http://127.0.0.1:8000/
# Email: admin@jeevithaya.com
# Password: admin123
```
