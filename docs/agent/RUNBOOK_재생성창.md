# RUNBOOK — 컨테이너 재생성 창 (대표 결정 ③ · 30분)

> 2026-09-15 · 턴 Q · 차선 E 준비 · 집행 조율자 · **대표 승인 뒤에만 연다**(WO-01 §9 ③ · 운영계는 대표 한 마디 뒤).
> 닫는 것: **자격 3**(P-138) → **`/backup` 마운트**(OPS-12a) → **운영 프로필 판정 7/7**(SEC-18a) → **상한 반영**(P-139).
> 잠금 정본: `docs/agent/evidence/DA-05/blockers.yaml:1606` `PLACEHOLDER_CREDENTIALS_BAKED_INTO_CONTAINERS` —
> 이 쪽은 그 `unlock_step` ①~④ 를 명령으로 편 것이다.

**규칙 셋.** ① 값은 출력하지 않는다 — 치환은 아래 스크립트가 하고 화면에는 줄 수만 나온다(P-135 불변).
② 금고는 두 자리다(`RUNBOOK_로컬기동.md` 와 같은 말): 형상 덤프는 **`C:\GuardianX-vault\recreate\`**(STEP 2B ①과 같은 자리 ·
저장소 밖 · D-204), 새 자격은 **`~/.guardianx-secrets/`**(D-002 · `.gitignore:73` · 사용자 한 명 ACL).
③ 한 단계의 확인이 아니면 **다음 단계로 가지 않는다** — 되돌리기는 맨 아래, 원본은 ①의 덤프다.

**창 전에 서 있어야 할 것 — 셋 다 아니면 창을 열지 않는다**

| # | 무엇 | 확인 | 지금 |
|---|---|---|---|
| a | 새 자격 금고 파일 2 | `ls ~/.guardianx-secrets/` → `cred3_20260915.env` · `cred3_20260915_alter_db_role.sql` | [실측 09-15] 섰다 · 형식: `evidence/P-138/vault_prepared_20260915.json` |
| b | ⑦ 가드 패치(`settings_prod.py` · 소유 차선) | 20자 미만 · 접근키==비밀키 · 자리표 낱말 → `[SEC-18]` 거부 (blockers.yaml:1654) | **섰다** [실측 2026-09-16 · 턴 R · P-151] — 코드는 들어갔고 격리에서 **7/7**. 증거 `evidence/P-151/iso_guard_20260916T0114Z.json` · 아래 §b′ |
| c | 다른 차선 정지 | 시험 DB 연결 0 · 큐 0 (`RUNBOOK_로컬기동.md` STEP 2B ⓪㉠ · ③) | 창 직전 |

**b′ 가드는 이미 섰다 — 창에서 할 일이 하나 줄었다** [실측 2026-09-16 · 턴 R · 차선 E · P-151]

`backend/config/settings_prod.py` 에 ⑦ 절이 들어갔다(`CRED_MIN_LEN 20` · `CREDENTIAL_PLACEHOLDER_WORDS` 8낱말 ·
접근키==비밀키 거부 · `CREDENTIAL_GUARD = "SEC-18-⑦"`). 값을 읽는 자리는 환경이 아니라 **앱이 실제로 쓰는
`django.conf.settings`** 다(`MINIO_ACCESS_KEY`·`MINIO_SECRET_KEY`·`DATABASES["default"]["PASSWORD"]`).

* **격리에서 7/7** — `python docs/agent/evidence/P-151/iso_guard.py` 가 `gx-shell` 의 환경 41개를 뜨고
  자격 **넷만** 금고(`cred3_20260915.env`)의 새 값으로 갈아 낀 컨테이너 `gx_e` 를 세운 뒤,
  그 안에서 `verify_prod_settings.py --no-delegate` → **`통과 7/7` · exit 0**.
  ⑦ 줄이 `MinIO 접근/비밀 20·40자 · DB 비밀 32자 · 자리표 없음 | 자리표→거부 O · 5자→거부 O · 둘이 같음→거부 O` —
  금고 증거(`evidence/P-138/vault_prepared_20260915.json`)의 길이와 같다(창 전 조건 ㉡ 충족).
* **나쁜 값은 실제로 못 뜬다** — 같은 컨테이너에서 여덟 판을 띄웠다. 짧은 값 · 둘이 같은 값 · 자리표 · 짧은 DB 비밀
  네 가지가 **설정 기동**과 **`gunicorn --check-config`** 두 자리 모두에서 exit 1 · `[SEC-18]` 거부.
  좋은 값 두 판만 떴다. **경고를 찍고 뜨는 자리는 하나도 없다.**
* ⚠ **그러나 지금 도는 컨테이너에서는 이 가드가 빨강을 만든다** — 그것이 옳고, blockers.yaml:1636 의 A/B 가
  예고한 그대로다. 호스트에서 `python scripts/verify_prod_settings.py`(= `gx-shell` 위임)를 지금 부르면
  기준판 `full` 이 **거부**되고 일곱 수가 전부 「재지 못했다 — 판이 안 떴다」가 되어 **실패 7/7 · exit 1** 이다.
  `gx-shell` 의 MinIO 자격이 아직 5자이기 때문이다. **이 빨강은 창의 ② 가 끝나야 초록이 된다** —
  ②를 건너뛰고 ④만 부르면 7/7 이 아니라 0/7 을 본다. 순서를 쪼개지 말라는 말이 이 뜻이다.

---

**⓪ 기록 (2분)** — 기동 시각을 적어 둔다. 창 뒤에 **바뀐 것만** 바뀌었는지 이것과 견준다.
```bash
for c in gx-gunicorn-e gx-celery-e gx-beat-e gx-shell gx-nginx-e postgres redis guardianx-source-minio-1; do
  printf "%-26s %s\n" $c "$(docker inspect -f '{{.State.StartedAt}}' $c)"; done | tee /c/GuardianX-vault/recreate/startedat.pre
