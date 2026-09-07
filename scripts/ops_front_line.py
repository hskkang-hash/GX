#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-13 — 앞단 관문을 **만들고 · 대조하고 · 두드린다** (D-361).

    **단일 방어선은 방어선이 아니다.**
    미들웨어는 코드이고, 코드는 리팩터링 중에 순서가 바뀐다 — 앞단은 그때 남는다.

이 도구가 하는 일 셋. 셋 다 **다른 것을 묻는다**:

    --render   `common/access_gate.py` 의 목록에서 nginx 위치 블록을 만든다
    --check    디스크의 설정이 그 목록과 **아직 같은가** (드리프트 · 손댐)
    --probe    떠 있는 앞단이 **실제로 401 을 내는가** (D-210 — 호출로 확인한다)

★ 앞단의 401 과 미들웨어의 401 을 **어떻게 가르는가**
-----------------------------------------------------
둘 다 401 이라 상태 코드만으로는 못 가른다. 앞단이 뒷단을 그냥 통과시키고 있어도
미들웨어가 401 을 내면 「앞단이 막았다」로 읽힌다 — **거짓 초록의 전형**이다.
그래서 앞단의 거절 본문에는 `(front line)` 이 박혀 있고, `--probe` 는 그 낱말을 본다.
낱말이 없으면 그 401 은 **뒷단의 답**이고, 이 판정기는 그것을 통과로 적지 않는다.

    python scripts/ops_front_line.py --self-test
    python scripts/ops_front_line.py --render
    python scripts/ops_front_line.py --check nginx/generated/gx-gate.conf
    python scripts/ops_front_line.py --probe http://gx-nginx-e:8500

종료 코드: **0 쟀고 통과 · 1 쟀고 실패 · 2 못 쟀다(회색)**. 회색은 초록이 아니다.

★ **5xx 는 여기서 세지 않는다** (P-84 · 2026-09-06 · 턴 I)
------------------------------------------------------
가용성(5xx) 판정은 **두 줄**이고 그 두 줄은 한 자리에서만 난다:

    ① 개발 기계 수      참고 · runserver N대 · loadavg 를 같은 줄에 적는다
    ② 운영형 인스턴스    `gx-gunicorn-e` / `gx-nginx-e`(8500) — **SLA 정본은 이것뿐**

    python scripts/verify_front_line_502.py --sla-5xx

②를 못 재면 「SLA 미측정 · 사유: 운영형 인스턴스 없음」(회색)이다 — ①의 수를 SLA
칸에 옮겨 적는 길은 없다. 여기(이 파일)에 5xx 수를 따로 적으면 **표가 둘이 되고**,
표가 둘이면 다음 사람이 어느 표를 봐야 하는지 모른다 (D-212).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: 컨테이너는 `/app`(=backend) 으로, 호스트는 `<repo>/backend` 로 붙는다.
#: 한 자리로 못 박으면 한쪽에서 「모듈이 없다」로 죽는다 (D-369 계열).
for _cand in (ROOT / "backend", Path("/app"), ROOT / "repo" / "backend", Path("/repo/backend")):
    if (_cand / "common" / "access_gate.py").is_file():
        sys.path.insert(0, str(_cand))
        break

#: ★ `access_gate` 는 `core.api.v1.auth` 를 타고 Django 모델을 건드린다 — 앱 등록이
#:   끝나기 전에는 `AppRegistryNotReady` 다. 그래서 **여기서 세운다.** DB 에 붙지는
#:   않는다(설정만 읽는다). 이 도구는 컨테이너 안에서 도는 도구다.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
try:
    import django                                              # noqa: E402

    django.setup()
except Exception as _exc:                                      # noqa: BLE001
    print(f"[FRONT-LINE] **회색(exit 2)** — Django 를 세우지 못했다: "
          f"{type(_exc).__name__}: {_exc}. 이 도구는 백엔드 컨테이너 안에서 돈다")
    sys.exit(2)

