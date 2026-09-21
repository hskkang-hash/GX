#!/usr/bin/env python
"""마이그레이션 정합 검사 — **모델 선언과 표가 갈라지면 멈춘다** (D-282).

무엇을 막나 — 착시 ⑤ 환경
-------------------------
2026-08-29, `DetectionEvent` 표가 DB 에 **없는데 시험은 초록이었다.**
`pytest --nomigrations` 가 마이그레이션을 건너뛰고 **모델 선언에서 직접** 테스트 DB 를
만들어 주기 때문이다. 시험은 모델을 봤고, 운영은 표를 본다. **재는 자리가 실물과 달랐다.**

    D-282: *"시험 환경이 실물과 다르면 초록은 실물을 말하지 않는다."*
           *"--nomigrations 는 **속도용 보조 수단**이지 정본 판정 환경이 아니다."*

앞의 네 착시와 종류가 다르다:

    ① 부착률(D-249) ② 시나리오 수(D-262) ③ 모수와 술어(D-271)  → 무엇을 얼마나 쟀나
    ④ 탐지기 자체(D-277)                                        → 재는 기계가 작동하나
    ⑤ **환경(D-282)**                                           → **재는 자리가 실물인가**

무엇을 보나 — **눈이 둘이다**
-----------------------------
모델에서 표까지는 두 걸음이고, 이번 사고는 **둘째 걸음**에서 났다. 한쪽만 보면 못 잡는다.

    ① 모델 → 마이그레이션 파일   `makemigrations --check --dry-run` 과 같은 판정.
                                  D-282 가 지목한 눈이다. "모델 14건 / 표 0건" 처럼
                                  **선언은 있는데 마이그레이션이 없는** 상태를 잡는다.

    ② 마이그레이션 파일 → DB     `migrate --check` 와 같은 판정. **이번에 실제로 벌어진
                                  격차**가 여기다 — `0016_detectionevent` 는 파일로는
                                  있었지만 DB 에 적용되지 않았고, 그래서 표가 없었다.
                                  ①만 보면 이 상태는 **초록으로 보인다.**

    ※ ② 는 D-282 문언을 넘어선 추가다. 근거: D-282 의 원칙이 "재는 자리가 실물인가"이고,
      ①만으로는 **실물(DB)을 아예 보지 않기** 때문이다. 판정문에 없는 것을 임의로
      더한 것이므로 증거 문서에 명시하고 회신에서 확인을 구한다.

    python scripts/verify_migrations.py            # 두 눈 모두 (어긋나면 exit 1)
    python scripts/verify_migrations.py --list     # 앱별 미반영 변경·미적용 마이그레이션 출력
    python scripts/verify_migrations.py --no-db    # ① 만 (DB 없는 곳에서 — ②는 판정 불가로 남는다)
    python scripts/verify_migrations.py --self-test  # ★ 탐지기가 실제로 탐지하는지 (D-277)

★ 양성 대조 의무 (D-277)
------------------------
"미반영 변경 0건"은 **탐지기가 눈이 멀었을 때도 나오는 값**이다. 그래서 판정할 때마다
가짜 필드 하나를 모델 상태에 심어 자동탐지기에 먹이고, **그것이 잡히는지**를 함께 본다.
잡히지 않으면 본 판정의 초록도 **무효로 처리한다**(exit 1) — 재는 기계가 작동하지
않는데 나온 초록을 통과로 세지 않는다.

Django 가 없으면 — **통과가 아니라 판정 불가다**
------------------------------------------------
이 검사는 Django 를 띄워야 한다(사내 private 패키지 `dj-core` 의존). 호스트나
`python:3.11-alpine` CI 러너에서는 import 자체가 안 된다. 그때 **exit 0 을 내지 않는다** —
`verify_layers` 가 대상 0건일 때 self-test 로 넘어가는 것과 같은 이유다.
**못 센 것을 통과로 세지 않는다.** 판정 불가는 exit 2 이고, 호출하는 쪽이 그것을
"환경 미비"로 다룰지 "실패"로 다룰지 정한다.

    exit 0  정합 — 두 눈 모두 0건이고 자기 시험도 통과
    exit 1  불일치 — 미반영 변경·미적용 마이그레이션이 있거나, 탐지기가 자기 시험에 실패
    exit 2  판정 불가 — Django 를 띄우지 못했거나 DB 에 닿지 못했다 (**통과가 아니다**)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_DRIFT, EXIT_CANNOT_JUDGE = 0, 1, 2


def _boot_django() -> str | None:
    """Django 를 띄운다. 실패하면 그 사유를 문자열로 돌려준다 (예외를 삼키지 않는다)."""
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        import django

        django.setup()
    except Exception as exc:  # noqa: BLE001 — 무엇 때문에 못 띄웠는지 그대로 보고한다
        return f"{type(exc).__name__}: {exc}"
    return None


def _detect(extra_field: tuple[str, str] | None = None) -> list[tuple[str, list[str]]]:
    """마이그레이션 그래프와 현재 모델 선언의 차이를 앱별로 낸다.

    `makemigrations --check --dry-run` 이 하는 판정과 같은 것을 **직접** 한다.
    관리 명령을 subprocess 로 부르지 않는 이유는 두 가지다 —
    ① 종료 코드만 보면 *무엇이* 어긋났는지 이 파일이 말해 줄 수 없다.
    ② `--self-test` 가 가짜 변경을 심으려면 자동탐지기의 입력(ProjectState)에 손이 닿아야 한다.

    `extra_field` 는 self-test 전용이다: `(app_label.model_name, field_name)` 자리에
    없던 필드 하나를 **모델 상태 쪽에만** 심는다. 정상 판정이라면 이것이 반드시 잡혀야 한다.
    """
    from django.apps import apps as django_apps
    from django.db import connections, models
    from django.db.migrations.autodetector import MigrationAutodetector
    from django.db.migrations.loader import MigrationLoader
    from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
    from django.db.migrations.state import ProjectState

    loader = MigrationLoader(None, ignore_no_migrations=True)
    from_state = loader.project_state()
    to_state = ProjectState.from_apps(django_apps)

    if extra_field is not None:
        label, field_name = extra_field
        model_state = to_state.models[tuple(label.split("."))]
        model_state.fields[field_name] = models.CharField(max_length=8, null=True)
        to_state.reload_model(*label.split("."))

    autodetector = MigrationAutodetector(
        from_state, to_state,
        NonInteractiveMigrationQuestioner(specified_apps=set(), dry_run=True),
    )
    changes = autodetector.changes(
        graph=loader.graph, trim_to_apps=None, convert_apps=None,
        migration_name=None,
    )
    connections.close_all()

    out: list[tuple[str, list[str]]] = []
    for app_label, migrations_ in sorted(changes.items()):
        ops = [f"{op.__class__.__name__}: {getattr(op, 'name', '') or getattr(op, 'model_name', '')}"
               f"{('.' + op.name) if hasattr(op, 'model_name') and hasattr(op, 'name') else ''}"
               for migration in migrations_ for op in migration.operations]
        out.append((app_label, ops))
    return out


def _unapplied() -> tuple[list[str], str | None]:
    """DB 에 **적용되지 않은** 마이그레이션 목록. 두 번째 눈 (D-282 확장).

    돌려주는 것은 `(미적용 목록, DB 오류)` 다. DB 에 못 닿았으면 목록은 비고 오류가 찬다 —
    **빈 목록을 "미적용 0건"으로 세지 않기 위해서다.** 못 센 것과 0 은 다르다.
    """
    from django.db import DEFAULT_DB_ALIAS, connections
    from django.db.migrations.executor import MigrationExecutor

    conn = connections[DEFAULT_DB_ALIAS]
    try:
        executor = MigrationExecutor(conn)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
    except Exception as exc:  # noqa: BLE001 — DB 미가동·권한 등, 사유를 그대로 올린다
        return [], f"{type(exc).__name__}: {exc}"
    finally:
        connections.close_all()
    return [f"{app}.{name}" for (app, name), _backwards in
            [((m.app_label, m.name), b) for m, b in plan]], None


def _unapplied_self_test() -> list[str]:
    """★ ② 눈도 대조한다 — 미적용이 **있을 때** 잡는가 (D-277).

    지금 DB 는 전부 적용돼 있어 ② 는 늘 0 을 낸다. **0 은 탐지기가 눈이 멀었을 때도 나온다.**
    그래서 로더가 기억하는 "적용됨" 집합에서 항목 하나를 **메모리에서만** 빼고 다시 세어
    본다 — DB 는 건드리지 않는다(읽기 전용, D-270). 그때 계획이 비어 있으면 ② 는 무효다.
    """
    from django.db import DEFAULT_DB_ALIAS, connections
    from django.db.migrations.executor import MigrationExecutor

    conn = connections[DEFAULT_DB_ALIAS]
    try:
        executor = MigrationExecutor(conn)
        applied = executor.loader.applied_migrations
        if not applied:
            return ["self-test 불가(②): 적용된 마이그레이션이 하나도 없다 — 대조할 것이 없다"]
        # leaf 하나를 골라 '적용 안 된 것처럼' 만든다. leaf 여야 계획에 확실히 들어온다.
        leaves = [n for n in executor.loader.graph.leaf_nodes() if n in applied]
        if not leaves:
            return ["self-test 불가(②): 적용된 leaf 가 없다 — 대조할 것이 없다"]
        victim = leaves[0]
        # ★ 여기서 `build_graph()` 를 부르면 안 된다 — 그것이 DB 에서 적용 목록을
        #   **다시 읽어** 방금 세운 가정을 지운다. 처음 이 대조를 그렇게 짰다가
        #   "탐지기가 눈멀었다"는 실패를 받았고, 눈이 먼 것은 탐지기가 아니라 대조였다.
        #   그 실패가 곧 이 대조가 작동한다는 증거다 (D-277).
        del executor.loader.applied_migrations[victim]
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception as exc:  # noqa: BLE001
        return [f"self-test 불가(②): {type(exc).__name__}: {exc}"]
    finally:
        connections.close_all()

    if not plan:
        return ["self-test 실패(②): 적용됨 표식 하나를 뺐는데 **미적용으로 세지 못했다.** "
                "이 상태의 '미적용 0건' 은 초록이 아니라 아무것도 재지 않은 것이다 (D-277)"]
    print(f"[MIGR] 양성 대조(②) — 적용 표식 1건({victim[0]}.{victim[1]})을 빼자 "
          f"미적용 {len(plan)}건으로 잡혔다. 판정기는 작동한다")
    return []


def self_test() -> list[str]:
    """★ 탐지기가 실제로 탐지하는가 (D-277 양성 대조).

    없던 필드 하나를 모델 상태에 심는다. 이것이 **안 잡히면** 자동탐지기가 눈이 먼 것이고,
    그러면 본 판정의 "미반영 0건" 도 아무 뜻이 없다. `verify_layers --self-test` 와 같은 계열.
    """
    problems: list[str] = []
    probe = ("stream_monitors.detectionevent", "gx_selftest_probe_field")

    try:
        planted = _detect(extra_field=probe)
    except KeyError:
        # 대조 대상 모델이 없으면 **다른 모델로 갈아타지 않는다.** 조용히 통과하는 것보다
        # "대조를 못 했다"고 말하는 편이 낫다 — 그 침묵이 정확히 D-277 이 막는 것이다.
        return [f"self-test 불가: 대조 모델 {probe[0]} 이 없다. "
                f"모델이 옮겨졌다면 이 파일의 probe 를 같은 커밋에서 함께 고쳐라"]

    hit = any(probe[1] in op for _, ops in planted for op in ops) or bool(planted)
    if not hit:
        problems.append(
            "self-test 실패: 없던 필드를 심었는데 자동탐지기가 **잡지 못했다.** "
            "이 상태에서 나오는 '미반영 0건' 은 초록이 아니라 아무것도 재지 않은 것이다 (D-277)")
    else:
        print("[MIGR] 양성 대조 — 가짜 필드 1건을 심자 탐지기가 잡았다. 판정기는 작동한다")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="마이그레이션 정합 검사 (D-282)")
    ap.add_argument("--list", action="store_true", help="앱별 미반영 변경을 전부 출력")
    ap.add_argument("--self-test", action="store_true", help="탐지기 자체만 시험한다 (D-277)")
    ap.add_argument("--no-db", action="store_true",
                    help="② 마이그레이션→DB 눈을 끈다 (DB 없는 러너용 — 초록이 아니라 판정 불가로 남는다)")
    args = ap.parse_args()

    boot_error = _boot_django()
    if boot_error is not None:
        print(f"[MIGR] 판정 불가 — Django 를 띄우지 못했다: {boot_error}")
        print("[MIGR] ※ 이것은 **통과가 아니다** (exit 2). 이 검사는 dj-core 가 설치된 "
              "환경(backend 컨테이너)에서 돌아야 한다 — 못 센 것을 통과로 세지 않는다")
        return EXIT_CANNOT_JUDGE

    problems = self_test()
    if not args.no_db:
        problems += _unapplied_self_test()
    if args.self_test:
        for p in problems:
            print(f"  · {p}")
        print("[MIGR] self-test " + ("실패" if problems else "통과"))
        return EXIT_DRIFT if problems else EXIT_OK

    drift = _detect()
    n_ops = sum(len(ops) for _, ops in drift)
    if drift:
        problems.append(
            f"마이그레이션에 반영되지 않은 모델 변경 {n_ops}건 "
            f"({len(drift)}개 앱: {', '.join(a for a, _ in drift)}). "
            f"`python manage.py makemigrations` 로 생성하고, **적용은 D-209/D-283 절차**를 "
            f"따른다 — 생성과 적용은 다른 일이다")
        if args.list:
            for app_label, ops in drift:
                print(f"  [{app_label}]")
                for op in ops:
                    print(f"    · {op}")

    # 분모와 술어를 함께 적는다 (D-271 신설 규칙).
    print(f"[MIGR] ① 모델→마이그레이션 — 미반영 {n_ops}건 "
          f"(술어=MigrationAutodetector, 모수=INSTALLED_APPS 전수, D-282)")

    # ── ② 마이그레이션 → DB ─────────────────────────────────────────────
    cannot_judge_db = False
    if args.no_db:
        print("[MIGR] ② 마이그레이션→DB — **판정 안 함**(--no-db). "
              "이것은 초록이 아니다: 이번 사고(0016 미적용)는 정확히 이 눈이 보는 자리였다")
        cannot_judge_db = True
    else:
        unapplied, db_error = _unapplied()
        if db_error is not None:
            print(f"[MIGR] ② 마이그레이션→DB — **판정 불가**: {db_error}")
            print("[MIGR]    ※ 빈 목록을 '미적용 0건' 으로 세지 않는다. 못 센 것과 0 은 다르다")
            cannot_judge_db = True
        else:
            print(f"[MIGR] ② 마이그레이션→DB — 미적용 {len(unapplied)}건 "
                  f"(술어=MigrationExecutor.migration_plan, 모수=leaf 전수)")
            if unapplied:
                if args.list:
                    for name in unapplied:
                        print(f"    · {name}")
                problems.append(
                    f"DB 에 적용되지 않은 마이그레이션 {len(unapplied)}건 "
                    f"({', '.join(unapplied[:5])}{' …' if len(unapplied) > 5 else ''}). "
                    f"**파일이 있는 것과 표가 있는 것은 다르다** — 이 상태에서 --nomigrations "
                    f"시험이 초록이면 그 초록은 실물을 말하지 않는다 (D-282 착시 ⑤). "
                    f"적용은 D-283 절차(DDL 첨부 → 역방향 확인 → 로컬만 → 스냅샷)를 따른다")

    if problems:
        print("\n[MIGR] 불일치")
        for p in problems:
            print(f"  · {p}")
        return EXIT_DRIFT

    if cannot_judge_db:
        print("[MIGR] ① 정합 · ② 판정 불가 — **초록으로 세지 않는다** (exit 2)")
        return EXIT_CANNOT_JUDGE
    print("[MIGR] 정합 — 모델 선언 = 마이그레이션 그래프 = DB")
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    _n_mig = sum(1 for _p in (ROOT / "backend").rglob("migrations/*.py")
                 if _p.name != "__init__.py")
    gate_header(
        __file__,
        measured=("① 모델 → 마이그레이션 미반영 ② 마이그레이션 → DB 미적용 — "
                  "**분모 %s개**(`backend/**/migrations/*.py` 전수 · 지금 셌다) + "
                  "살아 있는 DB 의 적용 이력(ORM 으로 받는다). ★ **빈 목록을 "
                  "「미적용 0건」으로 세지 않는다** — 못 센 것과 0 은 다르다"
                  % (_n_mig or "못 셌다")),
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        source="살아 있는 DB·앱 레지스트리 (django.setup 뒤 ORM) — 파일 사진이 아니다",
    )
    raise SystemExit(main())
