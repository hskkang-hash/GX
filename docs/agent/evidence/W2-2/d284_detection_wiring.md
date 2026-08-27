# D-284 이행 — 검출이 버려지지 않는다 · 거짓 성공 조사 39건

**작성** 2026-08-29 · 대상 W2-2 · 근거 D-284 · D-281 · D-271 · D-277

---

## 1. 한 줄 요약

**검출이 없던 게 아니라 받아서 버리고 있었다.** 배선만으로 살아났고, 그 배선을 재는 시험이
**커널 결함 하나를 함께 잡았다.**

```
시험   143 passed · 0 skipped    (직전 118 · 0 · 그 앞 111 · 1 skipped)
       술어 = pytest tests -q --nomigrations -p no:randomly, 모수 = tests/ 전수
게이트 verify_tenant_scope · layers · classification · kernel_map · timeout ·
       migrations(컨테이너) · scan_silent_success(self-test) 전건 exit 0
```

---

## 2. 호출처 ① — `grpc_client` 가 검출을 버리던 자리 (D-284 (1))

### 무엇이 있었나

`FrameWithDetections{frame, detections}` 를 받아 `.frame.image_data` 만 디코딩하고
`.detections` 를 **통째로 버렸다.** metadata 에도 안 실었다. 그 결과
`DetectionEvent` 는 **정의 1건 · 사용 0건**이었다.

### 무엇을 했나

| 자리 | 한 일 |
|---|---|
| `grpc_client.process_frame_batch` | `detections` 를 metadata 에 싣는다 (`detections` · `detection_count`) |
| `grpc_client._detections_to_dicts` | proto(픽셀 정수) → 계약(**정규화 0.0~1.0**) |
| `detection_event_bridge.publish_detections` | 라벨 → `event_type` → K1 `record_detection` |
| `grpc_dual_stream_service._publish_detection_events` | **실호출 경로**에서 배선을 부른다 |

**반환 시그니처를 바꾸지 않았다.** `(frames, metadata)` 를 받는 호출처가 세 곳이고,
튜플을 셋으로 늘리면 그 셋이 한꺼번에 깨진다. 더하는 것은 하위 호환이다.

### 세 가지를 갈라 두었다 — 갈라 두지 않으면 다음에 또 못 본다

1. **검출 0건 ≠ 배선 없음.** 전에는 둘 다 "metadata 에 아무것도 없음"이었다.
   이제 `detections` 키는 **항상 있고** 값이 빈 것뿐이다. 키가 사라지면
   `_publish_detection_events` 가 **ERROR 로그**를 낸다 (D-284 회귀 탐지).
2. **bbox 를 모르는 것 ≠ bbox 가 0.** 프레임 크기를 모르면 `bbox=None` 이고
   `bbox_unavailable_reason` 에 사유가 남는다. 0 은 "왼쪽 위 모서리의 점"이라는
   **뜻이 있는 값**이라 모르는 것을 0 으로 채우면 아는 척이 된다.
3. **옮길 줄 모르는 라벨 ≠ 검출 없음.** `unmapped_labels` 로 **세어서 돌려준다.**

### ★ 아직 재지 못한 것 — AI 라벨 어휘

**AI 서버가 실제로 어떤 라벨 문자열을 쓰는지 모른다.** `AI_GRPC_URL` 이 이 PC 에서
닿지 않는다(`media-ai.invalid`). 그래서 `LABEL_TO_EVENT_TYPE` 에는 **계약 열거값과
글자가 같은 것만** 넣었다. `"car" → vehicle` 은 그럴듯하지만 재지 않았고,
재지 않은 것을 표에 적으면 그 표가 근거처럼 읽힌다 (D-280 · D-273).

그 밖의 라벨은 버리지 않고 센다 — **그 목록이 곧 표를 늘릴 근거다.**

---

## 3. ★ 배선 시험이 커널 결함을 잡았다 (F-04 위반)

`test_dedup_is_the_kernels_job_not_the_bridges` 를 쓰자 빨간불이 났다.

```
같은 배치에 같은 검출 3연발 → 이벤트 1건으로 접힘.  그런데 should_notify 가 **세 번 다 참**
```

**원인.** 알림 질의가 `.exclude(pk=event.pk)` 로 자기 자신을 뺀다. 그런데 **접히면
`event` 는 기존 이벤트**이므로, 유일한 "5분 안의 이전 것"이 매번 제외됐다.
K2 가 같은 이벤트로 여러 번 알림을 보내게 되고, 그것이 F-04(동일 이벤트 5분 내 중복 알림
0건) 위반이다.

**왜 기존 시험이 못 잡았나.** `test_event_count_and_notify_count_differ` 는 30초 간격이라
**매번 새 이벤트**였다. 접힘 갈래를 한 번도 지나가지 않았다 —
시나리오가 초록이어도 갈래가 안 덮이면 못 잡는다. **착시 ②(D-262)의 작은 판이다.**

