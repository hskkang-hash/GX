# -*- coding: utf-8 -*-
"""끊은 역할↔메뉴 연결을 **장부대로** 되잇는다 — UX-21 · P-50 되돌리기.

★ 장부 항목마다 **어느 판정으로 끊었나**(`bundle`)가 적혀 있다. `--bundle P-50`
  으로 그 판정만 되돌릴 수 있다 — 「레거시 셋은 되살리되 인수 자산 8자리는
  끊긴 채로」가 가능해야 판정 하나를 무를 수 있다.
  `bundle` 칸이 없는 옛 항목은 UX-21 로 읽는다(그때는 묶음이 하나뿐이었다).

★★ **이 표는 소속(테넌트)을 갖는다 — 공용 마스터가 아니다.**
    쓰는 표는 `core.menu.RoleMenu` 이고, 분류 등록부
    (`backend/tests/tenant_classification.py`)에서 **DEFERRED** 다
    (「일부만 공용일 수 있다」 — 아직 아무도 정하지 않았다).
    실물은 969행 중 926행이 소속을 갖는다 [실측 2026-09-05].
    그래서 되돌리기도 **장부에 적힌 소속의 그 행만** 건드린다.

    python manage.py relink_control_role_menus --dry-run
    python manage.py relink_control_role_menus
    python manage.py relink_control_role_menus --group 6   # 그 소속만 되돌린다

★ 표가 아니라 **장부**를 되돌려 쓴다. 표만 보고 켜면 끊기 전부터 꺼져 있던 연결까지
  켜서 **없던 권한을 준다** — 그것은 되돌리기가 아니라 새 부여다.
★ 장부가 없으면 아무것도 하지 않고 멈춘다 — 「되돌릴 것이 없다」와
  「되돌릴 것을 모른다」는 다른 사실이다.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from common import evidence_guard
from common.menu_exposure import (
    BUNDLE_IDS,
    EXPECTED_CLASSIFICATION,
    PERMIT_FIELDS,
    WRITE_TARGET,
    assert_classification_unchanged,
    bundles_by_id,
    default_ledger_path,
    live_link_count,
)


class Command(BaseCommand):
    help = ("UX-21 · P-50 되돌리기 — 장부에 적힌 대로 역할↔메뉴 연결을 다시 잇는다"
            "(`--bundle` 로 판정 하나만 무를 수 있다). "
            "**공용이 아니라 소속을 갖는 표다**(core.menu.RoleMenu · 등록부 DEFERRED). "
            "장부: docs/agent/evidence/UX-21/menu_unlink_ledger.json")

    def add_arguments(self, parser):
        parser.add_argument("--group", type=int, action="append", default=None,
                            help="이 소속의 항목만 되돌린다. 여러 번 줄 수 있다")
        parser.add_argument("--bundle", action="append", default=None,
                            choices=list(BUNDLE_IDS),
                            help="이 판정으로 끊은 것만 되돌린다(여러 번 가능). "
                                 "안 주면 장부의 안 되돌린 것 전부")
        parser.add_argument("--dry-run", action="store_true", help="바꾸지 않고 표만 낸다")
        parser.add_argument("--ledger", default=None)

    def _declare_classification(self):
        """등록부가 분류의 **유일한 출처**다 — 여기에 판정식을 복사하지 않는다(D-212)."""
        got, why, refuse = assert_classification_unchanged()
        if refuse:
            raise CommandError(refuse)
        self.stdout.write(self.style.WARNING(
            "[분류] %s = %s (기대 %s) — %s"
            % (WRITE_TARGET, got, EXPECTED_CLASSIFICATION, " ".join(why.split()))))
        return got

    def handle(self, *args, **opts):
        from core.menu.models import RoleMenu  # dj-core — 읽고 그 행의 칸만 되돌린다

        self._declare_classification()

        ledger_path = Path(opts["ledger"]) if opts["ledger"] else default_ledger_path()
        if not ledger_path.exists():
            raise CommandError(
                "장부가 없다: %s — 무엇을 되돌릴지 모르므로 멈춘다." % ledger_path)

        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        groups = opts.get("group")
        entries = [e for e in ledger.get("entries", []) if not e.get("restored_at")]
        if groups:
            entries = [e for e in entries if e.get("group_id") in set(groups)]

        want_bundles = opts.get("bundle")
        if want_bundles:
            try:
                bundles_by_id(want_bundles)          # 모르는 이름이면 여기서 멈춘다
            except KeyError as exc:                  # pragma: no cover — choices 가 먼저 막는다
                raise CommandError(str(exc))
            # ★ `bundle` 칸이 없는 항목은 **P-50 이전에 끊은 것**이다(UX-21 만 있던 때).
            #   「모르니까 포함」이 아니라 「그때는 UX-21 뿐이었다」는 사실로 읽는다.
            entries = [e for e in entries
                       if e.get("bundle", "UX-21") in set(want_bundles)]

        self.stdout.write("장부 %s · 끊을 때 범위 %s"
                          % (ledger_path, ledger.get("scope", "(안 적힘)")))
        self.stdout.write("되돌릴 항목 %d · 소속 %s"
                          % (len(entries),
                             dict(Counter(e.get("group_id") for e in entries)) or "없음"))
        for e in entries:
            self.stdout.write("  소속%-5s %-8s %-22s %-24s → %s" % (
                e.get("group_id"), e.get("bundle", "UX-21"),
                e["role_code"], e["menu_path"],
                "".join("RCUD"[i] if e["before"][f] else "-"
                        for i, f in enumerate(PERMIT_FIELDS)),
            ))

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("dry-run — 아무것도 쓰지 않았다."))
            return
        if not entries:
            self.stdout.write(self.style.SUCCESS("되돌릴 것이 없다."))
            return

        missing, restored = [], 0
        with transaction.atomic():
            for e in entries:
                # ★ **소속까지 좁힌다.** (역할, 메뉴)만으로 고르면 같은 짝이 여러
                #   소속에 있을 때 `.first()` 가 **남의 소속 행**을 되살릴 수 있다.
                #   장부는 소속을 적어 두었으므로 그것을 쓴다(옛 항목은 안 적혀 있다).
                qs = RoleMenu.objects.filter(
                    role_id=e["role_id"], menu_id=e["menu_id"])
                if e.get("group_id") is not None:
                    qs = qs.filter(group_id=e["group_id"])
                rm = qs.first()
                if rm is None:
                    # 조용히 넘어가지 않는다 — 넘어가면 「다 되돌렸다」가 거짓이 된다.
                    missing.append(e)
                    continue
                for f in PERMIT_FIELDS:
                    setattr(rm, f, bool(e["before"][f]))
                rm.save(update_fields=list(PERMIT_FIELDS))
                e["restored_at"] = datetime.now(dt_timezone.utc).isoformat()
                restored += 1

        ledger["updated_at"] = datetime.now(dt_timezone.utc).isoformat()
        #: ★ [P-87 ④ · 턴 I] 시험 중에는 장부를 안 쓴다 — `unlink` 쪽과 같은 자리.
        written = evidence_guard.write_text_guarded(
            ledger_path, json.dumps(ledger, ensure_ascii=False, indent=2),
            who="relink_control_role_menus 장부")
        if written is None:
            self.stdout.write(self.style.WARNING(
                "장부를 **안 썼다** — 시험 중이다 (증거 폴더 격리 가드 · P-87 ④)"))

        self.stdout.write(self.style.SUCCESS(
            "되이었다: %d개 · 되살아난 연결 %d" % (restored, live_link_count())))
        if missing:
            raise CommandError("행을 찾지 못한 항목 %d개 — 장부에 남겨 두었다." % len(missing))
