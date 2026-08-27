# K1 이벤트 커널 착수 — 실측 (D-275 EXIT 승인 후 · 지시 §5⑥)

**측정** 2026-08-28 · **done 조건** 이중 AC 테스트 먼저 · **호출처 2곳 확인**
**커널** `backend/kernels/k1_event/` · **시험** `backend/tests/test_k1_event_kernel.py`

---

## 0. 첫 줄 — 분모와 술어를 함께 적는다 (D-274)

```
이중 AC 시험     14/14 green  (대상 = F-04 × U1 4건 · F-05 × U1 3건 · 격리 7건,
                              술어 = pytest tests/test_k1_event_kernel.py --nomigrations)
전체 시험        111 passed · 1 skipped   (직전 97 + 신설 14. skip 은 컨테이너에
                                          scripts/ 가 마운트되지 않아 계층 게이트를 못 부른 것)
공개 면          6/6 실재     (술어 = DA-04 §2 K1 표의 "공개 면" 열과 이름 대조.
                              단 subscribe 는 **이름만** — 부르면 NotImplementedYet)
게이트           3종 exit 0   (verify_tenant_scope · verify_layers · verify_classification)
호출처           2/2 확인     (술어 = 파일·행·프로토 실측. **둘 다 지금은 이벤트를 못 만든다**)
마이그레이션     0 → 1 생성   (술어 = makemigrations --check --dry-run exit 0)
```

**초록이 아닌 수가 셋 있다** — `subscribe` 미구현 · 호출처 2곳 미배선 · 마이그레이션 **미적용**.
지우지 않고 §4·§5 에 적는다.

---

## 1. 시험이 구현보다 먼저였다 — 그 빨간불이 증거다

지시 §5⑥: *"K1 이벤트 커널 착수 — **이중 AC 테스트 먼저**"*.

`backend/tests/test_k1_event_kernel.py` 를 먼저 쓰고 커널 없이 돌렸다:

```
1 failed, 1 skipped, 13 errors in 5.83s
E   ModuleNotFoundError: No module named 'kernels'
```
(원자료: `red_before_impl.txt`)

**구현이 없을 때 빨갛지 않은 시험은 구현이 있을 때도 초록의 뜻이 없다** (D-277 착시 ④).
그 다음 커널을 세우고 다시 돌려 `14 passed, 1 skipped` 가 됐다.

---

## 2. ★ 이중 AC 가 충돌하는 지점 — 두 창을 가른다

DA-04 §2 K1 이 이미 해법을 적어 두었고, 이 커널의 설계 전부가 그 한 문장에서 나온다:

> 중복 억제는 **기록 단계**(10초·이벤트)와 **알림 단계**(5분·K2)를 나눈다.
> **이벤트를 접으면 U1 의 오탐률 분모가 거짓이 되므로 이벤트는 남기고 알림만 접는다.**

| AC | 요구 | 이 커널이 지키는 방식 |
|---|---|---|
| **F-04** 계약 | 동일 이벤트 5분 내 중복 **알림** 0건 | `NOTIFY_WINDOW = 5분` → `RecordResult.should_notify` |
| **U1** 상품 | 오탐률 **수치화** | `DEDUP_WINDOW = 10초` → 이벤트는 남는다. 분모가 산다 |

`record_detection` 은 `created`(10초 창)와 `should_notify`(5분 창)를 **따로** 낸다.
둘을 하나로 합치고 싶어지는 순간이 곧 한쪽 AC 를 깨뜨리는 순간이다.

### 그것을 시험으로 고정했다 — 이 파일에서 가장 중요한 단언

`test_event_count_and_notify_count_differ_in_five_minutes`
5분 동안 30초 간격 5회 검출 →

```
이벤트  5건   ← U1 오탐률 분모가 살아 있다
알림    1건   ← F-04 "5분 내 중복 알림 0건"
```

**둘이 같아지면 실패한다.** 5로 같아지면 F-04 위반, 1로 같아지면 U1 의 분모가 거짓이 된다.

음성 대조도 함께 둔다 — `test_records_beyond_10s_make_a_new_event`.
"10초 안이면 접힌다"만 시험하면 **전부 접는 구현**도 통과한다.

---

## 3. ★ 호출처 2곳 확인 — done 조건 (지시 §5⑥)

**둘 다 지금은 이벤트를 만들지 못한다.** 그리고 못 만드는 이유가 서로 다르다.

### ① `stream_monitors/services/grpc_client.py:147-152` — **받아서 버린다**

proto 를 실측했다 (컨테이너에서 디스크립터 로드):

```
Detection            :: x, y, width, height, label, confidence, color
FrameWithDetections  :: frame, detections
ProcessedFrameBatch  :: processed_frames, batch_id, processing_time_ms, timestamp
```

**AI 서버는 검출 결과를 이미 돌려주고 있다.** 그런데 클라이언트는:

```python
for frame_with_detections in response.processed_frames:
    nparr = np.frombuffer(frame_with_detections.frame.image_data, np.uint8)
    processed_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed_frames.append(processed_img)          # ← 이미지만 남기고
                                                    # frame_with_detections.detections 를 버린다
```

`metadata` 에도 안 싣는다. `grpc_dual_stream_service.py:401` 은 `processed_frames` 만 소비한다.

> **검출이 없는 게 아니라 받아서 버리고 있다.** 이것이 W2-2 의 핵심이고,
> 이 사실을 모르면 "AI 서버가 검출을 안 준다"로 잘못 진단하게 된다.

### ② `media_data/services/media_data_detect_service.py:233` — **독스트링과 본문이 다르다**

```python
def detect_and_save(data: MediaDetectInSchema):
    """... - Create VideoAnalysis record with video_path and analysis_path"""
    results = MediaDataDetectService.detect_media(data)
    created_records = []          # 만들고 쓰지 않는다
    return True, results          # 저장하지 않고 True 를 낸다
```

부르는 쪽은 **저장된 줄 안다.** `True` 가 돌아오기 때문이다.
K1 의 `exceptions.NotImplementedYet` 이 막으려는 것이 정확히 이 모양이다 —
**없는 것은 없다고 말한다.**

### 대조 — `DetectionEvent` 사용처 전수

```
$ grep -rn "DetectionEvent" backend --include=*.py | grep -v "^backend/tests/"
backend/stream_monitors/models.py:125:class DetectionEvent(BaseModelWithGroup):
```

**정의 1건, 사용 0건.** 모델은 껍데기였다. DA-04 의 "구현 일부"가 이 상태다.

---

## 4. ★ 모델은 있는데 **표가 없었다**

W2-1 의 verify 명령이 `makemigrations --check --dry-run` 인데, 실제로 돌려 보니:

```
Migrations for 'stream_monitors':
  stream_monitors/migrations/0016_detectionevent.py
    + Create model DetectionEvent
EXIT=1
```

DB 도 확인했다:

```
information_schema 에서 '%detection%' 표: []
stream_monitors 적용 마이그레이션: 14건
```

**표가 없다.** 시험이 초록이던 이유는 `--nomigrations` 가 모델 선언에서 테스트 DB 를
직접 만들기 때문이다(D-273) — **시험이 도는 것과 스키마가 맞는 것은 다르다**(P-LOCAL-4).

→ `0016_detectionevent` 를 **생성**했다. `--check` 가 exit 0 이 됐다.
→ ⚠ **적용하지 않았다.** 운영 DB 적용은 별건이고 D-269(스냅샷) · D-270(쓰기 안전 3원칙) ·
  "운영 DB 직접 변경 금지"가 걸린다. **표가 없는 상태에서 배선하면 첫 검출에서 죽는다 —
  적용이 배선보다 먼저다.**

### 부수 실측 — 소유 필드는 `group` FK 다

생성된 마이그레이션이 `('group', ForeignKey(... to='user.usergroup'))` 를 냈다.
저장소 소스의 `BaseModelWithGroup` 은 `groups` **M2M** 을 선언하는데
**실행 중인 dj-core 는 `group` FK** 를 준다. D-271 이 술어를 `groups ∪ group` 으로 넓힌
근거가 이것이고, W0-13 백필 25,296행이 채운 것이 바로 그 `group_id` 다.

커널은 어느 쪽도 하드코딩하지 않는다 — `_owner_field()` 가 런타임에 고른다.
한쪽을 박으면 다른 환경에서 **시험이 조용히 판정 불가**가 된다.

---

## 5. ★ 게이트가 첫 커널 커밋을 막았다 — 그리고 그것이 옳았다

어제 세운 C-3.1 게이트(`verify_tenant_scope`)가 K1 공개 함수 **6건 전부를 반려**했다.

```
[SCOPE] 위반 6건 — 멈춘다
  · services.py:record_detection: 커널 공개 함수인데 @tenant_scoped 도 없고 PUBLIC 등재도 없다
  · ... (query_events · get_event · review_event · close_event · subscribe)
```

**게이트를 커널 0줄일 때 세운 이유가 이것이다** — 빚이 태어나기 전에 잡힌다.

### 문제: 데코레이터가 커널에서는 작동하지 않는다

`tenant_scoped` 는 인자에서 `request` 를 찾고 **못 찾으면 그냥 통과시킨다**
(`_find_request` → `None` → `_check` 생략). 커널 함수에는 `request` 가 없다.
붙이면 **표식만 남고 아무것도 안 막는다** — 데코레이터 466/466 부착을 완결로 착각했던
**착시 ①(D-249)이 커널에서 재현**된다.

### 해결: 통과 형태를 하나 **더한다** — 무르게가 아니라 높이는 쪽으로

