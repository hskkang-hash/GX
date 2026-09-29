#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-429 — `.env.gates` 를 이 프로세스에만 싣고 `${...}` 를 펼친 뒤 판정기를 그대로 부른다
(턴 AP · 차선 Q).

왜 있나
-------
`verify_route_alive.py` 는 제 안에 `load_local_env()`/`expand_env_refs()` 를 갖고
있어 `.env.gates` 의 `GX_ROUTE_PASSWORD=${GX_SEED_ROLE_PASSWORD}` 같은 간접 참조를
셸과 같은 뜻으로 펼친다(그 파일 401~461행 · D-386 의 사고 기록 — 펼치지 않은 채
넘기면 리터럴 `${GX_SEED_ROLE_PASSWORD}` 24자가 그대로 비밀번호로 나가 400 이
났었다). 그런데 그 로더는 **그 판정기 하나에만** 있다. 다른 판정기 다수는
`os.environ.get(...)` 을 직접 읽거나 아예 `.env.gates` 를 안 읽어서, `${...}` 간접
참조가 필요한 자리에서 같은 사고가 판정기마다 되풀이될 수 있다.

이 실행기를 판정기 앞에 세우면 **판정기를 한 줄도 안 고치고** 같은 펼치기 규약을
준다 — 펼치는 규칙은 `verify_route_alive.expand_env_refs` 하나뿐이고(두 벌로 안
둔다 · D-369), 이 파일은 그것을 호출 시점에 이 프로세스의 환경에 적용할 뿐이다.

이 실행기가 하는 일 — 그리고 하지 않는 일
-------------------------------------------
    한다   : `.env.gates` 를 읽어 **이 프로세스의 환경에만**(`os.environ`) 싣는다.
             값에 `${NAME}`/`$NAME` 참조가 있으면 `expand_env_refs` 로 셸과 같은
             뜻으로 펼친다. 다 펼친 뒤 인자로 받은 명령(예:
             `python scripts/verify_x.py --user gxprobe`)을 `subprocess.run` 으로
             **그대로** 부른다 — 자식은 이 프로세스의 환경을 물려받으므로 펼쳐진 값을
             그대로 읽는다(자식에게 값을 따로 실어 주지 않는다 · 한 곳에서만 편다).
    안 한다: **값을 어디에도 찍지 않는다** — 이 실행기 자신의 출력에는 이름·읽은
             파일 이름·실은 개수·(필요하면) sha256 앞 12자까지만 나온다(§ 규약
             「비밀 값 출력 금지」와 같은 선). 인자로 받은 `argv` 를 **고치지
             않는다** — 우리가 값을 그 안에 끼워 넣지 않는다(비밀은 환경으로만
             간다 · 규약 「비밀은 쿼리 문자열·argv 에 싣지 않는다」).

쓰는 법
-------
    python scripts/run_with_gates.py --self-test      # 순수 함수만 (파일·자식 없이)
    python scripts/run_with_gates.py -- python scripts/verify_route_alive.py --user gxprobe_e2e

종료 코드: 자식이 있었으면 **자식의 종료 코드를 그대로** 돌려준다. 펼친 뒤에도
`${` 가 남은 이름이 있으면(가리키는 이름이 그 파일에 없다) 자식을 부르기 **전에**
멈추고 1 을 낸다 — 안 펼쳐진 자리로 판정기를 부르면 2026-09-11 의 그 사고(펼치지
않은 눈)가 되풀이된다. 부를 명령이 없으면 1. `--self-test` 실패는 2.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_route_alive import expand_env_refs  # noqa: E402 — 펼치는 규칙은 한 곳(D-369)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent
EXIT_OK, EXIT_RED, EXIT_SELFTEST_FAIL = 0, 1, 2
TAG = "[RUN-GATES]"

