# E → 조율자 — 자동 백업이 「저절로 돌았다」를 기계가 판정문 한 장으로 말하게 [실측 2026-09-23 10:20 KST경]

## ① 실측 명령과 출력 그대로

### 자기시험 (호스트) — 26/26 통과, 음성 대조 포함
```
$ python scripts/verify_backup_recovery.py --self-test
```
```
[P-107] TARGET=호스트 + 컨테이너 «gx-celery-e» 의 금고 «/backup» · 증거 파일 D-373/backup_last.json · D-373/restore_drill_last.json · D-354/restore_run*.md
[P-107] AS=(계정 없음) — `docker exec` 로 금고를 **읽기만** 한다. 이 파일 안에 docker exec 가 있으므로 **호스트에서** 부른다
[P-107] SOURCE=살아 있는 금고의 **바이트**와 기계가 쓴 판정문 — 「백업이 있다」는 말이 아니라 파일 크기를 직접 잰다
[P-107] MEASURED=금고의 `*.dump` 를 **크기와 함께** 전수 + 회수증 후보 문서 전수 + 판정문 — **분모 43** (금고 덤프 39 · 회수증 후보 3 · 판정문 1). 「파일이 생겼다」가 아니라 **바이트**를 센다
  [통과] ★ 출생 표본: 2026-09-22 실제 금고는 빨강이다
  [통과] ★ 출생 표본: 0바이트 다섯을 세어 말한다
  [통과] ★ 출생 표본: 바이트 있는 덤프가 15일 전이라 늙었다고 말한다
  [통과] 양성: 최근 덤프에 바이트가 있으면 초록
  [통과] 음성: 0바이트만 있으면 빨강
  [통과] 음성: 바이트가 있어도 15일 전이면 빨강
  [통과] 음성: 금고에 못 닿으면 회색
  [통과] 혼합: 진짜가 있으면 초록이되 0바이트 개수를 말한다
  [통과] 이름에 시각이 없으면 None
  [통과] stat 줄 둘을 읽는다
  [통과] 양성: invoked_by=beat 이고 파일이 금고 최신과 같으면 초록
  [통과] ★★ 음성 대조: 금고에 바이트 있는 최신 덤프가 있어도 판정문이 manual 이면 빨강 — 손으로 뜬 덤프만 있는 금고는 초록이 아니다
  [통과] 음성: invoked_by 칸이 아예 없으면 빨강
  [통과] 음성: invoked_by=beat 이어도 판정문 파일과 금고 최신 파일이 다르면 빨강
  [통과] 음성: invoked_by=beat · 파일 일치 · 그러나 26h 를 넘으면 빨강
  [통과] 음성: 금고에 바이트 있는 덤프가 없으면 beat 판정문이 있어도 빨강
  [통과] ★★ 출생 표본: 배선 전 실제 판정문(invoked_by 없음)은 실제 자동 덤프가 있어도 ㉡ 을 못 채운다
  [통과] ★★ 출생 표본: 같은 실물에 invoked_by=beat 만 더하면 초록
  [통과] ★ 출생 표본: 그날의 판정문(ALARM)은 빨강이다
  [통과] 음성: 판정문이 UNKNOWN 이면 회색(초록 아님)
  [통과] 음성: 판정문이 없으면 회색
  [통과] 양성: 판정문이 OK 면 초록
  [통과] 음성: 「복구 성공」이 없는 문서는 회수증이 아니다
  [통과] 양성: 「복구 성공」 + 최근 시각이면 초록
  [통과] 음성: 성공했어도 21일 전이면 빨강
  [통과] 음성: 주기 복구시험이 UNKNOWN 이면 회수증이 아니다
[SELF-TEST] 26건 중 0건 실패
```

