# Presentation Deck & Speaker Script: Jeevithaya Blood Bank Management System
**Course:** Master of Information Technology (MIT) - 2025/2026 Batch  
**Project:** Jeevithaya (Centralized Blood & Plasma Management System)  
**Team:** Group 5  
**Total Estimated Presentation Time:** 15 – 20 Minutes (approx. 3-4 minutes per member)  

---

## Team Division & Agenda Overview

| Member | Focus Area | Slides Covered | Time Allocation |
| :--- | :--- | :---: | :---: |
| **Member 1** | Introduction, Problem Statement, Objectives & Scope | Slides 1 – 3 | 3.5 mins |
| **Member 2** | System Architecture, Tech Stack & Database Schema | Slides 4 – 6 | 4.0 mins |
| **Member 3** | Object-Oriented Programming (OOP) Implementation | Slides 7 – 9 | 4.0 mins |
| **Member 4** | Core Modules & Live Workflow Walkthrough | Slides 10 – 12 | 4.5 mins |
| **Member 5** | Security (RBAC), Testing, Challenges & Conclusion | Slides 13 – 15 | 3.5 mins |

---

## Slide 1: Title & Team Introduction (Member 1)
* **Title:** Jeevithaya (ජීවිතය) — Centralized Blood & Plasma Management System
* **Subtitle:** An Enterprise Solution for Cold-Chain Integrity, Quality Control, and Rapid Transfusion Logistics
* **Presenter:** Member 1 (Introduction & Project Scope)
* **Visuals:** Project Logo, Group 5 MIT Batch details, Date & University Crest

> **Speaker Notes (Member 1):**  
> *"Good morning respected lecturers and colleagues. On behalf of Group 5 of the MIT batch, I am proud to present our project: **Jeevithaya**—a comprehensive, centralized blood and plasma management system. In critical emergency medicine, minutes matter. Our mission with Jeevithaya is to connect donors, blood banks, laboratories, and hospital wards on a unified, high-reliability platform that prevents wastage and saves lives."*

---

## Slide 2: Problem Statement & Motivation (Member 1)
* **Key Challenges in Current Blood Bank Operations:**
  * **Siloed Paper Records:** Inability to locate rare blood types across affiliated hospital centers quickly.
  * **Cold-Chain Spoilage:** Manual shelf-life tracking causes usable blood units to expire on the shelf.
  * **Transfusion Safety Risks:** High risk of clerical error when recording multi-marker serological tests (HIV, Hepatitis).
  * **Delayed Transfusions:** Lack of real-time communication between surgery theaters and blood storage banks.

> **Speaker Notes (Member 1):**  
> *"Blood is a perishable, highly sensitive therapeutic resource. Traditional manual or fragmented blood bank records suffer from three fatal flaws: high wastage rates due to missed expiry dates, communication delays between emergency rooms and blood banks, and the ever-present danger of contaminated blood entering circulation. Jeevithaya was engineered specifically to solve these four critical bottlenecks through software automation and strict digital checkpoints."*

---

## Slide 3: Project Objectives & Scope (Member 1)
* **Core Project Goals:**
  * Establish a single centralized repository for donors, patients, stock, and requisitions.
  * Automate cold-chain shelf-life monitoring with proactive expiration alerts.
  * Enforce non-negotiable laboratory verification before unit release.
  * Implement strict Role-Based Access Control (RBAC) across hospital hierarchies.
  * Provide real-time operational analytics for management decision-making.

> **Speaker Notes (Member 1):**  
> *"Our scope covers the full blood supply chain: donor recruitment and registration, intake phlebotomy sessions, laboratory serological testing, cold-storage inventory tracking, surgical ward requisition fulfillment, bio-hazardous waste disposal, and executive auditing. I will now hand over to Member 2 to walk you through our system architecture and database design."*

---

