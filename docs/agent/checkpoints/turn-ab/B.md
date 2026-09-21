# 차선 B — 청구·계량 (턴 AB · P-224 집행)

WO-GX-20260921-04 §3 B · 판정 **P-224** · 착수 2026-09-21 · 브랜치 `turn-q`
**로그인 0회 · 브라우저 0회 · 서버 재기동 0회 · 삭제 0건 · `--no-verify` 0**

---

## ① ★ 전/후 표 — **마이그레이션 전에 떠 놓고, 뒤에 다시 떴다**

> 「전」은 마이그레이션 **전에** 실제로 센 수다. 「후」는 **같은 표·같은 소프트 삭제
> 규칙**으로 다시 센 수이고, 달라진 것은 **청구 거름 한 줄**(`exclude_unbillable`)뿐이다.
> 두 수를 다른 셈으로 내면 그 차이는 표식의 효과가 아니라 셈의 차이다.

| 재는 것 | **전** 11:37:31 | **후** 12:05:19 | 차이 | 근거 파일 |
|---|---|---|---|---|
| ETRI-Group **청구 카메라** | **15** | **4** | **−11 (−73 %)** | `evidence/P-224/{before,after}.json` |
| ETRI-Group **청구 계정** | **30** | **19** | **−11 (−36.7 %)** | 〃 |
| ETRI-Group **화면 카메라**(운영 면) | 15 | **15** | **0** ★ | 〃 |
| ETRI-Group **화면 계정**(운영 면) | 30 | **30** | **0** ★ | 〃 |
| ETRI-Group 미디어 | 115건 · 1,493,917,814 B | 115건 · 1,493,917,814 B | 0 (**못 쟀다**) | 〃 |
| 다른 테넌트 아홉 (청구·화면 전부) | 아래 표 | **한 칸도 안 변함** | **0** | 〃 |

★ **이 두 줄(화면 0)이 이 차선의 심장이다.** 청구만 −11 이고 **운영 면은 안 움직였다** —
씨앗을 감춘 것이 아니라 **청구에서 뺀 것**이다 (P-224 ③ · D-497).

```
[적용 기록 · 실물]
  common.0002_p224_billing_mark          OK      (곁표 한 표)
  common.0003_p224_seed_account_marks    OK      (계정 표식 11줄)
  stream_monitors.0031_p224_camera_data_source OK (칸 + 카메라 표식 11줄)
  showmigrations 실물 확인 → 셋 다 [X]

[표식 실물 · 12:0x]
  카메라 출처별   live 40 · probe 7 · seed 1 · drill 3      (표식 11 = 꼭 그 11대)
  곁표 BillingMark  11줄  (user.coreuser: seed 5 · probe 6)
  ⇒ **씨앗 청구 0** — 카메라 11/15 → 0 · 계정 11/30 → 0
```

**남은 청구 카메라 4대** = 고객 3(`GD-150Q` · `H40` · `NBP-DR-P2`) + **분류 미정 1**
(`GX-U5-01` · 아래 ⚠). 계정 19 = 고객 19.

### 전 — 전 테넌트 [실측 2026-09-21T11:37:31+00:00 · ORM · `gx-shell`]

| pk | 테넌트 | 청구 카메라 | 청구 계정 | 미디어 건 | 미디어 바이트 |
|---|---|---|---|---|---|
| 4 | **ETRI-Group** | **15** | **30** | 115 | 1,493,917,814 |
| 5 | Group Default | 0 | 4 | 2 | 793,418 |
| 6 | Anyang | 9 | 25 | 667 | 379,668,206 |
| 7 | Gaion | 15 | 15 | 194 | 2,122,401,540 |
| 8 | Thailand | 0 | 8 | 34 | 169,389,509 |
| 11 | Fire_Drone | 11 | 6 | 19 | 2,627,089 |
| 12 | DRONE-ROBOT | 0 | 7 | 16 | 1,830,151 |
| 13 | Gaion Test | 0 | 1 | 0 | 0 |
| 14 | Gongju | 1 | 4 | 13 | 9,081,661 |
| 15 | GeumSan-ETRI | 0 | 2 | 0 | 0 |