**교정.** `should_notify = (not folded) and (not prior_exists)`.
접혔다는 것은 **같은 이벤트**라는 뜻이므로 알리지 않는다.
이벤트는 여전히 남는다(`last_seen_at` 갱신) — **U1 의 오탐률 분모는 그대로다**(두 창 유지).

**양성 대조.** 고침을 되돌리자 `test_folded_records_do_not_notify_again` 이 빨개졌고
(1 failed / 21 passed), 복구하니 22 passed. 회귀 시험을 **커널 시험 파일에** 고정했다 —
배선 시험만 갖고 있으면 커널을 따로 쓰는 다음 사람이 같은 것을 다시 깬다.

---

## 4. 호출처 ② — `detect_and_save` (D-284 (2))

### 지시서의 전제를 한 가지 정정합니다

D-284 는 *"독스트링은 '저장한다'인데 본문이 비어 있고 True 를 낸다"* 고 적었습니다.
**앞부분은 맞고, "저장이 안 된다"는 틀립니다.** 되짚어 보니:

* `VideoAnalysis` 행은 `detect_media` 안의 `create_video_analysis_records()` 가
  `threading.Timer(total_frames / 20)` 로 **배경 스레드에서** 만든다.
* MinIO 의 JSON 은 우리가 쓰지 않는다 — AI 서비스가 쓰고 `callback_url` 로 알려 준다.

그래서 **`NotImplementedError` 를 던지지 않았습니다.** 없는 구현을 있다고 적는 것만큼,
있는 구현을 없다고 적는 것도 다음 사람을 헤매게 합니다. 대신 **함수가 하는 일을 정확히
적는 쪽**을 골랐고, 죽은 코드(`created_records = []`)를 걷어냈습니다.

### 그 자리에서 진짜 "조용한 성공"을 하나 찾았습니다

```python
results = response_data.get('results', [])     # ← 상류 오류를 **빈 목록**으로 바꾼다
...
return True, results                           # ← 무조건 True
```

뷰에는 `if not success: return 400` 이 있었지만 **그 400 에는 닿을 수 없었습니다.**
상류가 오류를 돌려줘도 이 API 는 200 "Detection completed successfully" 를 냈습니다.

→ 모양 불일치를 센티넬(`_UPSTREAM_SHAPE_MISMATCH`)로 갈라 400 이 닿게 했습니다.
`None`/`[]` 를 쓰지 않은 이유: 그 둘은 **"검출 0건"과 글자가 같습니다.**

### K1 이벤트로는 잇지 않았습니다 — 판단을 구합니다

이 경로의 결과 모양(업로드 영상 분석 JSON)을 **재지 못했습니다.**
AI 분석 서비스가 이 PC 에서 닿지 않습니다(`ai-analysis.invalid`).
추정으로 파서를 쓰면 2027.2 에 전부 재작업이 됩니다 (D-280 · D-273 초안 검증 원칙).

**그래서 ⑥ "K1 done" 을 제 판단으로 선언하지 않습니다.** 호출처 ① 은 이어졌고
이중 AC 는 green 이지만, ② 를 잇는 것이 W2-2 범위인지가 미정입니다.

---

## 5. 거짓 성공 전수 조사 (D-284 (3)) — 39건

`scripts/scan_silent_success.py` · 결과: `docs/agent/evidence/W2-2/silent_success_survey.{txt,json}`

```
훑은 파일 514개 (모수 = backend/**/*.py 전수, 제외 = migrations · __pycache__ · tests · .venv · node_modules)
후보 39건 — high 29 · medium 6 · low 4 · 판정불가 0
```

**이것은 판정이 아니라 목록입니다.** 게이트로 만들면 래칫밖에 못 걸고, 무엇이 "빈 본문"
인지는 사람이 봐야 갈립니다. 기계는 읽을 순서를 정해 줄 뿐입니다.

### ★ 조사기가 처음에 실제 과녁을 놓쳤습니다 (착시 ④ 재현)

첫 술어는 **"빈 본문"** 하나였습니다. 합성 대조 7건은 전부 통과했는데,
**이 조사를 하게 만든 바로 그 함수를 0건으로 셌습니다.** 고치기 전 `detect_and_save` 는
`results = detect_media(d)` 라는 실질 작업이 있어서 "빈 본문"이 아니었기 때문입니다.

진짜 모양은 **"실패를 낼 길이 없다"** 였습니다 — `return True, results`.

그래서 술어를 둘로 넓혔습니다:

| 모양 | 뜻 |
|---|---|
| ① 빈 본문 | 실질 작업을 걷어내면 `return True` / `None` / 암묵 None 만 남는다 |
| ② **무조건 성공** | 함수의 **모든** return 이 성공 상수를 낸다 → 부르는 쪽의 실패 갈래가 죽은 코드 |

