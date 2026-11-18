# Jeevithaya (ජීවිතය) — Centralized Blood & Plasma Management System

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x%20%7C%206.x-green.svg)](https://www.djangoproject.com/)
[![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20SQLite-orange.svg)](https://www.mysql.com/)
[![Course](https://img.shields.io/badge/Course-MIT%202025%2F2026-purple.svg)]()

> **Master of Information Technology (MIT) Assignment**  
> **Developed by:** Group 5 (MIT 2025/2026 Batch)

---

## 📌 Executive Summary

**Jeevithaya** is an enterprise-grade, centralized web application designed for healthcare facilities, blood transfusion centers, and hospital surgical wards. It addresses critical logistical challenges in blood banking by providing real-time cold-chain inventory monitoring, automated infectious disease testing gates, and clinical requisition fulfillment.

---

## 🚀 Key Modules & Capabilities

1. **Executive Dashboard:** Live metrics for available blood bags, urgent patient requisitions, and donor counts.
2. **Donor Management:** Registration, contact tracking, and eligibility validation for voluntary donors.
3. **Patient Registration:** Triage categorization (`Normal`, `Urgent`, `Critical`) and clinical transfusion logs.
4. **Requisition & Smart Allocation:** Hospital blood requests with automated inventory compatibility matching and stock deduction.
5. **Cold-Chain Inventory:** Expiration tracking, batch monitoring, and automated alerts for spoiled units.
6. **Laboratory Screening:** Serological quality control testing for HIV, Hepatitis B, Hepatitis C, and Syphilis.
7. **Bio-Hazardous Disposal:** Statutory disposal logging for contaminated or expired blood units.
8. **Operational Analytics:** Filterable management reports and CSV data export for health authorities.
9. **User Administration:** Role-Based Access Control (RBAC) and credential delegation.

---

## 🏛️ Object-Oriented Programming (OOP) Architecture

The application has been engineered to showcase the **4 Core Pillars of OOP**:

| OOP Pillar        | Code Implementation | Description |
| :---------------- | :------------------ | :---------- |
| **Abstraction**   | `BaseAuditableEntity`, `StatefulEntity`, `BasePerson` (`models.py`); `BaseService`, `BaseReportStrategy` (`services.py`); `ModelResource` (`api/common.py`) | Abstract classes define the contracts; concrete classes supply only what differs. |
| **Inheritance**   | Every model inherits `BaseAuditableEntity`; `Donor`/`Patient` inherit `BasePerson`; `BloodRequest`/`Inventory` inherit `StatefulEntity`; one `ModelResource` subclass per API resource | Audit fields, age calculation, lifecycle rules and CRUD behaviour are written once. |
| **Encapsulation** | `StatefulEntity.transition_to()` with per-class `TRANSITIONS`; `BloodRequest.approve()/fulfill()/reject()`; `Inventory.mark_issued()/mark_discarded()`; `User.set_password()/check_password()` | Status can only change through guarded methods, and passwords are only stored hashed. |
| **Polymorphism**  | `AnalyticsContext` runs any `BaseReportStrategy`; `ModelResource` hooks (`perform_create`, `perform_update`, `authorize`) overridden per resource | The caller is unaware of the concrete class. |
| **Association**   | Foreign keys: `Donation → Donor`, `Inventory → Donation, Donor`, `Verification → Inventory, Donor`, `Disposal → Inventory`, `BloodRequest → Patient` | Objects navigate to each other (`unit.donation.donor`) and the database enforces integrity. |

### SOLID Principles

| Principle | Where it is applied |
| :-------- | :------------------ |
| **Single Responsibility** | `models.py` holds entity rules, `services.py` holds workflows, `api/` handles HTTP only (split into `auth`, `resources`, `reports`, `common`), `pdf_reports.py` handles rendering. |
| **Open/Closed** | New report = new `BaseReportStrategy` subclass + one map entry. New API resource = new `ModelResource` subclass. New lifecycle = a `TRANSITIONS` table. Existing code is not edited. |
| **Liskov Substitution** | Any `BaseReportStrategy`, `BaseService` or `ModelResource` subclass can replace its parent; tests swap in subclasses of `InventoryService` and `RequestFulfillmentService`. |
| **Interface Segregation** | Small, focused contracts: `BaseReportStrategy.generate()`, `BaseService.model`, `ModelResource` hooks that subclasses override only when needed. |
| **Dependency Inversion** | `RequestFulfillmentService` receives its `InventoryService` through the constructor; views obtain services from `container.py` (the composition root), so implementations can be replaced without touching views. |

### Security

All API endpoints and pages require a logged-in, active user, and each is limited to the roles allowed to use it (checked on the server, see `api/common.py` and `jeevithaya/views.py`). Write requests are protected by Django's CSRF check.

---

## ⚙️ Quickstart Installation & Setup

### 1. Clone or Open Project

```powershell
cd c:\wamp64\www\Jeevithaya-mit
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Choose Database Mode

#### Option A: SQLite (Instant Setup - No MySQL Required)

```powershell
$env:DB_ENGINE="sqlite"
```

#### Option B: MySQL (Production / WAMP Server)

Ensure MySQL is running on port `3306` with database `jeevithaya_mit` created:

```powershell
$env:DB_ENGINE="mysql"
$env:DB_NAME="jeevithaya_mit"
$env:DB_USER="root"
$env:DB_PASSWORD=""
```

### 4. Run Migrations & Seed Sample Data

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py seed_db
```

### 5. Launch Development Server

```powershell
python manage.py runserver
```

Access the application at: **`http://127.0.0.1:8000/`**

---

## 🔐 Default Demo Accounts

| Role               | Email                        | Password      | Permissions                                         |
| :----------------- | :--------------------------- | :------------ | :-------------------------------------------------- |
| **System Admin**   | `admin@jeevithaya.com`       | `admin123`    | Full access across all modules                      |
| **Hospital Admin** | `hospital@jeevithaya.com`    | `hospital123` | Clinical approvals, patient records & reports       |
| **Front Office**   | `frontoffice@jeevithaya.com` | `front123`    | Donor registration & request submissions            |
| **Lab Assistant**  | `lab@jeevithaya.com`         | `lab123`      | Phlebotomy intake, laboratory screening & inventory |

---

## 🧪 Automated Testing

Run the test suite with:

```powershell
python manage.py test bloodbank
```

---

## 🖥️ Presentation & Deliverables

- 📊 **In-Browser Presentation Deck:** Run the application and open `http://127.0.0.1:8000/presentation.html` (or click **Slides Deck ↗** in the dashboard sidebar).
- 🧪 **Automated Test Suite:** Run `python manage.py test bloodbank` to verify OOP entities, services, and API endpoints.

---

**© Jeevithaya | Group 5 MIT 2025/2026 Batch**

---

---