### 실제 게이트 (호스트, `--json`) — 지금은 정직하게 빨강
```
$ python scripts/verify_backup_recovery.py --json
```
```
[OPS-04] [입력] 모수 43 — 금고 덤프 39 · 회수증 후보 3 · 판정문 1
[OPS-04] ㉠ 판정문 초록 — 기계가 OK 를 적었다
[OPS-04] ㉡ beat 덤프 빨강 — 판정문의 호출자가 'beat' 가 아니다(None) — 손으로 뜬 덤프는 이 술어를 채우지 못한다(P-264)
[OPS-04] ㉢ 회수증 초록 — 복구 회수증이 0.5일 전에 있다 (restore_drill_last.json)
[OPS-04] ㉣ ★ 0바이트 덤프 30개 — (지우지 않음)
[OPS-04] 빨강 — 복구할 것이 남아 있지 않다.
```
**이 빨강은 옳다.** `D-373/backup_last.json` 은 이 배선(호출자 칸) **이전**에 쓰인
실물(2026-09-22T20:00:00Z · 149,701,407 바이트 · 자동 덤프)이라 `invoked_by` 가 없다.
초록으로 만들려고 다시 부르지 않았다(WO 지시대로 「임시 앞당김→실행→원복」 안 함).
**다음 예정 실행(내일 05:00 KST)이 `invoked_by="beat"` 판정문을 쓰면 같은 게이트가
같은 파일로 초록을 낸다** — 코드를 더 고칠 일이 없다.

### 단위시험 — 내가 고친 것이 걸리는 시험 6개, 전부 통과 (host 위임 → gx-shell)
```
$ MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
    python -m pytest tests/test_u56_backup_declaration.py tests/test_evidence_guard.py \
    tests/test_be_purge.py tests/test_dormant_wiring.py tests/test_l_retention.py \
    tests/test_s_key_rotation.py -q --create-db -p no:randomly
```
```
................................................s.....................................................................
107 passed, 1 skipped, 37 warnings in 299.97s (0:04:59)
```
(1 skip 는 기존부터 있던 skip — 내가 만들지 않았다. 0 실패.)

### celery.py 배선 확인 (gx-shell 안, import 검증)
```
task common.ops_backup_beat
kwargs {'invoked_by': 'beat'}
hour {5} minute {0} tz Asia/Seoul
other entry tz (should be app default, Ho_Chi_Minh) Asia/Ho_Chi_Minh hour {2}
```
→ **이 항목만** Asia/Seoul, 나머지(예 audit-purge)는 그대로 Ho_Chi_Minh. 격리 확인됨.

### 살아 있는 DB 행 반영 확인 (재기동 없이 · DatabaseScheduler 는 tick 마다 재읽음)
```
BEFORE {'crontab_id': 11, 'kwargs': '{}', 'crontab': ('0', '3', '*', '*', '*', 'Asia/Ho_Chi_Minh')}
new_cron id 22 created True
AFTER {'crontab_id': 22, 'kwargs': '{"invoked_by": "beat"}', 'crontab': ('0', '5', '*', '*', '*', 'Asia/Seoul')}
OLD ROW STILL 0 3 Asia/Ho_Chi_Minh
sharer unaffected 11 3 Asia/Ho_Chi_Minh   ← purge-audit-logs-daily(disabled) 가 옛 행을 같이 쓰고 있어 손대지 않았다
last_run_at 2026-09-22 20:00:00.002436+00:00 total_run_count 16   ← 안 건드림 → 다음 발화는 여전히 내일(24h 뒤)
```

### gx_shell_bootstrap.py 격리 기동 확인 (대체 포트 18000/13002 · 지금 도는 8000/3002 는 안 건드림)
```
http://127.0.0.1:18000/api/health/ HTTPError 404   ← Django 가 살아서 응답(경로만 없음)
http://127.0.0.1:13002/ 200                         ← SPA index.html
http://127.0.0.1:13002/api/whatever HTTPError 404   ← API 경로 폴백 안 함(200 위장 방지, 턴 U 짝)
```
확인 뒤 두 프로세스 종료함(`kill`). 지금 도는 gx-shell 의 진짜 8000/3002 는 손대지 않았다.

