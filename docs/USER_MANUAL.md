# Jeevithaya (ජීවිතය) - Centralized Blood & Plasma Management System
## Official User Manual & Operational Handbook
**Course:** Master of Information Technology (MIT)  
**Project Group:** Group 5 (MIT 2025/2026 Batch)  
**Version:** 2.0 (OOP Refactored Edition)  
**Release Date:** November 2026  

---

## 1. Executive Summary & Purpose

**Jeevithaya** is an enterprise-grade, centralized web platform engineered to eliminate operational bottlenecks, reduce transfusion turnaround times, and prevent bio-hazardous waste across hospital networks and blood transfusion centers.

### Core Objectives:
1. **Zero-Waste Cold Chain Tracking:** Real-time monitoring of blood units, batch shelf-life, and expiration alerts.
2. **Strict Serological Safety Gates:** Mandatory multi-marker verification (HIV, Hepatitis B, Hepatitis C, Syphilis) before any unit is released to available inventory.
3. **Role-Based Access Security (RBAC):** Hierarchical separation of duties across administrators, laboratory scientists, and front-office coordinators.
4. **End-to-End Auditability:** Full traceability from initial donor intake session down to transfusion fulfillment or bio-hazardous disposal.

---

## 2. System Architecture & Prerequisites

### 2.1 Technology Stack
* **Backend Application Server:** Python 3.12+ with Django 5.x/6.x Framework
* **Database Management System:** MySQL 8.x (`jeevithaya_db`) / SQLite development mode
* **Frontend Client Layer:** HTML5, CSS3 Grid/Flexbox design, Vanilla JavaScript (ES6+ API client architecture)
* **Design Philosophy:** Modular Object-Oriented Architecture (Encapsulation, Inheritance, Abstraction, Polymorphism)

### 2.2 System Prerequisites
* Web Browser: Google Chrome 100+, Mozilla Firefox 100+, Microsoft Edge 100+
* Network: TCP/IP connection to the Jeevithaya application host (`localhost:8000` or production intranet IP)
* Minimum Display Resolution: 1280 x 720 (Optimized for 1920 x 1080 desktop screens)

---

## 3. Role-Based Access Control (RBAC) Matrix

Jeevithaya implements strict Role-Based Access Control. Each user account is assigned one of four distinct security profiles:

| Module / Screen | System Admin | Hospital Admin | Front Office User | Lab Assistant |
| :--- | :---: | :---: | :---: | :---: |
| **System Dashboard** | Full Access | Full Access | Full Access | Full Access |
| **Donor Management** | Full Access | View Only | View / Register | View Only |
| **Patient Registration** | Full Access | Full Access | View / Register | View Only |
| **Blood Requests** | Full Access | View / Approve | Create / View | View Only |
| **Inventory Cold-Chain** | Full Access | View Only | No Access | Manage / Update |
| **Donation Intake** | Full Access | View Only | View Only | Register / Intake |
| **Testing & Verification**| Full Access | View Only | No Access | Conduct & Record |
| **Disposal Management** | Full Access | View Only | No Access | Execute Disposal |
| **Analytical Reports** | Full Access | Full Access | No Access | No Access |
| **User Administration** | Full Access | No Access | No Access | No Access |
| **Profile Settings** | Self Edit | Self Edit | Self Edit | Self Edit |

---

## 4. Module-by-Module User Guide

### 4.1 System Login & Authentication
1. Navigate to the login portal at `http://127.0.0.1:8000/login.html`.
2. Select your designated role radio button:
   * **System Admin**
   * **Hospital Admin**
   * **Front Office**
   * **Lab Assistant**
3. Enter your institutional **Email** and **Password**.
4. *(Optional)* Select **Remember Me** to persist your session across browser tabs.
5. Click **Sign In**. On successful authentication, the system validates your role and routes you directly to the **Dashboard**.

> [!NOTE]
> For evaluation and training purposes, default demo credentials are provided:
> * System Admin: `admin@jeevithaya.com` / `admin123`
> * Hospital Admin: `hospital@jeevithaya.com` / `hospital123`
> * Front Office: `frontoffice@jeevithaya.com` / `front123`
> * Lab Assistant: `lab@jeevithaya.com` / `lab123`

---

