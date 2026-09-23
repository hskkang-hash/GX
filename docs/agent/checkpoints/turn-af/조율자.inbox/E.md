# E → 조율자 [턴 AF] — 내일 확실히 오르게 배선 재확인 · VAPID 구멍 막음 · 아침 칸은 손대지 않음

## §0 확인 — 오늘 OPS-19 절은 안 올렸다
지시대로 **절을 올리지 않았다.** `ga_readiness.yaml` OPS-19 행의 `status: 미착수` 그대로,
`kind: measured_red` 그대로 — 손대지 않았다. beat 스케줄도 앞당기지 않았다.

---

## ① 실측 명령과 출력 그대로

### 1) 「내일 그 덤프에 invoked_by=beat 가 박히는가」 — 세 겹으로 재확인 (전부 읽기만)

**a. 살아 있는 PeriodicTask 행 (ORM, gx-shell 안)**
```
name ops-backup-daily
task common.ops_backup_beat
kwargs {"invoked_by": "beat"}
enabled True
crontab 0 5 * * * Asia/Seoul
last_run_at 2026-09-22 20:00:00.002436+00:00   ← 턴 AE 이후 안 바뀜(다음 발화 아직 안 옴)
total_run_count 16                              ← 안 바뀜(내가 몰래 부르지 않았다는 증거)
```

**b. DatabaseScheduler 가 이 행에서 실제로 만드는 엔트리 (`ModelEntry` — celery 가 메시지를
   지을 때 쓰는 바로 그 클래스, gx-shell 안)**
```
entry.name ops-backup-daily
entry.task common.ops_backup_beat
entry.kwargs {'invoked_by': 'beat'}
entry.schedule <crontab: 0 5 * * * (m/h/d/dM/MY), Asia/Seoul>
entry.options {'headers': {}, 'periodic_task_name': 'ops-backup-daily'}
```
→ **b가 a보다 강한 증거다.** a는 DB 행이 맞다는 것만 말하지만, b는 beat 이 celery 에게
실제로 건넬 **메시지의 kwargs 그 자체**다. 내일 05:00 KST 에 이 그대로 나간다.

**c. `invoked_by` 기본값 잠금 — 단위시험(몽키패치로 `_write_evidence` 를 막아 실제
   `backup_last.json` 은 절대 안 건드림, gx-shell 안, `/tmp` 임시 스크립트 · 실행 후 삭제)**
```python
ops_tasks._write_evidence = _fake_write_evidence   # 진짜 판정문 쓰기를 가로채 메모리에만 담음
settings.OPS_BACKUP_DIR = ''                        # 가장 싼 분기(SKIPPED_UNDECLARED)로 떨어뜨림
r1 = ops_tasks.ops_backup_beat()                    # kwargs 없음
r2 = ops_tasks.ops_backup_beat(invoked_by='beat')   # kwargs 있음
```
```
CASE1 no-kwargs invoked_by = 'manual'
CASE2 kwargs=beat invoked_by = 'beat'
ASSERT manual: True
ASSERT beat: True
captured writes (should be 2, both fake, real vault untouched): 2
```
호출 뒤 실제 `D-373/backup_last.json` 의 mtime·`git status` 를 대조 — **안 바뀜**
(mtime 그대로 2026-09-23T00:48:54 UTC · git status 에 안 뜸). 내일 증거는 오염되지 않았다.

**결론 — a·b·c 가 서로를 가리킨다.** DB 행에 kwargs 가 있고(a), 스케줄러가 그것을 그대로
메시지에 옮기고(b), 함수 자신도 그 kwarg 를 받으면 정확히 그 값을 판정문에 싣는다(c).
내일 05:00 KST 뒤 `python scripts/verify_backup_autonomy.py` 를 돌리면 ㉤ 이 초록으로
바뀔 것이다 — 코드를 더 고칠 일이 없다(턴 AE 결론 재확인, 이번엔 세 겹으로 쟀다).

### 2) VAPID 구멍 — gx_shell_bootstrap.py 가 금고 파일을 읽게 함

**실측 A — 지금 gx-shell 은 `/repo` 를 통째 마운트하지 않는다 (지시서의 경고가 맞다)**
```
$ docker exec gx-shell find / -iname '*.env*'
/app/.env  /app/.env.example  /app/.env.stg          ← .env.vapid 없음
$ docker inspect gx-shell --format '{{json .Mounts}}'
... Destination: /repo/backend, /repo/frontend, /repo/scripts, /docs, /app, /backup ...
                                                       ← 저장소 뿌리 자체는 안 물려 있음
```

