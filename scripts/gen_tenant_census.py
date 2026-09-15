#!/usr/bin/env python
"""격리 대상 인구조사 표를 생성한다 — `backend/tests/tenant_census.py` (D-271 ② · D-272).

왜 생성하나
-----------
`test_registry_covers_all_isolatable_models` 의 모수가 틀렸다 (D-271 ② 인정).
옛 술어(`groups` M2M 만)로 세면 모수가 **2종**이고, 그 위의 초록은 아무것도 말하지 않는다.

실측 모수는 **142종**(저장소 관할 · `groups` M2M ∪ `group` FK)이다.
그 142종을 **하나도 빠짐없이** 분류해 두고, 시험이 그 표와 실제 코드를 대조한다.
표에 없는 모델이 코드에 나타나면 실패한다 — **모르는 것을 만나면 멈춘다**(D-264).

무엇을 붙이나
-------------
  · `priority`     covered / P0 / P1 / P2 / GAP   (근거: leak_targets.json · D-260 · D-263)
  · `reach`        D-272 의 3값 — direct_pk / via_parent / no_route
  · `rows`         실측 행수 (없으면 null — P-LOCAL-4 로 셀 수 없는 것)
  · `reason`       왜 그 분류인가. **사유 없는 등재는 시험이 거부한다.**

도달 가능성(reach)을 어떻게 정하나 — `route_model_map.json`(AST 실경로 추적, D-263)에서:
  · `single_record_routes > 0`                  → **direct_pk**
  · 아니고 목록·본문지목쓰기 라우트가 있다      → **via_parent** (부모를 통해 노출된다)
  · 어느 것도 없다                              → **no_route** (면제가 아니라 등재 대상)

    python scripts/gen_tenant_census.py            # 생성
    python scripts/gen_tenant_census.py --check    # 생성물이 최신인지만 확인 (게이트용)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import models as dj  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FRAMEWORK_APPS = {"user", "core"}


def _root() -> Path:
    for cand in (Path("/docs"), Path(__file__).resolve().parent.parent / "docs"):
        if cand.is_dir():
            return cand.parent if cand.name == "docs" else cand
    return Path(__file__).resolve().parent.parent


def _ev(name: str) -> Path:
    for cand in (Path("/docs/agent/evidence/W0-14") / name,
                 Path(__file__).resolve().parent.parent / "docs" / "agent"
                 / "evidence" / "W0-14" / name):
        if cand.is_file():
            return cand
    raise SystemExit(f"[CENSUS] 근거 파일을 못 찾았다: {name} — 추측으로 만들지 않는다")


def owns_group(model) -> str | None:
    """소유 필드의 모양. **이름이 아니라 필드로** 판정한다 (D-263).

    `auth.Permission` 에는 `auth.Group.permissions` 의 역방향 접근자가 `group` 이라는
    이름으로 잡힌다 — 첫 판이 그것을 800행짜리 격리 대상으로 보고했다.
    """
    concrete = [f for f in model._meta.get_fields() if isinstance(f, dj.Field)]
    m2m = any(f.name == "groups" and getattr(f, "many_to_many", False) for f in concrete)
    fk = any(f.name == "group" and getattr(f, "many_to_one", False) for f in concrete)
    if m2m and fk:
        return "both"
    if m2m:
        return "m2m"
    if fk:
        return "fk"
    return None


def _norm(s: str) -> str:
    """비교용 정규화 — 소문자 · 구분자 제거 · 끝의 `id`/복수 `s` 제거."""
    s = s.strip("{}").lower().replace("_", "").replace("-", "")
    if s.endswith("id"):
        s = s[:-2]
    if s.endswith("s"):
        s = s[:-1]
    return s


def _is_own_pk(path: str, model_name: str) -> bool:
    """이 경로의 pk 자리가 **이 모델의 것**인가.

    ★ 왜 여기서는 이름 비교를 쓰나 (D-263 은 이름 매칭을 금지했다)
      D-263 이 금지한 것은 **면제를 주는 방향**의 이름 매칭이다
      ("이름이 안 맞으니 이 라우트는 이 모델과 무관하다" → 조용히 검사 밖).
      여기서는 반대다. 못 맞추면 `via_parent` 로 떨어지고, via_parent 는
      **부모 경로 스코프 + 자식 필터를 둘 다** 시험하라는 뜻이므로 **더 엄격하다.**
      즉 이 비교가 틀리는 방향은 항상 "더 많이 시험한다" 쪽이다.

    실측이 이 구분을 요구했다 — `route_model_map.json` 의 `single_record_routes` 는
    "pk 자리가 있는 라우트가 이 모델을 만진다"를 센다. 그래서
    `MissionWaypoint` 의 유일한 상세 경로가 `/survey-missions/{survey_mission_id}`(부모의 pk)인데도
    direct 로 잡혔다 — D-272 가 via_parent 의 **예로 든 바로 그 모델**이다.
    """
    target = _norm(model_name)
    parts = [seg for seg in path.split("/") if seg]
    holders = [i for i, seg in enumerate(parts) if seg.startswith("{")]
    if not holders:
        return False

    for i in holders:
        raw_name = parts[i].strip("{}").lower()
        # ① 자리표시자 이름이 그대로 말해 준다 — {video_analysis_id} ↔ VideoAnalysis
        if _norm(parts[i]) == target:
            return True
        # ② 자리표시자 **바로 앞** 조각 — /order-status-mappings/{mapping_id}
        if i and _norm(parts[i - 1]) == target:
            return True
        # ③ 한 칸 더 앞 — 다만 자리표시자가 **일반형일 때만**.
        #    /flight-log/flight-log/detail/{id} 는 direct 이지만
        #    /dashboard/dashboard/check-health/{drone_id} 는 아니다 —
        #    후자의 pk 는 **다른 것(drone)** 을 명시하고 있다. 실측에서 그 하나 때문에
        #    Dashboard 가 direct_pk 로 잘못 잡혔다. 일반형 {id}·{pk} 에만 뒤로 더 본다.
        if raw_name in ("id", "pk") and i >= 2 and _norm(parts[i - 2]) == target:
            return True
    return False


def reach_of(entry: dict | None, model_name: str = "",
             all_paths: list[str] | None = None) -> tuple[str, str]:
    """D-272 의 3값. 근거는 두 실측본을 **함께** 본다.

      · `route_model_map.json` — 어떤 라우트가 이 모델을 **만지는가** (AST 추적)
      · `openapi_routes.json`  — 어떤 라우트가 **존재하는가** (531 경로 · 652 오퍼레이션)

    왜 둘인가 — AST 추적본에는 커버리지 구멍이 있다. 실측:
    `/api/report-template/{id}` 는 존재하고 격리 시험이 실제로 치는데도
    추적본은 `report_template.ReportTemplate` 의 상세 경로로 그것을 싣지 않았다
    (source_routes 465 / registered 652 — 187 경로가 애초에 소스되지 않았다).
    추적본만 믿으면 **자기 pk 경로가 있는 모델을 via_parent 로 적게 되고**,
    그러면 등재된 사실과 인구조사가 서로 다른 말을 한다.
    """
    # ① 존재하는 라우트 중 **자기 pk** 를 지목하는 것이 있으면 direct_pk 다.
    #    (추적본이 그 라우트를 못 실었어도 경로는 실재한다)
    for path in all_paths or []:
        if "{" in path and _is_own_pk(path, model_name):
            return "direct_pk", (f"자기 pk 로 지목하는 경로가 실재한다 ({path}) — "
                                 f"근거: openapi_routes.json 전수")
    # ② pk 가 없는 경로라도 **이름이 이 모델을 가리키면** 닿는다 — no_route 가 아니다.
    #   실측: `/api/comment` · `/api/rating` · `/api/tag` 가 실재하는데 AST 추적본이
    #   그 라우트를 소스하지 않아(465/652) 세 모델이 **no_route 로 적혀 있었다.**
    #   `verify_tenant_scope` 의 no_route 게이트가 그 셋을 잡았다 — 게이트가 생성기의
    #   사각지대를 잡은 것이고, "닿을 수 없다"는 가장 조용한 면제다.
    named = [p for p in (all_paths or [])
             if any(_norm(s) == _norm(model_name) for s in p.split("/") if s)]
    if named and entry is None:
        return "via_parent", (f"자기 pk 경로는 없으나 이름이 이 모델을 가리키는 경로가 "
                              f"{len(named)}개 실재한다 (예: {named[0]}) — "
                              f"닿을 수 없는 것이 아니다")

    if entry is None:
        return "no_route", "실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"
    rts = entry.get("routes", {}) or {}
    # ★ pk 자리가 있는 라우트는 `detail` 에만 있지 않다. 실측: SurveillanceProfileChecklistItem 의
    #   유일한 pk 경로가 `write` 버킷(`/{profile_id}/check-complete`)에 들어 있어,
    #   detail 만 보던 첫 판이 그 모델을 **no_route** 로 떨어뜨렸다 —
    #   P0(라우트가 닿는다)인데 no_route 라는 모순이 그렇게 생겼다. 전 버킷을 본다.
    pk_routes = (rts.get("detail") or []) + (rts.get("write") or [])
    own = [r for r in pk_routes if _is_own_pk(r.get("path", ""), model_name)]
    other = [r for r in pk_routes if r not in own]
    lists = entry.get("list_routes", 0)
    nopk = len(rts.get("write_nopk") or [])
    if own:
        return "direct_pk", (f"자기 pk 로 지목하는 경로 {len(own)}개 "
                             f"(예: {own[0].get('path')}) — 그 경로에 스코프를 부착하고 시험한다")
    if other or lists or nopk:
        via = other[0].get("path") if other else "(목록·본문지목쓰기)"
        return "via_parent", (f"자기 pk 경로는 없다. 부모 pk 경로 {len(other)}개 · 목록 {lists} · "
                              f"본문지목쓰기 {nopk} 로 닿는다 (예: {via}) — "
                              f"부모 경로 스코프와 자식 필터를 **둘 다** 시험한다")
    return "no_route", "실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"


HEADER = '''# -*- coding: utf-8 -*-
"""격리 대상 인구조사 — **모수를 눈에 보이게 둔다** (D-271 ② · D-272).

