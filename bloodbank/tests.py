import json
from datetime import date, timedelta

from django.test import TestCase, Client

from bloodbank import container
from bloodbank.models import (
    User, Donor, Patient, BloodRequest, Donation, Inventory, Verification, Disposal,
    InvalidTransition,
)
from bloodbank.services import (
    InventoryService, RequestFulfillmentService, BaseService,
    InventoryReportStrategy, DonationReportStrategy, RequestReportStrategy,
    AnalyticsContext,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
def make_user(role, email=None, password="secret123", status="Active"):
    user = User(Name=f"Test {role}", Email=email or f"{role}@test.com", Role=role, Status=status)
    user.set_password(password)
    user.save()
    return user


def make_donor(donor_id="D1", group="O+"):
    return Donor.objects.get_or_create(
        DonorID=donor_id, defaults=dict(Name=f"Donor {donor_id}", BloodGroup=group, Phone="0770000000")
    )[0]


def make_unit(unit_id, group="O+", comp="Blood", days=20, status="Available", qty=1, donor_id="D1"):
    donor = make_donor(donor_id, group)
    donation = Donation.objects.get_or_create(
        DonationID=f"DN-{unit_id}",
        defaults=dict(donor=donor, Date=date.today(), BloodGroup=group, Type=comp, Quantity=qty, BloodBankID=1),
    )[0]
    return Inventory.objects.create(
        UnitID=unit_id, donation=donation, donor=donor, BloodBankID=1, BloodGroup=group, Type=comp,
        Quantity=qty, BatchNo="B1", ExpiryDate=date.today() + timedelta(days=days), Status=status,
    )


def make_patient(patient_id="P1", group="O+"):
    return Patient.objects.get_or_create(
        PatientID=patient_id,
        defaults=dict(HospitalID=1, Name=f"Patient {patient_id}", BloodGroup=group, Type="Blood",
                      Urgency="Normal", Contact="0711111111"),
    )[0]


def make_request(request_id="REQ1", qty=1, status="Approved", group="O+"):
    return BloodRequest.objects.create(
        RequestID=request_id, patient=make_patient(group=group), HospitalID=1, RequestDate=date.today(),
        BloodGroup=group, Type="Blood", Quantity=qty, Urgency="Normal", Status=status,
    )


class ApiTestCase(TestCase):
    """Base class: a client logged in with a chosen role."""
    role = User.SYSTEM_ADMIN

    def setUp(self):
        self.user = make_user(self.role)
        self.client = Client()
        self.login(self.user)

    def login(self, user, password="secret123"):
        res = self.client.post("/api/auth/login/", json.dumps({"email": user.Email, "password": password}),
                               content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def put(self, url, data):
        return self.client.put(url, json.dumps(data), content_type="application/json")


# ----------------------------------------------------------------------
# OOP: inheritance, encapsulation, lifecycle
# ----------------------------------------------------------------------
class OOPModelTests(TestCase):

    def test_inheritance_and_age_calculation(self):
        birth_date = date.today() - timedelta(days=365.25 * 25)
        donor = Donor.objects.create(DonorID="D_TEST1", Name="Test Donor", BloodGroup="O+",
                                     Phone="0771234567", DateOfBirth=birth_date)
        self.assertEqual(donor.calculate_age, 25)
        self.assertTrue(donor.is_eligible())

    def test_every_model_inherits_audit_fields(self):
        for model in (User, Donor, Patient, BloodRequest, Donation, Inventory, Verification, Disposal):
            names = {f.name for f in model._meta.fields}
            self.assertTrue({"CreatedAt", "UpdatedAt"} <= names, model.__name__)

    def test_password_is_hashed_and_plaintext_rejected(self):
        user = User.objects.create(Name="Admin", Email="a@example.com", Role=User.SYSTEM_ADMIN)
        user.set_password("Secret123!")
        user.save()
        self.assertNotEqual(user.Password, "Secret123!")
        self.assertTrue(user.check_password("Secret123!"))
        self.assertFalse(user.check_password("WrongPassword"))

        legacy = User.objects.create(Name="Legacy", Email="l@example.com", Role=User.SYSTEM_ADMIN, Password="plain")
        self.assertFalse(legacy.check_password("plain"))

    def test_inventory_expiry(self):
        self.assertFalse(make_unit("U_VAL", days=10).is_expired())
        self.assertTrue(make_unit("U_EXP", days=-2).is_expired())

    def test_verification_safety_rule(self):
        unit = make_unit("U1")
        fields = dict(unit=unit, donor=unit.donor, VerifiedBy="Doctor", Date=date.today(),
                      HIV="Passed", HepatitisC="Passed", Syphilis="Passed")
        self.assertTrue(Verification(VerificationID="V1", HepatitisB="Passed", OverallResult="Passed", **fields).is_safe())
        self.assertFalse(Verification(VerificationID="V2", HepatitisB="Failed", OverallResult="Failed", **fields).is_safe())

    def test_request_lifecycle_is_enforced(self):
        req = make_request(status="Pending")
        with self.assertRaises(InvalidTransition):
            req.fulfill()  # must be approved first
        req.approve()
        req.reject()
        req.reopen()
        self.assertEqual(req.Status, "Pending")

    def test_unit_lifecycle_is_enforced(self):
        unit = make_unit("U_LIFE")
        unit.mark_issued()
        with self.assertRaises(InvalidTransition):
            unit.mark_available()  # issued is final

    def test_relations_navigate_between_objects(self):
        unit = make_unit("U_NAV", donor_id="D_NAV")
        self.assertEqual(unit.donation.donor, unit.donor)
        self.assertIn(unit, unit.donor.units.all())


# ----------------------------------------------------------------------
# Services, polymorphism, dependency inversion
# ----------------------------------------------------------------------
class OOPServiceAndPolymorphismTests(TestCase):

    def test_polymorphic_reporting_strategies(self):
        context = AnalyticsContext(InventoryReportStrategy())
        self.assertIn("total_available_units", context.execute())
        context.set_strategy(DonationReportStrategy())
        self.assertIn("total_donations", context.execute())
        context.set_strategy(RequestReportStrategy())
        self.assertIn("total_requests", context.execute())

    def test_expired_count_excludes_units_no_longer_in_storage(self):
        make_unit("U_EXP_HELD", days=-3, status="Expired")
        make_unit("U_EXP_STALE", days=-3, status="Available")
        make_unit("U_EXP_GONE", days=-3, status="Discarded")
        make_unit("U_EXP_SENT", days=-3, status="Issued")
        report = InventoryReportStrategy().generate()
        self.assertEqual(report["summary"]["expiredRecords"], 2)
        o_pos = next(r for r in report["componentMatrix"] if r["bloodGroup"] == "O+")
        self.assertEqual(o_pos["expiredUnits"], 2)

    def test_base_service_is_abstract_and_shared(self):
        with self.assertRaises(TypeError):
            BaseService()
        make_unit("U_SVC")
        self.assertEqual(InventoryService().get("U_SVC").UnitID, "U_SVC")

    def test_failed_verification_discards_unit_with_unique_disposal_ids(self):
        service = InventoryService()
        ids = []
        for unit_id in ("UA0001", "UB0001"):  # same last 4 characters
            unit = make_unit(unit_id, status="Reserved")
            ver = Verification.objects.create(
                VerificationID=f"V-{unit_id}", unit=unit, donor=unit.donor, VerifiedBy="Lab", Date=date.today(),
                HIV="Passed", HepatitisB="Failed", HepatitisC="Passed", Syphilis="Passed", OverallResult="Failed",
            )
            ids.append(service.process_verification_result(ver).DisposalID)
            unit.refresh_from_db()
            self.assertEqual(unit.Status, "Discarded")
        self.assertEqual(len(set(ids)), 2)

    def test_fulfilment_uses_injected_inventory_service(self):
        class FakeInventory(InventoryService):
            calls = 0

            def get_available_units(self, *args, **kwargs):
                FakeInventory.calls += 1
                return super().get_available_units(*args, **kwargs)

        make_unit("U_DI")
        req = make_request()
        RequestFulfillmentService(inventory_service=FakeInventory()).fulfill_request(req.RequestID)
        self.assertEqual(FakeInventory.calls, 1)


# ----------------------------------------------------------------------
# Security: authentication, roles, CSRF, page access
# ----------------------------------------------------------------------
class SecurityTests(TestCase):

    def test_api_requires_login(self):
        c = Client()
        for url in ("/api/users/", "/api/donors/", "/api/inventory/", "/api/reports/", "/api/dashboard/stats/"):
            self.assertEqual(c.get(url).status_code, 401, url)

    def test_pages_redirect_to_login(self):
        res = Client().get("/dashboard.html")
        self.assertEqual(res.status_code, 302)
        self.assertIn("login.html", res["Location"])
        self.assertEqual(Client().get("/login.html").status_code, 200)

    def test_roles_are_enforced_on_api_and_pages(self):
        make_user(User.FRONT_OFFICE, email="fo@test.com")
        c = Client()
        c.post("/api/auth/login/", json.dumps({"email": "fo@test.com", "password": "secret123"}),
               content_type="application/json")
        self.assertEqual(c.get("/api/donors/").status_code, 200)
        for url in ("/api/users/", "/api/inventory/", "/api/donations/", "/api/reports/"):
            self.assertEqual(c.get(url).status_code, 403, url)
        self.assertEqual(c.get("/create_user.html").status_code, 302)

    def test_csrf_token_required_for_writes(self):
        make_user(User.SYSTEM_ADMIN, email="admin@test.com")
        c = Client(enforce_csrf_checks=True)
        c.get("/login.html")  # sets the csrftoken cookie
        token = c.cookies["csrftoken"].value
        body = json.dumps({"email": "admin@test.com", "password": "secret123"})
        self.assertEqual(c.post("/api/auth/login/", body, content_type="application/json").status_code, 403)
        self.assertEqual(c.post("/api/auth/login/", body, content_type="application/json",
                                HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_inactive_user_session_is_rejected(self):
        user = make_user(User.SYSTEM_ADMIN, email="x@test.com")
        c = Client()
        c.post("/api/auth/login/", json.dumps({"email": "x@test.com", "password": "secret123"}),
               content_type="application/json")
        User.objects.filter(pk=user.pk).update(Status="Inactive")
        self.assertEqual(c.get("/api/donors/").status_code, 401)


# ----------------------------------------------------------------------
# REST API behaviour
# ----------------------------------------------------------------------
class RESTAPITests(ApiTestCase):

    def test_donor_api_crud(self):
        res = self.post("/api/donors/", {"DonorID": "D_API_01", "Name": "API Donor", "BloodGroup": "AB+",
                                         "Phone": "0770001111", "Status": "Eligible"})
        self.assertEqual(res.status_code, 201)
        donors = self.client.get("/api/donors/").json()
        self.assertTrue(any(d['DonorID'] == "D_API_01" for d in donors))

    def test_invalid_input_returns_readable_error(self):
        res = self.post("/api/donors/", {"DonorID": "D_BAD", "Name": "X", "BloodGroup": "Z+", "Phone": "1"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("BloodGroup", res.json()["error"])

    def test_references_must_exist(self):
        res = self.post("/api/inventory/", {"UnitID": "U_X", "DonationID": "DN_NONE", "DonorID": "D_NONE",
                                            "BloodBankID": 1, "BloodGroup": "O+", "Type": "Blood", "Quantity": 1,
                                            "BatchNo": "B", "ExpiryDate": "2030-01-01", "Status": "Available"})
        self.assertEqual(res.status_code, 400)

    def test_cannot_delete_donor_with_linked_records(self):
        make_unit("U_LINK", donor_id="D_LINK")
        res = self.client.delete("/api/donors/D_LINK/")
        self.assertEqual(res.status_code, 409)
        self.assertTrue(Donor.objects.filter(pk="D_LINK").exists())

    def test_relation_ids_keep_their_api_names(self):
        make_unit("U_JSON", donor_id="D_JSON")
        row = self.client.get("/api/inventory/U_JSON/").json()
        self.assertEqual(row["DonorID"], "D_JSON")
        self.assertEqual(row["DonationID"], "DN-U_JSON")

    def test_dashboard_stats_api(self):
        data = self.client.get("/api/dashboard/stats/").json()
        for key in ("donorCount", "unitCount", "requestCount"):
            self.assertIn(key, data)

    def test_failed_verification_via_api_creates_disposal(self):
        make_unit("U_V")
        res = self.post("/api/verifications/", {"VerificationID": "V_API", "UnitID": "U_V", "VerifiedBy": "Lab",
                                                "Date": str(date.today()), "OverallResult": "Fail", "Notes": "HBV"})
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["DonorID"], "D1")  # filled in from the unit
        self.assertEqual(Inventory.objects.get(pk="U_V").Status, "Discarded")
        self.assertTrue(Disposal.objects.filter(unit_id="U_V").exists())

    def test_inventory_status_change_follows_lifecycle(self):
        make_unit("U_ST")
        self.assertEqual(self.put("/api/inventory/U_ST/", {"Status": "Issued"}).status_code, 200)
        self.assertEqual(self.put("/api/inventory/U_ST/", {"Status": "Available"}).status_code, 409)

    def test_user_management_and_inactive_login(self):
        created = self.post("/api/users/", {"Name": "Nurse Jane", "Email": "jane@jeevithaya.com",
                                            "Role": "lab_assistant", "Password": "Password123!"})
        self.assertEqual(created.status_code, 201)
        user_id = created.json()["UserID"]
        self.assertNotIn("Password", created.json())

        updated = self.put(f"/api/users/{user_id}/", {"Name": "Nurse Jane Updated", "Role": "frontoffice_user",
                                                      "Status": "Inactive"}).json()
        self.assertEqual((updated["Role"], updated["Status"]), ("frontoffice_user", "Inactive"))

        other = Client()
        body = json.dumps({"email": "jane@jeevithaya.com", "password": "Password123!"})
        self.assertEqual(other.post("/api/auth/login/", body, content_type="application/json").status_code, 403)
        self.put(f"/api/users/{user_id}/", {"Status": "Active"})
        self.assertEqual(other.post("/api/auth/login/", body, content_type="application/json").status_code, 200)

        self.assertEqual(self.client.delete(f"/api/users/{user_id}/").status_code, 204)
        self.assertFalse(User.objects.filter(UserID=user_id).exists())
        self.assertEqual(self.client.delete(f"/api/users/{self.user.pk}/").status_code, 400)  # not yourself

    def test_professional_reports_api_and_strategies(self):
        alice = Donor.objects.create(DonorID="D_R1", Name="Alice", BloodGroup="O+", Phone="0771112222", Status="Eligible")
        Donor.objects.create(DonorID="D_R2", Name="Bob", BloodGroup="A-", Phone="0773334444", Status="Not Eligible")
        patient = Patient.objects.create(PatientID="P_R1", HospitalID=1, Name="Charlie", BloodGroup="O+", Type="Blood",
                                         Urgency="Critical", Contact="0711112222")
        dn = Donation.objects.create(DonationID="DN_R1", donor=alice, Date=date.today(), BloodGroup="O+", Type="Blood",
                                     Quantity=2, BloodBankID=1, Status="Completed")
        common = dict(donation=dn, donor=alice, BloodBankID=1)
        u1 = Inventory.objects.create(UnitID="U_R1", BloodGroup="O+", Type="Blood", Quantity=2, BatchNo="B-1",
                                      ExpiryDate=date.today() + timedelta(days=5), Status="Available", **common)
        Inventory.objects.create(UnitID="U_R2", BloodGroup="A-", Type="Plasma", Quantity=1, BatchNo="B-2",
                                 ExpiryDate=date.today() + timedelta(days=45), Status="Available", **common)
        u3 = Inventory.objects.create(UnitID="U_R3", BloodGroup="O+", Type="Blood", Quantity=1, BatchNo="B-3",
                                      ExpiryDate=date.today() - timedelta(days=1), Status="Expired", **common)
        BloodRequest.objects.create(RequestID="REQ_R1", patient=patient, HospitalID=1, RequestDate=date.today(),
                                    BloodGroup="O+", Type="Blood", Quantity=3, Urgency="Critical", Status="Pending")
        markers = dict(HIV="Passed", HepatitisC="Passed", Syphilis="Passed")
        Verification.objects.create(VerificationID="VER_R1", unit=u1, donor=alice, VerifiedBy="Senior Lab Officer",
                                    Date=date.today(), HepatitisB="Passed", OverallResult="Passed", **markers)
        Verification.objects.create(VerificationID="VER_R2", unit=u3, donor=alice, VerifiedBy="Lab Assistant",
                                    Date=date.today(), HepatitisB="Failed", OverallResult="Failed", Notes="Reactive HBV", **markers)
        Disposal.objects.create(DisposalID="DISP_R1", unit=u3, DisposalDate=date.today(), Reason="Expired",
                                DisposedBy="Senior Lab Officer", Notes="Auto expired")

        payload = self.client.get("/api/reports/?type=all").json()["reports"]
        self.assertEqual(set(payload.keys()), {"overview", "inventory", "requests", "donations", "verification", "disposal"})
        self.assertEqual(payload["inventory"]["summary"]["expiringSoonUnits"], 2)
        self.assertEqual(payload["inventory"]["summary"]["expiredUnits"], 1)
        self.assertEqual(payload["requests"]["summary"]["criticalRequests"], 1)
        self.assertEqual(payload["requests"]["ledger"][0]["patientName"], "Charlie")
        self.assertEqual(payload["donations"]["summary"]["eligibleDonors"], 1)
        self.assertEqual(payload["verification"]["summary"]["failedCount"], 1)
        self.assertEqual(payload["disposal"]["summary"]["expiredReasonCount"], 1)
        self.assertTrue(any(s["bloodGroup"] == "O+" and s["shortage"] for s in payload["overview"]["criticalShortages"]))

        inv_filtered = self.client.get("/api/reports/?type=inventory&blood_group=A-&item_type=Plasma").json()["report"]
        self.assertEqual([row["unitId"] for row in inv_filtered["ledger"]], ["U_R2"])
        self.assertEqual(self.client.get("/api/reports/?type=unknown").status_code, 400)
        self.assertEqual(self.client.get("/reports.html").status_code, 200)

        for rtype in ("overview", "inventory", "requests", "donations", "verification", "disposal", "all"):
            pdf_res = self.client.get(f"/api/reports/pdf/?type={rtype}")
            self.assertEqual(pdf_res.status_code, 200)
            self.assertTrue(pdf_res.content.startswith(b"%PDF-"))
        self.assertIn("attachment; filename=", self.client.get("/api/reports/pdf/?type=all&download=1")["Content-Disposition"])
        self.assertEqual(self.client.get("/api/reports/pdf/?type=invalid").status_code, 400)

        notif = self.client.get("/api/notifications/").json()
        self.assertEqual(notif["count"], len(notif["notifications"]))
        self.assertGreaterEqual(notif["count"], 4)


class ProfileSelfServiceTests(ApiTestCase):
    role = User.FRONT_OFFICE

    def test_user_can_edit_own_name_and_password_only(self):
        url = f"/api/users/{self.user.pk}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.put(url, {"Name": "New Name", "Password": "newpass1"}).status_code, 200)
        self.assertEqual(self.put(url, {"Role": User.SYSTEM_ADMIN}).status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.Role, User.FRONT_OFFICE)
        self.assertTrue(self.user.check_password("newpass1"))

    def test_user_cannot_read_other_users(self):
        other = make_user(User.LAB_ASSISTANT, email="other@test.com")
        self.assertEqual(self.client.get(f"/api/users/{other.pk}/").status_code, 403)


# ----------------------------------------------------------------------
# Request workflow: approval and automatic stock issue
# ----------------------------------------------------------------------
class RequestFulfillmentApiTests(ApiTestCase):

    def setUp(self):
        super().setUp()
        for i, days in enumerate([30, 5, 60]):
            make_unit(f"U_F{i}", days=days)
        make_request("REQ_F1", qty=2, status="Approved")

    def test_fulfill_issues_units_closest_to_expiry(self):
        res = self.put("/api/requests/REQ_F1/", {"Status": "Fulfilled"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(sorted(res.json()["units_issued"]), ["U_F0", "U_F1"])
        self.assertEqual(BloodRequest.objects.get(pk="REQ_F1").Status, "Fulfilled")
        self.assertEqual(Inventory.objects.get(pk="U_F2").Status, "Available")

    def test_fulfill_refused_when_stock_short(self):
        BloodRequest.objects.filter(pk="REQ_F1").update(Quantity=5)
        res = self.put("/api/requests/REQ_F1/", {"Status": "Fulfilled"})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(BloodRequest.objects.get(pk="REQ_F1").Status, "Approved")
        self.assertEqual(Inventory.objects.filter(Status="Issued").count(), 0)

    def test_fulfilled_is_final(self):
        self.put("/api/requests/REQ_F1/", {"Status": "Fulfilled"})
        self.assertEqual(self.put("/api/requests/REQ_F1/", {"Status": "Pending"}).status_code, 409)
        self.assertEqual(Inventory.objects.filter(Status="Issued").count(), 2)

    def test_pending_request_must_be_approved_before_fulfilment(self):
        make_request("REQ_P", status="Pending")
        self.assertEqual(self.put("/api/requests/REQ_P/", {"Status": "Fulfilled"}).status_code, 409)

    def test_front_office_can_raise_but_not_approve(self):
        make_user(User.FRONT_OFFICE, email="fo2@test.com")
        fo = Client()
        fo.post("/api/auth/login/", json.dumps({"email": "fo2@test.com", "password": "secret123"}),
                content_type="application/json")
        new = {"RequestID": "REQ_FO", "PatientID": "P1", "HospitalID": 1, "RequestDate": str(date.today()),
               "BloodGroup": "O+", "Type": "Blood", "Quantity": 1, "Urgency": "Normal", "Status": "Pending"}
        self.assertEqual(fo.post("/api/requests/", json.dumps(new), content_type="application/json").status_code, 201)
        res = fo.put("/api/requests/REQ_FO/", json.dumps({"Status": "Approved"}), content_type="application/json")
        self.assertEqual(res.status_code, 403)

    def test_service_container_can_be_swapped(self):
        original = container.services

        class RefusingRequests(RequestFulfillmentService):
            def change_status(self, request_obj, new_status):
                return {"success": False, "message": "Blocked by test double"}

        container.services = container.ServiceContainer(requests=RefusingRequests())
        try:
            res = self.put("/api/requests/REQ_F1/", {"Status": "Fulfilled"})
            self.assertEqual(res.json()["error"], "Blocked by test double")
        finally:
            container.services = original