**실측 B — 존재하지 않는 파일을 단일 파일로 바인드마운트하면 Docker 가 어떻게 하는가**
(이 값에 따라 「없으면 죽는다」인지 「빈 디렉터리로 조용히 넘어간다」인지가 갈린다)
```
$ docker run --rm -v ".../.env.vapid.NOPE:/repo/.env.vapid.NOPE:ro" alpine sh -c "ls -la /repo/.env.vapid.NOPE"
total 4
drwxr-xr-x  ...  .
drwxr-xr-x  ...  ..
```
→ **빈 디렉터리가 생긴다. 에러 없이.** 그래서 `.env.vapid` 가 없는 환경에서도 컴포즈가
안 죽는다 — 대신 코드가 `os.path.isfile()` 로 그 더미를 「없다」로 읽어야 한다(그렇게 짰다).

**실측 C — 고친 뒤: 버리는 통(`docker run --rm`, 다른 이름 `gx-shell-vapid-throwaway`,
   다른 포트)으로 새 마운트 자체는 확인, DB/MinIO 비밀은 안 건드림**
```
$ docker run -d --name gx-shell-vapid-throwaway --entrypoint python \
    -v ".../.env.vapid:/repo/.env.vapid:ro" ... -p 18009:18009 -p 13009:13009 \
    guardianx-backend:latest /repo/scripts/gx_shell_bootstrap.py
[VAPID]   GX_VAPID_PUBLIC_KEY  len=87 sha256[:12]=<가림> (금고에서 실음)
[VAPID]   GX_VAPID_PRIVATE_KEY len=43 sha256[:12]=<가림> (금고에서 실음)
[VAPID]   GX_VAPID_SUBJECT     len=26 sha256[:12]=<가림> (금고에서 실음)
```
VAPID 적재까지는 성공. 그 뒤 `manage.py runserver` 가 `DB_PASSWORD`(이어서 `MINIO_ACCESS_KEY`)
없이는 `config/settings.py` import 단계에서 죽는다 — **이건 내 변경과 무관한, 이미 있던
간격이다**: 지금 도는 gx-shell·gx-celery-e·gx-beat-e 는 전부 **compose 밖에서 손으로
만들어졌다**(턴 AE 가 이미 실측·기록함 — `OPS_BACKUP_DIR` 볼륨 문제와 같은 뿌리). 그 실제
비밀들을 이 버리는 통에 다시 넣으려면 진짜 자격증명을 꺼내 담아야 했고, 그건 「값을
로그·argv 에 0」과 이번 턴의 credential-비물질화 원칙에 어긋난다고 판단해 **안 했다**
(자세한 사유는 ③ 참조). 컨테이너는 곧바로 지웠다(`docker rm -f gx-shell-vapid-throwaway`).

**실측 D — 그래서 전체를 다르게 검증했다: 이미 진짜 비밀을 갖고 있는 살아 있는 gx-shell
   **안에서**, `docker cp` 로 `.env.vapid` 사본만 얹고(마운트 아님·재생성 아님), 대체 포트
   18010/13010 로 똑같은 부트스트랩 스크립트를 실행**