docker exec postgres pg_dump -U postgres -Fc database_guardianx > /c/GuardianX-vault/gx_$(date +%Y%m%d_%H%M).dump   # 회수증
```

**① 형상 뜨기 (3분)** — `RUNBOOK_로컬기동.md` STEP 2B ①과 같은 명령에 **gx-*-e 셋**을 더한다.
```bash
cd /c/GuardianX-vault/recreate && cp /c/GuardianX/guardianx-source/.env root.env.pre-window
for c in gx-gunicorn-e gx-celery-e gx-beat-e gx-shell; do
  docker inspect $c --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -vE '^(PATH|LANG|HOME|HOSTNAME|GPG_KEY|PYTHON_VERSION|PYTHON_SHA256|LD_LIBRARY_PATH)=' | grep -v '^$' > $c.env
  docker inspect $c > $c.json; echo "$c: $(wc -l < $c.env) vars"; done
```

**② 자격 3 (10분)** — 앱을 먼저 멈추고(큐 0 확인 뒤), DB → MinIO → env-file 순.
```bash
docker stop gx-beat-e gx-celery-e gx-gunicorn-e
# ②-a DB 역할 — 평문이 아니라 SCRAM 검증자를 싣는다(서버 로그에 문장이 남아도 평문 없음)
docker exec -i postgres psql -U postgres -d database_guardianx -q -v ON_ERROR_STOP=1 < ~/.guardianx-secrets/cred3_20260915_alter_db_role.sql && echo "DB role OK"
# ②-b MinIO 서버 — 뿌리 .env 두 줄을 금고 값으로 (값은 화면에 안 나온다)
cd /c/GuardianX/guardianx-source && python - ~/.guardianx-secrets/cred3_20260915.env <<'PY'
import sys, pathlib
v = dict(l.split("=", 1) for l in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l and l[0] != "#" and "=" in l)
p = pathlib.Path(".env"); L = p.read_text(encoding="utf-8").splitlines(); n = 0
for i, l in enumerate(L):
    k = l.split("=", 1)[0]
    if k in ("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"): L[i] = k + "=" + v[k]; n += 1
