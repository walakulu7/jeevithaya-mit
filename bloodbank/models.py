from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.hashers import make_password, check_password, identify_hasher
from datetime import date


# ==============================================================================
# SHARED DOMAIN VOCABULARY (single source of truth for choice lists)
# ==============================================================================

BLOOD_GROUP_CHOICES = [
    ('O+', 'O+'), ('O-', 'O-'),
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
]

COMPONENT_TYPE_CHOICES = [
    ('Blood', 'Blood'),
    ('Plasma', 'Plasma'),
]

URGENCY_CHOICES = [
    ('Normal', 'Normal'),
    ('Urgent', 'Urgent'),
    ('Critical', 'Critical'),
]

TEST_RESULT_CHOICES = [
    ('Passed', 'Passed'),
    ('Failed', 'Failed'),
]


class InvalidTransition(Exception):
    """Raised when an entity is asked to move to a state its lifecycle forbids."""


# ==============================================================================
# OOP PILLAR 1 & 2: ABSTRACTION & INHERITANCE (Abstract Base Models)
# ==============================================================================

class BaseAuditableEntity(models.Model):
    """
    Abstract base entity encapsulating audit timestamps.
    Every domain model inherits it, so audit fields are defined exactly once.
    """
    CreatedAt = models.DateTimeField(auto_now_add=True)
    UpdatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class StatefulEntity(BaseAuditableEntity):
    """
    Abstract base for entities with a guarded status lifecycle.

    Subclasses declare TRANSITIONS (current status -> allowed next statuses).
    All status changes go through transition_to(), so no caller can put an
    entity into a state its lifecycle forbids (Encapsulation + Template Method).
    """
    TRANSITIONS = {}

    class Meta:
        abstract = True

    def can_transition_to(self, new_status):
        return new_status == self.Status or new_status in self.TRANSITIONS.get(self.Status, ())

    def transition_to(self, new_status):
        if new_status == self.Status:
            return self
        if not self.can_transition_to(new_status):
            allowed = ', '.join(self.TRANSITIONS.get(self.Status, ())) or 'none (final state)'
            raise InvalidTransition(
                f"{self._meta.verbose_name} {self.pk} cannot move from {self.Status} to {new_status}. "
                f"Allowed next: {allowed}."
            )
        self.Status = new_status
        self.save(update_fields=['Status', 'UpdatedAt'])
        return self


class BasePerson(BaseAuditableEntity):
    """
    Abstract base class representing common demographic and contact attributes
    shared by Donors and Patients. Demonstrates OOP Inheritance.
    """
    BLOOD_GROUP_CHOICES = BLOOD_GROUP_CHOICES

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
# USER MANAGEMENT (Encapsulation of Authentication & Roles)
# ==============================================================================