`docker compose --profile tools config shell` (YAML 유효성 · env 는 더미로 채움) →
`entrypoint: [python, /repo/scripts/gx_shell_bootstrap.py]` 로 정상 파싱됨.

---

## ② 고친 파일:줄 (소유표 §2 E 행 안)

- `backend/common/ops_tasks.py` — `ops_backup_beat()` 시그니처에 `invoked_by: str = "manual"`
  추가, 5개 분기(payload) 모두에 `"invoked_by": invoked_by` 실음 (약 L360~435).
- `scripts/verify_backup_recovery.py` — `_read_verdict_raw()` 신설, `judge_verdict()` 에
  `invoked_by` 칸 추가, `FRESH_BEAT_DUMP_HOURS=26` + `judge_beat_dump()`(새 ㉡) 신설,
  `run()`/`report()` 를 새 ㉡ 로 교체(㉣ 0바이트 표시는 그대로 유지), `self_test()` 에
  케이스 9개 추가(음성 대조 필수 1건 + 출생 표본 2건 포함, 총 26건).
- `backend/config/celery.py` — `zoneinfo.ZoneInfo` import, `_seoul_crontab()` 헬퍼 신설,
  `ops-backup-daily` 항목에 `kwargs={"invoked_by": "beat"}` 추가 + `schedule` 을
  `_seoul_crontab(hour=5, minute=0)` 로 교체(옛 `crontab(hour=3, minute=0)`). 다른 12개
  beat 항목은 **손대지 않음**.
- `docker-compose.yml` — `shell` 서비스의 `entrypoint: ["sleep"]` + `command: ["infinity"]`
  를 `entrypoint: ["python", "/repo/scripts/gx_shell_bootstrap.py"]` 로 교체(주석 포함).
  ⚠ **소유표에 명시된 파일이 아니다** — P-263 이 요구하는 「gx-shell 이 다시 설 때 스스로
  뜨게」를 이루는 유일한 자리라 판단해 건드렸다. 최소한(그 두 줄 + 주석)만 고쳤다.
  검토해 달라.
- `scripts/gx_shell_bootstrap.py` (신규) — `/tmp/gx_spa_server.py` 의 SPA 정적 서버 로직을
  그대로 옮기고(로직 불변), `manage.py runserver 0.0.0.0:8000 --noreload` 기동을 더함.
  `manage.py migrate` 는 부르지 않음(D-283 안전장치 유지).
- `docs/agent/evidence/D-346/ga_readiness.yaml` — **OPS-19 한 행만**: `kind: unmeasurable`
  → `kind: measured_red`, `kind_why` 갱신, `gate: scripts/verify_backup_recovery.py` 신규
  추가, `note_turn_ae` 신규 추가(①~④ 요약). **`status` 는 `미착수` 그대로 뒀다** —
  P-264 대로 아직 절을 올리지 않았다. 기존 필드(`note_turn_ad2`·`gate_missing_why`·
  `note_turn_j` 등) **하나도 지우지 않음**.

### 실제로 적용한 DB 변경 (파일이 아니라 상태 — 기록으로 남긴다)
`django_celery_beat` 의 `PeriodicTask(name="ops-backup-daily")` 를 **새** `CrontabSchedule`
행(id=22 · `0 5 * * * Asia/Seoul`)에 연결하고 `kwargs='{"invoked_by": "beat"}'` 로 갱신함.
옛 행(id=11 · `0 3 * * * Asia/Ho_Chi_Minh`)은 disabled 인 `purge-audit-logs-daily` 가
같이 쓰고 있어 **손대지 않음**(공유 행이라 직접 고치면 그쪽도 바뀔 뻔했다 — 위 실측으로 잡음).
컨테이너는 하나도 재생성·재시작하지 않았다 — `DatabaseScheduler` 가 다음 tick 에 DB 변경을
스스로 읽는다(코드로 확인).