```
$ docker cp .env.vapid gx-shell:/tmp/e_vapid_test/.env.vapid
$ docker exec -d -e GX_VAPID_ENV_FILE_PATH=/tmp/e_vapid_test/.env.vapid \
    -e GX_RUNSERVER_BIND=0.0.0.0:18010 -e GX_SPA_PORT=13010 -w /app gx-shell \
    python /repo/scripts/gx_shell_bootstrap.py
$ docker exec gx-shell ps -eo pid,cmd | grep 18010
  38604 python /repo/scripts/gx_shell_bootstrap.py
  38610 python manage.py runserver 0.0.0.0:18010 --noreload
$ docker exec gx-shell sh -c "tr '\0' '\n' < /proc/38610/environ | grep -o '^GX_VAPID_[A-Z_]*' | sort -u"
GX_VAPID_ENV_FILE_PATH
GX_VAPID_PRIVATE_KEY
GX_VAPID_PUBLIC_KEY
GX_VAPID_SUBJECT
$ docker exec gx-shell python -c "... urlopen(...) ..."
http://127.0.0.1:18010/api/health/   404   (Django 가 살아서 응답 — 경로만 없음)
http://127.0.0.1:13010/              200   (SPA index.html)
http://127.0.0.1:13010/api/whatever  404   (API 폴백 안 함 — 턴 U 짝 유지)
```
→ **진짜 서버(진짜 DB/MinIO 비밀 포함)가 실제로 뜨고, 그 서버 프로세스의 진짜 환경에
VAPID 세 이름이 실제로 들어가 있는 것**까지 `/proc/PID/environ` 으로 직접 확인했다 —
앱 코드가 "값이 있다고 주장"하는 게 아니라 커널이 그 프로세스에 실제로 넘긴 값이다.
끝나고 정리:
```
$ docker exec gx-shell sh -c "kill 38604 38610"
$ docker exec gx-shell rm -rf /tmp/e_vapid_test
$ docker exec gx-shell ps -eo pid,cmd | grep -E 'runserver 0.0.0.0:8000|gx_spa_server'
     86 python /tmp/gx_spa_server.py            ← 진짜 3002, 안 건드림
  30961 python manage.py runserver 0.0.0.0:8000 --noreload   ← 진짜 8000, 안 건드림
```
**gx-shell 을 재생성하지 않았다.** 지금 도는 진짜 8000/3002 는 시작부터 끝까지 그대로 뒀다.

### 3) 아침 칸(P-271) — 읽기만 했다 (이 파일은 내 소유가 아니다)
```
$ python scripts/ops_reboot_morning.py
회색 ㉡ 아침     아침 1/10

$ python scripts/ops_reboot_morning.py --record-morning
[OPS-20] 아침 기록 — **거부한다** — 컨테이너 중에 지난 기록(2026-09-22T20:58:43)보다
**먼저 선 것**이 있다(가장 오래된 시작 2026-09-22T11:41:39). **재부팅이 없었는데
아침을 세는 것은 수를 지어내는 것이다**
[OPS-20] **한 줄도 안 늘렸다.** 수를 지어내지 않는다
```
→ **오늘 「1/10」이 「재부팅이 없었다」라는 것을 판정기가 스스로, 명시로 말한다** — 이
문장은 회색 사유와 분리된 별도 진단 메시지다. `can_record()` 가 컨테이너들의 실제
`StartedAt` 을 지난 기록과 대조해서 가른다(사람 말이 아니라 타임스탬프로).

**다만 코드를 읽다가 갈리지 않는 자리를 하나 찾았다.** `judge()` 의 ㉡(아침 N/M)은
`len(mornings) >= MORNINGS_TARGET` 만 본다 — 기록된 각 아침에 실려 있는 `all_running`
칸(컨테이너가 실제로 전부 `running` 이었는지)을 **집계 판정에서는 안 본다.** 즉 raw
JSON 에는 `all_running: false` 가 남더라도(재부팅은 됐는데 일부가 안 섰다), 그 아침도
그냥 분자에 더해진다 — 「재부팅이 없었다」(오늘 이 경우 · `can_record` 가 걸러 줌)와
「재부팅했는데 일부가 안 섰다」(raw 필드엔 남지만 집계 색에는 안 드러남)가 **판정기의
최종 N/M 줄에서는 같은 무게**다. 이 파일(`scripts/ops_reboot_morning.py`)은 내
소유표에 없어 **고치지 않았다** — 아래 ④ 로 넘긴다.

---

## ② 고친 파일:줄

- `scripts/gx_shell_bootstrap.py`
  - 머리말에 VAPID 절 추가(왜·어디서·실패해도 안 죽는 이유 — L1~L34 부근).
  - `import hashlib` 추가(L77).
  - `VAPID_ENV_NAMES`(L86) · `VAPID_ENV_FILE_PATH`(L91, 기본 `/repo/.env.vapid`,
    `GX_VAPID_ENV_FILE_PATH` 로 덮어쓸 수 있음 — 시험용) 신설.
  - `_fp()`(L94, `mint_vapid_pair.py` 의 sha256[:12] 관례 재사용) 신설.
  - `_load_vapid_env()`(L99~약158) 신설 — 파일 없음/디렉터리(더미 마운트)면 죽지 않고
    한 줄 찍고 돌아감, 있으면 알려진 이름 셋만 실음, **이미 환경에 값이 있으면 안 덮음**,
    값은 절대 안 찍고 이름·길이·지문만 찍음.
  - `main()` 맨 앞에 `_load_vapid_env()` 호출 추가(L200 부근) — `subprocess.Popen` 이
    `env=` 없이 부모 `os.environ` 을 그대로 물려받으므로 runserver 뜨기 **전에** 채운다.
