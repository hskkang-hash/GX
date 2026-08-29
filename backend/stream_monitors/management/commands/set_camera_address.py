# -*- coding: utf-8 -*-
"""카메라 설치 주소를 **채우는 자리** — D-338.

왜 이것이 먼저인가
------------------
`install_address` 는 **정의 있음 · 읽기 있음 · 쓰기 0곳**이었다.
D-304 착시 ⑥(스키마의 착시)의 정확한 형태다 — `clip_path` 가 그랬다.

계측기(`scripts/verify_camera_address.py`)가 「39/39 미입력」을 출력하니 **숨지는 않는다.**
그러나 **숨지 않는 것과 살아 있는 것은 다르다.** 채울 수단이 없으면 그 수는 영원히 39 다.
관리자 UI 는 나중이어도 좋으나, **지금 채울 수 있어야 한다**(D-338 ①).

무엇을 하는가
-------------
    # 한 대
    python manage.py set_camera_address --name "정문카메라" \\
        --address "경기도 안양시 만안구 안양로 123" --detail "정문"

    # 여럿 — 대표께 부탁드린 세 칸 그대로다 (이름 / 도로명주소 / 현장 표현)
    python manage.py set_camera_address --csv cameras.csv

    # 무엇이 바뀌는지 먼저 본다. **기본이 이쪽이 아니라는 점을 분명히 한다**
    python manage.py set_camera_address --csv cameras.csv --dry-run

    # 지금 현황
    python manage.py set_camera_address --list

CSV 형식 — 헤더 있는 세 칸. 셋째 칸은 비어도 된다.

    name,address,detail
    정문카메라,경기도 안양시 만안구 안양로 123,정문
    3층복도,경기도 안양시 만안구 안양로 123,3층 복도

규약
----
· `address_source` 는 **`manual` 로만 쓴다.** 팝업 API 로 채워도 출처는 사람이다(D-331).
· 주소를 지우려면 `--clear` 를 쓴다. 빈 문자열을 주소로 넣지 않는다 —
  **「안 적음」과 「빈 주소」는 다른 사실이다**(D-290). 지우면 `unset` 으로 돌아간다.
· 이름이 겹치면 **아무것도 쓰지 않고 멈춘다.** 어느 카메라인지 모르는 채로 쓰면
  엉뚱한 카메라의 주소가 알림에 나가고, 그 알림은 사람을 엉뚱한 곳으로 보낸다.
· 없는 이름은 **건너뛰지 않고 센다.** 조용히 넘어가면 「39대 다 넣었다」는 보고가
  실제로는 3대만 들어간 상태와 구별되지 않는다(D-301).
"""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stream_monitors.models import StreamMonitor


