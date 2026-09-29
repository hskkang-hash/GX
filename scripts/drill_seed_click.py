#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-395 / P-416 — 「누른 뒤」 회색 중 **자료 상태**로 회색인 행을 위한 드릴 씨앗
한 줄 파이프 (턴 AO · 차선 Q). **여기서는 심지 않는다** — 이 파일은 준비이고,
실제 심기는 V 창의 몫이다(규약 §「절대 금지」— 라이브 서버 측정은 V 창).

무엇을 위한 도구인가
--------------------
`docs/agent/evidence/P-118/click_completes.json::observations` 의 회색 11행을
훑으면 사유가 둘로 갈린다:

    ① **자료 상태** — U1#11 하나. "이번 회에 미판정(verdict 없음) 사건이 없다
       (표본 25건 전부 판정됨) — 새 씨앗이 이번 회에 심기지 않았거나 전부 이미
       판정된 상태다." 이것은 **씨앗을 새로 심으면 없어지는** 회색이다.
    ② **도구가 누를 자리를 선언하지 않음** — 나머지 열(U1#4·U2#3·U3#14·U3#16·
       U4#9·U5#1·U5#4·U5#5·U5#10·U6#14). 이유는 각각: 화면에 서버 값이 드러나는
       칸이 없다 / 계약으로 잠긴 자리라 단추가 없다 / 여러 걸음이라 4.5초 클릭
       창에 안 들어온다 / 같은 상태를 두 번 흔들지 않으려고 일부러 안 누른다,
       등이다. **씨앗을 더 심어도 없어지지 않는다** — 자료가 아니라 절차·계약의
       문제다. 이 도구가 손대는 것은 ①뿐이다.

    참고: 옛 `BIRTH_SAMPLE`(죽은 표본 · `verify_click_completes.py`)의
    U2#3·U3#9 도 같은 "미판정" 부류였지만, 지금의 회색표(P-118)에서 U2#3 은
    "「되돌리기(사유 필수)」를 화면에서 못 찾았다"(②류)로 이미 갈라져 있다 — 그
    자리는 씨앗이 아니라 화면 단추의 문제다. 이 도구가 U1#11 하나에 집중하는
    까닭이다.

이 도구가 하는 일 — 그리고 하지 않는 일
---------------------------------------
    한다   : `scripts/capture_screens.py` 의 그 함수들을 **그대로** 부른다 —
             `seed_events()`(K1 `record_detection` 생성 경로 · 화면 캡처가 쓰는
             바로 그 함수)와 `_write_seed_file()`(`runs/<stamp>/seed.json` 을
             **같은 모양**으로 낸다). 두 벌을 두지 않는다(D-369) — 이 파일은
             부르기만 하고, 심는 규칙은 한 곳(`capture_screens.py`)에만 있다.
             기본 **4건**을 심는다(이번 절이 요청한 수).
    안 한다: 지우지 않는다(`clean_events()` 를 안 부른다) — 지우면 심은 씨앗을
             바로 못 쓴다. 정리는 늘 하던 대로 `capture_screens.py --clean-seeds`
             나 다음 회의 `probe_marks` 제외 규칙이 한다.

V 가 gx-shell 안에서 부르는 **한 줄**
--------------------------------------
    MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \\
      -w /app gx-shell python /repo/scripts/drill_seed_click.py \\
      --user gxseed_u1_operator --n 4

    ★ [P-426 · 턴 AP · 차선 Q] `--unjudged` 를 더하면 심은 뒤 DB 를 다시 읽어
      verdict 가 실제로 비었는지 확인하고, U1#11(`verify_click_completes.py`)이 그
      표본으로 설지를 **코드로**(HTTP 를 때리지 않고) 확인한다. **기본값은 그대로다**
      — 옵션이 없으면 심는 동작(`seed_events`)은 전과 똑같고 확인 단계만 빠진다:
          ... drill_seed_click.py --user gxseed_u1_operator --n 4 --unjudged

그 뒤에 이어지는 게이트(`verify_click_completes.py` · `verify_feature_reach` ·
`measure_onboarding_t.py`)는 **그대로** 부르면 된다 — `--seed-file` 을 안 줘도
`probe_marks.load_seed()` 가 `docs/agent/evidence/P-157/runs/` 아래 **가장 최신**
`seed.json` 을 스스로 찾는다(`latest_seed_file`). 그래서 "한 줄로 심고" 뒤에는
추가 배선이 필요 없다.

종결 — **한 프로세스, 한 종료 코드**
-------------------------------------
심기 → 명세 쓰기 → 요약 출력이 이 한 번의 호출 안에서 끝나고 그대로 끝난다(추가
손걸음이 없다). `exit 0` = 심었다 · `exit 1` = 심다가 실패(부분 심김일 수 있다 —
출력의 event_ids 를 본다) · `exit 2` = 판정 불가(Django 를 못 세웠다 · gx-shell
밖에서 불렀다 등 — `capture_screens.py` 와 같은 결의 종료 코드).

★ **자격증명을 여기 적지 않는다.** 이 도구는 로그인을 하지 않는다 — Django ORM
  으로 직접 심는다(`capture_screens.seed_events()` 와 같은 경로). 계정 이름은
  받되 비밀번호는 받지 않는다(필요 없다).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

TAG = "[DRILL]"

#: 이번 절이 요청한 수 — U1#11 이 보는 큐(전체 미판정 표본)에 **새 미판정 4건**을
#: 더하면 "표본 전부 판정됨"이 깨진다. 더 심어야 할 이유가 생기면 `--n` 으로 덮는다.
DEFAULT_N = 4


def plant(username: str, n: int, address: str | None):
    """실제로 심는다. **규칙은 `capture_screens.py` 안에만 있다** — 여기서 되풀이하지 않는다."""
    import capture_screens as cs

    cs._django()
    first = cs.seed_events(username, n=n, address=address)
    seed_path = cs._write_seed_file()
    return cs, first, seed_path


#: [P-426 · 턴 AP · 차선 Q] `--unjudged` 확인이 쓰는 잣대 — **`verify_click_completes.py`
#: 의 그 줄과 같은 잣대**(`unv = [... if not e.get("verdict")]`, 이 파일 근처 3076행)를
#: ORM 으로 재현한다. 두 벌을 따로 두면 갈릴 수 있어 여기 주석에 그 출처를 못박는다 —
#: `verify_click_completes.py` 가 바뀌면 이 함수도 같이 봐야 한다.
def verify_unjudged(event_ids) -> dict:
    """심은 사건을 DB 에서 다시 읽어 **정말 미판정(verdict 없음)인지** 확인한다.

    U1#11 이 서려면(`verify_click_completes.py`) `GET /api/dsm/events?limit=50` 로 다시
    읽었을 때 이 표본 중 최소 하나가 `verdict` 가 비어 있어야 한다. 여기서는 HTTP 를
    때리지 않고 **같은 잣대**(`verdict` 가 falsy)를 ORM 으로 그대로 적용해, 이번에 심은
    것이 그 표본이 될지를 **코드로** 확인한다 — 실제로 누르지는 않는다(V 몫).

    `record_detection`(K1)은 `verdict` 를 받지 않으므로 심은 직후에는 항상 비어
    있어야 정상이다. 이 함수는 그 전제가 **실제로** 지켜졌는지 심은 뒤 되읽어 검사한다
    (다른 프로세스가 그사이 먼저 판정했거나, K1 이 바뀌어 기본값이 달라지는 경우를 잡는다).
    """
    from django.apps import apps as django_apps

    DE = django_apps.get_model("stream_monitors", "DetectionEvent")
    ids = list(event_ids)
    rows = list(DE._base_manager.filter(pk__in=ids).values("pk", "verdict"))
    found_ids = {r["pk"] for r in rows}
    judged = sorted(r["pk"] for r in rows if r["verdict"])
    unjudged = sorted(r["pk"] for r in rows if not r["verdict"])
    missing = sorted(set(ids) - found_ids)
    return {"planted": len(ids), "found": len(rows), "judged": judged,
           "unjudged": unjudged, "missing": missing}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="U1#11 류(자료 상태) 회색을 없애는 드릴 씨앗 — 한 줄로 심고 끝에 종결. "
                    "실제 심기는 gx-shell 안에서만 뜻이 있다(V 몫).")
    ap.add_argument("--user", default="gxseed_u1_operator",
                    help="심을 계정 — U1#11 은 U1(gxseed_u1_operator)이 보는 큐다. "
                         "다른 테넌트가 필요하면 capture_screens.PERSONAS 의 다른 이름을 준다")
    ap.add_argument("--n", type=int, default=DEFAULT_N,
                    help="심을 사건 수 (기본 %d — 이번 절이 요청한 수)" % DEFAULT_N)
    ap.add_argument("--address", default=None,
                    help="씨앗 카메라 주소. 기본은 실재 카메라 주소 재사용"
                         "(capture_screens._borrow_real_address 와 같다)")
    ap.add_argument("--unjudged", action="store_true",
                    help="[P-426] 심은 뒤 DB 를 다시 읽어 verdict 가 실제로 비어 있는지 "
                         "확인한다 — U1#11(verify_click_completes.py)이 그 씨앗으로 서는지를 "
                         "코드로 확인한다. **기본값 불변**: 이 옵션이 없으면 심는 동작은 "
                         "전과 같고(seed_events 는 애초에 verdict 를 안 준다), 확인 단계만 "
                         "빠진다")
    args = ap.parse_args(argv)

    if args.n <= 0:
        print("%s --n 은 1 이상이어야 한다(받은 값: %s)" % (TAG, args.n))
        return EXIT_UNDECIDABLE

    try:
        import capture_screens  # noqa: F401  (임포트만 확인 — 실제 사용은 plant() 안에서)
    except Exception as exc:                            # noqa: BLE001
        print("%s capture_screens 를 못 들였다(scripts/ 옆에 있는가?) — %s: %s"
              % (TAG, type(exc).__name__, exc))
        return EXIT_UNDECIDABLE

    try:
        cs, first, seed_path = plant(args.user, args.n, args.address)
    except ModuleNotFoundError as exc:
        print("%s Django 를 못 세웠다 — gx-shell **안**에서 불렀는가? %s: %s"
              % (TAG, type(exc).__name__, exc))
        return EXIT_UNDECIDABLE
    except Exception as exc:                            # noqa: BLE001
        print("%s 못 심었다 — %s: %s" % (TAG, type(exc).__name__, exc))
        return EXIT_FAIL

    if seed_path is None:
        print("%s 심었다는 답이 왔는데 seed.json 을 못 썼다 — SEED_SPEC 이 비었다"
              " (event_ids=%s)" % (TAG, getattr(cs, "SEEDED_EVENT_IDS", [])))
        return EXIT_FAIL

    print("%s 심음 %d건 · 첫 사건 %s · run=%s" % (TAG, len(cs.SEEDED_EVENT_IDS), first, cs.RUN_STAMP))
    print("%s 명세 → %s" % (TAG, seed_path))

    if args.unjudged:
        check = verify_unjudged(cs.SEEDED_EVENT_IDS)
        if check["judged"] or check["missing"]:
            print("%s --unjudged 확인 실패 — 판정된 채로 들어간 사건 %s · 못 찾은 사건 %s"
                  % (TAG, check["judged"], check["missing"]))
            return EXIT_FAIL
        print("%s --unjudged 확인 — 심은 %d건 중 %d건이 미판정(verdict 없음)이다. "
              "verify_click_completes.py 의 `unv = [... if not e.get('verdict')]` 와 "
              "같은 잣대로 쟀다 — U1#11 이 이 씨앗으로 설 표본이 있다"
              % (TAG, check["found"], len(check["unjudged"])))

    print("%s 종결 — 추가 손걸음 없음. 뒤 게이트는 `--seed-file` 없이도 이 파일을 "
          "가장 최신으로 찾는다(probe_marks.latest_seed_file)" % TAG)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