★ **분모를 보고 옮겼다.** 턴 AA 에 「계정 105개 중 11개(10 %)」로 올라간 수가 있었는데
**105 는 전 테넌트 합**이었다. 같은 테넌트는 **30**이고, 비중은 10 % 가 아니라
**36.7 %** 다. 이 표의 분모는 전부 **한 고객의 수**다 — 손으로 적은 분모는 없다.

### 씨앗의 정체 — 한 줄씩 본 것 (분류는 **진단**이지 규칙이 아니다)

| 표 | 우리 것 | 무엇 | 남는 것 |
|---|---|---|---|
| 카메라 15 | **11** | 탐침 7(`gxprobe-D384-screen-CAM` 1 · `GX-ONB-V-*` 6) · 검수 씨앗 1(`GX-SEED-DSM`) · 훈련 3(`GX-DRILL-ANYANG-01·02·03`) | 고객 3 + **분류 미정 1** |
| 계정 30 | **11** | `employee_id=GX-SEED-ROLE-*` 4 · 표식 없는 탐침 7 | 고객 19 |
| 미디어 115 | **못 쟀다** | 표식 0 · 이름 0건 · 만든이가 씨앗 계정 0건 | — |

⚠ **분류 미정 1 = `GX-U5-01`(안양천서로카메라).** `GX-` 접두 말고 근거가 없다.
접두는 **정황**이고 정황을 청구 근거로 쓰지 않는다(D-301). **안 건드렸다** —
이 한 대는 지금 고객 쪽에 선다. 근거가 생기는 날 장부에 한 줄 더한다.

⚠ **미디어는 0이 아니라 「못 쟀다」다.** 곁표는 섰지만 *무엇을 표시할지*의 근거가
없다. 0으로 덮지 않았다.

---

## ② 한 일 — P-224 다섯

| # | P-224 | 한 것 | 파일 |
|---|---|---|---|
| ① | 카메라 표만 `data_source` 칸 · 기본 `live` | 칸 + 씨앗 11줄 소급 | `backend/stream_monitors/migrations/0031_p224_camera_data_source.py` · `stream_monitors/models.py` |
| ② | dj-core 셋은 **발급 순간 `billing_marks` 표식** | 곁표 `common.BillingMark` + `mark_unbillable()` + 계정 11줄 소급 | `backend/common/models.py` · `common/migrations/0002_p224_billing_mark.py` · `0003_p224_seed_account_marks.py` · `common/billing_marks.py` |
| ③ | 고객 면은 `live` 만 · **운영·감사 면은 한 줄도 안 뺀다** | 거름은 `exclude_unbillable` 한 곳에만. 화면·큐·감사는 이 값을 안 본다 | 불변 시험 4개(아래 ④) |
| ④ | **이름으로 안 거른다**(D-280) | 세는 코드에 `gxseed`·`gxprobe` 낱말 **0** — 시험이 붙든다 | `tests/test_b_billing_marks.py::TheCountingCodeDoesNotKnowOurNamesTest` |
| ⑤ | **훈련 = 0원 줄** · 사용량에 제외 표기 | `invoice_draft()` 의 훈련 줄 · `usage()["exclusions"]` | `apps/dsm/metering.py` |

### 왜 갈래가 둘인가 (한 줄)

세 표 중 둘이 **dj-core** 라 칸을 못 더한다(§0.4). 그래서 **우리 표(카메라)는 칸**,
**남의 표는 곁표**다 — 남의 행은 한 자도 안 고치고 **우리 표에 사실을 적는다.**
선례는 `common/migrations/0001_audit_logger_name_index.py`(「표는 빌리고, 코드는 안
만진다」). **부르는 쪽은 한 글자도 안 고쳤다** — 갈래를 고르는 일은 전부
`exclude_unbillable` 안에서 끝난다(K1·K2·K6 무수정).

### 소급은 **규칙이 아니라 장부**다

