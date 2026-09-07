#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""착시 ⑨ **배선의 착시** — 「만들어진 것」과 「켜진 것」은 다르다 (D-377).

    K3 역할별 프레임 : 코드가 **서 있었다**. 설정이 비어 모두가 같은 화면을 봤다
    모니터링 3종     : `scripts/ops_monitor.py` 가 **있었다**. 없던 건 주기다
    백업 자동화      : `scripts/ops_backup.py` 가 **있었다**. 없던 건 주기다

셋 다 「구현하라」고 지시받았고 셋 다 이미 있었다. 없던 것은 **코드가 아니라 배선과 주기**다.
착시 ⑥(스키마)은 「필드가 있으면 기능이 있다」고 읽는 것이었다. ⑨(배선)은 한 단계 위다 —
**「코드가 있으면 동작한다」고 읽는 것.** 시험은 함수를 직접 불러 통과시키고, 운영은 그
함수를 부르지 않는다. **둘 다 초록이다.**

이 스크립트가 하는 일
---------------------
「잠자는 기능」을 **세 술어로 따로** 센다. ★ 셋을 한 수로 합치지 않는다 —
**고치는 방법이 다르기 때문이다**(D-377). ㉠은 배선, ㉡은 등록, ㉢은 데이터다.

    ㉠ 호출 없음   정의는 있으나 **운영 코드가 그 이름을 한 번도 부르지 않는다**
                   (시험만 부르는 것도 여기다 — 운영에서는 죽은 것이다)
    ㉡ 주기 없음   주기적으로 돌아야 하는데 **스케줄러에도 없고 아무도 큐에 넣지 않는다**
    ㉢ 설정 빔     코드는 분기하는데 **설정이 비어 늘 같은 가지로 간다**

    python scripts/verify_dormant.py               # 판정 (세 술어 건수 각각)
    python scripts/verify_dormant.py --list        # 잠자는 것 전수
    python scripts/verify_dormant.py --census      # 모수·술어와 함께 전체 표
    python scripts/verify_dormant.py --predicate b # 한 술어만
    python scripts/verify_dormant.py --self-test   # 양성·음성 대조 (D-277)
    python scripts/verify_dormant.py --freeze      # 오늘의 빚을 기준선에 잠근다 (D-311)

★ 래칫이다 (D-311). 오늘 자는 것을 이름으로 잠그고 **새로 자는 것만** 막는다.
  **새로 만드는 것은 「켜진 상태로 태어나야 한다」** — 운영 경로 연결 없이 커밋되면 exit 1.

⚠ 이 판정기는 **정적**이다. 문자열로 부르는 자리(`import_string`·`send_task("a.b")`)는
  이름이 소스에 나타나므로 잡히지만, 완전히 동적으로 조립하는 이름은 놓친다.
  그래서 **놓치는 쪽으로 틀린다** — 자는 것을 깨어 있다고 볼 수는 있어도, 깨어 있는 것을
  자고 있다고 말하는 일은 드물다. 래칫으로 두는 이유가 그것이다.

⚠ §0.4 금지구역(delivery·orders·terminals)은 **세되 잔여 분모에서 뺀다**(D-311).
  우리가 못 고치는 빚을 분모에 넣으면 갚을 수 없는 수가 진척률을 눌러 앉힌다.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-377" / "dormant_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

_SKIP_DIRS = {"__pycache__", "migrations", ".venv", "node_modules", "venv"}

#: §0.4 이관 자산 — 세되 우리 잔여에서는 뺀다.
FORBIDDEN_APPS = {"delivery", "orders", "terminals"}

# ---------------------------------------------------------------------------
# ㉠ 이 이름들은 **프레임워크가 부른다.** 우리 코드에 호출부가 없는 것이 정상이다.
#    여기에 넣는 것은 면제가 아니라 **모수에서 빼는 것**이다 — 애초에 우리가 부를 자리가 없다.
# ---------------------------------------------------------------------------
FRAMEWORK_HOOKS = {
    # Django
    "ready", "handle", "add_arguments", "save", "delete", "clean", "clean_fields",
    "get_queryset", "get_object", "get_context_data", "get_absolute_url", "get_form",
    "get_serializer", "get_serializer_class", "get_permissions", "has_permission",
    "has_object_permission", "form_valid", "form_invalid", "dispatch",
    "get", "post", "put", "patch", "options", "head",
    # DRF / ninja / serializer
    "to_representation", "to_internal_value", "validate", "create", "update",
    "resolve", "run_validation",
    # celery / channels / asgi
    "run", "on_failure", "on_success", "on_retry", "connect", "disconnect",
    "receive", "receive_json", "send_json", "websocket_connect", "websocket_disconnect",
    # migration / app config
    "forwards", "backwards",
    # ★ [2026-09-26] pytest — **훅과 픽스처는 pytest 가 이름으로 부른다.**
    #   QA-11 이 `backend/conftest.py` 에 훅 하나와 픽스처 하나를 넣자 이 판정기가
    #   「아무도 안 부른다」로 잡았다. 옳은 관찰이고 **틀린 결론**이다: 부르는 쪽이
    #   우리 코드가 아닐 뿐 그 둘은 매 실행마다 돈다. 안 돌면 시험이 통째로 다르게 돈다.
    #   ⚠ 이름으로 거르므로 좁게 적는다 — 넓히면 「conftest 에 있으면 다 봐준다」가 된다.
    "pytest_configure", "pytest_collection_modifyitems", "pytest_addoption",
    "pytest_load_initial_conftests", "pytest_sessionstart", "pytest_sessionfinish",
    "pytest_runtest_setup", "pytest_generate_tests",
    "django_db_setup", "django_db_modify_db_settings",
}

#: 진입점을 표시하는 데코레이터. 이것이 붙으면 **프레임워크가 진입시킨다** — 모수 밖이다.
ENTRY_DECORATORS = {
    "shared_task", "task", "periodic_task", "receiver", "property", "cached_property",
    "setter", "getter", "deleter", "register", "api_controller",
    #: pytest 픽스처 — 이름이 아니라 **데코레이터**로 안다. `@pytest.fixture` 가 붙으면
    #: 부르는 쪽은 pytest 이고, 그것은 우리 코드에 안 나타난다.
    "fixture",
    "get", "post", "put", "patch", "delete", "route", "http_get", "http_post",
    "http_put", "http_patch", "http_delete", "database_sync_to_async",
}

