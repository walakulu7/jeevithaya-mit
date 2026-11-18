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
from django.db import transaction
from django.db.models import Sum
from .models import (
    User, Donor, Patient, BloodRequest, Donation,
    Inventory, Verification, Disposal, InvalidTransition,
)


# ==============================================================================
# OOP PILLAR 1: ABSTRACTION (Base Service Interface)
# ==============================================================================

class BaseService(ABC):
    """
    Abstract Base Class for all Domain Services.

    Each concrete service names the model it manages; shared read operations
    are implemented once here (Template Method), and subclasses add the
    business workflows for their own aggregate.
    """

    @property
    @abstractmethod
    def model(self):
        """The Django model class this service is responsible for."""

    def get_all(self):
        """Retrieve all records managed by this service, newest first."""
        return self.model.objects.all().order_by('-CreatedAt')

    def get(self, pk):
        """Retrieve one record by primary key, or None."""
        return self.model.objects.filter(pk=pk).first()


def next_sequential_id(model, prefix, start=1001):
    """Return the next free ID of the form <prefix><number> for a model's primary key."""
    pk_name = model._meta.pk.name
    numbers = []
    for value in model.objects.filter(**{f"{pk_name}__startswith": prefix}).values_list(pk_name, flat=True):
        suffix = value[len(prefix):]
        if suffix.isdigit():
            numbers.append(int(suffix))
    return f"{prefix}{max(numbers, default=start - 1) + 1}"


# ==============================================================================
# OOP PILLAR 2 & 3: ENCAPSULATION & INHERITANCE (Domain Services)
# ==============================================================================

class InventoryService(BaseService):
    """
    Service class encapsulating inventory management, cold-chain shelf-life
    tracking, and lab screening outcomes for stored units.
    """
    model = Inventory

    def get_available_units(self, blood_group=None, item_type=None):
        """Query usable, non-expired units, closest to expiry first (FEFO)."""
        qs = Inventory.objects.filter(Status='Available', ExpiryDate__gte=date.today())
        if blood_group:
            qs = qs.filter(BloodGroup=blood_group)
        if item_type:
            qs = qs.filter(Type=item_type)
        return qs.order_by('ExpiryDate', 'UnitID')

    def process_verification_result(self, verification):
        """
        Business rule: a unit that fails serological screening is discarded
        and a bio-waste disposal record is created for it (once).
        Returns the disposal record created, or None.
        """
        if verification.OverallResult != 'Failed':
            return None

        unit = verification.unit
        unit.mark_discarded()  # raises InvalidTransition if the unit was already issued

        if unit.disposals.exists():
            return None
        return Disposal.objects.create(
            DisposalID=next_sequential_id(Disposal, 'DISP'),
            unit=unit,
            DisposalDate=date.today(),
            Reason='Failed Verification',
            DisposedBy=verification.VerifiedBy,
            Notes=f"Auto-disposed after failed screening {verification.VerificationID}. {verification.Notes or ''}".strip(),
        )

    def record_disposal(self, disposal):
        """Disposing of a unit takes it out of use permanently."""
        disposal.unit.mark_discarded()
        return disposal

    def auto_scan_and_flag_expired(self):
        """Scans inventory for units past their expiry date and updates status."""
        expired_units = Inventory.objects.filter(
            ExpiryDate__lt=date.today(),
            Status__in=['Available', 'Reserved']
        )
        count = 0
        for u in expired_units:
            u.mark_expired()
            count += 1
        return count


