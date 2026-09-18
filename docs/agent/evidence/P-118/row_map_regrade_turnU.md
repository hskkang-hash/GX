# P-169 절 1 — **row_map 회색 25 재판정** (2026-09-18 · 턴 U · 차선 Q)

- 분모 **39** — 손으로 적지 않았다: `docs/agent/evidence/D-309/contract_ac_ledger.yaml` 의 `features[*].clauses[*]` 를 세어 39.
  색의 출처도 파일이 아니라 코드다: 사슬 선언 `scripts/verify_feature_reach.py::REACH_MAP` · 회색 사유 `GREY_WHY`
  (P-142 의 `row_map.json` 은 「이 파일로 수가 움직이는 길은 없다」고 스스로 적어 두었고, 그 말은 **지금도 참이다** —
  `linked:true` 인 행이 0 이다. 그래서 재판정은 **판정기 안의 사유**를 고치는 일이다).
- 판정 기준: **라우트 대장 749**(`docs/agent/evidence/D-343/route_inventory.json` · `totals.routes == 749` · 2026-09-17 11:05 실측)
  + `frontend/src` 실재 파일명 grep(2026-09-18).

## 지배 사실이 낡았다 — **0건이 13건이 됐다**

P-142 가 2026-09-15 에 적은 지배 사실:

> 회색 25 가운데 24 는 **그 절을 사람에게 보여 주는 화면이 제품에 없다** — 설정 쓰기 문은 서버에 서 있으나
> `frontend/src/features` 에서 `/api/dsm/settings` 를 부르는 코드가 **0건**이다 [grep 2026-09-15]

[재실측 2026-09-18] `grep -rn "api/dsm/settings" frontend/src | wc -l` → **13**.
화면도 라우터에 섰다: `/dsm/audit`·`/dsm/notify`·`/dsm/integrations`·`/dsm/people`·`/dsm/cameras/tuning`·`/dsm/system`
(`features/dsm/routes.ts` · `routes.u24.ts` · 페이지 파일 32개).

## 사유 낡음 — **6행을 지금 사실로 고쳐 적었다** (목표 ≥ 4)

| 절 | 옛 사유 | 지금 사실 [2026-09-18] | 처분 |
|---|---|---|---|
| F-12-c2 | 「성공·실패 감사로그를 보여 주는 화면이 없다」 | `/dsm/audit`(`routes.u24.ts:41`)이 `AuditLog.tsx:89` 에서 `GET /api/dsm/audit` 를 부른다. 대장 749 에 그 라우트 있음 · 읽는 사람 U2·U4·U5(`api_u24.py:307`) | **회색 → REACH_MAP 선언** |
| F-12-c3 | 「수신자 관리 화면이 없다」 | `/dsm/notify` 가 `NotifySettings.tsx:117` 에서 `GET /api/dsm/settings/notify-rules/list` 를 부른다 | **회색 → REACH_MAP 선언** |
| F-12-c8 | 「API 키 관리 화면이 없다」 | `/dsm/integrations` 가 `Integrations.tsx:159` 에서 `GET /api/dsm/settings/api_keys` 를 부른다(하이픈 아니다 · D-470) · 발급/폐기도 같은 화면 | **회색 → REACH_MAP 선언** |
| F-02-c3 | 「`/operation-settings` 는 설정 API 를 한 건도 부르지 않았다」 | 그 화면이 아니라 `/dsm/cameras/tuning` 이 임계값 자리다(`CameraTuning.tsx` → `GET /api/dsm/stats/camera-threshold(s)`). **남은 것은 축이 다르다는 것** — 계약은 지점(구역)별, 제품은 카메라별 | **회색 유지 · 사유 교체** |
| F-12-c6 | 「임계값 관리 화면이 없다」 | 화면은 섰다. 그러나 이 절이 말하는 관리자 **설정** 문 `/api/dsm/settings/thresholds` 를 부르는 **페이지**는 0건이다(`api.ts` 가 상수만 들고 있다) | **회색 유지 · 사유 교체** |
| F-10-c1 | 「등급별 수신그룹 설정 화면이 없다」 | 절반만 낡았다 — 수신그룹은 `/dsm/notify` 로 섰고, 등급규칙 문 `POST /api/dsm/settings/grade-rules` 는 프런트 호출 **0건**이다. 「등급**별**」이라 둘 다 서야 한다 | **회색 유지 · 사유 교체** |
| F-11-c1 | 「`/report-template` 은 레거시 print-format」 | 옛 사유는 **그대로 참**. 새 사실: `GET /api/dsm/reports/templates` 가 대장 749 에 섰고 프런트 호출 0건 — 이번 턴 U24 의 `Reports.tsx` 가 서면 REACH_MAP 에 한 줄 | **회색 유지 · 사유 보강** |

