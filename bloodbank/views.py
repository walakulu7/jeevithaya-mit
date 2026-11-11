from datetime import date, timedelta
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
import json
from .models import (
    User, Donor, Patient, BloodRequest, Donation, 
    Inventory, Verification, Disposal
)
from .services import (
    InventoryService, RequestFulfillmentService,
    ExecutiveOverviewStrategy, InventoryReportStrategy,
    RequestReportStrategy, DonationReportStrategy,
    VerificationReportStrategy, DisposalReportStrategy,
    AnalyticsContext,
)
from .pdf_reports import REPORT_TITLES, generate_pdf_report

# Utility function to serialize model objects
def model_to_dict(obj):
    """Convert model instance to dictionary"""
    if obj is None:
        return None
    data = {}
    for field in obj._meta.fields:
        value = getattr(obj, field.name)
        if hasattr(value, 'isoformat'):  # Handle dates/datetimes
            data[field.name] = value.isoformat()
        else:
            data[field.name] = value
    return data


def normalize_payload(model_cls, data):
    """Normalize input dict keys to match model fields (case-insensitive & camelCase aliases)."""
    field_names = [f.name for f in model_cls._meta.fields]
    field_map = {f.name.lower(): f.name for f in model_cls._meta.fields}
    aliases = {
        'patientid': 'PatientID',
        'donorid': 'DonorID',
        'donationid': 'DonationID',
        'requestid': 'RequestID',
        'unitid': 'UnitID',
        'hospitalid': 'HospitalID',
        'bloodbankid': 'BloodBankID',
        'verificationid': 'VerificationID',
        'disposalid': 'DisposalID',
        'userid': 'UserID',
        'bloodgroup': 'BloodGroup',
        'dob': 'DateOfBirth',
        'dateofbirth': 'DateOfBirth',
        'contact': 'Contact',
        'contactno': 'ContactNo',
        'phone': 'Phone',
        'requestdate': 'RequestDate',
        'disposaldate': 'DisposalDate',
        'expirydate': 'ExpiryDate',
        'verifiedby': 'VerifiedBy',
        'disposedby': 'DisposedBy',
        'overallresult': 'OverallResult',
        'result': 'OverallResult',
        'comment': 'Notes',
        'notes': 'Notes',
        'qty': 'Quantity',
        'quantity': 'Quantity',
        'batchno': 'BatchNo',
        'hepatitisb': 'HepatitisB',
        'hepatitisc': 'HepatitisC',
    }
    normalized = {}
    for k, v in data.items():
        clean_k = k.lower().replace('_', '')
        target_field = aliases.get(clean_k) or field_map.get(clean_k)
        if target_field and target_field in field_names:
            if v == "" and target_field in ['Age', 'HospitalID', 'Quantity', 'BloodBankID', 'DateOfBirth']:
                v = None
            normalized[target_field] = v
    return normalized


# ============= AUTH API =============
DEFAULT_DEMO_USERS = [
    {
        "Name": "System Administrator",
        "Email": "admin@jeevithaya.com",
        "Role": "system_admin",
        "Password": "admin123"
    },
    {
        "Name": "Hospital Administrator",
        "Email": "hospital@jeevithaya.com",
        "Role": "hospital_admin",
        "Password": "hospital123",
        "HospitalID": 1
    },
    {
        "Name": "Front Office User",
        "Email": "frontoffice@jeevithaya.com",
        "Role": "frontoffice_user",
        "Password": "front123"
    },
    {
        "Name": "Lab Assistant",
        "Email": "lab@jeevithaya.com",
        "Role": "lab_assistant",
        "Password": "lab123"
    }
]

def ensure_demo_users():
    """Ensure baseline demo users exist in the database."""
    try:
        if not User.objects.exists():
            for u in DEFAULT_DEMO_USERS:
                User.objects.create(**u)
    except Exception:
        pass

