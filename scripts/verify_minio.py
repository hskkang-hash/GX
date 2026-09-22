#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""저장소가 **섰는가**, 그리고 화면이 부르는 자리가 **그것을 받는가** (P-5).

    "P-5 MinIO: docker compose 1개 · lock 고정 · 자격증명 로컬 .env(이름만 저장소) ·
     강제 도구: /api/media-data/ 200 + 객체 1 · route-alive 죽은 라우트 0"

왜 판정기가 따로 있는가 — **떴다와 받는다는 다른 사실이다**
------------------------------------------------------------
`docker ps` 가 `healthy` 라고 말하는 것은 **프로세스가 산다**는 뜻이다. 우리가 알고
싶은 것은 그것이 아니라 **화면이 부르는 자리가 답을 주는가**이다. 둘 사이에는
DNS · 자격증명 · 버킷 · 권한 · 백엔드 설정이 통째로 들어 있고, 그 중 하나만 어긋나도
`healthy` 는 그대로 초록이다.

그래서 이 판정기는 세 자리를 **끝에서 끝까지** 본다:

    ① 저장소가 살아 있는가          MinIO health
    ② 우리 버킷에 객체가 있는가      최소 1건 — 0건은 「빈 것」이지 「닿은 것」이 아니다
    ③ 화면이 부르는 라우트가 받는가   /api/media-data/ 200 **그리고** success:true

★ ③의 `success` 를 함께 보는 이유가 이 파일의 존재 이유에 가깝다. 2026-09-14 에
  이 자리가 **`success: true` · `status: 500`** 을 냈다(D-397). dj-core `BaseResponse` 의
  기본값이 True 라 뷰가 안 넘기면 **조용히 참**이 된다. 상태 코드만 보는 판정은 그날
  초록이었을 것이고, 상태 코드만 보는 판정은 오늘도 그럴 것이다.

    python scripts/verify_minio.py            # 판정
    python scripts/verify_minio.py --self-test

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(자격증명·환경 없음)

★ 목록의 내용은 MinIO 가 아니라 **DB** 가 낸다 [실측 2026-09-18] —
  `MediaDataService.list_media` 는 MinIO 로는 **가용성만** 보고 항목은 질의로 만든다.
  그래서 버킷에 객체를 직접 넣어도 목록에 안 뜬다. **그것이 옳다.** 이 판정기가
  ②와 ③을 따로 세는 이유이기도 하다 — 둘은 다른 것을 증명한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_route_alive import (  # noqa: E402  — **같은 눈으로 읽는다** (D-369)
    LOCAL_ENV_FILES,
    delegate_to_container,
    load_local_env,
    login,
)

ROOT = Path(__file__).resolve().parent.parent
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 것은 그날의 두 수다.
#:   [실측 2026-09-14~17] `/api/media-data/` 와 `/api/media-data` 가 **둘 다 500** 이었고,
#:   그것이 게이트 `route-alive` 의 유일한 빨강이었다. 원인은 MinIO 부재.
BIRTH_SAMPLE_DEAD = ("/api/media-data/", "/api/media-data", 500)

#: ★ 출생 표본 ② — **조용한 성공** (D-397). 그날 응답 봉투가 이랬다:
#:   `success: true` · `status: 500`. 상태 코드만 보는 판정은 이것을 초록으로 읽는다.
BIRTH_SAMPLE_SILENT_SUCCESS = (500, True)   # (status, success) — 이 조합은 **죽었다**

MEDIA_PATH = "/api/media-data/?page_size=25&current_page=1"