## 사유가 **그대로 참**임을 재확인한 행 (낡지 않았다)

- **F-12-c5 구역 관리 · F-03-c3 위험구역 편집** — `GET/POST /api/dsm/settings/zones` 는 대장 749 에 **있는데**
  `frontend/src` 에서 그 문을 부르는 코드가 **0건**이다 [grep 2026-09-18]. 문은 있고 화면이 없다. 사유에 그 실측을 덧붙였다.
- 시간·부작위·집계 절(F-02-c2 · F-04-c2 · F-10-c2 · F-13-c1 · F-14-c2)과 화면에 안 드러나는 판정 절
  (F-01-c1 · F-03-c1 · F-03-c2 · F-04-c1) — **화면 한 장으로 잴 수 없다**는 성질의 사유라 낡지 않는다. 그대로 둔다.
- F-09-c1(다섯 상태 중 한 장) · F-12-c1(403 을 다른 자리에서 받았다) · F-11-c2/c3 · F-12-c4/c7 · F-02-c1 — 그대로.

## V 가 **이번 턴** 잴 수 있는 행 — 셋 (목표 ≥ 3)

`REACH_MAP` 선언 셋(F-12-c2 · F-12-c3 · F-12-c8)과 **같은 커밋**으로 캡처 자리를 세웠다:
`scripts/capture_screens.py::TARGETS` step **29** `/dsm/audit`(U4) · **30** `/dsm/notify`(U5) · **31** `/dsm/integrations`(U5).

- 세 절 모두 **시험 다리(proof)는 이미 서 있다**(계약 대장의 `proof` 파일이 실재 — 3/3). 남은 고리는 **캡처**뿐이다.
- 찍히면 초록, 안 찍히면 **회색**(「선언한 화면이 인덱스에 없다」), 찍혔는데 그 문을 안 불렀거나 200 이 아니면 **빨강**이다.
  ★ 이 선언이 초록을 만들지 못한다 — 만들 수 있으면 그것이 결함이다.
- `must_see` 는 **일부러 달지 않았다.** 이번이 첫 촬영이라 화면이 실제로 쓰는 글자를 우리가 못 봤다.
  안 본 글자를 정답으로 적으면 제품이 아니라 우리 기대를 재게 된다(P-132 가 여덟 자리에서 고친 그 모양).

## 지금 수 (재판정 **전후 모두 실측** · 이 문서가 수를 만들지 않는다)

    PYTHONIOENCODING=utf-8 python scripts/verify_feature_reach.py --no-gates
    → 색: 초록 4 · 빨강 0 · 회색 28 · 잠김 7 (절 39)      # 게이트 셋을 안 부른 실행
    → 게이트를 부르면 초록 7 (F-05-c1·c2·c3 가 그 셋이다)

**영역 ① 은 이 커밋으로 움직이지 않았다** — 7/39 그대로다. 움직이는 것은 V 가 석 장을 찍은 뒤다(목표 10/39).
분모 39 는 그대로다(대장은 줄지 않는다).
