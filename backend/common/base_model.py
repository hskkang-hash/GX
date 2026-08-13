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

        # W0-2: 권한 우회 목록 — 업무 데이터 모델 7종 제거 완료 (2026-08-13)
        #
        # 제거한 것: order, orderitem, orderhistory, payment, ordercomment,
        #            orderassignment, terminal
        #   이 모델들은 group 격리를 건너뛰고 있었다. 단일 기관 온프레미스에서는
        #   무해하나 SaaS 에서는 A 고객이 B 고객의 주문·터미널을 조회할 수 있다.
        #
        # ⚠ 이 목록에 항목을 추가하지 말 것 (절대금지 #6 / D-103).
        #   성능 문제는 인덱스 → select_related/prefetch_related → 쿼리 분할 → 캐시
        #   순서로 푼다. 권한 필터 우회로 되돌리는 것은 금지다.
        #   backend/tests/test_tenant_isolation.py::test_bypass_list_does_not_grow
        #   가 업무 모델의 재등록을 막는다.
        #
        # 남긴 것: 프레임워크 모델 7종. dj-core 의존이라 즉시 제거하면 전 화면이
        #   흔들린다(§0.4). 뷰 레벨에서 request.user.group 필터를 강제한다.
        #   해소 조건은 docs/agent/exceptions.md 참조.
        performance_bypass_models = [
            # 프레임워크 모델 (rj-core/dj-core 의존 — 뷰 레벨 필터로 대응)
            'coreuser', 'usergroup', 'role', 'userprofilelink',
            'multilanguagecontent', 'userprofile', 'group',
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
