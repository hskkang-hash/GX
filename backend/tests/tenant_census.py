# -*- coding: utf-8 -*-
"""격리 대상 인구조사 — **모수를 눈에 보이게 둔다** (D-271 ② · D-272).

⚠ 이 파일은 `scripts/gen_tenant_census.py` 가 생성한다. **손으로 고치지 말 것.**
  고쳐야 할 것은 분류의 근거이지 표가 아니다.

왜 있나
-------
`test_registry_covers_all_isolatable_models` 는 `groups` M2M 만 세었다.
그 술어로 센 모수는 **2종**이다 (`dashboard.Dashboard` · `dashboard.DashboardPanel`).
모수 2 위에서 나온 "누락 1건"이라는 초록은 아무것도 말하지 않는다 —
D-260 이 지적하고 D-271 이 인정한 **작은 모수의 착시**가 이것이다.

실측 모수는 **146종**이다 (저장소 관할 · `groups` M2M ∪ `group` FK).
그 전부를 여기 분류해 두고, 시험이 이 표와 실제 코드를 대조한다.
**표에 없는 모델이 코드에 나타나면 시험이 실패한다** — 모르는 것을 만나면 멈춘다(D-264).

인구조사가 못 보던 것 — 행 0 은 안전이 아니다
---------------------------------------------
`leak_targets.json`(131종)은 백필 dry-run 의 **덤프 집계**에서 나왔고, 덤프 집계는
**행이 있는 표만** 센다. 그래서 33종이 목록 밖에 있었다 (행 0 이 29종).
행이 0인 것은 "격리가 필요 없다"가 아니라 **"아직 안 썼다"**이다 —
내일 첫 행이 들어오는 순간 그 모델은 무방비로 시작한다.
행이 **있는데도** 빠져 있던 것도 4종 있었다. 그쪽은 0행 아티팩트가 아니라 집계 누락이다.

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
SOURCE = {
    "census": "docs/agent/evidence/W0-14/leak_targets.json",
    "routes": "docs/agent/evidence/W0-14/route_model_map.json",
    "generator": "scripts/gen_tenant_census.py",
    "measured_at": "2026-08-28",
}

#: label -> (priority, reach, owns, rows, reason)
CENSUS: dict[str, tuple[str, str, str, int | None, str]] = {
    "advanced_table.GridSetting":
        ("P2", "no_route", "fk", 928,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "advanced_table.GridSettingCategory":
        ("P2", "no_route", "fk", 2,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "advanced_table.GridSettingUser":
        ("P2", "no_route", "fk", 3230,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "advanced_table.SearchConditionsUser":
        ("P2", "no_route", "fk", 2,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "advanced_table.UserGridManagement":
        ("P2", "no_route", "fk", 77,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "article.Article":
        ("GAP", "direct_pk", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/article/related/{article_id}) — 근거: openapi_routes.json 전수"),
    "checklist_setting.ChecklistSetting":
        ("covered", "direct_pk", "fk", 63,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/checklist-setting/categories/{id}) — 근거: openapi_routes.json 전수"),
    "checklist_setting.ChecklistSettingCategory":
        ("P1", "via_parent", "fk", 3,
         "라우트가 닿는다(단건 2 · 목록 1 · 본문지목쓰기 1) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 2개 · 목록 1 · 본문지목쓰기 1 로 닿는다 (예: /api/advanced-table/grid-management/{grid_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "configuration.AdminConfig":
        ("P2", "no_route", "fk", 12,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "dashboard.Dashboard":
        ("covered", "via_parent", "both", 21,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 2 · 본문지목쓰기 2 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "dashboard.DashboardPanel":
        ("P1", "via_parent", "both", 26,
         "라우트가 닿는다(단건 0 · 목록 2 · 본문지목쓰기 2) — 행 26건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 2 · 본문지목쓰기 2 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "dashboard.WeatherSetting":
        ("P1", "via_parent", "fk", 20,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 1) — 행 20건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 1 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.Address":
        ("P2", "no_route", "fk", 1353,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "delivery.DeliveryCancellation":
        ("P1", "via_parent", "fk", 3,
         "라우트가 닿는다(단건 1 · 목록 9 · 본문지목쓰기 2) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 9 · 본문지목쓰기 2 로 닿는다 (예: /api/orders/order/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryCancellationType":
        ("P1", "via_parent", "fk", 2,
         "라우트가 닿는다(단건 0 · 목록 0 · 본문지목쓰기 2) — 행 2건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 0 · 본문지목쓰기 2 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryOperation":
        ("P0", "via_parent", "fk", 304,
         "단건 경로 21건이 이 모델을 만지고, 행 304건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 21개 · 목록 22 · 본문지목쓰기 22 로 닿는다 (예: /api/third-api/delivery/confirmation/{operation_id}/photo/) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryOperationApproval":
        ("P1", "via_parent", "fk", 256,
         "라우트가 닿는다(단건 0 · 목록 0 · 본문지목쓰기 1) — 행 256건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 0 · 본문지목쓰기 1 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryOperationApprovalChecklist":
        ("P1", "via_parent", "fk", 3013,
         "라우트가 닿는다(단건 0 · 목록 0 · 본문지목쓰기 1) — 행 3013건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 0 · 본문지목쓰기 1 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryOperationHistory":
        ("P2", "no_route", "fk", 856,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "delivery.DeliveryOperationItem":
        ("P0", "via_parent", "fk", 285,
         "단건 경로 13건이 이 모델을 만지고, 행 285건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 13개 · 목록 6 · 본문지목쓰기 10 로 닿는다 (예: /api/operational-data/operational-data/{order_item_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryReturn":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없다. 부모 pk 경로 3개 · 목록 1 · 본문지목쓰기 3 로 닿는다 (예: /api/orders/order/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.DeliveryStatus":
        ("P1", "via_parent", "fk", 14,
         "라우트가 닿는다(단건 17 · 목록 0 · 본문지목쓰기 16) — 행 14건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 17개 · 목록 0 · 본문지목쓰기 16 로 닿는다 (예: /api/third-api/delivery/confirmation/{operation_id}/photo/) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "delivery.TerminalSequence":
        ("P1", "via_parent", "fk", 875,
         "라우트가 닿는다(단건 0 · 목록 0 · 본문지목쓰기 3) — 행 875건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 0 · 본문지목쓰기 3 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "devices.BatteryType":
        ("P1", "direct_pk", "fk", 6,
         "라우트가 닿는다(단건 3 · 목록 1 · 본문지목쓰기 1) — 행 6건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/battery-types/{id}) — 근거: openapi_routes.json 전수"),
    "devices.CameraType":
        ("P1", "via_parent", "fk", 12,
         "라우트가 닿는다(단건 11 · 목록 1 · 본문지목쓰기 3) — 행 12건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 11개 · 목록 1 · 본문지목쓰기 3 로 닿는다 (예: /api/devices/cameras/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "devices.CargoCompartments":
        ("P2", "no_route", "fk", 44,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.Device":
        ("covered", "direct_pk", "fk", 31,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/battery-types/{id}) — 근거: openapi_routes.json 전수"),
    "devices.DeviceCamera":
        ("P2", "no_route", "fk", 8,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.DeviceGNSS":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "devices.DeviceProtocol":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "devices.DeviceStatus":
        ("P1", "via_parent", "fk", 5,
         "라우트가 닿는다(단건 10 · 목록 2 · 본문지목쓰기 7) — 행 5건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 10개 · 목록 2 · 본문지목쓰기 7 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}/test-upload-profile-to-flightbird) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "devices.DeviceType":
        ("P2", "no_route", "fk", 4,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.DimensionsAndWeight":
        ("P1", "via_parent", "fk", 44,
         "라우트가 닿는다(단건 4 · 목록 2 · 본문지목쓰기 3) — 행 44건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 4개 · 목록 2 · 본문지목쓰기 3 로 닿는다 (예: /api/devices/devices-management/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "devices.EnvironmentalSpecification":
        ("P2", "no_route", "fk", 44,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.FlightPerformance":
        ("P2", "no_route", "fk", 41,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.FrameClass":
        ("P2", "no_route", "fk", 14,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.FrameType":
        ("P2", "no_route", "fk", 24,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.GNSSSystem":
        ("P1", "direct_pk", "fk", 6,
         "라우트가 닿는다(단건 3 · 목록 1 · 본문지목쓰기 1) — 행 6건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/gnss-systems/{id}) — 근거: openapi_routes.json 전수"),
    "devices.IMU":
        ("GAP", "direct_pk", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/imus/{id}) — 근거: openapi_routes.json 전수"),
    "devices.ImageStabilization":
        ("P1", "direct_pk", "fk", 6,
         "라우트가 닿는다(단건 3 · 목록 1 · 본문지목쓰기 1) — 행 6건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/image-stabilizations/{id}) — 근거: openapi_routes.json 전수"),
    "devices.InsuranceInformation":
        ("P2", "no_route", "fk", 40,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.Library":
        ("P1", "via_parent", "fk", 13,
         "라우트가 닿는다(단건 5 · 목록 1 · 본문지목쓰기 1) — 행 13건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 5개 · 목록 1 · 본문지목쓰기 1 로 닿는다 (예: /api/devices/libraries-management/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "devices.ManufacturerInformation":
        ("P2", "no_route", "fk", 40,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.MotorType":
        ("P1", "direct_pk", "fk", 6,
         "라우트가 닿는다(단건 3 · 목록 1 · 본문지목쓰기 1) — 행 6건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/motor-types/{id}) — 근거: openapi_routes.json 전수"),
    "devices.NavigationControl":
        ("P2", "no_route", "fk", 44,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.PackageType":
        ("P2", "no_route", "fk", 7,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.PackagingOption":
        ("P2", "no_route", "fk", 359,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.PackagingOptionSpecification":
        ("P2", "no_route", "fk", 693,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.PackagingSpecification":
        ("P1", "direct_pk", "fk", 15,
         "라우트가 닿는다(단건 7 · 목록 2 · 본문지목쓰기 1) — 행 15건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/packaging-specifications/{ids}/activate) — 근거: openapi_routes.json 전수"),
    "devices.PackagingSpecificationDevice":
        ("P2", "no_route", "fk", 45,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.PropulsionSystem":
        ("P1", "via_parent", "fk", 43,
         "라우트가 닿는다(단건 0 · 목록 0 · 본문지목쓰기 1) — 행 43건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 0 · 본문지목쓰기 1 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "devices.Protocol":
        ("P1", "direct_pk", "fk", 17,
         "라우트가 닿는다(단건 7 · 목록 1 · 본문지목쓰기 3) — 행 17건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/devices/protocols/{id}) — 근거: openapi_routes.json 전수"),
    "devices.RadioCommunication":
        ("P2", "no_route", "fk", 40,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.SafetyFeature":
        ("P2", "no_route", "fk", 44,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.SensorSuite":
        ("P2", "no_route", "fk", 44,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.Telemetry":
        ("P2", "no_route", "fk", 44,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "devices.Unit":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "discuss.Comment":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없으나 이름이 이 모델을 가리키는 경로가 1개 실재한다 (예: /api/comment) — 닿을 수 없는 것이 아니다"),
    "discuss.Following":
        ("GAP", "direct_pk", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/topic/following/{topic_id}) — 근거: openapi_routes.json 전수"),
    "discuss.Rating":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없으나 이름이 이 모델을 가리키는 경로가 2개 실재한다 (예: /api/rating) — 닿을 수 없는 것이 아니다"),
    "discuss.Topic":
        ("GAP", "direct_pk", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/topic/following/{topic_id}) — 근거: openapi_routes.json 전수"),
    "file_management.UserMediaFile":
        ("P2", "no_route", "fk", 1077,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "file_management.UserMediaFileItem":
        ("P2", "no_route", "fk", 8,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "flight_log.DroneAnomalyPrediction":
        ("P1", "via_parent", "fk", 2,
         "라우트가 닿는다(단건 2 · 목록 0 · 본문지목쓰기 0) — 행 2건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 2개 · 목록 0 · 본문지목쓰기 0 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}/completed-profile) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "flight_log.FlightLog":
        ("P0", "direct_pk", "fk", 308,
         "단건 경로 5건이 이 모델을 만지고, 행 308건이 실재한다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/flight-log/flight-log/detail/{id}) — 근거: openapi_routes.json 전수"),
    "guardian.GroupObjectPermission":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "handover.HandoverContent":
        ("P1", "via_parent", "fk", 11,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 4) — 행 11건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 4 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "handover.HandoverDocument":
        ("covered", "via_parent", "fk", 11,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 4 · 본문지목쓰기 4 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "handover.HandoverNotice":
        ("P1", "via_parent", "fk", 11,
         "라우트가 닿는다(단건 0 · 목록 5 · 본문지목쓰기 7) — 행 11건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 5 · 본문지목쓰기 7 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "handover.HandoverNoticeComment":
        ("GAP", "via_parent", "fk", 3,
         "인구조사에 없었는데 **3행이 있다** — 0행 아티팩트가 아니라 집계 누락이다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 5 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "handover.HandoverShift":
        ("P1", "via_parent", "fk", 2,
         "라우트가 닿는다(단건 0 · 목록 4 · 본문지목쓰기 0) — 행 2건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 4 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "logger.AuditLogs":
        ("GAP", "no_route", "fk", 1085,
         "인구조사에 없었는데 **1085행이 있다** — 0행 아티팩트가 아니라 집계 누락이다 / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "menu.Menu":
        ("P2", "direct_pk", "fk", 107,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/advanced-table/menu-grid/{menu_id}) — 근거: openapi_routes.json 전수"),
    "menu.RoleMenu":
        ("P2", "no_route", "fk", 923,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "menu.RoleTab":
        ("P2", "no_route", "fk", 375,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "menu.Tab":
        ("P2", "direct_pk", "fk", 27,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/menu/tabs/{tab_id}) — 근거: openapi_routes.json 전수"),
    "menu.UserMenu":
        ("P2", "no_route", "fk", 60,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "operation_settings.OperationSettings":
        ("P1", "direct_pk", "fk", 35,
         "라우트가 닿는다(단건 8 · 목록 6 · 본문지목쓰기 1) — 행 35건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/operation-settings/operation-settings/{setting_id}) — 근거: openapi_routes.json 전수"),
    "operational_data.OperationalData":
        ("P1", "direct_pk", "fk", 3,
         "라우트가 닿는다(단건 5 · 목록 3 · 본문지목쓰기 1) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/operational-data/operational-data/{order_item_id}) — 근거: openapi_routes.json 전수"),
    "operational_data.OperationalDataUploadStatus":
        ("P1", "via_parent", "fk", 21,
         "라우트가 닿는다(단건 8 · 목록 1 · 본문지목쓰기 0) — 행 21건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 8개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: /api/operational-data/operational-data/{order_item_id}/download-operational-log-drone) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "operational_data.OperationalNotice":
        ("P1", "direct_pk", "fk", 3,
         "라우트가 닿는다(단건 4 · 목록 1 · 본문지목쓰기 1) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/operational-data/operational-notice/{notice_id}) — 근거: openapi_routes.json 전수"),
    "orders.Bank":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: /api/orders/order/{id}/refund) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.DeliveryEvent":
        ("P2", "no_route", "fk", 3033,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "orders.DeliveryOption":
        ("P1", "via_parent", "fk", 2,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 0) — 행 2건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.DeliveryProof":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.ExternalOrderStatus":
        ("P1", "via_parent", "fk", 38,
         "라우트가 닿는다(단건 5 · 목록 6 · 본문지목쓰기 1) — 행 38건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 5개 · 목록 6 · 본문지목쓰기 1 로 닿는다 (예: /api/orders/external-order-statuses/{external_status_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.GuessUser":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.Invoice":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.Order":
        ("covered", "direct_pk", "fk", 304,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/orders/order/{id}) — 근거: openapi_routes.json 전수"),
    "orders.OrderAssignment":
        ("P1", "via_parent", "fk", 261,
         "라우트가 닿는다(단건 0 · 목록 0 · 본문지목쓰기 3) — 행 261건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 0 · 본문지목쓰기 3 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.OrderAssignmentProcess":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.OrderComment":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.OrderHistory":
        ("P0", "via_parent", "fk", 5882,
         "단건 경로 9건이 이 모델을 만지고, 행 5882건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 9개 · 목록 6 · 본문지목쓰기 4 로 닿는다 (예: /api/orders/order/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.OrderItem":
        ("P0", "direct_pk", "fk", 304,
         "단건 경로 7건이 이 모델을 만지고, 행 304건이 실재한다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/operational-data/operational-data/{order_item_id}) — 근거: openapi_routes.json 전수"),
    "orders.OrderItemType":
        ("P1", "via_parent", "fk", 23,
         "라우트가 닿는다(단건 0 · 목록 2 · 본문지목쓰기 1) — 행 23건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 2 · 본문지목쓰기 1 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.OrderStatus":
        ("P1", "via_parent", "fk", 7,
         "라우트가 닿는다(단건 8 · 목록 0 · 본문지목쓰기 8) — 행 7건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 8개 · 목록 0 · 본문지목쓰기 8 로 닿는다 (예: /api/delivery/returned/check-arrived-timeout/{operation_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.OrderStatusMapping":
        ("P0", "direct_pk", "fk", 84,
         "단건 경로 3건이 이 모델을 만지고, 행 84건이 실재한다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/orders/order-status-mappings/{mapping_id}) — 근거: openapi_routes.json 전수"),
    "orders.Payment":
        ("P0", "via_parent", "fk", 64,
         "단건 경로 8건이 이 모델을 만지고, 행 64건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 8개 · 목록 9 · 본문지목쓰기 2 로 닿는다 (예: /api/orders/external-order-statuses/{external_status_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.PaymentCallback":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.PaymentType":
        ("P1", "via_parent", "fk", 4,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 0) — 행 4건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.ProductItem":
        ("P2", "no_route", "fk", 247,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "orders.Recipient":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "orders.RefundOrder":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 2 · 본문지목쓰기 0 로 닿는다 (예: /api/orders/order/{id}/refund) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.ReturnOrder":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 0 · 본문지목쓰기 0 로 닿는다 (예: /api/orders/order/{id}/return-order) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "orders.Sender":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "partner.Partner":
        ("P1", "direct_pk", "fk", 3,
         "라우트가 닿는다(단건 9 · 목록 1 · 본문지목쓰기 1) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/partner/api/partners/refresh-token/{partner_id}) — 근거: openapi_routes.json 전수"),
    "print_format.PrintFormat":
        ("P1", "direct_pk", "fk", 4,
         "라우트가 닿는다(단건 4 · 목록 0 · 본문지목쓰기 1) — 행 4건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/print-format/print-formats/print-formats/{print_format_id}/preview) — 근거: openapi_routes.json 전수"),
    "report_template.ReportTemplate":
        ("covered", "direct_pk", "fk", 13,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/report-template/{id}) — 근거: openapi_routes.json 전수"),
    "role.Role":
        ("P2", "direct_pk", "fk", 15,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/menu/menus/{menu_id}/role-permissions/{role_id}) — 근거: openapi_routes.json 전수"),
    "stream_monitors.AIModel":
        ("P1", "via_parent", "fk", 4,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 1) — 행 4건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 1 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "stream_monitors.DeliveryRecord":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "stream_monitors.DetectionEvent":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "stream_monitors.DrawingSession":
        ("GAP", "via_parent", "fk", 1,
         "인구조사에 없었는데 **1행이 있다** — 0행 아티팩트가 아니라 집계 누락이다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 6개 · 목록 1 · 본문지목쓰기 2 로 닿는다 (예: /api/stream-monitors/drawing/sessions/{session_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "stream_monitors.EventClip":
        ("GAP", "no_route", "fk", 0,
         "2026-09-02 D-306 으로 신설(마이그 0021). 인구조사(2026-08-14 덤프)에 없었던 것이 아니라 그때 존재하지 않았다. 소유는 **이벤트에서 물려받는다**(stream_monitors.services.clips._own) — 주인 없는 행은 §0.4 의 created_by__isnull OR 절을 타고 모두에게 보인다(W0-13 이 되돌린 상태). 격리 단언은 backend/tests/test_clip_playback.py 의 test_the_clip_inherits_the_tenant_from_the_event 와 규약 ①(test_rule1_another_tenant_gets_404)이 함께 잰다. 쓰기 면은 이벤트 생성 경로 안 한 곳뿐이고 HTTP 로 만드는 경로는 없다 — 생기면 WRITE_PROBES 에 함께 등재한다(D-290) / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "stream_monitors.NotificationRule":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "stream_monitors.StreamMonitor":
        ("covered", "direct_pk", "fk", 39,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/stream-monitors/stream-monitors/external-stream-monitors/{stream_monitor_id}) — 근거: openapi_routes.json 전수"),
    "stream_monitors.StreamMonitorAIModel":
        ("GAP", "via_parent", "fk", 14,
         "인구조사에 없었는데 **14행이 있다** — 0행 아티팩트가 아니라 집계 누락이다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 3개 · 목록 3 · 본문지목쓰기 5 로 닿는다 (예: /api/stream-monitors/drawing/sessions/{session_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "stream_monitors.Zone":
        ("GAP", "no_route", "fk", 0,
         "2026-09-01 D-299 로 신설(마이그 0019). 인구조사(2026-08-14 덤프)에 **없었던 것이 아니라 그때 존재하지 않았다** — 행 0 은 아티팩트가 아니라 신설 직후의 사실이다. 소유는 dj-core BaseModel 의 group FK 로 첫 행부터 붙고, 판정 서비스(stream_monitors.services.zones)는 스코프로 좁힌 뒤에만 구역을 돌려준다. 격리 단언은 backend/tests/test_zone_judgment.py 의 test_isolation_another_tenant_cannot_see_our_zones 가 양방향으로 잰다. 구역을 **만드는** 공개 면은 아직 없으므로 쓰기 IDOR 표면도 아직 없다 — 생기면 WRITE_PROBES 에 함께 등재한다(D-290) / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "surveillance.MissionPurpose":
        ("P1", "via_parent", "fk", 3,
         "라우트가 닿는다(단건 1 · 목록 4 · 본문지목쓰기 1) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 4 · 본문지목쓰기 1 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.MissionWaypoint":
        ("P0", "via_parent", "fk", 8877,
         "단건 경로 1건이 이 모델을 만지고, 행 8877건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 1 · 본문지목쓰기 2 로 닿는다 (예: /api/surveillance/survey-missions/{survey_mission_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveillanceProfile":
        ("covered", "direct_pk", "fk", 81,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/surveillance/surveillance-profiles/{profile_drone_id}/download-analysis) — 근거: openapi_routes.json 전수"),
    "surveillance.SurveillanceProfileChecklist":
        ("P0", "via_parent", "fk", 83,
         "단건 경로 3건이 이 모델을 만지고, 행 83건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 3개 · 목록 4 · 본문지목쓰기 0 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveillanceProfileChecklistItem":
        ("P0", "via_parent", "fk", 231,
         "단건 경로 1건이 이 모델을 만지고, 행 231건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 0 · 본문지목쓰기 0 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}/check-complete) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveillanceProfileDrone":
        ("P0", "via_parent", "fk", 127,
         "단건 경로 20건이 이 모델을 만지고, 행 127건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 20개 · 목록 8 · 본문지목쓰기 3 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveillanceProfileRepeatType":
        ("P1", "via_parent", "fk", 4,
         "라우트가 닿는다(단건 1 · 목록 1 · 본문지목쓰기 0) — 행 4건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 1개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}/stop-repeat) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveillanceProfileRepeatUntilType":
        ("P1", "via_parent", "fk", 3,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 0) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveillanceStatus":
        ("P1", "via_parent", "fk", 7,
         "라우트가 닿는다(단건 7 · 목록 1 · 본문지목쓰기 0) — 행 7건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 7개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: /api/surveillance/surveillance-profiles/{profile_id}/test-upload-profile-to-flightbird) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.SurveyMission":
        ("P1", "direct_pk", "fk", 39,
         "라우트가 닿는다(단건 10 · 목록 3 · 본문지목쓰기 2) — 행 39건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/surveillance/survey-missions/mission/drone-division/{survey_mission_id}) — 근거: openapi_routes.json 전수"),
    "surveillance.SurveyMissionStatus":
        ("P1", "via_parent", "fk", 3,
         "라우트가 닿는다(단건 2 · 목록 0 · 본문지목쓰기 2) — 행 3건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 2개 · 목록 0 · 본문지목쓰기 2 로 닿는다 (예: /api/surveillance/survey-missions/{survey_mission_id}/approve) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "surveillance.VideoAnalysis":
        ("P0", "direct_pk", "fk", 117,
         "단건 경로 4건이 이 모델을 만지고, 행 117건이 실재한다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/surveillance/video-analysis/{video_analysis_id}) — 근거: openapi_routes.json 전수"),
    "tag.Tag":
        ("GAP", "via_parent", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 자기 pk 경로는 없으나 이름이 이 모델을 가리키는 경로가 1개 실재한다 (예: /api/tag) — 닿을 수 없는 것이 아니다"),
    "tag.TaggedItem":
        ("GAP", "no_route", "fk", 0,
         "인구조사(덤프 집계)에 없었다 — 행이 0이라 안 보였다. **아직 안 쓴 것이지 안전한 것이 아니다** / 도달: 실경로 추적본에 항목이 없고, 전수 라우트에도 이 모델을 가리키는 경로가 없다"),
    "task_status.TaskStatus":
        ("P0", "direct_pk", "fk", 84,
         "단건 경로 3건이 이 모델을 만지고, 행 84건이 실재한다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/optimization/optimization/task-status/{task_id}) — 근거: openapi_routes.json 전수"),
    "terminals.DayOfWeek":
        ("P1", "via_parent", "fk", 7,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 0) — 행 7건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "terminals.DeactivateReason":
        ("P1", "via_parent", "fk", 4,
         "라우트가 닿는다(단건 4 · 목록 0 · 본문지목쓰기 0) — 행 4건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 4개 · 목록 0 · 본문지목쓰기 0 로 닿는다 (예: /api/terminals/terminals/{ids}/deactivate) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "terminals.Function":
        ("P1", "direct_pk", "fk", 9,
         "라우트가 닿는다(단건 6 · 목록 8 · 본문지목쓰기 4) — 행 9건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/terminals/functions/{id}) — 근거: openapi_routes.json 전수"),
    "terminals.LocationType":
        ("P1", "via_parent", "fk", 4,
         "라우트가 닿는다(단건 0 · 목록 1 · 본문지목쓰기 0) — 행 4건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 0개 · 목록 1 · 본문지목쓰기 0 로 닿는다 (예: (목록·본문지목쓰기)) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "terminals.PurposeType":
        ("P2", "no_route", "fk", 3,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "terminals.RouteService":
        ("P2", "no_route", "fk", 2,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "terminals.RouteTerminal":
        ("P0", "via_parent", "fk", 2062,
         "단건 경로 9건이 이 모델을 만지고, 행 2062건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 9개 · 목록 3 · 본문지목쓰기 8 로 닿는다 (예: /api/terminals/qground-control/export-single-plan/{route_id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "terminals.Routes":
        ("P1", "direct_pk", "fk", 30,
         "라우트가 닿는다(단건 17 · 목록 4 · 본문지목쓰기 6) — 행 30건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/delivery/processing/get-drone-by-route/{route_id}) — 근거: openapi_routes.json 전수"),
    "terminals.Terminal":
        ("covered", "direct_pk", "fk", 5686,
         "격리 시험 MODELS 레지스트리에 등재돼 있다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/terminals/days-of-week/{id}) — 근거: openapi_routes.json 전수"),
    "terminals.TerminalException":
        ("P1", "via_parent", "fk", 2,
         "라우트가 닿는다(단건 7 · 목록 0 · 본문지목쓰기 0) — 행 2건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 7개 · 목록 0 · 본문지목쓰기 0 로 닿는다 (예: /api/terminals/terminals/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "terminals.TerminalOperatingTime":
        ("P0", "via_parent", "fk", 98,
         "단건 경로 7건이 이 모델을 만지고, 행 98건이 실재한다 / 도달: 자기 pk 경로는 없다. 부모 pk 경로 7개 · 목록 0 · 본문지목쓰기 0 로 닿는다 (예: /api/terminals/terminals/{id}) — 부모 경로 스코프와 자식 필터를 **둘 다** 시험한다"),
    "terminals.TerminalPurpose":
        ("P2", "no_route", "fk", 3,
         "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. **'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — 동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263) / 도달: 실경로 추적에서 상세·쓰기·목록·본문지목쓰기 어느 버킷에도 없다"),
    "terminals.TerminalType":
        ("P1", "direct_pk", "fk", 9,
         "라우트가 닿는다(단건 8 · 목록 7 · 본문지목쓰기 6) — 행 9건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. 본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다 / 도달: 자기 pk 로 지목하는 경로가 실재한다 (/api/terminals/terminal-types/{ids}/change-status) — 근거: openapi_routes.json 전수"),
}


def by_priority(name: str) -> list[str]:
    return sorted(k for k, v in CENSUS.items() if v[0] == name)


def by_reach(name: str) -> list[str]:
    return sorted(k for k, v in CENSUS.items() if v[1] == name)


def fk_models() -> list[str]:
    """`group` FK 로 테넌트를 가리는 모델 — D-271 의 술어 확장분."""
    return sorted(k for k, v in CENSUS.items() if v[2] in ("fk", "both"))
