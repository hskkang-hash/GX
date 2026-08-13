# proxy/middleware.py
from django.utils.deprecation import MiddlewareMixin


class RemoveXFrameOptionsMiddleware(MiddlewareMixin):
    """
    Middleware to remove X-Frame-Options header for proxy endpoints
    This runs after XFrameOptionsMiddleware to override its behavior
    """
    def process_response(self, request, response):
        # Check if this is a proxy endpoint
        if request.path.startswith('/api/proxy/'):
            # Remove X-Frame-Options header
            if 'X-Frame-Options' in response:
                del response['X-Frame-Options']
        return response

