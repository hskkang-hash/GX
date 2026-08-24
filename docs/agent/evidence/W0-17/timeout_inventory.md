# W0-17 — 외부 의존 저하 운전: 타임아웃 대장 + 다운 시험

**실행** 2026-08-22 · **티켓** W0-17 (WP-2 · R2) · **환경** 로컬 기동본
**대상 DB** `w017_guardianx` (= `database_guardianx` 의 TEMPLATE 복제본. **운영 복제본 무변경** · D-245)

---

## 0. 판정

> **부분 실패가 더 이상 전면 정지가 아니다.** 스트리밍 서버를 죽인 상태에서
> 목록 API 가 **500 → 200**. 그리고 죽었다는 사실을 숨기지 않는다 —
> 응답의 `stream_status` 가 `"unavailable"` 로 나온다.
>
> 타임아웃 없는 `requests` 호출 **17건 → 0건** (면제 3건은 `setdefault` 형태라 정적으로만 안 보인다).

---

## 1. ★ 지시서의 "49건"은 과대 추정이었다 (AUTHOR-ERROR #18 · D-214)

지시서(WP-2 ENTRY §2)는 "requests 사용 29파일 / timeout 없는 호출 **49건**"이라 적었다.
그 수는 grep 이고, grep 은 **이름이 비슷한 것을 같이 센다.**

`scripts/scan_request_timeouts.py`(AST 실측)로 다시 세면:

| 구분 | 수 |
|---|---:|
| `requests` 계열 호출 전체 | **76** |
| — 타임아웃 있음 | 58 → **73** (조치 후) |
| — **타임아웃 없음** | **17** → **0** (조치 후) |
| 면제(사유 등재) | **3** |

**49에 섞여 있던 것들** — 전부 `requests` 가 아니다:
* `redis_client.delete(...)` 14건 — Redis 클라이언트. 타임아웃 기전이 다르다(소켓 옵션)
* `self.client.get(...)` (OpenSearch) 2건 — OpenSearch 클라이언트. 자체 timeout 인자를 쓴다
* `self.client_a.get(...)` 5건 — **Django 테스트 클라이언트**. 외부 호출이 아니다
* `self._sessions.get(record_id)` 1건 — dict 조회

> 실측대로 구현했다 (D-214). 남은 Redis·OpenSearch 계열은 **다른 티켓의 대상**이며
> §5 에 남긴다 — 이 티켓에서 조용히 끼워 넣지 않는다.

## 2. 무엇을 바꿨나

| # | 무엇 | 어디 |
|---|---|---|
| ① | 타임아웃 값 **설정 1곳** | `config/settings.py` `EXTERNAL_HTTP_TIMEOUT` = (연결 3s, 응답 5s) · `..._LONG` = (3s, 60s) |
| ② | 저하 운전 헬퍼 | `common/external_http.py` — `fetch_json()` 은 **실패를 예외가 아니라 값으로** 돌려준다 `(data, ok)` |
| ③ | 목록 API 저하 운전 | `stream_monitors/schemas/schemas_djantic_out.py` — 상태조회 실패 시 `stream_status="unavailable"` + 200 |
| ④ | 타임아웃 부여 17건 | 9파일 (§3) |
| ⑤ | 회귀 게이트 | `scripts/scan_request_timeouts.py --check` (exit 1) + `tests/test_external_dependency_degraded.py` 11건 |

### 왜 헬퍼인가 — 숫자를 흩지 않기 위해서다 (D-212)
호출부에 `timeout=5` 를 적으면 그 5가 몇 초인지 나중에 아무도 모른다. 이미 그 상태였다
(`timeout=5` 가 코드 곳곳에 있었다). 값은 설정 한 곳이고 `default_timeout()` 만 그것을 읽는다.

### 왜 `stream_status` 필드인가
스트리밍 서버가 죽었을 때 **빈 목록을 200 으로 주는 것은 거짓말**이다. 사용자는 "드론이 없다"로 읽는다.
필드 하나로 "목록은 정상, 스트리밍 상태만 일시 불가"를 구분한다. 필드 추가는 **가산적 변경**이라
기존 클라이언트를 깨지 않는다 (W0-18 계약 정합의 하위호환 원칙과 같은 방향).

## 3. 타임아웃을 부여한 17건

