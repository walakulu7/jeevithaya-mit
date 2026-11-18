"""Dashboard statistics, analytical reports, PDF exports and live alerts."""

from datetime import date, timedelta

from django.db.models import Sum
from django.http import HttpResponse, JsonResponse

from ..models import Donor, BloodRequest, Inventory, Verification
from ..services import (
    ExecutiveOverviewStrategy, InventoryReportStrategy,
    RequestReportStrategy, DonationReportStrategy,
    VerificationReportStrategy, DisposalReportStrategy,
    AnalyticsContext,
)
from ..pdf_reports import REPORT_TITLES, generate_pdf_report
from .common import api_view, ADMIN_ROLES


# ============= DASHBOARD STATS API =============
@api_view(["GET"], roles=None)
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


@api_view(["GET"], roles=ADMIN_ROLES)
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


@api_view(["GET"], roles=ADMIN_ROLES)
def api_reports_pdf(request):
    """Generate and serve a formal multi-page PDF document for the requested report."""
    report_type = (request.GET.get('type') or 'overview').strip().lower()
    if report_type not in REPORT_TITLES and report_type != 'donors':
        return JsonResponse({'error': f'Unsupported PDF report type: {report_type}'}, status=400)

    normalized_type = 'donations' if report_type == 'donors' else report_type
    filters = _extract_report_filters(request)
    prepared_by = (
        request.current_user.Name
        or request.current_user.Email
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
@api_view(["GET"], roles=None)
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
            'title': f"Failed QC Screening ({v.unit_id})",
            'message': f"Verification {v.VerificationID} flagged Failed by {v.VerifiedBy}.",
            'severity': 'warn',
            'link': 'verification.html',
            'timestamp': v.Date.isoformat(),
        })

    return JsonResponse({
        'count': len(notifications),
        'notifications': notifications,
    })
