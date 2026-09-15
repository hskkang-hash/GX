# 복구 실행 기록 — **해 봤다** (D-354 ①)

> 「백업 있음」은 절이 아니고 **「복구 성공」이 절이다.** 이 문서는 그 절의 증거다.
> `scripts/ops_restore.py` 가 만든다 — 손으로 적지 않는다.

| | |
|---|---|
| 실행 시각 | 2026-09-07T10:11:42+00:00 |
| 백업 시각 | 2026-09-07T10:11:16+00:00 |
| 원본 DB | `database_guardianx` |
| 복구 대상 | `restore_check_test_gx_e_20260907101131` (임시 · 끝나고 지웠다) |
| 덤프 파일 | `db_database_guardianx_20260907T101116Z.dump` · 40242096 bytes |
| sha256 | `8b6391e80c3f134b793949263cc7f85a9fbc8a8bab6aabda7e31b292ffb99a5e` |
| 뜬 자리 | `docker:postgres` · 클라이언트 `pg_dump (PostgreSQL) 18.1 (Debian 18.1-1.pgdg13+2)` |
| 판정 | **복구 성공** |

## 쓴 명령 — 그대로 재현할 수 있다

```
docker exec postgres pg_dump -Fc -h localhost -p 5432 -U postgres -d database_guardianx -f /tmp/db_database_guardianx_20260907T101116Z.dump
docker cp postgres:/tmp/db_database_guardianx_20260907T101116Z.dump 'C:\Users\hskka\AppData\Local\Temp\claude\c--GuardianX\f2a30b3b-dfbd-4ba6-b446-935d940a0f17\scratchpad\backup\db_database_guardianx_20260907T101116Z.dump'
docker cp C:\Users\hskka\AppData\Local\Temp\claude\c--GuardianX\f2a30b3b-dfbd-4ba6-b446-935d940a0f17\scratchpad\backup\db_database_guardianx_20260907T101116Z.dump postgres:/tmp/db_database_guardianx_20260907T101116Z.dump
docker exec postgres psql -U postgres -c CREATE DATABASE "restore_check_test_gx_e_20260907101131"
docker exec postgres pg_restore --no-owner --no-privileges -h localhost -p 5432 -U postgres -d restore_check_test_gx_e_20260907101131 /tmp/db_database_guardianx_20260907T101116Z.dump
docker exec postgres psql -U postgres -c DROP DATABASE "restore_check_test_gx_e_20260907101131"
```

## 증인 표 행 수 대조

| 표 | 백업 | 복구 |
|---|---:|---:|
| `stream_monitors_streammonitor` | 40 | 40 |
| `stream_monitors_detectionevent` | 22 | 22 |
| `stream_monitors_eventclip` | 22 | 22 |
| `user_coreuser` | 113 | 113 |
| `auth_group` | 0 | 0 |

## 객체저장 (영상·캡처)

객체 None개 · None bytes
