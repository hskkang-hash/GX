# P-71 턴 G — 새 시험 DB 가 **태어났다**. dj-core 는 한 글자도 안 고쳤다

- 집행: 차선 S · **2026-09-06 턴 G** · 고친 파일: `backend/conftest.py` **하나**
- 새 시험: `backend/tests/test_s_conftest_bootstrap.py` (4건 · DB 없이 돈다)

---

## 1. 잠금 — **새 이름의 시험 DB 를 만들면 죽었다** [실측 · 재현]

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_s_p71a \
  gx-shell python -m pytest tests/test_l_retention.py -q -p no:randomly
  → **13 errors in 157.84s**

core/logger/migrations/0009_auditaccesstype_auditaction_auditcommand_and_more.py:17
    MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
E   LookupError: No installed app with label 'multilanguage'.
```

`logger/0009` 이 `multilanguage` 의존을 **선언하지 않는다.** 장고가 세운 기본 순서로 빈 DB 에
`migrate` 를 돌리면 그 `RunPython` 이 아직 상태에 없는 앱을 찾다가 죽는다.
그 파일은 **dj-core — §0.4 금지구역이라 고칠 수 없다.**

⚠ `--nomigrations` 를 주면 이 잠금이 **안 보인다.** 마이그레이션 자체가 꺼져 `logger/0009`
  가 아예 안 돌기 때문이다. 그래서 이번 재현은 `--nomigrations` 를 뺐다.

## 2. 고친 것 — **순서만.** 우회층은 이미 있었다

OPS-03 이 만든 우회층 `manage.py migrate_bootstrap` 이 이 순서를 이미 안다
(`BOOTSTRAP_ORDER = ("user", "multilanguage")`). 없던 것은 **그 층이 시험 DB 생성 경로에는
안 깔려 있었다**는 것뿐이다 — 사람이 손으로 부르는 명령이라 pytest 가 만드는 DB 는 그 순서를
모른 채 태어났다.

장고의 `BaseDatabaseCreation.create_test_db` 는 빈 DB 를 만든 뒤 `migrate` 를 **한 번** 부른다
(django 5.1). 그 한 번 **앞에** 같은 순서를 끼운다.

```
backend/conftest.py
    bootstrap_steps(order, *, migrate_disabled) -> tuple      ← 순수 함수 (D-277)
    _install_migrate_bootstrap()                              ← pytest_configure 가 부른다
```

- 목록은 **베끼지 않는다.** `BOOTSTRAP_ORDER` 를 그 파일에서 읽어 온다 — 두 벌로 두면
  한쪽만 고쳐지고, 어긋난 복사본 하나가 D-212 였다.
- `--nomigrations`(`TEST['MIGRATE'] is False`)면 **끼우지 않는다.** 꺼진 실행에 순서를 끼우면
  **없는 일을 한 척**이 되고, 그 척은 다음 사람이 이 훅을 믿지 못하게 만든다.
- 이미 선 DB(`keepdb`)에서는 전부 「적용 완료」라 아무 일도 하지 않는다.
- **dj-core·스키마는 한 글자도 안 바꿨다** (§0.4).

## 3. 실측 — **초록**

```
docker exec postgres psql -U postgres -c 'DROP DATABASE IF EXISTS "test_gx_s_p71a";'
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_s_p71b \
  gx-shell python -m pytest tests/test_l_retention.py -q -p no:randomly
  → **1 failed, 12 passed** in 195.68s      (앞: 13 errors)
  → `No installed app with label 'multilanguage'` **0건**

docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_s_p71c \
  gx-shell python -m pytest tests/test_s_conftest_bootstrap.py -q -p no:randomly
  → **4 passed** in 0.60s
```

남은 1건은 이 훅과 무관하다 — 차선 E 가 P-67(보존 일수 선언)로 작업 중인 자리다:

```
FAILED tests/test_l_retention.py::TheNumberIsDeclaredOnceTest::test_a_broken_setting_does_not_become_zero_days
E   ImportError: cannot import name 'DEFAULT_RETENTION_DAYS' from 'apps.dsm.retention'
```

**마이그레이션 잠금은 사라졌고, 남은 빨강은 제품의 빨강이다.** 그 둘이 갈린 것이 이번 일의 값이다.

## 4. 지키는 시험 — `tests/test_s_conftest_bootstrap.py` (DB 없이 돈다)

| 시험 | 무엇을 지키나 |
|---|---|
| `…the_order_comes_from_the_ops03_layer_not_a_copy` | 목록의 정본은 하나다 (D-212) |
| `…multilanguage_is_stood_up_before_the_rest` | **출생 표본** — 그날 못 찾은 그 앱이 앞에 선다 |
| `…nomigrations_run_gets_no_extra_steps` | 꺼진 실행에 「한 척」 하지 않는다 |
| `…the_hook_is_actually_installed` | **선언이 아니라 적용을 본다** — 안 깔리면 DB 는 그대로 죽는다 |
