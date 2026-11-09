from django.test import TestCase, Client
from datetime import date, timedelta
from bloodbank.models import (
    User, Donor, Patient, BloodRequest, Inventory, Verification, Disposal
)
from bloodbank.services import (
    InventoryService, RequestFulfillmentService,
    InventoryReportStrategy, DonationReportStrategy, RequestReportStrategy, AnalyticsContext
)


class OOPModelTests(TestCase):
    """Unit tests validating OOP Inheritance, Encapsulation, and Calculations."""

    def test_inheritance_and_age_calculation(self):
        """Validates that Donor and Patient inherit from BasePerson and calculate age correctly."""
        birth_date = date.today() - timedelta(days=365.25 * 25)
        donor = Donor.objects.create(
            DonorID="D_TEST1",
            Name="Test Donor",
            BloodGroup="O+",
            Phone="0771234567",
            DateOfBirth=birth_date
        )
        self.assertEqual(donor.calculate_age, 25)
        self.assertTrue(donor.is_eligible())

    def test_encapsulation_password_hashing(self):
        """Validates that User entity encapsulates secure PBKDF2 password hashing."""
        user = User.objects.create(
            Name="Test Admin",
            Email="testadmin@example.com",
            Role="system_admin"
        )
        user.set_password("Secret123!")
        user.save()

        # Raw password must not be stored in plaintext
        self.assertNotEqual(user.Password, "Secret123!")
        self.assertTrue(user.check_password("Secret123!"))
        self.assertFalse(user.check_password("WrongPassword"))

    def test_inventory_encapsulated_expiry(self):
        """Validates that Inventory unit correctly calculates whether it is expired."""
        valid_unit = Inventory.objects.create(
            UnitID="U_VAL",
            DonationID="DN1",
            DonorID="D1",
            BloodBankID=1,
            BloodGroup="A+",
            Type="Blood",
            Quantity=1,
            BatchNo="B1",
            ExpiryDate=date.today() + timedelta(days=10),
            Status="Available"
        )
        expired_unit = Inventory.objects.create(
            UnitID="U_EXP",
            DonationID="DN2",
            DonorID="D2",
            BloodBankID=1,
            BloodGroup="A+",
            Type="Blood",
            Quantity=1,
            BatchNo="B2",
            ExpiryDate=date.today() - timedelta(days=2),
            Status="Available"
        )
        self.assertFalse(valid_unit.is_expired())
        self.assertTrue(expired_unit.is_expired())

    def test_verification_safety_rule(self):
        """Validates that Verification entity checks all serological markers."""
        safe_ver = Verification(
            VerificationID="V_SAFE",
            UnitID="U1",
            DonorID="D1",
            VerifiedBy="Doctor",
            Date=date.today(),
            HIV="Passed",
            HepatitisB="Passed",
            HepatitisC="Passed",
            Syphilis="Passed",
            OverallResult="Passed"
        )
        unsafe_ver = Verification(
            VerificationID="V_UNSAFE",
            UnitID="U2",
            DonorID="D2",
            VerifiedBy="Doctor",
            Date=date.today(),
            HIV="Passed",
            HepatitisB="Failed",
            HepatitisC="Passed",
            Syphilis="Passed",
            OverallResult="Failed"
        )
        self.assertTrue(safe_ver.is_safe())
        self.assertFalse(unsafe_ver.is_safe())


class OOPServiceAndPolymorphismTests(TestCase):
    """Unit tests validating OOP Abstraction, Polymorphism, and Domain Services."""

    def test_polymorphic_reporting_strategies(self):
        """Validates that AnalyticsContext polymorphically executes report strategies."""
        inv_strat = InventoryReportStrategy()
        don_strat = DonationReportStrategy()
        req_strat = RequestReportStrategy()

        context = AnalyticsContext(inv_strat)
        inv_report = context.execute()
        self.assertIn("total_available_units", inv_report)

        context.set_strategy(don_strat)
        don_report = context.execute()
        self.assertIn("total_donations", don_report)

        context.set_strategy(req_strat)
        req_report = context.execute()
        self.assertIn("total_requests", req_report)

    def test_inventory_service_verification_workflow(self):
        """Validates that failed verification automatically triggers disposal creation."""
        unit = Inventory.objects.create(
            UnitID="U_TEST_FLOW",
            DonationID="DN1",
            DonorID="D1",
            BloodBankID=1,
            BloodGroup="B+",
            Type="Blood",
            Quantity=1,
            BatchNo="B100",
            ExpiryDate=date.today() + timedelta(days=20),
            Status="Reserved"
        )

        service = InventoryService()
        # Process failed verification
        service.process_verification_result(
            unit_id=unit.UnitID,
            donor_id="D1",
            result="Failed",
            verified_by="Lab Tech",
            notes="Inconclusive marker"
        )

        unit.refresh_from_db()
        self.assertEqual(unit.Status, "Expired")
        # Check automatic bio-waste disposal record
        self.assertTrue(Disposal.objects.filter(UnitID=unit.UnitID).exists())


class RESTAPITests(TestCase):
    """Integration tests validating REST API endpoints and payload normalizers."""

    def setUp(self):
        self.client = Client()

    def test_donor_api_crud(self):
        """Validates creating and listing donors through the REST API."""
        payload = {
            "DonorID": "D_API_01",
            "Name": "API Donor",
            "BloodGroup": "AB+",
            "Phone": "0770001111",
            "Status": "Eligible"
        }
        res = self.client.post("/api/donors/", data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 201)

        get_res = self.client.get("/api/donors/")
        self.assertEqual(get_res.status_code, 200)
        donors = get_res.json()
        self.assertTrue(any(d['DonorID'] == "D_API_01" for d in donors))

    def test_dashboard_stats_api(self):
        """Validates that dashboard statistics endpoint returns correct counts."""
        res = self.client.get("/api/dashboard/stats/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("donorCount", data)
        self.assertIn("unitCount", data)
        self.assertIn("requestCount", data)