#: [P-429] 명시적으로 이 파일만 싣는다 — `verify_route_alive.LOCAL_ENV_FILES` 처럼
#: `.env.local`/`.env` 까지 넓히지 않는다(이 실행기의 임무는 「지시서가 부른 그
#: 이름」 하나를 정직하게 펼치는 것이고, 넓히면 어느 파일에서 왔는지 사람이
#: 못 따라간다 — 필요하면 `--env-file` 로 부르는 쪽이 정한다).
DEFAULT_ENV_FILE = ".env.gates"


# ═══════════════════════════════════════════════════════════════════════════
# 순수 함수 — 파일 I/O 없이 문자열·dict 만 받는다(`--self-test` 가 이것만 잰다)
# ═══════════════════════════════════════════════════════════════════════════

def parse_env_text(text: str) -> dict[str, str]:
    """`KEY=VALUE` 줄을 판다. **앞줄이 뒷줄의 `${...}` 참조를 채운다**(셸 소싱과 같은 순서
    — `verify_route_alive.load_local_env` 의 그 규칙 그대로, 두 벌로 안 둔다).

    주석(`#` 로 시작하는 줄)과 빈 줄은 건너뛴다. **값 안의 `#` 는 안 자른다** — 비밀번호에
    `#` 이 들어갈 수 있고, 자르면 이번과 반대 방향의 같은 사고가 난다.
    """
    seen: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if not k:
            continue
        raw = expand_env_refs(v.strip().strip('"').strip("'"), seen)
        seen[k] = raw
    return seen


def unresolved_names(env: dict[str, str]) -> list[str]:
    """펼친 뒤에도 `${` 가 남은 **이름만** 돌려준다(값은 절대 안 돌려준다 — 부르는 쪽이
    이 결과를 그대로 찍어도 값이 새지 않는다).
    """
    return sorted(k for k, v in env.items() if isinstance(v, str) and "${" in v)


