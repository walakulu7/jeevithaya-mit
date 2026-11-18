"""Login, logout and current-user endpoints."""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..models import User
from .common import api_view, error_response, model_to_dict, read_json, ApiError


DEFAULT_DEMO_USERS = [
    {"Name": "System Administrator", "Email": "admin@jeevithaya.com", "Role": User.SYSTEM_ADMIN, "Password": "admin123"},
    {"Name": "Hospital Administrator", "Email": "hospital@jeevithaya.com", "Role": User.HOSPITAL_ADMIN, "Password": "hospital123", "HospitalID": 1},
    {"Name": "Front Office User", "Email": "frontoffice@jeevithaya.com", "Role": User.FRONT_OFFICE, "Password": "front123"},
    {"Name": "Lab Assistant", "Email": "lab@jeevithaya.com", "Role": User.LAB_ASSISTANT, "Password": "lab123"},
]


def ensure_demo_users():
    """Create the demo accounts (with hashed passwords) on an empty database."""
    if User.objects.exists():
        return
    for spec in DEFAULT_DEMO_USERS:
        data = dict(spec)
        raw_password = data.pop('Password')
        user = User(**data)
        user.set_password(raw_password)
        user.save()


def public_user(user):
    data = model_to_dict(user)
    data.pop('Password', None)
    return data


@require_http_methods(["POST"])
def api_auth_login(request):
    try:
        ensure_demo_users()
        data = read_json(request)
    except ApiError as e:
        return error_response(str(e), e.status)

    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    if not email or not password:
        return error_response('Email and password are required.', 400)

    user = User.objects.filter(Email__iexact=email).first()
    if not user or not user.check_password(password):
        return error_response('Invalid email or password.', 401)
    if not user.is_active:
        return error_response('Account is inactive. Please contact an administrator.', 403)

    request.session.cycle_key()  # prevent session fixation
    request.session['user_id'] = user.UserID
    request.session['user_role'] = user.Role
    request.session['user_name'] = user.Name
    return JsonResponse({'message': 'Login successful', 'user': public_user(user)})


@require_http_methods(["POST"])
def api_auth_logout(request):
    request.session.flush()
    return JsonResponse({'message': 'Logged out successfully'})


@api_view(["GET"], roles=None)
def api_auth_me(request):
    return JsonResponse({'user': public_user(request.current_user)})
