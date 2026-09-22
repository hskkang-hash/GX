#!/usr/bin/env python
"""카메라 설치 주소 미입력 건수 — **막지 않는다. 다만 보이게 한다** (D-330 · D-301).

왜 exit 0 인가
--------------
`install_address` 는 **운영자가 채우는 값**이지 개발이 막는 값이 아니다.
비었다고 커밋을 세우면, 그 게이트는 개발자가 지울 수밖에 없는 게이트가 된다.

그런데 아무 말도 하지 않으면 **아무도 채우지 않는다.** 카메라 주소는
"언젠가 하겠지" 로 3년을 갈 수 있는 종류의 일이고, 그 사이 알림은 계속 좌표 1줄로 나간다.
그래서 판정하지 않고 **센다.** D-301 이 말한 대로 — **수가 보여야 채워진다.**

    python scripts/verify_camera_address.py            # 건수 출력 (exit 0)
    python scripts/verify_camera_address.py --list     # 미입력 카메라 이름까지
    python scripts/verify_camera_address.py --self-test

exit 코드
---------
    0  세었다 (미입력이 있어도 0 이다 — **이건 판정이 아니라 계측이다**)
    2  판정 불가 — Django 를 띄우지 못했다. **통과가 아니다** (verify_migrations 와 같은 규약)

★ 출생 표본 (D-310)
-------------------
이 도구를 만들게 한 사례는 **「좌표만 있는 알림 1줄」**이다 —
`address_source='unset'` 인 카메라에서 난 이벤트의 알림에는 도로명주소가 없고,
새벽 당직자는 좌표를 지도에 찍어 봐야 어디인지 안다. 자기시험 첫 갈래가 그 상태다.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

EXIT_OK, EXIT_CANNOT_JUDGE = 0, 2

#: ★ [턴 AD · 차선 Q · P-107 MEASURED 배선] 머리글의 **분모**. `classify()` 가 카메라
#: 한 대마다 가르는 갈래 이름 그대로다 — 카메라 **전수**(라이브 DB)는 `--self-test`
#: 호출(호스트 · Django 없음)에서는 잴 수 없어서, 분모를 손으로 안 넣고 이 판정기가
#: 항상 가르는 갈래 수를 센다(D-301). 라이브 카메라 전수는 `[CAM-ADDR]` 줄에 찍힌다.
CLASSIFY_BUCKETS = ("filled", "unset", "inconsistent")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def classify(rows) -> dict[str, list]:
    """(name, install_address, address_source) 목록을 세 갈래로 가른다.

    **순수 함수다** — 자기시험이 겨누는 과녁이 여기다 (D-277).
    「아직 안 적음」과 「적었다」를 가르는 것이 전부이고, 그 둘을 한 칸에 두지 않는
    것이 D-290 이다.
    """
    out = {"filled": [], "unset": [], "inconsistent": []}
    for name, address, source in rows:
        has = bool((address or "").strip())
        if has and source == "unset":
            # 주소는 있는데 출처가 미입력 — 한 사실이 두 칸에서 다르게 말한다.
            out["inconsistent"].append(name)
        elif has:
            out["filled"].append(name)
        else:
            out["unset"].append(name)
    return out


def _boot_django() -> str | None:
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        import django

        django.setup()
    except Exception as exc:  # noqa: BLE001 — 왜 못 띄웠는지 그대로 보고한다
        return f"{type(exc).__name__}: {exc}"
    return None


def self_test() -> int:
    """★ 출생 표본 — 좌표만 있는 알림 1줄(= 주소 미입력 카메라)."""
    cases = (
        # 출생 표본: 이 행이 있는 한 그 카메라의 알림에는 도로명주소가 없다
        ("★ 출생표본 주소 미입력 카메라를 센다",
         [("정문CCTV", "", "unset")], {"filled": 0, "unset": 1, "inconsistent": 0}),
        ("주소를 적은 카메라는 미입력이 아니다",
         [("정문CCTV", "서울시 …로 12", "manual")],
         {"filled": 1, "unset": 0, "inconsistent": 0}),
        ("공백만 있는 주소는 적은 것이 아니다",
         [("A", "   ", "unset")], {"filled": 0, "unset": 1, "inconsistent": 0}),
        ("주소는 있는데 출처가 unset 이면 어긋남으로 센다",
         [("A", "서울시 …로 12", "unset")],
         {"filled": 0, "unset": 0, "inconsistent": 1}),
        ("0건이면 세 갈래 모두 0 이다",
         [], {"filled": 0, "unset": 0, "inconsistent": 0}),
    )
    bad = 0
    for label, rows, want in cases:
        got = {k: len(v) for k, v in classify(rows).items()}
        ok = got == want
        print(f"  {'OK  ' if ok else 'FAIL'} {label}  → {got}")
        if not ok:
            bad += 1
    if bad:
        print(f"[CAM-ADDR] 자기시험 {bad}건 실패 — 이 계측기는 눈이 멀었다")
        return 1
    print(f"[CAM-ADDR] 자기시험 {len(cases)}건 통과 (출생 표본 포함)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:
        return 1

    boot_error = _boot_django()
    if boot_error:
        print(f"[CAM-ADDR] 판정 불가 — Django 를 띄우지 못했다: {boot_error}")
        print("[CAM-ADDR] ※ 이것은 **통과가 아니다** (exit 2). 컨테이너에서 돌린다: "
              "docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /repo gx-shell "
              "python scripts/verify_camera_address.py")
        return EXIT_CANNOT_JUDGE

    from django.apps import apps

    Model = apps.get_model("stream_monitors", "StreamMonitor")
    rows = list(Model._base_manager.values_list(
        "name", "install_address", "address_source"))
    groups = classify(rows)
    total = len(rows)

    print(f"[CAM-ADDR] 등록 카메라 **{total}대** (모수=StreamMonitor 전수 · "
          f"술어=install_address 가 비었는가)")
    if total == 0:
        print("[CAM-ADDR] 카메라가 0대다 — 정말 없는 것인지 못 읽은 것인지 "
              "이 계측기는 구별하지 못한다. **0% 를 100% 로 읽지 마라** (D-301)")
        return EXIT_OK
    print(f"[CAM-ADDR] 주소 입력 **{len(groups['filled'])}대** · "
          f"미입력 **{len(groups['unset'])}대** · 어긋남 {len(groups['inconsistent'])}대")
    print(f"[CAM-ADDR] 미입력 카메라의 알림은 종전대로 **좌표 1줄**로 나간다 — "
          f"발송이 지연되지는 않는다(D-330 · D-308).")
    if args.list:
        for name in groups["unset"]:
            print(f"    미입력  {name}")
        for name in groups["inconsistent"]:
            print(f"    어긋남  {name} — 주소는 있는데 address_source='unset' 이다")
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("카메라 설치 주소 미입력 건수 — 카메라마다 `filled`/`unset`/"
                  "`inconsistent` 셋 중 하나로 **분모 %d갈래**(`classify()` 의 갈래 · "
                  "지금 셌다). 라이브 카메라 전수는 gx-shell 안에서 재고 "
                  "`[CAM-ADDR]` 줄에 그대로 찍힌다" % len(CLASSIFY_BUCKETS)),
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        source="살아 있는 DB·앱 레지스트리 (django.setup 뒤 ORM) — 파일 사진이 아니다",
    )
    sys.exit(main())