def fingerprint(value: str) -> str:
    """값 대신 적을 것 — sha256 앞 12자(§ 규약 「비밀 값 출력 금지」의 그 잣대)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════════════
# 파일 I/O — 위 순수 함수에 무엇을 먹일지만 정한다
# ═══════════════════════════════════════════════════════════════════════════

def load_into_this_process(env_file: str = DEFAULT_ENV_FILE, *, root: Path | None = None) -> dict[str, str]:
    """`.env.gates` 를 읽어 **이 프로세스의 환경에만** 싣는다.

    이미 이 프로세스 환경에 있는 이름은 파일보다 **이긴다**(사람이 실행 인자로
    `-e NAME=값` 을 준 실행에서는 그 값이 이긴다 — `verify_route_alive.load_local_env`
    와 같은 규칙). 자식 프로세스는 `subprocess.run` 이 기본으로 부모 환경을 물려주므로
    여기서 이 프로세스 환경에 실은 값이 그대로 넘어간다 — 자식에게 따로 실어 주지 않는다.

    ★ `root` 의 기본값을 **함수 몸통 안에서** 전역 `ROOT` 를 읽어 정한다(인자 목록의
      `root: Path = ROOT` 로 두지 않는다) — 그렇게 두면 파이썬이 그 값을 **정의 시점에**
      한 번 굳혀서, 시험이 `run_with_gates.ROOT` 를 갈아 끼워도 이 함수는 옛 값을 본다
      (몸통에서 다시 읽어야 시험이 실제로 격리된 자리를 겨눌 수 있다).
    """
    root = ROOT if root is None else root
    f = root / env_file
    if not f.is_file():
        return {}
    text = f.read_text(encoding="utf-8", errors="replace")
    parsed = parse_env_text(text)
    for k, v in parsed.items():
        if k not in os.environ:
            os.environ[k] = v
    return parsed


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        usage="%(prog)s [--self-test] [--env-file PATH] -- <판정기 명령...>")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--env-file", default=DEFAULT_ENV_FILE,
                    help="이 프로세스 환경에 실을 파일 (기본 .env.gates)")
    ns, rest = ap.parse_known_args(argv)

    if ns.self_test:
        return _self_test()

    #: argparse 가 `--` 를 자기 것으로 삼키지 않는 버전이 있어 손으로 한 번 더 벗긴다.
    if rest and rest[0] == "--":
        rest = rest[1:]
    if not rest:
        print("%s 부를 판정기 명령이 없다 — 예: run_with_gates.py -- python scripts/verify_x.py ..."
              % TAG)
        return EXIT_RED

    parsed = load_into_this_process(ns.env_file)
    #: 방금 실은 이름만 다시 읽어(부르는 쪽이 이미 갖고 있던 환경까지 훑지 않는다) 펼침이
    #: 끝난 값으로 되읽는다 — `os.environ` 쪽이 이겼을 수 있으므로 `parsed` 자체가 아니라
    #: 실제로 이 프로세스에 **실려 있는** 값을 본다.
    live = {k: os.environ.get(k, "") for k in parsed}
    bad = unresolved_names(live)
    if bad:
        print("%s 펼친 뒤에도 ${ 가 남은 이름 — 가리키는 이름이 %s 에 없다: %s"
              % (TAG, ns.env_file, ", ".join(bad)))
        print("%s 값은 적지 않는다(§ 규약) — 판정기를 부르지 않고 멈춘다" % TAG)
        return EXIT_RED

    print("%s %s 읽음 · 이름 %d개 실었다(값 0개 출력) · 판정기 인자 %d개로 부른다"
          % (TAG, ns.env_file, len(parsed), len(rest)))
    proc = subprocess.run(rest)
    return proc.returncode


# ═══════════════════════════════════════════════════════════════════════════
# --self-test — 파일도 자식 프로세스도 없이 순수 함수만 잰다
# ═══════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # ① 앞줄이 뒷줄의 ${...} 참조를 채운다(셸 소싱과 같은 순서)
    env = parse_env_text("A=1\nB=${A}-2\n")
    check("뒷줄이 앞줄 참조를 편다", env == {"A": "1", "B": "1-2"})

    # ② 주석·빈 줄은 건너뛴다
    env2 = parse_env_text("# 주석\n\nA=1\n")
    check("주석·빈 줄을 건너뛴다", env2 == {"A": "1"})

    # ③ 값 안의 # 은 안 자른다(비밀번호에 #이 들어갈 수 있다)
    env3 = parse_env_text("PW=abc#def\n")
    check("값 안의 # 은 안 자른다", env3 == {"PW": "abc#def"})

    # ④ 못 찾는 참조는 지어내지 않고 ${...} 그대로 남긴다
    env4 = parse_env_text("B=${GX_NOT_DEFINED_ANYWHERE_P429}\n")
    check("못 찾는 참조는 ${...} 그대로 남는다", env4["B"] == "${GX_NOT_DEFINED_ANYWHERE_P429}")

    # ⑤ ★ 자기시험 짝 — 펼친 뒤 ${ 가 남으면 unresolved_names 가 잡는다(=빨강 조건)
    check("펼친 뒤 ${ 가 남으면 unresolved_names 가 잡는다", unresolved_names(env4) == ["B"])
    check("다 펼쳐지면 unresolved_names 가 빈다", unresolved_names(env) == [])

    # ⑥ fingerprint 는 원문을 담지 않고 길이가 12 다
    fp = fingerprint("super-secret-value-xyz")
    check("fingerprint 길이 12", len(fp) == 12)
    check("fingerprint 는 원문을 안 담는다", "super-secret-value-xyz" not in fp)

    # ⑦ 빈 이름(`=값`처럼 키가 빈 줄)은 조용히 버린다(빈 이름으로 os.environ 을 어지르지 않는다)
    env5 = parse_env_text("=orphan\nC=3\n")
    check("빈 키 줄은 버린다", env5 == {"C": "3"})

    if failures:
        print("%s --self-test 실패 %d건: %s" % (TAG, len(failures), failures))
        return EXIT_SELFTEST_FAIL
    print("%s --self-test 통과 %d건" % (TAG, 8))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
