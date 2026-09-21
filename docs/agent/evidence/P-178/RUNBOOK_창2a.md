# RUNBOOK — **창 2a** (세종 창 · 30분 · 집행 조율자 · 차선 전부 정지 후 한 번)

# ★ 창 2a — **2026-09-23 (수) 12:00 KST** · C0 에서 **대표께 묻는다**

> **대표가 2026-09-21 에 일시를 주셨다.** 이 문서는 그 일시로 **박혔다.**
> 여는 사람은 **조율자**다. 이 줄 아래 「여는 날 순서」를 **위에서 아래로** 따라간다.
> 오늘(09-21) 이 저장소에서 창을 **열지 않았다** — 준비만 했다(맨 아래 「오늘 한 일」).

## 여는 날 순서 — **여덟 칸. 건너뛰지 않는다**

| 칸 | 무엇 | 어디 | 대략 | 멈춤 |
|---|---|---|---|---|
| **①** | **§1 네 조건 확인** (a 차선 정지 · b 금고 자격 둘 · c 시험 DB 역할 결정 · d 보존본) | [§1](#1-창-전에-서-있어야-할-것--넷-다-아니면-창을-열지-않는다) | 3분 | **넷 중 하나라도 ✗ 면 창을 열지 않는다** |
| **②** | **§2 기준선 ㉠㉡㉢㉣ 을 뜬다** (창 뒤에 이것과 견준다) | [§2](#2-기준선--창-전에-이-수를-떠-둔다-창-뒤에-바뀐-것만-바뀌었나를-이것과-견준다) | 3분 | — |
| **③** | **A0 보존 (5분)** — ★A2 가 「되돌릴 수 없다」가 되는 것을 막는 유일한 단계 | [A0](#a0--보존-5분--이걸-빠뜨리면-a2-가-정말로-되돌릴-수-없어진다) | 5분 | 보존본이 안 떠지면 **A부를 열지 않는다** |
| **④** | **A1 → ★A2 → A3 → A4** (`gx-shell` 재생성 + 감독) | A부 | 10분 | ★A2 · ★A3-함정 (아래 ★표) |
| **⑤** | **B1 → B2 → B3** (`--config` 절대경로 명시 · OPS-13a 재측) | B부 | 5분 | **값은 한 자도 안 바꾼다** |
| **⑥** | **★★ C0 — 여기서 멈춘다. 대표께 「계속합니까」** | [C0](#-c0--여기서-멈춤--대표-결정-필요) | — | **ⓐⓑⓒ 세 칸이 차기 전에는 C1 로 가지 않는다** |
| **⑦** | **C0-ⓒ 집행(OPS-24 회수) → C1 → C2 → C3 → C4 → C5 → C6** | C부 | 10분 | ⓒ 가 **C1 보다 먼저**다(아래 ⚠) |
| **⑧** | **§3 되돌림 표** — 되돌릴 일이 생기면 **거꾸로** | [§3](#3-되돌림--거꾸로) | — | 되돌렸으면 **사유를 그 절 아래에 적는다** |

⚠ **⑦ 안의 순서 하나만은 바꿀 수 없다**: **C0-ⓒ(시험 DB 회수)가 C4(앱 역할 전환)보다
  먼저**다. 앱이 아직 `postgres` 로 돌 때만 남의 DB 를 지울 수 있고, C4 뒤에는 `gx_migrate`
  가 그 권한을 **안 갖는다**. 미루면 되돌릴 수 없는 막다른 길이 된다(C부 머리 표 ②).

## ★ 되돌릴 수 없는 자리 **셋** — 이 셋 앞에서는 손을 멈추고 한 번 더 읽는다

| ★ | 어디 | 어느 칸 | 무엇이 안 돌아오나 |
|---|---|---|---|
| **★A2** | `docker rm -f gx-shell` | ④ | 컨테이너 레이어 — playwright·브라우저 캐시 656MB·유령 `/repo/docs` 8파일. **A0 보존본이 유일한 원본** |
| **★A3-함정** | `docker run` 에서 **`--entrypoint` 를 빼먹음** | ④ | 이미지 entrypoint 가 **개발 DB 에 `migrate` + 초기화 관리명령 스물몇 개**를 쓴다. 그 쓰기는 안 돌아온다 |
| **⛔★C7** | `ALTER ROLE … NOSUPERUSER` | — | **이번 창에서 하지 않는다.** 마지막 superuser 가 속성을 잃으면 single-user 모드 없이는 아무도 못 돌려준다 |

> ⛔ **C7 은 이번 창에 없다.** 단계 셈 16 에 들어 있지 않고, 아래 §C7 절이 그 이유를
> 적어 둔 **금지 표지**다. P-187 이 말한 「superuser 회수」는 **C4+C6** 으로 끝난다.
> C7 을 하려거든 **별도 창 · 회수증(`pg_dump`) · 되돌림 시연**을 먼저 요구하라.

## ★★ 멈추는 자리는 **하나**다 — C0

C0 은 「확인하고 넘어가는 칸」이 아니라 **대표께 묻고 답을 기다리는 칸**이다.
물을 것은 한 문장이다:

> **「창 2a 의 A부·B부가 끝났습니다. C부(역할 전환)로 계속합니까?**
> **그러려면 ⓐ 자격 넷 · ⓑ 시험 DB 를 만들 역할 · ⓒ 시험 DB 13개 회수 — 세 칸이 필요합니다.」**

세 칸이 **비어 있으면 C1 로 가지 않는다.** 비운 채로 전환하면 pytest 가 전부 죽고,
그 빨강은 「분리가 실패했다」로 읽힌다 — **그 둘은 다른 사실이다.**
C0 에서 멈추고 창을 닫아도 **A부·B부의 성과는 남는다**(A·B 는 대표 결정 없이 끝까지 간다).

---


> 2026-09-20 · 턴 X · 차선 **U56 준비** · **집행은 조율자**.
> 이 문서를 쓴 차선은 **창을 열지 않았다.** 이 턴에 DB 에 만든 역할 **0** · 바꾼 권한 **0** ·
> 돌린 `GRANT`/`REVOKE` **0줄** · 바꾼 `.env` 값 **0** · 재생성한 컨테이너 **0**.
> 증거: `SELECT rolname FROM pg_roles WHERE rolname IN ('gx_app','gx_migrate','gx_test')`
> → **빈 결과** [실측 2026-09-20 13:2x].
>
> 닫는 것 셋 (세종 P-194 · 위임 이의 #3 이 창을 2a/2b 로 쪼갠 뒤):
> **A** `gx-shell` 재생성 + entrypoint 를 `gate_servers.sh` 감독으로 (P-183) ·
> **B** `--max-requests N + jitter` → **OPS-13a 재측** ·
> **C** **P-187 역할 전환**(dry-run → 실 · superuser 회수) — **대표 결정 앞에서 멈춘다**.

---

## 0. 먼저 읽을 것 — **이 차선의 자진 오판 하나** (턴 V·W 의 내 산출물이 틀렸다)

`P-178/dry_run.md` §3 은 전환 수단으로 **`docker-compose.yml` 의 `environment:` diff** 를 냈다.
**그 diff 는 도는 시스템에 닿지 않는다.**

```
[실측 2026-09-20 13:1x]
도는 컨테이너 10개 전부 compose 라벨이 비어 있다 (scripts/gate_servers.sh 머리말 ① 과 같은 수)
뿌리 .env 가 들고 있는 키: MINIO_ROOT_USER · MINIO_ROOT_PASSWORD · MINIO_BUCKET_NAME ·
                           GX_STORAGE_CAPACITY_GB  — **DB_USER 도 DB_PASSWORD 도 없다(0줄)**
앱 넷의 DB 자격 출처: `--env-file C:/GuardianX-vault/recreate/<이름>.new.env`
                      (RUNBOOK_재생성창.md ②-c ③ 이 만든 그 파일들)
DB_USER 는 넷이 같다: sha256 앞 12자 `a942b37ccfaf` = sha256("postgres") 앞 12자
```

⇒ **compose 를 고치는 것은 선언이지 집행이 아니다** — 세종이 P-194 에서 위임 이의 #3 에
한 그 말이 **내 산출물에도 그대로 걸린다.** 아래 C부는 compose 가 아니라 **env-file 교체**로
쓴다. `docker-compose.yml` 의 diff 는 *언젠가 compose 가 이 컨테이너들을 소유하는 날*을 위한
**선언으로만** 남긴다(그날이 오기 전에는 한 줄도 집행되지 않는다).

---

## 1. 창 전에 서 있어야 할 것 — 넷 다 아니면 창을 열지 않는다

| # | 무엇 | 확인 명령 | 지금 [실측 2026-09-20 13:2x] |
|---|---|---|---|
| a | **다른 차선 정지** | 아래 §2 기준선 ㉠ (시험 DB 연결 0) | ✗ — **F(11) · S(8)** 이 잡고 있다. F 의 잰 창 12:45~14:30 |
| b | **금고 자격 둘** (`gx_app` · `gx_migrate` 비밀번호) | `ls ~/.guardianx-secrets/` | ✗ — **대표 결정 ⓐ** (§C0) |
| c | **시험 DB 를 만들 역할 결정** | — | ✗ — **대표 결정 ⓑ** (§C0) |
| d | **gx-shell 안 상태 보존본** | §A0 | ✗ — 창 직전에 뜬다 |

---

## 2. 기준선 — **창 전에 이 수를 떠 둔다.** 창 뒤에 「바뀐 것만 바뀌었나」를 이것과 견준다

```bash
# ㉠ 시험 DB · 누가 물고 있나 (OPS-24 의 그 수 · 살아 있는 것은 절대 안 지운다)
docker exec postgres psql -U postgres -d postgres -A -F' | ' -t -c "
SELECT d.datname, pg_get_userbyid(d.datdba),
       to_char((pg_stat_file('base/'||d.oid::text)).modification AT TIME ZONE 'Asia/Seoul','MM-DD HH24:MI'),
       pg_size_pretty(pg_database_size(d.datname)),
       s.numbackends, s.xact_commit
FROM pg_database d JOIN pg_stat_database s ON s.datname=d.datname
WHERE d.datname LIKE 'test%' ORDER BY s.numbackends DESC, 3;"
# ㉡ 역할 — **빈 결과여야 한다**(아직 안 만들었다는 증거)
docker exec postgres psql -U postgres -A -t -c \
  "SELECT coalesce(string_agg(rolname,','),'(빈 결과)') FROM pg_roles WHERE rolname IN ('gx_app','gx_migrate','gx_test');"
# ㉢ 기동 시각 열 줄
for c in gx-gunicorn-e gx-celery-e gx-beat-e gx-shell gx-nginx-e postgres redis \
         guardianx-source-minio-1 guardianx-source-mailpit-1 gx-fe-build; do
  printf "%-30s %s\n" $c "$(docker inspect -f '{{.State.StartedAt}}' $c)"; done | tee /c/GuardianX-vault/recreate/startedat.pre.2a
# ㉣ gunicorn 이 **실제로 무엇을 물고 도는가** (B부의 기준선 · §B 참조)
docker exec gx-gunicorn-e sh -c 'cd /app && python -m gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 --workers 4 --threads 4 --worker-class gthread --timeout 120 \
  --access-logfile - --error-logfile - --check-config --print-config' | \
  grep -E "^(config|max_requests|max_requests_jitter|keepalive|workers|worker_class|preload_app) "
```

**기준선 실측값 [2026-09-20 13:2x]** — 창 뒤에 이것과 대 본다:

```
시험 DB 13개 · 합 426MB · 소유자 전부 postgres · 살아 있는 것 2 (test_gx_f 11 · test_gx_s 8)
pg_roles(gx_app·gx_migrate·gx_test) = (빈 결과)
public 스키마 표 231 · 로그인 superuser 둘(postgres · pgroot) · 로그인 가능 역할은 그 둘뿐
PostgreSQL 18.1 · PUBLIC 이 schema public 에 USAGE,CREATE 를 갖고 있다
gunicorn: config = ./gunicorn.conf.py · max_requests 200 · jitter 50 · keepalive 75 · preload_app True
          workers 4 · worker_class gthread   ← 파일은 2 · uvicorn 이라 적혀 있다(명령줄이 덮는다)
```

---

# A부 — `gx-shell` 재생성 + entrypoint 를 `gate_servers.sh` 감독으로

> 되돌릴 수 있는 단계 셋 · **되돌릴 수 없는 단계 하나(★A2)** · **★함정 하나(A3)**.

### A0 — 보존 (5분) · **이걸 빠뜨리면 ★A2 가 정말로 되돌릴 수 없어진다**

`gx-shell` 안 **컨테이너 레이어**에만 있는 것 [실측 2026-09-20 13:3x]:

```
playwright 1.62.0 · py-vapid 1.9.1 · pywebpush 1.14.1        (pip)
/root/.cache/ms-playwright                                    656 MB
/repo/docs                                                    ★ 유령 8파일 — 아래 A4-⚠ 을 보라
```

살아남는 것(호스트 bind 라 안 사라진다 — **보존 목록에 넣지 않는다**):
`/app`(=`backend/`) · `/app/_fe_dist` 31MB · `/repo/{backend,frontend,scripts}` · `/docs` ·
볼륨 `gx_backup_vault_e:/backup` · `/tmp/gx_spa_server.py`(창 뒤 `gate_servers.sh` 가 `/repo/scripts`
에서 **다시 복사한다** · D-493).

```bash
mkdir -p /c/GuardianX-vault/recreate/gx-shell-extras-2a
docker cp gx-shell:/root/.cache/ms-playwright /c/GuardianX-vault/recreate/gx-shell-extras-2a/
docker exec gx-shell python -m pip freeze > /c/GuardianX-vault/recreate/gx-shell-extras-2a/pip-freeze.txt
docker exec gx-shell sh /repo/scripts/gate_servers.sh stop        # 게이트 둘을 곱게 내린다
```

### A1 — 형상 뜨기 (2분) · **되돌리기의 원본**

```bash
R=/c/GuardianX-vault/recreate
docker inspect gx-shell --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -vE '^(PATH|LANG|HOME|HOSTNAME|GPG_KEY|PYTHON_VERSION|PYTHON_SHA256|LD_LIBRARY_PATH)=' \
  | grep -v '^$' > $R/gx-shell.2a.env
docker inspect gx-shell > $R/gx-shell.2a.json
wc -l < $R/gx-shell.2a.env        # 기준선: 49 중 걸러 낸 나머지
```

### ★A2 — `docker rm -f gx-shell` (1분) · **되돌릴 수 없다**

컨테이너 레이어가 사라진다. A0 의 보존본이 **유일한 원본**이다.
동시에 사라지는 것 하나 더 — **그것이 좋은 일이다**: §A4-⚠.

```bash
docker rm -f gx-shell
```

### A3 — 재생성 (4분) · ★**함정: `--entrypoint` 를 빼면 되돌릴 수 없는 쓰기가 일어난다**

```
[실측] 이미지 ENTRYPOINT = ["/entrypoint.sh"] 이고 그 파일은
  celery worker & · celery beat & · **python manage.py migrate** ·
  initialize_base_data · initialize_grid_data · migrate_menu_translations ·
  … 관리 명령 **스물몇 개** … · exec gunicorn -c gunicorn.conf.py config.asgi:application
```
⇒ `--entrypoint` 를 빼거나 잘못 적으면 `gx-shell` 이 **개발 DB 에 초기화 자료를 쓴다.**
   그 쓰기는 **되돌릴 수 없다**(그래서 compose 주석이 「entrypoint 를 비워 자동 migrate 를
   끊는다 — 이 두 줄이 이 서비스의 존재 이유다」라고 적혀 있다).
   **감독 명령은 이미지 entrypoint 를 부르지 않는다.** 아래 그대로 쓴다.

```bash
R=C:/GuardianX-vault/recreate; S=C:/GuardianX/guardianx-source
LOG="--log-opt max-size=10m --log-opt max-file=5"
MSYS_NO_PATHCONV=1 docker run -d --name gx-shell --network gx-main-network --restart unless-stopped $LOG \
  --env-file $R/gx-shell.2a.env \
  -v $S/backend:/app -v $S/backend:/repo/backend -v $S/scripts:/repo/scripts \
  -v $S/frontend:/repo/frontend -v $S/docs:/docs -v gx_backup_vault_e:/backup \
  -w /app --entrypoint sh guardianx-backend:latest -c \
  'sh /repo/scripts/gate_servers.sh start; while :; do sleep 60; \
   sh /repo/scripts/gate_servers.sh status >/dev/null 2>&1 || sh /repo/scripts/gate_servers.sh start; done'
# 보존본 되넣기 (6분)
docker cp /c/GuardianX-vault/recreate/gx-shell-extras-2a/ms-playwright gx-shell:/root/.cache/
docker exec gx-shell python -m pip install playwright==1.62.0 pywebpush==1.14.1 py-vapid==1.9.1
```

⚠ `--restart unless-stopped` 를 **그대로 둔다**(지금도 그 값이다). P-183 이 말한
「재시작 정책이 **프로세스까지** 덮게」는 두 겹이다: 컨테이너는 도커가, 그 안 서버 둘은
위 `while` 감독이 되살린다. 감독 없이 `sleep infinity` 로 두면 컨테이너만 살고 문은 죽는다.

### A4 — 확인 (3분) · **「띄웠다」가 아니라 「대답한다」를 본다**

```bash
docker exec gx-shell sh /repo/scripts/gate_servers.sh status   # api 8000 · spa 3002 둘 다 「대답한다」
docker exec gx-shell sh -c 'cat /tmp/gx_gates/api.by'          # ← 「손(표식 없음)」이 아니어야 한다
docker logs --tail 20 gx-shell
python scripts/verify_live_freshness.py --all; echo "EXIT=$?"
curl -s -o /dev/null -w 'front=%{http_code}\n' http://localhost:8500/admin/login/   # 200
```

**P-183 「손으로 띄운 프로세스 0」의 닫는 조건**: `gate_servers.sh status` 의 *띄운 것* 칸이
두 줄 다 `gate_servers.sh <시각>` 이고, 그 시각이 **컨테이너 기동 시각 뒤**여야 한다.
사람이 `docker exec … start` 를 친 판과 감독이 띄운 판은 **표식이 같다** — 그래서 시각으로
가른다. 기동 시각보다 뒤이면서 아무도 안 쳤으면 그것은 감독이 띄운 것이다.

⚠ **재생성이 공짜로 고치는 것 하나 — 그리고 그것이 판정을 바꾼다.**
지금 `gx-shell` 의 `/repo/docs` 는 **마운트가 아니라 컨테이너 레이어에 남은 유령**이다
[실측: `docker inspect` 의 Mounts 에 없는데 `ls` 하면 있다 · 파일 **8개** · `P-105`·`P-159` 등
지난 실행이 거기 쓴 것]. 스크립트 여럿이 「`/repo/docs` 가 있으면 거기, 없으면 `/docs`」로
고르므로(`capture_screens.py:1662` · `measure_onboarding_t.py:1501` · `walk_scenarios.py:1146`),
**재생성 뒤 그 갈래가 바뀐다.** 창 뒤 판정이 창 전과 다르면 **먼저 이 줄을 의심하라** —
제품이 바뀐 것이 아니다. (턴 W 에 `verify_tenant_scope`·`verify_write_auth` 가 「판정 불가」로
끝난 그 자리이기도 하다.) 창에서 `-v $S/docs:/repo/docs` 를 **더하지 않는다** — 자리를 하나로
못 박는 것은 소유 차선의 결정이고, 창은 그 결정을 대신하지 않는다.

**A부 되돌림** — `docker rm -f gx-shell` 뒤 A1 의 `gx-shell.2a.env`·`.json` 그대로,
`--entrypoint sleep guardianx-backend:latest infinity` 로 다시 띄우고 A0 보존본을 되넣는다.
그러면 창 전과 같다. **단 컨테이너 레이어의 유령 `/repo/docs` 8파일은 돌아오지 않는다**(★A2).

---

# B부 — `--max-requests N + jitter` → OPS-13a 재측

### B1 — **값: `max_requests = 200` · `max_requests_jitter = 50` — 바꾸지 않는다.**

**왜 그 값인가 — 이 저장소가 이미 두 번 재서 답했다** (`backend/gunicorn.conf.py` 주석):

| 재 본 것 | 결과 | 판정 |
|---|---|---|
| `200 + rand(0..50)` (평균 225 · 폭 50) | 502 **3건** / 3,600요청 | 지금 값 |
| `125 + rand(0..200)` (평균 225 · 폭 200) | 502 **5건** — **나빠졌다** | ⛔ 되돌렸다(턴 C). 평균은 같아도 **최소 주기가 200→125** 로 짧아져 이른 재활용이 당겨졌다 |
| `max_requests = 0` (재활용 끔) | 502 **0건** · 재시도 0 · p95 도 빨라짐 | ⛔ 되돌렸다(턴 D). **결함을 고친 0 이 아니라 숨긴 0** 이고, 누수 대비를 버린다 |

⇒ **키우는 것도 금지다**(200→2000 이면 502 가 1/10 이 되고 그만큼 덜 재현된다).
⇒ **줄이는 것도 금지다**(턴 C 가 실측으로 기각했다).
⇒ 그러므로 창 2a 에서 **값에는 남은 자유도가 없다.** 남은 것은 **「그 값이 실제로 걸려 있나」**다.

### B2 — **진짜 물음: 값이 우연히 걸려 있다** [실측 2026-09-20 13:2x]

도는 명령줄에 `-c gunicorn.conf.py` 가 **없다**:
```
Entrypoint=["python"] Cmd=["-m","gunicorn","config.wsgi:application","--bind","0.0.0.0:8000",
           "--workers","4","--threads","4","--worker-class","gthread","--timeout","120", …]
```
`--print-config` 로 재니 그래도 `config = ./gunicorn.conf.py` 였다 — gunicorn 이 **cwd 의
`gunicorn.conf.py` 를 자동으로 집는** 덕이고, `/app` = `backend/` 라 우연히 그 파일이 거기 있다.
**즉 502 를 막는 값이 「작업 디렉터리가 우연히 맞아서」 걸려 있다.** `-w` 가 바뀌거나 파일이
옮겨지면 조용히 gunicorn 기본값으로 떨어지고, 그 기본값은 **`max_requests=0` · `keepalive=2`** —
`keepalive 2` 는 이 파일 주석이 **「그 값이 502 를 만들었다」**고 적어 둔 바로 그 수다.

### B2-b — ⚠⚠ **위 문단의 근거가 틀렸다. `config =` 줄은 거짓말한다** [실측 2026-09-20 15:5x · 턴 Y · U56]

위에서 「`--print-config` 로 재니 그래도 `config = ./gunicorn.conf.py` 였다」를 **걸렸다는
근거**로 썼다. **그 줄은 근거가 아니다** — gunicorn 은 파일을 **못 찾아도 그 문자열을 그대로
찍는다**(기본값 라벨이다). 같은 순간 세 갈래를 `gx-shell` 에서 재서 갈랐다(**재기동 0**):

| 갈래 | `config` 줄 | `keepalive` | `max_requests` | `workers` | `worker_class` |
|---|---|---|---|---|---|
| **A** `cwd=/app` · 플래그 없음 | `./gunicorn.conf.py` | **75** | **200** | 2 | UvicornWorker |
| **B** `cwd=/` · 플래그 없음 | `./gunicorn.conf.py` | **2** | **0** | 1 | sync |
| **C** `cwd=/` · `--config /app/…` | **`/app/gunicorn.conf.py`** | **75** | **200** | 2 | UvicornWorker |

```bash
# 재는 법 (읽기만 한다 — 바인드하지 않고 찍고 끝난다)
docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell sh -c \
  "cd / && python -m gunicorn --config /app/gunicorn.conf.py config.wsgi:application \
   --print-config" | grep -E '^(config|keepalive|max_requests) '
```

★ **A 와 B 의 `config` 줄이 같다.** 갈리는 것은 **값**뿐이다. 그러니 「걸렸는가」는
**경로 줄이 아니라 `keepalive` 로 묻는다** — **75 면 걸렸고 2 면 안 걸렸다.**
그리고 **B 가 곧 떨어졌을 때의 모습**이다: `keepalive 2` · `max_requests 0` · 워커 하나 · sync.
`keepalive 2` 는 `gunicorn.conf.py` 주석이 **「그 값이 502 를 만들었다」**고 적어 둔 그 수다.

**창에서 할 일 — 값이 아니라 명시** (1줄 · **C 갈래를 그대로 박는다**):
```bash
# 앱 셋을 다시 띄울 때(C4 에서 어차피 다시 띄운다) 명령줄에 이 한 토막을 더한다
… python -m gunicorn config.wsgi:application --config /app/gunicorn.conf.py \
      --bind 0.0.0.0:8000 --workers 4 --threads 4 --worker-class gthread --timeout 120 \
      --access-logfile - --error-logfile -
```
⚠ `-c` 가 아니라 **`--config` 절대 경로**다. 상대 경로(`-c gunicorn.conf.py`)는 **cwd 의존을
그대로 남긴다** — 못 박는 것이 이 한 줄의 전부인데 그러면 아무것도 안 박은 것이다.
⚠ `--config` 는 **먼저** 읽히고 뒤의 플래그가 덮는다. 그래서 아래 「덮는 넷」은 그대로
4/gthread/120/threads4 로 돈다 — 바뀌는 것은 **안 덮는 값이 우연에 안 매달리는 것** 하나다.

**적용 뒤 확인 한 줄**(창 안 · C5 와 함께):
```bash
docker exec gx-gunicorn-e python -m gunicorn --config /app/gunicorn.conf.py \
  config.wsgi:application --print-config | grep -E '^(config|keepalive) '
# → config = /app/gunicorn.conf.py · keepalive = 75   (2 면 안 걸린 것이다)
```
⚠ 명령줄 넷(`workers 4` · `gthread` · `timeout 120` · `threads 4`)은 **파일 값을 덮는다**
(파일에는 `workers 2` · `uvicorn.workers.UvicornWorker` · `timeout 30` 이라 적혀 있다).
덮는 것 자체는 결함이 아니지만 **파일이 읽는 사람에게 거짓말한다.** 문구 정정은 `gunicorn.conf.py`
소유 차선(U56)이 창 밖에서 한다 — 이 턴에 **주석만** 달아 두었고 **값은 한 자도 안 바꿨다**.

### B3 — 재측 (OPS-13a)

```bash
python scripts/verify_perf_budget.py            # 같은 부하 · 502 수와 재활용 수를 함께 읽는다
docker logs gx-gunicorn-e --since 10m 2>&1 | grep -c "Autorestarting worker after current request"
```
**읽는 법**: 502 **0건**이 나오면 **먼저 재활용 수를 보라.** 재활용이 0 이면 그 0 은
「고친 0」이 아니라 `--config` 가 또 안 걸린 것이다(턴 D 의 그 0).
⚠ 그리고 **`config =` 줄로 확인하지 말 것** — B2-b 가 잰 대로 그 줄은 안 걸려도 같다.
**`keepalive` 가 75 인가 2 인가**로 묻는다.

---

# C부 — P-187 역할 전환 · **「무엇을 먼저 만들고 무엇을 나중에 회수하는가」**

> **이 부의 본체는 순서다.** 규칙 한 줄: **만드는 것이 전부 먼저, 회수는 전부 나중.**
> 그 사이에 **「새 자격으로 실제로 붙어 본다」**가 들어간다. 이 셋의 순서를 바꾸면
> 중간에 앱이 DB 에 못 붙고, 못 붙는 동안은 되돌릴 자격도 확인할 수 없다.

### ★ 집행 순서 — **OPS-24(회수)가 C4(앱 전환)보다 먼저다** (턴 Y 반영 · U56)

단계 수는 그대로 **16**이다(C0 이 한 단계이고 ⓐⓑⓒ 는 그 안의 칸이다). 바뀐 것은
**ⓒ 의 집행이 어느 칸에 놓이는가**이고, 그것이 이 창의 유일한 순서 제약이다:

| 차례 | 무엇 | 되돌아가나 | 왜 이 자리인가 |
|---|---|---|---|
| ① | **C0-ⓐⓑ** 대표 결정 두 칸 | — | 비면 여기서 멈춘다 |
| ② | **C0-ⓒ 집행 = OPS-24 회수** (세 근거 재측 → 연쇄 표 → 스냅샷 → `DROP DATABASE`) | ❌ 아니오 | **앱이 아직 `postgres` 로 돈다** — 지울 권한이 지금은 있고 C4 뒤에는 **없다**(소유자 전부 postgres · `CREATEDB` 로는 못 지운다) |
| ③ | **C1 · C2** 역할 만들기·권한 주기 | 예 | 만드는 것이 전부 먼저 |
| ④ | **C3** 새 자격으로 실제로 붙어 본다 | 예(읽기·ROLLBACK) | 옮기기 전에 확인 — 이 단계가 순서의 심장 |
| ⑤ | **C4** 앱을 옮긴다 | 예 | ②가 안 끝났으면 **여기서 pytest 가 전부 죽는다** |
| ⑥ | **C5 · C6** 기동 확인 · superuser 회수 | 예 | 회수는 전부 나중 |
| ⑦ | **⛔★C7** `NOSUPERUSER` | ❌ | **이번 창에서 하지 않는다**(§4) |

⚠ **②를 ⑤ 뒤로 미루면 되돌릴 수 없는 막다른 길이 된다** — `gx_migrate` 는 남의 DB 를
못 지우고, 되돌리려면 앱을 도로 `postgres` 로 옮겨야 한다(C4 를 두 번 친다).
⚠ **②는 삭제다. 그러므로 §1-1 규약을 탄다: 연쇄 표 → 스냅샷 → 집행.** 회수 후보마다
세 근거(㉠㉡㉢)를 **창에서 다시 재고**, 지우기 전에 목록과 크기를 적어 둔다 —
「13개 중 셋 · 95MB」는 **지난 사진**이고, 사진으로 지우면 남의 것을 지운다.

## ★★ C0 — **여기서 멈춤 — 대표 결정 필요**

**이 세 칸이 비어 있으면 C1 로 가지 않는다.** 비운 채로 전환하면 **pytest 가 전부 죽고**,
그 빨강은 「분리가 실패했다」로 읽힌다 — 그 둘은 다른 사실이다(OPS-24 를 OPS-23 과 가른 이유).

| | 무엇 | 왜 이 차선이 안 골랐나 | 채워야 할 자리 |
|---|---|---|---|
| **ⓐ** | 뿌리 `.env` 의 **값 넷** — `DB_APP_USER` · `DB_APP_PASSWORD` · `DB_MIGRATE_USER` · `DB_MIGRATE_PASSWORD` | 값을 만드는 것은 대표 결정(D-204). 이름만 `.env.example:186~211` 에 **전부 주석으로** 서 있다 | `~/.guardianx-secrets/` 금고 파일 (`cred3_*` 과 같은 규약) |
| **ⓑ** | **시험 DB 를 만들 역할** — ㉠ `gx_migrate` 에 `CREATEDB` 를 준다 / ㉡ 시험 전용 셋째 역할 `gx_test` 를 둔다 | `p178_app_db_roles.sql` 은 **어느 쪽도 안 골랐다**. 둘 다 NOCREATEDB 인 채로 전환하면 pytest 가 `CREATE DATABASE test_gx_*` 에서 한 줄도 못 돈다 | SQL ① 에 `CREATEDB` 를 넣거나 역할을 하나 더 |
| **ⓒ** | ★ **남은 시험 DB 13개의 회수** (= OPS-24) | **이것이 새로 드러난 셋째 결정이다** — 아래 |

### ⓒ 가 왜 **결정이자 순서 제약**인가 — [실측 2026-09-20 13:2x]

```
시험 DB 13개 · 소유자 **전부 postgres** · 합 426MB
```
`DROP DATABASE` 는 **소유자이거나 superuser** 여야 한다. `CREATEDB` 만으로는 못 지운다.
⇒ `gx-shell` 을 `gx_migrate` 로 옮기는 순간, **이미 있는 13개를 만나는 pytest 는
`--create-db`/`--reuse-db` 어느 쪽이든 「permission denied to drop database」로 죽는다.**
CREATEDB 를 줘도(ⓑ㉠) **안 낫는다** — 새로 만드는 권한과 남의 것을 지우는 권한은 다르다.

⇒ **순서 제약**: **OPS-24(회수)가 C4(앱 역할 전환)보다 먼저다.** 이 두 절을 가른 것이
   행정이 아니라 **집행 순서**였다는 것이 여기서 처음 수로 나온다.

**회수 규약 — 「한 번의 삭제」가 아니라 세 근거를 다 만족할 때만** (OPS-24 의 본체):

| 근거 | 재는 법 | 왜 |
|---|---|---|
| ㉠ **지금 아무도 안 붙었다** | `pg_stat_database.numbackends = 0` **그리고** `pg_stat_activity` 에도 없다 — **두 출처** | 붙어 있는 것을 지우면 **남의 빨강**을 만든다 |
| ㉡ **기동 이래 한 트랜잭션도 없었다** | `xact_commit = 0` (창: `pg_postmaster_start_time()` 이래) | 「이름이 남았을 뿐」과 「도는 차선의 것」을 가른다 |
| ㉢ **디렉터리가 그 창보다 오래됐다** | `pg_stat_file('base/'||oid)` 의 `modification` | ㉡ 만 쓰면 기동 직후엔 전부 0 이라 **전부 지워도 된다고 나온다** |

**지금 이 규약이 고르는 것** [실측 2026-09-20 13:2x · postmaster 기동 09-18 12:24 · 창 2일 1시간]:

```
회수 후보 3 : test_database_guardianx (31MB) · test_database_guardianx_e2e (32MB) · test_gx_u3b (32MB)
              → 합 **95MB**
살아 있음 2 : test_gx_f (11연결) · test_gx_s (8연결)   ← **절대 안 지운다**
남김    8 : 나머지 (xact_commit 3,894~6,893 — 이 창 안에 돌았다)
```

⚠ **창 2b 의 「시험 DB 4 삭제(127MB)」는 이제 맞지 않는다.** 그 수는 지난 턴의 사진이다.
  창에서 **다시 재서** 고르라 — 목록을 박아 두면 그 목록이 다음 턴에 남의 것을 지운다.

⚠ **재는 순간의 사진을 창까지 들고 가지 말라 — 40분이면 바뀐다** [실측 2026-09-20]:
  13:2x 와 14:0x 두 판 모두 **총수 13** 인데 그 사이에 `test_gx_s` 가 사라지고
  `test_gx_u56` 이 생겼으며 `test_gx_u24` 는 **재생성**됐다(`xact_commit` 3,894 → 691).
  **회수 후보 셋은 두 판 모두 같았다** — 규약이 실제로 도는 것과 버려진 것을 가른다는 뜻이다.
  그래도 **창에서 다시 재라.**

⚠ **이름만 보고 고르지 말라 — 총수는 거짓말한다.** 턴 V 12 → 턴 W 12 → 지금 **13** 인데
  **한 벌이 계속 돈다**: 턴 W 에 있던 `test_gx_u56` 은 사라졌고 `test_gx_f`·`test_gx_s` 가
  새로 생겼다. **총수가 제자리인 것은 안정이 아니라 덮어씀이다.**

## C1 — 역할 둘을 **만든다** (되돌릴 수 있다 · `DROP ROLE`)

```bash
docker exec -i postgres psql -U postgres -d database_guardianx -q -v ON_ERROR_STOP=1 \
  -v app_password="$(…금고…)" -v migrate_password="$(…금고…)" \
  < docs/agent/evidence/P-178/p178_app_db_roles.sql
```
**이 단계에서 앱은 아직 `postgres` 로 돈다.** 아무것도 안 끊긴다.
되돌림: `DROP ROLE gx_app, gx_migrate;` — SQL ⑥ 이 **소유권을 안 옮겼으므로** 소유물이 0 이라
바로 지워진다(그것이 `REASSIGN OWNED` 를 일부러 안 넣은 이유다).

⚠ SQL ②③ 의 `REVOKE ALL … FROM PUBLIC` 이 **이 창에서 유일하게 남을 건드리는 줄**이다.
  걱정할 것 없다는 것을 쟀다: **로그인 가능한 역할은 `postgres`·`pgroot` 둘뿐이고 둘 다
  superuser** 라 ACL 을 통과한다 [실측]. ⓑ㉡ 로 `gx_test` 를 만들기로 했다면 그 역할에도
  `GRANT USAGE ON SCHEMA public` 을 **같은 판에서** 줘야 한다 — PUBLIC 에 기대면 안 된다.
  (이 DB 는 PostgreSQL **18.1** 인데 PUBLIC 이 `USAGE,CREATE` 를 갖고 있다 — 18 의 기본이
  아니다. 누군가 되돌려 준 것이고, 그래서 이 REVOKE 는 실제로 무언가를 지운다.)

## C2 — 권한을 **준다** (되돌릴 수 있다 · `REVOKE`)

SQL ②~⑤ 가 그것이다. **③ 시퀀스**(`GRANT USAGE, SELECT ON ALL SEQUENCES`)와
**⑤ `ALTER DEFAULT PRIVILEGES`** 를 빠뜨리지 말라 — 전자는 **모든 INSERT** 가 죽고,
후자는 **다음 마이그레이션이 만든 표**에서 죽는다(장애가 배포 **다음날** 처음 보인다).

## C3 — ★ **앱을 옮기기 전에 새 자격으로 실제로 붙어 본다** (이 단계가 순서의 심장)

```bash
# 되는 것 (읽기·쓰기·시퀀스) · 안 되는 것 (DDL) 을 **둘 다** 본다 — 되는 것만 재면 절반이다
docker exec -e PGPASSWORD="$(…금고…)" postgres psql -U gx_app -d database_guardianx -A -t -c "
  SELECT 'select_ok=' || count(*) FROM django_migrations;" -c "
  BEGIN; CREATE TABLE _c3_probe(id int); ROLLBACK;"   # ← **반드시 permission denied 여야 한다**
```
**읽는 법**: 두 줄이 다 「됐다」면 **분리가 안 된 것**이다. 둘째 줄이 `permission denied for
schema public` 로 죽어야 C4 로 간다. 여기서 실패하면 **C4 를 하지 않는다** — 아직 앱은
돌고 있고, C1·C2 만 되돌리면 창 전이다.

## C4 — 앱을 옮긴다 (되돌릴 수 있다 · 옛 env-file 로 재생성)

**compose 가 아니라 env-file 이다**(§0). `--env-file` 사본을 만들고 앱 넷을 **재생성**한다
(`docker restart` 로는 환경이 안 바뀐다).

```
gx-gunicorn-e · gx-celery-e · gx-beat-e  →  DB_USER/DB_PASSWORD = gx_app     (DDL 없음)
gx-shell                                 →  DB_USER/DB_PASSWORD = gx_migrate (마이그레이션·시험)
```
⚠ `gx-shell` 줄은 **C0-ⓑ 와 C0-ⓒ 가 둘 다 끝난 뒤**에만 친다. 아니면 pytest 가 전부 죽는다.
⚠ A부에서 이미 `gx-shell` 을 한 번 만들었다 — C4 에서 **또** 만든다. 한 창에서 두 번 만드는
  것이 싫으면 **A3 를 C4 뒤로 미루면 된다.** 그러나 C0 가 비어 있으면 C부 전체가 멈추므로,
  **A부를 먼저 두었다**: A부는 대표 결정 없이 끝까지 간다.

## C5 — 기동을 본다 · **`permission denied` 를 센다**

```bash
docker logs --tail 50 gx-gunicorn-e
docker logs gx-gunicorn-e gx-celery-e gx-beat-e --since 30m 2>&1 | grep -ci "permission denied"
```
⚠ `dj_db_conn_pool` 은 자격을 **기동 때** 잡는다 — 틀리면 첫 요청이 아니라 **기동에서** 죽는다.
   그것이 낫다(조용히 반쯤 도는 것보다).
⚠ **0 을 초록으로 적지 않는다.** `rj-core`/`dj-core` 번들 안의 DDL 은 이 저장소의 grep 이
   못 읽었다(dry_run §4-4). **하루 돌려 본 0** 만 0 이다. 창 안의 0 은 「아직 안 나왔다」다.

## C6 — **superuser 회수** (되돌릴 수 있다 — 금고에 옛 값이 있을 때만)

**회수는 「앱이 superuser 자격을 더 이상 쓰지 않게 하는 것」이다.** 그 실질은 C4 에서 이미
끝났다. C6 는 **옛 자격을 무효화**하는 마무리다:

```bash
# postgres 역할의 비밀번호를 새 값으로 (SCRAM 검증자로 싣는다 — 평문이 로그에 안 남는다)
#   RUNBOOK_재생성창.md ②-a 와 같은 규약 · 되돌림도 거기 「되돌리기」 절과 같다
```
⚠ 순서: **C5 가 조용한 것을 본 뒤.** 앱이 새 자격으로 도는 것을 확인하기 전에 옛 자격을
  무효화하면 되돌아갈 곳이 없다.
⚠ `pgroot` 는 **그대로 둔다.** 사람의 둘째 통로가 없으면 다음 사고에서 아무도 못 들어간다.

## ⛔★ C7 — `ALTER ROLE … NOSUPERUSER` — **이번 창에서 하지 않는다**

**되돌릴 수 없는 단계다.** 마지막 superuser 가 superuser 를 잃으면 **single-user 모드로
서버를 다시 띄우기 전에는 아무도 그것을 돌려줄 수 없다**(컨테이너 DB 에서 그 짓은 창 30분에
들어가지 않는다). P-187 이 말한 「superuser 회수」는 **C4+C6** 으로 충분하다 — 앱이 더 이상
superuser 를 들지 않는 것이 회수이고, `postgres` 역할에서 속성을 뽑는 것은 **다른 일**이다.
그 일을 하려거든 **별도 창 · 회수증(`pg_dump`) · 되돌림 시연을 먼저** 요구하라.

---

## 3. 되돌림 — **거꾸로**

| 되돌리는 것 | 명령 | 되돌아가나 |
|---|---|---|
| C6 | `ALTER ROLE postgres PASSWORD <옛 검증자>` (금고의 창 전 값) | **예** — postgres 역할 비밀번호엔 「최근 사용」 거절이 없다 |
| C4 | 앱 넷을 `docker rm -f` 뒤 **창 전 `.new.env`** 로 다시 `docker run` → 앞단 확인 | **예** |
| C3 | 되돌릴 것 없음(읽기·ROLLBACK) | — |
| C2 | `REVOKE` (SQL ②~⑤의 역) | **예** |
| C1 | `DROP ROLE gx_app, gx_migrate;` (소유물 0) | **예** |
| C0-ⓒ | 지운 시험 DB | ❌ **아니오 — 지운 것은 안 돌아온다.** 그러나 시험 DB 는 **다시 만들면 되는 것**이다(pytest 가 만든다). 회수증이 필요한 자료가 아니다 |
| B | 값 안 바꿨다 · `--config` 는 명령줄이라 다음 재생성에서 빠진다 | **예** |
| ★A2 | A1 의 `gx-shell.2a.env`/`.json` 으로 다시 `docker run --entrypoint sleep … infinity` + A0 보존본 되넣기 | **부분** — 컨테이너 레이어의 유령 `/repo/docs` 8파일은 **안 돌아온다** |

**되돌렸으면 사유를 이 절 아래에 적는다** — 적지 않으면 다음 사람이 같은 것을 또 시도한다.

---

## 4. 이 창의 ★ 셈 — **되돌릴 수 없는 자리 셋**

| ★ | 어디 | 왜 |
|---|---|---|
| **★A2** | `docker rm -f gx-shell` | 컨테이너 레이어(playwright·브라우저 656MB·유령 `/repo/docs`)가 사라진다. **A0 보존본이 유일한 원본** |
| **★A3-함정** | `--entrypoint` 를 빼먹음 | 이미지 entrypoint 가 **개발 DB 에 migrate + 초기화 스물몇 개**를 쓴다. 그 쓰기는 안 돌아온다 |
| **⛔★C7** | `ALTER ROLE … NOSUPERUSER` | 마지막 superuser 를 잃으면 single-user 모드 없이는 못 돌아온다. **이번 창에서 하지 않는다** |

단계 셈: **A부 5 · B부 3 · C부 8(C0 포함) = 16 단계** · 그중 ★ **셋**(위) ·
**「여기서 멈춤 — 대표 결정 필요」 한 자리(C0)에 결정 세 칸(ⓐⓑⓒ)**.

---

## 5. 오늘(2026-09-21 · 턴 Z · 차선 U56) 이 문서에 한 일 — **그리고 안 한 일**

**한 일**: 대표가 준 일시(**2026-09-23 12:00 · C0 에서 대표께 묻는다**)를 문서 머리에 박고,
여는 날 조율자가 그대로 따라갈 수 있게 **여덟 칸 순서표**·**★셋 표**·**C0 멈춤 문장**을
맨 위로 올렸다. 본문(A·B·C 각 절·되돌림 표·§4)은 **한 줄도 안 고쳤다** — 순서를 위로
끌어올린 것이지 절차를 바꾼 것이 아니다.

**안 한 일 — 이 턴에 창을 열지 않았다**:

```
만든 역할 0 · 바꾼 권한 0 · 돌린 GRANT/REVOKE 0줄 · 지운 DB 0개
바꾼 .env 값 0 · 재생성한 컨테이너 0 · docker rm -f 0회
```

⚠ **§1·§2 의 [실측] 값은 2026-09-20 13:2x 의 사진이다.** 창은 09-23 이다 —
  **사진으로 지우지 말라.** 특히 §C0-ⓒ 의 「회수 후보 셋 · 95MB」는 **창에서 다시 잰다**
  (그 절의 ⚠ 두 개가 40분 만에 목록이 바뀐 것을 수로 적어 두었다).