## Slide 4: System Architecture & Tech Stack (Member 2)
* **Tiered Architecture:**
  * **Presentation Tier:** Clean HTML5, Responsive CSS Grid, Vanilla JS API Client.
  * **Application Tier:** Python Django Framework with decoupled REST API endpoints.
  * **Data Tier:** Relational Database (MySQL 8.x in production / SQLite for isolated development).
* **Communication Model:** Asynchronous JSON REST API over HTTP/HTTPS with unified error handling and cross-environment database fallback.

> **Speaker Notes (Member 2):**  
> *"Thank you, Member 1. To ensure high availability and responsiveness in critical healthcare environments, we implemented a decoupled tiered architecture. Our presentation layer communicates asynchronously with the Django backend via RESTful JSON endpoints. We selected Django for its proven robustness, built-in ORM security, session management, and scalability. On the database level, we run MySQL for production with an automated fallback to SQLite for local staging and isolated unit testing."*

---

## Slide 5: Database Design & Entity Relationships (Member 2)
* **Key Entities & Relational Modeling:**
  * `User`: System accounts with role choices (`system_admin`, `hospital_admin`, etc.).
  * `Donor` & `Patient`: Demographic, contact, and blood group records.
  * `Donation`: Intake sessions linked to donors and blood banks.
  * `Verification`: Quality control records storing HIV, Hepatitis B/C, and Syphilis outcomes.
  * `Inventory`: Cold-chain tracking with batch numbers, expiry dates, and statuses (`Available`, `Reserved`, `Issued`, `Expired`).
  * `BloodRequest`: Patient requisitions categorized by urgency (`Normal`, `Urgent`, `Critical`).
  * `Disposal`: Bio-hazardous waste destruction audit logs.

> **Speaker Notes (Member 2):**  
> *"Our database schema is normalized to 3NF to avoid redundancy. Crucially, we designed the schema to reflect real-world clinical relationships: a Donor gives a Donation, which yields an Inventory Unit. That Unit cannot enter the Available pool without a successful Verification record. If it fails or expires, it transitions into the Disposal log. This maintains end-to-end relational integrity."*

---

## Slide 6: API Layer & Full-Stack Integration (Member 2)
* **Decoupled API Architecture:**
  * Standardized `/api/` endpoints: `/api/donors/`, `/api/inventory/`, `/api/requests/`, etc.
  * **Payload Normalization:** Custom backend serializer handling both camelCase (client JS) and PascalCase (Django ORM).
  * **Zero-Breaking Fallback:** Client-side local storage fallback ensuring the UI remains operable during network disconnects or offline drills.

> **Speaker Notes (Member 2):**  
> *"A key highlight of our integration is resilience. In healthcare, a dropped network packet cannot crash a nurse's terminal. We developed an intelligent payload normalizer on the Django backend that accepts multi-format inputs, paired with an offline storage fallback on the client side. Now, Member 3 will explain how we modeled this system using core Object-Oriented Programming concepts."*

---

## Slide 7: OOP in Jeevithaya: Abstraction & Inheritance (Member 3)
* **OOP Pillar 1: Abstraction**
  * `BaseAuditableEntity`: Abstract model encapsulating `CreatedAt` and `UpdatedAt` timestamps.
  * `BaseService`: Abstract interface defining uniform data-access contracts across domain services.
* **OOP Pillar 2: Inheritance**
  * `BasePerson`: Abstract parent class containing shared demographic properties (`Name`, `BloodGroup`, `Gender`, `DateOfBirth`, `Address`).
  * `Donor` and `Patient` inherit directly from `BasePerson`, eliminating code duplication and enforcing consistent validation.

> **Speaker Notes (Member 3):**  
> *"Thank you, Member 2. As an MIT assignment, one of our primary design goals was demonstrating software engineering rigor through Object-Oriented Programming. We implemented abstract models to avoid repetition. `BasePerson` abstracts all common attributes of human actors in the system. `Donor` and `Patient` inherit from `BasePerson`, gaining shared methods like dynamic age calculation while adding their own specialized properties."*

---