@csrf_exempt
@require_http_methods(["POST"])
def api_auth_login(request):
    try:
        ensure_demo_users()
        data = json.loads(request.body)
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()
        role = (data.get('role') or '').strip()

        if not email or not password:
            return JsonResponse({'error': 'Email and password are required.'}, status=400)

        # Lookup user by email
        user = User.objects.filter(Email__iexact=email).first()
        if not user:
            return JsonResponse({'error': 'Invalid email or password.'}, status=401)

        # Validate password using encapsulated OOP method
        if not user.check_password(password):
            return JsonResponse({'error': 'Invalid email or password.'}, status=401)

        if getattr(user, 'Status', 'Active') == 'Inactive':
            return JsonResponse({'error': 'Account is inactive. Please contact an administrator.'}, status=403)

        # Store session
        user_dict = model_to_dict(user)
        user_dict.pop('Password', None)
        request.session['user_id'] = user.UserID
        request.session['user_role'] = user.Role
        request.session['user_email'] = user.Email
        request.session['user_name'] = user.Name
        request.session.modified = True

        return JsonResponse({
            'message': 'Login successful',
            'user': user_dict
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_auth_logout(request):
    request.session.flush()
    return JsonResponse({'message': 'Logged out successfully'})

@require_http_methods(["GET"])
def api_auth_me(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)
    try:
        user = User.objects.get(UserID=user_id)
        user_dict = model_to_dict(user)
        user_dict.pop('Password', None)
        return JsonResponse({'user': user_dict})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


# ============= USER API =============
def serialize_user(user):
    data = model_to_dict(user)
    data.pop('Password', None)
    return data


@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_users(request):
    if request.method == 'GET':
        users = User.objects.all()
        return JsonResponse([serialize_user(user) for user in users], safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(User, data)
            raw_password = normalized.pop('Password', '')
            user = User(**normalized)
            if raw_password:
                user.set_password(raw_password)
            user.save()
            return JsonResponse(serialize_user(user), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_user_detail(request, user_id):
    try:
        user = User.objects.get(UserID=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(serialize_user(user))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(User, data)
            raw_password = normalized.pop('Password', None)
            for key, value in normalized.items():
                setattr(user, key, value)
            if raw_password:
                user.set_password(raw_password)
            user.save()
            return JsonResponse(serialize_user(user))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        user.delete()
        return JsonResponse({'message': 'User deleted'}, status=204)


# ============= DONOR API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_donors(request):
    if request.method == 'GET':
        donors = Donor.objects.all()
        data = [model_to_dict(donor) for donor in donors]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Donor, data)
            donor = Donor.objects.create(**normalized)
            return JsonResponse(model_to_dict(donor), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_donor_detail(request, donor_id):
    try:
        donor = Donor.objects.get(DonorID=donor_id)
    except Donor.DoesNotExist:
        return JsonResponse({'error': 'Donor not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(donor))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Donor, data)
            for key, value in normalized.items():
                setattr(donor, key, value)
            donor.save()
            return JsonResponse(model_to_dict(donor))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        donor.delete()
        return JsonResponse({'message': 'Donor deleted'}, status=204)


# ============= PATIENT API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_patients(request):
    if request.method == 'GET':
        patients = Patient.objects.all()
        data = [model_to_dict(patient) for patient in patients]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Patient, data)
            patient = Patient.objects.create(**normalized)
            return JsonResponse(model_to_dict(patient), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_patient_detail(request, patient_id):
    try:
        patient = Patient.objects.get(PatientID=patient_id)
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(patient))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Patient, data)
            for key, value in normalized.items():
                setattr(patient, key, value)
            patient.save()
            return JsonResponse(model_to_dict(patient))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        patient.delete()
        return JsonResponse({'message': 'Patient deleted'}, status=204)


# ============= BLOOD REQUEST API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_requests(request):
    if request.method == 'GET':
        requests = BloodRequest.objects.all()
        data = [model_to_dict(req) for req in requests]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(BloodRequest, data)
            request_obj = BloodRequest.objects.create(**normalized)
            return JsonResponse(model_to_dict(request_obj), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_request_detail(request, request_id):
    try:
        request_obj = BloodRequest.objects.get(RequestID=request_id)
    except BloodRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(request_obj))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(BloodRequest, data)
            for key, value in normalized.items():
                setattr(request_obj, key, value)
            request_obj.save()
            return JsonResponse(model_to_dict(request_obj))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        request_obj.delete()
        return JsonResponse({'message': 'Request deleted'}, status=204)


# ============= DONATION API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_donations(request):
    if request.method == 'GET':
        donations = Donation.objects.all()
        data = [model_to_dict(donation) for donation in donations]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Donation, data)
            donation = Donation.objects.create(**normalized)
            return JsonResponse(model_to_dict(donation), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_donation_detail(request, donation_id):
    try:
        donation = Donation.objects.get(DonationID=donation_id)
    except Donation.DoesNotExist:
        return JsonResponse({'error': 'Donation not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(donation))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Donation, data)
            for key, value in normalized.items():
                setattr(donation, key, value)
            donation.save()
            return JsonResponse(model_to_dict(donation))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        donation.delete()
        return JsonResponse({'message': 'Donation deleted'}, status=204)


# ============= INVENTORY API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_inventory(request):
    if request.method == 'GET':
        inventory = Inventory.objects.all()
        data = [model_to_dict(item) for item in inventory]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Inventory, data)
            item = Inventory.objects.create(**normalized)
            return JsonResponse(model_to_dict(item), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_inventory_detail(request, unit_id):
    try:
        item = Inventory.objects.get(UnitID=unit_id)
    except Inventory.DoesNotExist:
        return JsonResponse({'error': 'Inventory item not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(item))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Inventory, data)
            for key, value in normalized.items():
                setattr(item, key, value)
            item.save()
            return JsonResponse(model_to_dict(item))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        item.delete()
        return JsonResponse({'message': 'Inventory item deleted'}, status=204)


# ============= VERIFICATION API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_verifications(request):
    if request.method == 'GET':
        verifications = Verification.objects.all()
        data = [model_to_dict(ver) for ver in verifications]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Verification, data)
            overall = normalized.get('OverallResult') or 'Passed'
            if overall in ['Pass', 'pass']:
                overall = 'Passed'
            elif overall in ['Fail', 'fail']:
                overall = 'Failed'
            normalized['OverallResult'] = overall
            for test in ['HIV', 'HepatitisB', 'HepatitisC', 'Syphilis']:
                if test not in normalized or not normalized[test]:
                    normalized[test] = overall
            verification = Verification.objects.create(**normalized)

            # Trigger OOP domain service to update inventory / disposal
            try:
                InventoryService().process_verification_result(
                    unit_id=verification.UnitID,
                    donor_id=verification.DonorID,
                    result=verification.OverallResult,
                    verified_by=verification.VerifiedBy,
                    notes=verification.Notes or ""
                )
            except Exception as service_err:
                print(f"[Verification Service Error]: {service_err}")

            return JsonResponse(model_to_dict(verification), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_verification_detail(request, verification_id):
    try:
        verification = Verification.objects.get(VerificationID=verification_id)
    except Verification.DoesNotExist:
        return JsonResponse({'error': 'Verification not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(verification))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Verification, data)
            for key, value in normalized.items():
                setattr(verification, key, value)
            verification.save()
            return JsonResponse(model_to_dict(verification))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        verification.delete()
        return JsonResponse({'message': 'Verification deleted'}, status=204)


# ============= DISPOSAL API =============
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_disposals(request):
    if request.method == 'GET':
        disposals = Disposal.objects.all()
        data = [model_to_dict(disp) for disp in disposals]
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Disposal, data)
            disposal = Disposal.objects.create(**normalized)
            return JsonResponse(model_to_dict(disposal), status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_disposal_detail(request, disposal_id):
    try:
        disposal = Disposal.objects.get(DisposalID=disposal_id)
    except Disposal.DoesNotExist:
        return JsonResponse({'error': 'Disposal not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse(model_to_dict(disposal))
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            normalized = normalize_payload(Disposal, data)
            for key, value in normalized.items():
                setattr(disposal, key, value)
            disposal.save()
            return JsonResponse(model_to_dict(disposal))
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        disposal.delete()
        return JsonResponse({'message': 'Disposal deleted'}, status=204)


# ============= DASHBOARD STATS API =============
@require_http_methods(["GET"])
def api_dashboard_stats(request):
    """Get dashboard statistics"""
    stats = {
        'donorCount': Donor.objects.count(),
        'requestCount': BloodRequest.objects.filter(
            Status__in=['Pending', 'Approved']
        ).count(),
        'unitCount': Inventory.objects.filter(
            Status='Available'
        ).aggregate(total=Sum('Quantity'))['total'] or 0,
        'urgentCount': BloodRequest.objects.filter(
            Urgency__in=['Urgent', 'Critical'],
            Status__in=['Pending', 'Approved']
        ).count(),
    }
    return JsonResponse(stats)


# ============= PROFESSIONAL REPORTS API =============
REPORT_STRATEGY_MAP = {
    'overview': ExecutiveOverviewStrategy,
    'inventory': InventoryReportStrategy,
    'requests': RequestReportStrategy,
    'donations': DonationReportStrategy,
    'donors': DonationReportStrategy,
    'verification': VerificationReportStrategy,
    'disposal': DisposalReportStrategy,
}


def _extract_report_filters(request):
    return {
        'days': request.GET.get('days', 'all'),
        'start_date': request.GET.get('from') or request.GET.get('start_date'),
        'end_date': request.GET.get('to') or request.GET.get('end_date'),
        'blood_group': request.GET.get('blood_group', ''),
        'item_type': request.GET.get('item_type', ''),
    }


@require_http_methods(["GET"])
def api_reports(request):
    """Return analytical reports dispatched polymorphically via AnalyticsContext."""
    report_type = (request.GET.get('type') or 'all').strip().lower()
    filters = _extract_report_filters(request)

    if report_type == 'all':
        bundle = {}
        context = AnalyticsContext(ExecutiveOverviewStrategy())
        for key in ('overview', 'inventory', 'requests', 'donations', 'verification', 'disposal'):
            context.set_strategy(REPORT_STRATEGY_MAP[key]())
            bundle[key] = context.execute(filters=filters)
        return JsonResponse({
            'filters': filters,
            'reports': bundle,
        })

    strategy_cls = REPORT_STRATEGY_MAP.get(report_type)
    if not strategy_cls:
        return JsonResponse({'error': f'Unsupported report type: {report_type}'}, status=400)

    context = AnalyticsContext(strategy_cls())
    return JsonResponse({
        'filters': filters,
        'type': report_type,
        'report': context.execute(filters=filters),
    })


@require_http_methods(["GET"])
def api_reports_pdf(request):
    """Generate and serve a formal multi-page PDF document for the requested report."""
    report_type = (request.GET.get('type') or 'overview').strip().lower()
    if report_type not in REPORT_TITLES and report_type != 'donors':
        return JsonResponse({'error': f'Unsupported PDF report type: {report_type}'}, status=400)

    normalized_type = 'donations' if report_type == 'donors' else report_type
    filters = _extract_report_filters(request)
    prepared_by = (
        request.GET.get('prepared_by')
        or request.session.get('user_name')
        or request.session.get('user_email')
        or 'System Administrator'
    )

    pdf_bytes, filename = generate_pdf_report(
        report_type=normalized_type,
        filters=filters,
        prepared_by=prepared_by,
    )
    disposition = 'attachment' if request.GET.get('download') in ('1', 'true', 'yes') else 'inline'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


# ============= NOTIFICATIONS API =============
@require_http_methods(["GET"])
def api_notifications(request):
    """Build real-time operational alerts for requests, expiry, shortages, and QC."""
    today = date.today()
    notifications = []

    urgent_reqs = BloodRequest.objects.filter(
        Urgency__in=['Critical', 'Urgent'],
        Status__in=['Pending', 'Approved'],
    ).order_by('-RequestDate')[:5]
    for r in urgent_reqs:
        notifications.append({
            'id': f"req-{r.RequestID}-{r.Status}",
            'title': f"{r.Urgency} Blood Request ({r.RequestID})",
            'message': f"{r.BloodGroup} {r.Type} x{r.Quantity} needed for Hospital #{r.HospitalID} ({r.Status}).",
            'severity': 'danger' if r.Urgency == 'Critical' else 'warn',
            'link': 'requests.html',
            'timestamp': r.RequestDate.isoformat(),
        })

    # Pending non-urgent open requests summary
    other_pending = BloodRequest.objects.filter(
        Urgency='Normal',
        Status='Pending',
    ).count()
    if other_pending > 0:
        notifications.append({
            'id': f"req-pending-normal-{other_pending}",
            'title': f"{other_pending} Pending Request{'s' if other_pending > 1 else ''}",
            'message': "Standard hospital requisitions awaiting review and fulfillment.",
            'severity': 'info',
            'link': 'requests.html',
            'timestamp': today.isoformat(),
        })

    # Expiring within 7 days & already expired units
    expiring_soon = Inventory.objects.filter(
        Status='Available',
        ExpiryDate__gte=today,
        ExpiryDate__lte=today + timedelta(days=7),
    ).order_by('ExpiryDate')[:5]
    for u in expiring_soon:
        days_left = (u.ExpiryDate - today).days
        notifications.append({
            'id': f"exp-soon-{u.UnitID}-{u.ExpiryDate.isoformat()}",
            'title': f"Expiring Soon: {u.UnitID} ({u.BloodGroup})",
            'message': f"Batch {u.BatchNo} ({u.Quantity}u {u.Type}) expires in {days_left} day{'s' if days_left != 1 else ''}.",
            'severity': 'warn',
            'link': 'inventory.html',
            'timestamp': u.ExpiryDate.isoformat(),
        })

    expired_units = Inventory.objects.filter(
        Status__in=['Available', 'Reserved'],
        ExpiryDate__lt=today,
    )[:5]
    for u in expired_units:
        notifications.append({
            'id': f"expired-{u.UnitID}-{u.ExpiryDate.isoformat()}",
            'title': f"Expired Unit in Stock: {u.UnitID}",
            'message': f"{u.BloodGroup} {u.Type} expired on {u.ExpiryDate.isoformat()} — dispose or mark expired.",
            'severity': 'danger',
            'link': 'disposal.html',
            'timestamp': u.ExpiryDate.isoformat(),
        })

    # Blood group shortage alerts (pending/approved demand > available safe stock)
    overview = ExecutiveOverviewStrategy().generate()
    for s in overview.get('criticalShortages', []):
        notifications.append({
            'id': f"shortage-{s['bloodGroup']}-{s['available']}-{s['pendingDemand']}",
            'title': f"Stock Shortage: {s['bloodGroup']}",
            'message': f"Only {s['available']} unit(s) available vs. {s['pendingDemand']} requested.",
            'severity': 'danger',
            'link': 'reports.html?tab=overview',
            'timestamp': today.isoformat(),
        })

    # Failed serological verifications
    failed_verifs = Verification.objects.filter(
        OverallResult='Failed'
    ).order_by('-Date')[:3]
    for v in failed_verifs:
        notifications.append({
            'id': f"verif-fail-{v.VerificationID}",
            'title': f"Failed QC Screening ({v.UnitID})",
            'message': f"Verification {v.VerificationID} flagged Failed by {v.VerifiedBy}.",
            'severity': 'warn',
            'link': 'verification.html',
            'timestamp': v.Date.isoformat(),
        })

    return JsonResponse({
        'count': len(notifications),
        'notifications': notifications,
    })