- `docker-compose.yml`
  - `shell` 서비스 `volumes:` 에 `./.env.vapid:/repo/.env.vapid:ro` 한 줄 추가(L456 부근,
    사유 주석 포함). **다음에 gx-shell 이 다시 설 때부터** 효과가 있다 — 지금 도는
    컨테이너는 이 턴에서도 재생성하지 않았다.
  - `docker compose --profile tools config shell` 로 YAML 유효성 재확인(POSTGRES_PASSWORD
    는 더미로만 채워 파싱만 검증 · RC=0 · 새 마운트가 `.env.vapid` 실제 경로로 정확히
    resolve 되는 것 확인).

이번 턴엔 `backend/common/ops_tasks.py` · `scripts/ops_backup.py` ·
`scripts/verify_backup_autonomy.py` · `scripts/verify_backup_recovery.py` ·
`docs/agent/evidence/D-346/ga_readiness.yaml` **고치지 않았다** — 턴 AE 배선이 이미
옳게 서 있는 것을 세 겹으로 재확인만 했다(①-1). 자기시험도 재확인: `verify_backup_
autonomy.py --self-test` 12/12 · `verify_backup_recovery.py --self-test` 18/18, 전부
그대로 통과(회귀 없음).

---

## ③ 안 한 것과 사유

- **OPS-19 절을 올리지 않음.** §0 대로 — 오늘 호출자 칸이 실린 실물 판정문이 없다
  (내일 05:00 KST 이후에야 난다). `ga_readiness.yaml` 손 안 댐.
- **beat 스케줄 임시 앞당김 안 함.** 지시대로.
- **gx-shell 재생성 안 함.** 지시대로 — VAPID 마운트·entrypoint 변경 둘 다 **선언만** 서고
  **적용은 다음 재생성**이다.
- **버리는 통(`docker run --rm`)으로 전체 서버(runserver 완주)까지는 못 갔다.** VAPID
  적재까지는 확인했지만, `settings.py` 가 `DB_PASSWORD`·`MINIO_ACCESS_KEY` 등 기본값
  없는 필수 비밀을 요구해서(의도된 하드닝 — "W0-0: 자격증명 기본값 제거") 완주하려면
  **진짜 비밀을 그 버리는 통에 다시 넣어야** 했다. 그 값들을 꺼내 담는 것 자체가
  이번 턴이 피하려는 「credential materialization」이라 판단해 멈췄다. 대신 **이미 진짜
  비밀을 갖고 있는 살아있는 gx-shell 안에서** `docker cp` 로 `.env.vapid` 사본만 얹고
  대체 포트로 돌려 **완주까지 증명했다**(①-2 실측 D) — 비밀은 한 글자도 새로 만지지
  않았다. 결과적으로 요구된 확인(실제로 서는지)은 됐다고 본다.
- **`scripts/ops_reboot_morning.py` 를 안 고침.** 내 소유표(§2 E 행)에 없는 파일이다
  (그 파일도 관계된 `docs/agent/evidence/OPS-20/reboot_mornings.json` 도 마찬가지 —
  ga_readiness.yaml 의 OPS-20 **행**만 내 것인데, 그 파일에는 애초에 `id: OPS-20`
  항목 자체가 없어 새로 짓지 않았다 — 안 시킨 일을 벌이는 것은 이번 지시서 범위 밖이다).
  「1/10 = 재부팅 없음」은 판정기가 이미 명시로 말한다(①-3) — 그 점은 **손대지 않아도
  이미 됐다.** 다만 raw `all_running` 이 집계에 안 쓰이는 간격은 **찾았지만 고치지
  않았다** — 소유가 아니다. 아래 ④ 로 넘긴다.
- **VAPID 값을 어디에도 찍지 않음.** 이 쪽지에도, 로그에도, argv 에도 — 이름·길이·
  sha256[:12] 만. 실제 값은 3곳(`.env.vapid` 파일 · 살아있는 프로세스 환경 · 조율자가
  어제 손으로 띄운 runserver)에만 있다.

---

## ④ 조율자가 할 것