`common.tenant_filters` 의 **진짜 문지기**가 호출 그래프에 있으면 인정한다.
문지기 목록은 `common.tenant_tripwire.GATEKEEPER_CALLS` **한 벌을 공유**한다 —
두 벌을 두면 "라우트에서는 문지기인데 커널에서는 아닌 것"이 생기고 그 어긋남은 아무도 못 본다.

```
[SCOPE] 커널 공개 함수 — @tenant_scoped 0개 · 문지기 호출 4개 · PUBLIC 2개
  G  query_events   — 문지기: filter_by_group_field
  G  get_event      — 문지기: assert_scoped, get_scoped_or_404
  G  review_event   — 문지기: assert_scoped
  G  close_event    — 문지기: assert_scoped
  P  record_detection — PUBLIC: 테넌트 데이터를 읽지 않는다(파이프라인 호출·id/bool 만 반환).
                        소유는 스트림에서 물려받는다. 시험 근거 2건 첨부
  P  subscribe        — PUBLIC: 구현 없음. 부르면 NotImplementedYet
```

**D-105 저촉 아님**: 표식만으로는 부족해졌으므로 요구 수준이 **올라갔다.**
다만 C-3.1 문언과 다른 이행이므로 임의로 정하지 않고 **`P-K1-1`** 로 적재했다 (D-213).

**양성 대조** — `query_events` 에서 문지기 한 줄을 빼자 게이트가 **exit 1**.
되돌리자 다시 exit 0. **탈출구는 등재부를 고치는 것이 아니라 문지기를 다는 것이다.**

---

## 6. 커널이 지키는 다른 계약들

| 계약 | 어디서 | 시험 |
|---|---|---|
| 남의 것이면 **404** (200+빈 응답 금지 · W0-18) | `get_event` · `review_event` · `close_event` | `test_get_event_of_other_tenant_is_404_not_empty_200` |
| **기각은 삭제가 아니다** — 지우면 오탐률 분자가 사라진다 | `review_event` | `test_rejected_event_is_not_deleted` |
| 필터는 **서버에서** — 클라이언트 필터는 클릭을 늘린다 (U1 3클릭) | `query_events` | `test_query_filters_by_type_severity_and_period_on_the_server` |
| `objects` 가 아니라 `_base_manager` (§0.4 OR 절 회피) | 전건 | `test_positive_control_own_event_is_found` |
| 모델을 밖으로 내보내지 않는다 (DA-04 §1-4) | `schemas.EventView` | `verify_layers.py` exit 0 |
| 소유를 **스트림에서 물려받는다** | `_inherit_owner` | `test_a_different_stream_is_never_folded` |

### ★ 양성 대조를 먼저 둔다 (D-277)

`KernelTenantScopeTest.test_positive_control_own_event_is_found` 이 다른 격리 시험들보다
먼저 온다. **"남의 것이 안 보인다"만 시험하면 아무것도 안 보이는 구현도 통과한다** —
WP-2 EXIT §5-2 의 목록 5종이 정확히 그 상태였다(통과가 아니라 판정 불가).

---

## 7. 아직 모르는 것 / 안 한 것 — 지우지 않는다

1. **F-05 의 p95 500ms 를 재지 못했다.** 부하도 데이터도 없다. 1건짜리 픽스처의 응답
   시간으로 p95 를 말하는 것은 모수 없는 초록이다(D-271). 대신 지금 잴 수 있는 것을 쟀다 —
   **N+1 없음**(행이 늘어도 쿼리 수가 그대로). p95 는 W2-3 화면이 서고 실데이터가 쌓인 뒤.
   ※ 쿼리 수를 **고정값으로 단언하지 않았다.** 그러면 고정 비용이 하나 늘 때마다 시험이
     깨지고, 깨진 시험은 숫자만 올려서 고쳐진다.
2. **`subscribe`(F-05 Webhook)는 이름만 있다.** 서명키 보관(D-204)·재시도 정책(W0-17)·
   구독 자체의 테넌트 소유 판정이 선행이다. 부르면 `NotImplementedYet` 을 던진다 —
   조용히 `None` 을 돌려주지 않는다.
3. **호출처 2곳이 아직 커널에 안 이어졌다.** W2-2 본체다. 선행은 마이그레이션 적용.
4. **마이그레이션을 적용하지 않았다.** §4 참조.
5. **OpenAPI 노출이 없다.** F-05 는 "OpenAPI 제공"을 요구한다. 커널은 L3 이고 HTTP 표면은
   App/라우트의 몫이라 별건으로 남긴다 — 라우트를 만드는 순간 **신규 경로 트립와이어**
   (D-275 §5-1)가 문지기를 요구한다. 그것이 정상이다.

---

## 8. 재현

```bash
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  PYTHONPATH=/app python -m pytest tests/test_k1_event_kernel.py -q --nomigrations -p no:randomly'
python scripts/verify_tenant_scope.py --list     # 커널 공개 함수 판정 6건
python scripts/verify_layers.py                  # 계층 위반 0
```
