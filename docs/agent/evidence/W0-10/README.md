# W0-10 증거 — 내부 토폴로지 정리

생성: 2026-08-13 · ⚠ **정본 tickets.yaml 에 W0-10 티켓이 없다**

RESUME_NEXT §2-1 이 지시한 티켓이나, v2.2 정본(62티켓)이 전달되지 않아
현재 정본(v2.0, 58티켓)에 항목이 없다. 지시가 명확하고 치환 예시까지 주어져
작업은 수행했고, 등재는 사람이 해야 한다.

## 치환 결과 — .env.example 2개, 13건

backend/.env.example (9건)
```
DB_HOST           192.168.0.48                    → db.internal.example
MINIO_ENDPOINT    files.gaion.dev                 → minio.internal.example
OPENSEARCH_HOST   gx-opensearch-api.gaion.dev     → opensearch.internal.example
STREAM_URL        gx-streaming-api.gaion.dev      → streaming.internal.example
RTSP_URL          vpn-vn.gaion.dev:30554          → rtsp.internal.example:8554
AI_RTSP_PATH      guardianx-ai.gaion.dev          → ai.internal.example
AI_GRPC_URL       media-ai-svc.gaion.dev          → media-ai.internal.example
AI_ANALYSIS_URL   gx-ai-analysis-vn.gaion.dev     → ai-analysis.internal.example
REDIS_HOST        redis://localhost:6379          → redis://redis:6379
```

frontend/.env.example (4건)
```
VITE_STREAMING_BASE_URL    gx-streaming-api.gaion.dev  → streaming.internal.example
VITE_STREAMING_WEBRTC_URL  gx-webrtc.gaion.dev         → webrtc.internal.example
VITE_TURN_URL              turn:192.168.0.200:30478    → turn:turn.internal.example:3478
VITE_AI_STREAM_WS_URL      media-ai-svc.gaion.dev      → wss://media-ai.internal.example
```

## DoD 검증

```
grep -cE '192\.168\.|\.gaion\.dev' backend/.env.example frontend/.env.example
  backend/.env.example:0
  frontend/.env.example:0
```

## 건드리지 않은 것 (D-203)

- `frontend/package.json` 의 사내 git URL 2건 — 기능상 필수다
  `@gaion/gcs-fe`, `rj-core` → `git+ssh://git@192.168.0.22/...`
- `docker-compose.yml` 의 서비스명 호스트 — 컨테이너 네트워크 내부 이름이다

## 범위 밖에 남은 것

`.env.example` 외의 소스에도 내부 도메인 리터럴이 남아 있다
(`settings.py` 의 env 기본값, `docker-compose.stg.yml` 등).
W0-10 의 DoD 는 `.env.example` 2개 파일 기준이라 거기까지만 했다.
전면 정리가 필요하면 별도 티켓으로 올려야 한다.

---

## ★ 2단계 — `settings.py` 기본값 (2026-08-15 · WP-0 §11-1 · P-W0-10-1 A안 채택)

v3.1 이 W0-10 의 DoD 를 **`.env.example` 2개 → settings.py 기본값 포함**으로 넓혔다.
위 "범위 밖에 남은 것"에 적어 둔 항목이 정식 범위가 된 것이다. 대표 판정은 **A안**
(status 를 `ready` 로 정정 + 전량 치환).

### 실측 — **ENTRY 는 13곳이라 적었고 실제는 16곳이었다**

| 위치 | 값 | 치환 |
|---|---|---|
| L33 `ALLOWED_HOSTS` 주석 | `192.168.88.216` | `host.internal.example` |
| L37-47 `CSRF_TRUSTED_ORIGINS` | `192.168.0.200` × 6 | **목록 자체를 `env.list("DJANGO_CSRF_TRUSTED_ORIGINS")` 로 전환.** 코드 기본값은 `localhost:8000`·`127.0.0.1:8000` 2개뿐 |
| " | `guardianx-api.gaion.dev`, `guardianx.gaion.dev` | 위와 동일 (env 로 이동) |
| L197 `DB_HOST` | `192.168.0.48` | `db.internal.example` |
| L471 `MINIO_ENDPOINT` | `192.168.0.200:30090` | `minio.internal.example` |
| L646 `STREAM_URL` | `192.168.0.200:30001` | `streaming.internal.example` |
| L653 `RTSP_URL` | `192.168.0.200:30554` | `rtsp.internal.example:8554` |
| L657 `AI_ANALYSIS_URL` | `192.168.0.200:30018` | `ai-analysis.internal.example` |
| L658 `AI_RTSP_PATH` | `guardianx-ai.gaion.dev` | `ai.internal.example` |
| L659 `AI_GRPC_URL` | `192.168.0.102:8000` | `media-ai.internal.example` |

