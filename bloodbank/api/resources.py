"""
REST resources for each domain model.

Every class inherits the generic CRUD behaviour from ModelResource and only
overrides the hooks where its business rules differ (Open/Closed + Polymorphism).
Workflow rules live in the domain services, obtained from the service container.
"""

from django.http import JsonResponse

from .. import container
from ..models import (
    User, Donor, Patient, BloodRequest, Donation, Inventory, Verification, Disposal,
)
from .common import (
    ModelResource, ApiError, model_to_dict, require_roles,
    ALL_ROLES, ADMIN_ROLES, LAB_ROLES, INVENTORY_ROLES, SYSTEM_ADMIN_ONLY,
)


class DonorResource(ModelResource):
    model = Donor
    label = 'Donor'


class PatientResource(ModelResource):
    model = Patient
    label = 'Patient'


class DonationResource(ModelResource):
    model = Donation
    label = 'Donation'
    read_roles = LAB_ROLES
    write_roles = LAB_ROLES


class BloodRequestResource(ModelResource):
    """
    Anyone on staff may raise a request; only admins may change its status.
    Status changes are delegated to RequestFulfillmentService, which enforces
    the lifecycle and issues stock on fulfilment.
    """
    model = BloodRequest
    label = 'Request'

    def serialize(self, obj):
        data = model_to_dict(obj)
        if getattr(obj, '_units_issued', None):
            data['units_issued'] = obj._units_issued
        return data

    def perform_create(self, request, data):
        status = data.pop('Status', None) or 'Pending'
        if status not in BloodRequest.INITIAL_STATUSES:
            raise ApiError("New requests must start as Pending or Approved.", 400)
        if status != 'Pending':
            require_roles(request, ADMIN_ROLES)
        data['Status'] = status
        return super().perform_create(request, data)

    def perform_update(self, request, obj, data):
        new_status = data.pop('Status', None)
        obj = super().perform_update(request, obj, data)
        if new_status and new_status != obj.Status:
            require_roles(request, ADMIN_ROLES)
            result = container.services.requests.change_status(obj, new_status)
            if not result['success']:
                raise ApiError(result['message'], 409)  # rolls back the whole update
            obj.refresh_from_db()
            obj._units_issued = result.get('units_issued', [])
        return obj


class InventoryResource(ModelResource):
    """Status changes go through the unit's guarded lifecycle."""
    model = Inventory
    label = 'Unit'
    read_roles = INVENTORY_ROLES
    write_roles = INVENTORY_ROLES

    def perform_update(self, request, obj, data):
        new_status = data.pop('Status', None)
        obj = super().perform_update(request, obj, data)
        if new_status:
            obj.transition_to(new_status)
        return obj


class VerificationResource(ModelResource):
    """A failed screening discards the unit and records its disposal."""
    model = Verification
    label = 'Verification'
    read_roles = LAB_ROLES
    write_roles = LAB_ROLES

    RESULT_ALIASES = {'pass': 'Passed', 'passed': 'Passed', 'fail': 'Failed', 'failed': 'Failed'}
    MARKERS = ('HIV', 'HepatitisB', 'HepatitisC', 'Syphilis')

    def prepare(self, request, data, instance=None):
        data = super().prepare(request, data, instance)
        if 'OverallResult' in data or instance is None:
            raw = str(data.get('OverallResult') or '').strip().lower()
            if raw not in self.RESULT_ALIASES:
                raise ApiError("Result must be Pass or Fail.", 400)
            data['OverallResult'] = self.RESULT_ALIASES[raw]
            for marker in self.MARKERS:
                if not data.get(marker):
                    data[marker] = data['OverallResult']
        if instance is None and not data.get('donor_id') and data.get('unit_id'):
            unit = Inventory.objects.filter(pk=data['unit_id']).first()
            if unit:
                data['donor_id'] = unit.donor_id
        return data

    def perform_create(self, request, data):
        verification = super().perform_create(request, data)
        container.services.inventory.process_verification_result(verification)
        return verification

    def perform_update(self, request, obj, data):
        verification = super().perform_update(request, obj, data)
        container.services.inventory.process_verification_result(verification)
        return verification


