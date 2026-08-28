# 실측 — **이 저장소의 스키마는 마이그레이션만으로 재현되지 않았다**

**날짜** 2026-08-30 · **발견 경위** D-291 규약 ①(E2E 는 실 마이그레이션 DB 에서 돈다)을
이행하려다 걸렸다 · **관련** D-282(착시 ⑤) · D-288(②눈) · P-ENV-1

---

## 1. 한 줄

**빈 DB 에 `manage.py migrate` 를 돌리면 죽는다.** 도는 개발 DB 는 어쩌다 맞는 순서로
적용된 결과이고, **새 환경에서는 처음부터 세울 수 없었다.**

이것은 E2E 만의 문제가 아니다. 계약 6차(2027.1) 인도는 **소스 인도**이고,
받는 쪽은 빈 DB 에서 시작한다.

---

## 2. 무엇이 죽었나 (원문)

```
core/logger/migrations/0009_auditaccesstype_auditaction_auditcommand_and_more.py:17
    MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
LookupError: No installed app with label 'multilanguage'.
```

`multilanguage` 는 `INSTALLED_APPS` 에 **있다** (`core.multilanguage`, label=`multilanguage`).
없는 것은 앱이 아니라 **그 시점의 마이그레이션 상태**다 — dj-core 의 `logger/0009` 가
`multilanguage` 에 대한 dependency 를 선언하지 않아, 실행 계획에서 뒤에 오면
`RunPython` 이 받는 `ProjectState` 에 그 앱의 모델이 아직 없다.

재현:

```
docker exec postgres psql -U postgres -c "CREATE DATABASE gx_migrate_probe;"
docker exec -e DB_NAME=gx_migrate_probe gx-shell sh -c \
  'cd /app && DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=/app python manage.py migrate'
→ LookupError (위)
```

---

## 3. 되돌린 시도 — **고치려던 것보다 더 큰 것을 깨뜨렸다**

빈 마이그레이션 `stream_monitors/0018` 에 순서 제약만 선언해 봤다:

```python
dependencies = [("stream_monitors", "0017_…"), ("multilanguage", "0001_initial")]
run_before   = [("logger", "0009_auditaccesstype_auditaction_auditcommand_and_more")]
operations   = []
```

| 대상 | 결과 |
|---|---|
| **빈 DB** | **통과.** `migrate --check` exit 0 · 표 212개 생성 |
| **이미 `logger/0009` 가 적용된 DB** (지금의 개발 DB · 운영 DB) | **`migrate` 자체가 죽는다** — `InconsistentMigrationHistory: Migration logger.0009… is applied before its dependency stream_monitors.0018…`. `--fake` 로도 통과하지 못한다 (`check_consistent_history` 가 계획 수립 **전에** 돈다) |

→ **되돌렸다.** 새 환경 하나를 살리려고 **도는 환경 전부를 세우는** 변경이다.
   운영 DB 에 들어갔다면 그 서버의 `migrate` 가 영구히 막힌다.

이 시도를 지우지 않고 남기는 이유는 D-286 이다 — 다음 사람이 같은 길로 다시 들어가지 않게.

---

## 4. 지금 쓰는 것 — **순서 두 줄** (스키마 변경 0)

빈 DB 실측:

```
manage.py migrate user               rc=0     # ※ 아래
manage.py migrate multilanguage      rc=0
manage.py migrate                    rc=0
manage.py migrate --check            rc=0     ← 정합
```

`user` 가 먼저인 이유도 실측이다. `multilanguage` 만 먼저 돌리면 dj-core 의 시그널이 씨앗
데이터 저장 중 `CoreUser … username='AnonymousUser'` 를 묻고, 그때 `user_coreuser` 표가
아직 없어 `UndefinedTable` 로 죽는다.

이 두 줄을 **E2E 시험 DB 생성에만** 끼웠다: `backend/tests/e2e/conftest.py`.
`PRE_MIGRATED_APPS = ("user", "multilanguage")` — 개수가 아니라 **이름**이다 (D-285 ②).

결과: `pytest tests/e2e -q -p no:randomly` → **15 passed** (마이그레이션 DB · `--nomigrations` 없음).

---

## 5. 무엇이 남았나

**이것은 받침이지 해결이 아니다.** 받침인 사실을 숨기지 않는다.

| 남은 것 | 왜 |
|---|---|
| 근본 원인 | dj-core `logger/0009` 의 dependency 누락. **§0.4 금지구역**이라 이 저장소가 못 고친다 → **P-ENV-1** |
| 운영/인도 절차 | `manage.py migrate` 한 줄로 세울 수 없다. 인도 문서의 설치 절차에 **두 줄**이 들어가야 한다 |
| CI | 빈 DB 에서 세우는 잡이 아직 없다. 있었다면 이 결함이 훨씬 전에 걸렸다 |

※ 확인용 DB `gx_migrate_probe` 는 확인 후 지웠다. **운영 DB 는 건드리지 않았다** (D-002).