from common.access_gate import AUTHN_REQUIRED_PATHS, INBOUND_KEY_ALLOWED  # noqa: E402
from common.front_line import (  # noqa: E402
    gated_paths,
    key_allowed,
    parse_gated_paths,
    parse_key_allowed,
    render_locations,
)

EXIT_OK, EXIT_FAIL, EXIT_GRAY = 0, 1, 2

#: 앞단이 낸 거절임을 알리는 표식. 이것이 없으면 그 401 은 뒷단의 답이다.
FRONT_MARK = "(front line)"

#: **들어오는(inbound) 키** 의 헤더와, 앞단이 거절해야 할 가짜 값.
#: ★ 방향을 이름에 박는다 (D-337 · 동음이의 게이트가 이 자리를 잡았다):
#:   **나가는 키**(우리가 남을 부를 때 우리가 내미는 것)와
#:   **들어오는 키**(남이 우리를 부를 때 내미는 것)는 **다른 것**인데 둘 다 "API Key" 라 불린다.
#:   2026-09-07 에 그 둘을 같은 것으로 읽어 잔여 절을 10 으로 셌고 실제로는 12 였다.
#:   여기서 재는 것은 **들어오는 쪽**이다 — 남이 가짜 키를 들고 왔을 때 앞단이 끊는가.
INBOUND_API_KEY_HEADER = "X-API-Key"
BOGUS_INBOUND_KEY = "not-a-real-key-000000"

#: 앞단이 **막지 않는** 자리 — 음성 대조. 전부 막는 앞단은 방어선이 아니라 벽이고,
#: 벽은 첫날 치워진다. `/_front/health` 는 뒷단을 타지 않고 200 이어야 한다.
NEGATIVE_CONTROL = "/_front/health"

DEFAULT_OUT = ROOT / "nginx" / "generated" / "gx-gate.conf"


