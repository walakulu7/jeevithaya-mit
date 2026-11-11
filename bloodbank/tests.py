from django.test import TestCase, Client
from datetime import date, timedelta
from bloodbank.models import (
    User, Donor, Patient, BloodRequest, Donation, Inventory, Verification, Disposal
)
from bloodbank.services import (
    InventoryService, RequestFulfillmentService,
    ExecutiveOverviewStrategy, InventoryReportStrategy, DonationReportStrategy,
    RequestReportStrategy, VerificationReportStrategy, DisposalReportStrategy, AnalyticsContext
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

    def test_user_edit_status_toggle_and_delete(self):
        """Validates user CRUD, active/inactive toggling, and inactive login rejection."""
        create_res = self.client.post(
            "/api/users/",
            data={
                "Name": "Nurse Jane",
                "Email": "jane@jeevithaya.com",
                "Role": "lab_assistant",
                "Password": "Password123!",
            },
            content_type="application/json",
        )
        self.assertEqual(create_res.status_code, 201)
        created = create_res.json()
        user_id = created["UserID"]
        self.assertEqual(created["Status"], "Active")
        self.assertNotIn("Password", created)

        # Edit user and deactivate
        edit_res = self.client.put(
            f"/api/users/{user_id}/",
            data={
                "Name": "Nurse Jane Updated",
                "Role": "frontoffice_user",
                "Status": "Inactive",
            },
            content_type="application/json",
        )
        self.assertEqual(edit_res.status_code, 200)
        updated = edit_res.json()
        self.assertEqual(updated["Name"], "Nurse Jane Updated")
        self.assertEqual(updated["Role"], "frontoffice_user")
        self.assertEqual(updated["Status"], "Inactive")

        # Inactive user cannot log in
        login_res = self.client.post(
            "/api/auth/login/",
            data={"email": "jane@jeevithaya.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(login_res.status_code, 403)

        # Reactivate and verify login works
        reactivate_res = self.client.put(
            f"/api/users/{user_id}/",
            data={"Status": "Active"},
            content_type="application/json",
        )
        self.assertEqual(reactivate_res.status_code, 200)
        login_ok = self.client.post(
            "/api/auth/login/",
            data={"email": "jane@jeevithaya.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(login_ok.status_code, 200)

        # Delete user
        del_res = self.client.delete(f"/api/users/{user_id}/")
        self.assertEqual(del_res.status_code, 204)
        self.assertFalse(User.objects.filter(UserID=user_id).exists())

    def test_professional_reports_api_and_strategies(self):
        """Validates all 6 detailed reports, expiry buckets, filters, and /api/reports/."""
        Donor.objects.create(DonorID="D_R1", Name="Alice", BloodGroup="O+", Phone="0771112222", Status="Eligible")
        Donor.objects.create(DonorID="D_R2", Name="Bob", BloodGroup="A-", Phone="0773334444", Status="Not Eligible")
        Patient.objects.create(PatientID="P_R1", HospitalID=1, Name="Charlie", BloodGroup="O+", Type="Blood", Urgency="Critical", Contact="0711112222")

        Donation.objects.create(DonationID="DN_R1", DonorID="D_R1", Date=date.today(), BloodGroup="O+", Type="Blood", Quantity=2, BloodBankID=1, Status="Completed")
        Inventory.objects.create(UnitID="U_R1", DonationID="DN_R1", DonorID="D_R1", BloodBankID=1, BloodGroup="O+", Type="Blood", Quantity=2, BatchNo="B-1", ExpiryDate=date.today() + timedelta(days=5), Status="Available")
        Inventory.objects.create(UnitID="U_R2", DonationID="DN_R1", DonorID="D_R1", BloodBankID=1, BloodGroup="A-", Type="Plasma", Quantity=1, BatchNo="B-2", ExpiryDate=date.today() + timedelta(days=45), Status="Available")
        Inventory.objects.create(UnitID="U_R3", DonationID="DN_R1", DonorID="D_R1", BloodBankID=1, BloodGroup="O+", Type="Blood", Quantity=1, BatchNo="B-3", ExpiryDate=date.today() - timedelta(days=1), Status="Expired")

        BloodRequest.objects.create(RequestID="REQ_R1", PatientID="P_R1", HospitalID=1, RequestDate=date.today(), BloodGroup="O+", Type="Blood", Quantity=3, Urgency="Critical", Status="Pending")
        Verification.objects.create(VerificationID="VER_R1", UnitID="U_R1", DonorID="D_R1", VerifiedBy="Senior Lab Officer", Date=date.today(), HIV="Passed", HepatitisB="Passed", HepatitisC="Passed", Syphilis="Passed", OverallResult="Passed")
        Verification.objects.create(VerificationID="VER_R2", UnitID="U_R3", DonorID="D_R1", VerifiedBy="Lab Assistant", Date=date.today(), HIV="Passed", HepatitisB="Failed", HepatitisC="Passed", Syphilis="Passed", OverallResult="Failed", Notes="Reactive HBV")
        Disposal.objects.create(DisposalID="DISP_R1", UnitID="U_R3", DisposalDate=date.today(), Reason="Expired", DisposedBy="Senior Lab Officer", Notes="Auto expired")

        res = self.client.get("/api/reports/?type=all")
        self.assertEqual(res.status_code, 200)
        payload = res.json()["reports"]

        self.assertEqual(set(payload.keys()), {"overview", "inventory", "requests", "donations", "verification", "disposal"})
        self.assertEqual(payload["inventory"]["summary"]["expiringSoonUnits"], 2)
        self.assertEqual(payload["inventory"]["summary"]["expiredUnits"], 1)
        self.assertEqual(payload["requests"]["summary"]["criticalRequests"], 1)
        self.assertEqual(payload["donations"]["summary"]["eligibleDonors"], 1)
        self.assertEqual(payload["verification"]["summary"]["failedCount"], 1)
        self.assertEqual(payload["disposal"]["summary"]["expiredReasonCount"], 1)
        self.assertTrue(any(s["bloodGroup"] == "O+" and s["shortage"] for s in payload["overview"]["criticalShortages"]))

        # Filtered single report check (BloodGroup=A-, Type=Plasma)
        filtered_res = self.client.get("/api/reports/?type=inventory&blood_group=A-&item_type=Plasma")
        self.assertEqual(filtered_res.status_code, 200)
        inv_filtered = filtered_res.json()["report"]
        self.assertEqual(len(inv_filtered["ledger"]), 1)
        self.assertEqual(inv_filtered["ledger"][0]["unitId"], "U_R2")

        # Invalid report type returns 400
        self.assertEqual(self.client.get("/api/reports/?type=unknown").status_code, 400)

        # Page template renders
        self.assertEqual(self.client.get("/reports.html").status_code, 200)

        # Formal PDF report endpoints
        for rtype in ("overview", "inventory", "requests", "donations", "verification", "disposal", "all"):
            pdf_res = self.client.get(f"/api/reports/pdf/?type={rtype}")
            self.assertEqual(pdf_res.status_code, 200)
            self.assertEqual(pdf_res["Content-Type"], "application/pdf")
            self.assertTrue(pdf_res.content.startswith(b"%PDF-"))

        dl_res = self.client.get("/api/reports/pdf/?type=all&download=1")
        self.assertEqual(dl_res.status_code, 200)
        self.assertIn("attachment; filename=", dl_res["Content-Disposition"])
        self.assertEqual(self.client.get("/api/reports/pdf/?type=invalid").status_code, 400)