#: ★ 출생 표본 (D-310 · D-393) — **데코레이터의 「점 뒤」가 배선인 갈래.**
#   `ENTRY_DECORATORS` 는 **이름 집합**이라 `@receiver` 는 잡지만
#   `@worker_process_init.connect` 는 못 잡는다. `_dec_names` 가 내는 이름은
#   {"connect", "worker_process_init"} 이고 둘 다 위 집합에 없다.
#   그래서 `backend/config/celery.py` 의 시그널 훅 셋이 ㉠「호출 없음」에 들었고,
#   D-388 이 그 셋을 **㉮「켜야 할 것」**으로 냈다 — **이미 켜져 있는 것을** 그렇게 냈다.
#   ★ gunicorn `server-hook` 오답(D-388 ③)과 **같은 모양**이다: 프레임워크가 부르는 자리를
#     「아무도 안 부른다」로 읽는다. 그때는 파일 이름으로 메웠고, 여기서는 **배선 형태**로 잡는다.
#   `@sig.connect` · `@sig.connect(sender=X)` 둘 다 django/celery 의 표준 시그널 배선이다.
_SIGNAL_WIRING_ATTRS = {"connect", "connect_via"}


def _wired_by_signal(fn: ast.AST) -> bool:
    """`@<시그널>.connect` 로 **배선된** 함수인가.

    이름이 아니라 **모양**을 본다 — 점 앞이 무엇이든 점 뒤가 `connect` 면 배선이다.
    `ENTRY_DECORATORS` 에 `"connect"` 를 넣는 것으로도 오늘은 같은 결과가 나오지만,
    그러면 `@connect` 라는 **이름의** 데코레이터까지 함께 빠진다. 모수에서 빼는 일은
    좁게 하는 쪽이 옳다 — 넓게 빼면 진짜 잠든 것이 조용히 사라진다 (D-301).
    """
    for dec in getattr(fn, "decorator_list", []) or []:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Attribute) and node.attr in _SIGNAL_WIRING_ATTRS:
            return True
    return False

#: ㉢ 「비었다」로 보는 값. 코드가 이 값으로 분기하면 **늘 같은 가지로 간다.**
_EMPTY_LITERALS = ("", None, False)


def iter_py(root: Path) -> list[Path]:
    out = []
    for p in root.rglob("*.py"):
        if set(p.parts) & _SKIP_DIRS:
            continue
        out.append(p)
    return sorted(out)


def _is_test(p: Path) -> bool:
    parts = set(p.parts)
    return "tests" in parts or p.name.startswith("test_") or p.name.endswith("_test.py")


def parse_all(paths: list[Path]) -> dict[Path, ast.Module]:
    out: dict[Path, ast.Module] = {}
    for p in paths:
        try:
            out[p] = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        except SyntaxError:
            # 못 읽은 것은 **못 읽었다고 말한다**. 조용히 넘기면 0건이 통과가 된다 (D-301).
            print(f"[DORMANT] WARN 파싱 실패(건너뜀): {p}", file=sys.stderr)
    return out


def _dec_names(fn: ast.AST) -> set[str]:
    out: set[str] = set()
    for dec in getattr(fn, "decorator_list", []) or []:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
            if isinstance(node.value, ast.Name):
                out.add(node.value.id)
    return out


def _rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