class RequestFulfillmentService(BaseService):
    """
    Service class encapsulating the blood request workflow: approval,
    rejection and fulfilment with automatic stock deduction.

    Depends on InventoryService for stock queries (injected, Dependency Inversion).
    """
    model = BloodRequest

    def __init__(self, inventory_service=None):
        self.inventory = inventory_service or InventoryService()

    def change_status(self, request_obj, new_status):
        """Move a request to new_status through the model's guarded transitions."""
        if new_status == request_obj.Status:
            return {"success": True, "message": "Status unchanged.", "units_issued": []}
        if new_status == 'Fulfilled':
            return self.fulfill_request(request_obj.RequestID)
        actions = {
            'Approved': request_obj.approve,
            'Rejected': request_obj.reject,
            'Pending': request_obj.reopen,
        }
        if new_status not in actions:
            raise InvalidTransition(f"Unknown request status: {new_status}")
        actions[new_status]()
        return {"success": True, "message": f"Request {request_obj.RequestID} is now {new_status}.", "units_issued": []}

    def fulfill_request(self, request_id):
        """
        Allocates matching inventory units to an approved hospital request.
        """
        req = BloodRequest.objects.filter(RequestID=request_id).first()
        if not req:
            raise ValueError(f"Request {request_id} not found.")

        if req.Status == 'Fulfilled':
            return {"success": True, "message": f"Request {request_id} is already fulfilled.", "units_issued": []}
        if not req.can_transition_to('Fulfilled'):
            raise InvalidTransition(f"Request {request_id} must be Approved before it can be fulfilled (currently {req.Status}).")

        with transaction.atomic():
            matching_units = list(self.inventory.get_available_units(req.BloodGroup, req.Type)[:req.Quantity])

            if len(matching_units) < req.Quantity:
                return {
                    "success": False,
                    "message": f"Insufficient stock for {req.BloodGroup} {req.Type}. Required: {req.Quantity}, Available: {len(matching_units)}"
                }

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

BLOOD_GROUPS = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']


def _parse_iso_date(value):
    """Parse YYYY-MM-DD strings into date objects safely."""
    if not value or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _normalize_report_filters(days=None, filters=None):
    """Build normalized filter dict supporting both legacy `days` and dict filters."""
    raw = dict(filters or {})
    if days is not None and 'days' not in raw:
        raw['days'] = days

    raw_days = raw.get('days')
    parsed_days = None
    if raw_days not in (None, '', 'all'):
        try:
            parsed_days = max(1, int(raw_days))
        except (TypeError, ValueError):
            parsed_days = None

    start_date = _parse_iso_date(raw.get('start_date') or raw.get('from'))
    end_date = _parse_iso_date(raw.get('end_date') or raw.get('to'))
    if parsed_days and not start_date:
        start_date = date.today() - timedelta(days=parsed_days)

    blood_group = (raw.get('blood_group') or '').strip()
    if blood_group.lower() == 'all':
        blood_group = ''

    item_type = (raw.get('item_type') or '').strip()
    if item_type.lower() == 'all':
        item_type = ''

    return {
        'days': parsed_days,
        'start_date': start_date,
        'end_date': end_date,
        'blood_group': blood_group,
        'item_type': item_type,
    }


def _apply_query_filters(qs, filters, date_field=None, has_blood_group=True, has_item_type=True):
    """Apply normalized date range, blood group, and component type filters to a queryset."""
    if date_field:
        if filters.get('start_date'):
            qs = qs.filter(**{f"{date_field}__gte": filters['start_date']})
        if filters.get('end_date'):
            qs = qs.filter(**{f"{date_field}__lte": filters['end_date']})
    if has_blood_group and filters.get('blood_group'):
        qs = qs.filter(BloodGroup=filters['blood_group'])
    if has_item_type and filters.get('item_type'):
        qs = qs.filter(Type=filters['item_type'])
    return qs


def _pct(part, total):
    """Compute rounded percentage cleanly without zero-division errors."""
    return round((part / total) * 100, 1) if total else 0.0


class BaseReportStrategy(ABC):
    """
    Polymorphic report generation interface.
    Each report type implements its own custom analytical calculation.
    """
    @abstractmethod
    def generate(self, days=None, filters=None):
        """Generate formatted analytical report dictionary."""
        pass


