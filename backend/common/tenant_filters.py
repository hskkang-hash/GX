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

from common.tenant_roles import is_global_admin

T = TypeVar("T", bound=Model)


def get_user_group(user: Any):
    """사용자의 소속 group. 없으면 None."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    profile = getattr(user, "userprofilelink", None)
    return getattr(profile, "group", None) if profile else None


class NoTenantGroupError(Exception):
    """요청자에게 소속 group 이 없다 — 조용히 아무 group 이나 고르지 않기 위한 신호 (W0-12).

    이 예외가 나오는 것이 **저장된 첫 UserGroup 을 집어오는 폴백보다 항상 낫다.**
    전자는 요청 하나가 실패하고, 후자는 남의 테넌트에 레코드가 생긴다.

    ※ 이 파일은 W0-12 의 verify 가 리터럴 grep 이라 그 호출식을 문자 그대로 적지 않는다.
    """


def require_user_group(user: Any):
    """쓰기 경로에서 소유 group 을 정한다. 없으면 던진다 (W0-12).

    `get_user_group()` 과 다른 점은 **None 을 돌려주지 않는다**는 것 하나다.
    읽기 필터는 group 이 없으면 빈 queryset 으로 닫으면 되지만(`filter_*`),
    **생성 경로는 닫을 대상이 없다** — 소유자를 정하지 못하면 만들지 않아야 한다.

    ⚠ 대체 경로를 추가하지 말 것. "group 이 없으면 기본 group" 같은 폴백이
      들어오는 순간 W0-12 가 고친 결함이 이름만 바꿔 돌아온다.
    """
    group = get_user_group(user)
    if group is None:
        raise NoTenantGroupError(
            f"user={getattr(user, 'id', None)} 에게 소속 group 이 없어 "
            f"소유 테넌트를 정할 수 없습니다."
        )
    return group


# ─────────────────────────────────────────────────────────────────────────────
# 경계를 넘어도 되는가 — 판정은 `common.tenant_roles` 한 곳에서만 한다 (W0-14 · D-247)
# ─────────────────────────────────────────────────────────────────────────────
#
# 이 파일에는 예전에 `is_superuser()` 가 있었다. 그 판정식은
#   user.is_superuser or 'superuser' 역할 보유
# 로, dj-core `core/base.py:308` 의 우회를 **글자 그대로 복제**한 것이었다.
# 그래서 뷰를 아무리 좁혀도 통과 대상이 같았다 — 레거시 `superuser` 역할 13계정
# (그중 7계정이 고객 테넌트 Anyang 안에 있다 · evidence/W0-16/superuser_accounts.md)
# 이 여기서도 전부 통과했다.
#
# 이제 그 질문의 답은 `tenant_roles.is_global_admin()` 만 낸다. 전환 플래그
# `TENANT_TRUST_LEGACY_SUPERUSER` 를 내리는 순간, **이 파일을 고치지 않고도**
# 레거시 역할이 여기서 통과하지 못하게 된다 (revocation_runbook §2).
#
# ⚠ 판정식을 이 파일에 되살리지 말 것 (D-212). 복사본 하나가 우회 지점 하나다.


def filter_users_by_group(queryset: QuerySet[T], user: Any) -> QuerySet[T]:
    """CoreUser 계열 queryset 을 요청자의 group 으로 좁힌다.

    **전역 관리자**(W0-16 정의)만 통과. 인증되지 않았거나 group 이 없으면 빈
    queryset 을 준다 (열어두는 쪽이 아니라 닫는 쪽이 기본값이다).
    """
    if is_global_admin(user):
        return queryset
    group = get_user_group(user)
    if group is None:
        return queryset.none()
    return queryset.filter(userprofilelink__group=group)


def filter_by_group_field(queryset: QuerySet[T], user: Any, field: str = "group") -> QuerySet[T]:
    """`group` FK 를 직접 가진 모델(UserProfileLink, UserProfile 등)용."""
    if is_global_admin(user):
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
    if not is_global_admin(user):
        group = get_user_group(user)
        if group is None:
            raise Http404(f"{model.__name__} not found")
        lookup = group_lookup or _guess_group_lookup(model)
        queryset = queryset.filter(**{lookup: group})
    try:
        return queryset.get(pk=pk)
    except model.DoesNotExist as exc:  # 403 이 아니라 404 — 존재 여부도 흘리지 않는다
        raise Http404(f"{model.__name__} not found") from exc


def assert_scoped(model: type[Model], pks: Any, user: Any, *,
                  group_lookup: str | None = None) -> None:
    """`pks` 가 **전부 요청자의 테넌트 것**인지 확인한다. 아니면 `Http404` (W0-14c).

    쓰기 경로(수정·삭제)의 문지기다. 핸들러 첫 줄에서 부른다::

        assert_scoped(ReportTemplate, id, request.user)

    왜 403 이 아니라 404 인가
        403 은 "그 id 는 존재하지만 네 것이 아니다"를 알려 준다 — 존재 여부가 새는 것도
        누출이다. 남의 것은 **없는 것과 같아야** 한다 (`get_scoped_or_404` 와 같은 규약).

    실측 근거 (evidence/W0-14/wiring_fix_and_findings.md)
        이 문지기가 없어서 tenant-A 가 tenant-B 의 레코드를 **지웠다** — Device 는 행 자체가
        사라지고, ChecklistSetting·SurveillanceProfile·ReportTemplate 는 소프트 삭제됐다.
        수정 경로에서는 남의 행에 UPDATE 가 실행됐고, 막은 것은 DB 의 NOT NULL 제약이었다.

    ⚠ 여기서 통과 판정을 따로 만들지 말 것 — 전역 여부는 `tenant_roles` 만 답한다 (D-212).
    """
    from django.http import Http404

    if is_global_admin(user):
        return

    if isinstance(pks, str):
        wanted = [p.strip() for p in pks.split(",") if p.strip()]
    elif isinstance(pks, (list, tuple, set)):
        wanted = [str(p) for p in pks]
    else:
        wanted = [str(pks)]
    if not wanted:
        return

    group = get_user_group(user)
    if group is None:
        raise Http404(f"{model.__name__} not found")

    lookup = group_lookup or _guess_group_lookup(model)
    # ★ `objects` 가 아니라 `_base_manager` 로 묻는다.
    #   `objects` 는 dj-core 의 테넌트 필터를 타고, 그 필터에는 `created_by__isnull=True`
    #   OR 절이 들어 있다(§0.4 라 고칠 수 없다). 문지기가 그 필터를 통해 물으면
    #   "내 것이 아닌데 통과"와 "없어서 통과"를 구별하지 못한다.
    #   **소유 판정은 필터를 거치지 않은 사실 위에서 해야 한다.**
    owned = set(
        str(pk) for pk in model._base_manager.filter(
            pk__in=wanted, **{lookup: group}
        ).values_list("pk", flat=True)
    )
    missing = [pk for pk in wanted if pk not in owned]
    if missing:
        # 무엇이 빠졌는지 응답에 싣지 않는다 — 존재 여부를 흘리지 않기 위해서다.
        raise Http404(f"{model.__name__} not found")


def _guess_group_lookup(model: type[Model]) -> str:
    """모델이 group 에 닿는 경로를 고른다."""
    names = {f.name for f in model._meta.get_fields()}
    if "groups" in names:          # BaseModelWithGroup
        return "groups"
    if "group" in names:           # group FK 직접 보유
        return "group"
    if "userprofilelink" in names:  # CoreUser
        return "userprofilelink__group"
    if "created_by" in names:
        # group 열이 없는 모델(ReportTemplate·Device 등)은 **생성자의 소속**이 소유다.
        # 이 저장소가 이미 그렇게 쓰고 있다 (report_template/views.py 의 기본값 조회).
        return "created_by__userprofilelink__group"
    raise ValueError(
        f"{model.__name__} 에서 group 경로를 찾을 수 없습니다. "
        "group_lookup 을 명시하십시오."
    )