# ===========================================================================
# ㉠ 호출 없음 — 정의는 있으나 운영 코드가 그 이름을 부르지 않는다
# ===========================================================================
def audit_uncalled(trees, ref_only_trees=None):
    """(모수, 잠든 것, 라벨별 (운영참조, 시험참조)).

    참조는 **정의 밖의 이름 등장**으로 센다 — 호출·속성·문자열 셋 다. 호출만 세면
    `handlers = [foo, bar]` 처럼 **넘겨서 부르는 자리**를 놓치고, 그러면 살아 있는 것을
    잠들었다고 말한다. 이 판정기는 그 반대로 틀리게 두었다(놓치는 쪽으로).

    ★★ `ref_only_trees` — **부르는 쪽으로만 세고 모수에는 안 넣는 나무** (2026-09-05 TC)
    -------------------------------------------------------------------------------
    [실측 2026-09-05 · 턴 C 병합] `backend/common/front_line.py` 의 셋
    (`parse_gated_paths`·`parse_key_allowed`·`render_locations`)이 **잠들었다**고 나왔다.
    그런데 `scripts/ops_front_line.py` 가 셋을 **전부 부르고 있었다** — 그 파일이
    앞단(nginx) 설정을 만들어 내는 우리 운영 도구다.

    뿌리는 코드가 아니라 **이 판정기의 눈**이었다: 참조를 `backend/**` 안에서만 찾았다.
    독스트링은 「**운영 코드가** 그 이름을 부르지 않는다」라고 적어 놓고, 실제로는
    「backend 안의 코드가 부르지 않는다」를 재고 있었다 — **주장보다 좁게 재고 있었다.**

    그래서 참조 스캔만 `scripts/**` 로 넓힌다. **모수는 넓히지 않는다** —
    scripts 의 함수까지 모수에 넣으면 판정기·프로브의 내부 도우미가 전부 「잠들었다」로
    쏟아지고, 그 소음이 진짜 하나를 덮는다. **넓히는 것은 보는 눈이지 재는 대상이 아니다.**

    ⚠ 이것은 게이트를 무르게 하는 변경이 아니다. 무르게 하는 변경은 「부르는 곳이 없는데
      통과시키는 것」이고, 이것은 「부르는 곳이 있는데 못 보던 것을 보는 것」이다.
      둘을 헷갈리면 다음에 진짜 면제를 이 이름으로 밀어 넣게 된다.
    """
    defs: dict[str, list[str]] = defaultdict(list)      # 이름 -> [라벨]
    for path, tree in trees.items():
        if _is_test(path):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith("_") or name in FRAMEWORK_HOOKS:
                continue
            if _dec_names(node) & ENTRY_DECORATORS:
                continue
            if _wired_by_signal(node):         # `@sig.connect` — 배선이다 (D-393)
                continue
            defs[name].append(f"{_rel(path)}::{name}")

    names = set(defs)
    prod_refs: dict[str, int] = defaultdict(int)
    test_refs: dict[str, int] = defaultdict(int)

    #: ★★ `scripts/**` 의 참조는 **가져온 이름만** 센다 — 맨이름 등장으로 세면 안 된다.
    #:   [실측 2026-09-05 · 첫 판이 그렇게 셌고 13건이 깨어났는데 그중 여럿이 가짜였다]
    #:     · `probe_commented_guards.py` 는 `oauth2_required` 를 **감사 대상으로 찾는다** —
    #:       부르는 것이 아니라 **찾는** 것이다. 그것을 「부른다」로 세면 정반대다.
    #:     · `classify_dormant.py` 는 **잠든 이름을 나열하는 도구**다. 맨이름으로 세면
    #:       **잠든 것을 적어 둔 도구가 잠든 것을 깨운다** — 판정기가 자기 꼬리를 문다.
    #:     · `setUp` 처럼 흔한 이름은 아무 도구에나 있어서 backend 의 동명이인을 전부 깨운다.
    #:   그래서 여기서는 `from <모듈> import <이름>` 과 `import <모듈>` + `<모듈>.<이름>`
    #:   만 인정한다. **가져오는 것은 쓰겠다는 선언이고, 이름을 적는 것은 아니다.**
    for tree in (ref_only_trees or {}).values():
        imported: set[str] = set()
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for a in node.names:
                    imported.add(a.asname or a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    modules.add((a.asname or a.name).rsplit(".", 1)[-1])
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in names and node.id in imported:
                prod_refs[node.id] += 1
            #: ★ [실측 2026-09-06 · 턴 I · 조율자] **`from pkg import module` 도 모듈을
            #:   가져오는 것이다.** 이 줄은 `import pkg.module` 만 모듈로 셌고,
            #:   `from common import evidence_guard` 로 가져온 뒤
            #:   `evidence_guard.synthetic_run(...)` 로 **실제로 부르는** 자리를 못 봤다.
            #:   그래서 판정기 안에서 이미 도는 함수가 「잠들었다」로 나왔다 —
            #:   **깨어 있는 것을 잠들었다고 말하는 빨강**이고, 그런 빨강은 게이트를 끄게 한다.
            #:   ⚠ 느슨해진 것이 아니다: 여전히 **가져온 이름**을 통한 참조만 센다.
            #:     맨이름 등장(`ast.Name` 인데 import 없음)은 종전대로 안 센다 —
            #:     「감사 대상으로 찾는 이름」을 「부른 이름」으로 세던 그 사고가 그 규칙이다.
            elif (isinstance(node, ast.Attribute) and node.attr in names
                  and isinstance(node.value, ast.Name)
                  and (node.value.id in modules or node.value.id in imported)):
                prod_refs[node.attr] += 1

    #: 모수는 위에서 `trees` 로만 세웠다. backend 안의 참조는 종전 규칙 그대로.
    for path, tree in trees.items():
        is_test = _is_test(path)
        bucket = test_refs if is_test else prod_refs
        for node in ast.walk(tree):
            # ★ `def foo` 의 이름은 `ast.Name` 노드가 **아니다** — 그래서 정의 자신을 빼는
            #   보정이 필요 없다. 1차판은 그 보정을 넣었고, 자기 파일 안에서 부르는
            #   함수(`entry()` 가 `called_helper()` 를 부르는 자리)가 **잠들었다고 나왔다.**
            #   자기시험의 음성 갈래가 그것을 잡았다 (D-277 · D-350).
            if isinstance(node, ast.Name) and node.id in names:
                bucket[node.id] += 1
            elif isinstance(node, ast.Attribute) and node.attr in names:
                bucket[node.attr] += 1
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # `send_task("app.tasks.foo")` · `import_string("...")` — 문자열로 부르는 자리
                tail = node.value.rsplit(".", 1)[-1]
                if tail in names:
                    bucket[tail] += 1

    parametr: list[str] = []
    dormant: list[str] = []
    counts: dict[str, tuple[int, int]] = {}
    for name, labels in defs.items():
        p, t = prod_refs.get(name, 0), test_refs.get(name, 0)
        for label in labels:
            parametr.append(label)
            counts[label] = (p, t)
            if p == 0:
                dormant.append(label)
    return sorted(parametr), sorted(dormant), counts


# ===========================================================================
# ㉡ 주기 없음 — 태스크는 있는데 beat 에도 없고 아무도 큐에 넣지 않는다
# ===========================================================================
_BEAT_TASK_RE = re.compile(r"""["']task["']\s*:\s*["']([\w\.]+)["']""")
_COMMENTED_BEAT_RE = re.compile(r"""^\s*#.*["']task["']\s*:\s*["']([\w\.]+)["']""")


def _beat_names(celery_py: Path):
    """(등록된 태스크 이름, **주석으로 꺼진** 태스크 이름).

    ★ 주석으로 꺼진 항목은 잠자는 기능의 **가장 순수한 형태**다 — 누군가 켰다가 껐고,
      끈 사유는 어디에도 없다. 세지 않으면 영원히 안 보인다.
    """
    live: set[str] = set()
    dead: set[str] = set()
    if not celery_py.exists():
        return live, dead
    for line in celery_py.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _COMMENTED_BEAT_RE.match(line)
        if m:
            dead.add(m.group(1))
            continue
        if line.lstrip().startswith("#"):
            continue
        m = _BEAT_TASK_RE.search(line)
        if m:
            live.add(m.group(1))
    return live, dead


def audit_unscheduled(trees):
    tasks: dict[str, str] = {}
    for path, tree in trees.items():
        if _is_test(path):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decs = _dec_names(node)
            if not (decs & {"shared_task", "periodic_task"}) and not (
                    "task" in decs and decs & {"app", "celery_app", "celery"}):
                continue
            tasks[node.name] = f"{_rel(path)}::{node.name}"

    live, commented = _beat_names(BACKEND / "config" / "celery.py")
    live_tails = {n.rsplit(".", 1)[-1] for n in live}
    commented_tails = {n.rsplit(".", 1)[-1] for n in commented}

    # 누가 큐에 넣는가 — `foo.delay(...)` · `foo.apply_async(...)` · `send_task("...foo")`
    enqueued: set[str] = set()
    for path, tree in trees.items():
        if _is_test(path):
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            fn = node.func
            if fn.attr in ("delay", "apply_async"):
                base = fn.value
                if isinstance(base, ast.Attribute):
                    enqueued.add(base.attr)
                elif isinstance(base, ast.Name):
                    enqueued.add(base.id)
            elif fn.attr == "send_task":
                for a in node.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        enqueued.add(a.value.rsplit(".", 1)[-1])

    parametr, dormant, why = [], [], {}
    for name, label in sorted(tasks.items()):
        parametr.append(label)
        if name in live_tails:
            why[label] = "beat 등록"
        elif name in enqueued:
            why[label] = "코드가 큐에 넣는다"
        elif name in commented_tails:
            why[label] = "★ beat 에 **주석으로 꺼져** 있다 — 켰다가 끈 자리, 사유 없음"
            dormant.append(label)
        else:
            why[label] = "beat 에도 없고 큐에 넣는 자리도 없다"
            dormant.append(label)
    for n in sorted(commented_tails - set(tasks)):
        label = f"backend/config/celery.py::~{n}"
        parametr.append(label)
        why[label] = "★ beat 에 주석으로 꺼져 있다 (태스크 정의는 이 모수 밖)"
        dormant.append(label)
    return sorted(parametr), sorted(dormant), why


# ===========================================================================
# ㉢ 설정 빔 — 코드는 분기하는데 설정이 비어 늘 같은 가지로 간다
# ===========================================================================
_UNRESOLVED = "<계산값>"


def _resolve(node: ast.AST, env_names: set, known: dict | None = None):
    """설정 표현식을 **기본값으로** 접는다. 못 접으면 `<계산값>`.

    ★ 1차판은 `ast.literal_eval` 만 썼다. 그런데 이 저장소의 설정은 거의 전부
      `os.getenv("X", "")` 형태라 **한 건도 접히지 않았고**, 그래서 ㉢ 이 **0건**으로 나왔다.
      0건을 「빈 설정이 없다」로 읽었으면 착시 ⑨ 를 잡으러 만든 도구가 착시를 하나 더
      만들 뻔했다 — **측정기를 먼저 의심한다**(D-350).

    여기서 접는 것은 **환경이 아무 값도 안 줄 때 코드가 보게 되는 값**이다.
    그것이 비어 있고 저장소 어디에서도 값을 주지 않으면, 그 분기는 **늘 같은 가지로 간다.**
    """
    known = {} if known is None else known
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        # 같은 파일에서 앞서 정해진 이름 — 표는 보통 조각으로 나뉘어 있다
        return known.get(node.id, _UNRESOLVED)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError, TypeError):
            return _UNRESOLVED
    if isinstance(node, ast.Dict):
        # ★ `{**{c: "OPERATOR" for c in CODES}, **{…}}` — K3 역할↔프리셋 표가 이 모양이다.
        #   `literal_eval` 은 이것을 못 읽고, 못 읽은 것을 「비지 않았다」로 넘기면
        #   **정확히 이 표가 비는 날 게이트가 조용하다.** D-377 을 낳은 그 자리다.
        out = {}
        for k, v in zip(node.keys, node.values):
            rv = _resolve(v, env_names, known)
            if rv is _UNRESOLVED:
                return _UNRESOLVED
            if k is None:                       # `**expr`
                if not isinstance(rv, dict):
                    return _UNRESOLVED
                out.update(rv)
                continue
            rk = _resolve(k, env_names, known)
            if rk is _UNRESOLVED:
                return _UNRESOLVED
            try:
                out[rk] = rv
            except TypeError:
                return _UNRESOLVED
        return out
    if isinstance(node, ast.DictComp) and len(node.generators) == 1:
        gen = node.generators[0]
        if gen.ifs or not isinstance(gen.target, ast.Name):
            return _UNRESOLVED
        it = _resolve(gen.iter, env_names, known)
        if not isinstance(it, (list, tuple, set, dict)):
            return _UNRESOLVED
        var = gen.target.id
        out = {}
        for item in it:
            k = item if isinstance(node.key, ast.Name) and node.key.id == var                 else _resolve(node.key, env_names, known)
            v = item if isinstance(node.value, ast.Name) and node.value.id == var                 else _resolve(node.value, env_names, known)
            if k is _UNRESOLVED or v is _UNRESOLVED:
                return _UNRESOLVED
            out[k] = v
        return out
    if isinstance(node, ast.Call):
        fn = node.func
        # django-environ — `env("NAME", default=…)` · `env.bool/str/int/list(…)`
        # ★ 이 저장소의 설정은 **거의 전부 이 모양**이다. 이것을 못 접으면 ㉢ 의 모수가
        #   41 에서 4 로 주저앉는다 — 실제로 그렇게 나왔다.
        _env_obj = (isinstance(fn, ast.Name) and fn.id == "env") or (
            isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
            and fn.value.id == "env")
        if _env_obj:
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                env_names.add(node.args[0].value)
            for kw in node.keywords:
                if kw.arg == "default":
                    return _resolve(kw.value, env_names)
            if len(node.args) >= 2:
                return _resolve(node.args[1], env_names)
            # 기본값 없는 `env("X")` 는 값이 **반드시 와야 하는 것**이다 — 빈 설정이 아니다
            return _UNRESOLVED
        # os.getenv("NAME", 기본) · os.environ.get("NAME", 기본)
        if isinstance(fn, ast.Attribute) and fn.attr in ("getenv", "get"):
            src = fn.value
            is_env = (isinstance(src, ast.Name) and src.id == "os") or \
                     (isinstance(src, ast.Attribute) and src.attr == "environ")
            if is_env and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    env_names.add(first.value)
                if len(node.args) >= 2:
                    return _resolve(node.args[1], env_names)
                for kw in node.keywords:
                    if kw.arg == "default":
                        return _resolve(kw.value, env_names)
                return None
        # 문자열 다듬기 — `.lower()` · `.upper()` · `.strip()` 는 값을 바꾸지 않는다(비었나만 본다)
        if isinstance(fn, ast.Attribute) and fn.attr in ("lower", "upper", "strip"):
            base = _resolve(fn.value, env_names)
            if isinstance(base, str):
                return getattr(base, fn.attr)()
            return _UNRESOLVED
        if isinstance(fn, ast.Attribute) and fn.attr == "split":
            base = _resolve(fn.value, env_names)
            if isinstance(base, str):
                sep = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
                return [x for x in base.split(sep) if x] if base else []
            return _UNRESOLVED
        if isinstance(fn, ast.Name) and fn.id in ("int", "float", "bool", "str"):
            base = _resolve(node.args[0], env_names) if node.args else _UNRESOLVED
            if base is _UNRESOLVED:
                return _UNRESOLVED
            try:
                return {"int": int, "float": float, "bool": bool, "str": str}[fn.id](base)
            except (ValueError, TypeError):
                return _UNRESOLVED
        return _UNRESOLVED
    # `os.getenv("X","False").lower() == "true"` 같은 **불 분기**를 접는다
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left = _resolve(node.left, env_names)
        right = _resolve(node.comparators[0], env_names)
        if left is _UNRESOLVED or right is _UNRESOLVED:
            return _UNRESOLVED
        op = node.ops[0]
        try:
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.In):
                return left in right
            if isinstance(op, ast.NotIn):
                return left not in right
        except TypeError:
            return _UNRESOLVED
    return _UNRESOLVED