class InventoryReportStrategy(BaseReportStrategy):
    """Generates inventory health, blood group × component matrix, expiry aging, and batch ledger."""
    def generate(self, days=None, filters=None):
        norm = _normalize_report_filters(days, filters)
        qs = _apply_query_filters(
            Inventory.objects.all(), norm, date_field=None, has_blood_group=True, has_item_type=True
        ).order_by('ExpiryDate', 'UnitID')

        units = list(qs)
        today = date.today()
        available_units = sum(u.Quantity for u in units if u.Status == 'Available' and u.ExpiryDate >= today)
        reserved_units = sum(u.Quantity for u in units if u.Status == 'Reserved')
        issued_units = sum(u.Quantity for u in units if u.Status == 'Issued')
        expired_units_list = [u for u in units if u.Status == 'Expired' or u.ExpiryDate < today]
        expired_count = len(expired_units_list)
        expired_qty = sum(u.Quantity for u in expired_units_list)

        breakdown = {}
        component_matrix = []
        active_groups = [norm['blood_group']] if norm['blood_group'] in BLOOD_GROUPS else BLOOD_GROUPS
        for bg in active_groups:
            bg_units = [u for u in units if u.BloodGroup == bg]
            avail_blood = sum(u.Quantity for u in bg_units if u.Type == 'Blood' and u.Status == 'Available' and u.ExpiryDate >= today)
            avail_plasma = sum(u.Quantity for u in bg_units if u.Type == 'Plasma' and u.Status == 'Available' and u.ExpiryDate >= today)
            reserved_bg = sum(u.Quantity for u in bg_units if u.Status == 'Reserved')
            expired_bg = sum(u.Quantity for u in bg_units if u.Status == 'Expired' or u.ExpiryDate < today)
            breakdown[bg] = avail_blood + avail_plasma
            component_matrix.append({
                "bloodGroup": bg,
                "bloodUnits": avail_blood,
                "plasmaUnits": avail_plasma,
                "totalAvailable": avail_blood + avail_plasma,
                "reservedUnits": reserved_bg,
                "expiredUnits": expired_bg,
            })

        buckets = {"Expired": 0, "Critical (<= 7d)": 0, "Warning (8-30d)": 0, "Healthy (> 30d)": 0}
        ledger = []
        for u in units:
            days_left = (u.ExpiryDate - today).days
            if u.Status == 'Expired' or days_left < 0:
                bucket = "Expired"
            elif days_left <= 7:
                bucket = "Critical (<= 7d)"
            elif days_left <= 30:
                bucket = "Warning (8-30d)"
            else:
                bucket = "Healthy (> 30d)"
            if u.Status in ('Available', 'Reserved', 'Expired'):
                buckets[bucket] += u.Quantity
            ledger.append({
                "unitId": u.UnitID,
                "donationId": u.donation_id,
                "donorId": u.donor_id,
                "bloodBankId": u.BloodBankID,
                "bloodGroup": u.BloodGroup,
                "type": u.Type,
                "quantity": u.Quantity,
                "batchNo": u.BatchNo,
                "expiryDate": u.ExpiryDate.isoformat(),
                "daysRemaining": days_left,
                "expiryBucket": bucket,
                "status": u.Status,
            })

        status_breakdown = [
            {"status": st, "records": sum(1 for u in units if u.Status == st), "units": sum(u.Quantity for u in units if u.Status == st)}
            for st in ['Available', 'Reserved', 'Issued', 'Expired']
        ]

        return {
            "report_name": "Inventory Distribution & Cold Chain Status",
            "total_available_units": sum(breakdown.values()),
            "expired_units": expired_count,
            "blood_group_distribution": breakdown,
            "summary": {
                "totalRecords": len(units),
                "availableUnits": available_units,
                "reservedUnits": reserved_units,
                "issuedUnits": issued_units,
                "expiredRecords": expired_count,
                "expiredUnits": expired_qty,
                "expiringSoonUnits": buckets["Critical (<= 7d)"],
            },
            "componentMatrix": component_matrix,
            "statusBreakdown": status_breakdown,
            "expiryBuckets": [{"bucket": k, "units": v} for k, v in buckets.items()],
            "ledger": ledger,
        }


