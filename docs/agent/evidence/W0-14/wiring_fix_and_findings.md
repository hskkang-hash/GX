# W0-14b — 격리 시험 배선 정정 + 처음 나온 판정 결과

**실행** 2026-08-24 · **결정** D-253 (P-W0-14-2 승인 · 배선만) · **티켓** W0-14 · W0-3 (WP-2)
**단언(assert)은 한 글자도 바꾸지 않았다.** 부르는 경로·메서드·본문·인증·픽스처만 고쳤다.

---

## 0. 판정

> **5시나리오가 처음으로 판정에 도달했다.** 그리고 그 판정은 **격리가 뚫려 있다**고 말한다.
>
> | 시나리오 | 이전(배선 결함) | **지금(판정 도달)** |
> |---|---|---|
> | list | 404·401 로 판정 전 사망 | **8/8 통과** — 남의 레코드가 목록에 없다 |
> | detail | 같음 | **5건 누출** — 남의 레코드를 HTTP 200 으로 읽는다 |
> | update | PATCH 405 | **3건 누출 + 2건은 남의 행에 쓰기 시도** |
> | delete | 같음 | **5건 200** — 그중 **실제로 지워진다** (§3) |
> | export | 대상 없음 | 대상 없음 (통과) |
>
> 이전 판이 "0/5 실행 → 9 failures·24 errors" 였던 것과 성격이 다르다. 그때는 **아무것도
> 묻지 못했고**, 지금은 **답이 나왔다.** 답이 나쁜 것이 배선이 고쳐졌다는 증거다.

---

## 1. 무엇이 배선 결함이었나 (실측 4종)

| # | 결함 | 실측 근거 | 고친 방법 |
|---|---|---|---|
| ① | `api_base` 4개가 404 | `/api/terminals/` 는 라우트가 아니라 **마운트 지점**이다 | 실경로 등록 (`/api/terminals/terminals`) |
| ② | 상세·수정 경로 형태 | 상세 경로에 **끝 슬래시가 없다**. **PATCH 는 저장소 전체에 1건** — 수정은 PUT(devices 는 POST), 삭제는 대개 `delete/{ids}` | 시나리오별 `(메서드, 경로)` 등록 |
| ③ | 인증 401 | `force_login`(세션)도, `RefreshToken.for_user()` 맨 토큰도 통과하지 못한다 — dj-core 는 토큰 `jti` 를 사용자에 저장된 세션값과 대조한다 | 로그인 경로와 **같은 3단계**(session_id → access → jti 저장) |
| ④ | 필수 FK 24건 | `Order.recipient_address` · `ChecklistSetting.category` · `SurveillanceProfile.mission` · `HandoverDocument.shift` 등 | `Deps` 헬퍼가 의존을 만들어 재사용 |

### 1-1. 배선을 고치는 과정에서 드러난 것 3개 (전부 별 결함)

* **권한이 없어서 401 이던 것을 권한 픽스처로 열었다.** 두 사용자에게 **동일한** 경로 권한을
  준다 — 그러면 남는 차이가 소속 테넌트 하나뿐이고, 그것이 이 시험이 묻는 것이다.
  역할 코드는 `superuser` 가 **아니다**(`tenant_iso_test`). 그 코드를 주면 dj-core 우회가
  켜져 시험이 스스로 격리를 무력화한다.
* **`path_permission` 의 거부는 dict 를 돌려준다.** 응답 스키마가 `List[...]` 인 라우트에서는
  pydantic 이 그 dict 를 거부해 **HTTP 500** 이 된다. D-248 이 말한 "200-body-403" 은
  타입 있는 라우트에서 **500** 으로 나타난다 → W0-18 의 입력.
* **빈 본문(`{}`)은 검증에서 422 로 튕긴다.** 실제 공격자는 자기 테넌트의 유효한 값을 보낸다.
  그래서 본문을 tenant-A 가 만들 수 있는 유효한 값으로 채웠다 — 그러자 판정에 도달했다.

---

## 2. 판정 결과 — 누출 목록 (재현: `python manage.py test tests.test_tenant_isolation -v 2 --keepdb`)

```
Ran 13 tests — 16 failures · 2 errors
```

| 대상 | detail | update | delete | 비고 |
|---|:--:|:--:|:--:|---|
| Order | **200** | (라우트 없음) | (라우트 없음) | 남의 주문 상세를 읽는다 |
| Terminal | **200** | **200** | **200** | 읽기·쓰기·삭제 전부 |
| Device | **200** | **DB 쓰기 도달** | **200** | §3 — 하드 삭제까지 |
| ChecklistSetting | (라우트 없음) | **DB 쓰기 도달** | **200** | |
| SurveillanceProfile | **200** | **200** | **200** | |
| ReportTemplate | **200** | **200** | **200** | |
| StreamMonitor · Dashboard · HandoverDocument | (라우트 없음) | (없음) | (없음) | list 는 통과 |
| DetectionEvent | HTTP 표면 미구현 (W2-2) | — | — | ORM 은 통과 |