p.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n"); print("뿌리 .env 치환", n, "(2 이어야 한다)")
PY
docker compose up -d --force-recreate minio && docker network connect --alias minio gx-main-network guardianx-source-minio-1
curl -s -o /dev/null -w 'minio=%{http_code}\n' http://localhost:9000/minio/health/live          # 200
# ②-c 앱 env-file — 넷을 금고 값으로, gx-shell 은 끝점도 바로잡고(D-378), 상한·백업 경로를 더한다
python - ~/.guardianx-secrets/cred3_20260915.env /c/GuardianX-vault/recreate <<'PY'
import sys, pathlib
v = dict(l.split("=", 1) for l in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l and l[0] != "#" and "=" in l)
R = pathlib.Path(sys.argv[2]); SWAP = ("MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "DB_PASSWORD", "DJANGO_SECRET_KEY")
ADD = {"GX_STORAGE_CAPACITY_GB": "50", "OPS_BACKUP_DIR": "/backup"}
for c in ("gx-gunicorn-e", "gx-celery-e", "gx-beat-e", "gx-shell"):
    out, seen = [], set()
    for l in (R / (c + ".env")).read_text(encoding="utf-8").splitlines():
        k = l.split("=", 1)[0]
        if k in SWAP: out.append(k + "=" + v[k]); seen.add(k)
        elif k in ADD: continue
        elif c == "gx-shell" and k == "MINIO_ENDPOINT": out.append("MINIO_ENDPOINT=minio:9000")
        else: out.append(l)
    out += [k + "=" + v[k] for k in SWAP if k not in seen] + [k + "=" + x for k, x in ADD.items()]
    (R / (c + ".new.env")).write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(c, "치환", len(seen), "· 없어서 더함", 4 - len(seen), "· 추가", len(ADD))
PY
```

**③ 재생성 + `/backup` (8분)** — 마운트·명령은 ①의 `*.json` 그대로이고 **`gx_backup_vault_e:/backup`**(볼륨 [실측] 있음)만 더한다.
```bash
R=/c/GuardianX-vault/recreate; S=C:/GuardianX/guardianx-source; LOG="--log-opt max-size=10m --log-opt max-file=5"
docker rm -f gx-gunicorn-e gx-celery-e gx-beat-e gx-shell
MSYS_NO_PATHCONV=1 docker run -d --name gx-gunicorn-e --network gx-main-network --restart unless-stopped $LOG \
  --env-file $R/gx-gunicorn-e.new.env -v $S/backend:/app -w /app --entrypoint python guardianx-backend:latest \
  -m gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 4 --worker-class gthread \
  --timeout 120 --access-logfile - --error-logfile -
MSYS_NO_PATHCONV=1 docker run -d --name gx-celery-e --network gx-main-network --restart unless-stopped $LOG \
  --env-file $R/gx-celery-e.new.env -v $S/backend:/app -v $S/backend:/repo/backend:ro -v $S/scripts:/repo/scripts:ro \
  -v $S/docs/agent/evidence/D-373:/docs/agent/evidence/D-373 -v gx_backup_vault_e:/backup -w /app --entrypoint python \
  guardianx-backend:latest -m celery -A config worker -l INFO --concurrency=2 --time-limit=600 --soft-time-limit=300 -n gx-worker-e@%h
MSYS_NO_PATHCONV=1 docker run -d --name gx-beat-e --network gx-main-network --restart unless-stopped $LOG \
  --env-file $R/gx-beat-e.new.env -v $S/backend:/app -v gx_backup_vault_e:/backup -w /app --entrypoint python \
  guardianx-backend:latest -m celery -A config beat -l INFO
MSYS_NO_PATHCONV=1 docker run -d --name gx-shell --network gx-main-network $LOG --env-file $R/gx-shell.new.env \
  -v $S/backend:/app -v $S/backend:/repo/backend -v $S/scripts:/repo/scripts -v $S/frontend:/repo/frontend \
  -v $S/docs:/docs -v gx_backup_vault_e:/backup -w /app --entrypoint sleep guardianx-backend:latest infinity
# ★ 앞단은 upstream 이름을 **기동·reload 때만** 푼다 — 새 gunicorn 의 IP 가 바뀌었으면 reload 없이 전부 502 다
MSYS_NO_PATHCONV=1 docker exec gx-nginx-e nginx -t -c /etc/nginx/gx/gx-front.conf && \
MSYS_NO_PATHCONV=1 docker exec gx-nginx-e nginx -s reload -c /etc/nginx/gx/gx-front.conf
```
⚠ `--entrypoint python`/`sleep` 는 빼지 않는다 — 이미지 `ENTRYPOINT`(`/entrypoint.sh`)는 무조건 migrate 한다(STEP 2B ②).

**④ 운영 프로필 판정 — SEC-18a (4분)** — 창 전 b(⑦ 가드 패치)를 **이 자리에서** 싣고 판정기를 돌린다.
```bash
python scripts/verify_prod_settings.py; echo "EXIT=$?"          # gx-shell 에 위임 · 12판을 실제로 띄운다
```
**SEC-18a 닫는 조건 — 넷 다** (「운영 프로필 선언 없이는 뜨지 않는다」는 **이 창에서만** 닫힌다 · P-137):
㉠ `EXIT=0` · **7/7** ㉡ ⑦ 줄이 `MinIO 접근/비밀 20·40자`(같은 문자열 아님) · `DB 비밀 32자` · 자리표 없음 — 금고 증거의 길이와 같다
㉢ ⑦ 음성 대조 셋 `자리표→거부 O · 5자→거부 O · 둘이 같음→거부 O` ㉣ ①~⑤ 의 `선언 없음→거부 O` 가 그대로.
그 뒤에야 `ga_readiness.yaml` SEC-18a `잠김 → 구현`(증거 파일과 함께). ⚠ b 없이 ②③만 하면 ㉢ 이 「X 떴다」로 남아 **6/7** 이다 —
6/7 을 구현으로 적지 않는다(blockers.yaml:1657). b 만 먼저 하면 기준판 `full` 이 거부되어 1/7 이 된다 — 순서를 쪼개지 않는다.

**⑤ 반영(P-139) · 확인 (3분)** — 「고쳤다」가 아니라 「도는 것」을 본다(D-301).
```bash
for c in gx-gunicorn-e gx-celery-e gx-beat-e gx-shell; do printf "%-14s %s\n" $c "$(docker inspect -f '{{.State.Status}}' $c)"; done
MSYS_NO_PATHCONV=1 docker exec gx-celery-e sh -c 'printenv GX_STORAGE_CAPACITY_GB; stat -c %d / /backup'   # 50 · 두 수가 달라야 한다
MSYS_NO_PATHCONV=1 docker exec gx-celery-e python -m celery -A config inspect ping -t 10 | tail -1
MSYS_NO_PATHCONV=1 docker exec -e PYTHONIOENCODING=utf-8 gx-celery-e python -c "import sys;sys.path.insert(0,'/repo/scripts');import ops_monitor as m;s=m.collect()['signals'];[print(k,s[k]['value'],s[k]['verdict']) for k in ('db_ping_ms','object_store_alive','storage_used_pct')]"
curl -s -o /dev/null -w 'front=%{http_code}\n' http://localhost:8500/admin/login/              # 200
python scripts/verify_live_freshness.py --all; echo "EXIT=$?"
```
기대: `storage_used_pct` 가 **UNKNOWN → 수(%)** · `object_store_alive OK`(새 MinIO 자격) · `db_ping_ms` 수(새 DB 비밀) · 로그인 4/4 는 조율자가 앱 자격으로 재확인.
⚠ 서명 키가 바뀌었으므로 창 전 세션·토큰·월 토큰·클립 서명 URL 은 전부 무효다 — **저장 암호화에는 안 쓰인다**
[코드 grep: `common/wall_token.py:142` · `stream_monitors/services/clips.py:187` · `partner/utils/partner_utils.py:444` 모두 HMAC 서명]. 자료 손실 없음 · 재로그인만.

**창에서 하지 않는 것**: P-137 앞단 재시도(peer 세 줄) 본 서버 적용 — 다음 턴(판정). 격리 수: `evidence/P-137/`.

---

## ⑥ 재부팅 전/후 실측 — **세션 밖에서 잰다** (G5 · 턴 R 차선 E)

Docker 자동 시작을 켠 뒤 **재부팅에서 열 컨테이너가 스스로 돌아오는지**를 아직 안 쟀다(G5 「재부팅 미실측」).
재부팅은 이 세션을 끊으므로 **집행자가 재부팅을 실행하지 않는다** — 아래 「전」은 이미 적혔고, 「후」는 재부팅 뒤
새 세션에서 같은 명령 넷을 그대로 부르면 된다.

**전 [실측 2026-09-16 09:0x · 재부팅 직전 · HEAD `5a403ef`]**

| 무엇 | 값 |
|---|---|
| 도는 컨테이너 | **10** (gx-shell · gx-gunicorn-e · gx-celery-e · gx-beat-e · gx-nginx-e · postgres · redis · minio-1 · mailpit-1 · gx-fe-build) |
| 재시작 정책 | 다섯 자리 모두 **`unless-stopped`** [`docker inspect .HostConfig.RestartPolicy.Name`] |
| 기동 시각(UTC · `StartedAt`) | gx-gunicorn-e `2026-09-15T11:27:44Z` · gx-celery-e `11:24:35Z` · gx-beat-e `11:24:36Z` · gx-nginx-e `04:23:22Z` · gx-shell `04:23:22Z` |
| `verify_live_freshness --all` | **exit 1 · 빨강** — 넷이 회색(`LIVE_OLDER_THAN_SOURCE`) · `gx-shell:runserver` 빨강(`LIVE_COMMIT_MISMATCH`) |

⚠ **이 빨강은 재부팅이 만든 것이 아니다** — 작업본이 소스 시각을 앞으로 당겨서다(이 턴에 `settings_prod.py` 를
고쳤다). 재부팅 뒤 같은 빨강이 나오면 **그것은 같은 사유**이고, 재부팅의 결함이 아니다.
「후」를 읽을 때 이 줄을 먼저 본다 — 안 그러면 없는 고장을 찾으러 간다.

**후 — 재부팅 뒤 새 세션에서 이 넷을 순서대로**

```bash
cd /c/GuardianX/guardianx-source
# ㉠ 열이 스스로 돌아왔는가 (Docker Desktop 자동 시작 + unless-stopped)
docker ps --format '{{.Names}}\t{{.Status}}' | sort          # 10줄이어야 한다
docker inspect gx-gunicorn-e gx-celery-e gx-beat-e gx-nginx-e gx-shell \
  --format '{{.Name}} {{.State.StartedAt}} restarts={{.RestartCount}} {{.HostConfig.RestartPolicy.Name}}'
# ㉡ **낡음** — 다섯 자리가 각자 자기 소스에 대해 (P-116)
python scripts/verify_live_freshness.py --all; echo "EXIT=$?"
# ㉢ 앞단이 뒷단 이름을 **다시 풀었는가** — 재부팅으로 gunicorn 의 IP 가 바뀌면 reload 없이 전부 502 다(③의 ★)
curl -s -o /dev/null -w 'front=%{http_code}\n' http://localhost:8500/admin/login/     # 200
# ㉣ 곁것들이 실제로 살아 있는가 (MinIO 없이 뜬 runserver 가 503 을 낸 P-150 ②의 그 자리)
MSYS_NO_PATHCONV=1 docker exec -e PYTHONIOENCODING=utf-8 gx-celery-e python -c \
  "import sys;sys.path.insert(0,'/repo/scripts');import ops_monitor as m;s=m.collect()['signals'];[print(k,s[k]['value'],s[k]['verdict']) for k in ('db_ping_ms','object_store_alive','storage_used_pct')]"
```

**읽는 법 — 셋**

1. **열이 아니면 빨강이다.** 몇이 안 왔는지, 그 컨테이너의 `RestartPolicy` 가 무엇인지 함께 적는다.
   `unless-stopped` 인데 안 왔으면 자동 시작이 아니라 **그 컨테이너의 고장**이다.
2. `live_freshness` 는 **기동 시각이 소스보다 뒤여야** 초록이다. 재부팅은 기동 시각을 **지금**으로 당기므로
   ㉡ 의 회색 넷은 재부팅만으로 **사라져야 한다**. 안 사라지면 그 자리는 안 뜬 것이다.
   `gx-shell:runserver` 의 `LIVE_COMMIT_MISMATCH` 는 **커밋의 문제**라 재부팅으로 안 사라진다 — 그것까지
   초록을 기대하지 않는다.
3. **㉢ 이 502 면 재부팅의 대표 고장이다** — 앞단은 upstream 이름을 기동·reload 때만 푼다.
   고치는 법은 ③의 마지막 두 줄(`nginx -t` → `nginx -s reload`)이고, **재기동이 아니다**.

⚠ **「후」를 안 쟀으면 G5 는 회색이다.** 재부팅했는데 안 쟀다면 「재부팅 됐다」가 아니라 **「안 쟀다」**로 적는다.

---

**되돌리기** — 원본은 ①의 `*.env`·`*.json`·`root.env.pre-window`. 단계별로 **거꾸로**.
* 앱 넷: `docker rm -f` 뒤 ③ 명령에서 `.new.env` → `.env`, `/backup` 줄을 빼고 다시 띄운다 → 앞단 reload.
* DB 역할: 옛 비밀번호로 되돌린다(값 출력 없이):
  `python -c "import sys;sys.path.insert(0,'docs/agent/evidence/P-138');import gen_vault as g;v=dict(l.split('=',1) for l in open('/c/GuardianX-vault/recreate/gx-gunicorn-e.env',encoding='utf-8').read().splitlines() if '=' in l);print(\"ALTER ROLE \\\"%s\\\" PASSWORD '%s';\"%(v['DB_USER'],g.scram_verifier(v['DB_PASSWORD'])))" | docker exec -i postgres psql -U postgres -d database_guardianx -q -v ON_ERROR_STOP=1`
  ⚠ dj-core 사용자 비밀번호와 달리 postgres 역할 비밀번호에는 「최근 사용」 거절이 없다 — 되돌릴 수 있다.
* MinIO: `cp /c/GuardianX-vault/recreate/root.env.pre-window .env` → `docker compose up -d --force-recreate minio` → 망 다시 잇기.
  [가정] 이 MinIO 판은 IAM 을 루트 자격으로 암호화하지 않는다 — 새 자격으로 떴는데 버킷이 안 보이면 **바로 이 줄**로 되돌린다.
* 확인: ⓪의 `startedat.pre` 와 견준다 — 창에서 바꾸기로 한 넷 + minio 말고 **기동 시각이 바뀐 것이 없어야** 한다.
* **되돌렸으면 사유를 이 절 아래에 적는다** — 적지 않으면 다음 사람이 같은 것을 또 시도한다(`RUNBOOK_로컬기동.md` 와 같은 규칙).
