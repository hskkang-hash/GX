#!/usr/bin/env python
"""커널 공개 함수가 테넌트 스코프를 통과하는지 판정한다 (C-3.1 · D-105 · K5).

C-3.1 이 요구하는 것
--------------------
    "커널의 모든 공개 함수는 `@tenant_scoped()` 를 거치거나,
     거치지 않는 경우 PUBLIC 등록부에 **근거와 함께** 등재되어야 한다."

이 게이트는 오늘 **아무것도 막지 않는다.** `backend/kernels/` 가 아직 없기 때문이다
(커널은 WP-2 EXIT 후 K1 부터 선다). 그래도 지금 세우는 이유가 있다.

왜 커널이 서기 **전에** 세우나
------------------------------
오늘 두 번, 판정을 지킨 것은 게이트가 아니라 사람의 눈이었다.
그 둘의 공통점은 **판정이 먼저 있고 게이트가 나중에 왔다**는 것이다.
나중에 오는 게이트는 이미 쌓인 빚을 만나고, 그러면 래칫으로 잠그는 수밖에 없다 —
`verify_classification.py` 가 빚 113건을 안고 출발한 것이 바로 그 모양이다.

커널은 아직 한 줄도 없다. **여기서만은 빚 0 으로 시작할 수 있다.**
K1 의 첫 커밋부터 이 게이트가 서 있으면 래칫이 필요 없다.

    python scripts/verify_tenant_scope.py           # 판정 (위반 시 exit 1)
    python scripts/verify_tenant_scope.py --list    # 함수별 상태 출력

무엇을 보지 **않나** — 경계를 분명히 한다
------------------------------------------
라우트 단위의 스코프(현재 실재하는 것)는 이 게이트가 아니라
`backend/tests/test_route_tenant_scope.py` 가 본다. 그쪽은 Django 를 띄워
라우트를 열거해야 하므로 pre-commit 에서 돌릴 수 없다.

**같은 것을 두 곳에서 세지 않는다** (원칙 1: 중복 0). 여기서는
Django 없이 정적으로 판정할 수 있는 것만 본다:

  · 커널 공개 함수의 스코프 표식 (AST)
  · `PUBLIC_ROUTES` 전건에 사유가 있는가 (AST — 시험도 보지만 커밋 시점에 먼저 잡는다)
  · 면제 목록이 **늘지 않았는가** (PUBLIC_BASELINE 래칫)
  · **신규 경로 트립와이어 — 정적 눈** (D-275 §5-1, 아래)

신규 경로 트립와이어 (D-275 §5-1) — **EXIT 승인의 유일한 필수 부대조건**
------------------------------------------------------------------------
WP-2 EXIT §5-1 의 미지는 이것이었다: 주인 없는 행은 매니저 수준에서 여전히 보이고,
근원은 저장소 밖이라 못 고친다. 지금 닫혀 있는 이유는 **라우트마다 문지기를 손으로 달았기
때문**이고, **문지기 없는 새 경로가 하나 생기면 그 순간 다시 샌다.**

그 문장을 사람의 기억이 아니라 게이트가 지키게 한다.

  판정기  `backend/common/tenant_tripwire.py` — **한 벌뿐이다**
  눈 둘   정적(여기, Django 불필요)  ·  런타임(`tests/test_route_tripwire.py`, 전수 열거)

여기가 정적 눈이다. 지시가 요구한 **런타임 전수 열거**는 시험 쪽이 한다 — pre-commit 은
Django 를 띄울 수 없기 때문이다. 정적 눈이 런타임 눈을 대신하는 것이 아니라,
**커밋 시점에 먼저 걸러 주는 앞눈**이다. 같은 것을 두 번 세는 것이 아니라 한 판정을
두 각도에서 먹인다 (원칙 1: 중복 0 은 **판정**의 중복을 금하는 것이다).

    python scripts/verify_tenant_scope.py --write-baseline   # 등재부 갱신(정적 구획만)
"""
from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
KERNEL_ROOT = ROOT / "backend" / "kernels"
APP_ROOT = ROOT / "backend" / "apps"
TENANT_SCOPE = ROOT / "backend" / "common" / "tenant_scope.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 스코프를 걸었다고 인정하는 데코레이터 이름.
SCOPE_DECORATORS = {"tenant_scoped"}