### 4.2 Executive Dashboard (`dashboard.html`)
The dashboard is the central control hub providing operational metrics:
* **Metric Cards:**
  * **Total Registered Donors:** Real-time count of active donors.
  * **Active Blood Requests:** Count of pending and approved requisitions.
  * **Available Inventory Units:** Total usable, verified blood and plasma units in stock.
  * **Critical Emergency Requests:** Urgent transfusions requiring prioritized attention.
* **Recent Requisitions Table:** Real-time log of the latest 5 patient transfusion orders, including Blood Group, Component Type, Quantity, and status badges.
* **Auto-Refresh:** Dashboard data refreshes automatically every 30 seconds.

---

### 4.3 Donor Management (`donors.html`)
**Primary Role:** Front Office, System Admin  
Enables registration and eligibility tracking of voluntary and replacement blood donors.

#### Registering a New Donor:
1. Locate the **Register New Donor** card at the top.
2. Enter the donor's **Full Name**, **Contact Number** (e.g. `0771234567`), and choose their **Blood Group** (`O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`).
3. Set their **Eligibility Status** (default is `Eligible`).
4. Optionally provide their **Email** and **Gender**.
5. Click **Register Donor**.
6. The record is validated and immediately rendered into the Donor Table.

#### Filtering and Searching:
* **Blood Group Filter:** Select a specific blood group from the dropdown to isolate matching donors for emergency drives.
* **Eligibility Filter:** Filter by `Eligible` or `Not Eligible`.
* **Instant Search:** Enter donor name, phone number, or Donor ID to filter results in real time.

---

### 4.4 Patient Registration (`patients.html`)
**Primary Role:** Front Office, Hospital Admin, System Admin  
Registers in-patients and emergency ward cases requiring blood transfusion therapy.

#### Registration Steps:
1. Enter the assigned **Hospital ID** and patient **Full Name**.
2. Select **Gender**, enter **Age** or **Date of Birth**, and enter patient/guardian **Contact Number**.
3. Select the required **Blood Group**, **Component Type** (`Blood` or `Plasma`), and **Urgency** level:
   * **Normal:** Routine surgery / elective transfusion.
   * **Urgent:** Schedule within 24 hours.
   * **Critical:** Immediate life-saving transfusion requirement.
4. Click **Save Patient**.

---

### 4.5 Blood Requests & Fulfillment (`requests.html`)
**Primary Role:** Front Office (Creation), Hospital Admin (Approval), System Admin  
Manages requisition orders submitted by hospital operating theaters and clinical wards.

#### Creating a Requisition:
1. Provide the **Patient ID** (e.g., `P101`) and submitting **Hospital ID**.
2. Select **Component Type**, **Blood Group**, and requested **Quantity** (units).
3. Set **Urgency Level** (`Normal`, `Urgent`, `Critical`).
4. Choose initial status (`Pending`).
5. Click **Submit Request**.

#### Requisition State Transitions:
* **Pending:** Awaiting blood bank hospital administrator review.
* **Approved:** Clinically authorized; queued for cross-matching and laboratory dispatch.
* **Fulfilled:** Units successfully allocated and issued from inventory.
* **Rejected:** Denied due to clinical counter-indications or unverified requisition.

---

### 4.6 Inventory & Cold Chain Tracking (`inventory.html`)
**Primary Role:** Lab Assistant, System Admin  
Tracks physical blood bags, expiration dates, refrigeration storage, and availability.

#### Adding a Verified Stock Unit:
1. Enter associated **Donation ID** and **Donor ID**.
2. Enter **Blood Bank Center ID** and select **Blood Group** and **Component Type**.
3. Specify **Quantity** and manufacturer **Batch Number** (e.g., `B-105`).
4. Enter the cold-chain **Expiry Date** (system automatically defaults to 30 days from entry).
5. Select status: `Available`, `Reserved`, or `Issued`.
6. Click **Add Unit**.

#### Expiration Warning System:
* Units past their cold-chain expiry date are automatically marked with red styling (`row-expired`) and status `Expired`.
* Expired units are locked from reservation and cannot be issued to patients.

---

### 4.7 Donation Intake (`donation.html`)
**Primary Role:** Lab Assistant, System Admin  
Records voluntary blood and plasma donations during mobile donation drives or blood bank center appointments.

