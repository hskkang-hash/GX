# -*- coding: utf-8 -*-
"""K2 알림 커널 — **공개 면**.

App(L4)이 만질 수 있는 것은 여기 있는 이름뿐이다. `scripts/verify_layers.py` 가
그 밖의 import 를 exit 1 로 막는다 (D-278 · DA-04 §1-4).

    from kernels.k2_notify import send, resolve_recipients      # 이렇게 쓴다
    from stream_monitors.models import DeliveryRecord           # 이러면 CI 가 막는다

목록은 **DA-04 §2 K2 표 그대로**다. 표를 바꾸려면 그 문서와 이 파일과
`tests/test_k2_notify_kernel.KernelPublicSurfaceTest.SURFACE` 를 **같은 커밋에서** 고친다.

★ 표는 저장소를 하나만 쓴다 — `DeliveryRecord` 가 알림 이력이자 **K4 의 조치 이력**이다.
  두 벌로 적재하면 알림과 보고서가 다른 말을 한다 (DA-04 K2 이중 AC).
"""
from kernels.k2_notify.exceptions import (
    CriticalWithoutRecipients,
    EventNotFound,
    InvalidNotifyInput,
    NotifyPermissionDenied,
    K2Error,
    NoRecipients,
    NotImplementedYet,
)
from kernels.k2_notify.schemas import (
    F10_MAX_LATENCY,
    SUPPRESS_WINDOW,
    DeliveryView,
    Recipient,
    RuleView,
)
from kernels.k2_notify.renotify import (
    DEFAULT_RENOTIFY_AFTER,
    MAX_RENOTIFY_AFTER,
    MIN_RENOTIFY_AFTER,
    RenotifyResult,
    renotify,
)
from kernels.k2_notify.alarm_budget import (
    BUDGET_OK,
    BUDGET_ORANGE,
    BUDGET_WINDOW_DAYS,
    EEMUA_191_ALARMS_PER_OPERATOR_HOUR,
    AlarmBudgetView,
    simulate_alarm_budget,
)
from kernels.k2_notify.heartbeat import (
    DEAD_MAN_RULE,
    DIGEST_ACTION,
    DIGEST_GRACE,
    DIGEST_HOUR,
    DIGEST_LOGGER,
    HeartbeatDigestResult,
    digest_clock,
    heartbeat_watch,
    send_heartbeat_digest,
)
from kernels.k2_notify.services import (
    list_deliveries,
    notice_false_positive,
    resolve_recipients,
    save_notification_rule,
    send,
    suppress,
)
# ★ [턴 S · 차선 U56 · WS-14] S-16 「알림 받는 사람·채널」의 서버 면.
#   **`services` 뒤에 온다** — `rule_admin` 이 `services` 를 부르므로 순서가 곧 초기화
#   순서다. 앞에 두면 부분 초기화된 패키지를 만진다.
from kernels.k2_notify.rule_admin import (
    CRITICAL,
    NotifyReach,
    my_notify_reach,
    notify_rule_overview,
    save_rule,
    send_test_notification,
)
# ★ [턴 T · 차선 U3 · P-160 ③] 웹푸시 발송 문 — **부르는 쪽과 같은 커밋에 열린다**
#   (`apps/dsm/notify_prefs.send_test_push` 가 이 이름을 부른다 · `webpush.py` 머리말).
#   턴 S 에 이 한 줄을 넣지 않은 이유(아무도 안 부르는 공개 면 = 잠든 코드)가 이번에 풀렸다.
from kernels.k2_notify.webpush import (
    CHANNEL_NOT_CHOSEN_REASON,
    QUIET_HOURS_REASON,
    WebPushNotConfigured,
    send_webpush,
    webpush_missing_env,
)

