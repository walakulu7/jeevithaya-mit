from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.hashers import make_password, check_password
from datetime import date


# ==============================================================================
# OOP PILLAR 1 & 2: ABSTRACTION & INHERITANCE (Abstract Base Models)
# ==============================================================================

class BaseAuditableEntity(models.Model):
    """
    Abstract base entity encapsulating audit timestamps.
    Demonstrates Abstraction and Inheritance across all domain models.
    """
    CreatedAt = models.DateTimeField(auto_now_add=True)
    UpdatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BasePerson(BaseAuditableEntity):
    """
    Abstract base class representing common demographic and contact attributes
    shared by Donors and Patients. Demonstrates OOP Inheritance.
    """
    BLOOD_GROUP_CHOICES = [
        ('O+', 'O+'), ('O-', 'O-'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]

    Name = models.CharField(max_length=100, null=False)
    BloodGroup = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)
    Gender = models.CharField(max_length=10, null=True, blank=True)
    DateOfBirth = models.DateField(null=True, blank=True)
    Address = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True

    # Encapsulated Business Logic
    @property
    def calculate_age(self):
        """Encapsulated method to calculate age dynamically from DateOfBirth."""
        if not self.DateOfBirth:
            return None
        today = date.today()
        return today.year - self.DateOfBirth.year - (
            (today.month, today.day) < (self.DateOfBirth.month, self.DateOfBirth.day)
        )


# ==============================================================================
# USER MANAGEMENT ENTITIES (Encapsulation of Authentication & Roles)
# ==============================================================================

class System_Admin(models.Model):
    AdminID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100, null=False)
    Role = models.CharField(max_length=50, null=True, blank=True)
    ContactNo = models.CharField(max_length=15, null=True, blank=True)
    Email = models.EmailField(max_length=100, unique=True)
    Password = models.CharField(max_length=255)
    Permissions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'System_Admin'
        verbose_name = 'System Admin'
        verbose_name_plural = 'System Admins'

    def __str__(self):
        return f"{self.Name} ({self.Email})"


class Hospital_Admin(models.Model):
    HospitalAdminID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100, null=False)
    HospitalID = models.IntegerField(null=False)
    ContactNo = models.CharField(max_length=15, null=True, blank=True)
    Email = models.EmailField(max_length=100, unique=True)
    Password = models.CharField(max_length=255)

    class Meta:
        db_table = 'Hospital_Admin'
        verbose_name = 'Hospital Admin'
        verbose_name_plural = 'Hospital Admins'

    def __str__(self):
        return f"{self.Name} ({self.Email})"


