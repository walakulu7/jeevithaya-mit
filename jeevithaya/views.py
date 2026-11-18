"""
Page views. Every page except login/logout requires a logged-in user, and
each page is limited to the roles shown for it in the sidebar. The browser-side
menu hiding in rbac.js is only cosmetic; these checks are the real gate.
"""

from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from bloodbank.api.common import (
    current_user, ALL_ROLES, ADMIN_ROLES, LAB_ROLES, INVENTORY_ROLES, SYSTEM_ADMIN_ONLY,
)


def page(template, roles=ALL_ROLES, public=False):
    """Build a view that renders `template` for users holding one of `roles`."""
    @ensure_csrf_cookie
    def view(request):
        if not public:
            user = current_user(request)
            if user is None:
                return redirect('login_html')
            if not user.has_role(*roles):
                return redirect('dashboard')
        return render(request, template)
    view.__name__ = template.replace('.html', '')
    return view


login = page('login.html', public=True)
logout = page('logout.html', public=True)
index = page('index.html', public=True)

dashboard = page('dashboard.html')
donors = page('donors.html')
patients = page('patients.html')
requests_page = page('requests.html')
profile = page('profile.html')
presentation = page('presentation.html')

inventory = page('inventory.html', roles=INVENTORY_ROLES)
donation = page('donation.html', roles=LAB_ROLES)
verification = page('verification.html', roles=LAB_ROLES)
disposal = page('disposal.html', roles=LAB_ROLES)
reports = page('reports.html', roles=ADMIN_ROLES)
create_user = page('create_user.html', roles=SYSTEM_ADMIN_ONLY)
