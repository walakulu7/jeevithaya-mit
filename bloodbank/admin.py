from django.contrib import admin
from .models import (
    System_Admin, Hospital_Admin, User, Donor, Patient, 
    BloodRequest, Donation, Inventory, Verification, Disposal
)

# Register your models here.

@admin.register(System_Admin)
class System_AdminAdmin(admin.ModelAdmin):
    list_display = ('AdminID', 'Name', 'Role', 'Email', 'ContactNo')
    list_filter = ('Role',)
    search_fields = ('Name', 'Email', 'ContactNo')
    ordering = ('AdminID',)


@admin.register(Hospital_Admin)
class Hospital_AdminAdmin(admin.ModelAdmin):
    list_display = ('HospitalAdminID', 'Name', 'HospitalID', 'Email', 'ContactNo')
    list_filter = ('HospitalID',)
    search_fields = ('Name', 'Email', 'ContactNo')
    ordering = ('HospitalAdminID',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('UserID', 'Name', 'Email', 'Role', 'HospitalID', 'ContactNo')
    list_filter = ('Role', 'HospitalID')
    search_fields = ('Name', 'Email', 'ContactNo')
    ordering = ('UserID',)


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ('DonorID', 'Name', 'BloodGroup', 'Phone', 'Status', 'CreatedAt')
    list_filter = ('BloodGroup', 'Status')
    search_fields = ('DonorID', 'Name', 'Phone', 'Email')
    ordering = ('-CreatedAt',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('PatientID', 'Name', 'HospitalID', 'BloodGroup', 'Type', 'Urgency', 'Contact')
    list_filter = ('BloodGroup', 'Type', 'Urgency', 'HospitalID')
    search_fields = ('PatientID', 'Name', 'Contact')
    ordering = ('-CreatedAt',)


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('RequestID', 'PatientID', 'HospitalID', 'BloodGroup', 'Type', 'Quantity', 'Urgency', 'Status')
    list_filter = ('Status', 'Urgency', 'Type', 'BloodGroup')
    search_fields = ('RequestID', 'PatientID')
    ordering = ('-CreatedAt',)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('DonationID', 'DonorID', 'Date', 'BloodGroup', 'Type', 'Quantity', 'Status')
    list_filter = ('BloodGroup', 'Type', 'Status', 'Date')
    search_fields = ('DonationID', 'DonorID')
    ordering = ('-Date',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('UnitID', 'DonationID', 'DonorID', 'BloodGroup', 'Type', 'Quantity', 'Status', 'ExpiryDate')
    list_filter = ('Status', 'BloodGroup', 'Type', 'BloodBankID')
    search_fields = ('UnitID', 'DonationID', 'DonorID', 'BatchNo')
    ordering = ('ExpiryDate',)


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ('VerificationID', 'UnitID', 'DonorID', 'VerifiedBy', 'Date', 'OverallResult')
    list_filter = ('OverallResult', 'Date')
    search_fields = ('VerificationID', 'UnitID', 'DonorID')
    ordering = ('-Date',)


@admin.register(Disposal)
class DisposalAdmin(admin.ModelAdmin):
    list_display = ('DisposalID', 'UnitID', 'DisposalDate', 'Reason', 'DisposedBy')
    list_filter = ('Reason', 'DisposalDate')
    search_fields = ('DisposalID', 'UnitID')
    ordering = ('-DisposalDate',)