class User(models.Model):
    ROLE_CHOICES = [
        ('system_admin', 'System Admin'),
        ('hospital_admin', 'Hospital Admin'),
        ('frontoffice_user', 'Front Office User'),
        ('lab_assistant', 'Lab Assistant'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    UserID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100, null=False)
    Email = models.EmailField(max_length=100, unique=True)
    Password = models.CharField(max_length=255)
    Role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    HospitalID = models.IntegerField(null=True, blank=True)
    ContactNo = models.CharField(max_length=15, null=True, blank=True)
    CreatedAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'User'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.Name} ({self.Email}) - {self.get_role_display()}"

    # Encapsulation: Password Security
    def set_password(self, raw_password):
        """Hashes and sets the user's password securely."""
        self.Password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifies candidate password with backward-compatible plain check."""
        try:
            if check_password(raw_password, self.Password):
                return True
        except Exception:
            pass
        if self.Password == raw_password:
            # Upgrade legacy plaintext to secure hash on match
            self.set_password(raw_password)
            self.save()
            return True
        return False

    # Encapsulation: Role Checking
    def has_role(self, *roles):
        """Returns True if the user possesses any of the specified roles."""
        return self.Role in roles or self.Role.replace('_', ' ').title() in roles


# ==============================================================================
# DONOR & PATIENT ENTITIES (Subclasses of BasePerson)
# ==============================================================================

class Donor(BasePerson):
    """
    Donor entity inheriting from BasePerson.
    Encapsulates eligibility assessment and donor contact details.
    """
    STATUS_CHOICES = [
        ('Eligible', 'Eligible'),
        ('Not Eligible', 'Not Eligible'),
    ]

    DonorID = models.CharField(max_length=20, primary_key=True)
    Phone = models.CharField(max_length=15)
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Eligible')
    Email = models.EmailField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'Donor'
        verbose_name = 'Donor'
        verbose_name_plural = 'Donors'

    def __str__(self):
        return f"{self.DonorID} - {self.Name} ({self.BloodGroup})"

    def is_eligible(self):
        """Check if donor is currently eligible for donation."""
        return self.Status == 'Eligible'

    def toggle_eligibility(self, eligible=True):
        """Set donor status."""
        self.Status = 'Eligible' if eligible else 'Not Eligible'
        self.save()


class Patient(BasePerson):
    """
    Patient entity inheriting from BasePerson.
    Encapsulates patient medical requirements and hospital tracking.
    """
    TYPE_CHOICES = [
        ('Blood', 'Blood'),
        ('Plasma', 'Plasma'),
    ]

    URGENCY_CHOICES = [
        ('Normal', 'Normal'),
        ('Urgent', 'Urgent'),
        ('Critical', 'Critical'),
    ]

    PatientID = models.CharField(max_length=20, primary_key=True)
    HospitalID = models.IntegerField(null=False)
    Type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    Urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    Contact = models.CharField(max_length=15)
    Age = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(120)])

    class Meta:
        db_table = 'Patient'
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return f"{self.PatientID} - {self.Name} ({self.BloodGroup})"

    def is_critical(self):
        """Check if patient requires immediate critical intervention."""
        return self.Urgency in ['Urgent', 'Critical']


# ==============================================================================
# TRANSACTIONAL & LOGISTICAL ENTITIES
# ==============================================================================

class BloodRequest(BaseAuditableEntity):
    """
    Represents a hospital transfusion or plasma request.
    Encapsulates status transitions and fulfillment checks.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Fulfilled', 'Fulfilled'),
        ('Rejected', 'Rejected'),
    ]

    URGENCY_CHOICES = [
        ('Normal', 'Normal'),
        ('Urgent', 'Urgent'),
        ('Critical', 'Critical'),
    ]

    TYPE_CHOICES = [
        ('Blood', 'Blood'),
        ('Plasma', 'Plasma'),
    ]

    RequestID = models.CharField(max_length=20, primary_key=True)
    PatientID = models.CharField(max_length=20)
    HospitalID = models.IntegerField()
    RequestDate = models.DateField()
    BloodGroup = models.CharField(max_length=5)
    Type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    Quantity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    Urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    class Meta:
        db_table = 'BloodRequest'
        verbose_name = 'Blood Request'
        verbose_name_plural = 'Blood Requests'

    def __str__(self):
        return f"{self.RequestID} - {self.PatientID} ({self.BloodGroup} x {self.Quantity})"

    def approve(self):
        """Transition request to Approved state."""
        self.Status = 'Approved'
        self.save()

    def fulfill(self):
        """Transition request to Fulfilled state."""
        self.Status = 'Fulfilled'
        self.save()

    def reject(self):
        """Transition request to Rejected state."""
        self.Status = 'Rejected'
        self.save()


class Donation(models.Model):
    """
    Represents an intake donation session from a registered donor.
    """
    BLOOD_GROUP_CHOICES = [
        ('O+', 'O+'), ('O-', 'O-'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]

    DonationID = models.CharField(max_length=20, primary_key=True)
    DonorID = models.CharField(max_length=20)
    Date = models.DateField()
    BloodGroup = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)
    Type = models.CharField(max_length=10, choices=[('Blood', 'Blood'), ('Plasma', 'Plasma')])
    Quantity = models.IntegerField(validators=[MinValueValidator(1)])
    BloodBankID = models.IntegerField()
    Status = models.CharField(max_length=20, default='Pending')
    CreatedAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Donation'
        verbose_name = 'Donation'
        verbose_name_plural = 'Donations'

    def __str__(self):
        return f"{self.DonationID} - Donor:{self.DonorID} ({self.BloodGroup})"


