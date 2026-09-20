# -*- coding: utf-8 -*-
"""QA-11 — **단위 시험과 E2E 가 서로의 DB 를 다투지 않는다** (D-390 · 차선 Q).

무엇이 문제였나
---------------
둘 다 `test_<DB_NAME>` 하나를 만들려 했다. 동시에 돌리면 나중에 시작한 쪽이
`DuplicateDatabase` / `ObjectInUse: being accessed by other users` 로 죽는다.

    ★ **그 빨강은 코드 결함처럼 보이지만 환경 충돌이다.**
      실제로 한 번 「실패 1건」을 그렇게 오독할 뻔했다.

지금까지의 대응은 「순차로 돌린다」였고, 그것은 **회피이지 해결이 아니다**(D-390).
그리고 회피는 사람의 기억을 요구한다 — 기억을 요구하는 규칙은 바쁜 날 깨진다(D-286).

무엇을 고쳤나 — 이름 하나
-------------------------
`DB_TEST_NAME` 은 이미 있었다(P-18 · 차선마다 이름 가르기). 없던 것은 **기본값**이다.
아무도 아무것도 안 정했을 때 둘이 같은 이름을 쓴다는 것이 전부였다.

그래서 **실행 자체를 보고 이름을 정한다**: 이 실행이 `tests/e2e` 를 겨누면
`…_e2e` 를 쓴다. 사람이 기억할 것이 없다.

    pytest tests --ignore=tests/e2e   →  test_<DB>          (단위)
    pytest tests/e2e                  →  test_<DB>_e2e      (E2E)
    DB_TEST_NAME=test_gx_c pytest …   →  test_gx_c          (사람이 정하면 그것이 이긴다)

★ 왜 환경변수가 아니라 **`django_db_modify_db_settings`** 인가 [실측 2026-09-26]
    처음에는 conftest 최상단에서 `os.environ["DB_TEST_NAME"]` 을 세웠다. **안 먹었다** —
    pytest-django 는 `pytest_load_initial_conftests` 에서 **먼저** `django.setup()` 을
    부르고, 그 순간 `config/settings.py` 가 이미 `DB_TEST_NAME` 을 읽어 버린다.
    그래서 E2E 실행이 여전히 단위와 같은 이름을 만들려 했고 `DuplicateDatabase` 12건으로 죽었다.
    **판정기가 아니라 순서 문제였고, 그 순서는 로그 어디에도 안 나온다.**
    pytest-django 가 그 자리에 준 손잡이가 이 픽스처다 — DB 를 만들기 **직전**에 불린다.

★ 사람이 `DB_TEST_NAME` 을 준 실행에서는 그 값이 이긴다 —
  차선마다 이름을 가르는 P-18 의 길을 막지 않는다.

★★ 그런데 **이름을 갈라도 다툰다** — 같은 이름을 든 내 실행 둘 [실측 2026-09-20 · 턴 X · 차선 S]
-----------------------------------------------------------------------------------------
위 규약은 「단위 ↔ E2E」와 「차선 ↔ 차선」만 가른다. **한 사람이 같은 이름으로 둘을 겹쳐
돌리는 경우**는 아무도 안 막았고, 턴 W 에 그 일이 실제로 났다(`DB_TEST_NAME=test_gx_s` 둘).
지금 다시 눌러서 본 얼굴은 이렇다 — 이 줄들이 이 가드의 출생 표본이다::

    A(먼저): 10 passed  ·  단 teardown 경고
             Error when trying to teardown test databases:
             database "test_gx_s" is being accessed by other users
    B(나중): 22 errors
             psycopg2.errors.UniqueViolation: duplicate key value violates unique
             constraint "auth_permission_content_type_id_codename_…"
             DETAIL: Key (content_type_id, codename)=(2211, add_apikey) already exists.

    ★ **B 의 빨강에는 DB 이름이 한 글자도 안 나온다.** `auth_permission` 중복이라
      마이그레이션·권한 코드의 결함처럼 읽힌다 — 턴 W 에 그렇게 읽을 뻔했다.
      나중에 온 실행이 DB 를 **못 지우고**(A 가 쥐고 있다) 남의 표 위에 그대로 얹은 것이다.

그래서 **다투는 순간에만** 이름을 한 번 더 가른다(`split_when_busy`). 평시에는 한 글자도
안 바뀌고, 겹친 실행만 `…_p<pid>` 로 제 DB 를 갖는다. 그 DB 는 그 실행이 끝날 때 함께
사라지므로 찌꺼기도 안 쌓인다. **사람이 기억할 것이 없다** — 기억을 요구하는 규칙은
바쁜 날 깨진다(D-286).

★ 못 물어봤으면 **「안 다툰다」로 읽지 않는다.** 붙어 있는 연결을 못 세는 실행에서는
  가드가 조용히 통과하는 대신 한 줄을 인쇄한다 — 회색은 초록이 아니다(D-301).
"""
from __future__ import annotations