#: 커널 공개 함수의 면제 — `모듈:함수` → 사유. 사유 없는 등재는 거부한다.
#:
#: ⚠ **PUBLIC 은 검사 면제가 아니라 "공용임을 시험으로 증명한 것"이어야 한다** (D-261 c).
#:   여기 이름을 올리는 것은 "이 함수는 테넌트 데이터를 반환하지 않는다"는 **선언**이고,
#:   그 선언은 시험으로 뒷받침되어야 한다. 추측으로 올리지 않는다.
KERNEL_PUBLIC: dict[str, str] = {
    # record_detection 은 D-281 적용으로 **여기서 내려왔다.** 사람이 부른 경우
    # `assert_scoped(StreamMonitor, ...)` 를 부르므로 문지기 통과(2차)로 판정된다.
    # PUBLIC 등재는 "테넌트를 안 만진다"는 선언인데, 그 선언이 더는 필요 없어진 것이다.
    "backend/kernels/k1_event/services.py:subscribe":
        "구현이 없다. 부르면 NotImplementedYet 을 던지고 **아무 데이터도 반환하지 않는다** "
        "(F-05 Webhook — W2-2 이후 별 티켓). 구현이 들어오는 커밋에서 이 등재를 지우고 "
        "문지기를 붙여야 한다 — 구독은 그 자체가 테넌트 자원이다. "
        "시험 근거: KernelPublicSurfaceTest.test_public_surface_matches_da04 (이름만 서 있음을 확인) · "
        "KernelScopeSignatureTest.test_subscribe_requires_scope_before_it_raises "
        "(scope 를 빼면 NotImplementedYet 이 아니라 TypeError 다 — D-281 은 구현 전에도 걸린다)",

    # ── K2 (2026-09-24 · OPS-14) — **시스템만 부를 수 있는 감시 하나**
    "backend/kernels/k2_notify/heartbeat.py:heartbeat_watch":
        "「오늘 08:00 것이 왔는가」를 테넌트마다 한 줄로 돌려준다 — dead man's switch 의 "
        "나머지 절반이다(보내는 것만으로는 안 온 것을 아무도 모른다). "
        "★ 이것은 한 테넌트의 사실이 아니라 **설비 전체의 사실**이라 좁힐 대상이 없다. "
        "그래서 문지기로 좁히지 않고 **문 자체를 시스템 스코프에만 연다** — 사람이 부르면 "
        "`NotifyPermissionDenied` 다. 사람이 부를 수 있으면 「지금 알림이 안 나가는 "
        "테넌트」를 남이 알게 되고, 그것은 감시가 아니라 정찰이다. "
        "★ 읽기만 한다 — 여기서 다시 보내지 않는다(감시가 발송을 겸하면 감시가 부하를 "
        "만들고 그 부하가 다시 감시 대상이 된다). "
        "시험 근거: test_q_heartbeat_digest.py::"
        "HeartbeatWatchTest.test_a_person_cannot_run_the_watch (사람 스코프 거절) · "
        "test_the_watch_reports_every_tenant_not_only_the_late_ones "
        "(늦지 않은 것도 돌려준다 — 늦은 것만 내면 「본 적 없다」와 「봤는데 괜찮다」가 "
        "같은 빈 목록이 된다 · D-290)",

    # ── K5 (2026-09-10 · D-367) — **테넌트 데이터를 반환하지 않는 함수 하나**
    "backend/kernels/k5_trust/inbound_keys.py:capability_now":
        "「이 키로 무엇을 할 수 있는가」를 문장으로 만든다. 읽는 것은 "
        "`common.access_gate.INBOUND_KEY_ALLOWED` — **설비의 사실**이지 테넌트의 사실이 "
        "아니다. 어느 테넌트가 물어도 같은 답이고, DB 를 보지 않는다. "
        "★ 그래서 scope 를 받지 않는다: 받으면 「테넌트마다 다른 답이 있다」는 "
        "거짓 신호가 시그니처에 남고, 다음 사람이 그 인자를 채우려다 없는 구별을 만든다. "
        "시험 근거: test_f05_inbound_key_lifecycle.py::"
        "test_the_capability_is_read_from_the_gate_not_retyped "
        "(허용 집합의 전건과 그 **건수**가 문장에 실재하는지 대조 — 문장을 따로 적으면 "
        "그 집합이 바뀌는 날 문장만 옛말이 된다 · D-286)",

    # ── K6 (2026-08-30 착수분) — 둘 다 **구현이 없다.** 데이터를 반환하지 않는다.
    #    등재는 면제가 아니라 선언이고, 그 선언은 아래 시험이 뒷받침한다.
    "backend/kernels/k6_feedback/services.py:usage_snapshot":
        "구현이 없다. 부르면 NotImplementedYet 을 던지고 **아무 데이터도 반환하지 않는다** "
        "(U4 과금 근거 — W4-1 `UsageSnapshot` 모델이 저장소에 없다, 실측 0건). "
        "본문 첫 줄에서 `scope.require_actor()` 를 부르므로 시스템 스코프로도 못 지나간다. "
        "구현이 들어오는 커밋에서 이 등재를 지우고 문지기를 붙여야 한다 — 사용량은 테넌트 자원이다. "
        "시험 근거: HonestAbsenceTest.test_usage_snapshot_raises_instead_of_returning_zero · "
        "HonestAbsenceTest.test_absent_surface_still_demands_scope_first",
    "backend/kernels/k6_feedback/services.py:kpi_series":
        "구현이 없다. 부르면 NotImplementedYet 을 던진다 — DA-03 §2-4 의 t0/t1 계측 적재가 "
        "선행이고, 표본 없는 p95 는 만들어진 수다 (D-280 · 적재 P-K6-3). "
        "본문에서 `scope.require_actor()` 를 먼저 부른다. "
        "시험 근거: HonestAbsenceTest.test_kpi_series_raises_instead_of_returning_empty",

    # ── K3 (2026-08-30 착수분) — **테넌트 데이터를 반환하지 않는다.**
    #    둘 다 요청자 **자신의** 역할에서 파생된 값만 낸다(프리셋 이름 · 가시성 열거).
    #    남의 테넌트 행을 읽는 자리는 `resolve_layout` 이고, 그것은 문지기를 탄다.
    "backend/kernels/k3_dashboard/services.py:get_preset":
        "테넌트 데이터를 반환하지 않는다 — 돌려주는 것은 프리셋 이름과 **요청자 자신의** "
        "역할 코드뿐이다. 전역 여부 판정은 `tenant_roles.is_global_admin` 한 곳만 부른다(D-212). "
        "시험 근거: PresetRoutingTest.test_preset_returns_no_other_tenants_data · "
        "PresetRoutingTest.test_unmapped_role_falls_back_to_the_narrowest_preset "
        "(모르면 좁게 — 넓은 쪽으로 떨어뜨리면 역할을 못 알아본 사람이 기관장 화면을 본다)",
    "backend/kernels/k3_dashboard/services.py:widget_permission":
        "테넌트 데이터를 반환하지 않는다 — 돌려주는 것은 `Visibility` 열거값 하나다. "
        "★ 이 함수는 **격리를 대신하지 않는다**: VISIBLE 을 줘도 그 위젯이 읽는 데이터는 "
        "여전히 `filter_by_group_field` 를 탄다 (DA-03 §3-4 — 화면에서 감추는 것은 통제가 아니다). "
        "편집(E)은 설정 없이는 절대 참이 되지 않는다. "
        "시험 근거: WidgetPermissionTest.test_editable_is_never_true_without_configuration · "
        "WidgetPermissionTest.test_visibility_does_not_replace_tenant_isolation",

    # ── K4 (2026-08-30 착수분) — 구현이 없다. 데이터를 반환하지 않는다.
    "backend/kernels/k4_report/services.py:render_period":
        "구현이 없다. 부르면 NotImplementedYet 을 던지고 **아무 데이터도 반환하지 않는다** "
        "(기간 종합 보고서 — 기간 집계의 정의가 선행이고, 지금 만들면 K6 의 집계 경로와 "
        "**두 벌**이 된다: DA-04 §2 K6 이 금지한 모양이다. P-K6-3 과 함께 연다). "
        "본문 첫 줄에서 `scope.require_actor()` 를 부르므로 시스템 스코프로도 못 지나간다. "
        "구현이 들어오는 커밋에서 이 등재를 지우고 문지기를 붙여야 한다 — "
        "기간 보고서는 그 기간의 테넌트 데이터를 통째로 읽는다. "
        "시험 근거: HonestAbsenceTest.test_render_period_raises_instead_of_returning_empty",

    # ── K5 표 ② 자격증명 (2026-09-06 · D-325 · D-328) — **테넌트 데이터가 아니다.**
    #    표 ②가 담는 것은 **우리 계정의 외부 API 키에 대한 사실**이다(juso 팝업키 ·
    #    공공데이터포털 일반키). 테넌트마다 다른 값이 아니라 회사 하나가 가진 자원이고,
    #    그래서 `filter_by_group_field` 로 좁힐 대상 자체가 없다 — 좁히면 전부 사라진다.
    #    ★ 그렇다고 아무나 볼 수 있는 것은 아니다. 넷 다 `scope` 를 **필수 인자로 받고**
    #      `require_actor()`/감사 기록을 통과한다. 시스템 스코프로도 못 지나간다.
    "backend/kernels/k5_trust/services.py:list_credentials":
        "테넌트 데이터를 반환하지 않는다 — 표 ②는 **우리 계정 키**에 대한 사실만 담고, "
        "**값을 담는 칸이 자체가 없다**(D-204 · D-319). 조회는 언제나 마스킹이다. "
        "본문 첫 줄에서 `scope.require_actor()` 를 부른다. "
        "시험 근거: CredentialStoreShapeTest.test_the_model_has_no_place_to_put_a_value · "
        "CredentialObservationTest.test_the_lookup_is_always_masked",
    "backend/kernels/k5_trust/services.py:credential_fact":
        "위와 같다 — 한 건짜리다. 값을 내보내지 않고 마스킹된 사실만 낸다. "
        "조회 자체가 감사에 남는다(guardianx.k5.credentials). "
        "시험 근거: CredentialObservationTest.test_the_lookup_is_always_masked · "
        "CredentialUsageGateTest.test_both_the_grant_and_the_refusal_are_audited",
    "backend/kernels/k5_trust/services.py:secret_for":
        "★ 값을 내보내는 **유일한 출구**다. 그러나 테넌트 자원이 아니라 우리 계정 키이고, "
        "두 조건(이 환경 상태 typed 이상 · capability 기재)을 넘지 못하면 값을 내주지 않는다"
        "(D-328 — juso 사건이 정확히 여기서 걸렸어야 했다). 허용도 거부도 감사에 남는다. "
        "시험 근거: CredentialUsageGateTest.test_a_key_below_typed_is_refused_to_feature_code · "
        "CredentialUsageGateTest.test_no_audit_row_carries_the_value",
    "backend/kernels/k5_trust/services.py:refresh_credential":
        "이 환경을 다시 보고 표의 상태·확인시각을 갱신한다. 반환하는 것은 상태와 시각이며 "
        "**값도 테넌트 행도 아니다**. 이 함수가 있어서 blockers.yaml 의 "
        "verified_at/verified_by 가 진술이 아니라 조회 결과가 된다(D-323). "
        "시험 근거: CredentialUsageGateTest.test_refresh_writes_the_verification_columns",
}