def _harvest(tree: ast.Module, vals: dict, envs: dict) -> None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if not (isinstance(tgt, ast.Name) and tgt.id.isupper()):
                continue
            names: set = set()
            vals[tgt.id] = _resolve(node.value, names, vals)
            envs[tgt.id] = names


def _settings_literals():
    """(설정 이름 -> 기본값, 설정 이름 -> 그 설정이 읽는 환경변수 이름들).

    ★ `settings.py` 만 읽으면 **표**를 놓친다. 이 저장소의 K3 역할↔프리셋 매핑은
      `config/k3_roles.py` 에 있고 settings 는 그것을 import 해 올린다. D-377 의 ㉢ 은
      「설정·표가 비어」이지 「settings.py 가 비어」가 아니다 — 그 표가 비면 코드는
      **늘 같은 가지로 간다.** 그래서 settings 가 `config.*` 에서 끌어오는 이름도 따라간다.
    """
    vals: dict = {}
    envs: dict = {}
    p = BACKEND / "config" / "settings.py"
    if not p.exists():
        return vals, envs
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return vals, envs

    for node in ast.walk(tree):
        if not (isinstance(node, ast.ImportFrom) and node.module
                and node.module.startswith("config.")):
            continue
        sub = BACKEND / Path(*node.module.split(".")).with_suffix(".py")
        if not sub.exists():
            continue
        try:
            _harvest(ast.parse(sub.read_text(encoding="utf-8", errors="replace")), vals, envs)
        except SyntaxError:
            print(f"[DORMANT] WARN 설정 모듈 파싱 실패: {_rel(sub)}", file=sys.stderr)

    _harvest(tree, vals, envs)     # settings.py 자신이 마지막 — 재대입이 이긴다
    return vals, envs


