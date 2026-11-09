from django.core.management.base import BaseCommand
from datetime import date, timedelta
from bloodbank.models import (
    User, Donor, Patient, BloodRequest, Donation,
    Inventory, Verification, Disposal
)
from bloodbank.views import DEFAULT_DEMO_USERS


class Command(BaseCommand):
    help = 'Seeds sample healthcare data for testing and demonstrations.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Jeevithaya database..."))

        # 1. Seed Demo Users
        for u in DEFAULT_DEMO_USERS:
            user, created = User.objects.get_or_create(
                Email=u['Email'],
                defaults={
                    'Name': u['Name'],
                    'Role': u['Role'],
                    'HospitalID': u.get('HospitalID', 1),
                    'ContactNo': '0112345678'
                }
            )
            if created or not user.Password.startswith('pbkdf2_'):
                user.set_password(u['Password'])
                user.save()
        self.stdout.write(self.style.SUCCESS(f"✓ Users verified: {User.objects.count()}"))

        # 2. Seed Donors
        sample_donors = [
            {"DonorID": "D001", "Name": "Charith Kasun", "BloodGroup": "O+", "Phone": "0777678678", "Status": "Eligible", "Email": "charith@example.com", "Gender": "Male"},
            {"DonorID": "D002", "Name": "Vithuran Shan", "BloodGroup": "A+", "Phone": "0711123123", "Status": "Not Eligible", "Email": "vithu@example.com", "Gender": "Male"},
            {"DonorID": "D003", "Name": "Sula Fernando", "BloodGroup": "B-", "Phone": "0755123123", "Status": "Eligible", "Email": "sula@example.com", "Gender": "Female"},
            {"DonorID": "D004", "Name": "Walakulu Bandara", "BloodGroup": "AB+", "Phone": "0788123123", "Status": "Eligible", "Email": "walakulu@example.com", "Gender": "Male"},
            {"DonorID": "D005", "Name": "Anoma Perera", "BloodGroup": "O-", "Phone": "0722334455", "Status": "Eligible", "Email": "anoma@example.com", "Gender": "Female"},
        ]
        for d in sample_donors:
            Donor.objects.update_or_create(DonorID=d['DonorID'], defaults=d)
        self.stdout.write(self.style.SUCCESS(f"✓ Donors verified: {Donor.objects.count()}"))

        # 3. Seed Patients
        sample_patients = [
            {"PatientID": "P101", "HospitalID": 1, "Name": "Kamal Wickramasinghe", "BloodGroup": "O+", "Type": "Blood", "Urgency": "Critical", "Contact": "0771122334", "Age": 45, "Gender": "Male"},
            {"PatientID": "P102", "HospitalID": 1, "Name": "Nalini Jayasuriya", "BloodGroup": "A+", "Type": "Plasma", "Urgency": "Urgent", "Contact": "0719988776", "Age": 62, "Gender": "Female"},
            {"PatientID": "P103", "HospitalID": 2, "Name": "Rohan Senanayake", "BloodGroup": "B-", "Type": "Blood", "Urgency": "Normal", "Contact": "0754433221", "Age": 28, "Gender": "Male"},
        ]
        for p in sample_patients:
            Patient.objects.update_or_create(PatientID=p['PatientID'], defaults=p)
        self.stdout.write(self.style.SUCCESS(f"✓ Patients verified: {Patient.objects.count()}"))

        # 4. Seed Inventory Units
        today = date.today()
        sample_inventory = [
            {"UnitID": "U1001", "DonationID": "DN101", "DonorID": "D001", "BloodBankID": 1, "BloodGroup": "O+", "Type": "Blood", "Quantity": 2, "BatchNo": "B-2026-A1", "ExpiryDate": today + timedelta(days=28), "Status": "Available"},
            {"UnitID": "U1002", "DonationID": "DN102", "DonorID": "D003", "BloodBankID": 1, "BloodGroup": "B-", "Type": "Plasma", "Quantity": 1, "BatchNo": "B-2026-A2", "ExpiryDate": today + timedelta(days=60), "Status": "Available"},
            {"UnitID": "U1003", "DonationID": "DN103", "DonorID": "D004", "BloodBankID": 1, "BloodGroup": "AB+", "Type": "Blood", "Quantity": 1, "BatchNo": "B-2026-A3", "ExpiryDate": today + timedelta(days=14), "Status": "Reserved"},
            {"UnitID": "U1004", "DonationID": "DN104", "DonorID": "D005", "BloodBankID": 1, "BloodGroup": "O-", "Type": "Blood", "Quantity": 3, "BatchNo": "B-2026-A4", "ExpiryDate": today + timedelta(days=32), "Status": "Available"},
            {"UnitID": "U1005", "DonationID": "DN105", "DonorID": "D002", "BloodBankID": 1, "BloodGroup": "A+", "Type": "Blood", "Quantity": 1, "BatchNo": "B-2025-X9", "ExpiryDate": today - timedelta(days=5), "Status": "Expired"},
        ]
        for inv in sample_inventory:
            Inventory.objects.update_or_create(UnitID=inv['UnitID'], defaults=inv)
        self.stdout.write(self.style.SUCCESS(f"✓ Inventory units verified: {Inventory.objects.count()}"))

        # 5. Seed Blood Requests
        sample_requests = [
            {"RequestID": "REQ101", "PatientID": "P101", "HospitalID": 1, "RequestDate": today, "BloodGroup": "O+", "Type": "Blood", "Quantity": 2, "Urgency": "Critical", "Status": "Pending"},
            {"RequestID": "REQ102", "PatientID": "P102", "HospitalID": 1, "RequestDate": today - timedelta(days=1), "BloodGroup": "A+", "Type": "Plasma", "Quantity": 1, "Urgency": "Urgent", "Status": "Approved"},
            {"RequestID": "REQ103", "PatientID": "P103", "HospitalID": 2, "RequestDate": today - timedelta(days=2), "BloodGroup": "B-", "Type": "Blood", "Quantity": 1, "Urgency": "Normal", "Status": "Fulfilled"},
        ]
        for r in sample_requests:
            BloodRequest.objects.update_or_create(RequestID=r['RequestID'], defaults=r)
        self.stdout.write(self.style.SUCCESS(f"✓ Requisitions verified: {BloodRequest.objects.count()}"))

        # 6. Seed Verifications
        sample_verifications = [
            {"VerificationID": "V1001", "UnitID": "U1001", "DonorID": "D001", "VerifiedBy": "Dr. Saman Kumara", "Date": today, "HIV": "Passed", "HepatitisB": "Passed", "HepatitisC": "Passed", "Syphilis": "Passed", "OverallResult": "Passed", "Notes": "Safe for clinical use"},
            {"VerificationID": "V1002", "UnitID": "U1005", "DonorID": "D002", "VerifiedBy": "Dr. Kasun Silva", "Date": today - timedelta(days=6), "HIV": "Passed", "HepatitisB": "Failed", "HepatitisC": "Passed", "Syphilis": "Passed", "OverallResult": "Failed", "Notes": "Positive for Hep B surface antigen"},
        ]
        for v in sample_verifications:
            Verification.objects.update_or_create(VerificationID=v['VerificationID'], defaults=v)
        self.stdout.write(self.style.SUCCESS(f"✓ Verifications verified: {Verification.objects.count()}"))

        # 7. Seed Disposal
        Disposal.objects.update_or_create(
            DisposalID="DISP1001",
            defaults={
                "UnitID": "U1005",
                "DisposalDate": today - timedelta(days=5),
                "Reason": "Failed Verification",
                "DisposedBy": "Senior Lab Officer",
                "Notes": "Incinerated per bio-hazardous protocol"
            }
        )
        self.stdout.write(self.style.SUCCESS(f"✓ Disposals verified: {Disposal.objects.count()}"))

        self.stdout.write(self.style.SUCCESS("\nDatabase successfully seeded with realistic healthcare data!"))