def _front_conf() -> Path | None:
    """앞단 설정이 **보이는 자리**. 없으면 None — 없는 것을 있다고 적지 않는다."""
    for base in (ROOT / "nginx", Path("/etc/nginx/gx"), Path("/repo/nginx"),
                 Path("/nginx")):
        cand = base / "gx-front.conf"
        if cand.is_file():
            return cand
    return None

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성 대조가 있다** (D-277 · D-289)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad: list[str] = []
    conf = render_locations()

    # ① 낸 것을 **되읽어** 선언과 견준다. 통째로 빠뜨려도 초록이 나면 안 된다.
    if parse_gated_paths(conf) != set(gated_paths()):
        bad.append("만든 설정을 되읽으니 익명 거절 경로가 선언과 다르다: "
                   f"{sorted(set(gated_paths()) - parse_gated_paths(conf))}")
    if parse_key_allowed(conf) != set(key_allowed()):
        bad.append("만든 설정을 되읽으니 키 허용 목록이 선언과 다르다")

    # ② 목록이 **비면** 그것은 「막았다」가 아니라 「아무것도 안 본다」이다 (D-301)
    if not AUTHN_REQUIRED_PATHS or not INBOUND_KEY_ALLOWED:
        bad.append("선언 목록이 비었다 — 앞단이 아무것도 안 본다")
    if len(parse_gated_paths(conf)) < 2 * len(AUTHN_REQUIRED_PATHS):
        bad.append("슬래시 변형이 빠졌다 — `/p` 를 막고 `/p/` 를 열면 막은 것이 아니다")

    # ③ 음성 대조 — **막지 않은 자리**가 실제로 안 막혀야 한다.
    #    이것이 없으면 「전부 401」인 설정도 위의 검사를 통과한다.
    ungated = "/api/flight-log/flight-log"
    if ungated in parse_gated_paths(conf):
        bad.append(f"{ungated} 까지 앞단이 막는다 — 그건 방어선이 아니라 벽이다")

    # ④ 거절은 **HTTP 상태로** 말하고 본문은 짧다 (D-349 · 반출 0)
    for line in conf.splitlines():
        if "return 401" in line:
            body = line.split("return 401", 1)[1]
            if len(body.encode("utf-8")) >= 512:
                bad.append("거절 본문이 512바이트를 넘는다")
            if "status_code" in body:
                bad.append("거절이 본문에 상태를 담았다 — 봉투와 내용이 갈린다(D-349)")

    # ⑤ 뒷단이 **gunicorn 이라고 적혀 있는가** — 앞단만 세우고 runserver 를 물리면
    #    `Server:` 가 nginx 라 합격선 모드로 갈리지만 잰 것은 개발 서버다.
    #    ⚠ 이 검사는 **설정 파일이 보이는 자리에서만** 돈다. `gx-shell` 은 저장소의
    #      `nginx/` 를 마운트하지 않으므로(backend·scripts·docs 만 붙는다) 거기서는
    #      돌지 않는다 — 그 사실을 **적는다.** 안 적으면 「돌았는데 통과」로 읽힌다(D-301).
    front = _front_conf()
    if front is not None:
        text = front.read_text(encoding="utf-8")
        if "gx-gunicorn" not in text:
            bad.append("gx-front.conf 의 upstream 이 gunicorn 을 가리키지 않는다")
        if "include /etc/nginx/gx/generated/gx-gate.conf;" not in text:
            bad.append("gx-front.conf 가 관문 생성물을 include 하지 않는다 — "
                       "앞단이 서도 관문은 없다")
        front_note = f"앞단 설정 {front} 대조함"
    else:
        front_note = ("앞단 설정이 **이 자리에서 안 보인다**(nginx/ 미마운트) — "
                      "그 자리는 `--probe` 가 실측한다")

    # ⑥ 앞단의 거절에 **표식**이 있는가 — 없으면 뒷단의 401 과 못 가른다
    if FRONT_MARK not in conf:
        bad.append(f"앞단 거절에 {FRONT_MARK} 표식이 없다 — 뒷단의 401 과 구별할 수 없고, "
                   f"구별 못 하는 증거는 증거가 아니다")

    if bad:
        print("[FRONT-LINE] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"[FRONT-LINE] 자기시험 통과 — 되읽기 2 · 빈목록 2 · 음성대조 1 · "
          f"본문규약 2 · 표식 1 "
          f"(익명거절 {len(gated_paths())}자리 · 키허용 {len(key_allowed())}자리) · "
          f"{front_note}")
    return EXIT_OK


def do_render(out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_locations(), encoding="utf-8")
    print(f"[FRONT-LINE] 만들었다 → {out}")
    print(f"[FRONT-LINE]   익명 401 {len(gated_paths())}자리 · 키 허용 {len(key_allowed())}자리")
    return EXIT_OK


def do_check(path: Path) -> int:
    if not path.is_file():
        print(f"[FRONT-LINE] **회색** — 대조할 파일이 없다: {path} (D-301)")
        return EXIT_GRAY
    got = path.read_text(encoding="utf-8")
    want = render_locations()
    if got == want:
        print(f"[FRONT-LINE] 통과 — {path} 가 선언과 같다")
        return EXIT_OK
    drift_paths = parse_gated_paths(got) ^ set(gated_paths())
    drift_keys = parse_key_allowed(got) ^ set(key_allowed())
    print(f"[FRONT-LINE] **실패** — {path} 가 선언과 갈렸다. "
          f"경로 차 {sorted(drift_paths)} · 키 차 {sorted(drift_keys)}")
    print("[FRONT-LINE]   `--render` 로 다시 만들어라. 손으로 고친 앞단은 낡는다")
    return EXIT_FAIL