⚠ 이 파일은 `scripts/gen_tenant_census.py` 가 생성한다. **손으로 고치지 말 것.**
  고쳐야 할 것은 분류의 근거이지 표가 아니다.

왜 있나
-------
`test_registry_covers_all_isolatable_models` 는 `groups` M2M 만 세었다.
그 술어로 센 모수는 **2종**이다 (`dashboard.Dashboard` · `dashboard.DashboardPanel`).
모수 2 위에서 나온 "누락 1건"이라는 초록은 아무것도 말하지 않는다 —
D-260 이 지적하고 D-271 이 인정한 **작은 모수의 착시**가 이것이다.

실측 모수는 **{total}종**이다 (저장소 관할 · `groups` M2M ∪ `group` FK).
그 전부를 여기 분류해 두고, 시험이 이 표와 실제 코드를 대조한다.
**표에 없는 모델이 코드에 나타나면 시험이 실패한다** — 모르는 것을 만나면 멈춘다(D-264).

인구조사가 못 보던 것 — 행 0 은 안전이 아니다
---------------------------------------------
`leak_targets.json`(131종)은 백필 dry-run 의 **덤프 집계**에서 나왔고, 덤프 집계는
**행이 있는 표만** 센다. 그래서 {gap}종이 목록 밖에 있었다 (행 0 이 {gap_zero}종).
행이 0인 것은 "격리가 필요 없다"가 아니라 **"아직 안 썼다"**이다 —
내일 첫 행이 들어오는 순간 그 모델은 무방비로 시작한다.
행이 **있는데도** 빠져 있던 것도 {gap_nonzero}종 있었다. 그쪽은 0행 아티팩트가 아니라 집계 누락이다.