#: ★ [턴 AD · 차선 Q · P-107 MEASURED 배선] 머리글의 **분모**. `main()` 이 끝에서 끝까지
#: 항상 재는 네 자리 이름 그대로다(①~④ 주석 그대로) — 저장소 객체 수·라우트 응답은
#: `--self-test`(호스트 · MinIO/DB 없음)에서는 잴 수 없어서, 분모를 손으로 안 넣고
#: 이 판정기가 매번 훑는 자리 수를 센다(D-301). 라이브 수는 `[MINIO]` 줄에 찍힌다.
MEASURED_STAGES = ("저장소 health", "버킷 객체 존재", "화면 라우트 응답(success 포함)",
                   "캐시 안팎 일치")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def judge_media(status: int, success: object) -> tuple[bool, str]:
    """미디어 목록 응답 하나를 판정한다. **규칙을 함수로 떼어 둔 이유는 시험하기 위해서다.**

    · 2xx + success:true    받았다
    · 2xx + success:false   **못 받았다** — 봉투가 스스로 아니라고 말한다
    · 그 밖                  못 받았다
    """
    if success is False:
        return False, "봉투가 success:false 다 — 상태 코드만 보면 놓친다 (D-397)"
    if 200 <= status < 300:
        return True, "받는다"
    if status >= 500:
        return False, "**서버 오류** — 저장소에 닿지 못하는 자리다"
    return False, "받지 못한다"


def probe(api: str, path: str, token: str) -> tuple[int, object]:
    """한 자리를 때려 (HTTP 상태, 본문 `success`) 를 돌려준다.

    ★ 두 값을 함께 내는 이유는 이 파일 머리말의 D-397 그대로다 — 상태 코드만 보는
      판정은 `success:true · status:500` 을 초록으로 읽는다.
    """
    req = urllib.request.Request(api + path)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            status = r.status
            body = json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read().decode("utf-8", "replace") or "{}")
        except json.JSONDecodeError:
            body = {}
    except Exception as exc:                             # noqa: BLE001
        print(f"[MINIO] {path} — 응답을 못 받았다: {type(exc).__name__} {exc}")
        status, body = 0, {}
    return status, (body.get("success") if isinstance(body, dict) else None)


def http_status(url: str, timeout: int = 10) -> int:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:                                   # noqa: BLE001
        return 0


def minio_host() -> str:
    """`MINIO_ENDPOINT` 는 `host[:port]` 다 — 스킴이 붙어 오면 떼어 낸다."""
    ep = (os.environ.get("MINIO_ENDPOINT") or "minio:9000").strip()
    for scheme in ("http://", "https://"):
        if ep.startswith(scheme):
            ep = ep[len(scheme):]
    return ep.rstrip("/")


def count_objects(host: str, user: str, password: str, bucket: str) -> int | None:
    """버킷의 객체 수. **못 세면 None** — 0건과 구별한다 (D-301)."""
    try:
        from minio import Minio                          # noqa: PLC0415
    except ImportError:
        print("[MINIO] minio 클라이언트가 없다 — 컨테이너 안에서 돌려야 한다")
        return None
    try:
        c = Minio(host, access_key=user, secret_key=password, secure=False)
        if not c.bucket_exists(bucket):
            print(f"[MINIO] 버킷이 없다: {bucket}")
            return 0
        return sum(1 for _ in c.list_objects(bucket, recursive=True))
    except Exception as exc:                             # noqa: BLE001
        print(f"[MINIO] 객체를 세지 못했다: {type(exc).__name__} {exc}")
        return None


