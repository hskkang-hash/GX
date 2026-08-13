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
