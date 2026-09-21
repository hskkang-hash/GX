# B → 조율자 (청구·계량 · P-224) — **끝났습니다**

## ① 결과 한 줄

**씨앗 청구 0.** ETRI-Group 청구 카메라 **15 → 4**(−11) · 청구 계정 **30 → 19**(−11).
**운영 면은 한 칸도 안 움직였습니다**(화면 카메라 15 → 15 · 화면 계정 30 → 30).
다른 테넌트 아홉은 청구·화면 모두 **한 칸도 안 변했습니다.**

전/후 표는 `docs/agent/checkpoints/turn-ab/B.md` 의 **첫 표**입니다.
증거: `docs/agent/evidence/P-224/{before.json,after.json,invoice_draft_sample.json}`

## ② 도커 — **제가 안 건드렸습니다**

11:37 에 전 측정을 끝냈고, 11:45 `makemigrations` 뒤부터 500 이었습니다.
그 사이에는 **호스트 일만** 했습니다(파일 쓰기·구문 검사). 재기동 0 · 서버 새로 세움 0.
되살아난 뒤 **`showmigrations` 로 실물을 먼저 보고**(셋 다 `[ ]`) 적용했습니다.
**엔진이 죽은 동안 잰 수는 제 표에 한 칸도 없습니다.**

⚠ 지시대로 **전량 시험 안 돌렸습니다.** 제 자리를 지나는 여덟 파일만:
**193 passed · 0 failed**(test_b_billing_marks 24 · 계량/앱/K6 94 · K1/K2/probe/drill 75).

## ③ 병합 때 보실 것 — **남의 파일 두 곳**

| 파일 | 무엇 | 왜 |
|---|---|---|
| `backend/stream_monitors/models.py` | 칸 하나(`data_source`) **덧붙이기만** (기존 줄 0자 수정) | P-224 ① 은 모델 선언 없이 집행 불가 — SQL 로만 내리면 ORM 이 그 칸을 몰라 거를 수 없다 |
| `backend/common/models.py` | **신설**(곁표 `BillingMark` 한 표) | `common` 앱에 models.py 가 없었다(마이그레이션 패키지는 이미 있었다) |

마이그레이션 셋은 전부 **적용 완료**(`common.0002` · `common.0003` ·
`stream_monitors.0031`). 되돌리기는 `migrate common 0001` / `migrate stream_monitors 0030`.

## ④ ★ **넘김 — 다른 차선이 한 줄씩 달아야 씨앗이 다시 안 샌다**

소급은 **한 번**이고 pk 로 얼려 두었습니다(규칙이 아니라 장부 · 근거 `reason` 한 줄씩).
**앞으로 나는 씨앗은 만드는 자리가 표식을 적어야 합니다.** 제 소유 밖이라 안 건드렸습니다:

| 만드는 자리 | 한 줄 | 주인 |
|---|---|---|
| 게이트 탐침 카메라 (`scripts/probe_*`) | 만들 때 `data_source="probe"` | 조율자 |
| 온보딩 계측기 (`measure_onboarding_t.py`) | 만들 때 `data_source="probe"` | V |
| 훈련 창 (`stream_monitors/services/drill.py`) | 만들 때 `data_source="drill"` | — |
| 씨앗 계정 (`seed_role_users`) | 만든 뒤 `billing_marks.mark_unbillable(user, "seed", reason=…)` | — |
| 탐침 계정 (게이트) | 같은 한 줄 | 조율자 |

`mark_unbillable(obj, source, reason=…)` 는 **dj-core 표에도 됩니다** — 그 행을 한 자도
안 고치고 우리 곁표에 적습니다. `data_source` 를 안 적으면 기본값 `live`(고객의 것)라
**청구에 듭니다** — 그것이 규약입니다(공짜가 된 것은 안 보이므로).

## ⑤ 창·로그인

**브라우저 0 · 로그인 0회.** ORM·마이그레이션·시험만 했습니다. 창 요청 없습니다.
**커밋 0** — 조율자가 하십니다.