`username__startswith` 같은 규칙을 세우면 그 규칙은 **다음 달에도 돈다** — 고객 이름
하나가 우리 접두와 겹치는 날 그 계정이 조용히 공짜가 된다(D-280). 그래서 소급은
**pk 로 얼린 22줄**(카메라 11 · 계정 11)이고, 줄마다 근거(`reason`)가 붙어 있다.
`pk` 와 `code`/`username` 이 **둘 다** 맞을 때만 손댄다 — pk 만 보면 다른 DB 에서
엉뚱한 고객 행이 공짜가 된다. **세는 코드는 이름을 모른다.**

---

## ③ 가격표 — **자리는 세우고 값은 비웠다** (§4-5 · P-223)

`backend/apps/dsm/metering/price_table.yaml` (신설 · 값 5칸 **비움** · 훈련 0 하나만 확정)

- 비면 청구서 초안의 그 줄이 **「단가 미확정」 회색**(`state: "unpriced"` · `amount: null`)
- 회색 줄이 하나라도 있으면 합계를 **`subtotal`** 이라 부르고 `is_total: false` —
  **부분합을 총액이라 부르지 않는다**
- **훈련 줄만은 회색이 아니다**: 건수를 못 세어도 금액이 확정이다(0 × 무엇이든 0)
- PyYAML 이 이 환경에 **없어서**(실측) 평평한 한 겹만 읽는 15줄짜리 읽개를 썼다 —
  청구서 한 장 때문에 의존성을 늘리지 않았다(늘리면 컨테이너를 다시 짓기 전엔 못 읽고,
  **못 읽히는 가격표는 없는 가격표**다)
- ⚠ `metering/` 에 `__init__.py` 가 생기면 **`metering.py` 를 가린다** — 시험이 붙든다

---

## ④ 시험 — `backend/tests/test_b_billing_marks.py` (신설 · 20개)

| 묶음 | 무엇을 붙드나 | 개수 |
|---|---|---|
| ★ **계량 전/후 불변** | 표식을 달아도 **관제 카메라 목록 · 사람 목록 · 감사 줄 · 행 수**가 안 변한다 | **4** |
| 두 방향 | 표식 단 행은 정확히 빠지고 · **안 단 행은 그대로 센다** · 출처 셋 전부 · 남의 테넌트 0 | 4 |
| D-280 | 세는 코드에 우리 이름 낱말 0 · 이름 칸을 아예 안 본다 | 2 |
| 짝 맞추기 | 마이그레이션 낱말 = `billing_marks` 낱말 · 칸 이름 = 표식 낱말 · **사건 표에 `track_id` 가 아직 있는가** | 4 |
| 발급 표식 | 두 번 달아도 한 줄 · 모르는 낱말 거절 · `live` 는 청구에 든다 | 3 |
| 가격표 | 넷 비었다 · 훈련 0 · 회색이 0원이 아니다 · 훈련 줄은 회색 아니다 · 자리가 자료만 | 5 |
| 제외 표기 | 사용량이 제 입으로 뺀 것을 말한다 · 저장은 「못 쟀다」로 따로 | 2 |

★ **한 방향만 재면 거짓 초록이 통과한다.** 「표식 단 것이 빠지는가」만 재면
*전부 0으로 만드는 코드*가 통과하고, 「불변」만 재면 *아무것도 안 하는 코드*가
통과한다. 그래서 두 방향을 **같은 클래스 안에서** 잰다.

★ **`exclude_unbillable` 이 FieldError 로 내던 큰 소리를 시험이 물려받았다.**
칸이 없는 표(`CoreUser`)에도 그 함수가 걸리게 된 뒤로는 그 소리를 낼 수 없다 —
`TheWordsAgreeTest::test_the_event_marker_still_has_its_field` 가 대신 낸다.

### 실행 — **193 통과 · 0 실패** [gx-shell · `--nomigrations -p no:randomly`]