import os

import pytest


def test_db_name(argv, *, base: str) -> str:
    """이 실행이 겨누는 시험 DB 이름. **순수 함수다** — 시험이 이것을 직접 먹인다.

    술어는 하나: 인자 중에 `tests/e2e` 를 가리키는 것이 있는가.
    `--ignore=tests/e2e` 는 **겨누는 것이 아니라 빼는 것**이므로 세지 않는다 —
    그 구별이 없으면 단위 실행이 E2E 이름을 쓰고, 그러면 갈라 놓은 보람이 없다.
    """
    for raw in argv or ():
        arg = str(raw).replace("\\", "/")
        if arg.startswith("-"):        # --ignore=tests/e2e · -k … 는 겨누는 것이 아니다
            continue
        if "tests/e2e" in arg.split("::", 1)[0]:
            return f"{base}_e2e"
    return base


def split_when_busy(name: str, *, busy: bool | None, pid: int) -> str:
    """**남이 이미 쥐고 있는** 시험 DB 면 이름을 한 번 더 가른다. 순수 함수다.

    `busy` 의 값이 셋인 것이 요점이다 — `True`(다툰다) · `False`(안 다툰다) ·
    **`None`(못 봤다)**. 「못 봤다」를 「안 다툰다」로 접으면 가드는 조용히 사라지고,
    조용히 사라진 가드는 있는 것보다 나쁘다. 그래서 갈래를 셋으로 두고, 못 본 실행은
    이름을 안 바꾸되 **부르는 쪽이 그 사실을 인쇄한다**.

    ⚠ 다투지 **않을** 때는 한 글자도 안 바꾼다. 늘 가르면 실행마다 새 DB 가 생기고,
      그 찌꺼기를 치우는 일이 다시 사람의 기억으로 돌아온다.
    """
    if not busy:
        return name
    return f"{name}_p{pid}"


def _say(msg: str) -> None:
    """가드가 한 일을 **끝까지 보이게** 말한다.

    ⚠ `print` 하나로는 안 보인다 [실측 2026-09-20]: 픽스처의 표준출력은 pytest 가
      삼키고 **실패했을 때만** 보여 준다. 그래서 갈라 놓고도 아무도 모르는 실행이
      나왔다 — 조용한 가드는 다음 사람에게 「왜 이 DB 가 생겼지」만 남긴다.
      경고는 실행 끝의 warnings summary 에 **언제나** 찍힌다.
    """
    import warnings

    print(msg)
    warnings.warn(msg, stacklevel=2)


