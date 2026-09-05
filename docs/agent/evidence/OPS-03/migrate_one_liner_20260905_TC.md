# OPS-03 — 마이그레이션이 **한 줄로 섰다** (2026-09-05 · 턴 C · 차선 E)

잠금 `MIGRATE_ONE_LINER` 의 해소 절차대로 했다. **dj-core 는 한 줄도 안 고쳤다.**

## 1. 무엇이 막고 있었나

dj-core `logger/0009` 가 `multilanguage` 의존을 **선언하지 않는다.** 빈 DB 에
`manage.py migrate` 를 그냥 돌리면 죽는다. 그 파일은 §0.4 금지구역이고, 순서 제약을
**우리 쪽에 선언**해 봤더니 이미 도는 환경이 전부 `InconsistentMigrationHistory` 로
죽었다 — 되돌렸다 (`docs/agent/evidence/e2e/migration_from_scratch.md`).

    [대장 OPS-03 · hand: in] dj-core 는 못 고치지만 **우회 경로를 우리 층에 둔다.**

## 2. 무엇을 했나 — **선언이 아니라 집행**

`backend/common/management/commands/migrate_bootstrap.py` (우리 층 · 스키마 변경 0):

    migrate user  →  migrate multilanguage  →  migrate  →  migrate --check

★ 왜 「설치 문서에 세 줄 적기」로 끝내지 않았나 (D-286): 여러 줄은 **사람의 기억에
맡긴 절차**이고, 사람의 기억에 맡긴 절차는 바쁜 날 한 줄이 빠진다. 빠진 그날 설치는
죽고, 죽은 자리를 보면 dj-core 의 의존 선언이 아니라 **「이 제품은 설치가 안 된다」**로
읽힌다. **순서를 아는 것은 도구여야 한다.**

## 3. [실측] 빈 DB 에서 실제로 돌렸다

```
docker exec postgres psql -U postgres -c "CREATE DATABASE gx_migrate_probe_e;"
docker exec -w /app -e DJANGO_SETTINGS_MODULE=config.settings -e DB_NAME=gx_migrate_probe_e \
    gx-shell python manage.py migrate_bootstrap
```

| 무엇 | 수 |
|---|---|
| 종료 코드 | **0** |
| 적용된 마이그레이션 | **436건** |
| 만들어진 표 | **221개** |
| `migrate --check` | **통과** (정합) |

확인용 DB `gx_migrate_probe_e` 는 확인 후 **지웠다.** 개발 DB·운영 DB 는 건드리지
않았다 (D-002).

★ 첫 시도는 `OSError: [Errno 12] Cannot allocate memory` 로 죽었다 — 같은 순간 다른
차선의 e2e 시험과 `runserver` 셋이 같은 컨테이너에서 돌고 있었다. **코드가 아니라
그날의 메모리다.** 그 사실을 적는다: 죽은 실행을 안 적으면 다음 사람이 같은 자리에서
같은 것을 코드 결함으로 읽는다.

## 4. 이것이 D-283 의 자동 migrate 가 되지 않게

  ① **사람이 손으로 부르는 명령**이다 — 어떤 entrypoint 에도 걸지 않았다
  ② 이미 마이그레이션이 적용된 DB 에서는 **그 자리에서 멈춘다**
     ([실측] 개발 DB 에서 `exit 1` · 「적용 438건 … 진행하려면 `--force`」)
  ③ `--plan` 은 **DB 를 만지지 않는다** — 사람이 먼저 볼 수 있어야 한다

시험: `backend/tests/test_e_ops03_migrate_bootstrap.py` **8 passed** (exit 0).
거절 판정은 **순수 함수**(`refuse_reason`)로 뽑았다 — `handle()` 안에만 두면 시험용
DB 는 언제나 비어 있어 **아무도 안 재는 갈래**가 된다.

## 5. 남은 것

잠금 자체(`MIGRATE_ONE_LINER`)는 **풀리지 않았다.** dj-core 의 의존 선언은 그대로다.
푼 것은 **설치 절차**이고, 잠금이 풀리는 날 이 명령은 `migrate` 한 줄과 같아진다 —
그때 지우면 된다. **우회층과 해결은 다른 것이고, 이 문서는 우회층이라고 적는다.**
