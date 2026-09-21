<!-- ⚠ 이 파일은 **둘을 합친 것**이다 [조율자 2026-09-20] -->
> ## ⚠ 왜 합쳤나 — 조율자 오판 ⑦
>
> 조율자가 차선을 부를 때 **이름이 같은 옛 턴의 차선**을 깨워 같은 일(P-205)을 시켰다.
> 그래서 **두 손이 같은 일을 하고 대장을 둘 썼다**:
> `audit_logger_name_index.md`(16:14 · 이 턴의 F) · `감사인덱스_마이그레이션.md`(16:51 · 옛 F).
>
> 차선 F 의 말이 옳다 — **「한 일에 대장이 둘이면 갈리는 순간 하나는 거짓말이다.」**
> **지우지 않고 합쳤다.** 양쪽에만 있는 수가 각각 있었기 때문이다:
> · 앞엣것에만: `relfilenode` no-op 대조 · 양성/음성 대조 넷 ·
>   **빈 DB 가 `logger.0009` 에서 죽는다**는 음성 대조
> · 뒤엣것에만: 표가 **147,484행**으로 자란 뒤에도 **0.825ms** · 버퍼 `hit=75 read=8`
>
> 아래 §A 가 이 턴 F 의 것, §B 가 옛 F 의 것이다. **수가 갈리는 자리는 없었다.**

---

# §A — 이 턴 차선 F (16:14)

# P-205 — 감사 표 `logger_name` 인덱스: **DB 에만 있던 것을 마이그레이션으로 내렸다**

작성: 차선 F(성능) · 턴 Y · 2026-09-20 · 기계 `C:\GuardianX\guardianx-source` · DB `database_guardianx`

## 0. 한 줄

턴 X 에 대표 결정으로 **DB 에 직접** 넣은 인덱스가 **마이그레이션에는 없었다.**
그대로 두면 스테이징·재생성 DB 는 인덱스 **없이** 태어나고, 이 자리는 거기서 다시 42ms 다.
이 턴에 `backend/common/migrations/0001_audit_logger_name_index.py` 로 내렸다.

## 1. 턴 X 의 전/후 — **행 수와 시간만** (값 출력 없음)

질의: `stream_monitors/services/response_clock.py:224 stamps_for`
→ `logger_auditlogs` 를 `logger_name` + `create_datetime` 로 거르는 한 줄.

| | 계획 | 버린 행 (`Rows Removed by Filter`) | Execution Time |
|---|---|---|---|
| **전** | `Parallel Seq Scan on logger_auditlogs` | **47,203** (워커마다) | **42.227 ms** |
| **후** | `Index Only Scan` | **0** — **54행 직행** | **0.242 ms** |

출처: `docs/workorders/WO-GX-20260915-01_report_wave3_turn4.md` §「대표 결정 ② 감사 인덱스」
(턴 X · 조율자 실측). 그보다 앞선 같은 자리의 첫 관찰은
`docs/agent/evidence/PERF-04/P-198_회귀의_원인을_이름으로.md` §4 —
`230행을 얻으려고 130,499행(282MB)` · `Rows Removed by Filter 43,431`(워커 3) · 35.4 ms.

⚠ **두 벌의 수가 다른 것(35.4 / 42.227)은 오류가 아니다** — 표가 그 사이에도 자랐다.
바로 그 자람이 §3 의 이유이고, 이 절이 「회귀의 엔진」이라 불린 까닭이다.
⚠ 값(어느 테넌트의 어떤 `logger_name` 인지, 어떤 행이 나왔는지)은 **여기 적지 않는다.**
행 수와 시간만으로 이 인덱스의 효과가 증명된다 — 값은 증명에 필요 없다.

## 2. 인덱스 한 줄

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS gx_audit_logger_dt_idx
    ON logger_auditlogs (logger_name, create_datetime);
