# OPS-07 — 로그 수집·보존 기간 · **선언을 적용으로 바꾸려다, 상한 밖의 수집기 둘을 찾았다**

> 2026-09-05 · 턴 D · 차선 E(운영·영역 ④)
> 직전 상태(대장): 「compose 11개 서비스에 회전·상한 **선언은 섰다**. 적용은 다음 재기동」
> **이 문서의 수는 전부 이 기계에서 실제로 잰 것이다.** 명령과 출력 원문을 함께 적는다.

---

## 0. 한 문장 — **정본이 무엇인가**

> **감사에 답하는 것은 DB 감사 로그(`logger_auditlogs` · 보존 90일)이고, 컨테이너
> stdout 은 운영 디버깅용 단기 버퍼다.**

그리고 그 정본에는 **이번 턴에 붙은 조건**이 하나 있다 —
**지우는 자리가 실제로 돌 때만 90일이 90일이다.** 이 기계에서는 안 돈다(§3).

---

## 1. 지금 떠 있는 컨테이너 **전부**의 로그 드라이버 [실측]

```bash
for c in $(docker ps --format '{{.Names}}'); do
    echo -n "$c "; docker inspect -f '{{json .HostConfig.LogConfig}}' $c
done
```

출력 원문:

```
gx-nginx-e                 {"Type":"json-file","Config":{"max-file":"5","max-size":"10m"}}
gx-gunicorn-e              {"Type":"json-file","Config":{"max-file":"5","max-size":"10m"}}
guardianx-source-minio-1   {"Type":"json-file","Config":{}}
gx-shell                   {"Type":"json-file","Config":{}}
gx-fe-build                {"Type":"json-file","Config":{}}
redis                      {"Type":"json-file","Config":{}}
postgres                   {"Type":"json-file","Config":{}}
```

| 컨테이너 | 상한이 **걸려 있나** | 어떻게 떴나 | 선언이 **있나** | 지우는 법 |
|---|---|---|---|---|
| `gx-nginx-e` | **예** (10m × 5) | `docker run --log-opt` (턴 C) | compose 밖 | 이미 걸림 |
| `gx-gunicorn-e` | **예** (10m × 5) | `docker run --log-opt` (턴 C) | compose 밖 | 이미 걸림 |
| `postgres` | **아니오** | `docker run` | **턴 D 에 compose 로 들였다** | 재기동(§4) |
| `redis` | **아니오** | `docker run` | `compose::redis` | 재기동 |
| `guardianx-source-minio-1` | **아니오** | compose | `compose::minio` | 재생성 |
| `gx-shell` | **아니오** | `docker run` | `compose::shell` | 재기동 |
| `gx-fe-build` | **아니오** | `docker run` | **없다** | `--log-opt` 로만 |

★ **일곱 중 둘만 걸려 있다.** 그 둘은 턴 C 가 RUNBOOK 의 `--log-opt` 경고를 지켜
띄운 것이다 — 경고가 **실제로 일했다**는 뜻이고, 이 표가 그 증거다.

---

## 2. 상한이 **닿지 않는 자리 둘** — 이번 턴에 찾은 것

### ㉠ 컨테이너 **안에서 파일로** 쌓는 로그 — `--log-opt` 가 여기 안 닿는다

앞단 `gx-nginx-e` 는 `access_log /var/log/nginx/gx-front.access.log` 로 **파일에**
적는다. stdout 이 아니므로 도커의 `json-file` 회전과 아무 상관이 없고,
`nginx:alpine` 에는 logrotate 도 없다.

```
docker exec gx-nginx-e sh -c 'ls -la /var/log/nginx/'
lrwxrwxrwx  access.log -> /dev/stdout      ← 이건 stdout 이다
lrwxrwxrwx  error.log  -> /dev/stderr      ← 이것도
-rw-r--r--  gx-front.access.log  6,079,532 ← **이것만 파일이다. 상한이 없다**
```

> **컨테이너에 `--log-opt` 를 걸었다 ≠ 그 컨테이너의 로그에 상한이 걸렸다.**
> 이 절에서 하기 쉬운 **두 번째** 거짓말이고, 첫 번째(「선언이 섰다」=「보존이
> 걸렸다」)를 조심하느라 이쪽을 못 봤다.

고치는 자리는 compose 가 아니라 `nginx/gx-front.conf` 의 `access_log` 다
(`/dev/stdout` 으로 보내면 이 앵커 안으로 들어온다). **이번 턴에는 안 고쳤다** —
앞단을 다시 띄워야 하고, 그 사이 OPS-13a 의 측정이 끊긴다. 다음 사람 몫으로 남긴다.

### ㉡ 「50MB 는 140일 치」라는 **판정이 뒤집혔다**

`docker-compose.yml` 머리말은 「가장 시끄러운 수집기(postgres 363 KB/일)에 50MB 는
약 140일 치 · 상한은 평시가 아니라 사고를 위한 것」이라고 못박아 두었다.
**앞단을 세운 뒤 다시 재니 그 판정이 서지 않는다** [실측 · 부하 중 한 시간 치]:

| 수집기 | 한 시간 치 [실측] | 하루 환산 [추정] | 50MB 는 몇 시간 치인가 |
|---|---|---|---|
| `gx-gunicorn-e` stdout (접근로그) | **10,274,859 바이트** | **247 MB/일** | **약 5시간** |
| `gx-nginx-e` 파일 접근로그 | 2,122,482 바이트 | 51 MB/일 | 상한 **없음** |
| `redis` stdout | 4,958 바이트 | 119 KB/일 | — |
| `postgres` stdout | 0 바이트 | 363 KB/일 [2026-09-24] | 약 140일 |

⚠ 위 한 시간 치는 **부하를 거는 동안** 잰 것이다(OPS-13a 의 3,722 요청 × 4벌).
평시 값이 아니다 — 그러나 **운영은 평시가 아니라 부하 때 사고가 난다.**

→ 그러므로 **컨테이너 stdout 은 사고 조사에 답하지 못한다**: 어제 로그를 찾으면 없다.
그것이 §0 의 「정본은 DB 감사 로그」를 **더 중요하게** 만든다. 머리말의 옛 판정은
지우지 않고 「뒤집혔다」로 남겼다 — 판정이 어떻게 틀렸는지가 판정보다 값나간다.

---

## 3. 정본의 **지우는 자리가 이 기계에서는 안 돈다** [실측]

「보존 90일」은 `config/celery.py` 의 beat 일정 `ops-audit-purge-daily`(03:10)로
서 있다. **그 일정을 실행할 워커가 하나도 없다.**

```bash
# ① 어느 컨테이너에도 celery 프로세스가 없다
for c in $(docker ps -a --format '{{.Names}}'); do docker top $c | grep -i celery; done
(출력 없음)

# ② 브로커는 살아 있고, 워커만 없다 — **회색이 아니라 빨강이다**
docker exec -w /app gx-shell python -c "... app.control.inspect(timeout=3).ping()"
broker  : redis://redis:6379/0
beat    : {'ops-audit-purge-daily': '<crontab: 10 3 * * *>', ... 14개}
ping    : None          ← **워커 0개**
active  : None
```

```bash
docker exec redis redis-cli KEYS '*celery*'    (없음)
docker exec redis redis-cli KEYS '*pidbox*'    (없음)   ← 워커가 붙은 흔적조차 없다
docker exec redis redis-cli LLEN default       0
```

> **선언은 삭제가 아니다.** 이 환경에서 `logger_auditlogs` 는 **무한 적재**다.
> 감사 로그 표가 아직 9일치(2026-08-27 ~ )라 「90일이 지켜지는지」를 자료로는
> 가를 수 없다 — **가를 수 있는 것은 지우는 자리가 도는가뿐이고, 안 돈다.**

### 양성 대조 — **판정기가 워커를 실제로 볼 수 있는가**

「워커가 없다」를 적으려면 **있을 때 보인다**는 것을 먼저 보여야 한다. 아무 일도
안 하는 판정기도 「없다」고 말한다.

```bash
# 남의 태스크를 훔치지 않도록 **전용 큐**로 임시 워커를 하나 띄웠다
docker exec -d -w /app gx-shell sh -c \
  'python -m celery -A config worker -Q gx_e_probe_queue -c 1 -n gxprobe-e@%h -l WARNING'

PING: {'gxprobe-e@775d49d45445': {'ok': 'pong'}}          ← **보인다**
python scripts/ops_log_collectors.py
| DB 감사 로그 · logger_auditlogs | **90일 (beat ops-audit-purge-daily · 워커 1)** | …

# 치웠다
docker exec gx-shell sh -c "pkill -f 'celery -A config worker -Q gx_e_probe_queue'"
docker exec gx-shell sh -c "ps aux | grep '[c]elery' | wc -l"   → 0
```

증거: `control_worker_alive.md`(양성) · `collectors.md`(음성 · 실제 상태).

---

## 4. compose 밖 컨테이너를 안으로 들이는 절차 — **선언은 섰다. 적용은 안 했다**

`docker-compose.yml` 에 `postgres` 서비스를 **선언했다**(`profiles: ["local"]` ·
`gx_pgdata` 외부 볼륨 · `logging: *gx-logging`). 절차는
`docs/agent/RUNBOOK_로컬기동.md` **STEP 2B** 에 적었다.

```bash
docker volume inspect gx_pgdata                  # ① 자료가 이름 붙인 볼륨에 있는가
# ② 뿌리 .env 에 POSTGRES_PASSWORD 를 넣는다 (없으면 compose 가 그 자리에서 멈춘다)
docker rm -f postgres                            # ③ ⚠ 여기서 연결이 끊긴다
docker compose --profile local up -d postgres
docker network connect --alias postgres gx-main-network guardianx-source-postgres-1  # ④
docker inspect -f '{{json .HostConfig.LogConfig}}' guardianx-source-postgres-1        # ⑤ 재서 확인
```

### ⛔ **③을 하지 않았다. 왜 안 했는지 적는다**

