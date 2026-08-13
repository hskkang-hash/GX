"""
Authentication-related views for stream monitors
"""
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
@ensure_csrf_cookie
def csrf_token_view(request):
    """
    Simple endpoint to get CSRF token for frontend
    """
    return JsonResponse({
        'csrf_token': get_token(request),
        'authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None
    })


@require_http_methods(["GET"])
def auth_status_view(request):
    """
    Check authentication status
    """
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'is_staff': request.user.is_staff if request.user.is_authenticated else False,
        'is_superuser': request.user.is_superuser if request.user.is_authenticated else False,
    })