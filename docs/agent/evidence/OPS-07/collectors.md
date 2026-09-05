# OPS-07 — 로그 수집기를 전수로 쟀다 (2026-09-05 15:39:07)

**이 파일은 `scripts/ops_log_collectors.py` 가 실행하며 적었다.**
한 시간 치는 [실측]이고 하루 환산은 [추정]이다 — 갈라서 적었다.

## 1. 수집기를 전수로 센다

| 수집기 | 보존 기간 | 한 시간 치 [실측] | 하루 환산 [추정] | 비고 |
|---|---|---|---|---|
| 컨테이너 stdout · gx-shell | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 · **선언은 섰다 · 적용은 다음 재기동** — docker-compose.yml::shell 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · postgres | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 · **선언은 섰다 · 적용은 다음 재기동** — docker-compose.yml::postgres 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · redis | 무한 | 4,958바이트 | 118,992바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 · **선언은 섰다 · 적용은 다음 재기동** — docker-compose.yml::redis 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · guardianx-source-minio-1 | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 · **선언은 섰다 · 적용은 다음 재기동** — docker-compose.yml::minio 에 10m × 5 로 선언돼 있다 (compose 라벨) |
| 컨테이너 stdout · gx-fe-build | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 · compose 에 대응 서비스가 **없다**(docker run — 이름 대응표) — `docker run --log-opt` 로만 걸린다 |
| 컨테이너 stdout · gx-nginx-e | 10m × 5 | 0바이트 | 0바이트 | 드라이버 json-file · 회전 10m × 5 · compose 에 대응 서비스가 **없다**(docker run — 이름 대응표) — `docker run --log-opt` 로만 걸린다 |
| 컨테이너 stdout · gx-gunicorn-e | 10m × 5 | 10,274,859바이트 | 246,596,616바이트 | 드라이버 json-file · 회전 10m × 5 · compose 에 대응 서비스가 **없다**(docker run — 이름 대응표) — `docker run --log-opt` 로만 걸린다 |
| 파일 · gx-nginx-e:/var/log/nginx/gx-front.access.log | 무한 | 2,122,482바이트 | 50,939,568바이트 | 컨테이너 **안의 파일**(총 6,079,532바이트) — `json-file` 회전 밖이다. `--log-opt` 도 compose 의 `logging` 도 여기 닿지 않고, `nginx:alpine` 에는 logrotate 가 없다 |
| DB 감사 로그 · logger_auditlogs | 무한 | 4행 | 96행 | 행 1427개 · 3571712바이트 · 가장 오래된 2026-08-27 13:28:44.947815+00:00 · ⚠ 보존 90일이 **선언돼 있으나 지우는 워커가 0개다** — beat 일정 `ops-audit-purge-daily` 은 적혀 있고, 그것을 실행할 celery 워커가 브로커에 하나도 붙어 있지 않다. **선언은 삭제가 아니다** |

### 선언 — **다음에 뜰 컨테이너에는 걸리는가** [실측]