2026-09-05 현재 `gx-shell` 안에서 다른 차선 셋이 시험 DB(`test_gx_*`)를 만들고
지우는 중이다. **postgres 를 내리면 그 셋이 한꺼번에 죽는다**(조율자 지시 · 턴 D).
`redis` · `gx-shell` · `minio` 도 같은 이유로 건드리지 않았다.

> **재기동이 필요한 조치를 「했다」로 적지 않는다.** 절차를 남기고 왜 안 했는지를
> 적는 것이 이 절의 정직한 산출이다.

`gx-fe-build` 는 compose 에 자리를 만들지 **않았다** — 프론트 빌드 결과를 꺼내려고
`sleep infinity` 로 띄운 임시 컨테이너이고(마운트 0개), compose 서비스로 만들면
`docker compose up` 이 끝나지 않는 컨테이너를 하나 더 세우게 된다. 이 하나는
`--log-opt` 로만 걸린다 — 판정기 ④가 그 자리를 계속 빨강으로 잡는다.

---

## 5. 판정기를 고쳤다 — **셋을 못 찍고 있었다**

`scripts/ops_log_collectors.py`:

| 무엇이 틀렸나 | 어떻게 고쳤나 |
|---|---|
| **목록이 낡아 「여섯을 세고 전수」라고 적었다** — 턴 C 의 앞단 둘(`gx-nginx-e`·`gx-gunicorn-e`)이 `PROJECT_CONTAINERS` 에 없었다 | 둘을 넣고, **⑤ 목록 신선도**를 새로 뒀다: 떠 있는데 목록에 없는 우리 컨테이너가 있으면 ①은 초록이 될 수 없다 |
| **컨테이너 안의 파일 로그를 한 번도 안 봤다** | `CONTAINER_FILE_LOGS` · `file_sinks()` — 총량과 **한 시간 치**(파일 자신의 시계로)를 잰다 |
| **beat 선언을 「보존 기간이 있다」로 읽었다** | 브로커 도달성과 **워커 유무**를 갈라서 잰다. 브로커에 못 닿으면 **회색**, 닿았는데 워커 0이면 **빨강** |
| compose 밖 컨테이너는 상한이 걸려 있어도 ④가 영원히 빨강이었다 | 빨강은 **상한이 실제로 없는 것**에만 남긴다 — 지울 수 없는 빨강은 다음 사람이 무시한다 |

```
python scripts/ops_log_collectors.py --self-test
self-test: 통과            # 합성 표 11갈래 · 양성·음성 대조 포함
python scripts/ops_log_collectors.py --evidence docs/agent/evidence/OPS-07/collectors.md
exit=1                     # 쟀고 실패다. 회색이 아니다
```

### 지금의 판정 (출력 원문 · `collectors.md`)

```
OK   ① 수집기 전수   수집기 9개를 전수로 셌다
FAIL ② 보존 기간    **보존 기간이 없다**(무한 적재): gx-shell · postgres · redis ·
                    minio · gx-fe-build · **앞단 파일 접근로그** · **DB 감사 로그**
OK   ③ 자라는 속도   9개의 한 시간 치를 쟀다
FAIL ④ 선언        **선언할 자리조차 없는 수집기**: gx-fe-build
```

---

## 6. 못 쟀거나 안 한 것 — **그대로 적는다**

- **재기동이 필요한 적용 전부**(postgres · redis · gx-shell · minio). 절차만 남겼다(§4).
- **앞단 파일 접근로그를 stdout 으로 돌리는 것.** 앞단 재기동이 필요하고 그 사이
  OPS-13a 측정이 끊긴다. 고칠 자리는 `nginx/gx-front.conf` 한 줄이다.
- **평시(무부하) 자라는 속도.** 이번 한 시간은 부하 중이었다 — 두 수를 섞지 않으려고
  「부하 중」이라고 적었다.
- **90일 보존이 실제로 지켜지는가.** 감사 로그가 9일치뿐이라 자료로는 못 가른다.
  가를 수 있는 것은 「지우는 자리가 도는가」뿐이고, 그것은 쟀다(안 돈다).

## 7. 다음 사람이 확인할 것 — 세 줄

1. `python scripts/ops_log_collectors.py` 를 먼저 돌려라. **exit 1 이면 쟀고 실패,
   exit 2 면 못 쟀다** — ②의 목록에 `파일 ·` 로 시작하는 줄이 있으면 그것은
   `--log-opt` 로는 안 지워진다(고칠 자리는 `nginx/gx-front.conf` 의 `access_log`).
2. 「보존 90일」을 인용하기 전에 **celery 워커가 붙어 있는지** 보라 —
   `docker exec -w /app gx-shell python -c "…inspect().ping()"` 이 `None` 이면
   그 90일은 선언일 뿐이고, 그 자리는 아무것도 지우지 않는다.
3. postgres 에 상한을 걸려면 **재기동해야 한다**(RUNBOOK STEP 2B). 다른 차선이
   `gx-shell` 에서 시험 DB 를 쓰는 동안에는 하지 마라 — 그 셋이 한꺼번에 죽는다.