_ENV_LINE_RE = re.compile(r"^\s*-?\s*([A-Z][A-Z_0-9]{2,})\s*[:=]\s*(\S.*)$", re.M)


def _env_supplied() -> set[str]:
    """저장소가 **값을 주는** 설정 이름 — compose · .env 예시 · 진입 스크립트."""
    supplied: set[str] = set()
    cands = [
        ROOT / "docker-compose.yml", ROOT / "docker-compose.stg.yml",
        BACKEND / "entrypoint.sh", BACKEND / "run_be.sh",
        ROOT / "docs" / "agent" / "ENV_EXAMPLE_외부데이터API.txt",
    ]
    cands += sorted(BACKEND.glob(".env*"))
    for p in cands:
        if not p.exists() or not p.is_file():
            continue
        for m in _ENV_LINE_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
            if m.group(2).strip() not in ("", '""', "''"):
                supplied.add(m.group(1))
    return supplied


def audit_empty_config(trees):
    """모수 = 코드가 **분기·조회에 쓰는** 설정 이름 중 settings.py 가 정의한 것."""
    used: dict[str, set[str]] = defaultdict(set)
    for path, tree in trees.items():
        if _is_test(path) or path.name == "settings.py":
            continue
        rel = _rel(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                    and node.value.id == "settings" and node.attr.isupper():
                used[node.attr].add(rel)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "getattr" and len(node.args) >= 2:
                base, key = node.args[0], node.args[1]
                if isinstance(base, ast.Name) and base.id == "settings" \
                        and isinstance(key, ast.Constant) and isinstance(key.value, str) \
                        and key.value.isupper():
                    used[key.value].add(rel)

    literals, env_names = _settings_literals()
    supplied = _env_supplied()

    parametr, dormant, detail, unresolved = [], [], {}, []
    for name in sorted(used):
        if name not in literals:
            continue                       # settings.py 가 정의하지 않은 것은 모수 밖
        val = literals[name]
        if val is _UNRESOLVED:
            unresolved.append(name)
            # ★ 접지 못한 것은 **모수 밖으로 낸다.** 「비었는지 모른다」를 「비지 않았다」로
            #   읽으면 그것이 조용한 면제다(D-263 계열). 못 본 것은 못 봤다고 센다.
            continue
        parametr.append(name)
        # 값을 주는 자리는 **설정 이름**으로도, 그 설정이 읽는 **환경변수 이름**으로도 본다
        keys = {name} | env_names.get(name, set())
        has_supply = bool(keys & supplied)
        empty = (val in _EMPTY_LITERALS) or (
            isinstance(val, (list, dict, tuple, set)) and len(val) == 0)
        detail[name] = (val, sorted(used[name]), has_supply)
        if empty and not has_supply:
            dormant.append(name)
    return parametr, dormant, detail, sorted(unresolved)


# ===========================================================================
# 기준선 (래칫 · D-311)
# ===========================================================================
_BASELINE_HEADER = (
    "# 잠자는 기능 기준선 (D-377 · 착시 ⑨). 술어 접두: A=호출없음 B=주기없음 C=설정빔\n"
    "# ★ 이 목록은 **줄어들기만 한다.** 새로 자는 것이 생기면 게이트가 막는다.\n"
    "#   여기서 이름이 빠지는 것이 「켰다」는 뜻이다.\n"
)


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {ln.strip() for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


# ===========================================================================
# 자기시험 (D-277) — 심어 놓고 잡히는지 본다
# ===========================================================================
def self_test() -> int:
    import tempfile
    global BACKEND, ROOT
    bad = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "config").mkdir()
        # ══════════════════════════════════════════════════════════════════
        # ★ **출생 표본** (D-310) — 이 도구를 만들게 한, 그리고 이 도구가 **틀렸던**
        #   바로 그 사례들을 fixture 로 박는다. 합성 예제만 보는 자기시험은
        #   자기가 태어난 이유를 못 본다.
        #
        #   ① `BIRTH_ENV_SETTING` — ㉢ 이 **0건**을 냈던 자리.
        #      이 저장소의 설정은 거의 전부 `env("X", default="")` 이고, 1차판은
        #      `ast.literal_eval` 만 써서 **한 건도 접지 못했다.** 그 0을 실측으로
        #      읽었으면 착시를 잡으러 만든 도구가 착시를 하나 더 만들었다.
        #   ② `BIRTH_UNREGISTERED_BEAT` — beat 표에 줄이 있는데 그 태스크를
        #      **아무도 import 하지 않는** 자리. D-373 이 「켰다」고 보고한 감시·백업이
        #      실제로 이 상태였다 (`common/tasks.py` 가 없어서 등록되지 않았다).
        #      ㉡ 은 「beat 에 없다」만 보므로 이 갈래는 시험이 따로 본다
        #      (`backend/tests/test_dormant_wiring.py`) — 여기서는 **주석으로 꺼진
        #      항목**이 잡히는지를 본다. 꺼진 것이 틀린 것을 숨기던 그 자리다.
        # ══════════════════════════════════════════════════════════════════
        (d / "config" / "env_settings.py").write_text(
            'BIRTH_ENV_SETTING = env.str("BIRTH_ENV_SETTING", default="")\n'
            'BIRTH_ENV_FILLED = env.str("BIRTH_ENV_FILLED", default="ok")\n',
            encoding="utf-8")
        # ★ 「표」 갈래 — settings 가 `config.*` 에서 끌어오는 매핑. K3 역할↔프리셋이 이 모양이다
        (d / "config" / "tables.py").write_text(
            'EMPTY_TABLE = {}\nFULL_TABLE = {"a": 1}\n', encoding="utf-8")
        (d / "config" / "settings.py").write_text(
            'from config.tables import EMPTY_TABLE, FULL_TABLE\n'
            'from config.env_settings import BIRTH_ENV_SETTING, BIRTH_ENV_FILLED\n'
            'AWAKE_FLAG = "on"\nSLEEPY_FLAG = ""\nSLEEPY_LIST = []\n', encoding="utf-8")
        (d / "config" / "celery.py").write_text(
            'app.conf.beat_schedule = {\n'
            '  "live": {"task": "m.tasks.awake_task", "schedule": 60.0},\n'
            '  # "off": {"task": "m.tasks.commented_task", "schedule": 60.0},\n'
            '}\n', encoding="utf-8")
        (d / "m").mkdir()
        (d / "m" / "tasks.py").write_text(
            "from celery import shared_task\n"
            "@shared_task\ndef awake_task():\n    return 1\n"
            "@shared_task\ndef commented_task():\n    return 1\n"
            "@shared_task\ndef orphan_task():\n    return 1\n"
            "@shared_task\ndef enqueued_task():\n    return 1\n", encoding="utf-8")
        (d / "m" / "views.py").write_text(
            "from django.conf import settings\n"
            "from . import tasks\n"
            "def called_helper():\n    return 1\n"
            "def uncalled_helper():\n    return 2\n"
            "def entry():\n"
            "    tasks.enqueued_task.delay()\n"
            "    if settings.SLEEPY_FLAG:\n        return called_helper()\n"
            "    if settings.AWAKE_FLAG:\n        return 0\n"
            "    if settings.EMPTY_TABLE:\n        return 3\n"
            "    if settings.FULL_TABLE:\n        return 4\n"
            "    if settings.BIRTH_ENV_SETTING:\n        return 5\n"
            "    if settings.BIRTH_ENV_FILLED:\n        return 6\n"
            "    return settings.SLEEPY_LIST\n", encoding="utf-8")
        # ★ 출생 표본 ③ (D-393) — `@<시그널>.connect`. `backend/config/celery.py` 의
        #   셋이 이 모양이었고 ㉠ 이 그것을 「아무도 안 부른다」로 셌다.
        #   ★ `signal_not_wired` 를 **같은 파일에** 둔 이유: 배선된 것만 빠지고
        #     **평범한 미호출 함수는 그대로 잡히는지**를 본다. 파일째 면제하면 안 된다.
        (d / "m" / "signals.py").write_text(
            "from celery.signals import worker_process_init, task_prerun\n"
            "@worker_process_init.connect\n"
            "def signal_wired_bare():\n    return 1\n"
            "@task_prerun.connect(sender=None)\n"
            "def signal_wired_called():\n    return 2\n"
            "def signal_not_wired():\n    return 3\n", encoding="utf-8")
        (d / "m" / "tests").mkdir()
        (d / "m" / "tests" / "test_x.py").write_text(
            "from m.views import uncalled_helper\n"
            "def test_it():\n    assert uncalled_helper()\n", encoding="utf-8")

        ob, orr = BACKEND, ROOT
        BACKEND, ROOT = d, d
        try:
            trees = parse_all(iter_py(d))
            _, da, _ = audit_uncalled(trees)
            _, db, _ = audit_unscheduled(trees)
            _, dc, _, _ = audit_empty_config(trees)
        finally:
            BACKEND, ROOT = ob, orr

    an = {x.split("::")[-1] for x in da}
    bn = {x.split("::")[-1].lstrip("~") for x in db}
    # 양성 — 잡혀야 하는 것
    if "uncalled_helper" not in an:
        bad.append("㉠ 시험만 부르는 함수를 못 잡았다")
    if "orphan_task" not in bn:
        bad.append("㉡ beat 에도 없고 큐에도 없는 태스크를 못 잡았다")
    if "commented_task" not in bn:
        bad.append("㉡ **주석으로 꺼진** beat 항목을 못 잡았다")
    if "SLEEPY_FLAG" not in dc or "SLEEPY_LIST" not in dc:
        bad.append("㉢ 빈 설정으로 분기하는 자리를 못 잡았다")
    if "EMPTY_TABLE" not in dc:
        bad.append("㉢ settings 가 `config.*` 에서 끌어오는 **빈 표**를 못 잡았다")
    if "signal_not_wired" not in an:
        bad.append("★ 출생 표본 ③ 양성 — 배선 안 된 미호출 함수가 시그널 파일에 있다고 "
                   "함께 빠졌다. **파일째 면제**는 모수를 조용히 줄인다 (D-301)")
    if "BIRTH_ENV_SETTING" not in dc:
        bad.append("★ 출생 표본 — `env(…, default=\"\")` 를 접지 못해 ㉢ 이 다시 0건이다 "
                   "(1차판이 정확히 이랬다 · D-350)")
    # 음성 — 잡히면 안 되는 것
    if "called_helper" in an:
        bad.append("㉠ 운영이 부르는 함수를 잠들었다고 했다 (거짓 양성)")
    if "awake_task" in bn:
        bad.append("㉡ beat 에 등록된 태스크를 잠들었다고 했다 (거짓 양성)")
    if "enqueued_task" in bn:
        bad.append("㉡ 코드가 큐에 넣는 태스크를 잠들었다고 했다 (거짓 양성)")
    if "AWAKE_FLAG" in dc:
        bad.append("㉢ 값이 있는 설정을 비었다고 했다 (거짓 양성)")
    if "FULL_TABLE" in dc:
        bad.append("㉢ 값이 든 표를 비었다고 했다 (거짓 양성)")
    if "BIRTH_ENV_FILLED" in dc:
        bad.append("★ 출생 표본 음성 — 기본값이 든 `env(…)` 를 비었다고 했다 (거짓 양성)")
    if "signal_wired_bare" in an:
        bad.append("★ 출생 표본 ③ 음성 — `@sig.connect` 로 **배선된** 함수를 잠들었다고 했다. "
                   "D-388 이 celery 훅 셋을 ㉮ 로 낸 자리다 (D-350 · D-393)")
    if "signal_wired_called" in an:
        bad.append("★ 출생 표본 ③ 음성 — `@sig.connect(sender=…)` 호출 형태를 못 알아봤다")

    if bad:
        print("[DORMANT] 자기시험 실패 — **판정기를 먼저 의심한다** (D-350)")
        for b in bad:
            print(f"  · {b}")
        return 1
    print("[DORMANT] 자기시험 통과 — 양성 7갈래 · 음성 8갈래 (출생 표본 셋 포함)")
    return 0


def _app_of_label(label: str) -> str:
    path = label.split("::")[0]
    parts = path.split("/")
    return parts[1] if len(parts) > 1 and parts[0] == "backend" else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="잠자는 기능 전수 (D-377 착시 ⑨)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--predicate", choices=["a", "b", "c"])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--json", metavar="PATH")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:                       # 판정 전에 판정기부터 (D-277 · D-350)
        return 1

    trees = parse_all(iter_py(BACKEND))
    if not trees:
        print("[DORMANT] backend 에서 .py 를 한 건도 못 읽었다 — 열거기가 눈이 멀었다. "
              "0건을 통과로 읽지 않는다 (D-301)")
        return 1

    #: ★ 참조만 세는 나무 — `scripts/**` 는 우리 운영 도구다(앞단 설정 생성·백업·판정기).
    #:   모수에는 안 넣는다. 자세한 사유는 `audit_uncalled` 독스트링.
    tool_trees = parse_all(iter_py(ROOT / "scripts")) if (ROOT / "scripts").is_dir() else {}

    pa, da, ca = audit_uncalled(trees, tool_trees)
    pb, db, wb = audit_unscheduled(trees)
    pc, dc, wc, uc = audit_empty_config(trees)

    print(f"[DORMANT] 검사 {len(trees)}개 파일 · 세 술어를 **따로** 센다 "
          f"(합치지 않는다 — 고치는 방법이 다르다 · D-377)")
    print(f"[DORMANT] ㉠ 호출 없음  모수 {len(pa):5}  "
          f"(backend/** 함수 정의 · 사적 `_`·프레임워크 훅 {len(FRAMEWORK_HOOKS)}종·"
          f"진입 데코 {len(ENTRY_DECORATORS)}종 제외)  -> **{len(da)}건**")
    #: ★ 무엇을 부르는 쪽으로 셌는지 **매 실행에 적는다** — 이 줄이 없으면 「부르는 곳이
    #:   없다」가 「내가 본 곳에 없다」와 구별되지 않는다. 2026-09-05 에 실제로 갈렸다.
    print(f"[DORMANT]   부르는 쪽: backend/**(맨이름·속성·문자열) + "
          f"scripts/**({len(tool_trees)}개 · **가져온 이름만**) "
          f"— 도구가 감사 대상으로 *찾는* 이름은 부른 것이 아니다")
    print(f"[DORMANT] ㉡ 주기 없음  모수 {len(pb):5}  "
          f"(celery 태스크 전수 + 주석으로 꺼진 beat 항목)  -> **{len(db)}건**")
    print(f"[DORMANT] ㉢ 설정 빔    모수 {len(pc):5}  "
          f"(코드가 분기·조회에 쓰고 settings.py 가 정의한 이름 중 **기본값을 접을 수 있는 것**)"
          f"  -> **{len(dc)}건**")
    if uc:
        # ★ 접지 못한 것은 「비지 않았다」가 아니라 **「모른다」**다. 수를 말하지 않으면
        #   그것이 곧 0건의 착시다 (D-301).
        print(f"[DORMANT] ㉢ 접지 못한 설정 {len(uc)}건 — 모수 밖으로 냈다(비었는지 **모른다**): "
              + ", ".join(uc[:8]) + (" …" if len(uc) > 8 else ""))

    labeled = ([f"A {x}" for x in da] + [f"B {x}" for x in db] + [f"C {x}" for x in dc])
    forb = [x for x in labeled if _app_of_label(x.split(" ", 1)[1]) in FORBIDDEN_APPS]
    ours = [x for x in labeled if x not in forb]
    print(f"[DORMANT] 합계 {len(labeled)}건 — §0.4 금지구역 {len(forb)}건 "
          f"(delivery·orders·terminals · **잔여 분모에서 제외**) · **우리 관할 {len(ours)}건**")

    if args.census or args.list:
        want = args.predicate
        if want in (None, "a"):
            print("\n-- ㉠ 호출 없음 — **배선**이 없다 (고치는 법: 운영 경로에 잇는다)")
            for label in (pa if args.census else da):
                p, t = ca[label]
                mark = "SLEEP" if p == 0 else "     "
                note = f"  <- 시험만 {t}곳에서 부른다" if p == 0 and t else ""
                print(f"  {mark} {label:76} 운영 {p:3} · 시험 {t:3}{note}")
        if want in (None, "b"):
            print("\n-- ㉡ 주기 없음 — **등록**이 없다 (고치는 법: beat 에 올린다)")
            for label in (pb if args.census else db):
                mark = "SLEEP" if label in db else "     "
                print(f"  {mark} {label:76} {wb[label]}")
        if want in (None, "c"):
            print("\n-- ㉢ 설정 빔 — **데이터**가 없다 (고치는 법: 값을 채운다)")
            for name in (pc if args.census else dc):
                val, where, sup = wc[name]
                mark = "SLEEP" if name in dc else "     "
                print(f"  {mark} {name:44} = {val!r:16} 쓰는 곳 {len(where):2}  "
                      f"{'env/compose 가 값을 준다' if sup else '아무도 값을 안 준다'}")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "scope": "backend/**",
            "uncalled": {"denominator": len(pa), "count": len(da), "items": da},
            "unscheduled": {"denominator": len(pb), "count": len(db), "items": db,
                            "why": wb},
            "empty_config": {"denominator": len(pc), "count": len(dc), "items": dc},
            "forbidden_zone_excluded": len(forb),
            "ours": len(ours),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[DORMANT] JSON -> {_rel(out)}")

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(_BASELINE_HEADER + "\n".join(sorted(labeled)) + "\n",
                            encoding="utf-8")
        print(f"[DORMANT] 기준선 {len(labeled)}건 기록 — {_rel(BASELINE)}")
        return 0

    baseline = load_baseline()
    if not baseline:
        print("[DORMANT] 기준선 파일이 없다 — `--freeze` 로 오늘 자는 것을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return 1

    fresh = [x for x in labeled if x not in baseline]
    woke = sorted(baseline - set(labeled))
    if woke:
        # ★ **켠 것이 보여야 켜는 맛이 난다** (D-311). 실패가 아니고 로그다.
        #
        # ★★ 그러나 목록에서 빠지는 길은 **둘**이고, 둘은 전혀 다른 일이다 (D-393):
        #     ① 켜졌다        — 모수에는 그대로 있는데 **운영이 이제 그것을 부른다.** 진척이다
        #     ② 자고 있지 않았다 — **모수에서 빠졌다.** 판정기가 틀렸던 것이지 우리가 한 일이 없다
        #   합쳐서 「켜졌다」로 적으면 **판정기 정정이 진척으로 둔갑한다.** D-385 가 금지한
        #   그 모양이다 — 「켰다」는 「돌았다」의 증거가 있어야 하고, ②에는 그 증거가 없다.
        #   ★ 이 갈래를 만든 자리: celery 시그널 훅 셋. 그것은 **처음부터 켜져 있었다.**
        universe = {f"A {x}" for x in pa} | {f"B {x}" for x in pb} | {f"C {x}" for x in pc}
        turned_on = [w for w in woke if w in universe]
        never_asleep = [w for w in woke if w not in universe]
        print(f"[DORMANT] ★ 기준선에서 빠진 {len(woke)}건 — "
              f"**켜졌다 {len(turned_on)}건 · 자고 있지 않았다 {len(never_asleep)}건**")
        for w in turned_on:
            print(f"[DORMANT]   켬: {w}  (모수에 있고 운영이 부른다 — 진척)")
        for w in never_asleep:
            print(f"[DORMANT]   정정: {w}  (**모수에서 빠졌다** — 판정기가 틀렸던 것이다)")
        print("[DORMANT] `--freeze` 로 기준선을 줄인다")
    if fresh:
        print("[DORMANT] 위반 — **새로 만드는 것은 「켜진 상태로 태어나야 한다」** (D-377)")
        for f in fresh:
            print(f"  · {f}")
        print("  운영 경로에 잇거나(㉠) · beat 에 올리거나(㉡) · 값을 채운 뒤(㉢) 커밋한다")
        return 1
    print(f"[DORMANT] 통과 — 새로 잠든 것 0건 (기준선 {len(baseline)}건 안에 있다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