class DonationReportStrategy(BaseReportStrategy):
    """Generates intake metrics, donor eligibility demographics, repeat donors, and donation ledger."""
    def generate(self, days=None, filters=None):
        norm = _normalize_report_filters(days, filters)
        donors_qs = _apply_query_filters(
            Donor.objects.all(), norm, date_field=None, has_blood_group=True, has_item_type=False
        )
        donations_qs = _apply_query_filters(
            Donation.objects.select_related('donor'), norm, date_field='Date', has_blood_group=True, has_item_type=True
        ).order_by('-Date', '-CreatedAt')

        donors = list(donors_qs)
        donations = list(donations_qs)

        eligible_count = sum(1 for d in donors if d.Status == 'Eligible')
        not_eligible_count = len(donors) - eligible_count

        active_groups = [norm['blood_group']] if norm['blood_group'] in BLOOD_GROUPS else BLOOD_GROUPS
        donor_by_bg = [
            {
                "bloodGroup": bg,
                "eligible": sum(1 for d in donors if d.BloodGroup == bg and d.Status == 'Eligible'),
                "notEligible": sum(1 for d in donors if d.BloodGroup == bg and d.Status != 'Eligible'),
                "total": sum(1 for d in donors if d.BloodGroup == bg),
            }
            for bg in active_groups
        ]

        age_brackets = {"18-25": 0, "26-35": 0, "36-50": 0, "51+": 0, "Unknown": 0}
        for d in donors:
            age = d.calculate_age
            if age is None:
                age_brackets["Unknown"] += 1
            elif age <= 25:
                age_brackets["18-25"] += 1
            elif age <= 35:
                age_brackets["26-35"] += 1
            elif age <= 50:
                age_brackets["36-50"] += 1
            else:
                age_brackets["51+"] += 1

        donor_totals = {}
        for dn in donations:
            entry = donor_totals.setdefault(dn.donor_id, {
                "donorId": dn.donor_id,
                "name": dn.donor.Name,
                "bloodGroup": dn.BloodGroup,
                "donations": 0,
                "units": 0,
                "lastDate": dn.Date.isoformat(),
            })
            entry["donations"] += 1
            entry["units"] += dn.Quantity
            if dn.Date.isoformat() > entry["lastDate"]:
                entry["lastDate"] = dn.Date.isoformat()

        top_donors = sorted(donor_totals.values(), key=lambda x: (-x["units"], -x["donations"]))[:10]

        ledger = [
            {
                "donationId": dn.DonationID,
                "donorId": dn.donor_id,
                "donorName": dn.donor.Name,
                "date": dn.Date.isoformat(),
                "bloodGroup": dn.BloodGroup,
                "type": dn.Type,
                "quantity": dn.Quantity,
                "bloodBankId": dn.BloodBankID,
                "status": dn.Status,
            }
            for dn in donations
        ]

        blood_donations = sum(1 for dn in donations if dn.Type == 'Blood')
        plasma_donations = sum(1 for dn in donations if dn.Type == 'Plasma')
        total_units_collected = sum(dn.Quantity for dn in donations)

        return {
            "report_name": "Donation Intake Summary",
            "total_donations": len(donations),
            "blood_donations": blood_donations,
            "plasma_donations": plasma_donations,
            "summary": {
                "totalDonors": len(donors),
                "eligibleDonors": eligible_count,
                "notEligibleDonors": not_eligible_count,
                "eligibilityRate": _pct(eligible_count, len(donors)),
                "totalDonations": len(donations),
                "totalUnitsCollected": total_units_collected,
                "bloodUnits": sum(dn.Quantity for dn in donations if dn.Type == 'Blood'),
                "plasmaUnits": sum(dn.Quantity for dn in donations if dn.Type == 'Plasma'),
            },
            "donorByBloodGroup": donor_by_bg,
            "ageDistribution": [{"bracket": k, "count": v} for k, v in age_brackets.items()],
            "topDonors": top_donors,
            "ledger": ledger,
        }


