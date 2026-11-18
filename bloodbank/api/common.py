"""
Shared HTTP plumbing for the JSON API: serialization, input normalisation,
authentication/authorisation, uniform error responses, and the generic
ModelResource that every CRUD endpoint is built from.
"""

import json
from functools import wraps

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from ..models import User, InvalidTransition


# ------------------------------------------------------------------
# Role groups (who may use which part of the system)
# ------------------------------------------------------------------
ALL_ROLES = (User.SYSTEM_ADMIN, User.HOSPITAL_ADMIN, User.FRONT_OFFICE, User.LAB_ASSISTANT)
ADMIN_ROLES = (User.SYSTEM_ADMIN, User.HOSPITAL_ADMIN)
LAB_ROLES = (User.SYSTEM_ADMIN, User.LAB_ASSISTANT)
INVENTORY_ROLES = (User.SYSTEM_ADMIN, User.HOSPITAL_ADMIN, User.LAB_ASSISTANT)
SYSTEM_ADMIN_ONLY = (User.SYSTEM_ADMIN,)


class ApiError(Exception):
    """An error that maps directly to an HTTP status and a user-facing message."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def error_response(message, status):
    return JsonResponse({'error': message}, status=status)


def read_json(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        raise ApiError('Request body must be valid JSON.', 400)


def _validation_message(exc):
    if hasattr(exc, 'message_dict'):
        parts = []
        for field, msgs in exc.message_dict.items():
            label = '' if field == '__all__' else f"{field}: "
            parts.append(label + ' '.join(msgs))
        return '; '.join(parts)
    return ' '.join(exc.messages)


def _protected_message(exc):
    names = sorted({o._meta.verbose_name_plural for o in getattr(exc, 'protected_objects', [])})
    linked = ', '.join(names) or 'other records'
    return f"Cannot delete: this record is still linked to {linked}. Remove those first."


# ------------------------------------------------------------------
# Authentication / authorisation
# ------------------------------------------------------------------
def current_user(request):
    """The logged-in, active user for this request, or None."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    user = User.objects.filter(UserID=user_id).first()
    if user is None or not user.is_active:
        return None
    return user


def require_roles(request, roles):
    if roles and not request.current_user.has_role(*roles):
        raise ApiError('You do not have permission to do this.', 403)


def api_view(methods, roles=ALL_ROLES):
    """
    Decorator for every JSON endpoint: restricts HTTP methods, requires a
    logged-in active user with one of `roles` (None = any logged-in user),
    and converts domain exceptions into consistent JSON error responses.
    """
    def decorator(fn):
        @require_http_methods(methods)
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            user = current_user(request)
            if user is None:
                return error_response('Authentication required. Please log in.', 401)
            request.current_user = user
            try:
                require_roles(request, roles)
                return fn(request, *args, **kwargs)
            except ApiError as e:
                return error_response(str(e), e.status)
            except InvalidTransition as e:
                return error_response(str(e), 409)
            except ProtectedError as e:
                return error_response(_protected_message(e), 409)
            except ValidationError as e:
                return error_response(_validation_message(e), 400)
        return wrapper
    return decorator


def csrf_failure(request, reason=''):
    """Return CSRF failures as JSON so the frontend can show a readable message."""
    return error_response('Security check failed. Refresh the page and try again.', 403)


# ------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------
def _public_name(field):
    """API key for a field: relations keep their legacy column name (e.g. DonorID)."""
    return field.db_column or field.name


def model_to_dict(obj):
    """Convert a model instance to a JSON-safe dict using the API's field names."""
    if obj is None:
        return None
    data = {}
    for field in obj._meta.concrete_fields:
        value = getattr(obj, field.attname)
        data[_public_name(field)] = value.isoformat() if hasattr(value, 'isoformat') else value
    return data


_ALIASES = {
    'dob': 'dateofbirth',
    'result': 'overallresult',
    'comment': 'notes',
    'qty': 'quantity',
}


def normalize_payload(model_cls, data, include_pk=True):
    """
    Map incoming JSON keys (any case, camelCase or snake_case) onto model
    attribute names. Relations accept their ID under the legacy key, e.g.
    {"DonorID": "D001"} -> {"donor_id": "D001"}. Unknown keys are ignored.
    """
    lookup = {}
    for f in model_cls._meta.concrete_fields:
        if not f.editable or (f.primary_key and not include_pk):
            continue
        for key in {f.name, f.attname, f.db_column or ''}:
            if key:
                lookup[key.lower().replace('_', '')] = f

    normalized = {}
    for key, value in data.items():
        clean = key.lower().replace('_', '')
        field = lookup.get(_ALIASES.get(clean, clean))
        if field is None:
            continue
        if value == '' and field.null:
            value = None
        normalized[field.attname] = value
    return normalized


# ------------------------------------------------------------------
# Generic resource (one class per model, overridden where behaviour differs)
# ------------------------------------------------------------------
class ModelResource:
    """
    A REST resource for one model: list, create, retrieve, update, delete.

    Subclasses set `model`, `label` and the roles allowed to read and write,
    and override hooks (prepare / perform_create / perform_update /
    perform_delete / authorize) only where their business rules differ.
    """
    model = None
    label = 'Record'
    read_roles = ALL_ROLES
    write_roles = ALL_ROLES

    # ---- hooks ---------------------------------------------------
    def queryset(self):
        return self.model.objects.all()

    def serialize(self, obj):
        return model_to_dict(obj)

    def authorize(self, request, action, obj=None):
        """action is one of: read, create, update, delete."""
        require_roles(request, self.read_roles if action == 'read' else self.write_roles)

    def prepare(self, request, data, instance=None):
        return normalize_payload(self.model, data, include_pk=instance is None)

    def perform_create(self, request, data):
        obj = self.model(**data)
        obj.full_clean()
        obj.save()
        return obj

    def perform_update(self, request, obj, data):
        for key, value in data.items():
            setattr(obj, key, value)
        obj.full_clean()
        obj.save()
        return obj

    def perform_delete(self, request, obj):
        obj.delete()

    # ---- plumbing ------------------------------------------------
    def get_object(self, pk):
        obj = self.queryset().filter(pk=pk).first()
        if obj is None:
            raise ApiError(f"{self.label} {pk} not found.", 404)
        return obj

    def collection_view(self):
        @api_view(['GET', 'POST'], roles=None)
        def view(request):
            if request.method == 'GET':
                self.authorize(request, 'read')
                return JsonResponse([self.serialize(o) for o in self.queryset()], safe=False)
            self.authorize(request, 'create')
            data = self.prepare(request, read_json(request))
            with transaction.atomic():
                obj = self.perform_create(request, data)
            return JsonResponse(self.serialize(obj), status=201)
        return view

    def item_view(self):
        @api_view(['GET', 'PUT', 'DELETE'], roles=None)
        def view(request, pk):
            obj = self.get_object(pk)
            if request.method == 'GET':
                self.authorize(request, 'read', obj)
                return JsonResponse(self.serialize(obj))
            if request.method == 'PUT':
                self.authorize(request, 'update', obj)
                data = self.prepare(request, read_json(request), instance=obj)
                with transaction.atomic():
                    obj = self.perform_update(request, obj, data)
                return JsonResponse(self.serialize(obj))
            self.authorize(request, 'delete', obj)
            with transaction.atomic():
                self.perform_delete(request, obj)
            return HttpResponse(status=204)
        return view