---

## ③ 안 한 것과 사유

- **beat 스케줄 임시 앞당김 → 실행 → 원복 안 함.** WO §4 가 이미 「자동 1회 증거는 났다,
  이 걸음은 필요 없다」고 못박았고, OPS-19 자동덤프_첫건 문서와 일치한다.
- **OPS-19 절을 `구현·closed` 로 올리지 않음.** P-264: 「호출자 칸과 음성 대조가 서기
  전에는 절을 올리지 마라」— 서는 것 자체는 됐지만, **지금 게이트를 돌리면 빨강**이다
  (기존 판정문이 배선 이전 것이라서). 실물로 초록이 나는 것은 **내일 05:00 KST**
  (beat 가 `invoked_by="beat"` 판정문을 쓸 때)이다. 그때 조율자가 다시 돌려 올리면 된다 —
  코드는 이미 준비돼 있다.
- **gx-shell 컨테이너를 재생성하지 않음.** 지시대로. `docker-compose.yml`·
  `scripts/gx_shell_bootstrap.py` 는 **다음에 gx-shell 이 다시 설 때**부터 효과가 있다.
  지금 도는 gx-shell(runserver PID 35 · SPA `/tmp/gx_spa_server.py` PID 86)은 그대로 둔다.
- **`config/settings.py` 의 `TIME_ZONE` 기본값(Asia/Ho_Chi_Minh)을 안 건드림.** 앱 전역
  시간대를 바꾸면 다른 12개 beat 항목(감사 정리·영상 보존·키 회전·월간 보고·복구 시험·
  생존 알림 등)이 전부 두 시간 밀린다 — 아무도 부탁하지 않은 변경이라 안 했다. 대신
  `ops-backup-daily` **한 항목만** `crontab.tz` 인스턴스 값을 덮어 Seoul 로 옮겼다
  (기술적 근거는 celery.py 의 `_seoul_crontab()` docstring · 이 쪽지 ①에 검증 포함).
- **`purge-audit-logs-daily`(disabled·레거시) 를 안 건드림.** `ops-backup-daily` 와
  같은 `CrontabSchedule` 행(id=11)을 공유하고 있었다 — 만졌으면 그쪽 스케줄도 같이
  바뀔 뻔했다. 대신 새 행(id=22)을 만들어 `ops-backup-daily` 만 옮겼다.
- **게이트 헤더(`_header()`)의 `measured=` 문구는 그대로 둠.** ㉡ 이름이 바뀐 것을
  본문에서 이미 충분히 설명하고 있어 위험 대비 이득이 작다고 판단해 손대지 않았다.

---

## ④ 조율자가 해야 할 것

1. **내일 05:00 KST 이후** `python scripts/verify_backup_recovery.py --json` 을 다시
   돌려 `beat_dump.state == "OK"` 인지 보고, 되면 OPS-19 를 `status: 구현 · kind: closed`
   로 올려 달라(이번 턴엔 P-264 때문에 안 올렸다).
2. **`docker-compose.yml` 의 `shell` 서비스 entrypoint 변경**을 검토해 달라 — 소유표
   밖 파일이라 최소한만 고쳤다. 다음에 gx-shell 을 재생성할 창(재부팅 아침 준비물의
   일부)에서 이 entrypoint 로 서는지, `docker exec gx-shell sh -c "ps aux"` 로
   runserver+SPA 둘 다 뜨는지 확인해 달라. (이 턴엔 재생성 안 함 · 대체 포트로만 검증)
3. **`gx-beat-e`** 는 내가 재생성·재시작하지 않았다 — 위 DB 변경이 다음 tick 에 스스로
   반영된다고 코드로 확인했지만, **실제 다음 발화(내일 05:00 KST)로 최종 확인**해 달라.
