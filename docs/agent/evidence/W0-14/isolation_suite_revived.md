# 격리 시험 5시나리오 기동 — D-250 픽스처 승인 적용 결과

**실행** 2026-08-22 · **결정** D-250(P-LOCAL-2 옵션 A 승인) · **티켓** W0-14 (WP-2)
**변경** `tests/test_tenant_isolation.py` `_make_user()` 에 `email=f"{username}@test.invalid"` **한 줄**
**판정 로직은 한 글자도 바뀌지 않았다.**

---

## 0. 판정

> **시험은 살아났고, 빨간불이 켜졌다.** D-250 이 예상한 그대로다.
> `0/5 실행` → **10건 실행 · 1건 ok · 9 failures · 24 errors**.
> 다만 **실패의 대부분은 누출이 아니라 시험 배선 결함**이다 (§2). 그것을 고치는 것이 W0-14 의 다음 작업이다.

---

## 1. 무엇이 막고 있었나

```
CoreUser.email 은 dj-core 에서 UNIQUE 다.
_make_user() 가 email 을 주지 않아 두 사용자가 모두 email='' → user_coreuser_email_key 위반
→ setUpTestData 단계에서 죽는다 → ORM·API 시험 5시나리오가 **한 번도 실행된 적이 없다**
```
운영 DB 에서는 이 제약 때문에 **email 이 빈 사용자가 최대 1명만 존재할 수 있다**
(`review/LOCAL_BRINGUP_결과.md` §182). 즉 픽스처가 운영 제약을 위반하고 있었다.

## 2. 실행 결과 — 실패를 성격별로 가른다

| 성격 | 건수 | 무엇 | 이것이 뜻하는 것 |
|---|---:|---|---|
| **시험 배선 결함** | 4 | `Target.api_base` 가 실재하지 않는 경로 — `/api/terminals/` `/api/stream-monitors/` `/api/dashboard/` `/api/devices/` 가 **404** | 시험이 애초에 실제 라우트를 부른 적이 없다 |
| **인증 배선 결함** | 1 | ReportTemplate — 응답 **401** | 시험 클라이언트의 토큰 부착이 안 된다 |
| **픽스처 부족** | 24(errors) | `Order.recipient_address_id` NOT NULL 등 필수 FK 미충족 (Order·ChecklistSetting·SurveillanceProfile·HandoverDocument·DetectionEvent) | 대상 모델의 factory_kwargs 가 스키마를 못 따라간다 |
| **정본 대장 미갱신** | 2 | `test_registry_covers_all_isolatable_models` / `test_unisolated_set_has_not_grown` — 격리 메커니즘 없는 모델 5종이 새로 추가됨 (ChecklistSetting·DetectionEvent·StreamMonitor·SurveillanceProfile·Terminal) | **실제 결함**. 부록 A / D-108 |
| **통과** | 1 | `test_export` | — |

### 2-1. 중요 — 이 결과는 "누출 5건"이 아니다

404·401·픽스처 오류는 **격리 판정에 도달하기 전에** 죽은 것이다. 누출 여부를 아직 말하지 못한다.
누출을 실제로 본 것은 HTTP 프로브 쪽이다 (`http_leak_probe.md` · `W0-16/http_role_split_test.md`).

**두 계측이 서로를 보완한다:**

| | 저장소 시험 (`test_tenant_isolation`) | HTTP 프로브 (`probe_tenant_isolation.py`) |
|---|---|---|
| 데이터 | 합성 픽스처 | **실제 테넌트·실제 레코드** |
| 범위 | 모델 12종 × 5시나리오 | 엔드포인트 1종 |
| 지금 상태 | 배선 결함으로 판정 미도달 | **누출 실측 완료** (15·18·1건 → 파일럿 회수 후 1건) |
| 역할 | CI 게이트 (회귀 차단) | 현실 확인 |

D-249 의 EXIT 기준(**누출 0건 · 시나리오 5/5**)은 이 둘을 동시에 요구한다. 어느 하나로는 부족하다.

## 3. 다음 작업 (W0-14 범위)

1. `Target.api_base` 를 실제 라우트로 고친다 — `route_baseline.json`(652개 실측 대장)에 실경로가 있다
2. 시험 클라이언트 인증 배선 (401 해소)
3. `factory_kwargs` 를 스키마 필수 FK 까지 채운다 (Order 외 4종)
4. 격리 메커니즘 없는 5종(ChecklistSetting·DetectionEvent·StreamMonitor·SurveillanceProfile·Terminal) —
   **대장에 넣는 것이 아니라 격리를 붙인다.** 대장을 늘리면 D-108 이 막는 방향으로 간다
5. 그 뒤에야 "5/5 green" 을 말할 수 있다

## 4. 재현

```bash
docker exec gx-shell python manage.py test tests.test_tenant_isolation -v 2 --keepdb
```
※ `--keepdb` 필수 — dj-core 1.1.6 은 마이그레이션을 0부터 쌓지 못한다(P-LOCAL-1).
   test DB 는 운영 스키마 템플릿으로 만든다 (`review/LOCAL_BRINGUP_결과.md` §2-1).