class Command(BaseCommand):
    help = "카메라(StreamMonitor)의 설치 도로명주소를 채운다 (D-338)"

    def add_arguments(self, parser):
        parser.add_argument("--name", help="카메라 이름 (정확히 일치)")
        parser.add_argument("--id", type=int, help="카메라 id")
        parser.add_argument("--address", help="도로명주소")
        parser.add_argument("--detail", default="", help="현장 표현 — 「정문」·「3층 복도」")
        parser.add_argument("--csv", help="name,address,detail 세 칸 CSV")
        parser.add_argument("--clear", action="store_true",
                            help="주소를 지우고 unset 으로 되돌린다")
        parser.add_argument("--list", action="store_true", help="현황만 출력한다")
        parser.add_argument("--dry-run", action="store_true",
                            help="무엇이 바뀌는지만 보이고 쓰지 않는다")

    # ── 판정 ────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        self._refuse_if_shared_master()
        if opts["list"]:
            return self._list()

        rows = self._rows(opts)
        if not rows:
            raise CommandError(
                "무엇을 채울지 주지 않았다 — --name/--id 와 --address, 또는 --csv 를 쓴다. "
                "현황만 보려면 --list."
            )

        dry = opts["dry_run"]
        changed, skipped, missing, ambiguous = 0, 0, [], []

        with transaction.atomic():
            for name, cam_id, address, detail in rows:
                qs = self._all_cameras()
                qs = qs.filter(id=cam_id) if cam_id else qs.filter(name=name)
                found = list(qs[:3])

                if not found:
                    missing.append(name or f"id={cam_id}")
                    continue
                if len(found) > 1:
                    # 어느 카메라인지 모르는 채로 쓰지 않는다. 위 규약 참조.
                    ambiguous.append(name or f"id={cam_id}")
                    continue

                cam = found[0]
                if opts["clear"]:
                    new = ("", "", StreamMonitor.AddressSource.UNSET)
                else:
                    if not (address or "").strip():
                        missing.append((name or f"id={cam_id}") + " (주소가 비었다)")
                        continue
                    new = (address.strip(), (detail or "").strip(),
                           StreamMonitor.AddressSource.MANUAL)

                old = (cam.install_address or "", cam.install_address_detail or "",
                       cam.address_source)
                if old == new:
                    skipped += 1
                    continue

                self.stdout.write(
                    f"  {'(안 씀) ' if dry else ''}{cam.name}: "
                    f"{old[2]} {old[0]!r} → {new[2]} {new[0]!r}"
                    + (f" · 현장표현 {new[1]!r}" if new[1] else "")
                )
                if not dry:
                    cam.install_address = new[0] or None
                    cam.install_address_detail = new[1] or None
                    cam.address_source = new[2]
                    cam.save(update_fields=["install_address", "install_address_detail",
                                            "address_source"])
                changed += 1

            if dry:
                transaction.set_rollback(True)

        # 못 한 것을 **센다.** 조용히 넘어가지 않는다 (D-301)
        self.stdout.write(
            f"[CAMERA-ADDR] {'(모의) ' if dry else ''}바뀜 {changed} · "
            f"이미 같음 {skipped} · 못 찾음 {len(missing)} · 이름 중복 {len(ambiguous)}"
        )
        for n in missing:
            self.stdout.write(f"  못 찾음: {n}")
        for n in ambiguous:
            self.stdout.write(f"  이름이 겹친다(쓰지 않았다): {n} — --id 로 지정하라")
        if missing or ambiguous:
            raise CommandError(
                f"못 채운 것이 {len(missing) + len(ambiguous)}건이다. "
                f"「다 넣었다」와 구별되어야 하므로 실패로 끝낸다 (D-301)"
            )

    # ── 어느 매니저로 보는가 ────────────────────────────────────────────
    @staticmethod
    def _all_cameras():
        """**요청 스코프가 아니라 전수**를 본다 — `_base_manager` 를 쓴다.

        왜 `objects` 가 아닌가 [실측 2026-09-07]:
        dj-core 의 `CustomManagerGroup.get_queryset()` 은 `_request` 로 걸러내는데,
        그 `_request` 는 **인스턴스가 아니라 클래스 속성**이다(core/base.py:219).
        즉 앞서 지나간 요청이 남긴 값이 그대로 남아, 요청과 무관한 문맥에서도 걸러낸다.
        시험 전수 실행에서 이 커맨드가 **자기가 방금 만든 카메라를 못 찾는 것**으로 드러났다.

        관리 커맨드는 요청이 없다. 스코프가 **떠도는 전역에 따라 달라지면**,
        「39대 다 넣었다」가 실제로는 3대만 넣은 상태와 구별되지 않는다(D-301).
        운영자 도구는 결정적이어야 하므로 전수를 보고, 대신 아래 둘로 안전을 건다:
          · 이름이 겹치면 **아무것도 쓰지 않는다** (어느 테넌트의 카메라인지 모르는 채로 쓰지 않는다)
          · 공용 마스터로 분류된 모델이면 **멈춘다** (`_refuse_if_shared_master`)

        ⚠ §0.4 — `CustomManagerGroup` 은 dj-core 소유라 고치지 않는다. 우리는 **안 쓴다**.
        """
        return StreamMonitor._base_manager.all()

    # ── 분류 등록부 대조 (D-270 ③) ──────────────────────────────────────
    def _refuse_if_shared_master(self):
        """공용 마스터에 **현장 주소**를 쓰지 않는다.

        왜 이 검사가 진짜인가: 설치 주소는 **한 테넌트의 현장 위치**다.
        `StreamMonitor` 가 언젠가 공용 마스터로 분류되면, 여기 쓴 한 줄이
        **전 테넌트에게 남의 현장 주소를 보여 준다.** 그때 이 커맨드는 멈춰야 한다.

        분류 등록부(`tests/tenant_classification.py`)가 그 분류의 유일한 출처다 —
        판정식을 복사하지 않는다(D-212 계열). 등록부를 못 읽으면 **통과시키지 않는다**:
        「검사 못함」과 「대상 아님」은 다른 사실이다(D-301).
        """
        label = "stream_monitors.StreamMonitor"
        try:
            from tests.tenant_classification import SHARED_MASTERS
        except ImportError as exc:
            raise CommandError(
                f"분류 등록부(tests/tenant_classification.py)를 읽지 못했다: {exc} — "
                f"공용 마스터인지 확인하지 못한 채로 쓰지 않는다 (D-270 ③ · D-301)"
            )
        if label in SHARED_MASTERS:
            raise CommandError(
                f"{label} 이 분류 등록부에서 **공용 마스터**다. 설치 주소는 한 테넌트의 "
                f"현장 위치이므로 공용 행에 쓰면 남의 현장이 전 테넌트에 보인다 (D-270 ③)"
            )

    # ── 입력 ────────────────────────────────────────────────────────────
    def _rows(self, opts):
        if opts["csv"]:
            path = Path(opts["csv"])
            if not path.is_file():
                raise CommandError(f"CSV 가 없다: {path}")
            out = []
            with path.open(encoding="utf-8-sig", newline="") as f:
                for i, row in enumerate(csv.DictReader(f), 2):
                    name = (row.get("name") or "").strip()
                    if not name:
                        raise CommandError(f"{path}:{i} — name 칸이 비었다")
                    out.append((name, None, (row.get("address") or "").strip(),
                                (row.get("detail") or "").strip()))
            return out
        if opts["name"] or opts["id"]:
            return [(opts["name"], opts["id"], opts["address"] or "", opts["detail"])]
        return []

    def _list(self):
        total = self._all_cameras().count()
        unset = self._all_cameras().filter(
            address_source=StreamMonitor.AddressSource.UNSET).count()
        self.stdout.write(f"[CAMERA-ADDR] 카메라 {total}대 · 미입력 {unset}대 · "
                          f"입력됨 {total - unset}대")
        for cam in self._all_cameras().order_by("name")[:200]:
            mark = "  " if cam.address_source == StreamMonitor.AddressSource.UNSET else "✓ "
            where = cam.install_address or "(미입력)"
            detail = f" [{cam.install_address_detail}]" if cam.install_address_detail else ""
            self.stdout.write(f"  {mark}{cam.name}: {where}{detail}")