def _db_is_busy(name: str) -> tuple[bool | None, str]:
    """그 이름의 DB 에 **나 말고 다른 연결**이 붙어 있나. `(답, 못 본 까닭)`.

    ★★ **장고의 연결로 묻지 않는다** [실측 2026-09-20 · 이 자리에서 32 passed 가 깨졌다]
      처음에는 `django.db.connection` 으로 물었다. 그랬더니 **묻는 행위 자체가**
      그 뒤의 `create_test_db` 를 바꿨다 — 멀쩡하던 시험 둘이 이렇게 죽었다::

          psycopg2.errors.FeatureNotSupported:
              cannot truncate a table referenced in a foreign key constraint

      (`TransactionTestCase` 의 뒷정리가 지울 표 목록을 **운영 DB 기준으로** 추렸다.
      `--nomigrations` 로 태어난 시험 DB 에만 있는 표가 목록에서 빠지고, 그 표를
      가리키는 FK 가 남아 TRUNCATE 가 선다.) 가드를 껐다 켜 **A/B 로 갈라 확인했다**:
      질의를 안 하면 32 passed · 장고 연결로 물으면 그 자리에서 실패.

      그래서 여기서는 **장고가 안 쓰는 별도 연결**을 psycopg2 로 직접 연다. 설정은
      장고에게서 읽되(자격을 두 벌로 두지 않는다) 연결 객체는 우리 것이고, 묻자마자
      닫는다. 장고의 `default` 연결은 **한 번도 안 열린 채로** 남는다.

    ★ **왜 「못 봤다」에 까닭을 함께 돌려주나** [실측 2026-09-20]
      처음에는 `None` 만 돌려줬다. 그랬더니 가드가 매 실행 「못 물어봤다」를 찍는데
      **왜** 못 물어봤는지가 아무 데도 안 나왔다 — 회색인데 그 회색의 원인이 없다.
      0 은 원인이 아니라 질문이다. 그래서 까닭을 같이 든다.

    ⚠ 붙는 방은 `postgres` 다 — 시험 DB 는 아직 태어나기 전이고, 운영 DB 에 붙으면
      우리가 세는 그 연결 수에 **우리 자신이 끼어든다**. 세는 자리와 붙는 자리를 가른다.
    """
    try:
        import psycopg2
        from django.db import connection

        if connection.vendor != "postgresql":
            return None, f"vendor={connection.vendor} — postgres 가 아니다"
        params = dict(connection.get_connection_params())     # 여는 것이 아니라 **읽는다**
        params.pop("cursor_factory", None)
        params["dbname"] = "postgres"      # 물어볼 방(方)은 시험 DB 도 운영 DB 도 아니다
        params.setdefault("connect_timeout", 5)
        raw = psycopg2.connect(**params)
        try:
            with raw.cursor() as cur:
                cur.execute("SELECT count(*) FROM pg_stat_activity "
                            "WHERE datname = %s AND pid <> pg_backend_pid()", [name])
                return bool(cur.fetchone()[0]), ""
        finally:
            raw.close()
    except Exception as exc:         # noqa: BLE001 — 못 물어봤다고 시험을 막지 않는다
        return None, f"{type(exc).__name__}: {str(exc).strip()[:200]}"


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings_xdist_suffix) -> None:
    """시험 DB 이름을 **만들기 직전에** 정한다 (QA-11 · 다툼 가드는 턴 X).

    `django_db_modify_db_settings_xdist_suffix` 를 먼저 받는 이유: xdist 로 나눠 돌 때
    pytest-django 가 워커별 접미사를 붙인다. 그 일을 지우지 않고 **그 뒤에** 얹는다 —
    지우면 xdist 실행이 서로의 DB 를 다투고, 그것은 우리가 고치려던 바로 그 병이다.

    ★ 다툼을 묻는 질의는 **장고를 거치지 않는다**(`_db_is_busy` 의 ★★ 참조).
      이 시점의 장고 연결은 두 겹으로 위험하다: pytest-django 가 막아 두었고
      (`RuntimeError: Database access not allowed …`), 열면 그 다음 걸음이 바뀐다.
      한 번 속았던 자리다 — 막힌 줄 모르고 두면 가드가 매 실행 「못 물어봤다」를 내고
      **아무것도 안 막는데**, 겹쳐 돌린 실행이 우연히 통과하면 「가드가 일했다」로 읽힌다.
    """
    from django.conf import settings

    db = settings.DATABASES["default"]
    test_conf = db.setdefault("TEST", {})
    if test_conf.get("NAME") and "gw" in str(test_conf.get("NAME")):
        return                       # xdist 접미사가 붙은 이름은 건드리지 않는다

    chosen = os.environ.get("DB_TEST_NAME")
    if chosen:
        name = str(chosen)           # 사람이 정한 이름이 이긴다 (P-18 차선별 이름)
    else:
        base = "test_" + str(db.get("NAME") or "guardianx-v2")
        name = test_db_name(_pytest_args, base=base)

    # ★ 턴 X — 사람이 정한 이름이라도 **둘이 동시에 들면 갈라야 한다**(머리말 ★★).
    #   여기서 안 가르면 나중 실행이 DB 를 못 지운 채 남의 표에 얹히고, 그 빨강은
    #   `duplicate key … auth_permission` 이라 **코드 결함처럼** 읽힌다.
    busy, why = _db_is_busy(name)
    if busy is None:
        _say(f"[QA-11] 시험 DB «{name}» 에 누가 붙어 있는지 **못 물어봤다**({why}) — "
             f"다툼 가드가 이 실행에서는 안 돈다. 회색이지 초록이 아니다")
    elif busy:
        name = split_when_busy(name, busy=True, pid=os.getpid())
        _say(f"[QA-11] 시험 DB 를 **갈랐다** → «{name}». 다른 실행이 원래 이름을 쥐고 있다 "
             f"— 그대로 두면 DROP 이 막히고 남의 표에 얹혀 "
             f"`duplicate key … auth_permission` 이 난다(환경 충돌이지 코드 결함이 아니다)")

    test_conf["NAME"] = name