```
tests/test_b_billing_marks.py                                     24 passed   26s
tests/test_u56_metering_seeds.py test_be_metering.py
  test_dsm_app.py test_k6_feedback_kernel.py                      94 passed   71s
tests/test_k1_event_kernel.py test_k2_notify_kernel.py
  test_u1_probe_not_counted.py test_u1_drill_counted.py           75 passed  118s
```

★ **전량은 안 돌렸다**(조율자 지시 · 병합 뒤 조율자가 돈다). 고른 여덟 파일은
**청구 셈을 지나는 전부**다 — 계량·씨앗·앱 얇기·K1·K2·K6·probe·drill.

### 게이트 둘 [기계 시각 12:1x]

```
scripts/verify_layers.py       (호스트)   → [LAYER] 통과 — 계층 위반 0건 (분모 83)
scripts/verify_migrations.py   (gx-shell) → [MIGR]  정합 — 모델 선언 = 마이그레이션 그래프 = DB
                                            ① 모델→마이그레이션 미반영 0 · ② 마이그레이션→DB 미적용 0
                                            (양성 대조 둘 다 잡혔다 — 판정기가 작동한다)
```
⚠ `verify_migrations.py` 는 머리말이 *"호스트에서 부르면 docker exec 로 위임한다"*
라고 적어 두었는데 **그 위임 코드가 파일에 없다**(`docker` 문자열 0건). 호스트에서
부르면 `celery 없음`으로 **rc 2 회색**이다. `gx-shell` 안에서 `/repo/scripts/…` 로
불러야 잰다. 제 파일이 아니라 안 고쳤다 — **Q 에게 한 줄 넘긴다.**

★ **청구서 초안을 실물로 한 장 떴다**: `evidence/P-224/invoice_draft_sample.json`
(ETRI-Group · 카메라 4 · 좌석 19 · 둘 다 **「단가 미확정」 회색** · 훈련 줄 **0원 초록** ·
`is_total: false` — 부분합을 총액이라 부르지 않는다).

---

## ⑤ 도커 엔진이 죽었다 되살아났다 — **제가 안 건드렸습니다**

```
[기계 시각 2026-09-21 11:45~12:00 · 호스트]
docker ps → 500 Internal Server Error (v1.54 API) → 이어서 파이프 자체가 사라짐
→ Docker Desktop 이 스스로(또는 조율자 손으로) 복귀 · 컨테이너 10/10 재기동
```

- **재기동 0 · 컨테이너 삭제 0 · 서버 새로 세움 0** (§ 서버 재기동 금지).
- 11:37 에 `gx-shell` 안에서 **전 측정**을 끝냈고, 11:45 `makemigrations common` 까지
  성공했다. 바로 다음 호출부터 500. 그 사이에는 **호스트 일만** 했다(파일 쓰기·구문 검사).
- 되살아난 뒤 **`showmigrations` 로 실물을 먼저 보고**(셋 다 `[ ]`) 시작했다.
- ⚠ **엔진이 죽은 동안 잰 수는 없다.** 「전」은 11:37(장애 전 · 코드 변경 전),
  「후」는 12:05(복구 후 · 적용 후)다. 경합 중에 잰 수가 이 표에 없다.
- 턴 AA 에 U56 도 같은 500 을 만났다(그 보고 ㉤ ①). **되풀이된다.**

⚠ **전 측정은 다시 못 뜬다** — 모델에 칸이 생긴 뒤로는 옛 셈이 `ProgrammingError`
(`column ... data_source does not exist`)로 죽는다. 11:37 의 `before.json` 이
**유일한 「전」**이고, 그래서 *마이그레이션 전에 떠 두는 것*이 규칙이다(WO §6 함정 ③).

---

## ⑥ 남긴 빚 — **넘김**

1. **발급 순간의 배선이 다섯 자리 남았다.** 소급은 한 번이고, 앞으로 나는 씨앗은
   만드는 경로가 제 손으로 표식을 적어야 한다. 그 다섯 자리는 제 소유 밖이라 안
   건드렸다 — 목록과 한 줄짜리 고침은 `조율자.inbox/B.md` ⑤ 에 있다.
