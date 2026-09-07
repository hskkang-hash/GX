# -*- coding: utf-8 -*-
"""관제 역할에서 인수 자산·레거시 메뉴의 **연결만** 끊는다 — UX-21(P-40) · P-50.

★ **묶음이 둘이다.** 무엇을 누구에게서 끊는지가 판정마다 다르다(`CUT_BUNDLES`):

      UX-21   인수 자산 8자리 → U1·U2·U4        (U5 유지 — 장비 등록의 자리)
      P-50    레거시 셋+묶음 마디 4자리 → U1·U2·U4·**U5**
              감시 대시보드 · 미디어 버킷 · 드론 다중 스트림 · Media Viewer 마디

  `--bundle UX-21` / `--bundle P-50` 로 하나만 돌릴 수 있다. 안 주면 **둘 다**.
  두 묶음은 `/media-data` 에서 겹치는데, 겹친 행은 **한 번만** 끊고 장부에는
  `bundle` 칸으로 어느 판정이 끊었는지 적는다.

★★ **이 끊기는 소속(테넌트)을 가로지른다 — 그것을 알고 한다.**

    이 명령이 쓰는 표는 `core.menu.RoleMenu` 이고, 분류 등록부
    (`backend/tests/tenant_classification.py`)에서 그 표는 **DEFERRED** 다 —
    「역할↔메뉴 매핑. **일부만 공용일 수 있다**」. 즉 **아직 아무도 정하지 않았다.**
    선언이 없으므로 실물을 쟀다 [실측 2026-09-05 · 개발 DB]:

        RoleMenu 969행 중 **926행이 소속을 갖는다**(그룹 4·5·6·7) · 소속 없음 43행

    **공용 마스터가 아니다.** 그러므로 소속을 안 가리고 끊으면 **남의 소속까지**
    끊긴다. 그것이 이 명령이 `--group` 또는 `--all-tenants` 중 하나를 **반드시**
    받는 이유다 — 조용한 기본값을 두지 않는다. 기본값이 전역인 명령은 언젠가
    반드시 모르고 눌린다.

    ⚠ `--all-tenants` 로 돌리면 그 역할을 쓰는 **모든 소속**에서 끊긴다. 나중에 다른
      지자체가 자기 관제요원에게 드론 화면을 보여 주고 싶어도 **이미 끊겨 있고**,
      왜 끊겼는지 그 사람은 모른다. 그래서 셋을 남긴다:
          장부      docs/agent/evidence/UX-21/menu_unlink_ledger.json
          안내      docs/agent/evidence/UX-21/README.md
          되돌리기  python manage.py relink_control_role_menus

    # 무엇이 바뀌는지 먼저 본다 (쓰기 면은 dry-run 이 먼저다)
    python manage.py unlink_control_role_menus --all-tenants --dry-run

    # 한 소속만
    python manage.py unlink_control_role_menus --group 6

    # 집행 · 검사
    python manage.py unlink_control_role_menus --all-tenants
    python manage.py unlink_control_role_menus --all-tenants --check

★ 지우지 않는다. `Menu` 행도, 라우트도, `RoleMenu` 행도 **한 줄도 안 지운다.**
  끊는 것은 그 행의 네 칸(read·create·update·delete)뿐이고, 바꾸기 전 값은 장부에 남는다.
★ U5(시스템 관리자)는 **UX-21 묶음에서만** 유지한다 — 세종 P-40 그대로.
  P-50 묶음(레거시 셋)은 **U5 에서도 끊는다** — 상용 점검 §8: 관제 제품인데
  인수 자산 화면이 그대로 보인다. 셋은 장비 등록의 자리가 아니라 고장났거나
  (스켈레톤 고착 · 검은 타일) **대체된**(UX-23 카메라 격자) 화면이다.
★ `superuser` 는 어느 묶음에도 없다 — 전역 관리자 판정은 `tenant_roles` 한 곳이
  한다(D-212). 그 역할에는 셋이 **그대로 보인다.** 모르고 남긴 것이 아니다.
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
    all_target_role_menus,
    assert_classification_unchanged,
    bundles_by_id,
    default_ledger_path,
    is_live,
    live_link_count,
)


def _load_ledger(path: Path) -> dict:
    if not path.exists():
        return {"decision": "P-40", "clause": "UX-21", "entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _key(entry: dict) -> tuple:
    return (entry["role_code"], entry["menu_id"], entry.get("group_id"))


class Command(BaseCommand):
    help = ("UX-21 · P-50 — 관제 역할의 인수 자산·레거시 메뉴 연결을 끊는다"
            "(묶음 둘: UX-21 은 U1·U2·U4 · P-50 은 U5 까지). "
            "**공용이 아니라 소속을 갖는 표다**(core.menu.RoleMenu · 등록부 DEFERRED) — "
            "--group 또는 --all-tenants 를 반드시 준다. "
            "되돌리기: relink_control_role_menus · 장부: docs/agent/evidence/UX-21/")

    def add_arguments(self, parser):
        parser.add_argument("--group", type=int, action="append", default=None,
                            help="이 소속만 끊는다. 여러 번 줄 수 있다")
        parser.add_argument("--all-tenants", action="store_true",
                            help="모든 소속에서 끊는다 — 전역이라는 것을 **선언하는** 것이다")
        parser.add_argument("--dry-run", action="store_true", help="바꾸지 않고 표만 낸다")
        parser.add_argument("--list", action="store_true", dest="show", help="현황만 낸다")
        parser.add_argument("--bundle", action="append", default=None,
                            choices=list(BUNDLE_IDS),
                            help="이 판정의 묶음만 끊는다(여러 번 가능). 안 주면 전부")
        parser.add_argument("--check", action="store_true", help="살아 있는 연결이 있으면 exit 1")
        parser.add_argument("--ledger", default=None, help="장부 파일 경로")

    # ── 분류 선언 — 쓰기 전에 **이 표가 누구 것인지 묻는다** (D-270 ③) ──────
    def _declare_classification(self):
        """등록부가 분류의 **유일한 출처**다 — 여기에 판정식을 복사하지 않는다(D-212)."""
        got, why, refuse = assert_classification_unchanged()
        if refuse:
            raise CommandError(refuse)
        self.stdout.write(self.style.WARNING(
            "[분류] %s = %s (기대 %s) — %s"
            % (WRITE_TARGET, got, EXPECTED_CLASSIFICATION, " ".join(why.split()))))
        self.stdout.write(
            "[분류] 이 표는 **공용 마스터가 아니다** — 행이 소속을 갖는다. "
            "안 가리고 끊으면 남의 소속까지 끊긴다.")
        return got

    def handle(self, *args, **opts):
        ledger_path = Path(opts["ledger"]) if opts["ledger"] else default_ledger_path()
        self._declare_classification()

        groups = opts.get("group")
        all_tenants = opts.get("all_tenants")
        if bool(groups) == bool(all_tenants):
            # 둘 다 주거나 둘 다 안 주면 멈춘다 — **조용한 기본값을 두지 않는다.**
            raise CommandError(
                "--group <소속id> (여러 번 가능) 또는 --all-tenants 중 하나를 주십시오. "
                "기본값을 두지 않는 이유: 이 표는 소속을 갖고, 안 가리면 남의 소속까지 "
                "끊긴다. 무엇을 끊는지 부르는 쪽이 말해야 합니다.")
        scope = "all-tenants" if all_tenants else sorted(groups)
        scoped = None if all_tenants else groups

        try:
            bundles = bundles_by_id(opts.get("bundle"))
        except KeyError as exc:                     # pragma: no cover — choices 가 먼저 막는다
            raise CommandError(str(exc))

        pairs = all_target_role_menus(group_ids=scoped, bundles=bundles)
        rows = [r for r, _ in pairs]
        of_bundle = {r.pk: bid for r, bid in pairs}
        live = [r for r in rows if is_live(r)]

        for b in bundles:
            self.stdout.write("[묶음 %s] %s" % (b["id"], b["why"]))
            self.stdout.write("   역할 %d: %s" % (len(b["roles"]), " · ".join(b["roles"])))
            self.stdout.write("   유지 %d: %s" % (len(b["keep"]),
                                                 " · ".join(b["keep"]) or "없음"))
            self.stdout.write("   메뉴 %d자리: %s" % (len(b["paths"]), " ".join(b["paths"])))
        self.stdout.write("범위: %s" % ("모든 소속" if all_tenants else "소속 %s" % scope))
        hit = Counter(r.group_id for r in live)
        self.stdout.write("대상 연결 행 %d · 살아 있는 연결 %d · 걸리는 소속 %s"
                          % (len(rows), len(live), dict(hit) or "없음"))
        for r in sorted(live, key=lambda x: (str(x.group_id), x.role.code, x.menu.path)):
            flags = "".join("RCUD"[i] if getattr(r, f) else "-"
                            for i, f in enumerate(PERMIT_FIELDS))
            self.stdout.write("  소속%-5s %-8s %-22s %-24s [%s] %s"
                              % (r.group_id, of_bundle[r.pk], r.role.code, r.menu.path,
                                 flags, r.menu.menu_name))

        if opts["check"]:
            n = live_link_count(group_ids=scoped, bundles=bundles)
            self.stdout.write("남은 연결: %d" % n)
            if n:
                raise SystemExit(1)
            return

        if opts["show"]:
            return

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "dry-run — 아무것도 쓰지 않았다. 집행하려면 --dry-run 을 뺀다."))
            return

        if not live:
            self.stdout.write(self.style.SUCCESS("끊을 것이 없다 — 이미 0개다."))
            return

        ledger = _load_ledger(ledger_path)
        ledger["write_target"] = WRITE_TARGET
        ledger["classification"] = EXPECTED_CLASSIFICATION
        ledger["scope"] = scope
        ledger["bundles"] = [b["id"] for b in bundles]
        known = {_key(e) for e in ledger["entries"]}

        with transaction.atomic():
            for r in live:
                entry = {
                    "role_code": r.role.code,
                    "role_id": r.role_id,
                    "menu_id": r.menu_id,
                    "menu_path": r.menu.path,
                    "menu_name": r.menu.menu_name,
                    "role_menu_id": r.id,
                    # ★ 소속을 적는다. 없으면 되돌리기가 **어느 소속의 것인지** 말하지
                    #   못하고, 다음 사람이 「왜 우리 메뉴가 없나」에 답을 못 찾는다.
                    "group_id": r.group_id,
                    # ★ **어느 판정으로 끊었나.** 이것이 없으면 되돌릴 때 「UX-21 만
                    #   되살리고 P-50 은 그대로」를 고를 수 없다.
                    "bundle": of_bundle[r.pk],
                    "before": {f: bool(getattr(r, f)) for f in PERMIT_FIELDS},
                    "cut_at": datetime.now(dt_timezone.utc).isoformat(),
                }
                # 이 행은 **지금 살아 있다** — 그러므로 방금 읽은 네 칸이 되돌릴 진실이다.
                # (이미 끊긴 행은 live 에 없으므로 여기 오지 않는다. 두 번 돌려도 안 덮인다.)
                if _key(entry) in known:
                    ledger["entries"] = [e for e in ledger["entries"]
                                         if _key(e) != _key(entry)]
                ledger["entries"].append(entry)
                known.add(_key(entry))
                for f in PERMIT_FIELDS:
                    setattr(r, f, False)
                r.save(update_fields=list(PERMIT_FIELDS))

        ledger["updated_at"] = datetime.now(dt_timezone.utc).isoformat()
        #: ★ [P-87 ④ · 턴 I] **시험 중에는 장부를 안 쓴다.** 장부는 되돌리기의
        #:   유일한 근거이고(OPS-07b), 시험 DB 의 연결 상태로 그 파일을 덮으면
        #:   되돌릴 수 있다고 믿은 채 되돌릴 수 없게 된다.
        written = evidence_guard.write_text_guarded(
            ledger_path, json.dumps(ledger, ensure_ascii=False, indent=2),
            who="unlink_control_role_menus 장부")
        if written is None:
            self.stdout.write(self.style.WARNING(
                "장부를 **안 썼다** — 시험 중이다 (증거 폴더 격리 가드 · P-87 ④). "
                "끊은 연결은 그대로이고, 되돌리려면 시험 밖에서 다시 돌린다"))

        self.stdout.write(self.style.SUCCESS(
            "끊었다: %d개 연결 · 소속 %s · 장부 %s (행은 하나도 지우지 않았다)"
            % (len(live), dict(hit), ledger_path)))
        self.stdout.write("남은 연결: %d"
                          % live_link_count(group_ids=scoped, bundles=bundles))
