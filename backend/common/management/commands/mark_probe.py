# -*- coding: utf-8 -*-
"""P-457 — **탐침 표식은 관리 명령 한 줄로.** 대표가 한 번 허락하는 이름 붙은 명령.

    표식   python manage.py mark_probe --id 8871 8872 --reason "U5#4 측정기 잔여 · 예시 CSV 글자 일치"
    미리   python manage.py mark_probe --id 8871 8872 --reason "…" --dry-run
    되돌림 python manage.py mark_probe --id 8871 8872 --undo
    다른 표 python manage.py mark_probe --model user.coreuser --id 123 --reason "…"

★ **곁표만 쓴다** (P-457 · P-453 「삭제가 아니라 표식」).
  `common.BillingMark` 에 `probe` 한 줄을 적을 뿐이고 **가리키는 행은 한 글자도 안
  고친다** — 카메라의 제 칸(`data_source`)도 그대로 `live` 다. 그래서 되돌리기는
  곁표 한 줄을 지우는 것으로 끝나고, 행이 무엇이었는지는 되돌린 뒤에도 그대로다.
  제품이 이 줄을 읽는 자리는 `billing_marks.exclude_not_counted` 의 ㉢ 갈래 하나다.

★ **덮어쓰지 않는다.** 이미 다른 낱말(`seed` · `drill` · `live`)로 적힌 행은 거절한다 —
  `mark_unbillable` 은 update_or_create 라서 그대로 부르면 씨앗 표식이 조용히 탐침으로
  바뀌고, `--undo` 뒤에는 원래 표식이 **사라진 채**로 남는다. 그 행은 사람이 본다.

★ **사유는 비울 수 없다.** 빈 사유는 면제와 구별되지 않는다(`BillingMark.reason`).

★ **지우지 않는다.** 행 삭제는 대표 몫이다(P-453). 이 명령에는 그 문이 없다.
"""
from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from common.billing_marks import _mark_model, mark_unbillable

#: 이 명령이 적는 낱말. `probe_marker` 가 정본이고 여기서 다시 타자하지 않는다.
from common.billing_marks import NOT_COUNTED_SOURCES

PROBE_SOURCE = NOT_COUNTED_SOURCES[0]

#: 곁표 사유 앞머리 — 「이 줄은 이 명령이 적었다」를 사람이 읽고 알 수 있게.
REASON_PREFIX = "mark_probe · P-457 · "

DEFAULT_MODEL = "stream_monitors.streammonitor"


def _refuse_shared_master(model) -> None:
    """공용 마스터 행에는 탐침 표식을 달지 않는다 (D-270 ③).

    탐침은 「고객이 세야 하나」에서 빠지는 표식이다. 공용 마스터 행에 달면 **모든
    테넌트** 화면에서 그 행이 사라진다 — 한 테넌트의 찌꺼기를 치우려다 남의 것을 치운다.
    등록부(`tests/tenant_classification.py`)가 그 분류의 유일한 출처다 · 못 읽으면 안 쓴다
    (「검사 못함」과 「대상 아님」은 다른 사실 — D-301).
    """
    try:
        from tests.tenant_classification import SHARED_MASTERS
    except ImportError as exc:                     # pragma: no cover - 환경 문제
        raise CommandError(
            f"분류 등록부(tests/tenant_classification.py)를 읽지 못했다: {exc} — "
            f"공용 마스터인지 확인하지 못한 채로 표식하지 않는다 (D-270 ③ · D-301)") from exc
    if model._meta.label in SHARED_MASTERS:
        raise CommandError(
            f"{model._meta.label} 은 분류 등록부의 **공용 마스터**다 — 탐침 표식을 달면 "
            f"모든 테넌트에서 그 행이 사라진다.")


class Command(BaseCommand):
    help = "P-457 탐침 표식 — 곁표(common.BillingMark)에 probe 한 줄 · 되돌리기 --undo · 행은 안 고친다"

    def add_arguments(self, parser):
        parser.add_argument("--id", dest="ids", nargs="+", required=True,
                            help="표식할 행의 pk (여러 개 가능)")
        parser.add_argument("--model", default=DEFAULT_MODEL,
                            help=f"표 이름 app_label.modelname (기본 {DEFAULT_MODEL})")
        parser.add_argument("--reason", default="",
                            help="왜 탐침인가 — 코드를 안 읽고 답할 수 있는 한 줄 (표식에 필수)")
        parser.add_argument("--undo", action="store_true",
                            help="이 명령이 적은 probe 곁표 줄을 지운다 (행은 그대로)")
        parser.add_argument("--dry-run", action="store_true",
                            help="무엇을 할지 보이기만 하고 쓰지 않는다")

    def handle(self, *args, **opts):
        label = opts["model"].lower()
        try:
            model = apps.get_model(label)
        except (LookupError, ValueError) as exc:
            raise CommandError(f"모르는 표입니다: {label!r} ({exc})") from exc
        Mark = _mark_model()
        if Mark is None:
            raise CommandError("곁표(common.BillingMark)가 없습니다 — 마이그레이션 먼저.")
        _refuse_shared_master(model)

        ids = [str(i) for i in opts["ids"]]
        reason = opts["reason"].strip()
        if not opts["undo"] and not reason:
            raise CommandError("--reason 이 비었습니다 — 빈 사유는 면제와 구별되지 않습니다.")

        marks = Mark._base_manager.filter(model_label=label)
        plan = []
        for oid in ids:
            existing = marks.filter(object_id=oid).first()
            if opts["undo"]:
                if existing is None:
                    plan.append((oid, "skip", "곁표 줄 없음"))
                elif existing.data_source != PROBE_SOURCE:
                    raise CommandError(
                        f"{label} #{oid} 의 곁표는 {existing.data_source!r} 입니다 — "
                        f"probe 가 아닌 표식은 이 명령이 지우지 않습니다.")
                else:
                    plan.append((oid, "undo", existing.reason))
                continue
            obj = model._base_manager.filter(pk=oid).first()
            if obj is None:
                raise CommandError(f"{label} #{oid} 행이 없습니다 — 아무것도 쓰지 않았습니다.")
            if existing is not None and existing.data_source != PROBE_SOURCE:
                raise CommandError(
                    f"{label} #{oid} 에 이미 {existing.data_source!r} 곁표가 있습니다 — "
                    f"덮어쓰지 않습니다(되돌릴 때 원래 표식이 사라집니다).")
            if existing is not None:
                plan.append((oid, "skip", "이미 probe"))
            else:
                plan.append((oid, "mark", str(obj)))

        # 전부 검사한 뒤에 쓴다 — 하나라도 거절이면 위에서 이미 멈췄다(반쪽 집행 0).
        with transaction.atomic():
            for oid, action, note in plan:
                verb = {"mark": "표식", "undo": "되돌림", "skip": "그대로"}[action]
                prefix = "[미리] " if opts["dry_run"] else ""
                self.stdout.write(f"{prefix}{verb}  {label} #{oid}  · {note}")
                if opts["dry_run"]:
                    continue
                if action == "mark":
                    obj = model._base_manager.get(pk=oid)
                    mark_unbillable(obj, PROBE_SOURCE, reason=REASON_PREFIX + reason)
                elif action == "undo":
                    marks.filter(object_id=oid, data_source=PROBE_SOURCE).delete()

        done = sum(1 for _, a, _ in plan if a != "skip")
        self.stdout.write(
            f"{'미리 보기 — 쓰지 않음' if opts['dry_run'] else '끝'} · "
            f"{'되돌림' if opts['undo'] else '표식'} {done} · 그대로 {len(plan) - done}")