2. **미디어(저장)의 씨앗 몫은 여전히 「못 쟀다」.** 곁표는 섰지만 표시할 근거가 없다.
   미디어의 출처는 **그것을 만든 것**(카메라·사건)에서 물려받아야 하는데
   `UserMediaFile` → 카메라의 관계가 `videoanalysis` 를 지난다. 0으로 안 덮었다.
3. **`GX-U5-01` 카메라 1대 분류 미정.** 접두 말고 근거가 없다.
4. **표식 없는 옛 훈련 사건**(`test_u56_metering_seeds::WhatWeStillCannotSubtract`)은
   이 턴에도 못 뺐다 — 창 판정은 행마다 감사를 물어야 해서 월 단위 셈에 못 쓴다.
   그 시험은 지금도 초록이다(빚이 그대로라는 뜻이다 · 0으로 안 덮었다).
5. **소급 22줄은 대표께 한 번 보여야 한다.** P-223 대로 「대표 결정 뒤」로 미루지 않고
   집행했지만, **청구서를 다시 내는 것은 못 되돌린다.** 목록은 마이그레이션 두 파일
   안에 근거와 함께 얼어 있다 — 되돌리기는 `migrate … 0030`/`0002` 한 줄이다(P-222).

★ **고친 것 하나**: `common/billing_marks.py` 머리말의 「105」(전 테넌트 수를 한
  테넌트 수로 적은 것)를 이번에 바로잡았다 — U56 이 다음 턴 첫 줄 후보로 남긴 것이다.

---

## ⑦ 절 5 중 **닫힘 5 · 넘김 5**(사유 — 전부 *소유 밖의 배선*이지 미완이 아니다)

| 닫는 조건 | 결과 | 증거 |
|---|---|---|
| **씨앗 청구 0** | 카메라 11/15 **→ 0** · 계정 11/30 **→ 0** | `evidence/P-224/after.json` · 표식 실물 22줄 |
| **전/후 표 1** | ① 표 (전 11:37 · 후 12:05 · 같은 셈) | `evidence/P-224/{before,after}.json` |
| **불변 시험 ≥ 3 통과** | **4개 통과**(화면 카메라·화면 계정·감사·행 수) + 실측 불변 2줄 | `tests/test_b_billing_marks.py` 24 passed |

색은 칠하지 않는다 — 위 증거 경로를 읽고 색은 V·조율자가 정한다.

**넘김 5** = ⑥의 다섯(발급 배선 · 미디어 근거 · 분류 미정 1 · 표식 없는 옛 훈련 사건 ·
소급 목록의 대표 확인). **다섯 다 제 소유 밖이거나 근거가 없는 것**이고, 근거 없는
자리를 0으로 덮지 않았다.

## ⑧ 만진 파일

```
신설  backend/common/models.py                                   (곁표 BillingMark)
신설  backend/common/migrations/0002_p224_billing_mark.py
신설  backend/common/migrations/0003_p224_seed_account_marks.py
신설  backend/stream_monitors/migrations/0031_p224_camera_data_source.py
신설  backend/apps/dsm/metering/price_table.yaml                 (값 비움)
신설  backend/tests/test_b_billing_marks.py
신설  docs/agent/evidence/P-224/{before.json,measure_billing_seeds.py,measure_billing_after.py}
수정  backend/common/billing_marks.py                            (소유 · 갈래 셋)
수정  backend/apps/dsm/metering.py                               (소유 · 가격표·초안·제외 표기)
수정  backend/stream_monitors/models.py                          ★ 소유 밖 · 칸 하나 덧붙임만
```

★ **`stream_monitors/models.py` 는 제 소유 밖이다.** P-224 ①(카메라 표에 `data_source`
칸)은 모델 선언 없이는 집행이 불가능하다 — 칸을 SQL 로만 내리면 ORM 이 그 칸을 모르고,
모르면 거를 수 없다. 소유표에 그 파일의 주인이 없어 **기존 줄은 0자도 안 고치고**
덧붙이기만 했다. 조율자에게 쪽지로 알렸다.

**커밋 0** — 조율자가 한다.
