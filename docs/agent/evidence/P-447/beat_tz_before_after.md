# P-447 — 전역 TIME_ZONE = Asia/Seoul · beat 표 전후 대조 (턴 AR · 조율자 E · 2026-09-30 19:4x KST)

조건(WO-21 §5 P-447): **발화 KST 가 전과 같을 때만 유지.** 저장값은 UTC(`USE_TZ=True`) 그대로 · 바뀌는 것은 표시와 beat.

재는 법: 스케줄러는 `django_celery_beat.DatabaseScheduler` 다 — 실제로 도는 것은 **DB `CrontabSchedule` 행**(행마다 `timezone` 칸)이고, beat 이 다시 뜰 때 `app.conf.beat_schedule`(코드)이 그 행을 덮는다(`from_schedule` 가 `schedule.tz` 를 칸에 적는다). 그래서 두 면을 잰다:
- **전 = DB 지금 행**(살아 있는 beat 이 읽는 것 · 고치기 전 실측)
- **후 = 새 코드가 beat 재기동 때 심을 행**(gx-shell · 새 settings 로 `config.celery` 를 읽어 계산)
- 발화 KST = 2026-10-01 00:00 KST 이후 첫 발화(분 단위 전수 · celery `crontab_parser`).

| beat | 전 crontab · tz | 전 발화 KST | 후 crontab · tz | 후 발화 KST | 같음 |
|---|---|---|---|---|---|
| surveillance-recurring-profile-generator | 0 0 · HCM | 02:00 | 0 2 · Seoul | 02:00 | ● |
| law08-evidence-anchor | 5 0 · HCM | 02:05 | 5 2 · Seoul | 02:05 | ● |
| ops-audit-purge-daily (꺼짐) | 40 2 · HCM | 04:40 | 40 4 · Seoul | 04:40 | ● |
| law02a-video-retention-sweep (꺼짐) | 50 2 · HCM | 04:50 | 50 4 · Seoul | 04:50 | ● |
| **ops-backup-daily** | 0 5 · Seoul | **05:00** | 0 5 · Seoul | **05:00** | ● |
| u24-monthly-report (매월 1일) | 0 3 · HCM | 05:00 | 0 5 · Seoul | 05:00 | ● |
| sec-key-rotation-watch-daily | 50 3 · HCM | 05:50 | 50 5 · Seoul | 05:50 | ● |
| celery.backend_cleanup | 0 4 · HCM(celery 기본) | 06:00 | 0 6 · Seoul(코드에 이름 그대로 명시) | 06:00 | ● |
| ops-restore-drill-weekly (일) | 0 6 · HCM | Sun 08:00 | 0 8 · Seoul | Sun 08:00 | ● |
| ops14-heartbeat-digest | 0 8 · HCM | 10:00 | 0 10 · Seoul | 10:00 | ● |

- **10/10 같음.** 백업 05:00 · 파기 둘 OFF(`enabled=False`) 그대로.
- DB 에만 있는 행(precompute-* · warm-* · purge-audit-logs-daily 꺼짐)은 코드가 덮지 않아 `timezone=Asia/Ho_Chi_Minh` 칸을 그대로 지닌다 → 발화 불변. 앞 넷은 분 단위 반복이라 두 시간 차와 무관.
- 간격(interval) 항목 11개는 시간대와 무관.
- ⚠ 사람이 읽을 때: 생존 알림 10:00 · 앵커 02:05 는 **옛 HCM 시각을 KST 로 옮긴 값**이다. 「08:00 KST 로 당길까」는 이 표의 일이 아니다 — 새 결정이 필요하면 세종 청구.
- 이 표의 「후」는 beat 재기동 뒤 DB 행으로 다시 잰다(창 ② 재시작 뒤 · 같은 스크립트).

바꾼 곳: `config/settings.py` 기본값 → Asia/Seoul · `config/celery.py` 시(hour) KST 로 옮김 · `_seoul_crontab`(P-260) 폐지 · `celery.backend_cleanup` 명시 · 표시 폴백 5곳(`pytz.timezone('Asia/Ho_Chi_Minh')` → `settings.TIME_ZONE`) · `incident_report.timezone_note` 머리말 「닫혔다」.
되돌리기: 환경 `TIME_ZONE=Asia/Ho_Chi_Minh` 한 줄 — ⚠ 단 그때는 celery.py 의 시도 되돌려야 발화가 같다(`git revert` 한 커밋).
시험: test_aq_w2b_dsm_screens · test_dormant_wiring · test_incident_report · test_l_retention · test_ops19_backup_is_autonomous = 77 passed · 1 skipped.

## 재기동 뒤 실측 (2026-09-30 20:16 KST · 대표 「docker restart gx-gunicorn-e gx-celery-e gx-beat-e」)
- beat 로그: `DatabaseScheduler: Schedule changed.` — 코드가 DB 행을 다시 심었다.
- DB `CrontabSchedule` 다시 잼(같은 스크립트): 코드 항목 10개 전부 `timezone=Asia/Seoul` · 발화 KST **02:00 · 02:05 · 04:40 · 04:50 · 05:00 · 05:00(1일) · 05:50 · 06:00 · Sun 08:00 · 10:00** = 위 「전」과 **10/10 같음**.
- DB 에만 있는 5행은 `Asia/Ho_Chi_Minh` 칸 그대로 · 발화 불변(예측대로).
- 8500 문서 문(익명): `/api/docs`→301→`/api/docs/` 404 · `/api/openapi.json` 404 · `/api/dsm/openapi.json` 404 · `/api/fws/docs` 404 · `/api/v1/access/openapi.json` 404 · `/` 200.
