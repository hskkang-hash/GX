#!/usr/bin/env python
"""착시 ⑥ **스키마의 착시** — 필드가 있으면 기능이 있다고 읽는다 (D-304).

    `clip_path` : 정의 1건 · 읽기 2곳 · **쓰기 0곳.**
    읽는 코드가 있으니 살아 있는 것처럼 보이고, 시험은 읽기만 지나가며 초록이 된다.
    **쓰기가 없는 필드는 "구현된 것처럼 보이는 미구현"이다.**

이 스크립트가 하는 일
---------------------
모델 필드를 **전수** 세고, 그중 **저장소 코드가 한 번도 쓰지 않는 필드**를 낸다.
화이트리스트(`DECLARED_UNWIRED`)에 「사유 + 결정 번호」와 함께 등재된 것만 통과하고,
그 밖에 한 건이라도 있으면 exit 1 이다.

    python scripts/verify_dead_fields.py             # 판정
    python scripts/verify_dead_fields.py --list      # 죽은 필드 전수
    python scripts/verify_dead_fields.py --census    # 모수·술어와 함께 전체 표
    python scripts/verify_dead_fields.py --self-test # 양성·음성 대조 (D-277)

★ 술어를 먼저 밝힌다 (D-271 ③ 모수와 술어)
-------------------------------------------
  모수 : `backend/**/models.py` 의 Django 모델 필드 전수
         (dj-core 가 주는 상속 필드는 **세지 않는다** — §0.4 관할 밖이고 우리가 못 고친다)
  술어 : 그 이름이 아래 **DB 를 바꾸는 자리** 중 하나로 나타나는가
           ① ORM 쓰기 호출의 키워드 인자  `create(f=…)` · `update(f=…)` · `get_or_create` ·
                                          `update_or_create` · `bulk_create`
           ② 속성 대입의 좌변              `obj.f = …`
           ③ `update_fields` 문자열        `save(update_fields=["f"])`
           ④ **`defaults=` 사전의 키**      `update_or_create(defaults={"f": …})`
                                          — `*_or_create` 는 **그 사전으로 쓴다**
                                            (턴 AB 에 이 갈래가 없어 거짓 빨강이 났다)
         **읽기는 세지 않는다.** 이 스크립트가 찾는 것이 정확히 "읽기만 있는 필드" 이기 때문이다.

  ★ 첫 판은 **모든 키워드 인자**를 쓰기로 셌다. 그래서 `EventView(clip_path=row.clip_path)`
    처럼 **값을 실어 나르는 자리**가 쓰기로 잡혔고, 판정기는 이 결정문을 만든 바로 그 필드
    (`clip_path`)를 **살아 있다고 답했다.** 심어 보고 잡은 것이 아니라 실측에서 드러났다 —
    자기시험이 합성 예제만 봤기 때문이다(착시 ④의 작은 판). 그래서 술어를 ORM 쓰기 동사로
    좁혔고, 자기시험에 그 갈래를 넣었다.

  ⚠ 좁힌 술어는 **놓치는 쪽**이 아니라 **잡는 쪽**으로 틀린다: `apps.get_model` 로 만든
    모델에 setattr 로 쓰는 자리 등은 여전히 ②가 잡지만, 동적 쓰기는 놓칠 수 있다.
    그래서 이 게이트는 **래칫**이다 — 오늘의 빚을 이름으로 잠그고 새 빚만 막는다.

  ⚠ 시험 코드의 쓰기는 **따로 센다.** 시험만 쓰는 필드는 운영에서 죽은 것이다 —
    그 구별이 없으면 픽스처 한 줄이 죽은 필드를 살아 있게 만든다.
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

_SKIP_DIRS = {"__pycache__", "migrations", ".venv", "node_modules", "venv"}

#: 필드로 세지 않는 이름. Django/dj-core 가 자동으로 넣거나 관리하는 것들이다 —
#: 우리 코드가 안 써도 그것은 미구현이 아니라 프레임워크의 몫이다.
FRAMEWORK_FIELDS = {
    "id", "created_on", "modified_on", "created_by", "modified_by",
    "deleted", "deleted_by_cascade", "group", "groups",
}

#: 필드 선언으로 인정하는 모듈 접두. `models.CharField(...)` 형태를 본다.
_FIELD_CALL_PREFIX = ("models.", "django.db.models.")

#: **DB 를 바꾸는 호출.** 여기 없는 호출의 키워드 인자는 쓰기로 세지 않는다 —
#: 값 객체 생성자를 쓰기로 세면 `EventView(clip_path=row.clip_path)` 가 쓰기가 되고,
#: 그러면 이 판정기는 자기가 태어난 이유(`clip_path`)를 못 본다. 실제로 그랬다.
#: M2M 은 `zone.cameras.set([...])` 형태라 인자에 이름이 없다 — ②(속성 대입)도 아니다.
#: 그래서 `set`·`add` 는 **호출 대상의 속성 이름**으로 따로 센다(아래 참조).
ORM_WRITE_CALLS = frozenset({
    "create", "update", "get_or_create", "update_or_create", "bulk_create",
    "bulk_update",
})

#: M2M 쓰기 동사. `obj.<field>.set(...)` · `.add(...)` · `.remove(...)` · `.clear()`
M2M_WRITE_CALLS = frozenset({"set", "add", "remove", "clear"})

#: ★ [턴 AB] **이름 붙은 사전으로 쓰는 호출** — `*_or_create` 둘뿐이다.
#:   이 둘만 `defaults=` 사전의 **키**를 필드로 쓴다. 다른 ORM 쓰기는 키워드 인자의
#:   **이름**이 곧 필드라 ①이 이미 본다.
DEFAULTS_DICT_CALLS = frozenset({"get_or_create", "update_or_create"})
#: 그 사전의 이름. `create_defaults` 는 Django 5 의 `update_or_create` 가 받는 짝이다.
#: ⚠ **이름이 붙은 것만** 센다 — 아무 사전이나 세면 진짜 죽은 필드가 숨는다.
DEFAULTS_KWARGS = frozenset({"defaults", "create_defaults"})

# ═══════════════════════════════════════════════════════════════════════════
# 화이트리스트 — **「선언된 미구현 + 사유 + 결정 번호」가 있는 것만**
# ═══════════════════════════════════════════════════════════════════════════
#: 이름 → 사유. 사유에 결정 번호(D-nnn 또는 DA-nn)가 없으면 이 스크립트가 스스로 거부한다.
#: 등재는 면제가 아니라 **선언**이다 — 여기 이름을 적는 일이 곧 "이것이 아직 배선되지
#: 않았음을 알고 있다"는 진술이고, 그 진술은 다음 사람이 읽는다 (D-264 · D-281 계열).
DECLARED_UNWIRED: dict[str, str] = {
    # ── D-463 · 2026-09-15 턴 Q — **v1.1 표 일곱은 배선보다 먼저 태어났다.**
    #    WO-01 §5 가 스키마 일곱을 파 1 에 **한 벌로** 내라고 정했다(마이그레이션 두 벌 금지).
    #    그래서 칸이 라우트보다 먼저 섰다 — 이것이 착시 ⑥(D-304)의 모양이라는 것을 안다.
    #    각 줄은 **누가 · 언제 배선하는가**를 적는다. 배선되면 이 게이트가 「등재를 지워라」로
    #    빨개진다(D-338 선례) — 이 등재는 면제가 아니라 **만료일이 적힌 이름표**다.
    # ── D-463 인계 자동 초안(UX-34) 넷 — **2026-09-16 턴 R 에 지웠다.**
    #    `handled_count` · `system_event_count` · `unresolved_count` ·
    #    `unresolved_event_ids` 가 여기 있었다. 사유는 「U1 차선 파 1 턴 2 가 쓴다」였고,
    #    **그 턴이 왔다** — `apps/dsm/handover_service.py` 가 넷을 쓴다.
    #    ★ 이 게이트가 먼저 알아냈다: 쓰기가 생기자 「등재를 지워라」로 빨개졌다.
    #      등재는 면제가 아니라 **만료일이 적힌 이름표**라고 적어 둔 그대로다.
    # ── D-463 내 알림 설정(UX-43-M4 · UX-48) 셋 — **2026-09-16 턴 S 에 지웠다.**
    #    `quiet_start` · `quiet_end` · `zone_ids` 가 여기 있었다. 사유는 「U3 차선 파 2
    #    **턴 4** 의 `me/notify-prefs` 가 쓴다」였는데, **파 2 턴 1 에 왔다** —
    #    `apps/dsm/notify_prefs.py` 가 셋을 쓰고 `PUT /api/dsm/me/notify-prefs` 가 그 문이다.
    #    ★ **이름표가 예정보다 세 턴 일찍 만료됐고, 그것을 사람이 아니라 게이트가 알아냈다.**
    #      아무도 「이제 배선했으니 등재를 지워 주세요」라고 말하지 않았다 — 쓰기가 생기자
    #      판정기가 「등재를 지워라」로 빨개졌다. 등재는 면제가 아니라 만료일이 적힌 이름표다.
    #    ⚠ 이 수정은 **배선과 같은 커밋에 들어가야 한다**(턴 R 에 배운 것): pre-commit 은
    #      스테이징 안 된 변경을 치워 두고 재므로, 판정기만 따로 두면 **옛 판정기가 새 코드를
    #      재서** 같은 자리에서 또 막힌다.
    # ── D-463 온보딩 진행률(UX-46) 둘 — **2026-09-16 턴 R 에 지웠다.**
    #    `card_key` · `source_ref` 가 여기 있었다. 사유는 「F 차선 파 1 턴 2 자동 완료
    #    훅이 쓴다」였고, **그 턴이 왔다** — `apps/dsm/onboarding.py` 가 둘을 쓴다.
    #    카드의 완료는 서버 기록이 닫는다(WO-01 §12) — 그 기록이 `source_ref` 였고,
    #    이제 그 이름이 실제로 채워진다.
    # ── D-514(P-224) · 2026-09-21 턴 AB — **청구 표식 칸이 발급 배선보다 먼저 태어났다.**
    #    대표 ⑧ 「청구 표식을 더해라」를 P-224 로 집행했고, 결정문은 **D-514** 다.
    #    카메라 표는 **우리 것**이라 칸(`data_source`)을 더했고,
    #    소급은 마이그레이션이 **한 번** 찍는다(pk 로 얼린 22줄).
    #    그러나 **새로 태어나는 카메라에 그 칸을 쓰는 운영 자리가 아직 없다** —
    #    차선 B 가 스스로 「넘김 — 발급 순간 배선 다섯 자리」로 적은 바로 그것이다.
    #    ★ 이것이 **착시 ⑥ 그대로의 모양**임을 안다. 숨기지 않고 적는다.
    #    ★ 기본값 `live` 는 쓰기가 아니다 — 기본값으로 태어난 칸은 「누가 정했는가」를
    #      모른다. 그래서 이 등재는 「문제 없다」가 아니라 **만료일이 적힌 이름표**다.
    #    배선할 자리(턴 AC · 보고 §13 ③): 게이트 탐침 카메라(`scripts/probe_*`) ·
    #    온보딩 계측기(`measure_onboarding_t.py`) · 훈련 창(`stream_monitors/services/drill.py`).
    #    ⚠ 배선되는 순간 이 게이트가 「등재를 지워라」로 빨개진다 — 그것이 이 목록의 뜻이다.
    "stream_monitors.StreamMonitor.data_source": (
        "D-514(P-224) · 턴 AB. 청구에서 씨앗을 빼는 칸 — 소급은 마이그레이션이 한 번 챠고, "
        "새로 태어나는 카메라에 쓰는 자리는 턴 AC 에 배선한다(보고 §13 ③ · 다섯 자리). "
        "기본값 `live` 는 쓰기가 아니다."),
    **{f"stream_monitors.DsmReportRun.{f}": (
        "D-463. 월간 자동본 실행 기록(UX-40)의 칸 — U24 차선 파 3 턴 5 `monthly_report.py` "
        "배치가 쓴다.")
       for f in ("trigger", "period_start", "period_end")},
    # ── D-463 둘 — **2026-09-17 턴 T 에 지웠다(차선 F · 게이트가 먼저 알아냈다).**
    #    `DsmUpperReportFlag.reported_at`(사유 「U24 파 2 턴 4 상급 보고 체크가 쓴다」) ·
    #    `WebhookSubscription.filters`(사유 「U56 파 2 턴 4 webhook filters 가 쓴다」) 가 여기 있었다.
    #    **그 턴이 왔다** — 같은 턴에 U24(`apps/dsm/api_u24.py`) · U56(`webhook filters`) 이 둘을 쓰자
    #    이 판정기가 「등재를 지워라」로 빨개졌다(exit 1 · 2건). 등재는 면제가 아니라 만료일이 적힌
    #    이름표다. ⚠ 이 삭제는 **그 배선과 같은 커밋 셋에 들어가야 한다** — 배선 없이 이 삭제만
    #    가면 같은 게이트가 「죽은 필드」로 반대쪽에서 빨개진다.
    # ── D-330 카메라 설치 주소 — **2026-09-07 지웠다 (D-338).**
    #    세 줄이 여기 있었다. 「운영자가 채우는 값이라 코드가 안 쓴다」가 사유였다.
    #    ★ 그 사유는 틀리지 않았지만 **결론이 틀렸다.** 채우는 수단이 없으면 그 값은
    #      영원히 안 채워지고, 등재는 그 사실을 덮는 이름표가 된다 — 착시 ⑥(D-304).
    #    쓰기 지점이 섰으므로(set_camera_address) 등재할 이유가 사라졌다.
    #    ★ 이 게이트가 먼저 알아냈다: 쓰기가 생기자 "등재를 지워라"로 빨개졌다.
    #      낡은 선언이 남으면 **다음에 죽는 필드를 그 이름이 가린다.**
    # ── D-325 표 ① 변경 이력 — Django 가 쓴다.
    "stream_monitors.ThresholdChange.changed_at":
        "D-325. `auto_now_add=True` 다 — **Django 가 쓴다.** 우리 코드가 이 이름을 대입하면 "
        "오히려 시각을 조작할 수 있게 되므로, 쓰지 않는 것이 설계다. "
        "이 판정기의 술어(ORM 쓰기 동사)가 프레임워크 자동 필드를 못 보는 것은 알려진 경계다.",

    "stream_monitors.DetectionEvent.clip_path":
        "D-306 으로 **대체됐다.** 이벤트↔영상 참조는 EventClip(object_key·start_offset·"
        "duration·clip_status)이 들고, 이 칸은 쓰지 않는다. 지우지 않는 이유는 K4 보고서 "
        "스키마가 이 이름을 읽고 있어 제거가 커널 공개 면 변경을 동반하기 때문이다 — "
        "그 제거는 CLIP_EXTRACTION_READY 를 올릴 때 함께 한다. "
        "그때까지 이 칸은 **언제나 비어 있고**, 비어 있다는 사실이 여기 적혀 있다.",

    # ── D-434 · 2026-09-05 턴 C — **삭제가 드러낸 것**. 대표 승인 뒤에 났다.
    #    `stream_monitors/tasks/record_task.py`(328줄 · `RecordingTask`)를 지웠다.
    #    그 파일이 이 칸의 **유일한 기록자**였다.
    "stream_monitors.StreamMonitorRecord.stream_id":
        "D-434. `RecordingTask` 가 지워지면서 쓰기 지점이 0곳이 됐다(D-428 이 지운 두 "
        "모듈이 그 클래스의 유일한 사용처였고, 이번에 클래스까지 지웠다). "
        "★ **읽는 곳도 시험 2곳뿐이다 — 시험만 쓰는 필드는 운영에서 죽은 것이다**(게이트의 말). "
        "그래서 이 등재는 「괜찮다」가 아니라 **「지울 차례인데 아직 못 지웠다」**의 이름표다. "
        "지우려면 마이그레이션이 필요하고 마이그레이션은 되돌리기가 어렵다 — 그리고 "
        "**삭제는 대표 승인 사항**이다(대표 지시 ① 2026-09-26). 그래서 지우지 않고 적어 둔다. "
        "★★ 이것이 이번 사슬의 **세 번째 층**이다: D-428 이 서비스 둘(999줄)을 지우자 "
        "`RecordingTask` 가 드러났고, 그것을 지우자 `redis_client::update_recording_status`(함수)와 "
        "이 칸(필드)이 드러났다. **죽은 코드는 층으로 쌓이고, 한 층을 걷어야 다음 층이 보인다.** "
        "다음 삭제 승인 때 이 칸과 그 함수를 함께 올린다.",

    # ── 우리가 만든 것 중 아직 운영 쓰기 경로가 없는 것 ────────────────────
    #    기준선(옛 빚)에 섞어 두지 않는다. 우리가 만든 것은 우리가 사유를 안다.
    # ★ Zone 의 네 칸은 **2026-09-10 에 등재에서 내려갔다** (D-365 · D-366).
    #   등재문이 예고한 그대로 됐다: *"편집 면이 생기면 이 등재를 지우고 쓰기 격리
    #   시험을 WRITE_PROBES 에 함께 올린다"* — `save_zone` 이 넷을 전부 쓰고,
    #   WRITE_PROBES 에 구역 쓰기 probe 가 올라갔다.
    #   ★ 낡은 선언을 남겨 두지 않는 이유: **남은 선언이 다음에 죽는 필드를 가린다.**
    #     게이트가 그것을 잡아 줬다(「등재에 있는데 이제 쓰인다」).
    # ── 2026-09-10 신설분 (D-368 표 ③) ───────────────────────────────────
    "stream_monitors.GradeRuleChange.changed_at":
        "D-368 로 신설. `auto_now_add=True` 라 **DB 가 채운다** — 우리 코드에 대입문이 "
        "없는 것이 정상이고, 없는 것이 오히려 옳다(사람이 시각을 적으면 그 시각을 "
        "속일 수 있다). 읽기는 `grade_rule_history` 가 한다. "
        "★ 같은 모양의 `ThresholdChange.changed_at`(D-325)과 대칭이며, 그쪽도 같은 "
        "이유로 등재돼 있다. 시험 근거: test_grade_rules.py::"
        "test_the_history_keeps_what_it_was_and_why (이력 행이 실재하고 읽힌다).",

    # ★ [2026-09-18 · 턴 V · 차선 F] `DsmSystemRequest.handled_note` 가 **여기서 빠졌다.**
    #   D-492 가 「만료일이 적힌 이름표」라고 적어 둔 그 줄이고, 그 만료일이 왔다:
    #   점검 창 기록 문(`POST /api/dsm/system/requests/{id}/handled` ·
    #   `apps/dsm/api_f_ops.py`)이 이 칸을 쓴다. 등재 해제와 배선은 **같은 변경**이다 —
    #   따로 두면 그 사이에 판정기가 「등재에 있는데 이제 쓰인다」로 빨개지고, 그 빨강을
    #   보고 배선을 되돌리는 사람이 생긴다. 그 문은 여전히 **서버를 내리지 않는다**:
    #   사람이 점검 창에서 한 일을 적는 칸이지 실행하는 문이 아니다.

    # ★ [2026-09-22 · P-20] `NotificationRule` 의 role·zone·channels 세 칸이 여기서
    #   **빠졌다.** 차선 E2 가 `save_notification_rule` 로 **쓰는 경로**를 열었고,
    #   시드가 그 문으로 규칙 4건을 만들었다 [실측]. 판정기가 「등재를 지워라」로 먼저
    #   말했다 — **낡은 선언이 남으면 다음에 죽는 필드를 그 이름이 가린다**(D-304).
}


#: 오늘의 빚을 **이름으로** 잠근 기준선. 줄어드는 것은 환영이고 실패가 아니다(D-295 규약).
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-304" / "dead_fields_baseline.txt"

#: §0.4 리팩터링 금지구역. 여기 빚은 우리가 못 고친다 — 세되 우리 몫으로 세지 않는다.
FORBIDDEN_APPS = ("delivery", "orders", "terminals")

_BASELINE_HEADER = """\
# 착시 ⑥ 기준선 — **쓰기 0곳 필드의 오늘 목록** (D-304 · 2026-09-02 실측)
#
# ★ 이 파일은 `python scripts/verify_dead_fields.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 왜 면제가 아니라 래칫인가
# -------------------------
# 실측 결과 쓰기 0곳 필드가 **166건**이었다(모수 872). 그중 62건은 §0.4 금지구역
# (delivery·orders·terminals)이라 우리가 고칠 수 없고, 나머지도 대부분 이 저장소가
# 인수하기 전부터 있던 것이다. 전부에 사유를 달라고 하면 그 작업은 **사후 정당화**가
# 되고(D-249 부착률 착시), 그렇다고 게이트를 안 세우면 **새 죽은 필드가 계속 태어난다.**
#
# 그래서 D-270 ③ · D-295 와 같은 방식을 쓴다: 오늘의 빚을 **이름으로** 잠그고,
# 목록 밖의 새 이름이 하나라도 생기면 exit 1. 목록이 줄어드는 것은 환영이다.
#
# ⚠ 이 목록은 **거짓 양성을 포함한다.** 술어가 정적이라 직렬화기가 `Model(**payload)` 로
#   쓰는 자리를 못 본다. 그래서 여기 이름이 있다는 것은 "죽었다"가 아니라
#   **"쓰기를 정적으로 확인하지 못했다"** 이다. 그 구별을 지우지 말 것 (D-301).
#
# ★ 우리가 새로 만든 것은 이 목록이 아니라 `DECLARED_UNWIRED` 로 간다 —
#   거기에는 사유와 결정 번호가 붙고, 배선되면 등재를 지워야 한다.
"""


def load_baseline() -> set[str]:
    if not BASELINE.is_file():
        return set()
    return {ln.strip() for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


def _rel(path: Path) -> str:
    """저장소 기준 상대 경로. 자기시험은 임시 폴더에서 도므로 **밖일 수 있다** —
    그때는 절대 경로를 그대로 쓴다. 여기서 예외가 나면 판정기 자신이 죽는다."""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _py_files(root: Path):
    for p in root.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p


def _is_field_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    src = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
    return src.startswith(_FIELD_CALL_PREFIX) and src.endswith("Field") or (
        src.startswith(_FIELD_CALL_PREFIX)
        and src.rsplit(".", 1)[-1] in {"ForeignKey", "ManyToManyField", "OneToOneField"})


def declared_fields() -> dict[str, str]:
    """`app.Model.field` → 선언 파일. **모수다.**"""
    out: dict[str, str] = {}
    for path in _py_files(BACKEND):
        if path.name != "models.py":
            continue
        app = path.parent.name
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for stmt in cls.body:
                if not isinstance(stmt, ast.Assign) or not _is_field_call(stmt.value):
                    continue
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id in FRAMEWORK_FIELDS:
                        continue
                    out[f"{app}.{cls.name}.{target.id}"] = _rel(path)
    return out


def write_sites() -> tuple[dict[str, int], dict[str, int]]:
    """(운영 코드의 쓰기 수, 시험 코드의 쓰기 수). 이름 단위로 센다.

    ★ 모델별로 가르지 않는다. `apps.get_model(...)` 로 만지는 코드가 많아 어느 모델인지
      정적으로 못 정하는 자리가 흔하고, 거기서 추측하면 **거짓 빨간불**이 난다.
      이름으로 세면 놓칠 수는 있어도 살아 있는 것을 죽었다고 하지는 않는다.
    """
    prod: dict[str, int] = defaultdict(int)
    test: dict[str, int] = defaultdict(int)
    for path in _py_files(BACKEND):
        if path.name == "models.py":
            continue                       # 선언 자체는 쓰기가 아니다
        rel = _rel(path)
        bucket = test if "/tests/" in rel or path.name.startswith("test_") else prod
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # ① ORM 쓰기 호출의 키워드 인자만 센다.
            #   값 객체 생성자(`EventView(clip_path=…)`)는 **쓰기가 아니다** — 그것을 세면
            #   읽어서 실어 나르는 자리가 쓰기로 잡히고, 죽은 필드가 살아 있게 보인다.
            if isinstance(node, ast.Call):
                fname = node.func.attr if isinstance(node.func, ast.Attribute) else ""
                if fname in ORM_WRITE_CALLS:
                    for kw in node.keywords:
                        if kw.arg:
                            bucket[kw.arg] += 1
                # ③ save(update_fields=["x"]) — 어느 호출이든 이 인자는 쓰기의 선언이다
                for kw in node.keywords:
                    if kw.arg == "update_fields" and isinstance(kw.value, (ast.List, ast.Tuple)):
                        for el in kw.value.elts:
                            if isinstance(el, ast.Constant) and isinstance(el.value, str):
                                bucket[el.value] += 1
                # ④ ★★ [실측 2026-09-21 · 턴 AB · 조율자가 찾고 차선 Q 가 고쳤다]
                #   **`update_or_create(defaults={...})` 의 사전 키도 쓰기다.**
                #
                #   이 게이트가 `common.BillingMark.data_source` 를 「새로 생긴
                #   **쓰기 0곳** 필드」로 찍었다. 그런데 운영 코드가 쓴다:
                #       backend/common/billing_marks.py:246-248
                #         Mark._base_manager.update_or_create(
                #             model_label=…, object_id=…,
                #             defaults={"data_source": source, "reason": reason[:500]})
                #   ①은 **키워드 인자의 이름**만 보므로 `defaults` 하나만 세고,
                #   **그 사전 안의 키는 못 봤다.** `*_or_create` 는 **그 사전으로 쓴다.**
                #
                #   ★★ 이 거짓 빨강이 특히 무거운 이유: 이 게이트의 처방은
                #     「배선해라 / 아니면 **죽었다고 선언해라**」인데 둘 다 틀린 답이다
                #     (이미 배선돼 있다). **거짓 빨강이 거짓 선언을 낳는다.**
                #
                #   ⚠ **넓히되 좁게 넓힌다** — 아무 사전이나 세면 **진짜 죽은 필드가
                #     숨는다.** 세 조건을 다 만족해야 한다:
                #       ⒜ 그 호출이 **`*_or_create`** 다 (`create(**payload)` 같은 건 아니다)
                #       ⒝ 키워드 이름이 **`defaults`**(또는 Django 5 의 `create_defaults`)다
                #       ⒞ 값이 **사전 리터럴**이고 키가 **문자열 상수**다
                #     `**something` 으로 넘긴 사전은 **안 센다** — 그 안에 무엇이 있는지
                #     이 도구가 모르고, 모르는 것을 쓰기로 세면 죽은 필드가 살아 보인다.
                if fname in DEFAULTS_DICT_CALLS:
                    for kw in node.keywords:
                        if kw.arg not in DEFAULTS_KWARGS:
                            continue
                        if not isinstance(kw.value, ast.Dict):
                            continue
                        for k in kw.value.keys:
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                bucket[k.value] += 1
                # M2M — `zone.cameras.set([...])` 의 `cameras`
                if fname in M2M_WRITE_CALLS and isinstance(node.func.value, ast.Attribute):
                    bucket[node.func.value.attr] += 1
            # ② 속성 대입의 좌변
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = getattr(node, "targets", None) or [node.target]
                for t in targets:
                    if isinstance(t, ast.Attribute):
                        bucket[t.attr] += 1
    return dict(prod), dict(test)


def ambiguous_field_names(fields: dict) -> set:
    """**같은 이름이 둘 이상의 모델에 있는** 필드 이름들.

    ★★ [실측 2026-09-21 · 턴 AB] 이 게이트의 쓰기 셈은 **이름 단위**다 —
      `data_source` 에 쓰면 그 이름을 가진 **모든 모델의 필드**가 살아 보인다.
      평소에는 안전한 쪽으로 틀리는 성질(놓치는 쪽)이라 그대로 두었는데,
      `defaults=` 갈래를 더하자 한 자리에서 **틀린 처방**이 나왔다:

          common.BillingMark.data_source        ← 진짜 쓴다 (billing_marks.py:248)
          stream_monitors.StreamMonitor.data_source ← **운영 쓰기 0곳** (D-514 로 등재)

      두 필드가 **이름이 같다.** 그래서 ④를 더하자 둘 다 「살아 있다」가 되었고,
      게이트가 등재된 쪽에 **「등재를 지워라」**를 시켰다. 지우면 진짜 미배선이
      목록에서 사라진다 — **거짓 빨강이 거짓 삭제를 낳는 자리**다.

    ★ 그래서 **이 게이트는 모델을 못 가른다는 사실을 스스로 말한다.**
      이름이 겹치는 필드에 대해서는 **「등재를 지워라」를 말하지 않는다** —
      말할 근거가 없기 때문이다. 면제가 아니라 **모른다는 말**이고,
      판정문이 그 사실을 소리 내어 적는다.
    ⚠ 「살아 있다」쪽은 그대로 둔다(놓치는 쪽으로 틀린다 · 이 게이트는 래칫이다).
      바꾸는 것은 **처방 한 줄**뿐이다.
    """
    seen: dict = {}
    for label in fields:
        name = label.rsplit(".", 1)[-1]
        seen[name] = seen.get(name, 0) + 1
    return {n for n, c in seen.items() if c > 1}


def audit() -> tuple[dict[str, str], list[str], dict[str, tuple[int, int]]]:
    """(모수, 죽은 필드 목록, 이름별 (운영 쓰기, 시험 쓰기))."""
    fields = declared_fields()
    prod, test = write_sites()
    counts: dict[str, tuple[int, int]] = {}
    dead: list[str] = []
    for label in fields:
        name = label.rsplit(".", 1)[-1]
        # ★ FK 는 `recipient_id=` 로도 쓴다 — Django 규약이다. 이름만 보면
        #   `DeliveryRecord.recipient` 가 죽은 것으로 잡힌다(실측에서 그랬다).
        #   `<이름>_id` 를 같은 필드의 쓰기로 함께 센다.
        keys = (name, f"{name}_id")
        counts[label] = (sum(prod.get(k, 0) for k in keys),
                         sum(test.get(k, 0) for k in keys))
        if counts[label][0] == 0:
            dead.append(label)
    return fields, sorted(dead), counts


def whitelist_problems() -> list[str]:
    """화이트리스트 자신이 규약을 지키는가 — 사유에 결정 번호가 있는가."""
    out = []
    for name, why in DECLARED_UNWIRED.items():
        why = (why or "").strip()
        if not why:
            out.append(f"{name}: 화이트리스트에 사유가 없다 — 등재는 면제가 아니라 선언이다")
        elif not any(tok in why for tok in ("D-", "DA-")):
            out.append(f"{name}: 사유에 결정 번호가 없다 — 어느 판정이 이 미배선을 "
                       f"허락했는지 적는다 (D-304)")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-289)
# ═══════════════════════════════════════════════════════════════════════════
_MODEL_SRC = '''
from django.db import models
class Thing(models.Model):
    written = models.CharField(max_length=10)
    only_read = models.CharField(max_length=10)
    carried = models.CharField(max_length=10)
    tagged = models.ManyToManyField("Other")
    by_defaults = models.CharField(max_length=10)
    in_plain_dict = models.CharField(max_length=10)
    in_kwargs_dict = models.CharField(max_length=10)
    id = models.BigAutoField(primary_key=True)
'''
_USER_SRC = '''
def go(t):
    Thing.objects.create(written="x")
    print(t.only_read)
    Thing.objects.filter(only_read="x")
    ThingView(carried=t.carried)          # 값 객체 — 실어 나르는 것이지 쓰는 것이 아니다
    t.tagged.set([1, 2])                  # M2M 쓰기

    # ★ [턴 AB] `*_or_create` 는 **defaults 사전으로 쓴다** — 그 키가 필드다
    Thing._base_manager.update_or_create(
        object_id="1", defaults={"by_defaults": "v"})

    # ★ 음성 ⒜ — 그냥 사전이다. `*_or_create` 의 `defaults=` 가 아니다
    payload = {"in_plain_dict": "v"}
    ThingView(**payload)
    some.helper(config={"in_plain_dict": "v"})
    # ★ 음성 ⒞ — `create` 는 ORM 쓰기지만 **`*_or_create` 가 아니다.**
    #   그 `defaults=` 는 그냥 인자이고, 사전 키를 필드로 세면 안 된다
    Thing.objects.create(defaults={"in_plain_dict": "v"})

    # ★ 음성 ⒝ — `**` 로 넘긴 사전. 안에 무엇이 있는지 이 도구는 모른다
    Thing.objects.update_or_create(object_id="2", **{"in_kwargs_dict": "v"})
'''


def self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        app = Path(d) / "backend" / "probe"
        app.mkdir(parents=True)
        (app / "models.py").write_text(_MODEL_SRC, encoding="utf-8")
        (app / "views.py").write_text(_USER_SRC, encoding="utf-8")

        global BACKEND
        saved, BACKEND = BACKEND, Path(d) / "backend"
        try:
            fields, dead, counts = audit()
        finally:
            BACKEND = saved

    checks = [
        ("모수를 센다 (프레임워크 필드 id 는 빼고 7건)", set(
            k.rsplit(".", 1)[-1] for k in fields)
            == {"written", "only_read", "carried", "tagged",
                "by_defaults", "in_plain_dict", "in_kwargs_dict"}),
        ("ORM 쓰기가 있는 필드는 안 잡는다", "probe.Thing.written" not in dead),
        ("★ 읽기만 있는 필드를 잡는다", "probe.Thing.only_read" in dead),
        ("filter 는 쓰기가 아니다", counts.get("probe.Thing.only_read", (9, 9))[0] == 0),
        # ★ **출생 표본** (D-310) — 이 도구를 만들게 한 바로 그 사례.
        #   착시 ⑥ 을 잡으려고 만든 판정기가 자기가 태어난 이유(clip_path)를
        #   "살아 있다" 고 답했다. 그 갈래가 아래 한 줄이고, 여기서 초록이 나오면
        #   이 도구는 도구가 아니다.
        ("★ 값 객체 생성자는 쓰기가 아니다 (clip_path 를 놓쳤던 갈래)",
         "probe.Thing.carried" in dead),
        ("M2M .set() 은 쓰기다", "probe.Thing.tagged" not in dead),
        # ★★ [턴 AB · 출생 표본] `update_or_create(defaults={...})` 의 사전 키는 쓰기다.
        #   이 갈래가 없어 `common.BillingMark.data_source` 가 **거짓 빨강**으로 났고,
        #   그 빨강의 처방이 「**죽었다고 선언해라**」라 **거짓 선언을 낳을 뻔했다.**
        ("★★ 출생 표본 · `update_or_create(defaults={...})` 의 사전 키는 **쓰기다** "
         "(BillingMark.data_source 를 죽었다고 찍던 갈래)",
         "probe.Thing.by_defaults" not in dead),
        # ★ 음성 셋 — 넓히되 **좁게** 넓혔는가. 아무 사전이나 세면 진짜 죽은 필드가 숨는다.
        ("★ 음성 · 그냥 사전·`create(defaults=…)` 의 키는 **쓰기가 아니다** "
         "(`*_or_create` 가 아니면 그 사전으로 쓰지 않는다)",
         "probe.Thing.in_plain_dict" in dead),
        ("★ 음성 · `**{…}` 로 넘긴 사전은 **안 센다** — 안에 무엇이 있는지 모르고, "
         "모르는 것을 쓰기로 세면 죽은 필드가 살아 보인다",
         "probe.Thing.in_kwargs_dict" in dead),
        # ★★ [턴 AB] **이 게이트는 모델을 못 가른다** — 그 사실을 스스로 안다.
        #   `defaults=` 를 더하자 `BillingMark.data_source` 의 쓰기가
        #   `StreamMonitor.data_source` 까지 살려서, 게이트가 등재된 쪽에
        #   **「등재를 지워라」**를 시켰다. 지우면 진짜 미배선이 사라진다.
        ("★★ 이름이 **둘 이상의 모델**에 있으면 겹침으로 센다",
         ambiguous_field_names({
             "a.A.data_source": "x", "b.B.data_source": "x", "a.A.only_here": "x",
         }) == {"data_source"}),
        ("★ 음성 · 한 모델에만 있는 이름은 겹침이 아니다 "
         "(겹침을 넓게 보면 「등재를 지워라」가 영영 안 나온다)",
         ambiguous_field_names({"a.A.only_here": "x", "b.B.other": "x"}) == set()),
        ("★ 음성 · 같은 모델의 같은 이름은 하나다(라벨이 같으므로)",
         ambiguous_field_names({"a.A.f": "x"}) == set()),
        ("화이트리스트가 사유·번호를 요구한다", whitelist_problems() == []),
    ]
    bad = 0
    for label, ok in checks:
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    if bad:
        print(f"[DEADFIELD] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[DEADFIELD] 자기시험 {len(checks)}건 통과 (양성 4 · 음성 9 — ★ `defaults=` 넓힘은 **음성 둘과 함께** 섰다)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--freeze", action="store_true",
                    help="오늘의 빚을 기준선으로 잠근다 (줄일 때도 쓴다)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:                   # 판정 전에 판정기부터 (D-277)
        return 1

    fields, dead, counts = audit()

    # ★ D-301 — 검사 건수를 낸다. 0건은 통과가 아니라 **열거기 고장**이다.
    print(f"[DEADFIELD] 검사 {len(fields)}건 (모수=backend/**/models.py 의 모델 필드 전수, "
          f"프레임워크 필드 {len(FRAMEWORK_FIELDS)}종 제외 · "
          f"술어=ORM 쓰기 호출의 키워드 인자·속성 대입·M2M set/add·update_fields·`*_or_create` 의 `defaults=` 사전 키)")
    if not fields:
        print("[DEADFIELD] 필드를 한 건도 못 찾았다 — 열거기가 눈이 멀었다. "
              "0건을 통과로 읽지 않는다 (D-301)")
        return 1

    baseline = load_baseline()
    declared = [d for d in dead if d in DECLARED_UNWIRED]
    debt = [d for d in dead if d in baseline and d not in DECLARED_UNWIRED]
    fresh = [d for d in dead if d not in baseline and d not in DECLARED_UNWIRED]
    #: ★ 이름이 겹치는 필드는 **어느 모델에 쓴 것인지 이 게이트가 못 가른다.**
    #:   그런 자리에는 「등재를 지워라」를 말하지 않는다 (위 `ambiguous_field_names`).
    ambiguous = ambiguous_field_names(fields)
    stale = [k for k in DECLARED_UNWIRED
             if k not in dead and k.rsplit(".", 1)[-1] not in ambiguous]
    stale_ambiguous = [k for k in DECLARED_UNWIRED
                       if k not in dead and k.rsplit(".", 1)[-1] in ambiguous]
    healed = sorted(baseline - set(dead))
    forbidden = [d for d in dead if d.split(".")[0] in FORBIDDEN_APPS]

    print(f"[DEADFIELD] 쓰기 0곳 {len(dead)}건 — 기준선 빚 {len(debt)} · 선언 등재 "
          f"{len(declared)} · **새 빚 {len(fresh)}** · 배선되어 빠진 것 {len(healed)}")
    # ★ D-311 — §0.4 금지구역은 **잔여 계산의 분모에서 뺀다.** 우리 관할이 아닌 것을
    #   분모에 넣으면 갚을 수 없는 빚이 영원히 진척률을 눌러 앉힌다(D-207).
    ours = [d for d in dead if d.split(".")[0] not in FORBIDDEN_APPS]
    print(f"[DEADFIELD] 그중 §0.4 금지구역 {len(forbidden)}건 "
          f"(delivery·orders·terminals — 우리가 못 고친다. **잔여 분모에서 제외**) · "
          f"**우리 관할 잔여 {len(ours)}건**")

    if args.census:
        for label in sorted(fields):
            p, t = counts[label]
            mark = "DEAD" if p == 0 else "    "
            note = " (시험만 씀)" if p == 0 and t else ""
            print(f"  {mark} {label:64} 운영 {p:3} · 시험 {t:3}{note}")
    elif args.list:
        for label in dead:
            p, t = counts[label]
            tag = "등재" if label in DECLARED_UNWIRED else "미등재"
            print(f"  [{tag}] {label:60} 시험 쓰기 {t}")

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        body = _BASELINE_HEADER + "\n" + "\n".join(
            d for d in dead if d not in DECLARED_UNWIRED) + "\n"
        BASELINE.write_text(body, encoding="utf-8")
        print(f"[DEADFIELD] 기준선 {len(dead) - len(declared)}건 기록 — "
              f"{BASELINE.relative_to(ROOT)}")
        return 0

    if not baseline:
        print("[DEADFIELD] 기준선 파일이 없다 — `--freeze` 로 오늘의 빚을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return 1

    problems = whitelist_problems()
    for label in fresh:
        t = counts[label][1]
        problems.append(
            f"{label}: **새로 생긴 쓰기 0곳 필드**다 — 필드를 먼저 만들고 배선을 나중에 "
            f"하는 것이 착시 ⑥ 다(D-304). 배선하거나, DECLARED_UNWIRED 에 사유와 결정 "
            f"번호를 달아 등재한다"
            + (f" (시험은 {t}곳에서 쓴다 — 시험만 쓰는 필드는 운영에서 죽은 것이다)"
               if t else ""))
    for label in stale:
        problems.append(
            f"{label}: DECLARED_UNWIRED 에 있는데 이제 쓰인다 — 등재를 지운다. "
            f"낡은 선언이 남으면 다음에 죽는 필드를 그 이름이 가린다")
    #: ★★ **못 가르는 것을 「지워라」로 말하지 않는다.** 소리 내어 적고 넘어간다 —
    #:   안 적으면 다음 사람이 「이 게이트가 모델까지 본다」고 읽는다.
    for label in stale_ambiguous:
        name = label.rsplit(".", 1)[-1]
        others = sorted(k for k in fields
                        if k.rsplit(".", 1)[-1] == name and k != label)
        print(f"[DEADFIELD] ? {label}: 이름 «{name}» 이 **다른 모델에도 있다** "
              f"({' · '.join(others)}) — 이 게이트의 쓰기 셈은 **이름 단위**라 "
              f"어느 모델에 쓴 것인지 **못 가른다.** 그래서 「등재를 지워라」를 "
              f"말하지 않는다. 면제가 아니라 **모른다는 말**이다")
    if healed:
        # ★ D-311 — **줄어드는 것이 보여야 갚는 맛이 난다.** 실패가 아니고 로그다.
        #   빚 목록이 조용히 늘지 않는 것만으로는 부족하다 — 줄어든 줄의 이름을 남긴다.
        print(f"[DEADFIELD] ★ 기준선에서 빠진 {len(healed)}건 — **배선됐다.**")
        for name in healed:
            print(f"[DEADFIELD]   갚음: {name}")
        print("[DEADFIELD] `--freeze` 로 기준선을 줄인다")

    if problems:
        print("[DEADFIELD] 위반 — 쓰기가 없는 필드는 '구현된 것처럼 보이는 미구현' 이다 (D-304)")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[DEADFIELD] 통과 — 새 빚 0건. 기준선 밖에서 태어난 죽은 필드가 없다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    _n_df = sum(1 for _ in (ROOT / "backend").rglob("*.py"))
    #: ★ [P-204 · 턴 Z · Q] **마지막 줄은 분모다.** 이 수는 **지금 센 것**이다 —
    #:   손으로 적은 수는 분모가 아니고, 분모를 안 말한 `exit 0` 은
    #:   「이 게이트가 통과」가 아니라 「이 호출이 끝났다」일 뿐이다.
    gate_header(__file__, measured=(
        "모델 필드마다 **쓰는 자리가 있는지** AST 로 훑는다(착시 ⑥) — "
        "**분모 %d**(backend/ 의 .py 전수 · 지금 셌다). 필드 수와 빚은 실행 중에 세어 "
        "아래 [DEADFIELD] 줄에 적는다 — **§0.4 금지구역은 잔여 분모에서 뺀다**" % _n_df))
    sys.exit(main())
