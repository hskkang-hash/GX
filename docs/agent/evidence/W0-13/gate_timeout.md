# C-3.3 게이트 확대 — 저장소도 외부 의존이다

**작성** 2026-08-27 · **규약** 초효율 코드구현 규약 C-3.3 · §2 (게이트 3종) · **티켓** W0-17 · W0-13
**게이트** `python scripts/verify_timeout.py` · 원자료 `verify_timeout_run.txt`

---

## 0. 결과 한 줄

**외부 호출 78건 중 타임아웃 없는 것 0건.** MinIO 저장소 1건을 실제로 고쳤고,
게이트가 보는 범위를 `requests` 하나에서 **외부 의존 전 계열**로 넓혔다.

---

## 1. ★ 신설이 아니라 확대다 (원칙 1: 중복 0)

규약 §2 는 `verify_timeout.py` 를 **신설**로 적었다. 그런데 이미
`scan_request_timeouts.py`(W0-17)가 **AST 실측**으로 같은 일을 하고 있었다 —
"이름 매칭 금지"도 이미 지키고 있었고, 면제 3건의 사유와
"지시서의 49건은 grep 추정치였다"는 정정 이력까지 붙어 있다.

여기에 판정 로직을 새로 쓰면 **같은 것을 세는 스크립트가 둘**이 된다.
둘은 언젠가 다른 수를 말하고, 그때 어느 쪽이 진실인지 알 수 없게 된다 —
D-227(manifest 유실)이 만든 상태이고, 백필 적용본이 dry-run 을 `import` 한 이유이기도 하다.

**처분**: 엔진(`scan_request_timeouts.py`)을 넓히고,
`verify_timeout.py` 는 **판정 로직이 없는 진입점**으로 두었다.
규약이 부른 이름은 살아 있고, 세는 곳은 하나다.

> 규약 §2 의 이름과 다르게 구현한 유일한 항목이므로 **보고한다.**
> 다른 결론을 원하시면 되돌리기는 쉽다 — 로직을 옮기면 된다. 다만 그 순간 수가 둘이 된다.

---

## 2. 무엇이 게이트 밖에 있었나 — 실측

C-3.3 은 "SDN·기상·위성·**저장소** 등 외부 호출"이라 썼는데, 게이트는 `requests` 만 셌다.
backend 실측:

| 계열 | 파일 수 | 종전 게이트 |
|---|---:|---|
| `requests` | 33 | 본다 |
| `urllib` | 9 | **못 본다** |
| `redis` | 5 | 대상 아님(캐시) |
| `urllib3` | 2 | **못 본다** |
| `grpc` | 2 | **못 본다** |
| `aiohttp` · `minio` · `socket` | 각 1 | **못 본다** |

### 2-1. 이것이 이론이 아님을 오늘 봤다

백필을 돌릴 때마다 MinIO 초기화가 `minio.invalid` 를 향해 **5회 재시도를 두 번** 돌았다
(백필 실행 로그에 그대로 남아 있다). 타임아웃도 재시도 상한도 없어서
**저장소 하나가 안 뜨면 그 뒤의 모든 작업이 그만큼 매달린다** —
C-3.3 이 말한 "부분 실패가 전면 정지가 되는 경로" 그대로다.

---

## 3. ★ 두 번, 내가 만든 함정에 내가 빠졌다

게이트를 넓히는 동안 **잘못된 보고를 두 번 냈다.** 둘 다 고쳤지만, 왜 생겼는지가 더 중요하다.

### 3-1. 이름 매칭 (D-263 이 금지한 그것)

감싼 클라이언트를 추적하려고 `CLIENT_CTORS` 에 `Client → httpx` 를 넣었다.
그러자 `test_api_contract.py` 의 **Django 테스트 클라이언트 12건**이
"타임아웃 없는 httpx 호출"로 보고됐다. `Client()` 는 httpx 도 쓰고 Django 도 쓴다.

**고침**: 그 파일이 **그 계열을 실제로 import 했을 때만** 클라이언트로 인정한다.
→ 오탐 22건 중 12건이 사라졌다.

### 3-2. 고칠 수 없는 곳을 가리켰다

MinIO 를 호출 단위로 세서 `get_object` · `fput_object` 등 **21건**을 "타임아웃 없음"으로 냈다.
그런데 **MinIO 파이썬 SDK 는 호출에 `timeout=` 을 받지 않는다.**
타임아웃은 `Minio(..., http_client=urllib3.PoolManager(timeout=…))` 로 **한 번** 정한다.

즉 그 보고는 "고칠 수 없는 21곳을 고치라"는 말이었다.
**게이트가 틀린 곳을 가리키면 사람은 그 게이트를 믿지 않게 되고, 안 믿는 게이트는 꺼진 게이트와 같다.**

**고침**: 계열을 두 갈래로 나눴다 — 호출마다 받는 것 / **생성자에서 한 번** 정하는 것.
→ 21건이 **생성 지점 1건**이 됐다. 그것이 진짜 결함이고 진짜 고칠 자리다.