__all__ = [
    # DA-04 §2 K2 공개 면 4개
    "resolve_recipients",
    "send",
    "suppress",
    "list_deliveries",
    # ★ P-16 오탐 ③ — 알림이 나간 이벤트가 오탐이 되면 원 수신자에게 **1회** (2026-09-20).
    #   발송이 아니라 **뒷정리**라 `DeliveryRecord` 행을 만들지 않는다 — 그 표는
    #   F-10 의 30초와 5분 억제를 재는 자리다(함수 머리말 ★★).
    "notice_false_positive",
    # ★ P-20 ① 알림 규칙 쓰기 면 — **개발 DB 규칙 0건**이 이 이름을 만들었다 (2026-09-22).
    #   격리 대장(`tests/test_tenant_isolation.WRITE_NO_PROBE`)에 **선등재된 이름**이고,
    #   면이 실제로 열렸으므로 그 줄은 probe 로 옮겨져야 한다(P-8).
    "save_notification_rule",
    # ★ 턴 S · 차선 U56 (WS-14) — S-16 「알림 받는 사람·채널」(UX-43).
    #   `save_rule` 은 `save_notification_rule` **위에** 선다: 종전 문은 「규칙 한 줄이
    #   말이 되는가」를 묻고(시드도 지난다), 이 문은 「저장 뒤에도 심각이 사람에게
    #   닿는가」를 묻는다(사람의 화면만 지난다). 두 문턱을 한 함수에 섞으면 시드가
    #   첫 규칙을 세우는 순간 스스로 막힌다 — `rule_admin` 머리말 참조.
    "notify_rule_overview",
    "save_rule",
    "send_test_notification",
    #: S-15 「내 정보」 — **읽기뿐이다.** 「내 알림 설정」의 쓰기 면은 WS-02(U3).
    "my_notify_reach",
    "CRITICAL",
    "NotifyReach",
    # ★ 턴 T · U3 (P-160 ③) — 웹푸시 「내 기기로 지금 한 통」. 행은 `channel=webpush` 로
    #   남고 훈련 표식(`drill:`)을 달아 5분 억제의 근거가 되지 않는다.
    "send_webpush",
    "webpush_missing_env",
    "WebPushNotConfigured",
    #: M4 설정이 발송을 막았을 때 행에 남는 사유 **이름** — 화면·시험이 같은 글자를 본다.
    "QUIET_HOURS_REASON",
    "CHANNEL_NOT_CHOSEN_REASON",
    # ★ 차선 Q (2026-09-04) OPS-14 생존 알림 — **매일 08:00 1통. 안 오면 장애다.**
    #   격리 대장(`tests/test_tenant_isolation.WRITE_NO_PROBE`)에 **선등재된 이름**이고,
    #   면이 실제로 열렸으므로 그 줄은 probe 로 옮겨져야 한다(P-8).
    #   ⚠ 이 발송은 `DeliveryRecord` 행을 만들지 않는다 — 그 표는 이벤트에 매달려
    #     F-10 의 30초를 재는 자리다. 생존 알림은 `logger.AuditLogs` 에 한 줄로 남는다.
    "send_heartbeat_digest",
    "heartbeat_watch",
    "digest_clock",
    # ★ 차선 Q (2026-09-04) QA-12 알림 예산 — **저장 전에 건수를 말한다.**
    #   읽기 전용이다: 규칙도 발송 이력도 만들지 않는다.
    "simulate_alarm_budget",
    # ★ 차선 D (2026-09-04) 재알림 N분 — **U3 「내가 놓친 알림」의 자리**.
    #   격리 대장(`tests/test_tenant_isolation.WRITE_NO_PROBE`)에 **선등재된 이름**이고,
    #   면이 실제로 열렸으므로 그 줄은 probe 로 옮겨져야 한다(P-8).
    #   ⚠ 5분 억제는 **같은 이벤트의 재발송을 접지 않는다** — 문턱은 이 모듈이 따로 잰다.
    "renotify",
    # 나가는 값의 모양
    "Recipient",
    "DeliveryView",
    "RuleView",
    "RenotifyResult",
    "AlarmBudgetView",
    "HeartbeatDigestResult",
    # 오류 계약
    "K2Error",
    "EventNotFound",
    "InvalidNotifyInput",
    "NotifyPermissionDenied",
    "NoRecipients",
    # ★ 턴 S · U56 — 「저장하면 심각이 0명이 된다」. `NoRecipients`(발송 시점)와
    #   **다른 사실**이다: 그쪽은 꺼진 것을 알리고 이쪽은 꺼지는 것을 막는다.
    "CriticalWithoutRecipients",
    "NotImplementedYet",
    # 계약이 정한 숫자 — 화면·시험·보고서가 **같은 값**을 본다 (D-212)
    "F10_MAX_LATENCY",
    "SUPPRESS_WINDOW",
    # 재알림 창의 기본·상한·하한. 화면이 자기 숫자를 들지 않는다 (D-212).
    "DEFAULT_RENOTIFY_AFTER",
    "MAX_RENOTIFY_AFTER",
    "MIN_RENOTIFY_AFTER",
    # ★ 알림 예산의 상한은 **우리가 지은 수가 아니다** — EEMUA 191 [인용] (QA-12).
    #   이름에 출처를 박아 둔다: `MAX_ALARMS` 였다면 불편할 때 누군가 8로 고쳤을 것이다.
    "EEMUA_191_ALARMS_PER_OPERATOR_HOUR",
    "BUDGET_WINDOW_DAYS",
    "BUDGET_OK",
    "BUDGET_ORANGE",
    # ★ 생존 알림의 규약 — 매뉴얼 첫 쪽이 이 문장을 인용한다 (OPS-14).
    "DIGEST_HOUR",
    "DIGEST_GRACE",
    "DIGEST_LOGGER",
    "DIGEST_ACTION",
    "DEAD_MAN_RULE",
]