4. `docs/agent/evidence/D-373/backup_last.json`·`evidence_anchor_last.json`·
   `key_rotation_last.json`·`docs/agent/evidence/OPS-20/reboot_mornings.json` 이
   git status 에 M 으로 뜨는 것은 **살아 있는 beat/monitor 태스크가 스스로 쓴 것**이고
   내가 만든 변경이 아니다(확인함 — `backup_last.json` diff 는 창2a 손덤프→오늘 새벽
   자동덤프로 이미 바뀌어 있던 것). 커밋 때 참고.

---

## ⑤ 내가 틀렸던 것 / 판단 기록

- 처음엔 `app.conf.timezone` 을 통째로 Seoul 로 바꾸려 했다 — celery 소스를 뜯어보니
  앱 전역 시간대 하나를 13개 항목이 공유해서, 그러면 backup 아닌 12개가 전부 2시간
  밀리는 것을 뒤늦게 발견했다. `crontab.tz` 가 `cached_property`(인스턴스로 덮어쓸 수
  있음)라는 것과 `django_celery_beat` 가 `schedule.tz` 를 그대로 DB 행에 옮겨 심는다는
  것을 코드로 확인한 뒤에야 한 항목만 격리하는 길을 찾았다. (기록: 이 쪽지 ①의
  celery.py import 검증 출력이 그 증거다.)
- `django_celery_beat` 의 `periodic_task_name` 옵션이 태스크 실행 컨텍스트에서
  「beat 가 불렀다」를 자동으로 말해 줄 것으로 처음 짐작했으나, celery/kombu 소스에
  그 필드를 소비하는 코드가 없어 **메시지에 안 실린다**는 것을 확인했다 — 그래서
  표준 메커니즘에 기대지 않고 `kwargs={"invoked_by": "beat"}` 로 직접 배선했다. 이
  삽질이 없었다면 「호출자 칸이 있는데 왜 항상 비는지」를 나중에 또 겪었을 것이다.
- `CrontabSchedule` 행이 여러 `PeriodicTask` 에 **공유**될 수 있다는 것(`purge-audit-
  logs-daily` 가 `ops-backup-daily` 와 같은 행을 쓰고 있었다)을 실제로 조회해 보고서야
  알았다 — 몰랐으면 옛 행을 직접 고쳐 disabled 레거시 태스크까지 건드릴 뻔했다.

---

## 덧붙임 — 조율자 교정 반영 [실측 2026-09-23 · 같은 회차]

조율자가 지적: ㉡ 를 「beat 덤프인가」로 바꾼 채로 두니 **한 게이트가 두 절(OPS-04·OPS-19)을
같이 답했고**, OPS-19 의 참인 빨강이 OPS-04 의 참인 초록을 덮어 마지막 줄이 세상과 어긋났다
(「복구할 것이 남아있지 않다」— 사실은 있었다). 지시대로 **자를 쪼갰다.**

### ① 고친 자리
- `scripts/verify_backup_recovery.py` — `run()`/`report()` 를 **원래대로 되돌림**(㉡ =
  「바이트 있는 덤프 ≤ 48h」 · `judge_vault` 그대로). `judge_beat_dump()` 함수 자체는
  **지우지 않음** — 아래 새 파일이 import 해서 쓴다(D-369). self_test() 에서 그 함수
  전용 표본 9개를 새 파일로 옮기고, 자리엔 이동 사유만 주석으로 남김(18/18 통과).
- `scripts/verify_backup_autonomy.py` (신규) — **OPS-19 전용** 게이트. ㉤ = 「마지막
  beat 덤프 나이 ≤ 26h」, `verify_backup_recovery.judge_beat_dump()` 를 그대로 import.
  자기시험에 조율자가 요구한 네 표본(① 오늘 실물로 ㉡ 초록·㉤ 빨강 ② 둘 다 초록
  ③ 둘 다 빨강 ④ ㉤ 음성 대조) + judge_beat_dump 단위 표본을 합쳐 12/12 통과.
