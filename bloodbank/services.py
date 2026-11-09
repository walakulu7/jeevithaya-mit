"""
Jeevithaya Blood Bank Management System - Service Layer
Implements core Object-Oriented Programming (OOP) design patterns:
- Abstraction: Clean interfaces separating business logic from HTTP presentation views.
- Encapsulation: State and behavior encapsulated within service classes.
- Polymorphism: Abstract Report Strategy pattern with polymorphic implementations.
- Inheritance: Common base service classes with shared database query logic.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from django.db.models import Sum
from .models import (
    User, Donor, Patient, BloodRequest, Donation,
    Inventory, Verification, Disposal
)


# ==============================================================================
# OOP PILLAR 1: ABSTRACTION (Base Service Interface)
# ==============================================================================

class BaseService(ABC):
    """
    Abstract Base Class for all Domain Services.
    Enforces standardized lifecycle and logging methods.
    """
    @abstractmethod
    def get_all(self):
        """Retrieve all records managed by this service."""
        pass


# ==============================================================================
# OOP PILLAR 2 & 3: ENCAPSULATION & INHERITANCE (Domain Services)
# ==============================================================================

class InventoryService(BaseService):
    """
    Service class encapsulating inventory management, cold-chain shelf-life
    tracking, stock reservations, and automated unit dispatching.
    """

    def get_all(self):
        return Inventory.objects.all().order_by('-CreatedAt')

    def get_available_units(self, blood_group=None, item_type=None):
        """Query currently usable and non-expired blood/plasma units."""
        qs = Inventory.objects.filter(Status='Available', ExpiryDate__gte=date.today())
        if blood_group:
            qs = qs.filter(BloodGroup=blood_group)
        if item_type:
            qs = qs.filter(Type=item_type)
        return qs

    def process_verification_result(self, unit_id, donor_id, result, verified_by, notes=""):
        """
        Business Rule Workflow:
        When quality verification completes, update unit status or trigger disposal.
        """
        unit = Inventory.objects.filter(UnitID=unit_id).first()
        if not unit:
            return None

        if result == 'Passed':
            unit.Status = 'Available'
            unit.save()
        else:
            unit.Status = 'Expired'
            unit.save()
            # Automatically record bio-waste disposal
            Disposal.objects.create(
                DisposalID=f"DISP{unit_id[-4:]}",
                UnitID=unit_id,
                DisposalDate=date.today(),
                Reason='Failed Verification',
                DisposedBy=verified_by,
                Notes=f"Auto-disposed due to failed testing. Notes: {notes}"
            )
        return unit

    def auto_scan_and_flag_expired(self):
        """Scans inventory for units past their expiry date and updates status."""
        expired_units = Inventory.objects.filter(
            ExpiryDate__lt=date.today(),
            Status__in=['Available', 'Reserved']
        )
        count = expired_units.count()
        for u in expired_units:
            u.Status = 'Expired'
            u.save()
        return count


class RequestFulfillmentService(BaseService):
    """
    Service class encapsulating hospital blood request fulfillment,
    compatibility checking, and automatic stock deduction.
    """

    def get_all(self):
        return BloodRequest.objects.all().order_by('-CreatedAt')

    def fulfill_request(self, request_id):
        """
        Attempts to allocate matching inventory units to a pending hospital request.
        """
        req = BloodRequest.objects.filter(RequestID=request_id).first()
        if not req:
            raise ValueError(f"Request {request_id} not found.")

        # Find matching available units
        matching_units = Inventory.objects.filter(
            BloodGroup=req.BloodGroup,
            Type=req.Type,
            Status='Available',
            ExpiryDate__gte=date.today()
        )[:req.Quantity]

        if matching_units.count() < req.Quantity:
            return {
                "success": False,
                "message": f"Insufficient stock for {req.BloodGroup} {req.Type}. Required: {req.Quantity}, Available: {matching_units.count()}"
            }

        # Mark units as Issued
        for unit in matching_units:
            unit.mark_issued()

        req.fulfill()
        return {
            "success": True,
            "message": f"Request {request_id} successfully fulfilled.",
            "units_issued": [u.UnitID for u in matching_units]
        }


# ==============================================================================
# OOP PILLAR 4: POLYMORPHISM (Strategy Pattern for Reporting & Analytics)
# ==============================================================================

class BaseReportStrategy(ABC):
    """
    Polymorphic report generation interface.
    Each report type implements its own custom analytical calculation.
    """
    @abstractmethod
    def generate(self, days=None):
        """Generate formatted analytical report dictionary."""
        pass


class InventoryReportStrategy(BaseReportStrategy):
    """Generates inventory health, blood group distribution, and expiry metrics."""
    def generate(self, days=None):
        total_units = Inventory.objects.filter(Status='Available').aggregate(total=Sum('Quantity'))['total'] or 0
        expired_count = Inventory.objects.filter(ExpiryDate__lt=date.today()).count()

        groups = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        breakdown = {}
        for bg in groups:
            breakdown[bg] = Inventory.objects.filter(BloodGroup=bg, Status='Available').aggregate(total=Sum('Quantity'))['total'] or 0

        return {
            "report_name": "Inventory Distribution & Cold Chain Status",
            "total_available_units": total_units,
            "expired_units": expired_count,
            "blood_group_distribution": breakdown
        }


class DonationReportStrategy(BaseReportStrategy):
    """Generates intake metrics and donor activity statistics."""
    def generate(self, days=None):
        qs = Donation.objects.all()
        if days:
            start_date = date.today() - timedelta(days=days)
            qs = qs.filter(Date__gte=start_date)

        return {
            "report_name": "Donation Intake Summary",
            "total_donations": qs.count(),
            "blood_donations": qs.filter(Type='Blood').count(),
            "plasma_donations": qs.filter(Type='Plasma').count(),
        }


class RequestReportStrategy(BaseReportStrategy):
    """Generates hospital order metrics and urgency distribution."""
    def generate(self, days=None):
        qs = BloodRequest.objects.all()
        if days:
            start_date = date.today() - timedelta(days=days)
            qs = qs.filter(RequestDate__gte=start_date)

        return {
            "report_name": "Hospital Transfusion Demand Summary",
            "total_requests": qs.count(),
            "pending": qs.filter(Status='Pending').count(),
            "fulfilled": qs.filter(Status='Fulfilled').count(),
            "critical": qs.filter(Urgency='Critical').count(),
        }


# Polymorphic Context Executor
class AnalyticsContext:
    """
    Executes report strategies polymorphically without knowing concrete classes.
    """
    def __init__(self, strategy: BaseReportStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: BaseReportStrategy):
        self._strategy = strategy

    def execute(self, days=None):
        return self._strategy.generate(days)