#: 실행 인자. `pytest_cmdline_main` 이 아니라 훅에서 받아 둔다 — 픽스처는 세션 뒤에 불리고
#: 그때 `sys.argv` 는 이미 다른 것이 만졌을 수 있다.
_pytest_args: list[str] = []


def pytest_configure(config) -> None:
    global _pytest_args
    _pytest_args = [str(a) for a in (config.args or [])]
    # P-71 — 시험 DB 생성 경로에 OPS-03 우회층을 태운다 (아래 블록 참조).
    #   `django.setup()` 은 pytest-django 가 이미 끝냈다 — 그래서 여기가 첫 자리다.
    _install_migrate_bootstrap()
    # P-87 4 — 증거 폴더 격리 **바닥 그물** (아래 블록 참조).
    _install_evidence_net()


# ═══════════════════════════════════════════════════════════════════════════
# P-87 4 — **시험이 운영 증거를 덮었다** (2026-09-06 · 턴 I · 차선 Q)
#
# 무엇이 있었나 [실측 2026-09-06 · 턴 H · 차선 E]
# ----------------------------------------------
#   `gx-shell` 에는 `/docs` 가 붙어 있다. 그래서 시험이 `ops_audit_purge_beat()` 을
#   부르는 순간 그 호출이 `docs/agent/evidence/D-373/audit_purge_last.json` 을
#   **진짜로 고쳤다.** 파일을 읽은 사람은 개발 환경이 미선언이라고 읽는다 — 아니다.
#   시험 DB 에 선언이 없었을 뿐이다.
#
#   그때 막은 자리는 **한 곳뿐이었다**(`ops_tasks._write_evidence` 의 인라인 검사).
#   증거 폴더에 쓰는 자리는 그 하나가 아니다: 장부 명령 둘 · 라우트 등재부 하나 ·
#   시험 안의 부트스트랩 하나 · 시험이 불러 쓰는 `scripts/` 의 도구들.
#   **한 자리만 막은 가드는 「막혀 있다」는 착시를 준다.**
#
# 왜 술어만으로는 모자라나 — 그물이 따로 있는 이유
# ------------------------------------------------
#   공통 술어(`evidence_guard.blocked_reason`)는 **부르는 쪽이 기억해야** 듣는다.
#   기억을 요구하는 규칙은 바쁜 날 깨지고(D-286), 새로 생기는 쓰기 자리는 아무도
#   그 술어를 안다고 보장할 수 없다. 그래서 쓰기 **원시함수**에 그물을 건다 —
#   `open(…, "w")` · `os.replace` · `os.rename` · `os.remove`. 증거 폴더로 가는
#   쓰기는 우리 코드든 남의 코드든 여기서 `EvidenceWriteBlocked` 로 선다.
#
#   ★ 읽기는 안 건드린다. 증거를 **읽는** 시험은 많고 그것은 정상이다.
#   ★ 일부러 쓰는 자리(E2E 단계표)는 `allow_evidence_writes("사유")` 로 이름을 대고
#     연다 — 환경변수 하나로 통째로 끄는 손잡이는 두지 않는다. 통째로 끄는 손잡이는
#     반드시 「일단 켜 두고 잊기」로 쓰인다.
# ═══════════════════════════════════════════════════════════════════════════
def _install_evidence_net() -> None:
    try:
        from common import evidence_guard
    except Exception:                    # noqa: BLE001 — 그물이 없다고 시험을 막지 않는다
        return
    evidence_guard.install_pytest_net()