1. **내일 05:00 KST 이후**: `python scripts/verify_backup_autonomy.py` (OPS-19) 재실행.
   ①-1 의 세 겹 증거대로 ㉤ 이 초록이면 `ga_readiness.yaml` OPS-19 행을
   `status: 구현 · kind: closed` 로 올려 달라 — 코드는 이미 준비돼 있다.
2. **다음에 gx-shell 을 재생성하는 창**(재부팅 정비의 일부)에서:
   - `docker compose up -d shell` 뒤 `docker exec gx-shell sh -c "ps aux | grep -E 'runserver|gx_shell_bootstrap'"` 로 둘 다 뜨는지,
   - `docker exec gx-shell sh -c "tr '\0' '\n' < /proc/<runserver_pid>/environ | grep -c GX_VAPID"` 로 **3** 이 나오는지(VAPID 가 새 마운트에서 실제로 실렸는지) 확인해 달라.
   - 이때 반드시 `.env.vapid` 가 저장소 뿌리에 그대로 있는지 먼저 확인(옮기거나
     지우면 스크립트는 안 죽지만 VAPID 없이 뜬다 — 그게 원래 있던 구멍으로 돌아가는 것).
3. **`scripts/ops_reboot_morning.py` 의 `judge()`** — ㉡(아침 N/M)이 각 기록의 `all_running`
   을 무시하고 개수만 센다(③ 참조). 이건 내 파일이 아니라 못 고쳤다. 고칠 차선(아마
   K+Q — 판정기 담당)에게 넘겨 주시길: 「재부팅했는데 일부가 안 섰다」인 아침을
   N/M 분자에서 빼거나 다른 표식을 달아야 「재부팅이 없었다」와 온전히 갈린다.
4. 오늘도 `docs/agent/evidence/D-373/backup_last.json` · `evidence_anchor_last.json` ·
   `key_rotation_last.json` · `docs/agent/evidence/OPS-20/reboot_mornings.json` 이 살아있는
   beat/monitor 가 스스로 쓴 변경으로 git status 에 뜬다 — 내가 만든 변경이 아니다.

---

## ⑤ 내가 틀렸던 것 / 판단 기록

- 처음엔 「버리는 통」을 `docker run --rm` 하나로 전부(진짜 DB·MinIO 포함) 완주시키려고
  더미 `DB_PASSWORD` 를 넣어 봤는데, 그 다음 줄에서 바로 `MINIO_ACCESS_KEY` 가 없다고
  죽었다 — 필수 비밀이 하나가 아니라 여럿이라는 것을 실측하고서야 알았다. 그 모든 것을
  가짜로 채우면 "완주는 하지만 내가 만든 가짜 앱을 시험한 것"이 되고, 진짜 값을 담으면
  비밀을 새로 물질화하는 것이라 **둘 다 아니다**로 판단했다. 대신 이미 진짜 비밀을 쥔
  살아있는 컨테이너에 파일 사본만 `docker cp` 로 얹는 셋째 길을 찾았다 — 재생성도
  아니고 비밀도 안 만지면서 완주까지 증명하는 길이었다. 처음 접근(버리는 통 단독 완주)을
  고집했으면 이 턴이 비밀 하나를 어딘가에 노출하고 끝났을 것이다.
  ⚠ 다만 이 `docker cp` 우회는 **실제 마운트 자체를 검증한 것은 아니다** — 마운트
  검증은 실측 C(버리는 통, VAPID 적재까지만)가 했고, 완주는 실측 D(docker cp, 이미
  진짜인 컨테이너)가 했다. 둘을 합쳐야 전체가 증명된다 — 어느 한쪽만으로는 부족했다.
- `docker exec -d` 로 백그라운드 실행한 프로세스는 `docker logs` 로 못 본다(그 방식은
  로그를 안 남긴다) — 그래서 stdout 대신 `/proc/PID/environ` 으로 직접 재는 쪽으로
  바꿨다. 이게 오히려 더 강한 증거였다(앱이 "봤다"고 주장하는 게 아니라 커널이 넘긴
  실제 값이니까).
- `scripts/ops_reboot_morning.py` 를 처음엔 "아마 K+Q 소유겠지" 하고 넘겨짚었는데,
  §2 표 어디에도 명시가 없다는 것을 다시 확인하고서야 "안전하게 안 건드리고 쪽지로
  넘긴다"로 정했다 — 표에 없는 파일을 짐작으로 고치는 것이 이번 규약이 가장 경계하는
  일이라 판단했다.