#: PUBLIC 라우트 면제의 증가금지 래칫. 오늘 실측 4건.
#:
#: 미분류(UNREVIEWED)를 줄이는 가장 쉬운 방법은 PUBLIC 으로 옮기는 것이다.
#: 그 길을 막지 않으면 **커버리지는 오르고 노출은 그대로 남는다.**
#: 늘리려면 대표 승인이 필요하다 — 이 수를 조용히 올리는 것이 그 승인을 건너뛰는 방법이다.
PUBLIC_BASELINE = 4

#: 커널이 아직 없어도 **이 게이트가 잠들지 않게** 한다.
#: 커널 디렉터리가 생기면 그때부터 판정 대상이 되고, 비어 있으면 그렇다고 말한다.
KERNEL_NAMES = ("k1_event", "k2_notify", "k3_dashboard", "k4_report",
                "k5_trust", "k6_feedback", "k7_context")


def _decorator_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    out: set[str] = set()
    for dec in fn.decorator_list:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
    return out


# ---------------------------------------------------------------------------
# D-281 — 1차 판정: **스코프는 시그니처다** (커널 공개 함수의 필수 인자)
# ---------------------------------------------------------------------------
#: 커널 공개 함수가 반드시 받아야 하는 키워드 전용 인자의 이름.
#:
#: 왜 이름 하나를 게이트가 강제하나
#: -------------------------------
#: D-281: *"데코레이터는 '붙였는가'만 보지만, 필수 인자는 **부르는 쪽이 테넌트를 알아야만**
#: 호출된다. 표식이 아니라 구조다 — 우회할 자리가 없다."*
#:
#: 이 검사가 없으면 다음 커널(K2~K7)이 설 때 아무도 이 규칙을 기억하지 못한다.
#: 문서에만 있는 규칙은 지켜진 적이 없다 — `verify_classification` 이 빚 113건을 안고
#: 출발한 것이 그 증거다. **여기서만은 빚 0 으로 시작할 수 있다.**
SCOPE_PARAM = "scope"

#: 이 인자에 기대하는 타입 이름. 어노테이션이 다르면 **경고**로만 남긴다 —
#: 이름이 맞는데 타입만 다른 것은 "생각하지 않은 호출"이 아니라 "다르게 생각한 호출"이고,
#: 그 둘을 같은 강도로 막으면 게이트가 판단이 아니라 잔소리가 된다.
SCOPE_TYPE = "TenantScope"


