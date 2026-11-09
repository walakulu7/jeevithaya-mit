# Jeevithaya System Design & UML Architecture Diagrams
**Course:** Master of Information Technology (MIT)  
**Project:** Centralized Blood & Plasma Management System  
**Team:** Group 5 (MIT 2025/2026 Batch)  

---

## 1. Object-Oriented Class Diagram (UML)

This diagram illustrates the **OOP Inheritance Hierarchy**, **Abstract Classes**, and **Domain Services** across the application.

```mermaid
classDiagram
    %% Abstract Base Classes
    class BaseAuditableEntity {
        <<Abstract>>
        +DateTimeField CreatedAt
        +DateTimeField UpdatedAt
    }

    class BasePerson {
        <<Abstract>>
        +CharField Name
        +CharField BloodGroup
        +CharField Gender
        +DateField DateOfBirth
        +TextField Address
        +calculate_age() int
    }

    class BaseService {
        <<Interface>>
        +get_all()* QuerySet
    }

    class BaseReportStrategy {
        <<Interface>>
        +generate(days)* dict
    }

    %% Inheritance Relationships
    BaseAuditableEntity <|-- BasePerson
    BasePerson <|-- Donor
    BasePerson <|-- Patient
    BaseAuditableEntity <|-- BloodRequest
    BaseAuditableEntity <|-- Inventory

    BaseService <|-- InventoryService
    BaseService <|-- RequestFulfillmentService

    BaseReportStrategy <|-- InventoryReportStrategy
    BaseReportStrategy <|-- DonationReportStrategy
    BaseReportStrategy <|-- RequestReportStrategy

    %% Concrete Entities
    class Donor {
        +CharField DonorID [PK]
        +CharField Phone
        +CharField Status
        +EmailField Email
        +is_eligible() bool
        +toggle_eligibility(bool)
    }

    class Patient {
        +CharField PatientID [PK]
        +IntegerField HospitalID
        +CharField Type
        +CharField Urgency
        +CharField Contact
        +IntegerField Age
        +is_critical() bool
    }

    class Inventory {
        +CharField UnitID [PK]
        +CharField DonationID
        +CharField DonorID
        +IntegerField BloodBankID
        +CharField BloodGroup
        +CharField Type
        +IntegerField Quantity
        +CharField BatchNo
        +DateField ExpiryDate
        +CharField Status
        +is_expired() bool
        +days_until_expiry() int
        +mark_reserved()
        +mark_issued()
    }

    class BloodRequest {
        +CharField RequestID [PK]
        +CharField PatientID
        +IntegerField HospitalID
        +DateField RequestDate
        +CharField BloodGroup
        +CharField Type
        +IntegerField Quantity
        +CharField Urgency
        +CharField Status
        +approve()
        +fulfill()
        +reject()
    }

    class Verification {
        +CharField VerificationID [PK]
        +CharField UnitID
        +CharField DonorID
        +CharField VerifiedBy
        +DateField Date
        +CharField HIV
        +CharField HepatitisB
        +CharField HepatitisC
        +CharField Syphilis
        +CharField OverallResult
        +is_safe() bool
    }

    class User {
        +AutoField UserID [PK]
        +CharField Name
        +EmailField Email
        +CharField Password
        +CharField Role
        +set_password(raw_password)
        +check_password(raw_password) bool
        +has_role(*roles) bool
    }

    %% Context Execution
    class AnalyticsContext {
        -BaseReportStrategy _strategy
        +set_strategy(strategy)
        +execute(days) dict
    }

    AnalyticsContext o-- BaseReportStrategy
```

---

## 2. Entity-Relationship Diagram (ERD)

This diagram visualizes the **Physical Database Schema** and relational associations.