```

되돌리기: `DROP INDEX CONCURRENTLY IF EXISTS gx_audit_logger_dt_idx;`

**답을 안 바꾸고 속도만 바꾼다.** 성능을 위해 답을 바꾸는 대안
(`data_after__event_id__in` 을 SQL 로 미는 것)은 턴 X 에 기각됐다 —
`data_after` 가 문자열로 오는 백엔드에서 그 행이 **조용히 사라진다**.

## 3. 왜 우리 앱의 마이그레이션인가

`logger_auditlogs` 는 dj-core(`core.logger.AuditLogs`)의 표 — **§0.4 금지구역**이다.
site-packages 안의 그 앱에 마이그레이션을 끼우는 것은 ⓐ 남의 자산을 고치는 일이고
ⓑ 패키지를 올리면 사라진다. 그래서 **우리 앱(`common`)의 마이그레이션이 남의 표에
인덱스만** 만든다. **dj-core 파일 0줄** — `dependencies = [("logger", "0001_initial")]` 로
그 앱을 **읽을 뿐**이다(`logger_name`·`create_datetime` 두 칸이 거기서 함께 생긴다).

`common` 앱에는 **구상 모델이 0개**다(전부 abstract). 그래서 마이그레이션 꾸러미를
새로 만들어도 자동탐지기가 만들 것이 없다 — `verify_migrations` ①이 0건인 이유다.

## 4. 눌러서 본 것 — 다섯 벌

기계 시각 2026-09-20 15:5x KST. 창 밖 작업(재기동 0 · 로그인 0 · 서버 안 건드림).

### ⓐ 있는 DB 에서 **no-op 인가** — 이것이 `IF NOT EXISTS` 의 요점이다

지금 개발 DB 에는 턴 X 가 넣은 인덱스가 **이미 있다.** 같은 인덱스를 다시 만들라는
마이그레이션이 여기서 죽으면 안 되고, **다시 지었다 세워도 안 된다**(4.8MB 짜리 재구축은
쓰기 길목에 부담이다). 그래서 죽지 않았다는 것만 보지 않고 **oid 와 relfilenode 를 대 봤다**:

| | oid | relfilenode | `indisvalid` | 표의 인덱스 수 |
|---|---|---|---|---|
| `migrate` 전 | `8518917` | `8518917` | `t` | 35 |
| `migrate` 후 | `8518917` | `8518917` | `t` | 35 |

> **relfilenode 가 같다 = 물리 파일을 다시 안 만들었다.** 「죽지 않았다」가 아니라
> **「아무 일도 안 일어났다」**를 잰 것이다. 두 수가 같아야 no-op 이다.
> (`pg_relation_size` 만 4,816,896 → 4,825,088 로 늘었는데, 이건 재구축이 아니라
> 그 8초 사이에도 **감사 행이 계속 들어오고 있다**는 증거다 — §5 가 세는 바로 그 자람이다.)

`django_migrations` 는 440 → **441**, `common | 0001_audit_logger_name_index` 한 줄. exit **0**.

### ⓑ 없는 DB 에서 **정말 만드는가** — 양성 대조

no-op 만 확인하면 「아무것도 안 하는 마이그레이션」도 초록이다. 그래서 인덱스가
**없는** 자리에서 같은 SQL 을 눌렀다(임시 DB `gx_p205_probe` · 시험 뒤 DROP):

| # | 누른 것 | 결과 |
|---|---|---|
| 1 | 인덱스 없는 표에 정방향 | `CREATE INDEX` · oid 생김 · `indisvalid = t` |
| 2 | 같은 정방향 한 번 더 | `NOTICE: … already exists, skipping` · **oid 그대로** |
| 3 | 역방향 | `DROP INDEX` · `pg_class` 에서 0건 |
| 4 | 역방향 한 번 더 | `NOTICE: … does not exist, skipping` · 안 죽는다 |

### ⓒ `atomic = False` 가 **장식이 아님** — 음성 대조

같은 SQL 을 트랜잭션 안에서(`psql -1`) 눌렀다:

```
ERROR:  CREATE INDEX CONCURRENTLY cannot run inside a transaction block
```

exit **1**. Django 는 마이그레이션마다 트랜잭션을 연다 → `atomic = False` 가 없으면
이 마이그레이션은 **어디서도 안 돈다.**

### ⓓ `verify_migrations` — 두 눈 · 양성 대조 둘

```
[MIGR] 양성 대조 — 가짜 필드 1건을 심자 탐지기가 잡았다. 판정기는 작동한다
[MIGR] 양성 대조(②) — 적용 표식 1건을 빼자 미적용 1건으로 잡혔다. 판정기는 작동한다
[MIGR] ① 모델→마이그레이션 — 미반영 0건
[MIGR] ② 마이그레이션→DB — 미적용 0건
[MIGR] 정합 — 모델 선언 = 마이그레이션 그래프 = DB
```
exit **0** (`gx-shell` 안 · 호스트에서는 Django 가 없어 exit 2 = 판정 불가).

### ⓔ `forbidden-zone` 게이트

`PASS 금지구역 변경 0건 (티켓 허용으로 지나간 것 0건)` · exit **0**.
**dj-core 0줄 · `backend/delivery`·`orders`·`terminals` 0줄 · 프런트 0줄.**

### ⓕ **새 DB 가 마이그레이션으로 태어나는가** — 여기서 이 턴의 전제가 깨졌다

이 마이그레이션의 존재 이유는 「스테이징·재생성 DB 가 **인덱스를 달고 태어나게** 한다」다.
그래서 그 말을 눌러 봤다 — 빈 DB 를 만들고 `migrate` 를 끝까지 돌렸다.

**끝까지 못 간다.** 내 마이그레이션에 **닿기도 전에** 죽는다:

```
Applying logger.0009_auditaccesstype_auditaction_auditcommand_and_more...
  KeyError: 'multilanguage'
  LookupError: No installed app with label 'multilanguage'.