| compose 서비스 | 파일 | 드라이버 | max-size | max-file |
|---|---|---|---|---|
| `backend` | docker-compose.yml | json-file | 10m | 5 |
| `backend-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
| `celery` | docker-compose.yml | json-file | 10m | 5 |
| `celery-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
| `frontend` | docker-compose.yml | json-file | 10m | 5 |
| `frontend-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
| `minio` | docker-compose.yml | json-file | 10m | 5 |
| `nginx-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
| `postgres` | docker-compose.yml | json-file | 10m | 5 |
| `redis` | docker-compose.yml | json-file | 10m | 5 |
| `redis-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
| `shell` | docker-compose.yml | json-file | 10m | 5 |

★ **선언과 적용은 다른 사실이다.** 도커의 `LogConfig` 는 컨테이너를 **만들 때**
  굳는다 — 위 선언은 이미 떠 있는 컨테이너에 닿지 않는다. 그래서 ②(적용)는
  빨간 채로 두고 ④(선언)를 따로 둔다. ②가 초록이 되는 것은 **다음 재기동**
  때이고, 지금 재기동하지 않는 이유는 다른 차선 셋이 이 컨테이너 위에서
  일하고 있기 때문이다 — 그것은 판정기가 정할 일이 아니다.

★ **보존 기간은 [판정]이다** — `max-size 10m × max-file 5` = 컨테이너당 **50MB 상한**.
  근거는 `docker-compose.yml` 머리말에 실측과 함께 적혀 있다. 요약하면:
  가장 시끄러운 수집기(postgres · 363 KB/일 [실측])에 대해 50MB 는 약 140일 치이고,
  그런데도 **「N일 보존」이라고 적지 않는다** — `json-file` 회전은 크기 기반이라
  조용한 달에는 더 오래 남고 시끄러운 날에는 몇 시간 만에 밀린다. 약속할 수 있는
  것은 상한이지 기간이 아니다. **감사에 답하는 정본은 DB 감사 로그(90일)** 이고,
  컨테이너 stdout 은 운영 디버깅용 **단기 버퍼**다 — 이 판정이 없으면 상한을 거는
  일이 곧 「증거를 지우는 일」이 된다.

### DB 감사 로그의 자세한 사실

```
table                  logger_auditlogs
time_col               create_datetime
time_col_candidates    ['create_datetime', 'created_on', 'deleted', 'modified_on']
rows                   1427
bytes                  3571712
oldest                 2026-08-27 13:28:44.947815+00:00
newest                 2026-09-05 05:50:31.804287+00:00
rows_last_hour         4
retention_days         90
purge_beat             {'ops-audit-purge-daily': '<crontab: 10 3 * * * (m/h/dM/MY/d)>'}
file_handlers          []
```

★ **파일 수집기는 0개다.** `settings.LOGGING` 의 핸들러 중 `FileHandler` 는 없다 — 
  즉 로그 파일이 디스크에 직접 쌓이는 자리는 없고, 전부 stdout 과 DB 로 간다.
  logrotate 를 찾을 이유가 없다는 뜻이고, 그 사실을 **찾아보고** 적는다.

## 2. 판정

  OK   ① 수집기 전수       수집기 9개를 전수로 셌다
  FAIL ② 보존 기간        **보존 기간이 없다**(무한 적재): 컨테이너 stdout · gx-shell, 컨테이너 stdout · postgres, 컨테이너 stdout · redis, 컨테이너 stdout · guardianx-source-minio-1, 컨테이너 stdout · gx-fe-build, 파일 · gx-nginx-e:/var/log/nginx/gx-front.access.log, DB 감사 로그 · logger_auditlogs
  OK   ③ 자라는 속도       9개의 한 시간 치를 쟀다
  FAIL ④ 선언           **선언할 자리조차 없는 수집기**: 컨테이너 stdout · gx-fe-build — compose 밖 `docker run` 으로 떴다. **compose 를 고쳐도 닿지 않는다.** 상한은 `--log-opt max-size=10m --log-opt max-file=5` 로만 걸리고, 그 문장은 `docs/agent/RUNBOOK_로컬기동.md` STEP 2A 에 적혀 있다 — 이 빨강은 **다음에 그 컨테이너를 띄우는 사람**이 지운다

판정 **실패**.

**선언은 섰고 적용은 다음 재기동**인 수집기 4개: 컨테이너 stdout · gx-shell, 컨테이너 stdout · postgres, 컨테이너 stdout · redis, 컨테이너 stdout · guardianx-source-minio-1
  고치는 자리(`docker-compose.yml` 의 `logging.options`)에는 값이 **섰고**,
  이미 떠 있는 컨테이너에는 **닿지 않았다** — 도커의 `LogConfig` 는 컨테이너를
  **만들 때** 굳는다. 그러므로 ②는 다음 재기동에 초록이 된다.
  **지금 재기동하지 않는다** — 다른 차선이 `gx-shell`·`postgres`·`minio` 위에서
  동시에 일하고 있다. 그것은 판정기가 정할 일이 아니다.

**선언할 자리조차 없는 수집기 3개**: 컨테이너 stdout · gx-fe-build, 컨테이너 stdout · gx-nginx-e, 컨테이너 stdout · gx-gunicorn-e
  compose 밖에서 `docker run` 으로 떴다. 이 빨강은 compose 를 고쳐서는
  안 지워진다 — **다음에 그 컨테이너를 띄우는 사람**이 `--log-opt` 를 붙여야
  지워진다(`docs/agent/RUNBOOK_로컬기동.md` STEP 2A).