등급도 **이름**을 보게 했습니다. `save_log_file_to_minio(data): pass` 는 독스트링이 없어
low 로 떨어졌지만, 부르는 사람이 읽는 것은 **이름**입니다.

대조 10건 전부 통과하고, **고치기 전 `detect_and_save` 를 high 로 잡습니다**
(`test_the_original_target_is_caught` 가 이것을 고정합니다).

### 눈에 띄는 것 (사람이 읽을 순서)

| 등급 | 자리 | 왜 |
|---|---|---|
| high | `media_data_download_service.py:197 send_progress()` | 본문이 **독스트링뿐**인데 아래에서 **실제로 불린다.** 진행률 알림이 조용히 아무것도 안 한다 |
| high | `flight_log_service.py:714 save_log_file_to_minio()` | 본문이 `pass`. 이름이 저장을 약속한다 |
| high | `task_status_service.py:128 update_status()` · 그 밖 27건 | 무조건 성공 — 실패를 낼 길이 없다 |

**이 39건을 고치지 않았습니다.** D-284 (3) 이 요구한 것은 **목록**이고, 39건을 한 커밋에서
고치는 것은 살아 있는 경로의 동작을 39곳에서 바꾸는 일입니다. 순서와 범위는 판정 사안입니다.

---

## 6. 적재한 판정 2건 (D-213 — STOP 대신 적재하고 전진)

| id | 무엇 | 잠정 |
|---|---|---|
| **P-W2-2-1** | AI 라벨 → `event_type` → `severity` 를 잇는 규칙이 **어느 문서에도 없다** | A 잠정 적용 (fire·smoke·sos=critical / intrusion=warning / person·vehicle=info) · 문턱값은 **0.0** |
| **P-W2-2-2** | `VideoAnalysis` 행이 **검출 실패와 무관하게** 만들어진다 (Timer 가 post 앞줄) | **기본값 없음** — 살아 있는 경로의 동작 변경이라 판정이 먼저다 |

문턱값을 0.0 으로 둔 이유: **"일단 0.5" 가 들어오는 순간 오탐률은 문턱값이 만든 수가 된다.**
실측 분포를 갖는 K6 가 정하는 것이 맞습니다.

---

## 7. 아직 모르는 것 / 안 한 것 — 지우지 않는다

1. **스냅샷은 붙였지만 실호출로 한 장도 못 올렸다.** `detection_snapshot.upload_snapshot`
   을 배선에 이었고(종류당 1장), 성공/실패 양쪽을 시험 5건으로 고정했다. 그러나 이 PC 에서
   MinIO 는 닿지 않는다(`minio.invalid`) — **실제로 올라간 것은 0장이다.**
   못 올리면 `snapshot_path` 는 **빈 문자열**이고 사유가 로그와 결과 양쪽에 남는다.
   **가짜 경로를 넣지 않았다** — 있지도 않은 객체를 가리키는 경로는 "저장했다"는
   거짓말이고, 그것이 D-284 가 이름 붙인 조용한 성공이다.
   타임아웃·재시도 상한은 `MinioClient` 가 이미 건 것을 탄다(C-3.3 — 두 벌을 두지 않는다).
   ※ 알려진 낭비: 접힐지 미리 알 수 없어 올린 뒤 접히면 그 1장이 쓰이지 않는다.
     **숨기지 않고 센다**(`snapshots_discarded`). 수가 커지면 그때 최적화의 근거가 된다.
2. **AI 라벨 어휘를 재지 못했다** (§2). 표는 글자가 같은 6종뿐이다.
3. **호출처 ② 를 K1 에 잇지 않았다** (§4). 응답 모양을 재지 못했다.
4. **실호출로 검출→이벤트를 한 번도 통과시키지 못했다.** AI 서버가 없다.
   지금 있는 것은 proto 모양의 가짜를 먹인 시험이다 — 배선은 재지만 **AI 와의 계약은
   못 잰다.** AI 서버가 닿는 날 `unmapped_labels` 로그가 그 계약을 알려 줄 것이다.
5. **F-05 p95 500ms 는 여전히 못 잰다.** 부하도 데이터도 없다.
6. **거짓 성공 39건을 고치지 않았다** (§5). 목록까지가 D-284 (3) 이다.

---

## 8. 재현

```bash
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  PYTHONPATH=/app python -m pytest tests/test_w2_2_detection_wiring.py \
  tests/test_k1_event_kernel.py -q --nomigrations -p no:randomly'

python scripts/scan_silent_success.py            # 조사 (자기 시험을 먼저 돌린다)
python scripts/scan_silent_success.py --self-test

# 양성 대조 — 커널 고침을 되돌리면 빨간가
#   services.py 의 should_notify=(not folded) and (not prior_exists)
#   → should_notify=not prior_exists 로 바꾸고 test_k1_event_kernel.py 실행
```