class RequestReportStrategy(BaseReportStrategy):
    """Generates hospital order metrics, urgency/status matrix, hospital demand, and requisition ledger."""
    def generate(self, days=None, filters=None):
        norm = _normalize_report_filters(days, filters)
        qs = _apply_query_filters(
            BloodRequest.objects.select_related('patient'), norm, date_field='RequestDate', has_blood_group=True, has_item_type=True
        ).order_by('-RequestDate', '-CreatedAt')

        requests_list = list(qs)
        today = date.today()
        avail_map = {}
        for inv in Inventory.objects.filter(Status='Available', ExpiryDate__gte=today):
            key = (inv.BloodGroup, inv.Type)
            avail_map[key] = avail_map.get(key, 0) + inv.Quantity

        pending_cnt = sum(1 for r in requests_list if r.Status == 'Pending')
        approved_cnt = sum(1 for r in requests_list if r.Status == 'Approved')
        fulfilled_cnt = sum(1 for r in requests_list if r.Status == 'Fulfilled')
        rejected_cnt = sum(1 for r in requests_list if r.Status == 'Rejected')
        critical_cnt = sum(1 for r in requests_list if r.Urgency == 'Critical')
        total_units_requested = sum(r.Quantity for r in requests_list)

        status_breakdown = [
            {
                "status": st,
                "count": sum(1 for r in requests_list if r.Status == st),
                "units": sum(r.Quantity for r in requests_list if r.Status == st),
            }
            for st in ['Pending', 'Approved', 'Fulfilled', 'Rejected']
        ]

        urgency_breakdown = [
            {
                "urgency": urg,
                "count": sum(1 for r in requests_list if r.Urgency == urg),
                "openCount": sum(1 for r in requests_list if r.Urgency == urg and r.Status in ('Pending', 'Approved')),
                "units": sum(r.Quantity for r in requests_list if r.Urgency == urg),
            }
            for urg in ['Critical', 'Urgent', 'Normal']
        ]

        hospitals = {}
        for r in requests_list:
            h = hospitals.setdefault(r.HospitalID, {
                "hospitalId": r.HospitalID,
                "totalRequests": 0,
                "fulfilled": 0,
                "open": 0,
                "totalUnits": 0,
            })
            h["totalRequests"] += 1
            h["totalUnits"] += r.Quantity
            if r.Status == 'Fulfilled':
                h["fulfilled"] += 1
            elif r.Status in ('Pending', 'Approved'):
                h["open"] += 1

        ledger = []
        for r in requests_list:
            pt = r.patient
            avail = avail_map.get((r.BloodGroup, r.Type), 0)
            ledger.append({
                "requestId": r.RequestID,
                "patientId": r.patient_id,
                "patientName": pt.Name,
                "hospitalId": r.HospitalID,
                "requestDate": r.RequestDate.isoformat(),
                "bloodGroup": r.BloodGroup,
                "type": r.Type,
                "quantity": r.Quantity,
                "urgency": r.Urgency,
                "status": r.Status,
                "availableStock": avail,
                "stockSufficient": avail >= r.Quantity,
            })

        return {
            "report_name": "Hospital Transfusion Demand Summary",
            "total_requests": len(requests_list),
            "pending": pending_cnt,
            "fulfilled": fulfilled_cnt,
            "critical": critical_cnt,
            "summary": {
                "totalRequests": len(requests_list),
                "pendingRequests": pending_cnt,
                "approvedRequests": approved_cnt,
                "fulfilledRequests": fulfilled_cnt,
                "rejectedRequests": rejected_cnt,
                "criticalRequests": critical_cnt,
                "totalUnitsRequested": total_units_requested,
                "fulfillmentRate": _pct(fulfilled_cnt, len(requests_list)),
            },
            "statusBreakdown": status_breakdown,
            "urgencyBreakdown": urgency_breakdown,
            "hospitalBreakdown": sorted(hospitals.values(), key=lambda x: x["hospitalId"]),
            "ledger": ledger,
        }


class VerificationReportStrategy(BaseReportStrategy):
    """Generates serological quality-control pass rates, marker reactivity, and verifier audit log."""
    def generate(self, days=None, filters=None):
        norm = _normalize_report_filters(days, filters)
        qs = _apply_query_filters(
            Verification.objects.select_related('unit'), norm, date_field='Date', has_blood_group=False, has_item_type=False
        ).order_by('-Date', '-CreatedAt')

        ver_list = []
        for v in qs:
            unit = v.unit
            if norm['blood_group'] and (not unit or unit.BloodGroup != norm['blood_group']):
                continue
            if norm['item_type'] and (not unit or unit.Type != norm['item_type']):
                continue
            ver_list.append((v, unit))

        passed_cnt = sum(1 for v, _ in ver_list if v.OverallResult == 'Passed')
        failed_cnt = len(ver_list) - passed_cnt

        markers = ['HIV', 'HepatitisB', 'HepatitisC', 'Syphilis']
        marker_breakdown = [
            {
                "marker": m,
                "passed": sum(1 for v, _ in ver_list if getattr(v, m) == 'Passed'),
                "failed": sum(1 for v, _ in ver_list if getattr(v, m) != 'Passed'),
            }
            for m in markers
        ]

        verifiers = {}
        for v, _ in ver_list:
            row = verifiers.setdefault(v.VerifiedBy, {"verifiedBy": v.VerifiedBy, "total": 0, "passed": 0, "failed": 0})
            row["total"] += 1
            if v.OverallResult == 'Passed':
                row["passed"] += 1
            else:
                row["failed"] += 1

        ledger = [
            {
                "verificationId": v.VerificationID,
                "unitId": v.unit_id,
                "donorId": v.donor_id,
                "bloodGroup": unit.BloodGroup if unit else "-",
                "type": unit.Type if unit else "-",
                "date": v.Date.isoformat(),
                "verifiedBy": v.VerifiedBy,
                "hiv": v.HIV,
                "hepatitisB": v.HepatitisB,
                "hepatitisC": v.HepatitisC,
                "syphilis": v.Syphilis,
                "overallResult": v.OverallResult,
                "notes": v.Notes or "",
            }
            for v, unit in ver_list
        ]

        return {
            "report_name": "Serological Screening & Quality Control Audit",
            "summary": {
                "totalVerified": len(ver_list),
                "passedCount": passed_cnt,
                "failedCount": failed_cnt,
                "passRate": _pct(passed_cnt, len(ver_list)),
            },
            "markerBreakdown": marker_breakdown,
            "verifierBreakdown": sorted(verifiers.values(), key=lambda x: -x["total"]),
            "ledger": ledger,
        }