# ═══════════════════════════════════════════════════════════════════════════
# P-71 — **새 시험 DB 가 마이그레이션 잠금에서 죽는다** (2026-09-06 · 턴 G · 차선 S)
#
# 무엇이 막고 있었나 [실측 2026-09-06 · 새 이름 `test_gx_s_p71a` 로 재현]
# ---------------------------------------------------------------------
#     core/logger/migrations/0009_auditaccesstype_… .py:17
#         MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
#     E   LookupError: No installed app with label 'multilanguage'.
#
#   `logger/0009` 는 `multilanguage` 의존을 **선언하지 않는다.** 그래서 장고가 세운
#   기본 순서로 빈 DB 에 `migrate` 를 돌리면, 그 RunPython 이 아직 상태에 없는 앱을
#   찾다가 죽는다. 그 파일은 dj-core — **§0.4 금지구역이라 고칠 수 없다.**
#
#   OPS-03 은 이 잠금의 우회층을 이미 만들어 두었다: `manage.py migrate_bootstrap`
#   (`backend/common/management/commands/migrate_bootstrap.py`). 없던 것은 **그 층이
#   시험 DB 생성 경로에는 안 깔려 있었다**는 것뿐이다. 사람이 손으로 부르는 명령이라
#   pytest 가 만드는 DB 는 그 순서를 모른 채 태어났다.
#
#   ★ **순서를 아는 것은 도구여야 한다** (D-286). 「새 시험 DB 를 만들기 전에
#     migrate_bootstrap 을 부르세요」는 사람의 기억에 맡긴 절차이고, 기억에 맡긴 절차는
#     바쁜 날 빠진다. 그래서 여기서 **자동으로** 같은 순서를 태운다.
#
# 무엇을 고쳤나 — **순서만.** 스키마도 dj-core 도 한 글자 안 바꿨다
# ------------------------------------------------------------------
#   장고의 `BaseDatabaseCreation.create_test_db` 는 빈 DB 를 만든 뒤 `migrate` 를
#   **한 번** 부른다(django 5.1 `db/backends/base/creation.py`). 그 한 번 앞에
#   `migrate user` · `migrate multilanguage` 를 끼운다 — `migrate_bootstrap` 이 손으로
#   부를 때 밟는 것과 **같은 순서, 같은 목록**이다.
#
#   ★ 목록을 여기 베끼지 않는다. `BOOTSTRAP_ORDER` 를 **그 파일에서 읽어 온다** —
#     두 벌로 두면 한쪽만 고쳐지고, 어긋난 복사본 하나가 D-212 였다.
#   ★ 이미 선 DB(`keepdb`)에서는 그 걸음이 전부 「적용 완료」라 아무 일도 하지 않는다.
#   ★ **마이그레이션이 꺼진 실행이면 끼우지 않는다.** 그때는 잠금도 함께 사라진다 —
#     `--nomigrations` 로 돌리면 이 결함이 안 보이던 이유가 바로 그것이다.
#     ⚠ 꺼졌는지는 깃발 하나로 못 묻는다: `TEST['MIGRATE'] is False` **와**
#     pytest-django 의 `--nomigrations`(= `settings.MIGRATION_MODULES` 교체)가
#     서로 다른 자리를 건드린다. `migrations_are_disabled()` 참조 — 그 하나를
#     빠뜨려 786 passed 가 21 errors 가 됐다 [실측 2026-09-06].
# ═══════════════════════════════════════════════════════════════════════════
def migrations_are_disabled(app_labels) -> bool:
    """마이그레이션이 **꺼진 실행인가.** 깃발을 믿지 않고 장고에게 직접 묻는다.

    ★ 왜 술어가 둘이 되었나 [실측 2026-09-06 · 턴 G · 조율자]
    ------------------------------------------------------
    이 훅은 처음에 `TEST['MIGRATE'] is False` 하나로만 물었다. 그런데
    **pytest-django 의 `--nomigrations` 는 그 칸을 안 건드린다** — 대신
    `settings.MIGRATION_MODULES` 를 「무엇을 물어도 None」인 물건으로 갈아 끼운다.
    그래서 판별자가 「꺼지지 않았다」고 답했고, 훅이 `migrate user` 를 불렀고,
    문서에 적힌 빠른 경로가 통째로 죽었다:

        conftest.py:183 create_test_db → :176 call_command
        CommandError: App 'user' does not have migrations.     ← 786 passed 가 21 errors

    ★ **깃발은 두 벌인데 사실은 하나다.** 그럴 때는 깃발을 세지 말고 사실을 잰다 —
      「이 앱에 태울 마이그레이션이 있는가」를 장고 자신의 로더에게 묻는다.
      새 도구가 세 번째 방식으로 마이그레이션을 꺼도 이 술어는 그대로 맞는다.

    ⚠ `all()` 이다 — 목록의 앱이 **하나라도** 태울 것이 있으면 켜진 실행으로 본다.
      `any()` 로 쓰면 앱 하나만 마이그레이션이 없어도 우회층 전체가 조용히 꺼진다.
    """
    from django.db.migrations.loader import MigrationLoader

    labels = tuple(app_labels)
    if not labels:
        return False
    try:
        return all(MigrationLoader.migrations_module(a)[0] is None for a in labels)
    except Exception:            # 앱 등록부를 못 읽으면 **끄지 않는다** (안전한 쪽)
        return False