### 3-3. 부르는 방법이 답을 바꿨다

`verify_timeout.py` 가 절대경로로 엔진을 부르자 면제 목록의 키(상대경로)가 안 맞아
**면제 4건이 전부 풀렸다.** 같은 코드가 부르는 방법에 따라 다른 답을 냈다는 뜻이다.

**고침**: 경로를 저장소 뿌리 기준으로 정규화(`_rel`). 상대·절대 호출이 같은 수를 낸다 (실측 확인).

---

## 4. 고친 것 — MinIO 생성부

`backend/stream_monitors/utils/minio_client.py`

```python
self.client = Minio(..., http_client=self._http_client())

@staticmethod
def _http_client():
    connect = getattr(settings, "MINIO_CONNECT_TIMEOUT", 3.0)
    read    = getattr(settings, "MINIO_READ_TIMEOUT", 10.0)
    retries = getattr(settings, "MINIO_MAX_RETRIES", 1)
    return urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=connect, read=read),
        retries=urllib3.Retry(total=retries, backoff_factor=0.2,
                              status_forcelist=[500, 502, 503, 504]),
    )
```

- **재시도 상한도 함께 걸었다.** 타임아웃만 걸고 재시도를 안 막으면 그 배수만큼 매달린다 —
  오늘 5회를 돈 것이 그 경우다.
- **값은 설정에서 온다.** 코드에 박으면 운영에서 못 바꾼다 (C-3.4 계열).
- 기본값은 보수적이다. 목적은 "요청을 끝내 성공시키는 것"이 아니라
  **"빨리 실패하고 나머지를 서빙하는 것"**이다.

### 4-1. 다운 모킹 시험 4건 (DoD "저하 운전 경로")

`backend/tests/test_external_dependency_degraded.py::MinioStorageDegradedTest`

| 시험 | 무엇을 지키나 |
|---|---|
| `test_pool_has_connect_and_read_timeout` | 연결·응답 타임아웃이 실제로 걸려 있는가 |
| `test_retries_are_capped` | 재시도 상한 ≤ 2 — 없으면 타임아웃의 배수만큼 매달린다 |
| `test_values_come_from_settings_not_literals` | 값이 코드에 박혀 있지 않은가 |
| `test_construction_failure_does_not_raise` | 저장소가 죽어도 예외가 아니라 `available=False` 로 온다 |

**실행 결과: 파일 전체 15건 통과** (기존 11 + 신규 4).

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  PYTHONPATH=/app python -m pytest tests/test_external_dependency_degraded.py -q'
→ 15 passed
```

---

## 5. 주입 시험 — 게이트가 실제로 멈추는가

| 주입 | 기대 | 결과 |
|---|---|---|
| `requests.get()` 을 타임아웃 없이 추가 | exit 1 | **exit 1** |
| MinIO 생성자에서 `http_client=` 제거 | exit 1 | **exit 1** |
| 둘 다 되돌림 | exit 0 | **exit 0** · 78건 중 미조치 0 |

> ⚠ 이 시험 중 `git checkout --` 으로 주입을 되돌리다가 **아직 커밋하지 않은 MinIO 수정본을
> 같이 날렸다.** 알아채고 재적용했고 시험을 다시 돌려 통과를 확인했다.
> 커밋 안 된 작업이 있는 파일에 `git checkout` 을 쓰면 주입만 지워지는 것이 아니다 —
> 다음부터는 주입을 **별도 파일**로 하거나 되돌리기 전에 커밋한다.

---

## 6. 면제 4건 (전건 사유 있음)

| 위치 | 사유 |
|---|---|
| `common/external_http.py:77` · `:109` | 직전 줄에서 `kwargs.setdefault("timeout", default_timeout())` — AST 가 못 본다 |
| `delivery/decorators.py:381` | 같은 형태 |
| `stream_monitors/services/frame_detection_pb2_grpc.py:87` | **protoc 생성 스텁.** `timeout` 을 위치 인자(13번째)로 넘겨 키워드 검사에 안 잡힌다. 손으로 쓴 호출이 아니므로 고칠 자리는 이 스텁을 **부르는 쪽**이다 |

> 면제는 "매달려도 된다"는 선언이 아니라 **"정적으로 안 보일 뿐 타임아웃이 들어간다"**는 선언이다.

---

## 7. 남은 것

| 항목 | 처분 |
|---|---|
| grpc 스텁을 부르는 쪽에 deadline 이 있는가 | W0-17 후속에서 확인 — 면제 사유에 명시해 뒀다 |
| `redis` 5파일 | 캐시라 이 게이트 대상이 아니다. 다만 **매달릴 수 있는 것은 같다** — 별건으로 볼지 판정 필요 |
| `verify_tenant_scope.py` 확장 | 규약 §2 의 남은 하나. 다음 단계 |
