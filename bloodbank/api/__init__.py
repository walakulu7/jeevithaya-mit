"""
JSON API for the blood bank, split by area:

- common:    serialization, auth decorator, error mapping, generic ModelResource
- auth:      login / logout / current user
- resources: CRUD resources for each domain model
- reports:   dashboard stats, analytics, PDF exports, notifications
"""

from .auth import api_auth_login, api_auth_logout, api_auth_me, DEFAULT_DEMO_USERS  # noqa: F401
from .resources import (  # noqa: F401
    api_users, api_user_detail,
    api_donors, api_donor_detail,
    api_patients, api_patient_detail,
    api_requests, api_request_detail,
    api_donations, api_donation_detail,
    api_inventory, api_inventory_detail,
    api_verifications, api_verification_detail,
    api_disposals, api_disposal_detail,
)
from .reports import (  # noqa: F401
    api_dashboard_stats, api_reports, api_reports_pdf, api_notifications,
)
