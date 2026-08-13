from functools import wraps
from django.http import JsonResponse
from oauth2_provider.models import AccessToken
from oauth2_provider import scope as oauth_scope
from django.contrib.auth.models import AnonymousUser
import logging
from django.utils import timezone
logger = logging.getLogger(__name__)


class OAuth2Authentication:
    """OAuth2 authentication utility"""
    
    @staticmethod
    def get_user_from_token(request):
        """Lấy user từ OAuth2 access token"""
        try:
            # Lấy token từ header Authorization
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                return None
                
            token = auth_header.split(' ')[1]
            
            # Tìm access token trong database
            try:
                access_token = AccessToken.objects.select_related('user', 'application').get(
                    token=token,
                    expires__gt=timezone.now()
                )
                return access_token.user, access_token
            except AccessToken.DoesNotExist:
                return None
                
        except Exception as e:
            logger.error(f"Error in OAuth2 authentication: {e}")
            return None
    
    @staticmethod
    def check_token_scopes(access_token, required_scopes):
        """Kiểm tra scopes của token"""
        if not required_scopes:
            return True
            
        token_scopes = access_token.scope.split()
        return oauth_scope.check(required_scopes, token_scopes)


def oauth2_required(scopes=None):
    """
    Decorator để yêu cầu OAuth2 authentication
    
    Args:
        scopes: List các scopes cần thiết (optional)
        
    Usage:
        @oauth2_required()
        @oauth2_required(['read'])  
        @oauth2_required(['read', 'write'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            from django.utils import timezone
            
            # Lấy user và token từ request
            result = OAuth2Authentication.get_user_from_token(request)
            if not result:
                return JsonResponse({
                    'error': 'invalid_token',
                    'error_description': 'Access token is invalid or expired'
                }, status=401)
            
            user, access_token = result
            
            # Kiểm tra scopes nếu được yêu cầu
            if scopes and not OAuth2Authentication.check_token_scopes(access_token, scopes):
                return JsonResponse({
                    'error': 'insufficient_scope',
                    'error_description': f'Token does not have required scopes: {scopes}'
                }, status=403)
            
            # Gán user và token vào request
            request.user = user
            request.oauth2_token = access_token
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def scope_required(required_scopes):
    """
    Decorator để kiểm tra scopes cụ thể
    
    Usage:
        @scope_required(['devices'])
        @scope_required(['admin', 'write'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Kiểm tra xem có token không
            if not hasattr(request, 'oauth2_token'):
                return JsonResponse({
                    'error': 'authentication_required',
                    'error_description': 'OAuth2 authentication required'
                }, status=401)
            
            # Kiểm tra scopes
            if not OAuth2Authentication.check_token_scopes(request.oauth2_token, required_scopes):
                return JsonResponse({
                    'error': 'insufficient_scope',
                    'error_description': f'Token does not have required scopes: {required_scopes}'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


class OAuth2Middleware:
    """Middleware để tự động xử lý OAuth2 authentication"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Chỉ áp dụng cho API endpoints
        if request.path.startswith('/api/'):
            self.process_oauth2_auth(request)
        
        response = self.get_response(request)
        return response
    
    def process_oauth2_auth(self, request):
        """Xử lý OAuth2 authentication"""
        try:
            result = OAuth2Authentication.get_user_from_token(request)
            if result:
                user, access_token = result
                request.user = user
                request.oauth2_token = access_token
                logger.info(f"OAuth2 authenticated user: {user.username}")
            else:
                # Giữ nguyên AnonymousUser nếu không có token
                if not hasattr(request, 'user'):
                    request.user = AnonymousUser()
        except Exception as e:
            logger.error(f"Error in OAuth2 middleware: {e}")
            request.user = AnonymousUser()


# Utility functions for checking permissions
def has_scope(request, scope):
    """Kiểm tra xem request có scope cụ thể không"""
    if not hasattr(request, 'oauth2_token'):
        return False
    return OAuth2Authentication.check_token_scopes(request.oauth2_token, [scope])


def get_token_scopes(request):
    """Lấy danh sách scopes của token hiện tại"""
    if not hasattr(request, 'oauth2_token'):
        return []
    return request.oauth2_token.scope.split()


def is_oauth2_authenticated(request):
    """Kiểm tra xem request có được xác thực bằng OAuth2 không"""
    return hasattr(request, 'oauth2_token') and request.oauth2_token is not None 