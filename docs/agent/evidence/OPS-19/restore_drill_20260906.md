# OPS-19 복구 시험 — **해 봤고, 몇 분인지 쟀다** (P-67 · 2026-09-06)

> `scripts/ops_restore_drill.py` 가 만든다 — 손으로 적지 않는다.

## 0. 무엇을 만들고 어떻게 지우는가 — **하기 전에 적는다**

만드는 것: DB 서버 안의 임시 DB `restore_check_20260906070334` 하나. **이 실행이 지운다.**
원본 `database_guardianx` 에는 **읽기 질의만** 던진다(표 수 세기). 쓰기 연결을 안 연다.
건드리지 않는 것: `gx-shell` · `redis` · MinIO · `gx_pgdata` 볼륨 ·
백업 볼륨 `gx_backup_vault_e` 의 파일(읽기 전용으로 붙인다).

| | |
|---|---|
| 실행 시각 | 2026-09-06T07:03:34+00:00 |
| 백업 볼륨 | `gx_backup_vault_e` → 컨테이너 안 `/backup` |
| 덤프 | `/backup/database_guardianx_20260906T160107.dump` · 9,209,410 bytes |
| sha256 | `ef9b9e6eb2dae9f7d8a20eefce09259398e08cc71256997b36e0550090871031` |
| 뜬 자리 | `postgres` 컨테이너 (이미지 `postgres:latest`) |

## 1. 쓴 명령 — 그대로 재현할 수 있다

```
docker exec postgres psql -U *** -d postgres -c 'CREATE DATABASE "restore_check_20260906070334"'  → rc=0
docker run --rm --network gx-main-network -v gx_backup_vault_e:/backup:ro postgres:latest
    pg_restore --no-owner --no-privileges -h postgres -p 5432 -U postgres -d restore_check_20260906070334 /backup/database_guardianx_20260906T160107.dump  → rc=0
docker exec postgres psql -U *** -d postgres -c 'DROP DATABASE "restore_check_20260906070334"'  → rc=0
```

## 2. 판정

  OK  ① 살릴 백업이 있는가           덤프 9,209,410바이트
  OK  ② 살아났는가                원본 223개 · 복구 223개 — 같다
  OK  ③ RTO 를 쟀는가            **0.14분** (SLA 초안 목표 30분 · 이 수는 판정이 아니라 대조다)
  OK  ④ 임시 DB 를 지웠는가         지웠다

**RTO 실측 0.14분** (8.2초) — 임시 DB 만들기부터 지우기까지 벽시계다.
복구만 따로 재지 않는다: 새벽에 사람이 겪는 시간에는 **DB 를 만들고 치우는**
시간이 들어 있고, 그것을 빼면 RTO 가 실제보다 짧게 적힌다.

## 3. 아직 못 잰 것

- **객체저장(영상·캡처)은 이 시험에 없다.** DB 만 살아나면 「영상이 있었다고
  말하는 DB」가 된다 — 그 절반은 `ops_restore.py --objects` 의 몫이다.
- **다른 호스트가 아니다.** 볼륨을 갈랐다는 사실은 「저장소와 함께 죽지
  않는다」까지 말하고, 「이 기계와 함께 죽지 않는다」는 말하지 않는다.
- 이 실행은 **사람이 불렀다.** 주 1회 저절로 도는 자리는 beat 표의
  `ops-restore-drill-weekly` 이고, 그 태스크는 이 기계에서 회색이다
  (앱 컨테이너 `pg_restore` 17.7 < 서버 18.1 · 사유는 그 태스크가 낸다).
