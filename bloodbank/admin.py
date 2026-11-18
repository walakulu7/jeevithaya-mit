from django.contrib import admin
from .models import (
    User, Donor, Patient, BloodRequest, Donation, Inventory, Verification, Disposal
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('UserID', 'Name', 'Email', 'Role', 'Status', 'HospitalID', 'ContactNo')
    list_filter = ('Role', 'Status', 'HospitalID')
    search_fields = ('Name', 'Email', 'ContactNo')
    ordering = ('UserID',)
    exclude = ('Password',)


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ('DonorID', 'Name', 'BloodGroup', 'Phone', 'Status', 'CreatedAt')
    list_filter = ('BloodGroup', 'Status', 'Gender')
    search_fields = ('DonorID', 'Name', 'Phone', 'Email')
    ordering = ('DonorID',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('PatientID', 'Name', 'HospitalID', 'BloodGroup', 'Type', 'Urgency', 'Contact')
    list_filter = ('BloodGroup', 'Type', 'Urgency', 'HospitalID')
    search_fields = ('PatientID', 'Name', 'Contact')
    ordering = ('PatientID',)


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('RequestID', 'patient', 'HospitalID', 'BloodGroup', 'Type', 'Quantity', 'Urgency', 'Status')
    list_filter = ('Status', 'Urgency', 'BloodGroup', 'Type')
    search_fields = ('RequestID', 'patient__PatientID', 'patient__Name')
    ordering = ('-RequestDate',)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('DonationID', 'donor', 'Date', 'BloodGroup', 'Type', 'Quantity', 'Status')
    list_filter = ('BloodGroup', 'Type', 'Status')
    search_fields = ('DonationID', 'donor__DonorID', 'donor__Name')
    ordering = ('-Date',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('UnitID', 'donation', 'donor', 'BloodGroup', 'Type', 'Quantity', 'Status', 'ExpiryDate')
    list_filter = ('Status', 'BloodGroup', 'Type')
    search_fields = ('UnitID', 'donation__DonationID', 'donor__DonorID', 'BatchNo')
    ordering = ('ExpiryDate',)


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ('VerificationID', 'unit', 'donor', 'VerifiedBy', 'Date', 'OverallResult')
    list_filter = ('OverallResult', 'HIV', 'HepatitisB', 'HepatitisC', 'Syphilis')
    search_fields = ('VerificationID', 'unit__UnitID', 'donor__DonorID')
    ordering = ('-Date',)


@admin.register(Disposal)
class DisposalAdmin(admin.ModelAdmin):
    list_display = ('DisposalID', 'unit', 'DisposalDate', 'Reason', 'DisposedBy')
    list_filter = ('Reason',)
    search_fields = ('DisposalID', 'unit__UnitID')
    ordering = ('-DisposalDate',)
