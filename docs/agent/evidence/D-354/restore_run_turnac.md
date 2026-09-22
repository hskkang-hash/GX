# 복구 실행 기록 — **해 봤다** (D-354 ①)

> 「백업 있음」은 절이 아니고 **「복구 성공」이 절이다.** 이 문서는 그 절의 증거다.
> `scripts/ops_restore.py` 가 만든다 — 손으로 적지 않는다.

| | |
|---|---|
| 실행 시각 | 2026-09-22T04:37:35+00:00 |
| 백업 시각 | 2026-09-22T04:36:47+00:00 |
| 원본 DB | `database_guardianx` |
| 복구 대상 | `restore_check_20260922043705` (임시 · 끝나고 지웠다) |
| 덤프 파일 | `db_database_guardianx_20260922T043647Z.dump` · 143581050 bytes |
| sha256 | `bad37c2182c4985a817b9414efc297edae3c2ce6bf39b590909248996d02916c` |
| 뜬 자리 | `docker:postgres` · 클라이언트 `pg_dump (PostgreSQL) 18.1 (Debian 18.1-1.pgdg13+2)` |
| 판정 | **복구 성공** |

## 쓴 명령 — 그대로 재현할 수 있다

```
docker exec postgres pg_dump -Fc -h localhost -p 5432 -U postgres -d database_guardianx -f /tmp/db_database_guardianx_20260922T043647Z.dump
docker cp postgres:/tmp/db_database_guardianx_20260922T043647Z.dump 'docs\agent\evidence\D-354\backup_turnac\db_database_guardianx_20260922T043647Z.dump'
docker cp docs\agent\evidence\D-354\backup_turnac\db_database_guardianx_20260922T043647Z.dump postgres:/tmp/db_database_guardianx_20260922T043647Z.dump
docker exec postgres psql -U postgres -c CREATE DATABASE "restore_check_20260922043705"
docker exec postgres pg_restore --no-owner --no-privileges -h localhost -p 5432 -U postgres -d restore_check_20260922043705 /tmp/db_database_guardianx_20260922T043647Z.dump
docker exec postgres psql -U postgres -c DROP DATABASE "restore_check_20260922043705"
```

## 증인 표 행 수 대조

| 표 | 백업 | 복구 |
|---|---:|---:|
| `stream_monitors_streammonitor` | 52 | 52 |
| `stream_monitors_detectionevent` | 41 | 41 |
| `stream_monitors_eventclip` | 41 | 41 |
| `user_coreuser` | 119 | 119 |
| `auth_group` | 0 | 0 |

## 객체저장 (영상·캡처)

객체 None개 · None bytes