class User(BaseAuditableEntity):
    SYSTEM_ADMIN = 'system_admin'
    HOSPITAL_ADMIN = 'hospital_admin'
    FRONT_OFFICE = 'frontoffice_user'
    LAB_ASSISTANT = 'lab_assistant'

    ROLE_CHOICES = [
        (SYSTEM_ADMIN, 'System Admin'),
        (HOSPITAL_ADMIN, 'Hospital Admin'),
        (FRONT_OFFICE, 'Front Office User'),
        (LAB_ASSISTANT, 'Lab Assistant'),
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
        """Verify a candidate password against the stored hash. Plain text is never accepted."""
        if not self.Password:
            return False
        return check_password(raw_password, self.Password)

    @staticmethod
    def is_hashed(value):
        """True when value is a recognised Django password hash."""
        try:
            identify_hasher(value)
            return True
        except (ValueError, TypeError):
            return False

    @property
    def is_active(self):
        return self.Status == 'Active'

    # Encapsulation: Role Checking
    def has_role(self, *roles):
        """Returns True if the user possesses any of the specified roles."""
        return self.Role in roles


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
    TYPE_CHOICES = COMPONENT_TYPE_CHOICES
    URGENCY_CHOICES = URGENCY_CHOICES

    PatientID = models.CharField(max_length=20, primary_key=True)
    HospitalID = models.IntegerField(null=False)
    Type = models.CharField(max_length=10, choices=COMPONENT_TYPE_CHOICES)
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
# TRANSACTIONAL & LOGISTICAL ENTITIES (associated through foreign keys)
# ==============================================================================

class BloodRequest(StatefulEntity):
    """
    A hospital transfusion or plasma request for one registered patient.
    Lifecycle: Pending -> Approved -> Fulfilled, with Rejected as an exit.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Fulfilled', 'Fulfilled'),
        ('Rejected', 'Rejected'),
    ]
    TRANSITIONS = {
        'Pending': ('Approved', 'Rejected'),
        'Approved': ('Fulfilled', 'Rejected', 'Pending'),
        'Rejected': ('Pending',),
        'Fulfilled': (),
    }
    INITIAL_STATUSES = ('Pending', 'Approved')
    URGENCY_CHOICES = URGENCY_CHOICES
    TYPE_CHOICES = COMPONENT_TYPE_CHOICES

    RequestID = models.CharField(max_length=20, primary_key=True)
    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, db_column='PatientID', related_name='requests'
    )
    HospitalID = models.IntegerField()
    RequestDate = models.DateField()
    BloodGroup = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)
    Type = models.CharField(max_length=10, choices=COMPONENT_TYPE_CHOICES)
    Quantity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    Urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    class Meta:
        db_table = 'BloodRequest'
        verbose_name = 'Blood Request'
        verbose_name_plural = 'Blood Requests'

    def __str__(self):
        return f"{self.RequestID} - {self.patient_id} ({self.BloodGroup} x {self.Quantity})"

    def approve(self):
        """Transition request to Approved state."""
        return self.transition_to('Approved')

    def fulfill(self):
        """Transition request to Fulfilled state. Stock is allocated by RequestFulfillmentService."""
        return self.transition_to('Fulfilled')

    def reject(self):
        """Transition request to Rejected state."""
        return self.transition_to('Rejected')

    def reopen(self):
        """Send a request back to Pending for re-review."""
        return self.transition_to('Pending')


class Donation(BaseAuditableEntity):
    """
    An intake donation session from a registered donor.
    """
    BLOOD_GROUP_CHOICES = BLOOD_GROUP_CHOICES

    DonationID = models.CharField(max_length=20, primary_key=True)
    donor = models.ForeignKey(
        Donor, on_delete=models.PROTECT, db_column='DonorID', related_name='donations'
    )
    Date = models.DateField()
    BloodGroup = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)
    Type = models.CharField(max_length=10, choices=COMPONENT_TYPE_CHOICES)
    Quantity = models.IntegerField(validators=[MinValueValidator(1)])
    BloodBankID = models.IntegerField()
    Status = models.CharField(max_length=20, default='Pending')

    class Meta:
        db_table = 'Donation'
        verbose_name = 'Donation'
        verbose_name_plural = 'Donations'

    def __str__(self):
        return f"{self.DonationID} - Donor:{self.donor_id} ({self.BloodGroup})"


class Inventory(StatefulEntity):
    """
    A physical blood/plasma unit stored in the cold chain, produced by one donation.
    Lifecycle: Available <-> Reserved -> Issued; Expired and Discarded are exits.
    """
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('Issued', 'Issued'),
        ('Expired', 'Expired'),
        ('Discarded', 'Discarded'),
    ]
    TRANSITIONS = {
        'Available': ('Reserved', 'Issued', 'Expired', 'Discarded'),
        'Reserved': ('Available', 'Issued', 'Expired', 'Discarded'),
        'Expired': ('Discarded',),
        'Issued': (),
        'Discarded': (),
    }

    UnitID = models.CharField(max_length=20, primary_key=True)
    donation = models.ForeignKey(
        Donation, on_delete=models.PROTECT, db_column='DonationID', related_name='units'
    )
    donor = models.ForeignKey(
        Donor, on_delete=models.PROTECT, db_column='DonorID', related_name='units'
    )
    BloodBankID = models.IntegerField()
    BloodGroup = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)
    Type = models.CharField(max_length=10, choices=COMPONENT_TYPE_CHOICES)
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

    def mark_available(self):
        return self.transition_to('Available')

    def mark_reserved(self):
        """Reserve unit for pending hospital dispatch."""
        return self.transition_to('Reserved')

    def mark_issued(self):
        """Issue unit to hospital."""
        return self.transition_to('Issued')

    def mark_expired(self):
        return self.transition_to('Expired')

    def mark_discarded(self):
        """Remove the unit from use permanently (failed screening, damage, disposal)."""
        return self.transition_to('Discarded')


class Verification(BaseAuditableEntity):
    """
    Quality control & serological testing of one unit (HIV, Hepatitis B/C, Syphilis).
    """
    RESULT_CHOICES = TEST_RESULT_CHOICES

    VerificationID = models.CharField(max_length=20, primary_key=True)
    unit = models.ForeignKey(
        Inventory, on_delete=models.PROTECT, db_column='UnitID', related_name='verifications'
    )
    donor = models.ForeignKey(
        Donor, on_delete=models.PROTECT, db_column='DonorID', related_name='verifications'
    )
    VerifiedBy = models.CharField(max_length=100)
    Date = models.DateField()
    HIV = models.CharField(max_length=20, choices=TEST_RESULT_CHOICES)
    HepatitisB = models.CharField(max_length=20, choices=TEST_RESULT_CHOICES)
    HepatitisC = models.CharField(max_length=20, choices=TEST_RESULT_CHOICES)
    Syphilis = models.CharField(max_length=20, choices=TEST_RESULT_CHOICES)
    OverallResult = models.CharField(max_length=20, choices=TEST_RESULT_CHOICES)
    Notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'Verification'
        verbose_name = 'Verification'
        verbose_name_plural = 'Verifications'

    def __str__(self):
        return f"{self.VerificationID} - Unit:{self.unit_id} ({self.OverallResult})"

    def is_safe(self):
        """Encapsulated check to verify all serological tests passed."""
        tests = [self.HIV, self.HepatitisB, self.HepatitisC, self.Syphilis, self.OverallResult]
        return all(t == 'Passed' for t in tests)


class Disposal(BaseAuditableEntity):
    """
    Bio-waste disposal record for one expired or contaminated unit.
    """
    REASON_CHOICES = [
        ('Expired', 'Expired'),
        ('Contaminated', 'Contaminated'),
        ('Damaged', 'Damaged'),
        ('Failed Verification', 'Failed Verification'),
    ]

    DisposalID = models.CharField(max_length=20, primary_key=True)
    unit = models.ForeignKey(
        Inventory, on_delete=models.PROTECT, db_column='UnitID', related_name='disposals'
    )
    verification = models.ForeignKey(
        Verification, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='VerificationID', related_name='disposals',
        help_text='The failed screening that led to this disposal, if any.',
    )
    DisposalDate = models.DateField()
    Reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    DisposedBy = models.CharField(max_length=100)
    Notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'Disposal'
        verbose_name = 'Disposal'
        verbose_name_plural = 'Disposals'

    def __str__(self):
        return f"{self.DisposalID} - Unit:{self.unit_id} ({self.Reason})"

    @property
    def donor_id(self):
        """The donor is the unit's donor; it is navigated, not stored twice."""
        return self.unit.donor_id if self.unit_id else None

    def clean(self):
        """A linked screening must be for the same unit being disposed of."""
        from django.core.exceptions import ValidationError
        if self.verification_id and self.unit_id and self.verification.unit_id != self.unit_id:
            raise ValidationError({'verification': (
                f"Verification {self.verification_id} is for unit {self.verification.unit_id}, not {self.unit_id}."
            )})
