# OPS-07 — 로그 수집기를 전수로 쟀다 (2026-09-05 23:07:25)

**이 파일은 `scripts/ops_log_collectors.py` 가 실행하며 적었다.**
한 시간 치는 [실측]이고 하루 환산은 [추정]이다 — 갈라서 적었다.

## 1. 수집기를 전수로 센다

| 수집기 | 보존 기간 | 한 시간 치 [실측] | 하루 환산 [추정] | 비고 |
|---|---|---|---|---|
| 컨테이너 stdout · gx-shell | 10m × 5 | 0바이트 | 0바이트 | 드라이버 json-file · 회전 10m × 5 · docker-compose.yml::shell 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · postgres | 10m × 5 | 87바이트 | 2,088바이트 | 드라이버 json-file · 회전 10m × 5 · docker-compose.yml::postgres 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · redis | 10m × 5 | 9,200바이트 | 220,800바이트 | 드라이버 json-file · 회전 10m × 5 · docker-compose.yml::redis 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · guardianx-source-minio-1 | 10m × 5 | 0바이트 | 0바이트 | 드라이버 json-file · 회전 10m × 5 · docker-compose.yml::minio 에 10m × 5 로 선언돼 있다 (compose 라벨) |
| 컨테이너 stdout · gx-fe-build | 10m × 5 | 0바이트 | 0바이트 | 드라이버 json-file · 회전 10m × 5 · compose 에 대응 서비스가 **없다**(docker run — 이름 대응표) — `docker run --log-opt` 로만 걸린다 |
| 컨테이너 stdout · gx-nginx-e | 10m × 5 | 816바이트 | 19,584바이트 | 드라이버 json-file · 회전 10m × 5 · compose 에 대응 서비스가 **없다**(docker run — 이름 대응표) — `docker run --log-opt` 로만 걸린다 |
| 컨테이너 stdout · gx-gunicorn-e | 10m × 5 | 3,075바이트 | 73,800바이트 | 드라이버 json-file · 회전 10m × 5 · compose 에 대응 서비스가 **없다**(docker run — 이름 대응표) — `docker run --log-opt` 로만 걸린다 |
| 컨테이너 stdout · gx-celery-e | 10m × 5 | 0바이트 | 0바이트 | 드라이버 json-file · 회전 10m × 5 · docker-compose.yml::celery 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| 컨테이너 stdout · gx-beat-e | 10m × 5 | 0바이트 | 0바이트 | 드라이버 json-file · 회전 10m × 5 · docker-compose.yml::beat 에 10m × 5 로 선언돼 있다 (docker run — 이름 대응표) |
| DB 감사 로그 · logger_auditlogs | 무한 | 110행 | 2,640행 | 행 4635개 · 11026432바이트 · 가장 오래된 2026-08-27 13:28:44.947815+00:00 · 워커 1 · ⚠ 보존 90일이 선언돼 있고 워커도 붙었으나 파기 항목이 **DB 주기 표에서 꺼져 있다**(ops-audit-purge-daily=off, purge-audit-logs-daily=off) — 파기 대상 판정(보존 일수 미선언 테넌트 제외)이 서기 전까지 차선 E 가 껐다(P-57 대기). **켜기 전에는 아무것도 안 지워진다** · ⚠ 보존 일수가 **어디에도 선언되지 않았다** — 90일은 `purge_old_audit_logs` 의 **코드 기본값**이고 `AdminConfig::System` 에 `security.audit_log_retention_days` 가 없다(표시값 탐침 [실측]). 이 상태로 파기를 켜면 **아무도 정하지 않은 수로 감사 기록을 하드 삭제**하게 된다. 먼저 선언하고, 그 다음에 켠다 |

### 선언 — **다음에 뜰 컨테이너에는 걸리는가** [실측]

| compose 서비스 | 파일 | 드라이버 | max-size | max-file |
|---|---|---|---|---|
| `backend` | docker-compose.yml | json-file | 10m | 5 |
| `backend-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
| `beat` | docker-compose.yml | json-file | 10m | 5 |
| `beat-stg` | docker-compose.stg.yml | json-file | 10m | 5 |
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
rows                   4635
bytes                  11026432
oldest                 2026-08-27 13:28:44.947815+00:00
newest                 2026-09-05 14:06:11.287777+00:00
rows_last_hour         110
retention_days         90
purge_beat             {'ops-audit-purge-daily': '<crontab: 10 3 * * * (m/h/dM/MY/d)>'}
file_handlers          []
```

★ **파일 수집기는 0개다.** `settings.LOGGING` 의 핸들러 중 `FileHandler` 는 없다 — 
  즉 로그 파일이 디스크에 직접 쌓이는 자리는 없고, 전부 stdout 과 DB 로 간다.
  logrotate 를 찾을 이유가 없다는 뜻이고, 그 사실을 **찾아보고** 적는다.

## 2. 판정

  OK   ① 수집기 전수       수집기 10개를 전수로 셌다
  FAIL ② 보존 기간        **보존 기간이 없다**(무한 적재): DB 감사 로그 · logger_auditlogs
  OK   ③ 자라는 속도       10개의 한 시간 치를 쟀다
  OK   ④ 선언           컨테이너 수집기 전부에 상한이 **선언돼 있다**
  OK   ⑤ 멈춘 파일 잔재     멈춘 채 남은 파일이 없다

판정 **실패**.

**선언은 없고 상한은 걸려 있는 수집기 3개**(빨강 아님 · 경고): 컨테이너 stdout · gx-fe-build, 컨테이너 stdout · gx-nginx-e, 컨테이너 stdout · gx-gunicorn-e
  compose 밖 `docker run` 으로 떴고, 상한은 **띄우는 명령**에 산다 —
  `--log-opt max-size=10m --log-opt max-file=5` (`docs/agent/RUNBOOK_로컬기동.md`
  STEP 2A). **지금 걸려 있다는 것이 다음에도 걸린다는 뜻은 아니다** —
  다음에 띄우는 사람이 그 문장을 빠뜨리면 상한은 조용히 사라진다.

