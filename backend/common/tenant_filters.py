"""테넌트(group) 필터 강제 헬퍼 — W0-2.

배경
    `CustomManagerGroup.get_queryset()` 의 `performance_bypass_models` 에서
    업무 데이터 모델 7종(order·orderitem·orderhistory·payment·ordercomment·
    orderassignment·terminal)은 제거했다.

    남은 프레임워크 모델 7종(coreuser·usergroup·role·userprofilelink·
    multilanguagecontent·userprofile·group)은 rj-core/dj-core 의존이라
    매니저 수준에서 제거할 수 없다(§0.4). 대신 **뷰·서비스 레벨에서**
    이 헬퍼로 group 기준 필터를 명시적으로 건다.

사용법
    from common.tenant_filters import filter_users_by_group, get_scoped_or_404

    # 목록
    users = filter_users_by_group(CoreUser.objects.all(), request.user)

    # 단건 — 다른 테넌트의 id 를 넣어도 못 가져간다 (IDOR 차단)
    target = get_scoped_or_404(CoreUser, user_id, request.user)

⚠ 성능이 문제라면 인덱스 → select_related/prefetch_related → 쿼리 분할 → 캐시
  순서로 푼다. 권한 필터를 우회하는 방식으로 되돌리지 않는다 (D-103 / 절대금지 #6).
"""

from __future__ import annotations

from typing import Any, TypeVar

from django.db.models import Model, QuerySet

T = TypeVar("T", bound=Model)


def get_user_group(user: Any):
    """사용자의 소속 group. 없으면 None."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    profile = getattr(user, "userprofilelink", None)
    return getattr(profile, "group", None) if profile else None


def is_superuser(user: Any) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    roles = getattr(user, "roles", None)
    return bool(roles and any(getattr(r, "code", None) == "superuser" for r in roles.all()))


def filter_users_by_group(queryset: QuerySet[T], user: Any) -> QuerySet[T]:
    """CoreUser 계열 queryset 을 요청자의 group 으로 좁힌다.

    superuser 는 통과. 인증되지 않았거나 group 이 없으면 빈 queryset 을 준다
    (열어두는 쪽이 아니라 닫는 쪽이 기본값이다).
    """
    if is_superuser(user):
        return queryset
    group = get_user_group(user)
    if group is None:
        return queryset.none()
    return queryset.filter(userprofilelink__group=group)


def filter_by_group_field(queryset: QuerySet[T], user: Any, field: str = "group") -> QuerySet[T]:
    """`group` FK 를 직접 가진 모델(UserProfileLink, UserProfile 등)용."""
    if is_superuser(user):
        return queryset
    group = get_user_group(user)
    if group is None:
        return queryset.none()
    return queryset.filter(**{field: group})


def get_scoped_or_404(model: type[T], pk: Any, user: Any, *, group_lookup: str | None = None) -> T:
    """다른 테넌트의 pk 를 넘겨도 가져갈 수 없는 단건 조회 (IDOR 차단).

    `CoreUser.objects.get(id=user_id)` 처럼 호출자가 준 id 를 그대로 믿는 코드를
    이 함수로 바꾼다. 저장소 안에 그런 호출이 30곳 있다 (W0-2 실측).
    """
    from django.http import Http404

    queryset = model.objects.all()
    if not is_superuser(user):
        group = get_user_group(user)
        if group is None:
            raise Http404(f"{model.__name__} not found")
        lookup = group_lookup or _guess_group_lookup(model)
        queryset = queryset.filter(**{lookup: group})
    try:
        return queryset.get(pk=pk)
    except model.DoesNotExist as exc:  # 403 이 아니라 404 — 존재 여부도 흘리지 않는다
        raise Http404(f"{model.__name__} not found") from exc


def _guess_group_lookup(model: type[Model]) -> str:
    """모델이 group 에 닿는 경로를 고른다."""
    names = {f.name for f in model._meta.get_fields()}
    if "groups" in names:          # BaseModelWithGroup
        return "groups"
    if "group" in names:           # group FK 직접 보유
        return "group"
    if "userprofilelink" in names:  # CoreUser
        return "userprofilelink__group"
    raise ValueError(
        f"{model.__name__} 에서 group 경로를 찾을 수 없습니다. "
        "group_lookup 을 명시하십시오."
    )
