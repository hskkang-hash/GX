# 사고 ③ — 인증 관문이 **아예 없던** 라우트에서 익명에게 데이터가 나갔다

**발견** 2026-09-08 · **경위** D-343 ① 라우트 인벤토리 전수 중 · **등급** 상급
**상태** 11자리 중 **9자리를 막고 재호출로 확인**했다. 남은 2자리는 §0.4 금지구역이라 못 막았고
**잠금 대장에 등재**했다(DELIVERY_ZONE_ANON_LEAK) · **관련** D-334(사고 ①) · D-335(사고 ②) · D-342

---

## 1. 무엇이 열려 있었나

라우트 **663건** 전수(런타임 ninja 레지스트리) 중, **우리 층에서 인증 콜백이 아예 없는 자리 79건**.

D-334 가 잡은 15자리는 「**주석 처리된** 권한 데코레이터 + `auth=` 없음」이었다. 이번 79건은
그보다 넓다 — **권한 데코레이터가 애초에 없던 자리**까지 포함한다. 같은 병의 더 큰 얼굴이다.

읽어서는 위험을 알 수 없어 **때렸다**(D-210). GET 51자리를 익명으로, 캐시를 우회해(D-341) 호출:

```
authz_blocked      20   @path_permission 이 익명을 떨어뜨렸다 (인증은 없었다 — D-342)
reached_no_data    20   핸들러에 닿았고 404·422·500·301 로 끝났다 (막힌 것이 아니다)
REACHED_WITH_DATA  11   ★ 익명에게 데이터가 나갔다
```

음성 대조 [실측]: D-334 가 막은 세 자리(`days-of-week`·`terminal-types`·`online-drones`)는
같은 실행에서 **401**. 대조가 성했으므로 위 수는 「환경이 인증을 안 건다」가 아니다.

### 데이터가 나간 11자리

| 경로 | 응답 크기 | 나간 것 |
|---|---:|---|
| `/api/delivery/drone-monitoring/drone-status` | 17,416 B | **드론 텔레메트리 전량** (배터리·풍속·좌표) |
| `/api/dronehw/group-management/groups-with-drones` | 16,089 B | **그룹·드론 일련번호** (`Anyang` 그룹 · `D-1763450042251`) |
| `/api/delivery/etri-mock/test-scenarios` | 1,976 B | 시험 시나리오 |
| `/api/devices/battery-types` 외 5 (`gnss-systems`·`image-stabilizations`·`imus`·`motor-types`·`protocols`) | 각 ~145 B | 기준정보 목록 (지금은 빈 배열 — **면이 열려 있었다**) |
| `/api/print-format/print-formats/print-formats` | 148 B | 인쇄양식 목록 |
| `/api/surveillance/video-analysis` | 151 B | 영상분석 목록 |

★ 앞의 둘은 빈 배열이 아니다. **운영 데이터가 그대로 나갔다.**
★ 뒤의 것들이 지금 빈 것은 **개발 DB 가 비어 있기 때문**이지 막혀서가 아니다.
  「빈 배열이 나왔다」를 「안전하다」로 읽으면 착시 ③(모수와 술어)이다.

### 쓰기도 열려 있었다

인쇄양식 컨트롤러는 **익명 POST·PUT·DELETE** 가 열려 있었다:

```
POST   /api/print-format/print-formats
PUT    /api/print-format/print-formats/{print_format_id}
DELETE /api/print-format/print-formats/{print_format_id}
POST   /api/delivery/etri-mock/receive-delivery
POST   /api/delivery/drone-monitoring/drone-status
```

부작용이 있어 **부르지 않았다.** 레지스트리 단언이 그 자리를 지킨다(시험 ①).

---

## 2. ★ 측정기가 먼저 틀렸다 — 봉투와 내용 (D-284 · D-341 의 사촌)

첫 판정에서 **18건**을 「데이터 반출」로 셌다. 그 18건의 HTTP 상태는 200 이었지만 본문은

```json
{"success": false, "message": {"ko": "권한이 거부되었습니다."}, "status_code": 403}
```

**봉투는 200, 내용은 403.** 권한이 막았고 막았다고 본문에 적혀 있는데 봉투에 200 이 찍혀 있다.
판정기가 봉투만 읽었다 — D-284(거짓 성공)의 **측정기 판**이다.

내용을 읽게 고친 뒤에야 진짜 11건이 드러났다. 즉 이 사고의 조사는 **두 번 틀렸다가 맞았다**:

1. 처음: 18건 반출 (**과대** — 권한이 막은 것을 반출로 셌다)
2. 고친 뒤: 11건 반출 (**실측**)

★ 이 200/403 봉투 자체는 **dj-core `core/role/permission.py:508`** 이 만든다.
  §0.4 금지구역이라 우리가 고칠 수 없다 — `blockers.yaml` 에 사유와 함께 올린다.
  **막고 있으므로 유출은 아니다. 그러나 호출자가 상태 코드를 믿으면 성공으로 읽는다.**

---

## 3. 무엇을 했나 — 그리고 **게이트가 내 손을 잡았다**

**익명에게 데이터를 돌려준 것이 확인된 컨트롤러**의, 인증 콜백 없는 라우트 전부에
`JwtOrInboundKey()` 를 붙였다.