def _scope_param_problem(key: str, fn) -> str | None:
    """커널 공개 함수가 `*, scope: TenantScope` 를 받는가 (D-281).

    **키워드 전용**이어야 한다. 위치 인자로 두면 순서로도 넘길 수 있고, 그러면
    호출부에서 `scope` 라는 글자가 사라진다 — 읽는 사람이 테넌트를 못 본다.
    """
    kwonly = {a.arg: a for a in fn.args.kwonlyargs}
    if SCOPE_PARAM not in kwonly:
        positional = {a.arg for a in (fn.args.posonlyargs + fn.args.args)}
        if SCOPE_PARAM in positional:
            return (f"{key}: `{SCOPE_PARAM}` 이 **키워드 전용이 아니다.** `*` 뒤로 옮겨라 — "
                    f"위치 인자로 두면 호출부에서 `{SCOPE_PARAM}=` 이라는 글자가 사라지고, "
                    f"읽는 사람이 그 호출이 어느 테넌트로서 일어나는지 못 본다 (D-281)")
        return (f"{key}: 커널 공개 함수인데 키워드 전용 필수 인자 "
                f"`*, {SCOPE_PARAM}: {SCOPE_TYPE}` 이 없다 (D-281). "
                f"커널(L3)에서는 `@tenant_scoped` 를 쓰지 않는다 — "
                f"`request` 가 없어 **표식만 남고 아무것도 안 막기** 때문이다(착시 ①). "
                f"테넌트 없이는 호출 자체가 불가능한 시그니처로 만들어라")

    # 기본값이 있으면 필수가 아니다 — `scope=None` 은 인자를 안 받는 것과 같다.
    idx = [a.arg for a in fn.args.kwonlyargs].index(SCOPE_PARAM)
    default = fn.args.kw_defaults[idx]
    if default is not None:
        return (f"{key}: `{SCOPE_PARAM}` 에 기본값이 있다 — 그러면 **필수 인자가 아니다.** "
                f"기본값을 두는 순간 부르는 쪽이 테넌트를 몰라도 호출이 되고, "
                f"D-281 이 막으려던 그 상태로 돌아간다")
    return None


def _scope_annotation_note(key: str, fn) -> str | None:
    """어노테이션이 `TenantScope` 인가 — 어긋나면 경고 한 줄(막지는 않는다)."""
    for a in fn.args.kwonlyargs:
        if a.arg != SCOPE_PARAM:
            continue
        if a.annotation is None:
            return f"{key}: `{SCOPE_PARAM}` 에 타입 표기가 없다 (기대: {SCOPE_TYPE})"
        text = ast.unparse(a.annotation) if hasattr(ast, "unparse") else ""
        if SCOPE_TYPE not in text:
            return f"{key}: `{SCOPE_PARAM}: {text}` — 기대한 타입은 {SCOPE_TYPE} 이다"
    return None


# ---------------------------------------------------------------------------
# C-3.1 의 두 번째 통과 형태 — **문지기 호출** (P-K1-1 → D-281 이 2차로 확정)
# ---------------------------------------------------------------------------
#: 판정기·문지기 목록을 여기서 다시 정의하지 않는다. 트립와이어가 라우트에 대해 쓰는
#: 것과 **같은 목록**을 쓴다 — 두 벌을 두면 "라우트에서는 문지기인데 커널에서는 아닌 것"이
#: 생기고, 그 어긋남은 아무도 못 본다.
_TRACE_CACHE: dict = {}


def _gatekeeper_names() -> set[str]:
    from common.tenant_tripwire import GATEKEEPER_CALLS
    return set(GATEKEEPER_CALLS)


def _gatekeepers_reached(path: Path, node: ast.AST) -> list[str]:
    """이 커널 함수의 호출 그래프가 **실제 문지기**에 닿는가.

    ★ 왜 `@tenant_scoped` 만으로 판정하지 않나 (P-K1-1)
      `tenant_scoped` 는 인자에서 `request` 를 찾고 못 찾으면 **그냥 통과시킨다**
      (`common/tenant_scope._find_request` → None → 검사 생략).
      커널 서비스 함수에는 `request` 가 없다. 붙이면 **표식만 남고 아무것도 안 막는다** —
      데코레이터 466/466 부착을 완결로 착각했던 착시 ①(D-249)과 똑같은 모양이다.

      그래서 통과 형태를 하나 **더한다.** 이것은 C-3.1 을 **무르게 하는 것이 아니라
      높이는 것**이다 (D-105 저촉 아님): 표식이 아니라 `common.tenant_filters` 의
      진짜 문지기가 호출 그래프에 있어야 인정한다.

      ⚠ C-3.1 문언과 다른 이행이므로 임의로 정하지 않고 `decisions_pending.yaml` 의
        **P-K1-1** 로 적재했다 (D-213). 판정이 나오면 이 함수와 그 항목을 함께 고친다.
    """
    from common import ast_call_trace as trace

    backend = BACKEND
    idx = _TRACE_CACHE.get("idx")
    if idx is None:
        idx = _TRACE_CACHE["idx"] = trace.Index(backend)
    t = idx.trace(node, path)
    return sorted(t.calls & _gatekeeper_names())