class DisposalResource(ModelResource):
    """Recording a disposal takes the unit out of use."""
    model = Disposal
    label = 'Disposal'
    read_roles = LAB_ROLES
    write_roles = LAB_ROLES

    def queryset(self):
        return Disposal.objects.select_related('unit')

    def serialize(self, obj):
        data = model_to_dict(obj)
        data['DonorID'] = obj.donor_id  # derived from the unit
        return data

    def prepare(self, request, data, instance=None):
        donor_id = (data.get('DonorID') or data.get('donorId') or '').strip()
        prepared = super().prepare(request, data, instance)
        unit_id = prepared.get('unit_id') or (instance.unit_id if instance else None)
        if donor_id and unit_id:
            unit = Inventory.objects.filter(pk=unit_id).first()
            if unit and unit.donor_id != donor_id:
                raise ApiError(f"Unit {unit_id} belongs to donor {unit.donor_id}, not {donor_id}.", 400)
        return prepared

    def perform_create(self, request, data):
        disposal = super().perform_create(request, data)
        container.services.inventory.record_disposal(disposal)
        return disposal


class UserResource(ModelResource):
    """
    System admins manage all accounts. Any user may read and update their own
    profile (name, contact, password) but not their role, status or email.
    """
    model = User
    label = 'User'
    read_roles = SYSTEM_ADMIN_ONLY
    write_roles = SYSTEM_ADMIN_ONLY
    SELF_EDITABLE = {'Name', 'ContactNo', 'Password'}

    def serialize(self, obj):
        data = model_to_dict(obj)
        data.pop('Password', None)
        return data

    def authorize(self, request, action, obj=None):
        is_self = obj is not None and obj.pk == request.current_user.pk
        if is_self and action in ('read', 'update'):
            return
        if is_self and action == 'delete':
            raise ApiError("You cannot delete your own account.", 400)
        super().authorize(request, action, obj)

    def prepare(self, request, data, instance=None):
        data = super().prepare(request, data, instance)
        acting_on_self = instance is not None and instance.pk == request.current_user.pk
        if acting_on_self and not request.current_user.has_role(User.SYSTEM_ADMIN):
            blocked = [k for k, v in data.items()
                       if k not in self.SELF_EDITABLE and getattr(instance, k) != v]
            if blocked:
                raise ApiError(f"You cannot change your own {', '.join(blocked)}.", 403)
        return data

    def _apply_password(self, user, raw_password):
        if raw_password:
            if len(raw_password) < 6:
                raise ApiError("Password must be at least 6 characters.", 400)
            user.set_password(raw_password)

    def perform_create(self, request, data):
        raw_password = data.pop('Password', '')
        if not raw_password:
            raise ApiError("A password is required for new users.", 400)
        user = User(**data)
        self._apply_password(user, raw_password)
        user.full_clean()
        user.save()
        return user

    def perform_update(self, request, obj, data):
        raw_password = data.pop('Password', None)
        for key, value in data.items():
            setattr(obj, key, value)
        self._apply_password(obj, raw_password)
        obj.full_clean()
        obj.save()
        return obj


def build(resource):
    """Return the (collection, item) view functions for a resource."""
    return resource.collection_view(), resource.item_view()


api_donors, api_donor_detail = build(DonorResource())
api_patients, api_patient_detail = build(PatientResource())
api_requests, api_request_detail = build(BloodRequestResource())
api_donations, api_donation_detail = build(DonationResource())
api_inventory, api_inventory_detail = build(InventoryResource())
api_verifications, api_verification_detail = build(VerificationResource())
api_disposals, api_disposal_detail = build(DisposalResource())
api_users, api_user_detail = build(UserResource())