**ENTRY 기재(13) 대비 +3의 내역** — ① L33 주석의 사설 IP(주석이라 눈에서 빠졌다)
② `AI_RTSP_PATH` 의 `gaion.dev`(ENTRY 는 "스트림/AI 4"로 묶으며 이 줄을 세지 않았다)
③ ENTRY 의 산술 자체(8+1+1+4 = 14 를 13 으로 적음).
**D-210 대로 실측을 따랐고 차이를 여기 적는다.**

### 왜 `localhost` 가 아니라 `*.internal.example` 인가

`.example` 은 RFC 6761 예약 TLD 라 **어떤 DNS 에서도 해석되지 않는다.**
`localhost` 기본값은 개발자 PC 의 엉뚱한 로컬 서비스에 조용히 붙을 수 있고,
그 사고는 "연결은 됐는데 데이터가 이상하다"로 나타나 찾기 어렵다.
해석 실패는 시끄럽고, 에러 메시지에 `db.internal.example` 이 그대로 찍혀 원인을 자기가 말한다.
**1단계에서 `.env.example` 에 이미 쓰던 어휘와도 같다 — 두 파일이 한 낱말을 쓴다.**

### DoD 검증

```
$ grep -REn '\b(192\.168|10\.|172\.(1[6-9]|2[0-9]|3[01]))\.' backend/config/settings.py
$ echo $?
1            ← 0건

$ grep -Ein 'gaion\.' backend/config/settings.py
$ echo $?
1            ← 0건

$ python -m py_compile backend/config/settings.py
SYNTAX OK
```

### `.env.example` 대응 (신규 1건)

```
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,https://api.your-deployment.example
```

나머지 9개 키(`DB_HOST`·`MINIO_ENDPOINT`·`STREAM_URL`·`RTSP_URL`·`AI_*`)는
1단계에서 이미 `.env.example` 에 있다. **새로 추가한 것은 CSRF 하나뿐이다.**

### 건드리지 않은 것 — 그리고 그 이유

| 대상 | 왜 |
|---|---|
| `CORS_ALLOWED_ORIGINS` 의 `aim.koca.go.kr` · `aip.caat.or.th` | **사설 IP 도 내부 도메인도 아니다** — 실제 고객사 배포 origin 이다. W0-10 의 DoD 범위 밖이고, 코드 기본값에서 빼면 해당 고객 배포가 `.env` 갱신 없이는 깨진다. 4원칙 ④ |
| `CORS_ALLOW_ALL_ORIGINS = True` (L629) | **범위 밖이지만 기록해 둔다** — 이 한 줄 때문에 위 `CORS_ALLOWED_ORIGINS` 목록은 현재 **아무 효력이 없다.** 운영 배포에서 전 origin 을 허용한다는 뜻이므로 릴리스 위생 관점의 실질 결손이다. → **WP-2 입력으로 이관** (적재: P-W0-10-2) |

### ⚠ 기동 확인은 아직이다

치환 자체는 정적으로 검증되지만(`py_compile`), **`.env` 없이 기동하면 이제 DB·MinIO 에 붙지 못한다.**
그것이 의도이나, 실제 기동 확인은 Docker 가 있어야 한다 → ENTRY §6 리스크 3 대로
**사내망 방문 당일에는 이 커밋을 적용하지 않고, 방문 이후 오프라인에서 기동 확인**한다.

```bash
# 방문 이후
docker compose up -d backend redis && docker compose logs --tail=50 backend
```