## Slide 8: OOP in Jeevithaya: Encapsulation (Member 3)
* **Encapsulating Business Logic within Entity Models:**
  * `User.set_password()` and `User.check_password()`: Password hashing encapsulated inside the User entity.
  * `Inventory.is_expired()` & `Inventory.days_until_expiry()`: Shelf-life logic self-contained within the Inventory unit.
  * `Verification.is_safe()`: Encapsulated serological rule verifying that all tests passed.
  * `BloodRequest.approve()`, `fulfill()`, `reject()`: Encapsulated state machines protecting entity state transitions.

> **Speaker Notes (Member 3):**  
> *"Instead of writing 'anemic domain models' where logic is scattered across raw views, we followed strict Encapsulation. An Inventory object knows how to check its own expiry date. A Verification object knows whether its serological markers are safe. A BloodRequest encapsulates its own state transitions. This prevents invalid states and makes our codebase maintainable and testable."*

---

## Slide 9: OOP in Jeevithaya: Polymorphism & Strategy Pattern (Member 3)
* **Polymorphism via Analytical Report Strategies:**
  * `BaseReportStrategy`: Abstract interface declaring the `generate(days)` method.
  * Concrete polymorphic implementations:
    * `InventoryReportStrategy`: Computes blood group distribution and expired stock.
    * `DonationReportStrategy`: Analyzes donor intake trends over time.
    * `RequestReportStrategy`: Evaluates hospital requisition demand and critical urgent rates.
  * `AnalyticsContext`: Polymorphically executes any strategy interchangeably at runtime.

> **Speaker Notes (Member 3):**  
> *"To demonstrate Polymorphism, we implemented the Strategy Design Pattern for our reporting module. `AnalyticsContext` can execute an `InventoryReportStrategy`, a `DonationReportStrategy`, or a `RequestReportStrategy` through a single unified `generate()` method. This makes adding new reports in the future as simple as adding a new class without modifying existing reporting pipelines. I will now hand over to Member 4 for the live workflow walkthrough."*

---

## Slide 10: Core Workflows: Donor Intake to Verification (Member 4)
* **The Clinical Pipeline (Part 1):**
  1. **Donor Registration:** Front office records voluntary donor into the system.
  2. **Intake Phlebotomy Session:** Blood collection session recorded with component type and quantity.
  3. **Laboratory Safety Gate:** Lab assistant runs HIV, Hep B, Hep C, and Syphilis tests.
  4. **Automated Status Update:** 
     * If `Passed` $\rightarrow$ Unit status set to `Available` in Inventory.
     * If `Failed` $\rightarrow$ Unit quarantined and automatically routed to `Disposal`.

> **Speaker Notes (Member 4):**  
> *"Thank you, Member 3. Let us now examine how these concepts translate into real hospital workflows. Everything starts with the donor. Once blood is collected, our system enforces a mandatory quality gate. Notice on the slide: until the laboratory records a 'Passed' verification across all four infectious disease markers, the unit is physically and digitally locked. It cannot be seen or reserved by hospital staff. If a sample fails, our service layer automatically logs a disposal order."*

---

## Slide 11: Core Workflows: Requisition & Smart Fulfillment (Member 4)
* **The Clinical Pipeline (Part 2):**
  1. **Requisition Submission:** Operating theater submits request with urgency rating (`Critical`, `Urgent`, `Normal`).
  2. **Administrative Clinical Review:** Hospital Admin reviews and approves the clinical need.
  3. **Inventory Auto-Allocation:** System checks verified available units matching blood group and component.
  4. **Issuance & Deduction:** Units transition from `Available` $\rightarrow$ `Issued`, automatically updating stock levels.

> **Speaker Notes (Member 4):**  
> *"When a surgery ward requests blood, the requisition carries an urgency badge. Critical requests appear at the top of the dashboard. Our `RequestFulfillmentService` performs an automated compatibility check. If sufficient stock exists, the system reserves and issues the specific matching batch units, preventing double-allocation and ensuring complete stock traceability."*