exit 1
```

`logger.0009`(dj-core)의 `RunPython` 이 `apps.get_model("multilanguage", …)` 를 부르는데,
그 마이그레이션이 `multilanguage` 를 **의존으로 선언하지 않았다.** 그래서 그래프가
`multilanguage` 를 **아직 하나도 안 적용한 채**(실측: `django_migrations` 에 0줄)
`logger.0009` 에 먼저 닿는다.

**음성 대조 — 내가 만든 것이 아니다.** 그래프에 마디를 더하면 순서가 바뀔 수 있으므로,
**내 마이그레이션을 뺀 채**(`MIGRATION_MODULES = {"common": None}` · 저장소는 안 건드리고
임시 설정으로) 또 다른 빈 DB 에 같은 것을 돌렸다 → **같은 자리에서 같은 오류 · exit 1.**

> ⇒ **이 저장소는 오늘 빈 DB 를 마이그레이션으로 못 세운다.** 내 마이그레이션은
> 그 사실을 **만들지도 고치지도 않는다** — 이미 그랬다.
> ⇒ 그러므로 「스테이징이 인덱스를 달고 태어난다」는 **아직 증명되지 않았다.**
> SQL 수준(ⓑ)과 있는 DB(ⓐ)에서는 증명됐지만, **태어나는 길 자체에 더 오래된 구멍**이
> 하나 더 있다. 그 구멍은 **dj-core 의 마이그레이션 안**이고 §0.4 다 — **안 고쳤다.**
> 재생성은 오늘 **덤프 복원**으로만 된다(OPS-19 회수증이 그 길이다).
>
> ⚠ 이것을 「내 일이 끝났다」로 적지 않는다. 내 일은 **인덱스가 마이그레이션에 있다**까지이고,
> **그 마이그레이션이 실제로 돌아 본 자리는 「이미 있는 DB」뿐**이다. 빈 DB 에서 도는 것은
> 위 구멍이 막힌 뒤에야 잴 수 있다. 조율자께 이름으로 올린다.

## 5. 남은 위험 — 적어 두고 안 고친 것

- ⚠ **실패한 `CONCURRENTLY` 는 INVALID 인덱스를 남긴다.** 플래너는 그것을 안 쓰는데
  `IF NOT EXISTS` 는 **이름만** 보므로 「있다」로 읽고 넘어간다. 인덱스가 있는데도
  Seq Scan 이 나오면 **`pg_index.indisvalid` 를 먼저 본다** — 그때는 `DROP INDEX` 뒤 재적용.
  (지금 DB 는 `indisvalid = t` 로 확인했다.)
- ⚠ **같은 병이 이웃에 셋 더 있다.** `audit_user_dt_idx` · `audit_tgtuser_dt_idx` ·
  `audit_acc_act_dt_idx` 도 DB 에는 있는데 **저장소의 어느 마이그레이션에도 없다**
  (`grep -rn audit_user_dt_idx backend/` → 0건 · `W2-K2/schema_before_0017.sql` 에만 흔적).
  **이 턴에 안 고쳤다** — 내가 잰 것은 `gx_audit_logger_dt_idx` 하나뿐이고,
  재지 않은 인덱스를 「같아 보이니까」 함께 내리는 것은 이 턴이 내내 걷어낸 병과 같은 종류다.
  **이름만 올린다.**
- ⚠ 이 인덱스는 **표가 자라는 것을 안 막는다.** 훑기를 인덱스로 바꿨을 뿐이다.
  자람 자체는 §OPS-20 (`ga_readiness.yaml`)에서 따로 센다.

- ⚠ **`logger.0009` 의 의존 누락**(위 ⓕ) — dj-core · §0.4 · **안 고쳤다.** 고치는 길은
  두 가지뿐이다: ⓐ 소유팀에 올린다 ⓑ `DA-05/blockers.yaml` 에 잠금으로 등재한다.
  **내가 등재하지 않았다** — 잠금 대장은 내 파일이 아니고, 등재는 선언이라 주인이 있다.


---

# §B — 옛 턴 F 가 같은 일을 한 기록 (16:51)

⚠ 조율자의 배달 사고로 **같은 일을 두 번** 했다. 이 절은 **버리지 않는다** —
§A 에 없는 수(표가 자란 뒤의 0.825ms · 버퍼 hit/read)가 여기 있다.

# P-205 — **감사 인덱스를 마이그레이션으로 내린다** (2026-09-20 · 턴 X · 차선 F)

## 0. 한 줄

> 턴 X 에 대표 결정으로 넣은 `gx_audit_logger_dt_idx` 가 **이 DB 에만** 있었다.
> 마이그레이션이 없으면 **스테이징·재생성 DB 는 인덱스 없이 태어나고**, 내가 이름을 댄
> 회귀의 엔진이 **새 기계에서 도로 열린다.** 이 파일이 그 간격을 닫은 증거다.

## 1. 무엇이 닫혔나 (되짚기)

`stream_monitors/services/response_clock.py:224 stamps_for` 가 감사 표를 통째로 훑던 자리.
`CoreLoggingMiddleware` 가 **요청마다 감사 한 행**을 쓰므로 이 표는 계속 자라고,
그래서 이 자리는 **코드가 안 변해도 날마다 느려진다.**

| | 행 | 시간 |
|---|---|---|
| **전** [조율자 실측 · 턴 X] Parallel Seq Scan | 버린 행 **47,203**(워커마다) | **42.227 ms** |
| **전** [F 실측 · 09-20 12:5x] Parallel Seq Scan | 230행 얻으려 **130,499행** 훑음 | **35.4 ms** |
| **후** [조율자 실측 · 턴 X] Index Only Scan | **54행 직행** · 버린 행 **0** | **0.242 ms** |
| **후** [F 실측 · 09-20 16:5x · 표가 더 커진 뒤] Index Scan | **240행 직행** | **0.825 ms** |

★ 마지막 줄이 요점이다 — 표가 **130,499 → 147,484 행**으로 **늘어난 뒤에도** 0.8ms 다.
  인덱스가 이 질의를 **표 크기에서 떼어 냈다.** 버퍼도 `hit=12,166 read=6,281` →
  **`hit=75 read=8`** 로 떨어졌다.

## 2. 마이그레이션 — `backend/common/migrations/0001_audit_logger_name_index.py`

**표는 빌리고 코드는 안 만진다.** `logger_auditlogs` 는 dj-core(`core.logger.AuditLogs`)의
표이고 §0.4 다. site-packages 안 그 앱에 마이그레이션을 끼우면 **패키지를 올리는 날
사라진다.** 그래서 **우리 앱**의 마이그레이션이 **남의 표에 인덱스만** 만들고,
dj-core 파일은 한 자도 안 고친다(`dependencies` 로 **읽을 뿐**).

| 요구 | 어디에 | 왜 |
|---|---|---|
| `atomic = False` | `Migration.atomic` | `CREATE INDEX CONCURRENTLY` 는 **트랜잭션 안에서 못 돈다** — 아니면 **배포 한가운데서** 죽는다 |
| `IF NOT EXISTS` | `FORWARD_SQL` | 이미 인덱스가 있는 DB(지금 개발 DB)에서 **no-op** 이어야 한다 |
| 역방향 `DROP INDEX` | `REVERSE_SQL` | 되돌릴 수 있는 변경만 둔다. `IF EXISTS` 는 인덱스 없이 태어난 DB 를 되감을 때 |
| 모델 상태 안 건드림 | `state_operations` 없음 | 남의 모델 선언을 우리가 들면 dj-core 를 올리는 날 **두 선언이 어긋난다** |

`CONCURRENTLY` 를 쓰는 이유: 감사 표는 **쓰기 길목**이라 잠그면 전 요청이 멈춘다.

⚠ **실패한 CONCURRENTLY 는 INVALID 인덱스를 남긴다** — 이름은 있고 플래너는 안 쓴다.
`IF NOT EXISTS` 는 **이름만** 보므로 그 찌꺼기도 「있다」로 읽는다. 그래서 시험이
`pg_index.indisvalid` 를 따로 본다(있는데 안 듣는 것이 가장 나쁜 모양이다).

## 3. 눌러서 본 것

### ① 있는 DB 에서 no-op 인가 — **그렇다**

```
django_migrations   common | 0001_audit_logger_name_index | 2026-09-20 06:50:30+00 (=15:50:30 KST)
pg_index            gx_audit_logger_dt_idx · indisvalid=t · indisready=t · 5,040 kB
```
적용 뒤에도 인덱스는 **하나**이고 **성하다**. 시험이 같은 DB 에서 `FORWARD_SQL` 을
**한 번 더** 걸어 수가 안 변하는지 본다(`test_두_번_걸어도_no_op_이다`).

### ② 정합 — `verify_migrations` **exit 0**

```
[MIGR] 양성 대조 — 가짜 필드 1건을 심자 탐지기가 잡았다. 판정기는 작동한다
[MIGR] 양성 대조(②) — 적용 표식 1건을 빼자 미적용 1건으로 잡혔다. 판정기는 작동한다
[MIGR] ① 모델→마이그레이션 — 미반영 0건
[MIGR] ② 마이그레이션→DB — 미적용 0건
[MIGR] 정합 — 모델 선언 = 마이그레이션 그래프 = DB
```
★ ①이 **0건**인 것이 `state_operations` 를 안 둔 값이다 — `makemigrations` 가 이 인덱스를
「모델에 없는 변경」으로 **다시 만들라고 하지 않는다.**

### ③ 빈 DB 에서 태어나는가 — **그렇다** (`tests/test_f_audit_index_migration.py`)

새 DB `test_gx_f_mig` 를 **지우고** 실 마이그레이션으로 세웠다(260개 적용 · 4분 40초).

```
9 passed, 5 warnings in 280.99s   ← 건너뛴 것 0
  규격 5건 (DB 없이):  atomic=False · IF NOT EXISTS · 역방향 DROP · 모델 상태 안 건드림 · 표·칸 이름이 진짜
  진짜 DB 4건:        태어난다 · **성하다(indisvalid=t)** · 두 번 걸어도 no-op · 되감았다 다시 걸린다
