"""대장 병합 — **대장은 줄지 않는다** (P-154 · 턴 S).

생성기가 사람이 쌓은 대장을 덮어쓴 일이 턴 R 에 넷 났다:

    D-347/screens/INDEX.yaml        32항목 → 2항목
    D-347/screens/run_log.json      1,513B → 232B (32단계 → 2단계)
    D-386/screen_routes.json        27자리 → 2자리
    (턴 Q 의 인구조사도 같은 모양이었다)

셋째 것은 `verify_feature_reach` · `verify_envelope` · `verify_route_alive`
**셋의 입력**이라, 그 상태로 잰 수가 보고에 실릴 뻔했다 — 상용 63.2 · 영역 ① 3/39.
되살린 뒤의 참값은 65.3 · 7/39 였다. **하락은 처음부터 없었다.**

★ 이 모듈이 하는 일은 하나다: **옛 것과 새 것을 합치되, 줄면 멈춘다.**

⚠ 되살리다가 같은 죄를 짓는 자리가 있다 — 턴 R 에 조율자가 `viewers` 를
  **라우트 이름으로** 묶어 32 → 28 로 만들었다. 같은 화면을 다른 역할 계정이 본
  기록 4건이 그렇게 사라졌다. 열쇠가 좁으면 병합은 곧 삭제다. 그래서 여기의
  기본 열쇠는 **기록 전체**다 — 한 칸이라도 다르면 다른 기록으로 센다.

쓰는 쪽:
    · `scripts/capture_screens.py` — 대장 넷을 쓰기 전에 (차선 Q · P-154)
    · `scripts/verify_ledger_monotonic.py` — HEAD 와 대조하는 게이트 (차선 F · P-154)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

#: 집안 규약 — 윈도 콘솔의 기본은 cp949 이고 `—`·`★` 를 못 찍는다. 그대로 두면
#: 판정이 **자기 출력에서 죽고**, 죽은 판정은 빨강과 구별되지 않는다.
#: (`verify_screens.py:60` · `verify_dead_fields.py:55` 와 같은 줄이다.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class LedgerShrank(RuntimeError):
    """대장이 줄었다. **예외로 멈춘다** — 줄어든 대장은 조용히 지나가면 안 된다."""


def record_key(record) -> str:
    """한 기록의 열쇠 — **기록 전체**다.

    ★ 라우트·파일명 같은 한 칸을 열쇠로 쓰면 「같은 화면을 다른 사람이 본 기록」이
      한 줄로 접힌다. 접힌 줄은 사라진 줄과 구별되지 않는다(D-301 의 대장판).
      느리지만 옳다 — 대장은 수만 줄이지 수백만 줄이 아니다.
    """
    return json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)


def merge_records(head, fresh, *, key=record_key) -> list:
    """옛 기록 + 새 기록. **순서는 옛 것이 먼저**이고, 같은 열쇠는 새 것이 이긴다.

    Args:
        head:  이미 대장에 있던 기록들(HEAD 또는 디스크의 것).
        fresh: 이번 실행이 낸 기록들.
        key:   열쇠 함수. 기본은 `record_key`(기록 전체) — **좁히지 말 것.**

    Returns:
        합친 목록. 길이는 `len(head)` 보다 **작아질 수 없다.**
    """
    out, seen = [], {}
    for r in head:
        k = key(r)
        if k in seen:                                  # 옛 대장 안의 중복은 그대로 둔다
            out.append(r)
            continue
        seen[k] = len(out)
        out.append(r)
    for r in fresh:
        k = key(r)
        if k in seen:
            out[seen[k]] = r                           # 같은 기록의 새 판
        else:
            seen[k] = len(out)
            out.append(r)
    return out


def head_bytes(repo_relative: str, *, root: Path | None = None) -> bytes | None:
    """`git show HEAD:<경로>` — 없으면 `None`. **없는 것은 없는 것이다**(지어내지 않는다).

    생성기가 이미 덮어쓴 뒤에도 옛 대장을 되찾을 수 있는 유일한 자리다.
    """
    base = root or Path(__file__).resolve().parents[1]
    try:
        done = subprocess.run(["git", "show", "HEAD:" + repo_relative],
                              cwd=str(base), capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def assert_not_shrunk(label: str, before: int, after: int) -> None:
    """줄면 **멈춘다.** 경고가 아니라 예외다 (P-154).

    ★ 경고로 두면 콘솔 한 줄이 되고, 콘솔 한 줄은 다음 사람이 안 읽는다.
      턴 R 에 이것이 경고였다면 30장이 출처를 잃은 채 커밋됐을 것이다.
    """
    if after < before:
        raise LedgerShrank(
            "%s 이 줄었다 — %d항목 → %d항목. **대장은 줄지 않는다**(P-154). "
            "생성기가 이번 실행분만 남기고 덮어썼는지 보라: "
            "`git show HEAD:<파일> | wc -c` 와 지금 파일을 견준다." % (label, before, after))


def self_test() -> int:
    """★ 출생 표본 — 이 판정이 **실제로 무엇을 잡는지** 여기서 보인다."""
    bad = []

    # ① 같은 화면을 다른 역할이 본 기록 둘은 **한 줄로 접히지 않는다** (턴 R 의 그 4건)
    same_route = [
        {"file": "a.png", "route": "/dsm/events", "viewed_by": "fire_admin"},
        {"file": "b.png", "route": "/dsm/events", "viewed_by": "view_only"},
    ]
    if len(merge_records(same_route, [])) != 2:
        bad.append("같은 라우트를 다른 사람이 본 기록 둘이 접혔다 — 병합이 곧 삭제다")

    # ② 라우트로 묶으면 **접힌다** — 이것이 하면 안 되는 모양이다(반례로 박아 둔다).
    #
    #   ★ 첫 판의 표본은 틀렸었다: 둘을 **둘 다 head 로** 주고 접히기를 기대했다.
    #     안 접힌다 — 옛 대장 안의 중복은 열쇠가 좁아도 그대로 둔다(그것이 「줄지 않는다」다).
    #     **삭제가 일어나는 자리는 head 와 fresh 가 만나는 이음매**이고, 턴 R 에 viewers
    #     4건이 사라진 자리도 정확히 거기였다 — 옛 기록 위에 새 기록이 같은 라우트로
    #     덮어썼다. 표본을 그 모양으로 고쳤다. **표본이 틀리면 게이트는 아무것도 못 잡는다.**
    folded = merge_records([same_route[0]], [same_route[1]], key=lambda r: r["route"])
    if len(folded) != 1:
        bad.append("반례가 성립하지 않는다 — 좁은 열쇠가 이음매에서 접지 않으면 이 표본은 뜻이 없다")
    if len(merge_records([same_route[0]], [same_route[1]])) != 2:
        bad.append("기록 전체를 열쇠로 써도 접혔다 — 이 모듈의 심장이 안 뛴다")

    # ③ 새 기록은 뒤에 붙고, 옛 것은 **그대로 남는다**
    merged = merge_records(same_route, [{"file": "c.png", "route": "/dsm/live"}])
    if len(merged) != 3 or merged[0]["file"] != "a.png":
        bad.append("새 것을 더하면서 옛 것의 자리가 바뀌었다")

    # ④ 줄면 **예외**다 — 경고가 아니다
    try:
        assert_not_shrunk("표본", 32, 2)
        bad.append("32 → 2 인데 멈추지 않았다 — 이 판정의 심장이 안 뛴다")
    except LedgerShrank:
        pass

    for b in bad:
        print("[LEDGER] 자기시험 실패 — " + b)
    print("[LEDGER] 자기시험 %s (표본 4)" % ("실패" if bad else "통과"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(self_test())