- `docs/agent/evidence/D-346/ga_readiness.yaml` — OPS-19 행: `gate:` 를
  `scripts/verify_backup_autonomy.py` 로 교체, `kind_why` 갱신, `note_turn_ae2` 추가
  (교정 내용 · note_turn_ae 는 지우지 않고 그대로 둠). **OPS-04 행은 안 건드림.**

### ② 게이트 두 갈래 실제 출력 그대로
```
$ python scripts/verify_backup_recovery.py     # OPS-04
[OPS-04] [입력] 모수 43 — 금고 덤프 39 · 회수증 후보 3 · 판정문 1
[OPS-04] ㉠ 판정문 초록 — 기계가 OK 를 적었다
[OPS-04] ㉡ 금고 초록 — 바이트가 있는 덤프가 5.5시간 전에 있다
[OPS-04] ㉢ 회수증 초록 — 복구 회수증이 0.6일 전에 있다 (restore_drill_last.json)
[OPS-04] ㉣ ★ 0바이트 덤프 30개 (지우지 않음)
[OPS-04] 초록 — 뜬 것이 있고, 그것을 살려 봤다.
```
```
$ python scripts/verify_backup_autonomy.py     # OPS-19
[OPS-19] [입력] 판정문 1 · 회수증 후보 3
[OPS-19] ㉠ 판정문 초록 — 기계가 OK 를 적었다
[OPS-19] ㉤ beat 덤프 빨강 — 판정문의 호출자가 'beat' 가 아니다(None) — 손으로 뜬 덤프는 이 술어를 채우지 못한다(P-264)
[OPS-19] ㉢ 회수증 초록 — 복구 회수증이 0.6일 전에 있다 (restore_drill_last.json)
[OPS-19] (참고 · 이 게이트의 rc 에는 안 들어간다) OPS-04 금고 신선도: 초록 — 바이트가 있는 덤프가 5.5시간 전에 있다
[OPS-19] 빨강 — 백업이 저절로 돌았다는 것을 이 판정문으로는 아직 못 말한다.
```
**세상과 어긋나지 않는다** — OPS-04(오늘 복구된다)=초록, OPS-19(아직 자동은 증명 못 함)=빨강,
둘 다 정직하다.

### ③ 자기시험 수
- `verify_backup_recovery.py --self-test` → **18/18 통과**(judge_beat_dump 전용 표본 이동 후).
- `verify_backup_autonomy.py --self-test` → **12/12 통과**(조율자 지정 4표본 포함).
- 단위시험 재확인(영향받는 6개 파일, 되돌림 반영 후): `107 passed, 1 skipped, 0 failed`.
- `_gate_header` 자기시험(P-204 분모 검사) 통과 — 처음엔 MEASURED= 에 「분모 N」 리터럴이
  없어 경고가 났고, `verify_backup_autonomy.py` 의 머리글에 `**분모 43**` 을 명시로 넣어 고침.

### ④ 내가 놓친 것
- 처음에 ㉡ 를 그 자리에서 바로 바꾼 것 자체가 「한 게이트, 두 물음」이 됐다 — 자기시험만
  보고 「초록/빨강이 옳게 갈린다」에 안심했지, **그 게이트가 동시에 답하고 있던 다른 절
  (OPS-04)의 마지막 줄이 뭐라고 말하는지**를 실제로 다시 읽어 보지 않았다. `run_gate()`
  가 `gate:` 를 **인자 없는 bare path** 로만 부른다는 것(`scripts/verify_ga_readiness.py`)도
  이번에 조회해서 알았다 — 그래서 `--clause` 플래그가 아니라 **파일을 가른** 것이 맞는
  선택이었다(안 갈랐으면 두 절이 여전히 같은 rc 를 받았을 것이다).
