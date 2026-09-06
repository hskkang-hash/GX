# -*- coding: utf-8 -*-
"""LAW-02a — **영상 보존 일수를 선언하고, 그 수대로 지운다** (차선 L · 2026-09-05).

대장이 못박은 두 조건, 그리고 둘째가 진짜다
--------------------------------------------
    ① 보존 일수를 선언하는 설정 자리가 생긴다
    ② **삭제가 그 수를 실제로 본다** — 「적었다」가 아니라 「그대로 지운다」까지.
    ⚠ 선언만 하고 삭제가 그 수를 안 보면 **안내판은 여전히 거짓말**이고,
      그때는 그 거짓말이 **법적 효력을 가진 문서**로 걸려 있다.

그래서 이 파일에는 수(數)와 **지우는 손**이 함께 있다. 하나만 있으면 안 된다.

왜 이제 **기본값이 없는가** — P-67 (2026-09-06 · 세종 판정 · 차선 E 집행)
-------------------------------------------------------------------------
이 자리에는 「왜 30인가」가 적혀 있었다. 수의 출처는 세종의 서식이었고
(GX-LAW-02 고지 **초안**의 안내판 칸 「기본 30일」) 그것은 사실이었다.
**틀린 것은 수가 아니라 자리다.**

    서식의 30 = 「안내판을 이렇게 인쇄한다」는 **초안의 예시**
    코드의 30 = 「남의 영상을 30일에 지운다」는 **집행 명령**

앞엣것을 뒤엣것으로 옮겨 적는 순간, 아무도 정하지 않은 수가 되돌릴 수 없는 일을
하게 된다. 그래서 P-67 이 셋을 갈랐다:

    ㉠ **코드 기본값 없음.** 미선언이면 `retention_days()` 가 `None` 을 내고
      파기·백업이 **돌지 않는다**(그리고 그 사실이 감사에 남는다).
    ㉡ **개발·스테이징은 선언**한다 — `backend/config/retention_seed.py`
      (감사 로그 365 · 스냅샷·구간 참조 30 · 백업 매일 03:00 · 목적지 `/backup` ·
       백업 보존 14 · 복구 시험 주 1회). 선언에는 임자와 환경이 있다.
    ㉢ **운영 값은 고객이 U5 설정 화면에서 선언**한다. 코드가 정하지 않는다.

법조문 대조는 여전히 법률대리인의 몫이고, RETENTION_LEGAL_REVIEW 가 그 사실을
응답에 싣는다 — 선언된 수가 **법적으로 맞는 수인지**는 여기서 답하지 않는다.

    ★ 운영자가 값을 정하면 **그 값이 이긴다** (VIDEO_RETENTION_DAYS 등).
      감사 로그 정리(ops-audit-purge-daily)가 「고객이 정한 일수 그대로」 지우는 것과
      같은 모양이다 — 보존기간은 우리가 남의 디스크에 대해 정하는 값이 아니다.

★ **삭제는 위험하다** — 이 파일이 지키는 셋
-------------------------------------------
    ㉠ dry_run=True 가 **기본값**이다. 부르는 쪽이 침묵하면 아무것도 안 지운다.
    ㉡ 지운 것은 **감사에 남는다**(common/audit_writer · LAW-08 체인 위에).
    ㉢ 되돌릴 수 없다는 사실을 **누르기 전에** 말한다 — 화면이 그렇게 그리고,
      서버도 같은 뜻을 irreversible 로 낸다.

★ 실측으로 알게 된 것 둘 — **덮지 않고 적는다**
-----------------------------------------------
① **이 저장소의 delete() 는 대개 지우지 않는다.** dj-core BaseModel 은
   SafeDeleteModel(SOFT_DELETE_CASCADE) 이다 [실측 core/base.py:110] —
   EventClip.delete() 는 행에 「지움」 표시를 할 뿐 행을 남긴다. 보존기간을
   약속해 놓고 표시만 하면 그것은 **지운 척**이다. 그래서 HARD_DELETE 를 명시한다.
② **보존기간은 지금 테넌트별이 아니다.** 녹화 표(StreamMonitorRecord)에는 소속
   칸이 없다 [실측 stream_monitors/models.py:163]. 그래서 이 집행은 **전역**이고,
   라우트는 전역 관리자만 실행할 수 있게 막는다. 테넌트마다 다른 보존기간은
   그 칸이 생기기 전에는 **약속할 수 없다** — 약속하지 않는다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from common import audit_writer

from apps.dsm.legal_notice import RETENTION_SETTING_NAMES

log = logging.getLogger("guardianx.law02a.retention")

#: 감사 행의 logger_name. **이 문자열로 보존기간 집행 전건을 뽑는다.**
LOGGER_NAME = "guardianx.law02a.retention"
TAG = "[LAW-02a]"

#: ★ **여기에 기본값이 있었다** — `DEFAULT_RETENTION_DAYS: int = 30` (P-67 로 지웠다).
#:
#:   세종 판정 P-67 (2026-09-06): 「보존 일수·백업 목적지·일정에 **코드 기본값 없음.**
#:   미선언 테넌트 = 파기·백업 **돌지 않음**.」
#:
#:   지운 사유는 「30이 틀린 수라서」가 아니다. **아무도 정하지 않았는데 수가 나오는
#:   자리**였기 때문이다. 서식에 30이 적혀 있어도 그것은 GX-LAW-02 **초안**의 수이고,
#:   이 코드가 그 수를 남의 자료에 대한 파기 명령으로 바꾸고 있었다.
#:   개발·스테이징의 수는 이제 `config/retention_seed.py` 가 **선언**한다 —
#:   선언에는 임자와 환경이 있고, 기본값에는 없다. 운영 값은 고객이 U5 에서 정한다.
#:
#:   ⚠ 다시 넣지 마라. 넣는 순간 「보존 30일」이 다시 아무도 정하지 않은 수가 되고,
#:     `scripts/verify_retention_declared.py` 의 정적 검사가 빨개진다.

#: 운영자가 값을 정하는 자리. legal_notice 와 **같은 목록을 쓴다** —
#: 두 벌로 적으면 안내판이 보는 수와 삭제가 보는 수가 갈리고, 그것이 최악이다.
SETTING_NAMES: tuple[str, ...] = RETENTION_SETTING_NAMES

#: ★ 법률 검토 대기. **선언된 수가 이 용도에 법적으로 맞는지**는 여기서 답하지 않는다.
#:   P-67 뒤로 이 문장이 가리키는 것은 「제품 기본값」이 아니라 **선언된 값**이다 —
#:   개발·스테이징은 세종 선언, 운영은 고객(U5)의 선언이고, 둘 다 조문 대조 전이다.
RETENTION_LEGAL_REVIEW: str = (
    "보존 일수의 법정 기준 대조는 법률대리인의 판정이다. 이 수는 제품 기본값이 "
    "아니라 **선언된 값**이며(P-67 · 코드 기본값 없음), 조문 대조 전이다."
)

#: 주기 집행 태스크의 이름. **beat 표에 이 이름이 있는지로 「도는가」를 잰다** —
#: 선언과 실행은 다른 사실이고(D-284), 안내판은 실행 쪽을 약속한다.
BEAT_TASK_NAME = "common.video_retention_sweep_beat"

#: 한 번의 집행이 지울 수 있는 상한. 상한이 없으면 첫 집행이 몇 만 행을 한 트랜잭션에
#: 물고 늘어진다 — 그리고 그 순간은 되돌릴 수 없다. 남은 것은 다음 회차가 지운다.
SWEEP_CAP: int = 2000

#: 감사에 적어 두는 식별자의 상한. 전부 적으면 감사 한 줄이 목록이 된다.
AUDIT_ID_SAMPLE = 200


# ═══════════════════════════════════════════════════════════════════════════
# 1. 수 — **선언된 자리와 그 출처를 함께 낸다**
# ═══════════════════════════════════════════════════════════════════════════
def retention_days() -> int | None:
    """영상 보존 일수. **선언이 없으면 수가 나오지 않는다** (`None`).

    ★ 2026-09-06 · P-67 — 이 함수는 예전에 **언제나 수를 냈다**(없으면 30).
      그 갈래가 「아무도 정하지 않았는데 수가 나오는」 자리였고, 그 수를
      `sweep()` 이 파기 명령으로 읽었다. 지금은 셋 다 같은 답을 낸다:
          미선언 → `None` → 안내판은 「미선언」 · 파기는 **안 돈다**.

    ★ `None` 은 **0일이 아니다.** 0일은 「즉시 지운다」이고 `None` 은
      「지우지 않는다」다 — 되돌릴 수 없는 쪽으로 틀리지 않는 것이 기본이다.

    0 이하·정수가 아닌 값도 `None` 이다. 예전에는 그것이 **기본값으로 되돌아갔는데**,
    되돌아갈 기본값이 없으므로 이제는 **미선언과 같게 다룬다** — 설정 오타 하나가
    파기 명령이 되지 않게 하는 것이 그때나 지금이나 이 갈래의 목적이다.
    """
    for name in SETTING_NAMES:
        value = getattr(settings, name, None)
        if value is None:
            continue
        try:
            days = int(value)
        except (TypeError, ValueError):
            log.warning("[LAW-02a] %s=%r 를 일수로 읽지 못했다 — **미선언으로 본다**. "
                        "지어낸 수로 지우지 않는다", name, value)
            return None
        if days <= 0:
            log.warning("[LAW-02a] %s=%r 는 0 이하다 — 「즉시 파기」라는 뜻이 되므로 "
                        "**선언으로 세지 않는다**", name, days)
            return None
        return days
    return None


def retention_source() -> str:
    """그 수가 **어디서 왔는가.** 값만 보이면 다음 사람이 출처를 못 되짚는다.

    ★ P-67 뒤로 「제품 기본값」이라는 출처는 **없다.** 선언이 없으면 출처도 없고,
      그 사실을 「미선언」이라는 낱말 하나로 말한다 — 화면(U5)의 빨강 배지가
      이 문자열을 그대로 읽는다.
    """
    for name in SETTING_NAMES:
        if getattr(settings, name, None) is not None:
            declared = getattr(settings, "RETENTION_DECLARATION_SOURCE", "")
            return f"운영 설정 {name}" + (f" · {declared}" if declared else "")
    return "미선언"


def sweep_is_scheduled() -> bool:
    """집행이 **저절로 도는가.** 「함수가 있다」와 「매일 돈다」는 다른 사실이다.

    beat 표를 읽어 답한다 — 못 읽으면 거짓이다. 못 읽은 것을 「돈다」로 적으면
    그 순간 안내판의 「자동으로 지워집니다」가 근거 없는 문장이 된다.
    """
    try:
        from config.celery import app as celery_app

        return BEAT_TASK_NAME in {
            entry.get("task")
            for entry in (celery_app.conf.beat_schedule or {}).values()
        }
    except Exception as exc:                                   # noqa: BLE001
        log.warning("[LAW-02a] beat 표를 읽지 못했다: %s", exc)
        return False


def policy() -> dict[str, Any]:
    """제품이 선언하는 보존 정책 한 벌. **화면과 안내판이 같은 것을 읽는다.**"""
    days = retention_days()
    declared = days is not None
    return {
        "retention_days": days,
        "declared": declared,
        "source": retention_source(),
        "cutoff": ((timezone.now() - timedelta(days=days)).isoformat()
                   if declared else None),
        #: ★ 「지워진다」를 약속하는 자리. 주기가 안 걸려 있으면 **거짓이다.**
        #:   그리고 **선언이 없으면 그것도 거짓이다** (P-67) — 주기는 도는데
        #:   지울 수를 아무도 안 정했으면 아무것도 안 지워진다. 두 조건이 다 참일
        #:   때만 안내판이 「자동으로 지워집니다」를 인쇄할 수 있다.
        "enforced": declared and sweep_is_scheduled(),
        "beat_task": BEAT_TASK_NAME,
        "irreversible": True,
        "targets": [t.label for t in TARGETS],
        "legal_review": RETENTION_LEGAL_REVIEW,
        "source_doc": "docs/design/GX-LAW-02_영상정보처리기기_고지_초안_v0.1.md",
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. 무엇을 지우는가 — **표로 적고, 표대로만 지운다**
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Target:
    """지우는 자리 하나.

    Attributes:
        label: 사람이 읽는 이름.
        model: 앱.모델.
        stamp_field: 「언제 것인가」를 재는 칸. 이 칸으로 기간을 판정한다.
        object_field: 객체저장소 경로가 든 칸. 비어 있으면 바이트가 없는 표다.
        row_action: hard_delete(행을 지운다) / blank_object(행은 남기고 칸을 비운다).
        why: 왜 이 자리가 「영상」인가. 적어 두지 않으면 다음 사람이 범위를 넓힌다.
    """

    label: str
    model: str
    stamp_field: str
    object_field: str
    row_action: str
    why: str


#: ★ 이 표가 곧 범위다. 여기 없는 표는 **지우지 않는다.**
#:   특히 DetectionEvent 행 자체는 지우지 않는다 — 그 행은 오탐률의 분모이고
#:   감사의 근거다. 지우면 「사건이 없었다」와 「기록을 지웠다」가 같은 상태가 된다.
#:   지우는 것은 그 행이 가리키는 **이미지 바이트**와 그 경로 한 칸이다.
TARGETS: tuple[Target, ...] = (
    Target(label="녹화 영상", model="stream_monitors.StreamMonitorRecord",
           stamp_field="created_at", object_field="object_path",
           row_action="hard_delete",
           why="객체저장소의 녹화 원본을 가리키는 유일한 표다"),
    Target(label="영상 구간 참조", model="stream_monitors.EventClip",
           stamp_field="created_on", object_field="",
           row_action="hard_delete",
           why="녹화가 지워지면 그 구간을 가리키던 참조는 갈 곳이 없다"),
    Target(label="이벤트 스냅샷", model="stream_monitors.DetectionEvent",
           stamp_field="occurred_at", object_field="snapshot_path",
           row_action="blank_object",
           why="정지 이미지 1장도 영상정보다. 행은 남기고 이미지만 지운다"),
)


def _model(label: str):
    app_label, _, name = label.partition(".")
    return apps.get_model(app_label, name)


def _remove_object(path: str) -> str:
    """객체저장소에서 바이트 하나를 지운다. **못 지우면 사유를 돌려준다**(빈 문자열이 성공).

    ⚠ 여기서 실패하면 부르는 쪽은 **행을 지우지 않는다.** 행을 먼저 지우면 그 바이트는
      가리키는 것이 아무것도 없는 채로 저장소에 영원히 남는다 — 보존기간을 지킨다면서
      정작 영상만 남기는 결과다.
    """
    path = (path or "").strip()
    if not path:
        return "경로가 비어 있다"
    try:
        from stream_monitors.utils.minio_client import minio_client
    except Exception as exc:                                   # noqa: BLE001
        return f"저장소 연결을 가져오지 못했다: {type(exc).__name__}: {exc}"[:200]

    bucket, _, name = path.partition("/")
    if not name:
        bucket, name = getattr(minio_client, "bucket_name", ""), path
    try:
        minio_client.client.remove_object(bucket, name)
    except Exception as exc:                                   # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"[:200]
    return ""


def _hard_delete(model, pks: list) -> None:
    """**진짜로 지운다.** 소프트 삭제 정책을 명시적으로 넘어선다 (머리말 실측 ①)."""
    qs = model._base_manager.filter(pk__in=pks)
    try:
        from safedelete.config import HARD_DELETE

        qs.delete(force_policy=HARD_DELETE)
    except (TypeError, ImportError):
        #: 소프트 삭제 모델이 아니다 — 평범한 delete() 가 곧 진짜 삭제다.
        qs.delete()


def _sweep_target(target: Target, *, cutoff, dry_run: bool,
                  tenant_filter: dict | None = None) -> dict:
    """자리 하나를 훑는다. **지난 것만 세고, 지난 것만 지운다.**

    Args:
        tenant_filter: 테넌트로 좁히는 조건. `None` 이면 **전역**이다 —
            `sweep()` 이 그렇게 부르고, `purge()` 는 반드시 조건을 준다.
            좁힐 수 없는 표를 좁히지 않은 채로 지우면 그것은 남의 테넌트 파기다.
    """
    try:
        model = _model(target.model)
    except Exception as exc:                                   # noqa: BLE001
        #: 표가 없는 것은 **판정 불가**이지 「0건 정리」가 아니다 (D-301).
        return {"label": target.label, "model": target.model, "verdict": "UNKNOWN",
                "why": f"{target.model} 을 찾지 못했다: {type(exc).__name__}"[:200],
                "tenant_scoped": tenant_filter is not None,
                "expired": 0, "deleted": 0, "kept": 0,
                "objects_deleted": 0, "object_failures": [], "deleted_ids": []}

    manager = model._base_manager
    base_qs = manager.all()
    if tenant_filter is not None:
        base_qs = base_qs.filter(**tenant_filter)
    total = base_qs.count()
    expired_qs = base_qs.filter(**{f"{target.stamp_field}__lt": cutoff}).order_by("pk")
    if target.row_action == "blank_object" and target.object_field:
        #: 이미 비워진 것은 지울 것이 없다 — 「지웠다」에 두 번 세지 않는다.
        expired_qs = expired_qs.exclude(**{target.object_field: ""})
    expired = expired_qs.count()
    rows = list(expired_qs[:SWEEP_CAP])

    result = {
        "label": target.label, "model": target.model, "verdict": "OK",
        "tenant_scoped": tenant_filter is not None,
        "why": target.why, "stamp_field": target.stamp_field,
        "rows_total": total, "expired": expired,
        "kept": total - expired,
        "capped": expired > SWEEP_CAP,
        "deleted": 0, "objects_deleted": 0, "object_failures": [],
        "deleted_ids": [],
    }
    if dry_run or not rows:
        return result

    deletable = []
    for row in rows:
        if target.object_field:
            reason = _remove_object(getattr(row, target.object_field, "") or "")
            if reason and reason != "경로가 비어 있다":
                #: 바이트를 못 지웠다 — **행을 남긴다**(위 _remove_object 머리말).
                result["object_failures"].append({"pk": row.pk, "why": reason})
                continue
            if not reason:
                result["objects_deleted"] += 1
        deletable.append(row.pk)

    if deletable:
        if target.row_action == "hard_delete":
            _hard_delete(model, deletable)
        else:
            manager.filter(pk__in=deletable).update(**{target.object_field: ""})
        result["deleted"] = len(deletable)
        result["deleted_ids"] = deletable[:AUDIT_ID_SAMPLE]
    return result


def sweep(*, days=None, dry_run: bool = True, actor=None, reason: str = "") -> dict:
    """보존기간을 **집행한다.** 기본값은 아무것도 지우지 않는 dry_run 이다.

    Args:
        days: 일수를 직접 준다. 주지 않으면 선언된 값(retention_days()).
        dry_run: 참이면 **세기만 한다.** 기본값이 참인 것이 이 함수의 안전장치다.
        actor: 사람이 눌렀으면 그 사람. 주기 실행이면 None.
        reason: 왜 지금 지우는가. 주기 실행이면 그 사실을 적는다.

    Returns:
        판정 한 벌. dry_run 이면 deleted 는 **전부 0** 이다 — 그것을 시험이 잰다.
    """
    started = timezone.now().isoformat(timespec="seconds")
    days = int(days) if days is not None else retention_days()
    if days is None:
        #: ★ P-67 — **선언이 먼저다.** 예전에는 여기서 제품 기본값 30이 나왔고,
        #:   이 함수는 **전역**이므로 그 30이 전 테넌트의 영상을 지웠다.
        #:   미선언은 「0건 지웠다」가 아니라 **「돌지 않았다」**이고, 그 둘을
        #:   가르는 것이 감사에 남는 이 한 줄이다 (D-290).
        payload = {
            "measured_at": started, "verdict": SKIPPED_UNDECLARED,
            "retention_days": None, "source": retention_source(),
            "cutoff": None, "dry_run": bool(dry_run), "targets": [],
            "expired_total": 0, "deleted_total": 0,
            "objects_deleted_total": 0, "object_failure_total": 0,
            "unknown_targets": [], "irreversible": True,
            "why": ("영상 보존 일수가 선언되지 않았다 — 지우지 않는다. "
                    "코드 기본값은 없다(P-67). 선언 자리: U5 설정 화면 · "
                    "개발·스테이징은 config/retention_seed.py"),
        }
        entry = audit_writer.write(
            logger_name=LOGGER_NAME, tag=TAG, actor=actor,
            action=SWEEP_SKIPPED_ACTION, outcome=audit_writer.ALLOWED,
            reason=(reason or payload["why"])[:400],
            before={"retention_days": None},
            after={k: v for k, v in payload.items() if k != "measured_at"})
        payload["audit_id"] = entry.audit_id
        payload["row_hash"] = entry.row_hash
        log.info("[LAW-02a] 전역 집행 건너뜀 — 보존 일수 미선언 (감사 %s)",
                 entry.audit_id)
        return payload
    cutoff = timezone.now() - timedelta(days=days)

    targets = [_sweep_target(t, cutoff=cutoff, dry_run=dry_run) for t in TARGETS]
    payload = {
        "measured_at": started,
        "retention_days": days,
        "source": retention_source(),
        "cutoff": cutoff.isoformat(),
        "dry_run": bool(dry_run),
        "targets": targets,
        "expired_total": sum(t["expired"] for t in targets),
        "deleted_total": sum(t["deleted"] for t in targets),
        "objects_deleted_total": sum(t["objects_deleted"] for t in targets),
        "object_failure_total": sum(len(t["object_failures"]) for t in targets),
        "unknown_targets": [t["label"] for t in targets if t["verdict"] == "UNKNOWN"],
        "irreversible": True,
    }

    #: ㉡ **지운 것은 감사에 남는다.** 미리보기(dry-run)도 남긴다 — 「누가 무엇을
    #:   지우려고 들여다봤는가」도 사후에 답해야 하는 질문이다.
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=("law02a:retention_sweep_preview" if dry_run
                else "law02a:retention_sweep"),
        outcome=audit_writer.ALLOWED,
        reason=(reason or ("보존기간 미리보기" if dry_run else "보존기간 집행"))[:400],
        before={"retention_days": days, "cutoff": cutoff.isoformat()},
        after={k: v for k, v in payload.items() if k != "measured_at"},
    )
    payload["audit_id"] = entry.audit_id
    payload["row_hash"] = entry.row_hash
    log.info("[LAW-02a] %s일 기준 %s — 만료 %d건 · 삭제 %d건 (감사 %s)",
             days, "미리보기" if dry_run else "집행",
             payload["expired_total"], payload["deleted_total"], entry.audit_id)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 3. 파기 — **「지운다」는 「그대로 지운다」다** (P-57 · 2026-09-05 · 차선 E)
# ═══════════════════════════════════════════════════════════════════════════
#
# 세종 판정 P-57 원문: *"파기 = 하드 삭제 + 객체(스냅샷) 삭제 + 파기 기록(감사).
# dj-core 무수정 — 우리 층에서 purge 경로(우리 모델 행은 raw delete · MinIO remove)."*
#
# ★ [실측 2026-09-05 · 차선 E] 위 `sweep()` 은 **이미 하드 삭제였다.**
#   확인한 방법과 수는 이렇다 (gx-shell · test DB · EventClip 1행):
#       ㉠ `clip.delete()`            → `_base_manager` 1 · `all_objects` 1 ·
#                                       `deleted_objects` 1 · **`objects` 1**
#       ㉡ `retention._hard_delete()` → `_base_manager` 0 · `all_objects` 0 ·
#                                       `deleted_objects` 0
#   ㉠이 이 절의 산출이다. 그런데 발견은 하나 더 있고, 그것이 더 나쁘다:
#
#   ⚠ **소프트 삭제된 행이 평범한 조회에서도 보인다.** dj-core 가 `objects` 를
#     `CustomManagerGroup(models.Manager)` 로 덮어써서 safedelete 의 매니저가 아니다
#     [실측 core/base.py:2082 · 2393]. 그래서 `Model.objects` 는 `deleted` 를 안 본다 —
#     「지운 척」이 화면에서 **지워지지도 않는다.** 세는 코드(계량·오탐률)가 이 사실을
#     모르면 **지운 카메라를 청구서에 올린다.** `metering.py` 가 그래서 명시적으로 뺀다.
#
# 그래서 이 절이 `sweep()` 위에 더하는 것은 「하드 삭제」가 아니라 **넷**이다:
#     ① **테넌트로 좁힌다.** `sweep()` 은 전역이다 — 전역 파기는 남의 테넌트 파기다.
#     ② **선언이 먼저다.** 보존 일수를 선언하지 않은 테넌트는 대상에서 뺀다(함정 ㉡).
#        제품 기본값 30은 **안내판의 수**이지 파기 명령이 아니다. 아무도 선언하지
#        않았는데 30일에 지우기 시작하면 그것은 우리가 남의 자료를 버린 것이다.
#     ③ **좁힐 수 없는 표는 지우지 않는다.** 소속 칸도, 소속으로 가는 길도 없으면
#        그 표는 UNKNOWN 이고 한 행도 건드리지 않는다. 「모르겠으니 다 지운다」는
#        되돌릴 수 없는 쪽으로 틀리는 기본값이다.
#     ④ **파기 기록이 부름 하나에 하나 남는다.** 미리보기·건너뜀도 남는다 —
#        「지웠다」와 「원래 없었다」가 같은 상태가 되면 안 된다(D-290).
#
# ⚠ 되돌릴 수 없다 — dry_run=True 가 여기서도 기본값이다 (D-209).
#
# ⚠ 위 2절의 `sweep()` 이 이 절의 `SKIPPED_UNDECLARED` · `SWEEP_SKIPPED_ACTION` 을
#   쓴다. 파이썬은 **부를 때** 이름을 찾으므로 순서는 문제가 아니지만, 판정 낱말을
#   두 벌로 두지 않으려고 일부러 이 자리 하나에 모았다 (D-369).

#: 테넌트별 보존 일수 선언 자리. {group_id: days}. **운영자가 채운다.**
#: 여기 없는 테넌트는 파기 대상이 아니다 — 「선언이 먼저다」가 그 뜻이다.
TENANT_RETENTION_SETTING = "VIDEO_RETENTION_DAYS_BY_TENANT"

#: 파기 감사의 action. **이 값으로 파기 전건을 뽑는다** — 「지운 기록」 화면의 원천.
PURGE_ACTION = "law02a:purge"
PURGE_PREVIEW_ACTION = "law02a:purge_preview"
PURGE_SKIPPED_ACTION = "law02a:purge_skipped"

#: 전역 집행(`sweep`)이 **미선언이라 돌지 않은** 것을 적는 자리 (P-67).
#: 「0건 지웠다」와 「돌지 않았다」를 같은 줄로 적으면 구별이 사라진다.
SWEEP_SKIPPED_ACTION = "law02a:retention_sweep_skipped"

#: 파기 판정 셋. 자유 문자열을 만들지 않는다 — 넷째가 생기면 집계가 갈린다.
PURGED = "PURGED"
PREVIEWED = "PREVIEWED"
SKIPPED_UNDECLARED = "SKIPPED_UNDECLARED"


def _tenant_map() -> dict:
    """선언 표를 읽는다. **못 읽으면 빈 표다** — 지어내지 않는다."""
    raw = getattr(settings, TENANT_RETENTION_SETTING, None)
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in raw.items():
        try:
            gid, days = int(key), int(value)
        except (TypeError, ValueError):
            log.warning("[LAW-02a] %s 의 %r=%r 를 읽지 못했다 — 그 테넌트는 "
                        "**선언하지 않은 것으로 본다**", TENANT_RETENTION_SETTING,
                        key, value)
            continue
        if days <= 0:
            log.warning("[LAW-02a] 테넌트 %s 의 보존 일수가 %d 다 — 0 이하는 "
                        "「즉시 파기」라는 뜻이 된다. 선언으로 세지 않는다", gid, days)
            continue
        out[gid] = days
    return out


def _global_declared_days():
    """운영자가 **전역으로** 선언한 일수. 없으면 None.

    ★ 2026-09-06 · P-67 — 이 함수는 `retention_days()` 를 **그대로 부른다.**
      예전에는 둘이 달랐다: 저쪽은 언제나 수를 냈고(기본값 30) 이쪽만 None 을 냈다.
      기본값이 사라진 지금 **둘은 같은 질문**이고, 술어를 두 벌로 두면 반드시
      어긋난다 — 어긋난 뒤에는 안내판이 보는 수와 파기가 보는 수가 갈리고
      그것이 이 파일이 가장 두려워하는 상태다(D-369).
    """
    return retention_days()


def declared_retention_days(group_id):
    """이 테넌트가 **스스로 선언한** 보존 일수. 선언이 없으면 None.

    None 은 **0일이 아니다** — 「파기하지 않는다」이고, 그것이 안전한 쪽이다.
    """
    try:
        gid = int(group_id)
    except (TypeError, ValueError):
        return None
    per_tenant = _tenant_map().get(gid)
    return per_tenant if per_tenant is not None else _global_declared_days()


def declaration_source(group_id) -> str:
    """그 선언이 **어디서 왔는가.** 값만 보이면 다음 사람이 되짚지 못한다."""
    try:
        gid = int(group_id)
    except (TypeError, ValueError):
        return "미선언"
    if gid in _tenant_map():
        return f"테넌트 선언 {TENANT_RETENTION_SETTING}[{gid}]"
    if _global_declared_days() is not None:
        for name in SETTING_NAMES:
            if getattr(settings, name, None) is not None:
                return f"운영 설정 {name} (전역 선언)"
    return "미선언"


def declared_tenants() -> list:
    """**파기 대상 테넌트 전부.** 선언하지 않은 테넌트는 이 목록에 없다.

    ★ 이 목록이 곧 주기 집행의 범위다. 화면이 이것을 그대로 읽어서, 관리자가
      「우리 테넌트가 여기 있나」를 눈으로 확인할 수 있어야 한다 — 파기는
      **일어난 뒤에 알면 늦다.**
    """
    UserGroup = apps.get_model("user", "UserGroup")
    per_tenant, global_days = _tenant_map(), _global_declared_days()
    rows = []
    for group in UserGroup._base_manager.all().order_by("pk"):
        days = per_tenant.get(group.pk, global_days)
        if days is None:
            continue
        rows.append({
            "group_id": group.pk,
            "name": getattr(group, "name", "") or getattr(group, "code", ""),
            "retention_days": days,
            "source": declaration_source(group.pk),
        })
    return rows


class TenantColumnMissing(LookupError):
    """이 표는 **어느 테넌트 것인지 알 수 없다.** 그러면 지우지 않는다."""


def _tenant_filter(target: Target, group_id) -> dict:
    """이 표를 테넌트로 좁히는 조건. **못 좁히면 던진다.**

    ★ [실측 2026-09-05] `StreamMonitorRecord` 에는 소속 칸이 없다 —
      이 파일 머리말 실측 ②가 적은 그대로다. 그런데 **길이 없는 것은 아니었다**:
      이 표의 `stream_id` 는 `StreamMonitor` 의 pk 를 문자열로 담고, 그 카메라에는
      `group` 이 있다. 그래서 카메라를 거쳐 좁힌다. 머리말 ②의 「테넌트마다 다른
      보존기간은 약속할 수 없다」는 이 길로 풀린다.
    """
    model = _model(target.model)
    names = {f.name for f in model._meta.get_fields()}
    if "group" in names:
        return {"group_id": group_id}
    if "stream_id" in names:
        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        ids = list(Stream._base_manager.filter(group_id=group_id)
                   .values_list("pk", flat=True))
        #: 카메라가 하나도 없으면 **빈 목록**이다 — 그러면 아무것도 안 지운다.
        #: 조건을 빼고 부르면 그 순간 전역 파기가 된다. 빈 목록이 옳다.
        return {"stream_id__in": [str(i) for i in ids]}
    raise TenantColumnMissing(
        f"{target.model} 을 테넌트로 좁힐 길이 없다 — 소속 칸도, 소속으로 가는 "
        f"길도 없다. 좁히지 못하는 표는 지우지 않는다")


def purge(*, group_id, days=None, dry_run: bool = True, actor=None,
          reason: str = "") -> dict:
    """한 테넌트의 보존기간을 **파기한다.** 기본값은 아무것도 안 지우는 미리보기.

    Args:
        group_id: 테넌트(UserGroup) 식별자. **필수다** — 전역 파기는 이 문으로 못 한다.
        days: 일수를 직접 준다. 주지 않으면 **그 테넌트가 선언한 값**.
        dry_run: 참이면 세기만 한다. **기본값이 참인 것이 이 함수의 안전장치다.**
        actor: 사람이 눌렀으면 그 사람. 주기 실행이면 None.
        reason: 왜 지금 지우는가.

    Returns:
        판정 한 벌. verdict 는 셋 중 하나이고, audit_id 가 **파기 기록**이다.
    """
    started = timezone.now().isoformat(timespec="seconds")
    declared = declared_retention_days(group_id)
    days = int(days) if days is not None else declared
    source = declaration_source(group_id)

    if declared is None:
        #: ★ 함정 ㉡ — **선언이 먼저다.** 선언 없는 테넌트는 한 행도 건드리지 않는다.
        payload = {
            "measured_at": started, "group_id": group_id,
            "verdict": SKIPPED_UNDECLARED, "retention_days": None,
            "source": source, "dry_run": bool(dry_run), "targets": [],
            "expired_total": 0, "deleted_total": 0,
            "objects_deleted_total": 0, "object_failure_total": 0,
            "unknown_targets": [], "irreversible": True,
            "why": ("이 테넌트는 보존 일수를 선언하지 않았다 — 파기 대상이 아니다. "
                    "제품 기본값 30일은 안내판의 수이지 파기 명령이 아니다"),
        }
        entry = audit_writer.write(
            logger_name=LOGGER_NAME, tag=TAG, actor=actor,
            action=PURGE_SKIPPED_ACTION, outcome=audit_writer.ALLOWED,
            reason=(reason or payload["why"])[:400],
            before={"group_id": group_id},
            after={k: v for k, v in payload.items() if k != "measured_at"})
        payload["audit_id"] = entry.audit_id
        payload["row_hash"] = entry.row_hash
        log.info("[LAW-02a] 테넌트 %s 건너뜀 — 보존 일수 미선언 (감사 %s)",
                 group_id, entry.audit_id)
        return payload

    cutoff = timezone.now() - timedelta(days=days)
    targets = []
    for target in TARGETS:
        try:
            narrow = _tenant_filter(target, group_id)
        except TenantColumnMissing as exc:
            #: 좁히지 못한 표는 **판정 불가**이고 「0건 파기」가 아니다 (D-301).
            targets.append({"label": target.label, "model": target.model,
                            "verdict": "UNKNOWN", "why": str(exc)[:300],
                            "tenant_scoped": False, "expired": 0, "deleted": 0,
                            "kept": 0, "objects_deleted": 0,
                            "object_failures": [], "deleted_ids": []})
            continue
        targets.append(_sweep_target(target, cutoff=cutoff, dry_run=dry_run,
                                     tenant_filter=narrow))

    payload = {
        "measured_at": started,
        "group_id": group_id,
        "verdict": PREVIEWED if dry_run else PURGED,
        "retention_days": days,
        "declared_days": declared,
        "source": source,
        "cutoff": cutoff.isoformat(),
        "dry_run": bool(dry_run),
        "targets": targets,
        "expired_total": sum(t["expired"] for t in targets),
        "deleted_total": sum(t["deleted"] for t in targets),
        "objects_deleted_total": sum(t["objects_deleted"] for t in targets),
        "object_failure_total": sum(len(t["object_failures"]) for t in targets),
        "unknown_targets": [t["label"] for t in targets if t["verdict"] == "UNKNOWN"],
        "irreversible": True,
    }
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=(PURGE_PREVIEW_ACTION if dry_run else PURGE_ACTION),
        outcome=audit_writer.ALLOWED,
        reason=(reason or ("파기 미리보기" if dry_run else "보존기간 파기"))[:400],
        before={"group_id": group_id, "retention_days": days,
                "cutoff": cutoff.isoformat()},
        after={k: v for k, v in payload.items() if k != "measured_at"})
    payload["audit_id"] = entry.audit_id
    payload["row_hash"] = entry.row_hash
    log.info("[LAW-02a] 테넌트 %s · %s일 기준 %s — 만료 %d건 · 파기 %d건 · "
             "객체 %d건 (감사 %s)", group_id, days,
             "미리보기" if dry_run else "집행", payload["expired_total"],
             payload["deleted_total"], payload["objects_deleted_total"],
             entry.audit_id)
    return payload


def purge_all_declared(*, dry_run: bool = True, actor=None,
                       reason: str = "") -> dict:
    """**선언한 테넌트만** 돌며 파기한다. 주기 실행이 부르는 자리.

    선언하지 않은 테넌트는 여기 목록에 애초에 오르지 않는다 — 「건너뛴다」가 아니라
    **범위 밖**이다. 그 차이를 응답이 skipped_undeclared 로 말한다.
    """
    rows = declared_tenants()
    UserGroup = apps.get_model("user", "UserGroup")
    total_tenants = UserGroup._base_manager.count()
    results = [purge(group_id=r["group_id"], days=r["retention_days"],
                     dry_run=dry_run, actor=actor,
                     reason=reason or "주기 집행 — 선언한 보존 일수대로 파기한다")
               for r in rows]
    return {
        "measured_at": timezone.now().isoformat(timespec="seconds"),
        "dry_run": bool(dry_run),
        "tenants_total": total_tenants,
        "tenants_declared": len(rows),
        "skipped_undeclared": max(total_tenants - len(rows), 0),
        "deleted_total": sum(r["deleted_total"] for r in results),
        "objects_deleted_total": sum(r["objects_deleted_total"] for r in results),
        "object_failure_total": sum(r["object_failure_total"] for r in results),
        "expired_total": sum(r["expired_total"] for r in results),
        "audit_ids": [r["audit_id"] for r in results],
        "tenants": results,
        "irreversible": True,
    }


def purge_history(*, group_id=None, limit: int = 50) -> list:
    """**「지운 기록」** — 파기 감사 전건 (GX-COPY §5 낱말).

    ⚠ `audit_writer.read()` 를 쓰지 않는다. 그 함수가 돌려주는 `AuditEntry` 에는
      `data_after` 도 시각도 없다 [실측 common/audit_writer.py:122] — 「무엇을 몇 건
      지웠나」가 그 값에는 아예 없다. 여기서는 표를 직접 읽는다.

    Args:
        group_id: 주면 그 테넌트 것만. **주지 않으면 전건**이고, 좁히는 판단은
            부르는 라우트가 한다 (`audit.entries` 와 같은 규약).
    """
    AuditLogs = apps.get_model("logger", "AuditLogs")
    qs = (AuditLogs._base_manager
          .filter(logger_name=LOGGER_NAME,
                  api_name__in=(PURGE_ACTION, PURGE_PREVIEW_ACTION,
                                PURGE_SKIPPED_ACTION))
          .order_by("-id"))
    rows = []
    for row in qs[:max(int(limit), 1) * 4]:
        after = row.data_after or {}
        if group_id is not None and str(after.get("group_id")) != str(group_id):
            continue
        rows.append({
            "audit_id": row.pk,
            "action": row.api_name or "",
            "actor_id": row.user_id,
            "at": (row.create_datetime.isoformat()
                   if getattr(row, "create_datetime", None) else None),
            "group_id": after.get("group_id"),
            "retention_days": after.get("retention_days"),
            "verdict": after.get("verdict"),
            "dry_run": after.get("dry_run"),
            "deleted_total": after.get("deleted_total", 0),
            "objects_deleted_total": after.get("objects_deleted_total", 0),
            "reason": row.note or "",
        })
        if len(rows) >= int(limit):
            break
    return rows
