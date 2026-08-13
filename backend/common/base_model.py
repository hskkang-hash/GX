from core.base import BaseModel
from core.user.models import UserGroup, CoreUser
from django.db import models
from django.db.models import Q
from django.utils.functional import SimpleLazyObject
from django.utils.deprecation import MiddlewareMixin
import threading
from core.middleware.refresh_token import get_current_request

class _RequestLocal(threading.local):
    def __init__(self):
        self.request = None

_request_local = _RequestLocal()

class RequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _request_local.request = request

class CustomManagerGroup(models.Manager):
    """
    Custom manager để quản lý permission filtering dựa trên created_by.group và group
    """
    _request = None
    _use_group = None

    def get_queryset(self):
        """
        Override phương thức get_queryset để lọc dữ liệu dựa trên group permissions
        """

        import time
        start_time = time.time()
        
        # Lấy QuerySet mặc định
        queryset = super().get_queryset()
        # Get model info for processing
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        
        request = get_current_request()
        
        # print(f"🔐 [MANAGER_DEBUG] CustomManagerGroup.get_queryset START - Model: {app_label}.{model_name} - User: {user_info}")
        
        # Danh sách các model của grid cần loại trừ
        grid_models = [
            'usergridmanagement',
            'gridsetting',
            'gridsettinguser',
            'gridsettingcategory',
            'searchconditionsuser',
            'menu',
            'tab',
            'role',
            'rolemenu',
            'roletab',
            'roleuser',
            'roleuser'
        ]
        
        # 🚀 PERFORMANCE OPTIMIZATION: Skip permission filtering for specific models
        performance_bypass_models = [
            # Order-related models (high-frequency access)
            'order', 'orderitem', 'orderhistory', 'payment', 'ordercomment', 'orderassignment',
            # User/Role models (prevent N+1 during schema processing)  
            'coreuser', 'usergroup', 'role', 'userprofilelink',
            # Content/Terminal models (frequent during data loading)
            'multilanguagecontent', 'terminal',
            # Frequently accessed during schema processing
            'userprofile', 'group'
        ]
        
        # Grid models bypass (no group filtering needed)
        if model_name.lower() in grid_models:
            return queryset
        
        # Performance-critical models bypass (prevent N+1 queries)
        if model_name.lower() in performance_bypass_models:
            return queryset

        # Lấy request và user hiện tại 
        if not request or not hasattr(request, 'user'):
            end_time = time.time()
            # print(f"⚠️ [MANAGER_DEBUG] No request/user - Time: {(end_time - start_time) * 1000:.2f}ms")
            return queryset.none()

        user = request.user
        
        # Kiểm tra nếu user không tồn tại hoặc không authenticated
        if not user or not user.is_authenticated or not user.is_active:
            end_time = time.time()
            # print(f"⚠️ [MANAGER_DEBUG] User not authenticated - Time: {(end_time - start_time) * 1000:.2f}ms")
            return queryset.none()
            
        # Superuser có thể thấy tất cả dữ liệu
        superuser_check_start = time.time()
        is_superuser = user.is_superuser or any(role.code == 'superuser' for role in user.roles.all())
        superuser_check_end = time.time()
        
        if is_superuser:
            end_time = time.time()
            # print(f"👑 [MANAGER_DEBUG] SUPERUSER - no filtering - Superuser check: {(superuser_check_end - superuser_check_start) * 1000:.2f}ms - Total: {(end_time - start_time) * 1000:.2f}ms")
            return queryset

        # print(f"👤 [MANAGER_DEBUG] NORMAL USER - applying group filtering")
        
        # SIMPLE CACHING: Only cache user group to avoid repeated lookups
        cache_start = time.time()
        if not hasattr(request, '_user_group_cache'):
            request._user_group_cache = {}
            
        user_id = user.id
        if user_id not in request._user_group_cache:
            profile_start = time.time()
            profile = user.userprofilelink if hasattr(user, 'userprofilelink') else None
            request._user_group_cache[user_id] = profile.group if profile else None
            profile_end = time.time()
            # print(f"📊 [MANAGER_DEBUG] Profile lookup: {(profile_end - profile_start) * 1000:.2f}ms")
            
        user_group = request._user_group_cache[user_id]
       
        cache_end = time.time()
        # print(f"📊 [MANAGER_DEBUG] Cache lookup: {(cache_end - cache_start) * 1000:.2f}ms - User group: {user_group}")
        
        # 🚀 CRITICAL OPTIMIZATION: Advanced Request-Level Permission Caching
        permission_cache_key = f"permission_{model_name}_{user.id}_{user_group.id if user_group else 'none'}"
        
        # Initialize permission cache if not exists
        if not hasattr(request, '_permission_result_cache'):
            request._permission_result_cache = {}
        
        # DEBUG: Track cache usage
        print(f"🔍 [CACHE_DEBUG] Model: {model_name}, Key: {permission_cache_key}")
        print(f"🔍 [CACHE_DEBUG] Cache exists: {permission_cache_key in request._permission_result_cache}")
        print(f"🔍 [CACHE_DEBUG] Total cache entries: {len(request._permission_result_cache)}")
        
        # Check if we already computed permission for this combination
        if permission_cache_key in request._permission_result_cache:
            cached_result = request._permission_result_cache[permission_cache_key]
            end_time = time.time()
            print(f"⚡ [CACHE_HIT] {model_name} - {(end_time - start_time) * 1000:.2f}ms")
            
            if cached_result == 'no_filter':
                return queryset
            elif cached_result == 'user_only':
                return queryset.filter(Q(created_by=user) | Q(created_by__isnull=True))
            elif isinstance(cached_result, list):
                return queryset.filter(Q(created_by__in=cached_result) | Q(created_by__isnull=True) | Q(groups=user_group))
            else:
                return queryset.none()
        
        # Compute permission (only first time per request)
        
        if not user_group:
            request._permission_result_cache[permission_cache_key] = 'user_only'
            print(f"💾 [CACHE_SET] {permission_cache_key} = 'user_only'")
            return queryset.filter(Q(created_by=user) | Q(created_by__isnull=True))
        
        # Optimized group user lookup with caching
        group_cache_key = f"group_users_{user_group.id}"
        if not hasattr(request, '_group_users_cache'):
            request._group_users_cache = {}
            
        if group_cache_key not in request._group_users_cache:
            # Batch load all group users once per request
            print(f"🔧 [GROUP_CACHE] Loading users for group {user_group.id}")
            group_user_ids = list(CoreUser.objects.filter(
                userprofilelink__group=user_group
            ).values_list('id', flat=True))
            request._group_users_cache[group_cache_key] = group_user_ids
            print(f"💾 [GROUP_CACHE_SET] {group_cache_key} = {len(group_user_ids)} users")
        else:
            group_user_ids = request._group_users_cache[group_cache_key]
            print(f"⚡ [GROUP_CACHE_HIT] {group_cache_key} = {len(group_user_ids)} users")
        
        # Cache the result
        if group_user_ids:
            request._permission_result_cache[permission_cache_key] = group_user_ids
            return queryset.filter(Q(created_by__in=group_user_ids) | Q(created_by__isnull=True) | Q(groups=user_group))
        else:
            request._permission_result_cache[permission_cache_key] = 'user_only'
            print(f"💾 [CACHE_SET] {permission_cache_key} = 'user_only' (no group users)")
            return queryset.filter(Q(created_by=user) | Q(created_by__isnull=True))
        

    @classmethod
    def set_use_group(cls, value):
        """Set the use_group value"""
        cls._use_group = value

class BaseModelWithGroup(BaseModel):
    """
    BaseModel mở rộng với tính năng lọc theo group và tự động assign group
    """
    groups = models.ManyToManyField(UserGroup, blank=True, related_name="%(class)s_groups")
    
    # Override default manager với CustomManagerGroup
    objects = CustomManagerGroup()

    def save(self, *args, **kwargs):
        """
        Override save method để tự động assign group cho record mới
        """
        is_new_record = self.pk is None
       
        # Lưu record trước (cần có ID để thêm vào ManyToManyField)
        super().save(*args, **kwargs)
        
        # Tự động assign group nếu là record mới và chưa có group
        if is_new_record and not self.groups.exists():
            self._auto_assign_group()
    
    def _auto_assign_group(self):
        """
        Tự động assign group của user hiện tại vào record
        """
        try:
            request = get_current_request()
            if not request or not hasattr(request, 'user'):
                return
                
            user = request.user
            if not user or not user.is_authenticated or not user.is_active:
                return
            
            # Lấy group của user hiện tại
            profile = getattr(user, 'userprofilelink', None)
            if profile and profile.group:
                self.groups.add(profile.group)
                
        except Exception as e:
            # Log error nhưng không fail transaction
            pass

    class Meta:
        abstract = True