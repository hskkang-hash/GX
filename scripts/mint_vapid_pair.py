# -*- coding: utf-8 -*-
"""창 2b — **VAPID 한 쌍을 만든다. 값은 화면에 내지 않는다.**

    세종 판정 **P-259**: 구독한 기기가 **0** 이라 새 쌍을 만들어도 **끊길 것이 없다**.
    값은 금고(저장소 밖 · gitignored) · 대표께는 「발급했다」 한 줄만 올린다.

★ 이 파일이 지키는 것 셋
  ① **비밀을 표준출력에 0** — 이름 · 길이 · sha256 앞 12자까지만 낸다(D-204).
  ② **argv 에 0** — 값을 인자로 받지도 내지도 않는다.
  ③ **이미 있으면 덮지 않는다** — 덮는 것은 「되돌릴 수 없는 변경」이다.
     바꾸려면 사람이 먼저 옛 파일을 비켜 두어야 한다(`--force` 같은 문은 안 둔다).

★ **공개키는 정의상 공개다** — 브라우저가 `pushManager.subscribe` 에 그 값을 넣는다.
  그래도 여기서는 안 찍는다: 이 창에서 사람이 읽을 일이 없고, 안 찍는 습관이 싸다.

부르는 자리: **gx-shell 안**(`py_vapid` 가 거기 있다). 저장소를 쓰지 않는다 —
파일은 표준출력이 아니라 `--out` 이 가리키는 자리에 **컨테이너가 직접 쓴다**.

    MSYS_NO_PATHCONV=1 docker exec -w /app gx-shell \\
      python /repo/scripts/mint_vapid_pair.py --out /repo/.env.vapid --subject mailto:...
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sys

PUBLIC_ENV = "GX_VAPID_PUBLIC_KEY"
PRIVATE_ENV = "GX_VAPID_PRIVATE_KEY"
SUBJECT_ENV = "GX_VAPID_SUBJECT"


def _fp(value: str) -> str:
    """지문 — sha256 앞 12자. **값 자체는 절대 돌려주지 않는다.**"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def mint() -> tuple[str, str]:
    """P-256 한 쌍을 만들어 **웹푸시가 기대하는 모양**으로 돌려준다.

    공개키 — 비압축점 65바이트(0x04 || X || Y)의 base64url. 브라우저의
    `applicationServerKey` 가 이 모양을 받는다.
    비밀키 — 32바이트 스칼라의 base64url. `pywebpush` 가 이 모양을 받는다.
    """
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    priv = key.private_numbers().private_value.to_bytes(32, "big")
    return _b64url(pub), _b64url(priv)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="쓸 자리 (저장소 밖 · gitignored 여야 한다)")
    ap.add_argument("--subject", required=True,
                    help="mailto: 한 줄 — 비밀이 아니다(푸시 서비스가 우리를 부를 주소)")
    args = ap.parse_args()

    if not args.subject.startswith(("mailto:", "https://")):
        print("[VAPID] subject 는 mailto: 나 https:// 로 시작해야 한다 — RFC 8292")
        return 2

    #: ★ 이미 있으면 **덮지 않는다.** 덮으면 지금 구독한 기기가 있을 때 조용히 끊긴다.
    if os.path.exists(args.out):
        print("[VAPID] `%s` 가 **이미 있다** — 덮지 않는다. "
              "바꾸려면 사람이 먼저 그 파일을 비켜 둔다" % args.out)
        return 1

    public, private = mint()

    #: 파일에만 값이 간다. 권한을 좁힌다(0600) — 같은 통 안의 다른 눈도 막는다.
    body = "%s=%s\n%s=%s\n%s=%s\n" % (
        PUBLIC_ENV, public, PRIVATE_ENV, private, SUBJECT_ENV, args.subject)
    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, body.encode("utf-8"))
    finally:
        os.close(fd)

    #: ★ 여기서부터가 사람이 보는 전부다 — **값은 한 글자도 없다.**
    print("[VAPID] 썼다: %s (0600)" % args.out)
    for name, value in ((PUBLIC_ENV, public), (PRIVATE_ENV, private)):
        print("[VAPID]   %s len=%d sha256[:12]=%s" % (name, len(value), _fp(value)))
    print("[VAPID]   %s len=%d (비밀 아님)" % (SUBJECT_ENV, len(args.subject)))
    print("[VAPID] ★ 값은 이 출력에 **0** 이다 — 이름 · 길이 · 지문까지만 낸다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