def self_test() -> int:
    """판정 규칙과 출생 표본을 함께 본다 (D-277 · D-310)."""
    bad: list[str] = []

    # ── 판정 규칙 ─────────────────────────────────────────────────────────
    for status, success, expect in ((200, True, True), (204, True, True),
                                    (500, False, False), (404, None, False),
                                    (0, None, False)):
        got, _ = judge_media(status, success)
        if got != expect:
            bad.append(f"judge_media({status}, {success}) = {got} (기대 {expect})")

    # ── 출생 표본 ① 죽어 있던 두 자리 ─────────────────────────────────────
    p1, p2, dead_status = BIRTH_SAMPLE_DEAD
    if judge_media(dead_status, None)[0]:
        bad.append(f"출생 표본 ① — {p1}·{p2} 의 {dead_status} 를 「받는다」로 읽는다. "
                   f"이 판정기가 태어난 바로 그 자리다")
    if p1.rstrip("/") != p2:
        bad.append("출생 표본 ① — 두 자리는 **같은 자리의 두 형태**(빗금 있음/없음)여야 한다")

    # ── 출생 표본 ② 조용한 성공 ───────────────────────────────────────────
    st, ok = BIRTH_SAMPLE_SILENT_SUCCESS
    if judge_media(st, ok)[0]:
        bad.append(f"출생 표본 ② — `status:{st}` 인데 `success:{ok}` 인 봉투를 「받는다」로 "
                   f"읽는다. 2026-09-14 에 이 자리가 정확히 그랬다 (D-397)")
    #: ★ 음성 갈래 — **모든 것을 빨갛게 만들면** 이 규칙도 쓸모가 없다.
    if not judge_media(200, True)[0]:
        bad.append("정상 봉투(200 + success:true)를 「못 받는다」로 읽는다")
    #: `success` 칸이 아예 없는 응답(None)은 상태 코드로 판정해야 한다 —
    #: 없는 것과 False 는 다른 사실이다 (D-290).
    if not judge_media(200, None)[0]:
        bad.append("`success` 칸이 없는 200 을 실패로 읽는다 — 없는 것과 False 는 다르다")

    if bad:
        print("[MINIO] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"[MINIO] 자기시험 통과 — 판정 규칙 5종 + 출생 표본 2"
          f"(죽은 두 자리 {dead_status} · 조용한 성공 {st}/{ok}) + 음성 2")
    return EXIT_OK


