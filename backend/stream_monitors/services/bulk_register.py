# -*- coding: utf-8 -*-
"""카메라 벌크 등록 — **dry-run 이 먼저다** (UX-18 · 차선 C · 2026-09-24 · D-209).

한 문장
-------
    100행짜리 CSV 를 받아 **무엇이 바뀔지 표로 먼저 보여 주고**, 그 표를 본 사람이
    다시 눌러야 쓴다. 표 없이 쓰는 길은 이 파일에 없다.

왜 표가 먼저인가
----------------
한 건짜리 등록 화면은 잘못 눌러도 한 건이 틀린다. 100행 일괄은 **한 번의 실수가
100대의 카메라 이름·주소를 덮어쓴다** — 그리고 덮어쓴 뒤에는 원래 값이 어디에도 없다.
`set_camera_address.py`(D-338)가 이미 `--dry-run` 을 그 이유로 갖고 있고, 이 파일은
같은 규약을 **화면에서 쓸 수 있는 모양**으로 다시 세운 것이다.

★ dry-run 과 apply 는 **같은 판정식을 쓴다.** 두 벌이면 표에 없던 일이 일어난다 —
  이 파일에서 판정은 `_plan()` 하나이고 `apply` 는 그 결과를 **재계산 없이** 집행한다.

착수 전 실측이 지시서의 두 항목을 고쳤다 [2026-09-24]
-----------------------------------------------------
지시서 §2 C행 UX-18 은 「CSV/**ONVIF** 일괄 등록 + **좌표→도로명 역지오코딩**」이라 적었다.

① **ONVIF 는 이 저장소에 없다.** `grep -ril onvif backend/` = **0건**.
   디스커버리 라이브러리도 어댑터 자리도 없다. 없는 프로토콜 위에 화면을 얹지 않는다
   (P-15 「문 없는 길 위에 화면 금지」의 같은 계열). CSV 만 낸다 — 그리고 이 파일의
   `Row` 는 출처를 칸으로 갖는다(`source`), ONVIF 어댑터가 생기면 **그 칸의 값이
   하나 늘 뿐** 나머지(판정·표·집행)는 그대로 쓰인다.

② **좌표→도로명 역지오코딩은 이미 「불가」로 판정돼 있다** (D-329 · `adapters/juso`
   `JUSO_REVERSE_SUPPORTED = 'no'`). 발급된 승인키 2건이 둘 다 「도로명주소 팝업 API」
   였고, 그것은 서버 조회 API 가 아니다. 게다가 **FX-5 자체가 대체됐다**(D-330):
   *카메라는 고정 설치물이므로 설치할 때 주소를 안다 — 적어 두지 않았을 뿐이다.*
   그리고 `StreamMonitor` 에는 **위도·경도 칸이 아예 없다** [실측] — 역지오코딩할
   좌표가 애초에 없다.
   → 그래서 주소는 **CSV 의 `address` 칸**으로 들어온다(D-330 이 정한 길). 좌표가
     CSV 에 실려 오면 `adapters.juso.resolve` 를 **부르기는 한다** — 그 어댑터가
     살아나는 날 이 경로가 그대로 열리고, 지금은 `disabled` 를 정직하게 표에 적는다.

지금 현황 — **39/40 미입력** [지시서 실측]. 이 파일이 그 수를 줄이는 손이고,
`address_gap()` 이 그 수를 **화면에 배지로** 내보내는 눈이다.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from django.core.exceptions import PermissionDenied
from django.db import transaction

import adapters.juso as juso
from common.tenant_filters import get_user_group, require_user_group
from common.tenant_roles import is_global_admin
from common.tenant_scope import TenantScope

log = logging.getLogger(__name__)

#: 한 번에 받는 행의 상한. 상한 없이 받으면 요청 하나가 표 전체를 다시 쓴다.
#: ★ 상한에 닿았다는 사실은 오류로 **말한다** — 조용히 자르면 「100행 넣었다」는 보고가
#:   실제로는 500행 중 100행인 상태와 구별되지 않는다(D-301).
MAX_ROWS = 500

#: CSV 머리글. `set_camera_address.py` 의 세 칸(name/address/detail)을 **그대로 품는다** —
#: 이미 그 형식으로 파일을 만든 사람이 있고, 그 파일이 여기서도 그대로 돌아야 한다.
REQUIRED_COLUMNS = ("name",)
OPTIONAL_COLUMNS = ("code", "ip_source", "address", "detail", "lat", "lng")

#: 행 하나의 판정 다섯. **「건너뜀」과 「오류」를 합치지 않는다**(D-290) —
#: 합치면 「이미 있어서 안 바꿨다」와 「이름이 겹쳐 못 바꿨다」가 같은 수로 세어진다.
CREATE, UPDATE, UNCHANGED, ERROR = "create", "update", "unchanged", "error"

#: 주소 출처. 팝업 API 로 채워도 출처는 **사람**이다 (D-331).
ADDRESS_SOURCE_MANUAL = "manual"
ADDRESS_SOURCE_UNSET = "unset"


@dataclass
class Row:
    """CSV 한 줄에 대한 **판정 한 줄.** 표의 한 행이 곧 이것이다."""

    line: int
    name: str
    action: str = ERROR
    reason: str = ""
    #: 무엇이 무엇으로 바뀌는가. **바뀌는 칸만** 담는다 — 안 바뀌는 칸을 담으면
    #: 표가 길어지고, 긴 표는 안 읽힌다. 안 읽힌 표는 dry-run 이 아니다.
    changes: dict[str, list] = field(default_factory=dict)
    camera_id: int | None = None
    #: 출처. 지금은 `csv` 하나뿐이고 ONVIF 어댑터가 생기면 값이 하나 는다.
    source: str = "csv"
    #: 좌표를 준 행에 대해 주소 어댑터가 뭐라 했는가 (`disabled`/`resolved`/`failed`).
    address_lookup: str = ""

    def as_dict(self) -> dict:
        return {
            "line": self.line, "name": self.name, "action": self.action,
            "reason": self.reason, "changes": self.changes,
            "camera_id": self.camera_id, "source": self.source,
            "address_lookup": self.address_lookup,
        }


@dataclass
class Plan:
    """dry-run 표 전체. **모수를 함께 낸다** (D-301)."""

    rows: list[Row] = field(default_factory=list)
    #: 파일 전체를 못 읽은 사유. 있으면 **한 행도 쓰지 않는다.**
    fatal: str = ""

    @property
    def counts(self) -> dict[str, int]:
        out = {CREATE: 0, UPDATE: 0, UNCHANGED: 0, ERROR: 0}
        for row in self.rows:
            out[row.action] = out.get(row.action, 0) + 1
        return out

    @property
    def writable(self) -> list[Row]:
        return [r for r in self.rows if r.action in (CREATE, UPDATE)]

    def as_dict(self) -> dict:
        counts = self.counts
        return {
            "dry_run": True,
            "fatal": self.fatal,
            "total": len(self.rows),
            "counts": counts,
            #: ★ 쓸 수 있는 행이 0 이면 그것은 성공이 아니다. 화면이 「적용」 버튼을
            #:   그릴지 말지를 이 값으로 정한다 — 누를 수 있는데 아무 일도 안 일어나는
            #:   버튼은 D-284 가 이름 붙인 조용한 성공이다.
            "will_write": len(self.writable),
            "rows": [r.as_dict() for r in self.rows],
        }


# ═══════════════════════════════════════════════════════════════════════════
# 읽기 — CSV 파싱은 **DB 를 만지지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
def parse_csv(text: str) -> tuple[list[dict], str]:
    """(행들, 치명 사유). 사유가 있으면 행은 비어 있고 **한 행도 쓰지 않는다.**"""
    if not (text or "").strip():
        return [], "빈 파일입니다 — 읽을 행이 없습니다."
    try:
        reader = csv.DictReader(io.StringIO(text))
        fields = [(f or "").strip().lower() for f in (reader.fieldnames or [])]
    except csv.Error as exc:
        return [], f"CSV 를 읽지 못했습니다: {exc}"

    missing = [c for c in REQUIRED_COLUMNS if c not in fields]
    if missing:
        return [], (f"머리글에 {', '.join(missing)} 칸이 없습니다. "
                    f"필수: {', '.join(REQUIRED_COLUMNS)} · "
                    f"선택: {', '.join(OPTIONAL_COLUMNS)}")

    rows: list[dict] = []
    for raw in reader:
        rows.append({(k or "").strip().lower(): (v or "").strip()
                     for k, v in raw.items() if k})
        if len(rows) > MAX_ROWS:
            return [], (f"행이 {MAX_ROWS} 개를 넘습니다. 나눠서 올리십시오 — "
                        f"조용히 자르면 「전부 넣었다」는 보고가 실제와 갈립니다.")
    if not rows:
        return [], "머리글만 있고 행이 없습니다."
    return rows, ""


def _camera_model():
    from stream_monitors.models import StreamMonitor
    return StreamMonitor


def _scoped_cameras(scope: TenantScope, group_id: int | None):
    """**문지기.** 이 요청자가 볼 수 있는 카메라만.

    전역 관리자가 아니면 자기 테넌트로 닫힌다. `group_id` 가 없으면 **빈 것으로
    닫는다** — 「테넌트를 못 정했으니 전부」는 격리의 부재다(W0-12).
    """
    qs = _camera_model().objects.all()
    if is_global_admin(scope.actor) and group_id is None:
        return qs
    if group_id is None:
        return qs.none()
    return qs.filter(group_id=group_id)


def _target_group(scope: TenantScope, group_id: int | None):
    """쓰기의 소유 테넌트. **남의 테넌트에 카메라를 심을 수 없다** (P-8 탐침이 재는 자리).

    ★ 시스템 스코프를 거절한다. 100대를 심는 일에 요청자가 없으면 「누가 넣었나」가
      영영 비고, 잘못 들어온 100대를 되돌릴 근거가 사라진다.
    """
    actor = scope.require_actor()
    own = getattr(require_user_group(actor), "pk", None) \
        if get_user_group(actor) is not None else None
    if own is None and not is_global_admin(actor):
        raise PermissionDenied(
            "소속 테넌트가 없는 요청자는 카메라를 등록할 수 없습니다 (W0-12).")
    if group_id is None or group_id == own:
        return own
    if is_global_admin(actor):
        return group_id
    raise PermissionDenied(
        f"group={group_id} 는 요청자의 테넌트가 아닙니다. 남의 테넌트에 카메라를 "
        f"무더기로 심으면 그 행들은 그쪽의 정상 데이터처럼 보입니다 (D-290).")


def _float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _plan(*, scope: TenantScope, csv_text: str,
          group_id: int | None = None) -> tuple[Plan, int | None]:
    """**판정은 여기 한 곳.** dry-run 과 apply 가 같은 것을 본다."""
    target = _target_group(scope, group_id)
    raw_rows, fatal = parse_csv(csv_text)
    if fatal:
        return Plan(fatal=fatal), target

    existing = {c.name: c for c in _scoped_cameras(scope, target)}
    #: 파일 안에서 이름이 겹치면 **아무것도 쓰지 않는다** — 어느 줄이 이겼는지
    #: 모르는 채로 쓰면 엉뚱한 카메라의 주소가 알림에 나간다(D-338 이 정한 규약).
    seen: dict[str, int] = {}

    plan = Plan()
    for index, raw in enumerate(raw_rows, start=2):      # 2 = 머리글 다음 줄
        name = raw.get("name", "")
        row = Row(line=index, name=name)
        if not name:
            row.reason = "이름이 비었습니다 — 어느 카메라인지 정할 수 없습니다."
            plan.rows.append(row)
            continue
        if name in seen:
            row.reason = f"{seen[name]}행과 이름이 겹칩니다 — 겹치면 쓰지 않습니다."
            plan.rows.append(row)
            continue
        seen[name] = index

        address = raw.get("address", "")
        detail = raw.get("detail", "")
        lat, lng = _float(raw.get("lat", "")), _float(raw.get("lng", ""))
        if not address and (lat is not None or lng is not None):
            #: ★ 어댑터를 **정말 부른다.** 지금은 `disabled` 가 돌아온다(D-329) —
            #:   그 사실을 표에 적는다. 「없는 척」과 「불러 봤더니 없다」는 다른 사실이다.
            result = juso.resolve(lat=lat, lng=lng)
            row.address_lookup = result.status
            if result.status == "resolved" and result.address:
                address = result.address

        camera = existing.get(name)
        if camera is None:
            if not raw.get("ip_source"):
                row.reason = ("새 카메라인데 `ip_source` 가 없습니다 — 주소 없는 "
                              "스트림은 등록해도 한 프레임도 오지 않습니다.")
                plan.rows.append(row)
                continue
            row.action = CREATE
            row.changes = {
                "name": [None, name],
                "code": [None, raw.get("code") or name],
                "ip_source": [None, raw.get("ip_source")],
            }
            if address:
                row.changes["install_address"] = [None, address]
                row.changes["address_source"] = [None, ADDRESS_SOURCE_MANUAL]
            if detail:
                row.changes["install_address_detail"] = [None, detail]
            row.reason = "새로 만듭니다."
            plan.rows.append(row)
            continue

        row.camera_id = camera.pk
        changes: dict[str, list] = {}
        if address and (camera.install_address or "") != address:
            changes["install_address"] = [camera.install_address, address]
            if camera.address_source != ADDRESS_SOURCE_MANUAL:
                changes["address_source"] = [camera.address_source,
                                             ADDRESS_SOURCE_MANUAL]
        if detail and (camera.install_address_detail or "") != detail:
            changes["install_address_detail"] = [camera.install_address_detail, detail]
        if raw.get("ip_source") and camera.ip_source != raw["ip_source"]:
            changes["ip_source"] = [camera.ip_source, raw["ip_source"]]
        if changes:
            row.action, row.changes = UPDATE, changes
            row.reason = f"{len(changes)}개 칸이 바뀝니다."
        else:
            row.action = UNCHANGED
            row.reason = "바뀌는 칸이 없습니다."
        plan.rows.append(row)

    return plan, target


def plan_camera_import(*, scope: TenantScope, csv_text: str,
                       group_id: int | None = None) -> dict:
    """**dry-run.** 아무것도 쓰지 않는다 — 표만 낸다 (D-209).

    이 함수가 `apply_camera_import` 보다 **먼저 있고**, 화면은 이것 없이 적용 버튼을
    그리지 않는다. 순서가 규약이다.
    """
    plan, _ = _plan(scope=scope, csv_text=csv_text, group_id=group_id)
    return plan.as_dict()


@transaction.atomic
def apply_camera_import(*, scope: TenantScope, csv_text: str,
                        group_id: int | None = None) -> dict:
    """표를 집행한다. **P-8 탐침이 재는 쓰기 면.**

    ★ 재계산하지 않는다 — `_plan()` 이 낸 그 표를 그대로 쓴다. 두 벌이면 표에 없던
      일이 일어나고, 그러면 dry-run 은 보여 주기일 뿐 약속이 아니게 된다.
    ★ 치명 사유가 있으면 **한 행도 안 쓴다.** 부분 성공을 만들지 않는다 —
      100행 중 37행이 들어간 상태는 되돌릴 지점이 없다.
    """
    plan, target = _plan(scope=scope, csv_text=csv_text, group_id=group_id)
    if plan.fatal:
        return {**plan.as_dict(), "dry_run": False, "applied": 0}

    Camera = _camera_model()
    created = updated = 0
    for row in plan.writable:
        if row.action == CREATE:
            values = {k: v[1] for k, v in row.changes.items()}
            camera = Camera(name=values["name"], code=values.get("code") or row.name,
                            ip_source=values.get("ip_source") or "",
                            install_address=values.get("install_address"),
                            install_address_detail=values.get("install_address_detail"),
                            address_source=values.get("address_source",
                                                      ADDRESS_SOURCE_UNSET))
            #: ★ 소유 테넌트를 **명시로** 박는다. 기본값에 맡기면 요청자의 컨텍스트가
            #:   없는 경로에서 조용히 다른 테넌트에 들어간다.
            if target is not None:
                camera.group_id = target
            camera.save()
            row.camera_id = camera.pk
            created += 1
        else:
            camera = _scoped_cameras(scope, target).filter(pk=row.camera_id).first()
            if camera is None:
                #: 계획과 집행 사이에 사라졌다. **조용히 넘기지 않는다.**
                row.action, row.reason = ERROR, "계획 후 카메라가 사라졌습니다."
                continue
            fields: list[str] = []
            for name, (_before, after) in row.changes.items():
                setattr(camera, name, after)
                fields.append(name)
            camera.save(update_fields=fields)
            updated += 1

    log.info("[UX-18] 벌크 등록 group=%s 생성=%d 수정=%d", target, created, updated)
    return {**plan.as_dict(), "dry_run": False,
            "applied": created + updated, "created": created, "updated": updated}


# ═══════════════════════════════════════════════════════════════════════════
# 「주소 없는 카메라 N대」 배지
# ═══════════════════════════════════════════════════════════════════════════
def address_gap(*, scope: TenantScope, group_id: int | None = None) -> dict:
    """**분모와 함께** 낸다 (D-301). 「39대」만 보면 그것이 40 중 39인지 400 중 39인지 모른다.

    ★ `unset`(안 적음)과 `manual`(적음)만 세지 않는다 — **빈 문자열로 적힌 것**도
      따로 센다. 「적었는데 빈 값」은 「안 적음」과 다른 사실이고(D-290), 이 둘을
      합치면 배지가 줄어드는데 알림 본문은 그대로 좌표만 나간다.
    """
    qs = _scoped_cameras(scope, _target_group(scope, group_id))
    total = qs.count()
    filled = qs.exclude(install_address__isnull=True).exclude(
        install_address="").count()
    blank_but_marked = qs.filter(address_source=ADDRESS_SOURCE_MANUAL).filter(
        install_address="").count()
    return {
        "total": total,
        "with_address": filled,
        "without_address": total - filled,
        "marked_but_blank": blank_but_marked,
        #: 분모가 0 이면 비율은 **null 이다 — 0 이 아니다.** 카메라가 한 대도 없는 것과
        #: 전부 주소가 있는 것을 같은 숫자로 내면 배지가 거짓말을 한다.
        "coverage": (filled / total) if total else None,
        "measurable": bool(total),
    }