def scan_kernels(verbose: bool) -> list[str]:
    """커널 공개 함수를 훑는다. 커널이 없으면 그 사실을 말하고 통과한다."""
    problems: list[str] = []
    if not KERNEL_ROOT.is_dir():
        print(f"[SCOPE] 커널 디렉터리 없음 ({KERNEL_ROOT.relative_to(ROOT).as_posix()}) "
              "— 커널은 WP-2 EXIT 후 K1 부터 선다. 게이트는 그때 자동으로 물린다")
        return problems

    known = set(KERNEL_NAMES)
    seen_kernels = {d.name for d in KERNEL_ROOT.iterdir() if d.is_dir()
                    and not d.name.startswith("_")}
    # ★ 모르는 커널을 만나면 멈춘다 (D-264). 이름이 목록에 없으면 C-1 이 정한 커널이 아니다.
    for name in sorted(seen_kernels - known):
        problems.append(
            f"모르는 커널 디렉터리: backend/kernels/{name} — C-1 의 K1~K7 에 없다. "
            f"새 커널이면 KERNEL_NAMES 와 DA-04 §4 표를 **같은 커밋에서** 함께 고쳐라")

    n_scoped = n_public = n_guarded = 0
    n_sig = 0                      # D-281 1차 — scope 인자를 받는 함수 수
    notes: list[str] = []          # 어노테이션 어긋남 등 경고(막지 않는다)
    for path in sorted(KERNEL_ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if "/tests/" in rel or path.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            problems.append(f"{rel}: 파싱 실패 ({exc.msg} @{exc.lineno}) — 판정할 수 없다")
            continue

        for node in tree.body:                       # 모듈 최상위 = 커널의 공개면
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue                             # 비공개는 커널 밖에서 못 부른다
            key = f"{rel}:{node.name}"

            # ── 1차: 시그니처 (D-281). **면제가 없다** — PUBLIC 등재도 이것을 대신하지 못한다.
            #   PUBLIC 은 "테넌트 데이터를 안 만진다"는 선언이지, "부르는 쪽이 테넌트를
            #   몰라도 된다"는 뜻이 아니다. 그래서 아래 통과 형태들과 **and 로 묶인다.**
            sig_problem = _scope_param_problem(key, node)
            if sig_problem:
                problems.append(sig_problem)
            else:
                n_sig += 1
                note = _scope_annotation_note(key, node)
                if note:
                    notes.append(note)

            # ── 2차: 문지기 / 데코레이터 / PUBLIC 등재
            guards = _gatekeepers_reached(path, node)
            if _decorator_names(node) & SCOPE_DECORATORS:
                n_scoped += 1
                # ★ D-281: 커널에서는 **데코레이터를 쓰지 않는다.** 통과로 세되 반려한다 —
                #   `tenant_scoped` 는 request 를 못 찾으면 그냥 통과시키므로, 커널에 붙은
                #   것은 초록을 칠할 뿐 아무것도 막지 않는다. 붙어 있다는 사실 자체가
                #   "여기는 막혀 있다"는 오해를 만든다.
                problems.append(
                    f"{key}: 커널(L3) 공개 함수에 @tenant_scoped 가 붙어 있다 — "
                    f"D-281 이 **금지**한다. 커널에는 `request` 가 없어 이 데코레이터는 "
                    f"검사를 건너뛰고 통과시킨다(표식만 남는다). "
                    f"`*, {SCOPE_PARAM}: {SCOPE_TYPE}` 시그니처와 문지기 호출로 대신하라")
                if verbose:
                    print(f"  X  {key} — @tenant_scoped (커널 금지, D-281)")
            elif guards:
                n_guarded += 1
                if verbose:
                    print(f"  G  {key} — 문지기: {', '.join(guards)}")
            elif key in KERNEL_PUBLIC:
                n_public += 1
                if verbose:
                    print(f"  P  {key} — PUBLIC: {KERNEL_PUBLIC[key]}")
            else:
                problems.append(
                    f"{key}: 커널 공개 함수인데 @tenant_scoped 도, 문지기 호출도, "
                    f"PUBLIC 등재도 없다 (C-3.1). "
                    f"인정하는 문지기: {', '.join(sorted(_gatekeeper_names()))}. "
                    f"스코프 없이 데이터를 반환하는 커널 함수는 반려한다")

    total = n_scoped + n_guarded + n_public
    # 분모와 술어를 함께 적는다 (D-271 신설 규칙). 분모 없는 초록은 보고가 아니다.
    print(f"[SCOPE] 커널 공개 함수 {total}개 — "
          f"1차 scope 시그니처 {n_sig}/{total} (술어=키워드 전용·기본값 없음, D-281) · "
          f"2차 @tenant_scoped {n_scoped} · 문지기 호출 {n_guarded} · PUBLIC {n_public}")
    for note in notes:
        print(f"  ! {note}")
    return problems


def scan_public_registry() -> list[str]:
    """`PUBLIC_ROUTES` 를 **Django 없이** 정적으로 읽어 사유·증가를 본다."""
    problems: list[str] = []
    if not TENANT_SCOPE.is_file():
        return [f"면제 대장이 없다: {TENANT_SCOPE.relative_to(ROOT).as_posix()} — "
                f"없으면 무엇을 면제했는지 아무도 모른다"]

    tree = ast.parse(TENANT_SCOPE.read_text(encoding="utf-8"))
    routes: dict[str, str] | None = None
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        elif isinstance(node, ast.Assign) and node.targets and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
        if target != "PUBLIC_ROUTES" or not isinstance(node.value, ast.Dict):
            continue
        routes = {}
        for k, v in zip(node.value.keys, node.value.values):
            key = ast.unparse(k) if k is not None else "?"
            routes[key] = v.value if isinstance(v, ast.Constant) else ""

    if routes is None:
        # 이름이 바뀌었거나 형태가 달라졌다 — **못 찾았으면 통과가 아니라 실패**다.
        return ["PUBLIC_ROUTES 를 읽지 못했다 — 이름이나 형태가 바뀌었다면 "
                "이 게이트도 함께 고쳐야 한다. 못 읽은 채 통과시키지 않는다"]

    for key, reason in routes.items():
        if not isinstance(reason, str) or len(reason.strip()) < 5:
            problems.append(f"PUBLIC_ROUTES[{key}] 에 사유가 없다 — "
                            f"사유 없는 면제는 미분류와 구별되지 않는다")

    n = len(routes)
    print(f"[SCOPE] PUBLIC 라우트 면제 {n}건 (래칫 상한 {PUBLIC_BASELINE})")
    if n > PUBLIC_BASELINE:
        problems.append(
            f"PUBLIC 면제가 {PUBLIC_BASELINE} → {n} 로 **늘었다**. "
            f"면제 추가는 대표 승인 사항이다 — 미분류를 PUBLIC 으로 옮기면 "
            f"커버리지는 오르고 노출은 그대로 남는다")
    elif n < PUBLIC_BASELINE:
        print(f"[SCOPE] ↓ 면제가 {PUBLIC_BASELINE} → {n} 로 줄었다 — "
              f"PUBLIC_BASELINE 을 {n} 로 낮춰라")
    return problems


def _norm(s: str) -> str:
    s = s.strip("{}").lower().replace("_", "").replace("-", "")
    if s.endswith("id"):
        s = s[:-2]
    if s.endswith("s"):
        s = s[:-1]
    return s


# ---------------------------------------------------------------------------
# P-93 / P-104 — **판정기가 읽는 자리는 앱이 쓰는 자리여야 한다**
# ---------------------------------------------------------------------------
#: 살아 있는 라우터 실측 하한. 2026-09-07T14:42 · 컨테이너 `gx-shell` 에서
#: `_iter_ninja_apis()` 전수 열거로 **705 오퍼레이션 · 578 경로**를 셌다.
#: 이보다 적게 세면 그것은 「라우트가 줄었다」가 아니라 **열거기나 사진이 낡았다**이다.
#: 수를 낮추려면 그 자리에서 다시 재고 사유를 함께 적어라 — 조용히 낮추면
#: 「못 본 경로」가 다시 초록 뒤에 숨는다 (D-301).
ROUTE_OPS_FLOOR = 705
ROUTE_PATH_FLOOR = 578

#: ★ 2026-08-22 · 531경로짜리 **폐기된 사진**. 여기를 다시 읽는 코드가 생기지 않도록
#:   이름을 남겨 둔다 — 이 판정기는 이 파일을 **읽지 않는다**(읽으면 위반으로 낸다).
DEPRECATED_ROUTE_SNAPSHOT = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "openapi_routes.json"
LIVE_ROUTE_INVENTORY = ROOT / "docs" / "agent" / "evidence" / "D-343" / "route_inventory.json"


def _live_router_paths() -> tuple[list[str], str] | None:
    """**살아 있는 라우터**에서 직접 열거한다 (Django 가 서는 자리에서만).

    ★ P-93 — *판정기가 읽는 근거는 앱이 쓰는 근거여야 한다.*
      이 판정기는 pre-commit(호스트, Django 없음)에서도 돌아야 하므로 여기서
      실패해도 멈추지 않는다. 대신 **살아 있는 실측본**(아래)으로 떨어지고,
      떨어진 사실과 그 실측본의 시각을 출력에 적는다.

    돌려주는 것은 (경로 목록, 어디서 왔는지) 이고, 못 서면 None 이다.
    """
    if os.environ.get("GX_SCOPE_NO_LIVE_ROUTER"):
        return None                     # 시험용 탈출구 — 기본값은 언제나 「살아 있는 쪽부터」
    #: ⚠ `DJANGO_SETTINGS_MODULE` 가 **이미 서 있을 때만** 앱을 세운다. 호스트에서
    #:   설정 이름을 우리가 지어 넣으면 반쯤 선 Django 가 남고, 그 반쪽이 아래
    #:   `common.tenant_tripwire` 판정에 조용히 섞인다. 살아 있는 라우터를 보는
    #:   자리는 컨테이너이고, 그 자리는 이 변수를 언제나 준다.
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return None
    try:
        import django                                    # noqa: PLC0415
        django.setup()
        from common.tenant_scope import _iter_ninja_apis, _join   # noqa: PLC0415
    except Exception:                                    # noqa: BLE001
        return None                                      # 호스트에는 앱이 없다 — 정상이다
    try:
        paths: list[str] = []
        for mount, api in _iter_ninja_apis():
            for prefix, router in getattr(api, "_routers", []) or []:
                for op_path, pv in getattr(router, "path_operations", {}).items():
                    for op in pv.operations:
                        for _m in op.methods:
                            paths.append(_join(mount, prefix, op_path))
    except Exception as exc:                             # noqa: BLE001
        return None if not paths else (paths, f"살아 있는 라우터(부분 열거 — {exc})")
    if not paths:
        return None
    return paths, "살아 있는 라우터 직접 열거 (_iter_ninja_apis)"


def _route_paths() -> tuple[list[str], str, str, list[str]]:
    """라우트 목록을 **살아 있는 자리에서** 가져온다. (경로들, 출처, 잰 때, 위반)."""
    problems: list[str] = []
    live = _live_router_paths()

    inv_paths: list[str] = []
    inv_stamp = "시각 미기재"
    if LIVE_ROUTE_INVENTORY.is_file():
        import json as _json                             # noqa: PLC0415
        _raw = _json.loads(LIVE_ROUTE_INVENTORY.read_text(encoding="utf-8"))
        _rows = _raw.get("routes") or _raw.get("items") or []
        inv_paths = [p for p in
                     (r if isinstance(r, str) else (r.get("path") or "") for r in _rows) if p]
        inv_stamp = _raw.get("measured_at") or _raw.get("generated_at") or "시각 미기재"

    if live is not None:
        paths, why = live
        #: 살아 있는 라우터와 실측본이 갈리면 **실측본이 낡은 것**이다. 조용히 넘기면
        #: 다음 사람이 낡은 사진을 근거로 초록을 낸다 — 이 게이트가 태어난 이유 그대로다.
        if inv_paths and len(inv_paths) < len(paths):
            problems.append(
                f"라우트 실측본이 낡았다: D-343/route_inventory.json 은 {len(inv_paths)}건 "
                f"(잰 때 {inv_stamp}) 인데 살아 있는 라우터는 {len(paths)}건이다 — "
                f"`docker exec gx-shell python /repo/scripts/probe_route_inventory.py "
                f"/docs/agent/evidence/D-343/route_inventory.json` 로 다시 재라 (P-93)")
        return paths, why, "지금 (살아 있는 라우터)", problems

    if not inv_paths:
        #: ★ 여기서 **옛 사진으로 떨어지지 않는다.** 폐기된 사진으로 낸 초록이
        #:   두 달 동안 초록으로 보였다(P-104). 못 읽었으면 통과가 아니라 실패다.
        problems.append(
            f"살아 있는 라우트 실측본이 없다: "
            f"{LIVE_ROUTE_INVENTORY.relative_to(ROOT).as_posix()} — "
            f"폐기된 옛 사진("
            f"{DEPRECATED_ROUTE_SNAPSHOT.relative_to(ROOT).as_posix()} · 2026-08-22 · 531경로)"
            f"으로 **떨어지지 않는다.** 컨테이너에서 다시 재라 (P-93 · P-104)")
        return [], "없음", "못 쟀다", problems

    #: 사진을 읽는 자리에는 **바닥**을 둔다. 사진이 줄면 그것은 라우트가 줄어서가
    #: 아니라 사진이 낡아서다 — 0건 위의 「위반 0」은 초록이 아니다 (D-301).
    if len(inv_paths) < ROUTE_OPS_FLOOR:
        problems.append(
            f"라우트 실측본이 {len(inv_paths)}건이다 — 실측 하한 {ROUTE_OPS_FLOOR}건"
            f"(2026-09-07 살아 있는 라우터 전수)보다 적다. 사진이 낡았거나 열거기가 "
            f"고장 났다. 적은 수로 낸 「라우트가 안 생겼다」는 판정이 아니다 (D-301)")
    return (inv_paths, "D-343/route_inventory.json (살아 있는 실측본 — 라우터가 쓴 것)",
            inv_stamp, problems)


#: ★ [D-272 보강 · 2026-09-18 · 턴 U 병합] **이름이 같다고 같은 자원이 아니다.**
#:
#:   아래 대조는 「`no_route` 라 적어 둔 모델의 이름이 실제 라우트의 한 조각과 같은가」를 본다.
#:   싼 술어이고 지금까지 옳게 잡아 왔다. 그런데 턴 U 에 **U5 의 「카메라 주소 한 대 고치기」**
#:   (`POST /api/dsm/cameras/{int:camera_id}/address`)가 서자, 조각 `address` 가 §0.4 앱의
#:   `delivery.Address` 와 부딪혀 **없는 결함**을 냈다. 그 라우트는 카메라(우리 층)의 주소 칸을
#:   고치는 문이고 택배 주소 모델과 아무 관계가 없다.
#:
#:   ⚠ 술어를 **느슨하게 만들지 않는다.** 대신 **부딪힘을 이름으로 등재**한다 — KERNEL_PUBLIC ·
#:     DECLARED_UNWIRED · PUBLIC_BY_DESIGN 과 같은 결이다: 면제가 아니라 **선언**이고, 사유가 없으면
#:     못 올린다. 등재되지 않은 새 부딪힘은 여전히 빨강이다(래칫은 살아 있다).
#:   ⚠ 등재는 **(모델, 경로) 한 쌍**으로만 한다. 모델 전체를 면제하면 그 모델에 진짜 라우트가
#:     생기는 날 아무도 모른다.
NO_ROUTE_NAME_COLLISION: dict[tuple[str, str], str] = {
    ("delivery.Address", "/api/dsm/cameras/{int:camera_id}/address"):
        "우리 층의 **카메라 설치 주소** 칸을 한 대씩 고치는 문이다(U5 #5 · 턴 U · WS-23 · "
        "`apps/dsm/api_u56.py`). 자원은 `stream_monitors.StreamMonitor` 이고 `delivery.Address` 는 "
        "한 번도 불리지 않는다 — 부딪힌 것은 **조각 이름**(`address`)뿐이다. "
        "근거: 그 라우트의 문지기·시험이 전부 카메라를 잰다(`tests/test_camera_address_write.py` · "
        "`tests/test_u56_turn_u_admin_surfaces.py`) · `delivery/` 는 §0.4 라 이 턴에 한 줄도 안 고쳤다",
}


def scan_no_route_models() -> list[str]:
    """`no_route` 로 등재된 모델에 **라우트가 생겼는지** 본다 (D-272).

    D-272 는 `no_route` 를 "면제가 아니라 등재"로 못 박고,
    **라우트가 추가되면 재검사되도록 게이트에 연결**하라고 했다. 여기가 그 연결이다.

    `no_route` 는 "닿을 수 없다"는 **그 시점의 사실**이다. 라우트 하나가 추가되면
    그 사실은 조용히 거짓이 되고, 아무도 그 모델을 다시 보지 않는다 —
    인구조사가 행 0 인 모델 25종을 못 보던 것과 같은 모양이다.

    ★ [실측 2026-09-07 · 턴 K · P-104] **이 칸은 거짓 초록이었다.**
      여기가 읽던 `W0-14/openapi_routes.json` 은 **2026-08-22 · 531경로**다.
      살아 있는 라우터는 같은 날 **705 오퍼레이션 · 578 경로** — 즉 이 칸은
      **새로 난 경로를 한 개도 안 보고** 「라우트가 안 생겼다」를 냈다.
      D-272 가 이 칸을 만든 이유가 「라우트 하나가 추가되면 no_route 는 조용히
      거짓이 된다」인데, **그 추가를 못 보는 사진**을 들고 있었다.

      → P-93: **판정기가 읽는 자리는 앱이 쓰는 자리여야 한다.**
        ① 살아 있는 라우터(컨테이너에서 돌 때) ② 라우터가 쓴 실측본(호스트)
        ③ **옛 사진으로는 떨어지지 않는다** — 못 읽었으면 통과가 아니라 실패다.
    """
    import ast as _ast

    census = ROOT / "backend" / "tests" / "tenant_census.py"
    if not census.is_file():
        return [f"인구조사를 못 찾았다 ({census.name}) — 못 읽은 채 통과시키지 않는다"]

    tree = _ast.parse(census.read_text(encoding="utf-8"))
    table = None
    for node in _ast.walk(tree):
        tgt = None
        if isinstance(node, _ast.AnnAssign) and isinstance(node.target, _ast.Name):
            tgt = node.target.id
        elif isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            tgt = node.targets[0].id
        if tgt == "CENSUS" and isinstance(node.value, _ast.Dict):
            table = {k.value: _ast.literal_eval(v)
                     for k, v in zip(node.value.keys, node.value.values)}
    if table is None:
        return ["tenant_census.CENSUS 를 읽지 못했다 — 형태가 바뀌었다면 게이트도 함께 고쳐라"]

    paths, routes_why, _stamp, problems = _route_paths()
    if not paths:
        #: 라우트를 한 건도 못 셌다. **0건 위의 「위반 0」은 초록이 아니다** (D-301).
        print(f"[SCOPE] no_route 대조 **못 했다** — 라우트 0건 · 출처 {routes_why}")
        return problems
    n = 0
    n_collision = 0
    for label, entry in table.items():
        if entry[1] != "no_route":
            continue
        n += 1
        model = label.split(".")[-1]
        for path in paths:
            parts = [s for s in path.split("/") if s]
            if any(_norm(s) == _norm(model) for s in parts):
                if (label, path) in NO_ROUTE_NAME_COLLISION:
                    n_collision += 1
                    continue          # 선언된 이름 부딪힘 — 사유가 위에 적혀 있다
                problems.append(
                    f"{label} 은 no_route 로 등재돼 있는데 라우트가 실재한다: {path} — "
                    f"인구조사를 다시 만들고 그 모델을 재검사하라 (D-272)")
                break
    #: ★ **무엇을 몇 건 보고 한 말인지 적는다**(D-301). 이 줄이 없어서
    #:   531라우트짜리 옛 사진으로 낸 초록이 두 달 동안 초록으로 보였다.
    if n_collision:
        #: **선언한 것은 수로 적는다** — 조용히 지나가면 다음 사람은 이 대조가 무엇을 봤는지 모른다.
        print(f"[SCOPE] 이름 부딪힘 선언 {n_collision}건 — 조각 이름만 같고 자원이 다른 자리"
              f"(NO_ROUTE_NAME_COLLISION · 사유 등재)")
    print(f"[SCOPE] no_route 등재 {n}종 — 라우트 {len(paths)}건(고유 {len(set(paths))}경로)과 "
          f"대조 (D-272) · 출처 {routes_why} · 잰 때 {_stamp}")
    return problems


def scan_route_tripwire(write_baseline: bool) -> list[str]:
    """★ 신규 경로 트립와이어 — **정적 눈** (D-275 §5-1).

    "라우트가 테넌트 모델을 만지는데 문지기가 하나도 없으면 unguarded" 를 판정하고,
    **등재부에 없던 unguarded 가 나타나면 실패**한다.

    판정기는 `backend/common/tenant_tripwire.py` 한 벌뿐이고, 여기는 그것에
    **정적 열거**를 먹인다. 런타임 전수 열거는 `tests/test_route_tripwire.py` 가 한다.

    ※ 왜 수가 아니라 이름인가: `PUBLIC_BASELINE` 처럼 수로 잠그면 낡은 라우트가 하나
      지워질 때마다 새 라우트 하나가 조용히 들어올 자리가 생긴다. 수는 그대로인데
      노출은 바뀐다. 그래서 이 게이트는 라우트 **하나하나의 이름**을 등재부에 적는다.
    """
    try:
        from common import tenant_tripwire as tw
    except Exception as exc:   # pragma: no cover - 판정기가 없으면 통과가 아니라 실패다
        return [f"트립와이어 판정기를 못 불렀다 ({exc}) — "
                f"backend/common/tenant_tripwire.py 가 있어야 한다. "
                f"판정기 없이 통과시키지 않는다"]

    rep = tw.compare(tw.Report("static", tw.scan_static()))
    print(rep.summary)
    for note in rep.notes:
        print("  · " + note)

    if write_baseline:
        import json
        path = tw.baseline_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = tw.build_baseline([rep], _today())
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + chr(10),
                       encoding="utf-8")
        os.replace(tmp, path)          # D-270 ① 원자 교체 — 원본을 truncate 하지 않는다
        print(f"[SCOPE] 등재부(정적 구획)를 다시 썼다: {path} — 커밋할 것. "
              f"런타임 구획은 건드리지 않았다")
        return []

    return rep.problems


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="함수별 상태를 전부 출력한다")
    ap.add_argument("--write-baseline", action="store_true",
                    help="트립와이어 등재부의 **정적 구획만** 다시 쓴다 (런타임 구획 보존)")
    args = ap.parse_args()

    print("[SCOPE] 커널 테넌트 스코프 대조 (C-3.1 · D-105 · K5)")
    problems = (scan_kernels(args.list) + scan_public_registry() + scan_no_route_models()
                + scan_route_tripwire(args.write_baseline))

    for key, why in KERNEL_PUBLIC.items():
        if len(why.strip()) < 10:
            problems.append(f"KERNEL_PUBLIC['{key}'] 에 사유가 없다")

    print()
    if problems:
        print(f"[SCOPE] 위반 {len(problems)}건 — 멈춘다")
        for p in problems:
            print("  · " + p)
        return 1
    print("[SCOPE] 통과")
    print("[SCOPE] ※ 라우트 단위 스코프는 이 게이트가 아니라 "
          "backend/tests/test_route_tenant_scope.py 가 본다 (Django 필요). 중복해서 세지 않는다")
    print("[SCOPE] ※ 트립와이어의 **런타임 전수 열거**는 backend/tests/test_route_tripwire.py 가 "
          "한다 (D-275 §5-1). 판정기는 한 벌이고 눈만 둘이다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header, file_stamp  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        #: ★ 출생 표본 ① 이 바로 이 게이트다 — 8월 사진(531)을 읽으며 초록이었다.
        #:   지금은 살아 있는 라우터를 순회하고, 그 사진은 **하한 대조로만** 쓴다.
        #:   그래서 사진의 날짜를 여기 그대로 적는다 — 날짜 없는 사진은 다시 그 사고다.
        source=("살아 있는 라우터 (gx-shell 안 django-ninja 레지스트리를 순회한다 · "
                "ROUTE_OPS_FLOOR=%d 아래면 회색) · 하한 대조로만 쓰는 옛 사진: %s"
                % (ROUTE_OPS_FLOOR, file_stamp(DEPRECATED_ROUTE_SNAPSHOT))),
        #: ★ [P-204 · 턴 Z · Q] **출생 표본 ① 의 죄는 분모였다** — 8월 사진의 531 을
        #:   분모로 삼아 초록이었고, 살아 있는 라우터는 705 였다. 그래서 여기서는
        #:   분모를 사진에서 읽지 않고 **살아 있는 레지스트리에서 지금 뽑는다.**
        measured=("살아 있는 라우터의 라우트를 **하나씩** 순회해 테넌트 스코프를 "
                  "지나는지 본다 — **분모는 이 실행에서 뽑은 라우트 전수**이고 "
                  "**하한 %d** 아래면 회색이다(사진 분모로 내려앉지 않게) · "
                  "커널 공개 면 **분모 %d**(KERNEL_PUBLIC) · 이름 부딪힘 선언 %d건. "
                  "gx-shell 에 못 닿으면 **분모 0 — 안 쟀다**(회색 2)"
                  % (ROUTE_OPS_FLOOR, len(KERNEL_PUBLIC),
                     len(NO_ROUTE_NAME_COLLISION))),
    )
    raise SystemExit(main())