* **list 8/8 통과**가 중요하다 — 목록은 이미 좁혀져 있다. 뚫린 것은 **단건 경로(IDOR)** 다.
  즉 "화면에 안 보이니 안전하다"가 거짓임을 이 표가 보여 준다.
* `test_null_created_by_is_not_globally_visible` **실패** — W0-13(백필)의 대상. D-209 가
  예고한 그대로이고, 실패가 산출물이다.
* 레지스트리 시험 2건 실패는 **P-LOCAL-3**(미결) 이다 — `is_group_isolatable()` 이 dj-core 의
  `group` FK(단수)를 모른다. 판정 함수라 손대지 않았다.

### 2-1. update 2건이 "에러"인 이유 — 더 나쁜 쪽이다

`Device` · `ChecklistSetting` 의 수정은 상태코드가 아니라 **DB 예외**로 끝난다:

```
psycopg2.errors.NotNullViolation: null value in column "active" of relation "devices_device"
DETAIL: Failing row contains (32, null, …, iso-updated, ISO-SN-21, …)
```

읽어야 할 것은 두 가지다. ① tenant-A 의 요청이 **tenant-B 의 행에 UPDATE 를 실행했다**
(권한·소유권 검사를 통과했다). ② 그 UPDATE 는 본문에 없는 필드를 **NULL 로 덮는다** —
막은 것은 애플리케이션이 아니라 **DB 의 NOT NULL 제약**이다.

---

## 3. ★ 교차 테넌트 DELETE 는 실제로 지운다 (별도 실측)

단언은 상태코드에서 먼저 실패하므로 "지워졌는가"는 따로 쟀다.

| 대상 | HTTP | 소유자에게 보이는가 | `deleted` 열 | 판정 |
|---|:--:|:--:|---|---|
| Device | 200 | 아니오 | **행 자체가 없다** | **하드 삭제** |
| ChecklistSetting | 200 | 예 | 타임스탬프 기록 | **소프트 삭제** |
| SurveillanceProfile | 200 | 예 | 타임스탬프 기록 | **소프트 삭제** |
| ReportTemplate | 200 | 예 | 타임스탬프 기록 | **소프트 삭제** |
| Terminal | 200 | 아니오 | `NULL`(행 유지) | 삭제 안 됨 — 200 만 돌려준다 |

> 남의 테넌트 데이터를 **지울 수 있다.** 이것은 조회 누출보다 심각하다 — 되돌릴 수 없거나
> (Device) 소유자가 잃는다. W0-14c(652 확대)의 우선순위를 단건 쓰기 경로로 둬야 하는 근거다.

---

## 4. 면제 대장 — "없어서 건너뜀"을 세는 장치

라우트가 실재하지 않는 시나리오는 `NO_ROUTE` 에 **사유와 함께** 등재했다 (16건).
`NoRouteRegistryTest` 가 ① 사유 없는 등재 ② 개수 증가 ③ 오타(없는 대상·시나리오)를 막는다.

조용히 건너뛰면 "5/5 초록"이 실제 커버리지보다 커 보인다 — `tickets.sha256`(WP-0 EXIT §6-1)과
같은 실패 모양이라 같은 방식으로 막았다.

---

## 5. 하지 않은 것

| 항목 | 왜 |
|---|---|
| 단언·판정 로직 수정 | D-253 이 승인한 것은 배선뿐이다. D-105 그대로 |
| `@expectedFailure` 등록 | 누출을 "예상됨"으로 표시하면 D-249 의 EXIT(누출 0건)가 무의미해진다. **빨간불로 둔다** |
| `is_group_isolatable()` 확장 | **P-LOCAL-3 미결.** 판정 함수다 |
| DetectionEvent 테이블 생성 | W2-1 의 마이그레이션 미적용 상태. ORM 시험은 통과하나 HTTP 표면은 W2-2 |
| 누출 자체의 수정 | **W0-14c(652 확대)** 의 일이다. 이 커밋은 "묻는 것"까지 |

## 6. 재현

```bash
docker exec gx-shell sh -c "cd /app && python manage.py test tests.test_tenant_isolation -v 2 --keepdb"
```
※ `--keepdb` 필수 — dj-core 1.1.6 은 마이그레이션을 0부터 쌓지 못한다 (P-LOCAL-1).
