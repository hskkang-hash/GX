# W0-14c(1차) — 쓰기 경로 문지기 + **직전 보고 정정**

**실행** 2026-08-24 · **티켓** W0-14 (WP-2) · **환경** 로컬 기동본 · test DB (`--keepdb`)
**앞 문서** `wiring_fix_and_findings.md` (같은 날 W0-14b)

---

## 0. 먼저 — **직전 보고의 누출 수치는 과대했다. 원인은 픽스처 오염이었다**

> W0-14b 보고서(`wiring_fix_and_findings.md` §2·§3)는 다음과 같이 적었다:
> *"detail 5건 200 · update 3건 200 · delete 5건 200 — 그리고 실제로 지워진다.
> Device 는 행 자체가 사라진다."*
>
> **그 판정은 틀렸다.** 원인은 저장소 코드가 아니라 **시험 픽스처**다.
>
> `acting_as()` 는 `get_current_request` 를 두 모듈에서 patch 했지만, dj-core 는 그 함수를
> **자기 모듈에서 import 해 쓴다.** 그래서 저장 시 `created_by` 자동 채움 경로가 덮이지
> 않았고, **직전 HTTP 요청의 사용자(= 공격자 tenant-A)** 가 소유자로 찍혔다.
> 즉 "tenant-B 의 레코드"라고 만든 것이 **실제로는 tenant-A 의 것**이었고,
> 그것을 A 가 읽고 지울 수 있는 것은 **정상**이다.
>
> 증상이 이상했던 것이 단서였다: 같은 엔드포인트가 시험 하나만 돌리면 404, 두 개를
> 돌리면 200 이었다. 첫 시험에서는 스레드 로컬이 비어 있어 소유자가 제대로 B 로 찍혔고,
> HTTP 요청이 한 번 지나간 뒤에는 A 로 찍혔기 때문이다.

### 0-1. 무엇을 고쳤나 (픽스처 4건 · 판정 로직 무변경)

| # | 고친 것 | 왜 |
|---|---|---|
| ① | `acting_as()` 가 **스레드 로컬 자체**를 교체한다 | dj-core 의 `created_by` 자동 채움을 덮는다 |
| ② | 의존 레코드 캐시를 **시험 하나의 수명**으로 (클래스 → 인스턴스) | 롤백된 pk 를 다음 시험이 재사용해 teardown FK 검사가 터졌다 |
| ③ | 의존의 `code` 에 테넌트 접미사 | `code` 는 전역 UNIQUE — A/B 양쪽 의존이 충돌했다 |
| ④ | "삭제됐는가" 판정을 `_base_manager` 로 | `objects` 는 테넌트 필터를 타므로 **"삭제됐다"와 "내게 안 보인다"를 구별하지 못했다** |

④ 는 판정을 **더 엄격하게** 만든다(더 많이 보는 매니저로 사실을 확인한다). 완화가 아니다.

---

## 1. 정정된 실측 — 격리는 HTTP 레벨에서 **버티고 있다**

```
Ran 13 tests — 4 failures · 1 error   (W0-14b 보고 시점: 16 failures · 2 errors)
```

| 시나리오 | 결과 | 판정 |
|---|---|---|
| **list** | 8/8 통과 | 남의 레코드가 목록에 없다 |
| **detail** | Order 만 실패 | Terminal·Device·SurveillanceProfile·ReportTemplate **통과(403/404)** |
| **update** | Terminal 만 실패 | 나머지 통과 |
| **delete** | Terminal 만 실패 | 나머지 통과 |
| **export** | 대상 없음 | — |
| 레지스트리 | 2건 실패 | `dashboard.DashboardPanel` 미등록 + P-LOCAL-3 (둘 다 별건) |

### 1-1. 남은 실패 3건은 **누출이 아니라 응답 계약 위반**이다 (→ W0-18)

| 대상 | HTTP | 실제로 무슨 일이 났나 | 판정 |
|---|---|---|---|
| `Order` 상세 | **500** | 테넌트 필터가 걸러서 `Order.DoesNotExist` → 핸들러가 잡지 않는다 | 격리는 됐다. 500 이 문제다 |
| `Terminal` 수정 | **400** | 본문은 `success:true` · `"Terminal matching query does not exist."` · **변경된 열 0개** | 격리는 됐다. 400 + success:true 가 문제다 |
| `Terminal` 삭제 | **200** | 본문 `"Deleted successfully"` · **행은 그대로 있고 `deleted` 는 NULL** | 격리는 됐다. **성공했다고 거짓말한다** |