```

**실 마이그레이션 DB 에서만 뜻이 선다.** `--nomigrations` 로 돌리면 표를 모델에서 바로
만들어 **이 마이그레이션이 아예 안 돌고**, 그래도 초록이 날 수 있다 — 그 초록은
아무것도 안 잰 초록이다. 그래서 `_migrations_ran()` 으로 **먼저 가르고** 안 돌았으면
**건너뛴다.** 건너뛴 것은 통과가 아니다. (이번 벌은 **건너뛴 것이 0** 이다.)

### ④ 되감기 시험이 **개발 DB 를 안 건드렸다**

`test_되감았다_다시_걸_수_있다` 는 DROP 뒤 CREATE 를 하므로, 잘못 돌면 **남이 쓰는 DB 를
인덱스 없이 두고 나갈** 수 있다. 자기 DB(`DB_TEST_NAME`)에서만 돌게 했고 `finally` 로
반드시 되돌린다. 시험 뒤 확인:

```
개발 DB database_guardianx : gx_audit_logger_dt_idx · indisvalid=t · 5,064 kB   ← 그대로
시험 DB test_gx_f_mig      : 없다 (pytest 가 치웠다)
```

### ⑤ Django 가 양쪽을 다 낸다 — `sqlmigrate`

```
정방향:  CREATE INDEX CONCURRENTLY IF NOT EXISTS gx_audit_logger_dt_idx
             ON logger_auditlogs (logger_name, create_datetime);