1. Specify **Donor ID** (must correspond to an eligible registered donor).
2. Record **Donation Date**, **Blood Group**, and **Component Type**.
3. Record volume **Quantity** (units) and the **Supervising Officer / Doctor**.
4. Click **Record Donation**.

---

### 4.8 Testing & Laboratory Verification (`verification.html`)
**Primary Role:** Lab Assistant, System Admin  
The quality control safety firewall. Every collected blood unit must undergo serological testing.

#### Verification Procedure:
1. Enter target **Unit ID** and originating **Donor ID**.
2. Record the **Testing Officer Name** and **Date**.
3. Record screening outcomes for mandatory markers:
   * **HIV Screening** (`Passed` / `Failed`)
   * **Hepatitis B Surface Antigen** (`Passed` / `Failed`)
   * **Hepatitis C Virus** (`Passed` / `Failed`)
   * **Syphilis / VDRL** (`Passed` / `Failed`)
4. Set **Overall Result** (`Passed` or `Failed`).
5. Click **Record Verification**.

> [!IMPORTANT]
> **Automated Safety Trigger:** When a verification record is saved as `Passed`, the inventory unit is unlocked and marked `Available`. If marked `Failed`, the unit is quarantined, flagged as contaminated, and an automatic bio-hazardous `Disposal` record is triggered.

---

### 4.9 Bio-Hazardous Waste Disposal (`disposal.html`)
**Primary Role:** Lab Assistant, System Admin  
Maintains statutory compliance records for incinerated or bio-neutralized blood units.

1. Enter target **Unit ID** and identifying reference numbers.
2. Select statutory **Disposal Reason**:
   * `Expired` (past viable transfusion window)
   * `Contaminated` (serological marker positive)
   * `Damaged` (bag puncture or refrigeration break)
   * `Failed Verification`
3. Enter authorized **Disposing Officer** name and date.
4. Click **Record Disposal**.

---

### 4.10 Analytical Reports & Audits (`reports.html`)
**Primary Role:** Hospital Admin, System Admin  
Provides operational intelligence and management visibility over blood reserves.

* **Reporting Horizons:** Filter analytics by `Last 7 Days`, `Last 30 Days`, `Last 90 Days`, or `All Time`.
* **Summary KPI Cards:**
  * Active Donors, Registered Patients, Cumulative Requests, Units in Cold Chain, Expired Stock Count, Completed Verifications, Executed Disposals.
* **Distribution Charts & Breakdown Tables:**
  * Requests by Status breakdown (Pending, Approved, Fulfilled, Rejected).
  * Inventory Distribution by Blood Group (O+, O-, A+, A-, B+, B-, AB+, AB-).
* **Recent Activity Audit Feed:** Reverse-chronological timeline of transactions.
* **Exporting:** Click **Export Summary** to download a CSV export for external reporting.

---

### 4.11 User Administration (`create_user.html`)
**Primary Role:** System Admin ONLY  
Delegates system privileges and creates user accounts for hospital staff.

1. Enter staff member's **Full Name** and **Institutional Email**.
2. Assign their **System Role** (`System Admin`, `Hospital Admin`, `Front Office User`, `Lab Assistant`).
3. Set temporary account **Password**.
4. Click **Create User**.
5. The account is created with encrypted credentials and becomes active immediately.

---

## 5. Security Best Practices & Troubleshooting

### Security Safeguards
* **Session Expiry:** Sessions timeout on inactivity. Always click **Logout** when leaving a terminal.
* **Encrypted Passwords:** User passwords are encrypted using PBKDF2 with SHA-256 password hashing.
* **Access Violations:** Attempting to directly load unauthorized URLs triggers immediate RBAC redirection.

### Frequently Asked Questions (FAQ)

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Session not found / Please login"** | Local authentication expired or browser storage was cleared. | Return to `login.html` and re-authenticate. |
| **"Unit is Expired" warning** | The unit's expiry date has passed current system date. | Unit cannot be issued; transfer unit to `disposal.html`. |
| **"Access Denied" on Create User** | Current logged-in user is not a System Admin. | Log out and sign in with a System Admin account. |
| **Backend Offline Warning in Console** | Django development server is not running. | Run `python manage.py runserver` from project directory. |

---

**© Jeevithaya | Group 5 MIT 2025/2026 Batch | All Rights Reserved.**