class DisposalReportStrategy(BaseReportStrategy):
    """Generates bio-waste disposal reason shares, blood group wastage, and officer audit trail."""
    def generate(self, days=None, filters=None):
        norm = _normalize_report_filters(days, filters)
        qs = _apply_query_filters(
            Disposal.objects.select_related('unit'), norm, date_field='DisposalDate', has_blood_group=False, has_item_type=False
        ).order_by('-DisposalDate', '-CreatedAt')

        disp_list = []
        for dp in qs:
            unit = dp.unit
            if norm['blood_group'] and (not unit or unit.BloodGroup != norm['blood_group']):
                continue
            if norm['item_type'] and (not unit or unit.Type != norm['item_type']):
                continue
            disp_list.append((dp, unit))

        total_units_disposed = sum((unit.Quantity if unit else 1) for _, unit in disp_list)
        reasons = ['Expired', 'Failed Verification', 'Contaminated', 'Damaged']
        reason_breakdown = []
        for reason in reasons:
            cnt = sum(1 for dp, _ in disp_list if dp.Reason == reason)
            reason_breakdown.append({
                "reason": reason,
                "count": cnt,
                "sharePercent": _pct(cnt, len(disp_list)),
            })

        bg_wastage = {}
        officers = {}
        ledger = []
        for dp, unit in disp_list:
            bg = unit.BloodGroup if unit else "Unknown"
            qty = unit.Quantity if unit else 1
            bg_entry = bg_wastage.setdefault(bg, {"bloodGroup": bg, "records": 0, "units": 0})
            bg_entry["records"] += 1
            bg_entry["units"] += qty

            off_entry = officers.setdefault(dp.DisposedBy, {"disposedBy": dp.DisposedBy, "records": 0, "units": 0})
            off_entry["records"] += 1
            off_entry["units"] += qty

            ledger.append({
                "disposalId": dp.DisposalID,
                "unitId": dp.unit_id,
                "bloodGroup": unit.BloodGroup if unit else "-",
                "type": unit.Type if unit else "-",
                "quantity": qty,
                "disposalDate": dp.DisposalDate.isoformat(),
                "reason": dp.Reason,
                "disposedBy": dp.DisposedBy,
                "notes": dp.Notes or "",
            })

        return {
            "report_name": "Bio-Waste Disposal & Wastage Compliance Audit",
            "summary": {
                "totalDisposals": len(disp_list),
                "totalUnitsDisposed": total_units_disposed,
                "expiredReasonCount": sum(1 for dp, _ in disp_list if dp.Reason == 'Expired'),
                "failedVerificationCount": sum(1 for dp, _ in disp_list if dp.Reason == 'Failed Verification'),
                "contaminatedCount": sum(1 for dp, _ in disp_list if dp.Reason == 'Contaminated'),
                "damagedCount": sum(1 for dp, _ in disp_list if dp.Reason == 'Damaged'),
            },
            "reasonBreakdown": reason_breakdown,
            "bloodGroupWastage": sorted(bg_wastage.values(), key=lambda x: -x["units"]),
            "officerBreakdown": sorted(officers.values(), key=lambda x: -x["records"]),
            "ledger": ledger,
        }