역방향:  DROP INDEX CONCURRENTLY IF EXISTS gx_audit_logger_dt_idx;
```
**역방향이 말로만 있는 것이 아니라** Django 가 실제로 낸다.

## 4. 성장률 — **첫 수** (OPS-18 이 읽을 자리)

[실측 2026-09-20 16:5x · `logger_auditlogs`]

```
전체            147,484행 · 324 MB  (본문 165 MB + 인덱스 107 MB)
새 인덱스                    5,040 kB
```

**하루 증분** (오늘은 아직 안 끝났으므로 **뺀** 지난 이레의 꽉 찬 날들):

| | 값 |
|---|---|
| 잰 날 | **5일** (이레 창에 빈 날이 있다 — 기계가 꺼져 있던 날) |
| 하루 **평균** | **12,383행 · 17 MB** |
| 하루 **가운데** | **11,173행** |
| 하루 **최대** | **19,864행** (09-19) |
| 이레 합계 | 61,914행 · 85 MB |

날짜별(최근):

```
09-20  19,221행 · 26 MB   ← 아직 안 끝난 날(16시 기준)
09-19  19,864행 · 31 MB
09-18   9,827행 · 12 MB
09-17  12,687행 · 19 MB
09-16  11,173행 · 13 MB
09-15   8,363행 · 10 MB
```

★ **이 수를 「운영의 수」로 읽지 말 것.** 여기는 개발 기계이고, 이 행의 상당수는
**우리가 게이트·시험·부하를 돌려서** 생긴 것이다(내가 이 턴에만 HTTP 로 2,658 요청을
때렸고 `CoreLoggingMiddleware` 는 **요청마다 한 행**을 쓴다). 그러니 이 수는
**「이 기계에서 하루에 이만큼 는다」**는 첫 수이지 운영 예측이 아니다.
운영 수를 내려면 **요청 수 대비 행 수**로 재야 하고, 그건 아직 안 쟀다.

★ 그래도 **방향은 말한다**: 하루 1만~2만 행이면 **한 달에 30만~60만 행**이다.
  인덱스가 없던 시절 이 표의 질의는 **행 수에 비례**했다 — 그래서 이 자리는
  **가만히 두면 다시 빨개지는 자리**였고, 인덱스가 그 비례를 끊었다(§1 마지막 줄).

## 5. 안 한 것 · 남는 것

- **보존 정책은 안 건드렸다.** 인덱스는 **읽기를 빠르게** 할 뿐 **표가 자라는 것을 안
  막는다**(324 MB · 하루 17 MB). 줄이려면 보존/파티션이고 그건 이 절이 아니다 —
  `OPS-18` 에 수만 넘긴다.
- **운영 성장률은 안 쟀다** (위 ★). 요청 대비 행 수를 재야 한다.
- dj-core 파일 **0줄** · `PERF-01/load.json` **0건** · `verify_perf_budget.py` **0건**.