```mermaid
erDiagram
    User ||--o{ Hospital_Admin : manages
    Donor ||--o{ Donation : gives
    Donation ||--|| Inventory : yields
    Inventory ||--|| Verification : screened_by
    Inventory ||--o| Disposal : condemned_to
    Patient ||--o{ BloodRequest : needs
    Hospital_Admin ||--o{ BloodRequest : authorizes

    User {
        int UserID PK
        string Name
        string Email
        string Password
        string Role
        int HospitalID
        string ContactNo
        datetime CreatedAt
    }

    Donor {
        string DonorID PK
        string Name
        string BloodGroup
        string Phone
        string Status
        string Email
        date DateOfBirth
        string Gender
        text Address
        datetime CreatedAt
        datetime UpdatedAt
    }

    Patient {
        string PatientID PK
        string Name
        int HospitalID
        string BloodGroup
        string Type
        string Urgency
        string Contact
        int Age
        date DateOfBirth
        datetime CreatedAt
        datetime UpdatedAt
    }

    Donation {
        string DonationID PK
        string DonorID FK
        date Date
        string BloodGroup
        string Type
        int Quantity
        int BloodBankID
        string Status
        datetime CreatedAt
    }

    Inventory {
        string UnitID PK
        string DonationID FK
        string DonorID FK
        int BloodBankID
        string BloodGroup
        string Type
        int Quantity
        string BatchNo
        date ExpiryDate
        string Status
        datetime CreatedAt
        datetime UpdatedAt
    }

    Verification {
        string VerificationID PK
        string UnitID FK
        string DonorID FK
        string VerifiedBy
        date Date
        string HIV
        string HepatitisB
        string HepatitisC
        string Syphilis
        string OverallResult
        text Notes
        datetime CreatedAt
    }

    BloodRequest {
        string RequestID PK
        string PatientID FK
        int HospitalID
        date RequestDate
        string BloodGroup
        string Type
        int Quantity
        string Urgency
        string Status
        datetime CreatedAt
        datetime UpdatedAt
    }

    Disposal {
        string DisposalID PK
        string UnitID FK
        date DisposalDate
        string Reason
        string DisposedBy
        text Notes
        datetime CreatedAt
    }
```

---

## 3. Clinical Workflow Sequence Diagram

### 3.1 Blood Intake, Testing, and Inventory Release
Traces how a physical blood bag moves through laboratory screening to available stock:

```mermaid
sequenceDiagram
    autonumber
    actor Donor as Voluntary Donor
    actor Lab as Lab Assistant / Phlebotomist
    participant Sys as Jeevithaya Web Portal
    participant DB as Relational Database
    participant Service as InventoryService

    Donor->>Lab: Presents for donation session
    Lab->>Sys: Submits Donation Intake (DonationID, DonorID, BloodGroup)
    Sys->>DB: Saves Donation Record (Status='Pending')
    
    Note over Lab,Sys: Laboratory Serological Testing Phase
    Lab->>Sys: Submits Serological Screening (HIV, Hep B/C, Syphilis)
    
    alt All Tests Passed
        Sys->>Service: process_verification_result(Passed)
        Service->>DB: Updates Unit Status to 'Available' in Inventory
        Sys-->>Lab: Confirmation: "Unit Released to Cold Chain Stock"
    else Any Test Failed
        Sys->>Service: process_verification_result(Failed)
        Service->>DB: Updates Unit Status to 'Expired' / Quarantined
        Service->>DB: Automatically logs Bio-Waste Disposal record
        Sys-->>Lab: Warning: "Unit Contaminated - Auto-Logged for Incineration"
    end
```

---

### 3.2 Transfusion Requisition & Smart Stock Deduction
Traces an emergency hospital request being matched and fulfilled from stock:

```mermaid
sequenceDiagram
    autonumber
    actor Ward as Surgery Ward / Front Office
    actor Admin as Hospital Administrator
    participant Sys as Jeevithaya Web Portal
    participant Fulfill as RequestFulfillmentService
    participant DB as Relational Database

    Ward->>Sys: Submits Blood Requisition (PatientID, BloodGroup, Urgency='Critical')
    Sys->>DB: Saves Request (Status='Pending')
    
    Admin->>Sys: Reviews clinical justification and clicks 'Approve'
    Sys->>DB: Updates Request (Status='Approved')
    
    Admin->>Sys: Clicks 'Fulfill Request'
    Sys->>Fulfill: fulfill_request(RequestID)
    Fulfill->>DB: Query non-expired 'Available' units matching BloodGroup & Type
    
    alt Stock Available
        Fulfill->>DB: Mark matched units as 'Issued'
        Fulfill->>DB: Mark Request as 'Fulfilled'
        Sys-->>Admin: Success: "Units Dispatched to Ward"
    else Stock Depleted
        Sys-->>Admin: Alert: "Insufficient stock. Emergency donor recall recommended"
    end
```