| 왜 컨트롤러 단위인가 | `{id}` 자리가 404 를 낸 것은 **막힌 것이 아니라 그 id 가 없었을 뿐**이다 (D-342). 목록만 막고 상세를 열어 두면 사고는 그대로다 |
|---|---|
| 왜 `JwtOrInboundKey` 인가 | 기본값이 **거절**이라 익명을 막으면서 **들어오는 키도 함께 좁힌다**(D-335 · D-343). `CustomJWTAuth()` 였다면 익명은 막히고 **발급된 아무 키나 닿았을 것**이다 |

```
backend/devices/views/{battery_type,gnss_system,image_stabilization,imu,motor_type,protocol}_views.py
                                                          각 2자리 = 12자리
backend/drone_communication/views/group_views.py           2자리
backend/print_format/views.py                              8자리
backend/surveillance/views/surveillance_profile_view.py    2자리
                                                          ─────────
                                                          24자리 (컨트롤러 9개)
```

### ★ 되돌린 것 — `backend/delivery/views/api.py` 4자리

처음에는 **28자리**를 닫았다. 거기에 `backend/delivery/views/api.py` 의 4자리가 있었고,
그 파일은 **§0.4 금지구역**이다(D-207 · 불변 제약).

```
[GATE forbidden-zone] FAIL  backend/delivery/views/api.py — §0.4 금지구역 변경 ← STOP(blocked)
```

**게이트가 내 손을 잡았고, 그것이 맞다** (D-327 — 게이트가 지시보다 위다).
되돌렸다. 그래서 익명에게 데이터를 내던 11자리 중 **2자리는 지금도 열려 있다**:

```
GET /api/delivery/drone-monitoring/drone-status   200 · 17,416 B  ★ 가장 큰 반출이 여기다
GET /api/delivery/etri-mock/test-scenarios        200 ·  1,976 B
```

★ 이것은 **「모른다」가 아니라 「못 한다」**이다. 막는 코드까지 써 봤고 되돌렸다.
  잠금 대장에 해소 절차 셋과 함께 등재했다: `DA-05/blockers.yaml :: DELIVERY_ZONE_ANON_LEAK`.
  **사고를 알면서 두는 것은 나쁘지만, 금지구역에 손을 넣는 것은 더 나쁘다.**

### 사후 확인 [실측 2026-09-08 · 캐시 우회]

```
관문 없는 자리(우리 층)   79 → 55
관문 없는 자리(전체)     128 → 104
들어오는 키 거절          10 →  34
REACHED_WITH_DATA         11 →   2   ★ 남은 2 는 전부 §0.4 금지구역
음성 대조                401 · 401 · 401 (변동 없음)
```

---

## 4. 남은 것 — **닫지 않은 55자리**

D-343 은 「③ 전역 적용은 인벤토리를 보고 내가 범위를 판정한 뒤에 한다」고 못박았다.
그래서 **데이터가 나간 것이 확인된 자리만** 닫았고, 나머지는 **재고 기록만** 남긴다.

| 갈래 | 건수 | 지금 상태 |
|---|---:|---|
| `@path_permission` 활성 (authz 가 막는다) | 24 | 익명 호출이 **전부** 권한에서 떨어졌다 [실측] |
| 아무 관문도 없음 | 31 | GET 은 데이터 없이 404·422·500·301. 그중 **2자리는 반출 중이고 §0.4 다** |

★ 「데이터가 안 나왔다」는 **「안전하다」가 아니다.** 핸들러가 돌았다는 뜻이다.
  이 55자리는 `route_baseline.txt` 에 래칫으로 잠갔다(D-311) — **늘면 게이트가 빨개진다.**
  닫을지 여부는 판정 대상이다.

---

## 5. 재발을 막는 것 (D-286 — 절차는 도구로)

| 도구 | 무엇을 막나 |
|---|---|
| `scripts/probe_route_inventory.py` | 라우트 전수 · 인증 수단 · 키 수용 · 테넌트 범위를 **레지스트리에서** 뜬다 |
| `scripts/probe_authn_gap_calls.py` | 관문 없는 자리를 **호출로** 잰다. 봉투가 아니라 **내용**을 읽는다 |
| `scripts/verify_route_inventory.py` | 대장 밖 라우트 · 코드/대장 불일치 · `open_anonymous` 증가를 exit 1 |
| `backend/tests/test_authn_gap_closed.py` | 24자리의 관문 · 401 · **본문** · 컨트롤러 부작위 (5건) |
| `scripts/verify_cache_bypass.py` | 이 측정이 캐시를 재지 않았음을 시험 파일마다 강제 (D-341) |

---

## 6. 이 사고가 남긴 원칙 하나

**「관문이 없다」와 「관문이 거절한다」는 같은 응답을 낼 수 있다.**
404 · 422 · 500 · 그리고 **200 봉투 안의 403** 까지 — 넷 다 「데이터가 안 나왔다」로 보인다.
그래서 **관문의 유무는 응답이 아니라 레지스트리에서 읽고, 반출 여부는 응답의 내용에서 읽는다.**
둘을 한 곳에서 읽으려 하면 이번처럼 18 과 11 을 오간다.