class ExecutiveOverviewStrategy(BaseReportStrategy):
    """Aggregates KPIs, supply vs demand shortages, and cross-module timeline across the blood bank."""
    def generate(self, days=None, filters=None):
        norm = _normalize_report_filters(days, filters)
        inv = InventoryReportStrategy().generate(filters=norm)
        req = RequestReportStrategy().generate(filters=norm)
        don = DonationReportStrategy().generate(filters=norm)
        ver = VerificationReportStrategy().generate(filters=norm)
        disp = DisposalReportStrategy().generate(filters=norm)

        active_groups = [norm['blood_group']] if norm['blood_group'] in BLOOD_GROUPS else BLOOD_GROUPS
        supply_vs_demand = []
        critical_shortages = []
        for bg in active_groups:
            available = inv["blood_group_distribution"].get(bg, 0)
            pending_demand = sum(
                row["quantity"] for row in req["ledger"]
                if row["bloodGroup"] == bg and row["status"] in ("Pending", "Approved")
            )
            gap = available - pending_demand
            item = {
                "bloodGroup": bg,
                "available": available,
                "pendingDemand": pending_demand,
                "gap": gap,
                "shortage": gap < 0,
            }
            supply_vs_demand.append(item)
            if gap < 0:
                critical_shortages.append(item)

        patients_qs = Patient.objects.all()
        if norm['blood_group']:
            patients_qs = patients_qs.filter(BloodGroup=norm['blood_group'])
        if norm['item_type']:
            patients_qs = patients_qs.filter(Type=norm['item_type'])

        total_handled = inv["summary"]["availableUnits"] + inv["summary"]["issuedUnits"] + disp["summary"]["totalUnitsDisposed"]

        timeline = []
        for row in req["ledger"][:20]:
            timeline.append({
                "module": "Request",
                "id": row["requestId"],
                "date": row["requestDate"],
                "bloodGroup": row["bloodGroup"],
                "summary": f"{row['type']} x{row['quantity']} • {row['urgency']} • {row['status']}",
            })
        for row in don["ledger"][:20]:
            timeline.append({
                "module": "Donation",
                "id": row["donationId"],
                "date": row["date"],
                "bloodGroup": row["bloodGroup"],
                "summary": f"Donor {row['donorName']} • {row['type']} x{row['quantity']}",
            })
        for row in ver["ledger"][:20]:
            timeline.append({
                "module": "Verification",
                "id": row["verificationId"],
                "date": row["date"],
                "bloodGroup": row["bloodGroup"],
                "summary": f"Unit {row['unitId']} • {row['overallResult']} • By {row['verifiedBy']}",
            })
        for row in disp["ledger"][:20]:
            timeline.append({
                "module": "Disposal",
                "id": row["disposalId"],
                "date": row["disposalDate"],
                "bloodGroup": row["bloodGroup"],
                "summary": f"Unit {row['unitId']} • {row['reason']} • By {row['disposedBy']}",
            })
        timeline.sort(key=lambda x: x["date"], reverse=True)

        return {
            "report_name": "Executive Blood Bank Analytics Overview",
            "summary": {
                "totalDonors": don["summary"]["totalDonors"],
                "totalPatients": patients_qs.count(),
                "totalRequests": req["summary"]["totalRequests"],
                "pendingRequests": req["summary"]["pendingRequests"] + req["summary"]["approvedRequests"],
                "fulfillmentRate": req["summary"]["fulfillmentRate"],
                "availableUnits": inv["summary"]["availableUnits"],
                "expiredUnits": inv["summary"]["expiredUnits"],
                "expiringSoonUnits": inv["summary"]["expiringSoonUnits"],
                "totalVerifications": ver["summary"]["totalVerified"],
                "verificationPassRate": ver["summary"]["passRate"],
                "totalDisposals": disp["summary"]["totalDisposals"],
                "wastageRate": _pct(disp["summary"]["totalUnitsDisposed"], total_handled),
            },
            "supplyVsDemand": supply_vs_demand,
            "criticalShortages": critical_shortages,
            "timeline": timeline[:25],
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

    def execute(self, days=None, filters=None):
        return self._strategy.generate(days=days, filters=filters)