> 셋 다 "막혔지만 그 사실을 정직하게 말하지 않는다". 특히 Terminal 삭제는 **하지 않은 일을
> 했다고 응답**한다 — 감사·운영 관점에서 조용한 누출보다 나쁠 수 있다. W0-18 의 입력이다.

## 2. 무엇을 넣었나 — 쓰기 경로 문지기 (`assert_scoped`)

`common/tenant_filters.assert_scoped(model, pks, user)` 를 신설하고 **4개 앱 8개 핸들러**에 걸었다.

| 앱 | 핸들러 | 결과 |
|---|---|---|
| `report_template` | `PUT /{id}` · `DELETE /delete/{ids}` | 남의 것 → **404** |
| `checklist_setting` | `PUT /{id}` · `DELETE /delete/{ids}` | 남의 것 → **404** |
| `devices` | `POST /{id}` · `DELETE delete/{ids}` | 남의 것 → **404** |
| `surveillance` | `PUT /{profile_id}` · `DELETE /{profile_id}` | 남의 것 → **404** |

### 2-1. ★ 문지기는 `try` **밖**에 둔다 — 이것이 핵심이다

처음에는 `try` 안에 넣었고, **아무것도 막지 못했다.** 이 핸들러들의 `except` 가 모든 예외를
잡아 **본문에 404 를 적고 HTTP 200 으로** 내보내기 때문이다. 문지기를 `try` 안에 두면
차단이 200 으로 바뀐다. 밖으로 옮기자 404 가 나갔다.

> 이 저장소에서 **예외를 삼켜 200 으로 바꾸는 관례**가 얼마나 위험한지 보여 준다 —
> 보안 검사 하나를 무력화하는 데 `try:` 한 줄이면 됐다. W0-18 의 후처리 계층이 필요한 이유다.

### 2-2. 문지기는 `_base_manager` 로 소유를 확인한다

`objects` 로 물으면 dj-core 의 필터(그 안에 `created_by__isnull=True` OR 절이 있다)를 타고,
"내 것이 아닌데 통과"와 "없어서 통과"가 섞인다. 소유 판정은 필터를 거치지 않은 사실 위에서 한다.

### 2-3. 소유의 정의 — `group` 열이 없는 모델

`ReportTemplate`·`Device` 는 `group` 열이 없다(`KNOWN_UNISOLATED`). 이 경우 소유는
**생성자의 소속**(`created_by__userprofilelink__group`)으로 본다 — 이 저장소가 이미 그렇게
쓰고 있다(`report_template/views.py` 의 기본값 조회). `_guess_group_lookup` 에 그 경로를 넣었다.

## 3. 하지 않은 것

| 항목 | 왜 |
|---|---|
| `terminals` · `orders` · `delivery` 문지기 | **§0.4 리팩터링 금지구역**(269 파일). 남은 실패 3건이 전부 여기다 → `P-W0-14-4` 로 적재 |
| 652 라우트 전면 확대 | **D-254** 가 W0-13 백필을 앞에 뒀고, 그 백필은 `P-W0-13-1`(reversible=false) 대기 중이다 |
| `DashboardPanel` 레지스트리 등록 | 등록하면 라우트가 없어 `NO_ROUTE` 가 4건 늘고 증가금지 래칫을 풀어야 한다. 별건으로 보고 |
| 상태코드 정정(500·400·200) | **W0-18** 의 범위다. 여기서 고치면 두 번 고친다 |

## 4. 재현

```bash
docker exec gx-shell sh -c "cd /app && python manage.py test tests.test_tenant_isolation -v 2 --keepdb"
# → Ran 13 · 4 failures(Terminal 2 · 레지스트리 2) · 1 error(Order 상세 500)
```

## 5. 교훈 하나를 남긴다

**시험이 빨간불이라고 해서 코드가 틀린 것은 아니다.** 이번에 그 둘을 가른 것은
"같은 요청이 실행 순서에 따라 다른 답을 낸다"는 이상 신호였다. 그 신호를 쫓아가지 않고
빨간불을 그대로 보고했다면, 존재하지 않는 누출 13건을 근거로 다음 판단이 쌓였을 것이다.
