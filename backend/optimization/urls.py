"""
🚀 OPTIMIZATION API URLs
Background processing optimization endpoints
"""

from django.urls import path
from ninja_extra import NinjaExtraAPI
from .views import OptimizationAPI

# Create API instance for optimization
api = NinjaExtraAPI(urls_namespace="optimization_api")

# Register optimization API controller
api.register_controllers(OptimizationAPI)

# URL patterns
urlpatterns = [
    path("", api.urls),
]