| 파일 | 건수 | 무엇 | 값 |
|---|---:|---|---|
| `stream_monitors/services/stream_monitor_services.py` | 4 | 녹화 시작·경로 등록/조회/삭제 (MediaMTX) | 기본 |
| `third_api/test_api.py` | 4 | API 키 수동 점검 스크립트 | 기본 |
| `dashboard/shemas/schemas_djantic_out.py` | 2 | open-meteo 날씨 · nominatim 역지오코딩 | 기본 |
| `delivery/services/processing_service.py` | 2 | AI 이상탐지 분석 요청 | 기본 |
| `delivery/decorators.py` | 1 | 외부 연동 데코레이터 (`request_kwargs.setdefault`) | 기본 |
| `devices/services/devices_service.py` | 1 | FlightBird 그룹 fetch 트리거 | 기본 |
| `flight_log/services/flight_log_service.py` | 1 | AI 분석 결과 조회 | 기본 |
| `media_data/services/media_data_detect_service.py` | 1 | 프레임 검출 API | **장기(60s)** |
| `surveillance/services/surveillance_profile_service.py` | 1 | 임무 업로드 (FlightBird) | **장기(60s)** |

면제 3건은 `kwargs.setdefault("timeout", …)` 로 **직전 줄에서** 넣는 형태라 AST 가 못 본다
(`common/external_http.py` 2 · `delivery/decorators.py` 1). 스캐너의 `EXEMPT` 에 사유와 함께 등재했다.

## 4. 다운 시험 — dod ① (같은 서버·같은 계정·같은 요청)

`STREAM_URL=http://streaming.dead.invalid` (존재하지 않는 호스트)로 서버를 띄우고 `man` 으로 호출.

| 화면 | 경로 | **before** | **after** |
|---|---|---:|---:|
| **목록(스트림 모니터)** | `/api/stream-monitors/stream-monitors` | **500** | **200** (`stream_status: unavailable`) |
| 이력(비행 로그) | `/api/flight-log/flight-log/` | 200 | 200 |
| 통계(대시보드) | `/api/optimization/optimization/dashboard-stats` | 200 | 200 |
| 목록(드론) | `/api/devices/devices-management` | 200 | 200 |

**before 는 추정이 아니라 실측이다** — 같은 서버에서 `schemas_djantic_out.py` 만
커밋본(`git show HEAD:…`)으로 되돌려 다시 쟀다.

> 부수 효과 하나: 이제 격리 시험에 **스트리밍 스텁이 필요 없다.**
> W0-16 시험이 매번 스텁을 띄워야 했던 이유가 이 500 이었다 (http_role_split_test.md §4-2).

## 5. 이 티켓에서 하지 않은 것 (그리고 왜)

| 항목 | 왜 |
|---|---|
| Redis 클라이언트 14건 | 타임아웃 기전이 다르다(연결 옵션 `socket_timeout`). 캐시 계층 전반의 판단이라 범위 밖 — 별도 티켓 권고 |
| OpenSearch 클라이언트 2건 | 같은 이유. 다만 실측에서 이름 해석 실패 시 **재시도 5회**를 도는 것이 보였다(기동 로그) — 저하 운전 대상이 맞다 |
| MinIO 클라이언트 | 기동 시 재시도 5회 후 FileSystemStorage 로 폴백한다 — **이미 저하 운전이 있다.** 다만 기동이 그만큼 늦다 |
| 로그인 rate limit 500 → 429 | W0-18 (계약 정합)의 대상 |
| 서킷 브레이커 | 타임아웃·폴백이 먼저다. 반복 실패 차단은 계측 후 판단 (P-W0-17-1) |

## 6. 재현

```bash
# 타임아웃 대장 (호스트에서)
python scripts/scan_request_timeouts.py backend           # 표
python scripts/scan_request_timeouts.py backend --check   # 미조치 있으면 exit 1

# 저하 운전 단위시험 (11건 · DB 무의존)
docker exec gx-shell sh -c "cd /app && python manage.py test tests.test_external_dependency_degraded -v 2 --keepdb"

# 다운 시험 (dod ①) — 복제본 + 죽은 호스트
docker exec postgres psql -U postgres -c "CREATE DATABASE w017_guardianx TEMPLATE database_guardianx"
docker exec -e DB_NAME=w017_guardianx gx-shell sh -c "cd /app && python manage.py migrate"
docker exec -d -e DB_NAME=w017_guardianx -e STREAM_URL=http://streaming.dead.invalid gx-shell \
  sh -c "cd /app && python manage.py runserver 0.0.0.0:8000 --noreload"
# → 로그인 후 §4 의 4개 경로 호출. 정리: DROP DATABASE w017_guardianx
```