class Inventory(BaseAuditableEntity):
    """
    Represents physical verified blood/plasma units stored in cold chain.
    Encapsulates expiry calculation and state management.
    """
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('Issued', 'Issued'),
        ('Expired', 'Expired'),
    ]

    UnitID = models.CharField(max_length=20, primary_key=True)
    DonationID = models.CharField(max_length=20)
    DonorID = models.CharField(max_length=20)
    BloodBankID = models.IntegerField()
    BloodGroup = models.CharField(max_length=5)
    Type = models.CharField(max_length=10, choices=[('Blood', 'Blood'), ('Plasma', 'Plasma')])
    Quantity = models.IntegerField(validators=[MinValueValidator(1)])
    BatchNo = models.CharField(max_length=50)
    ExpiryDate = models.DateField()
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')

    class Meta:
        db_table = 'Inventory'
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f"{self.UnitID} - {self.BloodGroup} ({self.Status})"

    def is_expired(self):
        """Check if inventory unit is past expiry date."""
        return self.ExpiryDate < date.today()

    def days_until_expiry(self):
        """Calculate days remaining before expiry."""
        delta = self.ExpiryDate - date.today()
        return delta.days

    def mark_reserved(self):
        """Reserve unit for pending hospital dispatch."""
        self.Status = 'Reserved'
        self.save()

    def mark_issued(self):
        """Issue unit to hospital."""
        self.Status = 'Issued'
        self.save()


class Verification(models.Model):
    """
    Quality control & serological testing entity (HIV, Hepatitis B/C, Syphilis).
    """
    RESULT_CHOICES = [
        ('Passed', 'Passed'),
        ('Failed', 'Failed'),
    ]

    VerificationID = models.CharField(max_length=20, primary_key=True)
    UnitID = models.CharField(max_length=20)
    DonorID = models.CharField(max_length=20)
    VerifiedBy = models.CharField(max_length=100)
    Date = models.DateField()
    HIV = models.CharField(max_length=20, choices=RESULT_CHOICES)
    HepatitisB = models.CharField(max_length=20, choices=RESULT_CHOICES)
    HepatitisC = models.CharField(max_length=20, choices=RESULT_CHOICES)
    Syphilis = models.CharField(max_length=20, choices=RESULT_CHOICES)
    OverallResult = models.CharField(max_length=20, choices=RESULT_CHOICES)
    Notes = models.TextField(null=True, blank=True)
    CreatedAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Verification'
        verbose_name = 'Verification'
        verbose_name_plural = 'Verifications'

    def __str__(self):
        return f"{self.VerificationID} - Unit:{self.UnitID} ({self.OverallResult})"

    def is_safe(self):
        """Encapsulated check to verify all serological tests passed."""
        tests = [self.HIV, self.HepatitisB, self.HepatitisC, self.Syphilis, self.OverallResult]
        return all(t == 'Passed' for t in tests)


class Disposal(models.Model):
    """
    Bio-waste disposal record for expired or contaminated units.
    """
    REASON_CHOICES = [
        ('Expired', 'Expired'),
        ('Contaminated', 'Contaminated'),
        ('Damaged', 'Damaged'),
        ('Failed Verification', 'Failed Verification'),
    ]

    DisposalID = models.CharField(max_length=20, primary_key=True)
    UnitID = models.CharField(max_length=20)
    DisposalDate = models.DateField()
    Reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    DisposedBy = models.CharField(max_length=100)
    Notes = models.TextField(null=True, blank=True)
    CreatedAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Disposal'
        verbose_name = 'Disposal'
        verbose_name_plural = 'Disposals'

    def __str__(self):
        return f"{self.DisposalID} - Unit:{self.UnitID} ({self.Reason})"