값의 뜻
-------
  priority  covered  이미 격리 시험 레지스트리에 있다
            P0       EXIT 필수 (D-262 ②)
            P1       계획 등재 (D-262 ③)
            P2       미검토 — 사유 첨부 (D-262 ④). **면제가 아니다**
            GAP      인구조사가 못 보던 것 (이번에 드러남)
  reach     direct_pk / via_parent / no_route  — D-272
  owns      m2m / fk / both — 소유 필드의 모양 (D-271 술어)
"""
from __future__ import annotations

#: 생성 시각의 근거. 수가 바뀌면 이 파일을 다시 만들고, **차이를 조사한다.**
SOURCE = {{
    "census": "docs/agent/evidence/W0-14/leak_targets.json",
    "routes": "docs/agent/evidence/W0-14/route_model_map.json",
    "generator": "scripts/gen_tenant_census.py",
    "measured_at": "{measured}",
}}

#: label -> (priority, reach, owns, rows, reason)
CENSUS: dict[str, tuple[str, str, str, int | None, str]] = {{
'''

FOOTER = '''}


def by_priority(name: str) -> list[str]:
    return sorted(k for k, v in CENSUS.items() if v[0] == name)


def by_reach(name: str) -> list[str]:
    return sorted(k for k, v in CENSUS.items() if v[1] == name)


def fk_models() -> list[str]:
    """`group` FK 로 테넌트를 가리는 모델 — D-271 의 술어 확장분."""
    return sorted(k for k, v in CENSUS.items() if v[2] in ("fk", "both"))
'''


#: ★ **인구조사 이후에 태어난 모델** — label → 사유 (D-264 · D-271 ②).
#:
#: 왜 목록이 필요한가. 인구조사(`leak_targets.json`)에 없는 모델은 아래에서 자동으로
#: "행이 0이라 안 보였다" 나 "셀 수도 없다(P-LOCAL-4)" 로 분류된다. 그 둘 다
#: **새로 만든 모델에는 거짓이다** — 인구조사 시점에 그 모델은 존재하지 않았고,
#: 행이 0인 것은 아티팩트가 아니라 당연한 사실이다.
#:
#: 거짓 사유를 자동 생성하면 그것이 근거처럼 읽힌다. 이 저장소가 반복해 만난
#: 사후 정당화의 모양이고(D-249 부착률 착시), 그래서 **새로 만든 것은 이름을 적는다.**
#: 적는 일이 곧 "이 모델의 격리를 생각했다"는 선언이다.
NEW_SINCE_CENSUS: dict[str, str] = {
    "stream_monitors.Zone":
        "2026-09-01 D-299 로 신설(마이그 0019). 인구조사(2026-08-14 덤프)에 **없었던 것이 "
        "아니라 그때 존재하지 않았다** — 행 0 은 아티팩트가 아니라 신설 직후의 사실이다. "
        "소유는 dj-core BaseModel 의 group FK 로 첫 행부터 붙고, 판정 서비스"
        "(stream_monitors.services.zones)는 스코프로 좁힌 뒤에만 구역을 돌려준다. "
        "격리 단언은 backend/tests/test_zone_judgment.py 의 "
        "test_isolation_another_tenant_cannot_see_our_zones 가 양방향으로 잰다. "
        "구역을 **만드는** 공개 면은 아직 없으므로 쓰기 IDOR 표면도 아직 없다 — "
        "생기면 WRITE_PROBES 에 함께 등재한다(D-290)",
    "stream_monitors.EventClip":
        "2026-09-02 D-306 으로 신설(마이그 0021). 인구조사(2026-08-14 덤프)에 없었던 것이 "
        "아니라 그때 존재하지 않았다. 소유는 **이벤트에서 물려받는다**"
        "(stream_monitors.services.clips._own) — 주인 없는 행은 §0.4 의 "
        "created_by__isnull OR 절을 타고 모두에게 보인다(W0-13 이 되돌린 상태). "
        "격리 단언은 backend/tests/test_clip_playback.py 의 "
        "test_the_clip_inherits_the_tenant_from_the_event 와 규약 ①"
        "(test_rule1_another_tenant_gets_404)이 함께 잰다. "
        "쓰기 면은 이벤트 생성 경로 안 한 곳뿐이고 HTTP 로 만드는 경로는 없다 — "
        "생기면 WRITE_PROBES 에 함께 등재한다(D-290)",
    # ── 2026-09-15 턴 Q · WO-01 §5 「데이터」 — v1.1 표 여섯(마이그 0029_v11_tables · D-463) ──
    **{label: (
        "2026-09-15 WO-01 §5 「데이터」로 신설(마이그 0029_v11_tables · 턴 Q 차선 F-DB · D-463). "
        "인구조사(2026-08-14 덤프)에 없었던 것이 아니라 그때 존재하지 않았다 — 행 0 은 신설 "
        "직후의 사실이다. 소유는 dj-core BaseModel 의 group FK(stream_monitors.models.TenantModel "
        "추상)로 첫 행부터 붙는다. 격리 단언은 backend/tests/test_v11_tables.py 의 "
        "V11TenantIsolationTest 가 잰다(B 에 안 보임 · A 양성 대조 · _base_manager 실재). "
        + extra) for label, extra in (
        ("stream_monitors.DsmHandover",
         "쓰는 라우트는 아직 없다 — U1 차선 인계 자동 초안(UX-34 · 파 1 턴 2)이 연다"),
        ("stream_monitors.DsmFieldPhoto",
         "★ 쓰는 라우트가 이번 턴 섰다 — POST /api/dsm/events/{id}/field-photo(U3). 사건을 "
         "거쳐 닿는다(services.event_detail 의 get_event 문지기가 남의 사건을 404). 격리는 "
         "backend/tests/test_u3_field_photo_route.py 가 함께 잰다. 커널 쓰기 함수가 아니라 "
         "App 층(apps/dsm/field.py) 쓰기라 WRITE_PROBES(커널 쓰기 대장)의 대상이 아니다"),
        ("stream_monitors.DsmNotifyPrefs",
         "쓰는 라우트는 아직 없다 — U3 차선 me/notify-prefs(UX-43-M4 · UX-48)가 연다"),
        ("stream_monitors.DsmOnboardingProgress",
         "쓰는 라우트는 아직 없다 — F 차선 온보딩 진행률(UX-46 · 파 1 턴 2)이 연다"),
        ("stream_monitors.DsmReportRun",
         "쓰는 자리는 아직 없다 — U24 차선 월간 자동본 배치(UX-40 · 파 3)가 연다"),
        ("stream_monitors.DsmUpperReportFlag",
         "쓰는 라우트는 아직 없다 — U24 차선 상급 보고 체크(UX-47 · 파 2)가 연다"),
    )},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--measured", default="2026-08-28")
    args = ap.parse_args()

    census_doc = json.loads(_ev("leak_targets.json").read_text(encoding="utf-8"))
    prio = {t["label"]: t for t in census_doc["targets"]}
    route_doc = json.loads(_ev("route_model_map.json").read_text(encoding="utf-8"))
    routes = {m["label"]: m for m in route_doc["models"]}
    api_doc = json.loads(_ev("openapi_routes.json").read_text(encoding="utf-8"))
    all_paths = sorted(api_doc["routes"])          # 531 경로 전수

    rows: dict[str, tuple] = {}
    gap_zero = gap_nonzero = 0
    for model in apps.get_models():
        label = f"{model._meta.app_label}.{model.__name__}"
        if model._meta.app_label in FRAMEWORK_APPS:
            continue                      # dj-core §0.4 — 면제가 아니라 관할 밖
        owns = owns_group(model)
        if owns is None:
            continue
        reach, why = reach_of(routes.get(label), model.__name__, all_paths)
        entry = prio.get(label)
        if entry is None:
            priority = "GAP"
            try:
                n = model._base_manager.count()
            except Exception:
                n = None
            if label in NEW_SINCE_CENSUS:
                # ★ 신설 모델은 자동 사유가 거짓이 된다 — 이름을 적은 사유를 쓴다.
                if n == 0:
                    gap_zero += 1
                elif n:
                    gap_nonzero += 1
                reason = NEW_SINCE_CENSUS[label]
            elif n == 0:
                gap_zero += 1
                reason = ("인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. "
                          "**아직 안 쓴 것이지 안전한 것이 아니다**")
            elif n is None:
                reason = ("인구조사에 없었고 셀 수도 없다 — 저장소 모델 ↔ 운영 스키마 "
                          "불일치 (P-LOCAL-4)")
            else:
                gap_nonzero += 1
                reason = (f"인구조사에 없었는데 **{n}행이 있다** — 0행 아티팩트가 아니라 "
                          f"집계 누락이다")
        else:
            p = entry.get("priority")
            priority = {"UNREVIEWED": "P2", "covered": "covered"}.get(p, p)
            n = entry.get("rows")
            reason = (entry.get("reason") or "").strip() or "근거 없음 — 조사 필요"
        rows[label] = (priority, reach, owns, n, f"{reason} / 도달: {why}")

    out = [HEADER.format(total=len(rows), gap=sum(1 for v in rows.values() if v[0] == "GAP"),
                         gap_zero=gap_zero, gap_nonzero=gap_nonzero, measured=args.measured)]
    for label in sorted(rows):
        p, r, o, n, why = rows[label]
        why = why.replace('"', "'")
        out.append(f'    "{label}":\n        ("{p}", "{r}", "{o}", {n!r},\n'
                   f'         "{why}"),\n')
    out.append(FOOTER)
    text = "".join(out)

    target = Path(__file__).resolve().parent.parent / "backend" / "tests" / "tenant_census.py"
    if not target.parent.is_dir():
        target = Path("/app/tests/tenant_census.py")

    if args.check:
        same = target.is_file() and target.read_text(encoding="utf-8") == text
        print(f"[CENSUS] {'최신' if same else '★ 낡았다 — 다시 생성하라'} ({target})")
        return 0 if same else 1

    # D-270 ① 원자 교체 — 원본을 truncate 하지 않는다
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)

    import collections
    print(f"[CENSUS] {target} 생성 — 모수 {len(rows)}종")
    print("         우선순위:", dict(collections.Counter(v[0] for v in rows.values())))
    print("         도달가능:", dict(collections.Counter(v[1] for v in rows.values())))
    print("         소유필드:", dict(collections.Counter(v[2] for v in rows.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
