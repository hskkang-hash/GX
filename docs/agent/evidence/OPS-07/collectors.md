# OPS-07 — 로그 수집기를 전수로 쟀다 (2026-09-04 15:36:30)

**이 파일은 `scripts/ops_log_collectors.py` 가 실행하며 적었다.**
한 시간 치는 [실측]이고 하루 환산은 [추정]이다 — 갈라서 적었다.

## 1. 수집기를 전수로 센다

| 수집기 | 보존 기간 | 한 시간 치 [실측] | 하루 환산 [추정] | 비고 |
|---|---|---|---|---|
| 컨테이너 stdout · gx-shell | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 |
| 컨테이너 stdout · postgres | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 |
| 컨테이너 stdout · redis | 무한 | 2,238바이트 | 53,712바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 |
| 컨테이너 stdout · guardianx-source-minio-1 | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 |
| 컨테이너 stdout · gx-fe-build | 무한 | 0바이트 | 0바이트 | 드라이버 json-file · max-size 없음 · max-file 없음 |
| DB 감사 로그 · logger_auditlogs | 90일 (beat ops-audit-purge-daily) | 0행 | 0행 | 행 1374개 · 3563520바이트 · 가장 오래된 2026-08-27 13:28:44.947815+00:00 |

### DB 감사 로그의 자세한 사실

```
table                  logger_auditlogs
time_col               create_datetime
time_col_candidates    ['create_datetime', 'created_on', 'deleted', 'modified_on']
rows                   1374
bytes                  3563520
oldest                 2026-08-27 13:28:44.947815+00:00
newest                 2026-09-04 05:17:27.794969+00:00
rows_last_hour         0
retention_days         90
purge_beat             {'ops-audit-purge-daily': '<crontab: 10 3 * * * (m/h/dM/MY/d)>'}
file_handlers          []
```

★ **파일 수집기는 0개다.** `settings.LOGGING` 의 핸들러 중 `FileHandler` 는 없다 — 
  즉 로그 파일이 디스크에 직접 쌓이는 자리는 없고, 전부 stdout 과 DB 로 간다.
  logrotate 를 찾을 이유가 없다는 뜻이고, 그 사실을 **찾아보고** 적는다.

## 2. 판정

  OK   ① 수집기 전수       수집기 6개를 전수로 셌다
  FAIL ② 보존 기간        **보존 기간이 없다**(무한 적재): 컨테이너 stdout · gx-shell, 컨테이너 stdout · postgres, 컨테이너 stdout · redis, 컨테이너 stdout · guardianx-source-minio-1, 컨테이너 stdout · gx-fe-build
  OK   ③ 자라는 속도       6개의 한 시간 치를 쟀다

판정 **실패** — 통과가 목표가 아니다. **지금 어떤 수집기가 무한히 쌓이는지**를
이 표가 처음으로 말한다. 고칠지 말지는 배포 형상이 정할 일이고, 고치는 자리는
`docker-compose.yml` 의 `logging.options.max-size`/`max-file` 하나다.