def main() -> int:
    _env_files = load_local_env()
    ap = argparse.ArgumentParser(description="저장소가 섰는가 · 화면이 받는가 (P-5)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER"))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    container = os.environ.get("GX_ROUTE_CONTAINER", "").strip()
    if container and not os.environ.get("GX_ROUTE_IN_CONTAINER"):
        os.environ.setdefault("GX_API", "http://localhost:8000")
        os.environ.setdefault("MINIO_ENDPOINT", "minio:9000")
        return delegate_to_container(container, None, script="verify_minio.py")

    if _env_files:
        print(f"[MINIO] 로컬 자격증명 파일 읽음: {', '.join(_env_files)} "
              f"(저장소엔 이름만 · D-204)")

    user = os.environ.get("MINIO_ROOT_USER")
    password = os.environ.get("MINIO_ROOT_PASSWORD")
    bucket = os.environ.get("MINIO_BUCKET_NAME", "guardianx-dev")
    if not (user and password):
        print(f"[MINIO] 저장소 자격증명이 없다 (MINIO_ROOT_USER/PASSWORD "
              f"또는 {' / '.join(LOCAL_ENV_FILES)})")
        print("[MINIO] **판정 불가** — 못 물어본 것을 초록으로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE

    host = minio_host()
    rc = EXIT_OK

    # ── ① 저장소가 살아 있는가 ─────────────────────────────────────────────
    health = http_status(f"http://{host}/minio/health/live")
    print(f"[MINIO] [입력] 1건 — 저장소 health ({host}) → {health}")
    if health != 200:
        print("[MINIO] ✗ 저장소에 닿지 못한다 — `docker compose up -d minio` 후 "
              "이 판정기를 다시 돌린다")
        return EXIT_FAIL

    # ── ② 우리 버킷에 객체가 있는가 ────────────────────────────────────────
    n = count_objects(host, user, password, bucket)
    if n is None:
        print("[MINIO] **판정 불가** — 객체를 세지 못했다 (0건과 구별한다 · D-301)")
        return EXIT_UNDECIDABLE
    print(f"[MINIO] [입력] {n}건 — 버킷 `{bucket}` 의 객체")
    if n < 1:
        print("[MINIO] ✗ 객체 0건 — **빈 것**과 **닿은 것**은 다른 사실이다. "
              "탐침 객체 1건을 넣고 다시 잰다")
        rc = EXIT_FAIL

    # ── ③ 화면이 부르는 라우트가 받는가 ────────────────────────────────────
    if not (args.user and args.password):
        print("[MINIO] 화면 자격증명이 없어 라우트를 못 때린다 — **판정 불가**")
        return EXIT_UNDECIDABLE
    token = login(args.api, args.user, args.password)
    if not token:
        print("[MINIO] 토큰을 못 받았다 — **판정 불가**")
        return EXIT_UNDECIDABLE
    for path in (MEDIA_PATH, MEDIA_PATH.replace("/api/media-data/", "/api/media-data")):
        status, success = probe(args.api, path, token)
        ok, why = judge_media(status, success)
        mark = "  " if ok else "✗ "
        print(f"[MINIO] {mark}{status:3} success={success!s:5} {path[:46]:46} {why}")
        if not ok:
            rc = EXIT_FAIL

    # ── ④ 캐시 안과 밖이 **같은 것을 말하는가** (P-19 · 상시 항목) ─────────
    #    액자에 든 사진은 언제나 200 이다. 같은 순간에 두 URL 을 견주지 않으면
    #    ③의 초록이 「지금 받는다」인지 「받았던 적이 있다」인지 갈리지 않는다.
    plain = probe(args.api, MEDIA_PATH, token)
    fresh = probe(args.api, f"{MEDIA_PATH}&bust={int(time.time() * 1000)}", token)
    print(f"[MINIO] [입력] 2건 — 같은 순간 두 URL (캐시 안 {plain[0]}/{plain[1]} · "
          f"캐시 밖 {fresh[0]}/{fresh[1]})")
    if plain != fresh:
        rc = EXIT_FAIL
        print(f"[MINIO] ✗ **캐시가 사진을 액자에 넣고 있다** — 질의문자열 하나로 답이 "
              f"바뀐다. 캐시 안 {plain} vs 캐시 밖 {fresh}")
        print("[MINIO]   `media-data` 가 BYPASS_PATTERNS 에서 빠졌는지 먼저 본다 "
              "(D-412 · P-19 · scripts/verify_cache_frame.py)")
    else:
        print("[MINIO]   캐시 안과 밖이 같은 답을 낸다 — 우회가 살아 있다 (D-412)")

    if rc == EXIT_OK:
        print(f"[MINIO] 통과 — 저장소 산다 · 객체 {n}건 · 화면이 부르는 두 자리가 받는다 · "
              f"캐시 안팎이 같다")
    return rc


if __name__ == "__main__":
    from _gate_header import gate_header, account_as  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("저장소가 섰는가 · 화면이 받는가 — 끝에서 끝까지 **분모 %d자리**"
                  "(`main()` 이 매번 훑는 자리 ①~④ · 지금 셌다). 버킷 객체 수 · 라우트 "
                  "응답은 gx-shell 안에서 재고 `[MINIO]` 줄에 그대로 찍힌다"
                  % len(MEASURED_STAGES)),
        target="저장소 " + (os.environ.get("MINIO_ENDPOINT") or "minio:9000") + " + " + os.environ.get("GX_API", "http://localhost:8000"),
        as_="저장소 쪽: MINIO_ROOT_USER/MINIO_ROOT_PASSWORD (호스트 .env · **앱의 자격이 아니다**) · 라우트 쪽: " + account_as(),
        source="살아 있는 저장소 + 살아 있는 서버 응답 (HTTP)",
        reason="root 로 재는 것은 **저장소 자체가 살아 있는가**뿐이다. 앱이 닿는지는 여기서 재지지 않는다 — 앱이 든 MINIO_ACCESS_KEY/SECRET_KEY 의 모양은 `verify_prod_settings.py` ⑦ 이 잰다 (턴 L: 둘 다 5자·같은 문자열 → 503)",
    )
    sys.exit(main())