def bootstrap_steps(order, *, migrate_disabled: bool) -> tuple:
    """시험 DB 의 `migrate` **앞에** 밟을 걸음. **순수 함수다** — DB 없이 시험한다.

    마이그레이션이 꺼진 실행이면 빈 튜플이다. 꺼진 실행에 순서를 끼우면 **없는 일을
    한 척**하게 되고, 그 척은 다음 사람이 이 훅을 믿지 못하게 만든다.

    ⚠ `migrate_disabled` 를 **판단하는 것은 이 함수가 아니다**(순수하게 남기려고).
      그 판단은 `migrations_are_disabled()` 가 하고, 그 자리가 한 번 틀렸었다.
    """
    if migrate_disabled:
        return ()
    return tuple(order)


_BOOTSTRAP_INSTALLED = False


def _install_migrate_bootstrap() -> None:
    """`create_test_db` 안의 `migrate` 한 번 앞에 OPS-03 순서를 끼운다."""
    global _BOOTSTRAP_INSTALLED
    if _BOOTSTRAP_INSTALLED:
        return

    import django.core.management as _mgmt
    from django.db.backends.base.creation import BaseDatabaseCreation

    original_create = BaseDatabaseCreation.create_test_db

    def create_test_db(self, verbosity=1, autoclobber=False, keepdb=False,
                       serialize=True):
        # ⚠ 목록의 정본은 OPS-03 우회층이다. 여기서 **읽어 오고, 베끼지 않는다.**
        try:
            from common.management.commands.migrate_bootstrap import BOOTSTRAP_ORDER
        except ImportError:                      # 우회층이 없으면 아무것도 안 한다
            return original_create(self, verbosity, autoclobber, keepdb, serialize)

        alias = self.connection.alias
        disabled = (
            self.connection.settings_dict.get("TEST", {}).get("MIGRATE") is False
            or migrations_are_disabled(BOOTSTRAP_ORDER)
        )
        steps = bootstrap_steps(BOOTSTRAP_ORDER, migrate_disabled=disabled)
        original_call = _mgmt.call_command
        state = {"done": not steps}

        def call_command(name, *args, **kwargs):
            # 장고가 빈 DB 에 부르는 **그 한 번**의 `migrate` 앞에서만 끼운다.
            # (인자 없는 `migrate` = 전체 계획. 앱 이름이 붙은 것은 우리가 부른 것이다)
            if name == "migrate" and not args and not state["done"]:
                state["done"] = True
                for app in steps:
                    original_call("migrate", app,
                                  verbosity=max(int(kwargs.get("verbosity", 1)) - 1, 0),
                                  interactive=False, database=alias)
            return original_call(name, *args, **kwargs)

        _mgmt.call_command = call_command
        try:
            return original_create(self, verbosity, autoclobber, keepdb, serialize)
        finally:
            _mgmt.call_command = original_call

    BaseDatabaseCreation.create_test_db = create_test_db
    _BOOTSTRAP_INSTALLED = True