# ═══════════════════════════════════════════════════════════════════════════
# 두드리기 — **호출로 확인한다** (D-210)
# ═══════════════════════════════════════════════════════════════════════════
def _hit(url: str, headers: dict | None = None) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read(600).decode("utf-8", "replace"), resp.headers.get("Server")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(600).decode("utf-8", "replace"), exc.headers.get("Server")
    except Exception as exc:                                  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}", None


def do_probe(base: str) -> int:
    base = base.rstrip("/")
    rows: list[tuple[str, str, str]] = []

    status, body, server = _hit(base + NEGATIVE_CONTROL)
    if status is None:
        print(f"[FRONT-LINE] **회색(exit 2)** — 앞단에 닿지 못했다: {base} · {body}")
        return EXIT_GRAY
    rows.append(("음성 대조 " + NEGATIVE_CONTROL,
                 "pass" if status == 200 else "fail",
                 f"{status} — 앞단이 전부를 막지는 않는다 (Server: {server})"))

    # ① 익명 → 앞단이 401 을 낸다. **표식으로 앞단의 답임을 확인한다**
    for path in gated_paths():
        status, body, _ = _hit(base + path)
        front = FRONT_MARK in (body or "")
        rows.append((f"익명 {path}",
                     "pass" if (status == 401 and front) else "fail",
                     f"{status} · 앞단표식 {'있음' if front else '**없음**'}"
                     + ("" if front else " — 이 401 은 뒷단이 냈다. 앞단은 통과시켰다")))

    # ② 키 기본값 거절 — 선언 밖에서는 앞단이 끊는다
    for path in ("/api/terminals/terminals", "/api/dsm/events/1/clip/stream"):
        status, body, _ = _hit(base + path, {INBOUND_API_KEY_HEADER: BOGUS_INBOUND_KEY})
        front = FRONT_MARK in (body or "")
        rows.append((f"키 {path}",
                     "pass" if (status == 401 and front) else "fail",
                     f"{status} · 앞단표식 {'있음' if front else '**없음**'}"))

    # ③ 양성 대조 — 선언한 자리에서는 앞단이 키를 **막지 않는다**.
    #    전부 거절이면 그건 「좁혔다」가 아니라 「다 막았다」이다.
    for method, path in key_allowed():
        if method != "GET":
            continue
        status, body, _ = _hit(base + path, {INBOUND_API_KEY_HEADER: BOGUS_INBOUND_KEY})
        blocked_by_front = FRONT_MARK in (body or "")
        rows.append((f"키 허용 {path}",
                     "fail" if blocked_by_front else "pass",
                     f"{status} · 앞단이 막지 않았다(뒷단이 판정한다)"
                     if not blocked_by_front else f"{status} · **앞단이 막았다**"))

    for name, verdict, why in rows:
        print(f"[FRONT-LINE] {'X ' if verdict == 'fail' else '  '}{name:56} {why}")
    failed = [n for n, v, _ in rows if v == "fail"]
    if failed:
        print(f"[FRONT-LINE] **실패** — {len(failed)}자리: {failed}")
        return EXIT_FAIL
    print(f"[FRONT-LINE] 통과 — 앞단이 {len(rows)}갈래에서 제 답을 냈다 "
          f"(익명 {len(gated_paths())} · 키 2 · 양성 1 · 음성 1)")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="OPS-13 앞단 관문")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--check", default="")
    ap.add_argument("--probe", default="")
    ap.add_argument("--json", default="", help="두드린 결과를 이 파일에 적는다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    rc = self_test()
    if rc != EXIT_OK:
        return rc
    if args.render:
        return do_render(Path(args.out))
    if args.check:
        return do_check(Path(args.check))
    if args.probe:
        rc = do_probe(args.probe)
        if args.json:
            Path(args.json).write_text(json.dumps(
                {"base": args.probe, "exit": rc}, ensure_ascii=False, indent=2),
                encoding="utf-8")
        return rc
    ap.print_help()
    return EXIT_GRAY


if __name__ == "__main__":
    sys.exit(main())
