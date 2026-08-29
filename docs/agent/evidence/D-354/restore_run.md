# 복구 실행 기록 — **해 봤다** (D-354 ①)

> 「백업 있음」은 절이 아니고 **「복구 성공」이 절이다.** 이 문서는 그 절의 증거다.
> `scripts/ops_restore.py` 가 만든다 — 손으로 적지 않는다.

| | |
|---|---|
| 실행 시각 | 2026-08-29T13:46:50+00:00 |
| 백업 시각 | 2026-08-29T13:44:57+00:00 |
| 원본 DB | `database_guardianx` |
| 복구 대상 | `restore_check_20260829134640` (임시 · 끝나고 지웠다) |
| 덤프 파일 | `db_database_guardianx_20260829T134442Z.dump` · 4447529 bytes |
| sha256 | `6578919a3bf0f272225695b7e2d76d90a5634ba46cc58524e5578ffc7cbfbcd1` |
| 뜬 자리 | `docker:postgres` · 클라이언트 `pg_dump (PostgreSQL) 18.1 (Debian 18.1-1.pgdg13+2)` |
| 판정 | **복구 성공** |

## 쓴 명령 — 그대로 재현할 수 있다

```
docker exec postgres pg_dump -Fc -h localhost -p 5432 -U postgres -d database_guardianx -f /tmp/db_database_guardianx_20260829T134442Z.dump
docker cp postgres:/tmp/db_database_guardianx_20260829T134442Z.dump 'docs\agent\evidence\D-354\backup\db_database_guardianx_20260829T134442Z.dump'
docker cp docs\agent\evidence\D-354\backup\db_database_guardianx_20260829T134442Z.dump postgres:/tmp/db_database_guardianx_20260829T134442Z.dump
docker exec postgres psql -U postgres -c CREATE DATABASE "restore_check_20260829134640"
docker exec postgres pg_restore --no-owner --no-privileges -h localhost -p 5432 -U postgres -d restore_check_20260829134640 /tmp/db_database_guardianx_20260829T134442Z.dump
docker exec postgres psql -U postgres -c DROP DATABASE "restore_check_20260829134640"
```

## 증인 표 행 수 대조

| 표 | 백업 | 복구 |
|---|---:|---:|
| `stream_monitors_streammonitor` | 39 | 39 |
| `stream_monitors_detectionevent` | 0 | 0 |
| `stream_monitors_eventclip` | 0 | 0 |
| `user_coreuser` | 103 | 103 |
| `auth_group` | 0 | 0 |

## 객체저장 (영상·캡처)

**닿지 못했다** — `minio.invalid`.

「닿지 못했다」와 「0개다」는 다른 사실이다(D-301). 이 환경에는 객체저장이 뜨지 않는다.
그래서 **객체 백업·복구는 미측정**이고 DB 복구만 실측이다 —
한 칸에 두면 「복구 성공」이 절반의 사실이 된다.

★ DB 만 살아나면 이벤트 행은 돌아오고 **그 이벤트의 영상은 사라진다.**
  복구된 시스템이 「영상이 있었다고 말하는 DB」가 된다 — 착시 ⑥(스키마)의 운영판이다.