---

## Slide 12: Real-Time Operational Analytics (Member 4)
* **Management Visibility & Compliance:**
  * Filterable KPI Dashboards (7, 30, 90 days, All time).
  * Breakdown of stock by all 8 blood groups (O+, O-, A+, A-, B+, B-, AB+, AB-).
  * Real-time activity audit timeline logging every user transaction.
  * One-click CSV Export for statutory health authority reporting.

> **Speaker Notes (Member 4):**  
> *"The Reports module gives blood bank directors immediate visibility. At a glance, they can see current reserves broken down by blood type, track expiring units before they spoil, and monitor request fulfillment rates. The audit feed records every action, ensuring medical accountability. Member 5 will now discuss our security implementation, testing, and conclusion."*

---

## Slide 13: Security Architecture & RBAC (Member 5)
* **Multi-Layered Security:**
  * **Role-Based Access Control (RBAC):** Dynamic interface filtering and server-side role validation for 4 profiles (`System Admin`, `Hospital Admin`, `Front Office`, `Lab Assistant`).
  * **Cryptographic Password Hashing:** PBKDF2 with SHA-256 password encryption with zero plaintext storage.
  * **Session Security:** Server-backed Django session middleware with automated cleanup on logout.
  * **CSRF & Injection Defenses:** Parameterized ORM queries eliminating SQL injection vectors.

> **Speaker Notes (Member 5):**  
> *"Thank you, Member 4. In healthcare informatics, confidentiality and role boundaries are paramount. A front-office clerk must not be able to alter laboratory test results, and a lab technician should not have administrative user-creation privileges. We implemented a dual-layer RBAC system: dynamic client-side menu trimming for usability, backed by server-side role enforcement. Passwords are encrypted with industry-standard PBKDF2-SHA256, and all database interactions use Django's parameterized ORM, protecting against SQL injection."*

---

## Slide 14: Verification, Testing & Challenges Overcome (Member 5)
* **Quality Assurance & Engineering Challenges:**
  * **Challenge 1:** Reconciling asynchronous client JavaScript with Django's backend REST APIs $\rightarrow$ *Resolved with unified fetch client and key normalizer.*
  * **Challenge 2:** Supporting development environments without active MySQL servers $\rightarrow$ *Resolved with dual-engine configuration (MySQL/SQLite).*
  * **Challenge 3:** Role naming mismatches between database tokens and UI display titles $\rightarrow$ *Resolved through case/space-agnostic string normalization.*
  * **Testing Strategy:** API endpoint tests, boundary tests on blood quantities (1-10 units), and authentication validation.

> **Speaker Notes (Member 5):**  
> *"During our development cycle, our biggest engineering hurdle was bridging the client-side single-page interactivity with the server-side Django ORM without introducing tight coupling. By standardizing our API contracts, building an intelligent normalizer for payload casing, and supporting seamless fallback between MySQL and SQLite, we achieved a resilient, maintainable system ready for hospital staging."*

---

## Slide 15: Conclusion & Future Enhancements (Member 5)
* **Summary of Achievements:**
  * Delivered a fully functional, centralized Blood & Plasma Management System.
  * Successfully applied all 4 OOP principles (Abstraction, Inheritance, Encapsulation, Polymorphism).
  * Created complete user documentation and full operational auditability.
* **Future Roadmap:**
  * Automated SMS/Email donor recall notifications when stock runs low.
  * IoT temperature sensor integration for cold-chain refrigeration units.
  * Mobile donor application for appointment scheduling.
* **Q&A Session:** *We welcome your questions!*

> **Speaker Notes (Member 5):**  
> *"To conclude, Jeevithaya represents our team's commitment to solving real-world healthcare challenges using solid software engineering and Object-Oriented principles. We have met all academic criteria, implemented end-to-end workflows, and built a system ready for real-world extension. On behalf of Group 5, thank you for your time, and we now welcome any questions from the panel."*
