# -*- coding: utf-8 -*-
"""LAW-08 증거 해시 체인 — **고치면 다음 날 종이와 어긋난다**.

무엇을 하는가
-------------
감사 한 줄이 저장될 때마다 그 줄에 `prev_hash` · `hash`(SHA-256) 두 값을 붙인다.
`hash = SHA256(prev_hash ‖ 그 행의 증거 필드)` 이므로, **행 하나를 고치면 그 뒤의 모든
행이 어긋난다.** 그리고 매일 00:00 그날의 마지막 `hash` 를 일일 보고서 꼬리에 인쇄한다 —
**종이가 앵커다.** 종이는 우리 DB 안에 없으므로, DB 를 통째로 다시 써도 어제 인쇄된
40자와 맞출 수 없다.

왜 체인만으로는 부족한가 (이 파일이 혼자서는 못 하는 일)
--------------------------------------------------------
체인만 있으면 **체인째 다시 계산**하면 된다. 그래서 값이 종이에 있다. 이 모듈은
「행이 바뀌었다」를 즉시 exit 1 로 만드는 절반이고, 나머지 절반은 인쇄된 앵커다.
`daily_anchor()` 가 그 둘을 잇는 자리다.

★ 두 칸을 **어디에** 두었나 — PRD 와 갈린 자리 [판정 2026-09-04 · 차선 S]
-------------------------------------------------------------------------
PRD v2.5 §E3-1 은 *"기존 `AuditLogs` 에 두 칸"* 이라고 적었다. 그런데 `logger.AuditLogs`
는 **dj-core 소유이고 §0.4 금지구역(D-207)** 이다 — 열을 더하려면 남의 모델을 고치거나
남의 표에 ALTER 를 걸어야 하고, 둘 다 금지구역을 건드린다. 게다가 시험은
`--nomigrations` 로 돌아 모델에 없는 열은 시험 DB 에 아예 서지 않는다 — 즉 열을 더하는
길은 **증거를 못 내는 길**이다.

그래서 두 칸을 **이미 우리 것인 칸 안**에 둔다: `data_after` JSON 의 예약 키 두 개
(`__prev_hash__` · `__hash__`). 이 칸은 `common/audit_writer.py` 가 쓰고 우리 코드만 읽는다.
바꾼 것은 **저장 위치뿐이고 성질은 같다** — 행마다 두 값이 있고, 값은 그 행의 내용에서
나오며, 하나를 고치면 뒤가 전부 어긋난다.

  ⚠ 진짜 열 두 개로 옮기려면 이 파일의 `_chain_of` · `_with_chain` 둘만 고치면 된다.
    다른 곳은 열의 모양을 모른다. 옮길 때 필요한 것은 dj-core 결정이지 이 파일이 아니다.

  ⚠ 2026-09-19(P-191) 부터 예약 키가 **셋**이다 — 세 번째 `__seq__` 는 증거가 아니라
    **자리표**(줄의 몇 번째인가)이고 해시에 안 들어간다. 왜 필요한지는 `SEQ_KEY` 에.

★ 같은 순간 두 손 — 체인이 갈라지던 자리 [P-191 · 실측 2026-09-19]
-------------------------------------------------------------------
두 요청이 같은 순간에 이어 붙이면 **둘 다 같은 앞 해시를 읽어** 줄이 갈라졌다.
막는 자리는 `lock_chain()`(구간 잠금)과 `SEQ_KEY`(자리표) 둘이고, 둘 다 있어야 막힌다.
이미 갈라진 자리는 **고치지 않고 적는다** — `RECORDED_BREAKS`.

★ `_base_manager` 를 쓰는 이유 — **면제가 아니라 요건이다**
-----------------------------------------------------------
`AuditLogs` 의 기본 매니저는 요청 스레드의 그룹으로 **행을 감춘다**(dj-core
`get_queryset` 실측). 체인은 감춰진 행을 건너뛰면 안 된다 — 건너뛴 순간 「없는 행」과
「지워진 행」이 같아지고, 그것이 바로 이 체인이 잡으려는 사건이다. 그래서 체인은
**언제나 전건을 본다.** 이 파일 밖에서 `_base_manager` 를 새로 쓰지 말 것.

★ 왜 테넌트별 체인이 아닌가
---------------------------
`AuditLogs` 에는 우리가 채우는 테넌트 열이 없다(`kernels/k1_event/field_reply.py` 머리말
[실측]). 없는 열로 체인을 가르면 「어느 체인에 붙일지」를 부르는 쪽이 고르게 되고,
**고를 수 있으면 남의 체인에 붙일 수 있다.** 그래서 체인은 하나이고, 이어 붙이는 자리는
`audit_writer.write()` 안쪽 한 곳뿐이다 — 인자로 체인을 고르는 면이 없다.
그 대신 테넌트는 **해시되는 내용 안에** 있다(actor·payload). 하나의 체인은 또한
「어느 테넌트에서든 한 행만 고쳐도 전체가 깨진다」는 뜻이라, 탐지력이 더 세다.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Sequence

#: 체인의 시작. 첫 행의 `prev_hash` 다. 0 40개가 아니라 **64개** — SHA-256 길이와
#: 같게 두어야 "길이가 다른 값" 이 조용히 섞이지 않는다.
GENESIS = "0" * 64

#: 두 칸의 이름. `data_after` JSON 안의 예약 키다.
PREV_KEY = "__prev_hash__"
HASH_KEY = "__hash__"

#: ★ P-191 — **자리표**. 증거가 아니라 「이 행이 줄의 몇 번째인가」다. 해시에 안 들어간다.
#:
#: 왜 필요한가 [실측 2026-09-19]
#:   체인의 순서는 원래 **행 번호(id)** 였다. 그런데 번호는 INSERT 가 **시작될 때** 나오고,
#:   줄에 붙는 것은 그 뒤다. 같은 순간 여러 손이 쓰면 **번호 순서와 붙은 순서가 뒤집힌다** —
#:   6번이 먼저 붙고 2번이 나중에 붙는다. 번호로 검증하면 그것이 「순서가 바뀌었다」로 읽힌다.
#:   자리표가 있으면 **붙은 순서가 곧 줄의 순서**이고, 잠금이 그 순서를 하나로 만든다.
#:
#: 자리표는 `max(앞자리 + 1, 행 번호)` 다 — 다투지 않는 평시에는 **자리표 = 행 번호**라
#: 옛 행(자리표 없는 행: 자리 = 번호)과 한 줄로 이어진다. 뒤집힌 순간에만 갈린다.
SEQ_KEY = "__seq__"

#: 해시가 **덮지 않는** 예약 키들. 늘릴 때는 반드시 `strip_chain` 을 거치게 둔다 —
#: 하나라도 빠지면 그 행은 저장하는 순간 자기 해시와 어긋난다.
RESERVED_KEYS = (PREV_KEY, HASH_KEY, SEQ_KEY)

#: 체인에 드는 행. **우리가 쓴 행만** 이다 — dj-core 미들웨어가 남기는 행은 우리가
#: 쓰지 않았으므로 이어 붙일 수 없고, 이어 붙이지 않은 것을 「끊겼다」고 부르면
#: 판정이 늘 빨강이 된다. 경계를 여기 한 줄로 적어 둔다.
CHAIN_PREFIX = "guardianx."

#: 해시가 덮는 **증거 필드**. 여기 없는 열을 고치면 체인은 조용하다 —
#: 그래서 무엇이 빠졌는지 다음 사람이 보이게 목록으로 둔다.
#:   · `id` · `create_datetime` — 순서와 시각. 빠지면 행을 **옮겨 끼울** 수 있다.
#:   · `logger_name` · `level_name` — 어느 전건인가 · 허용인가 거부인가.
#:   · `msg` · `note` — 사람이 읽는 사유.
#:   · `api_name` · `api_method` · `status_http` — 무엇을 어떻게 불렀나.
#:   · `user_id` · `username` · `target_user_id` — 누가 · 누구에게.
#:   · `data_before` · `data_after` — 값의 전후. **두 칸 자신은 뺀다**(아래 `_evidence_of`).
HASHED_FIELDS: tuple[str, ...] = (
    "id",
    "create_datetime",
    "logger_name",
    "level_name",
    "msg",
    "note",
    "api_name",
    "api_method",
    "status_http",
    "user_id",
    "username",
    "target_user_id",
    "data_before",
    "data_after",
)


# ══════════════════════════════════════════════════════════════════════════
# 1. 순수 계산 — Django 가 없어도 돈다. 게이트의 자기시험이 겨누는 과녁이 여기다.
# ══════════════════════════════════════════════════════════════════════════

def strip_chain(payload: Any) -> Any:
    """`data_after` 에서 **두 칸을 뺀** 값. 해시는 자기 자신을 덮지 않는다.

    빼지 않으면 해시를 저장하는 순간 그 행의 내용이 바뀌고, 다시 계산하면 다른 값이
    나온다 — 검증이 언제나 빨강이 된다.
    """
    if not isinstance(payload, dict):
        return payload
    rest = {k: v for k, v in payload.items() if k not in RESERVED_KEYS}
    #: ★ 두 칸만 있던 행은 **원래 비어 있던 행**이다. `{}` 로 두면 `None` 이었던
    #:   행과 값이 갈리고, 그러면 두 칸을 붙이는 행위 자체가 해시를 바꾼다.
    return rest or None


def canonical(record: dict) -> str:
    """해시에 넣는 **한 가지 모양**. 키 순서·공백·인코딩이 흔들리면 해시가 흔들린다."""
    return json.dumps(
        {k: record.get(k) for k in HASHED_FIELDS},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str,
    )


def digest(*, prev_hash: str, record: dict) -> str:
    """`SHA256(prev_hash ‖ 증거)`. 앞의 값이 들어가는 것이 체인의 전부다."""
    body = f"{prev_hash}\n{canonical(record)}"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Break:
    """체인이 어긋난 자리 하나. **어디가 · 왜** 를 둘 다 든다 —
    「깨졌다」만 있으면 사람이 고칠 데를 못 찾는다."""

    audit_id: int
    kind: str            # missing | prev_mismatch | hash_mismatch
    detail: str
    #: ★ P-191 — **그 자리의 두 값**. 사람이 읽는 `detail` 에는 앞 12자만 들어가는데,
    #:   12자는 「끊김 기록」(아래 `RECORDED_BREAKS`)의 열쇠로 쓰기엔 짧다. 짧은 열쇠는
    #:   다른 끊김을 같은 끊김으로 읽고, 그러면 **새 끊김이 옛 기록 뒤에 숨는다.**
    #:   그래서 64자 두 개를 값으로 들고 다닌다.
    got: str = ""        # 그 행에 **저장된** 값
    want: str = ""       # 체인에서 **나와야 하는** 값

    def __str__(self) -> str:      # pragma: no cover - 사람이 읽는 줄
        return f"#{self.audit_id} {self.kind} — {self.detail}"

    @property
    def key(self) -> tuple[int, str, str, str]:
        """이 끊김을 **딱 이것으로만** 가리키는 열쇠. 기록과 대조하는 자리다."""
        return (self.audit_id, self.kind, self.got, self.want)


#: 어긋남의 세 가지 모양. 문자열을 여기서만 만든다 — 부르는 쪽이 새 이름을 지으면
#: 집계가 갈린다.
MISSING = "missing"
PREV_MISMATCH = "prev_mismatch"
HASH_MISMATCH = "hash_mismatch"


def verify_sequence(entries: Sequence[dict]) -> tuple[Break, ...]:
    """행들을 **줄의 순서대로** 받아 어긋난 자리를 전부 돌려준다.

    ⚠ 순서를 만드는 것은 이 함수가 아니라 `chain_entries` 다(`_order_key` = 자리표).
      평시에는 그 순서가 곧 id 오름차순이다. 같은 순간에 붙어 번호와 순서가 뒤집힌
      자리에서만 갈리고, **그 자리를 번호로 읽으면 멀쩡한 줄이 빨강**이 된다 (P-191).

    `entries` 한 개의 모양::

        {"id": 12, "record": {...증거 필드...}, "prev_hash": "…", "hash": "…"}

    ★ 첫 어긋남에서 멈추지 않는다. 멈추면 "1건" 이라는 수가 언제나 나오고,
      그 수로는 **한 행이 바뀐 것**과 **표가 통째로 다시 쓰인 것**을 못 가른다.

    ★ 체인 이전의 행 — LAW-08 이 서기 전에 쌓인 행은 두 칸이 없다. 그것을 「끊겼다」로
      세면 판정이 영원히 빨강이고, 빨강이 상시가 되면 아무도 안 본다(D-301 의 형제).
      그래서 **첫 번째 해시가 있는 행부터** 체인으로 본다. 그 뒤에 두 칸 없는 행이
      나오면 그것은 진짜 끊김이다 — 누가 두 칸을 지운 것이다.

    ★ **앞머리는 비교하지 않는다** — 그 자리를 지키는 것은 코드가 아니라 종이다.
      감사 로그에는 보존기간 집행(`common/ops_tasks.ops_audit_purge_beat` → dj-core
      `purge_old_audit_logs`)이 있고, 그것은 **언제나 앞에서부터 지운다.** 앞머리에
      `GENESIS` 를 요구하면 보존기간이 한 번 돌자마자 판정이 영구 빨강이 되고, 상시
      빨강은 아무도 안 본다. 그래서 첫 체인 행의 `prev_hash` 는 그대로 받아들이고,
      **앞머리가 잘렸다는 사실을 보고서가 말한다**(`ChainReport.starts_at_genesis`).
      잘린 날들의 값은 그날 인쇄된 앵커에 있다 — 종이가 그 자리의 증거다.
      가운데를 지우는 것은 여전히 잡힌다: 다음 행의 `prev_hash` 가 어긋난다.
    """
    breaks: list[Break] = []
    prev_hash: str | None = None      # None = 아직 체인이 시작되지 않았다

    for e in entries:
        got_hash = e.get("hash")
        if prev_hash is None:
            if not got_hash:
                continue              # 체인 이전의 행 — 세지 않는다
            prev_hash = e.get("prev_hash") or ""   # 앞머리는 받아들인다(위 ★)

        if not got_hash:
            breaks.append(Break(e["id"], MISSING,
                                "두 칸이 없다 — 체인이 시작된 뒤의 행인데 해시가 비었다",
                                got="", want=prev_hash))
            continue

        declared_prev = e.get("prev_hash") or ""
        if declared_prev != prev_hash:
            breaks.append(Break(
                e["id"], PREV_MISMATCH,
                f"prev_hash={declared_prev[:12]}… 인데 앞 행의 hash 는 {prev_hash[:12]}… "
                f"— 앞 행이 지워졌거나 순서가 바뀌었다",
                got=declared_prev, want=prev_hash))

        expect = digest(prev_hash=declared_prev, record=e.get("record") or {})
        if expect != got_hash:
            breaks.append(Break(
                e["id"], HASH_MISMATCH,
                f"저장된 hash={got_hash[:12]}… 인데 내용에서 나오는 값은 {expect[:12]}… "
                f"— **이 행의 내용이 바뀌었다**",
                got=got_hash, want=expect))

        prev_hash = got_hash

    return tuple(breaks)


# ──────────────────────────────────────────────────────────────────────────
# ★ P-191 「끊김 기록」 — **과거 행을 고치지 않고** 체인을 그 지점부터 다시 잇는 자리
#
# 무엇이 있었나 [판정 2026-09-19 · 세종 · 차선 S]
#   경합으로 갈라진 자리들이 남았다. 고치는 길은 둘뿐인데 하나는 금지다:
#     ① 과거 행의 두 칸을 다시 계산해 덮는다 → **되돌리기다. 금지.** 그리고 그것은
#        이 체인이 잡으려는 행위 그 자체다 — 우리가 하면 남도 할 수 있다는 뜻이 된다.
#     ② 끊긴 자리를 **기록으로 남기고**, 체인은 그 지점부터 이어진 것으로 읽는다.
#   이 장부가 ② 다. **면제가 아니라 등재다**(D-261 c) — 가려지는 것이 아니라 적힌다.
#
# 왜 이것이 「빨강을 회색으로 바꾸는 것」이 아닌가
#   · 열쇠가 **64자 두 개 + id + 종류**다. 그 행에서 지금 나오는 값이 기록과 한 글자라도
#     다르면 **안 맞는다** — 즉 같은 자리에 새로 생긴 끊김은 기록 뒤에 못 숨는다.
#   · 기록된 끊김도 **세어서 들고 다닌다**(`ChainReport.recorded`). 사라지지 않는다.
#   · 새 줄을 여기 더하는 것은 커밋으로 남고 사람이 읽는다. 조용히 넓힐 수 없다.
#
# ⚠ 여기에 줄을 더하는 것은 **대표 결정**이다. 끊김을 적는 것은 「그 자리를 포기한다」는
#   선언이고, 그 선언을 코드가 혼자 하면 장부는 하루 만에 쓰레기가 된다.
# ──────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RecordedBreak:
    """이미 **적어 둔** 끊김 하나. 적은 날과 사유가 값 안에 있다 — 주석이 아니라 값이다."""

    audit_id: int
    kind: str
    got: str             # 그 행에 저장된 값 (64자)
    want: str            # 체인에서 나와야 하는 값 (64자)
    when: str            # 기록한 날
    why: str             # 왜 고치지 않고 적었나

    @property
    def key(self) -> tuple[int, str, str, str]:
        return (self.audit_id, self.kind, self.got, self.want)


#: 기록된 끊김. **늘어나는 것이 정상이 아니다.** 늘릴 때는 위 ⚠ 를 읽고 늘린다.
#:
#: 지금 든 22건 — 전부 `prev_mismatch` 이고 전부 **같은 원인**(P-191 경합)이다.
#:   · 판정문(2026-09-19 · 세종)은 「끊김 4건」이라 적었는데, 그날 도구로 재니 **22건**이었다.
#:     늘어난 까닭은 새 사건이 아니라 **같은 경합이 계속 재현됐기 때문**이다 —
#:     마지막 한 건이 07:04:55Z, 잠금이 선 것이 08:31Z 다. 그 뒤로 태어난 끊김은 없다.
#:   · 수를 손으로 세지 않았다: `verify_sequence` 가 낸 것을 그대로 적었다.
#:   ⚠ 22 는 4 보다 많다 — **판정문이 든 수를 넘겨 적은 것**이므로 조율자·대표의 확인이
#:     필요하다. 확인 전이라면 이 줄들을 지우는 쪽이 「조용히 두는 것」보다 옳다.
RECORDED_BREAKS: tuple[RecordedBreak, ...] = (
    RecordedBreak(
        250280, PREV_MISMATCH,
        "6560f0dac580d6eaf5c3304954486754dc99168a49baa45c4a210bf1ebf13395",
        "0a39b712b9b7f3448700bbf9093af93641fb8356b80d0872182afd1a1c08e60a",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-18T05:45:00Z · 잠금 이전"),
    RecordedBreak(
        250290, PREV_MISMATCH,
        "1467890b168d840861fd6101216db9276f3d8b1cd44c60a5ac8f83a41a397772",
        "a5c096484b2127e87239c1e2a263d7bd781e6f77974e6bf216b64a2fad9286cc",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-18T05:45:04Z · 잠금 이전"),
    RecordedBreak(
        250291, PREV_MISMATCH,
        "1467890b168d840861fd6101216db9276f3d8b1cd44c60a5ac8f83a41a397772",
        "a152b55832f9cdddd8b3ac5c820c524773caec2c2c3865a89e766b3d2702e6e4",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-18T05:45:04Z · 잠금 이전"),
    RecordedBreak(
        257053, PREV_MISMATCH,
        "2f97fbb8d633ecba40a856d948c379cb3fcbf13693a3f5141a95e4b4908200c2",
        "3e0cfc24e09f93d9c77d913fdc724c4b7249af4d3114ab42910be2ff04485215",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T05:42:24Z · 잠금 이전"),
    RecordedBreak(
        258633, PREV_MISMATCH,
        "48b9ba624880f1cfa863e0224f074bac7487e54f4bcabb76f2c67fde6d301243",
        "7936e26f2c9288af9d65253e1d574e525b68336afe16b38c3a39205e7ebe3f47",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:09:29Z · 잠금 이전"),
    RecordedBreak(
        258653, PREV_MISMATCH,
        "2caa72f799bafa106fbb6b4eb495d4c4b1ad37be658d230b69a944b76b7603e2",
        "68e2d8f64260df9231aa11bb9752ace8283e46e3f8004bf653fcde1ba78a16c8",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:09:49Z · 잠금 이전"),
    RecordedBreak(
        259425, PREV_MISMATCH,
        "804cf5502a171fb51a0102ee51453dfaf5f62b966e1fb2807216fd56de43177d",
        "c2a150394fb2cd00e44bb20f9ea15d46822049296cf3f880e186ebb5cae2ff06",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:33:14Z · 잠금 이전"),
    RecordedBreak(
        259426, PREV_MISMATCH,
        "804cf5502a171fb51a0102ee51453dfaf5f62b966e1fb2807216fd56de43177d",
        "867e41db2644f478aa99c37bd83d46d18f61ad3a714f0ced351e422cbe3c8857",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:33:14Z · 잠금 이전"),
    RecordedBreak(
        259833, PREV_MISMATCH,
        "691beb9e32a402cc1b1664a72ba3948b85c64c2eb299e9a7e7bfcb8ddd3dd5c2",
        "8f9f6b8aeb75ece19e4d1f0772a4bcedddd69ee638d26cfb3fcaeae3046a1d8a",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:45:52Z · 잠금 이전"),
    RecordedBreak(
        259834, PREV_MISMATCH,
        "691beb9e32a402cc1b1664a72ba3948b85c64c2eb299e9a7e7bfcb8ddd3dd5c2",
        "066b0c6ca4910eb702e76f1a6d3f44bcdb1a2199bfabafe8cc3800c1d2ddb8ed",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:45:52Z · 잠금 이전"),
    RecordedBreak(
        260075, PREV_MISMATCH,
        "e696eb08508bff9e8907437cbd0b25e3d80cb3ecb2bf233475d25e72569808f6",
        "9824707265b25fce56026372ec688d5e7f67516a9fdad97fcbdea4e185a4aad1",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:48:41Z · 잠금 이전"),
    RecordedBreak(
        260077, PREV_MISMATCH,
        "e696eb08508bff9e8907437cbd0b25e3d80cb3ecb2bf233475d25e72569808f6",
        "8c5a09cf8300dca8d88d032b39a3ce261766c82a5fd01c1ffc690fe10db1ee0f",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:48:41Z · 잠금 이전"),
    RecordedBreak(
        260372, PREV_MISMATCH,
        "5ebfe71b297a2f51af0a879850f888d221a3f4d3305688c52c5ef4b7188604b0",
        "72f66fe7bed02e518d1fef67a0cac8722f70d7d2c12eedd9f3413d39cba4ed21",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:53:13Z · 잠금 이전"),
    RecordedBreak(
        260373, PREV_MISMATCH,
        "5ebfe71b297a2f51af0a879850f888d221a3f4d3305688c52c5ef4b7188604b0",
        "374a6e01e676a16cff454192a417bc87884a12b8c5679db0171e7783e3ae4f11",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:53:13Z · 잠금 이전"),
    RecordedBreak(
        260733, PREV_MISMATCH,
        "64987bcb5791eae3f6d846d32003643e2c9b24d3a8be7d2c0304e831a6278dbc",
        "9023320bbfb1637b87d5b0009ceb6d6ee54bea6035fe53998dbce626e2dea25a",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:55:37Z · 잠금 이전"),
    RecordedBreak(
        260734, PREV_MISMATCH,
        "64987bcb5791eae3f6d846d32003643e2c9b24d3a8be7d2c0304e831a6278dbc",
        "f38e84f1dd94426c770fc3e4ed7489c483365d58a0af000f0556dce740e08477",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:55:37Z · 잠금 이전"),
    RecordedBreak(
        260978, PREV_MISMATCH,
        "2be3b83e5efd2bc1c1a3707964727484890e0a7ea4e6bac9a1ad7f4a74511fa3",
        "92bb183271def0ec193ef5da3a524ffa117d3a80f036868b3b1022f1591a7fc6",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:58:32Z · 잠금 이전"),
    RecordedBreak(
        260979, PREV_MISMATCH,
        "2be3b83e5efd2bc1c1a3707964727484890e0a7ea4e6bac9a1ad7f4a74511fa3",
        "5bac3e95d97839873224591a94d0d89af8f1a82d9edbb3f4416d8a338d81c721",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T06:58:32Z · 잠금 이전"),
    RecordedBreak(
        261199, PREV_MISMATCH,
        "50a0b2d099f9586661174da931cf90fd93099557f9a3b3b9a5d7cda4c51d3ba5",
        "28de4f1638aee112c4022b83ca8549bc80a0c3ee90ffa5f30beb61d958da5ff9",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T07:02:00Z · 잠금 이전"),
    RecordedBreak(
        261200, PREV_MISMATCH,
        "50a0b2d099f9586661174da931cf90fd93099557f9a3b3b9a5d7cda4c51d3ba5",
        "9d10cd7b1be1d15ffbe634fd9c9b7cb24e994c510c8925c45480eaf63e731e19",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T07:02:00Z · 잠금 이전"),
    RecordedBreak(
        261420, PREV_MISMATCH,
        "043771854c0ee50ba116db91ae36a9b65d50854065f91807d5091ef297e25399",
        "5389fddef2ee2f88cd9bc62a77c3287390ba63a040b7a405ca32025661feed7b",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T07:04:55Z · 잠금 이전"),
    RecordedBreak(
        261421, PREV_MISMATCH,
        "043771854c0ee50ba116db91ae36a9b65d50854065f91807d5091ef297e25399",
        "b7cbd94747ee97cba541edef3e9b3891c4b3d8503cf85a6915aaf1223d5850d7",
        "2026-09-19", "P-191 경합 — 태어난 때 2026-09-19T07:04:55Z · 잠금 이전"),
)


def recorded_keys() -> frozenset[tuple[int, str, str, str]]:
    return frozenset(r.key for r in RECORDED_BREAKS)


def split_recorded(breaks: Sequence[Break]) -> tuple[tuple[Break, ...],
                                                     tuple[Break, ...]]:
    """끊김들을 **(아직 안 적은 것, 이미 적은 것)** 으로 가른다. 순수 함수다."""
    known = recorded_keys()
    fresh = tuple(b for b in breaks if b.key not in known)
    kept = tuple(b for b in breaks if b.key in known)
    return fresh, kept


@dataclass(frozen=True)
class ChainReport:
    """검증 한 번의 결과. `ok` 가 거짓이면 게이트는 exit 1 이다."""

    total: int
    chained: int
    breaks: tuple[Break, ...]
    head: str
    #: 첫 체인 행의 `prev_hash`. `GENESIS` 가 아니면 **앞머리가 잘려 있다** —
    #: 보존기간 집행이 지웠거나, 누가 지웠다. 코드는 그 둘을 못 가른다.
    #: 가르는 것은 그날 인쇄된 앵커다. 그래서 「초록」이라 말할 때 이 값을 함께 낸다.
    tail_prev: str = ""
    #: ★ P-191 — **이미 적어 둔** 끊김들. `breaks` 에서 빠졌을 뿐 사라지지 않았다.
    #:   「어긋남 0」이라 말할 때 이 수를 함께 내야 그 초록이 정직하다.
    recorded: tuple[Break, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.breaks

    @property
    def recorded_count(self) -> int:
        return len(self.recorded)

    @property
    def starts_at_genesis(self) -> bool:
        return self.tail_prev == GENESIS


# ══════════════════════════════════════════════════════════════════════════
# 2. 표에 붙는 부분 — 여기서만 `logger.AuditLogs` 를 만진다.
# ══════════════════════════════════════════════════════════════════════════

def _model():
    from django.apps import apps

    return apps.get_model("logger", "AuditLogs")


def _rows():
    """체인에 드는 행 전건. **감춰진 행도 본다**(머리말 참조)."""
    return _model()._base_manager.filter(logger_name__startswith=CHAIN_PREFIX)


def _chain_of(payload: Any) -> tuple[str, str]:
    """저장된 행에서 두 칸을 꺼낸다. 없으면 `("", "")`.

    ★ 진짜 열 두 개로 옮기는 날 고치는 자리 ①."""
    if not isinstance(payload, dict):
        return "", ""
    return str(payload.get(PREV_KEY) or ""), str(payload.get(HASH_KEY) or "")


def _seq_of(payload: Any) -> int | None:
    """저장된 행의 **자리표**. 없으면 `None` — 자리표가 생기기 전의 행이다."""
    if not isinstance(payload, dict):
        return None
    raw = payload.get(SEQ_KEY)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _order_key(values: dict) -> tuple[int, int]:
    """검증이 읽는 **줄의 순서**. 자리표가 있으면 그것, 없으면 행 번호.

    ★ 두 세계가 한 줄에서 만난다: 자리표 없는 옛 행(자리 = 번호)과 자리표 있는 새 행.
      새 자리표는 언제나 `>= 그 행의 번호` 이고(`append_evidence_hash`), 옛 행은
      전부 더 낮은 번호라 **옛 행 전부가 새 행보다 앞**이다 — 순서가 뒤섞이지 않는다.
      번호를 곁들이는 것은 같은 자리표가 둘일 때의 **되풀이 가능한** 가름을 위해서다.
    """
    row_id = int(values.get("id") or 0)
    seq = _seq_of(values.get("data_after"))
    return (row_id if seq is None else seq, row_id)


def _with_chain(payload: Any, *, prev_hash: str, row_hash: str, seq: int) -> dict:
    """두 칸(+자리표)을 붙인 `data_after`. ★ 옮기는 날 고치는 자리 ②."""
    base = dict(payload) if isinstance(payload, dict) else {}
    base[PREV_KEY] = prev_hash
    base[HASH_KEY] = row_hash
    base[SEQ_KEY] = int(seq)
    return base


def _evidence_of(values: dict) -> dict:
    """DB 에서 읽은 한 행 → **해시가 덮는 부분**. 두 칸은 빠진다."""
    rec = {k: values.get(k) for k in HASHED_FIELDS}
    rec["data_after"] = strip_chain(values.get("data_after"))
    return rec


def _hashed_head() -> tuple[int | None, str, int]:
    """지금 **줄의 끝**. `(그 행의 id, hash, 자리표)`.

    아직 아무것도 안 이었으면 `(None, GENESIS, 0)` — 다음 행이 체인의 첫 행이다.

    ★ 자리표가 가장 큰 행이 줄의 끝이다. **번호가 가장 큰 행이 아니다** — 뒤집힌 순간에
      늦게 붙은 낮은 번호가 끝일 수 있고, 그때 번호로 끝을 고르면 줄이 또 갈라진다.
    """
    qs = _rows().exclude(data_after__isnull=True)
    try:
        qs = qs.filter(data_after__has_key=HASH_KEY)
    except Exception:                                   # pragma: no cover
        pass

    try:
        from django.db.models import IntegerField
        from django.db.models.fields.json import KeyTextTransform
        from django.db.models.functions import Cast

        by_seq = (qs.filter(data_after__has_key=SEQ_KEY)
                  .annotate(_seq=Cast(KeyTextTransform(SEQ_KEY, "data_after"),
                                      IntegerField()))
                  .order_by("-_seq", "-id"))
        for values in by_seq.values("id", "data_after")[:1]:
            _, h = _chain_of(values.get("data_after"))
            seq = _seq_of(values.get("data_after"))
            if h and seq is not None:
                return values["id"], h, seq
    except Exception:                                   # pragma: no cover
        pass                       # 자리표로 못 고르면 아래 옛 길로 — 회색이 아니라 옛 길

    #: 자리표가 생기기 전의 줄 끝. 그때는 **번호가 곧 자리**였다.
    for values in qs.order_by("-id").values("id", "data_after")[:1]:
        _, h = _chain_of(values.get("data_after"))
        if h:
            return values["id"], h, values["id"]
    return None, GENESIS, 0


def _prev_for_position(*, seq: int, row_id: int, fallback: str = "") -> str:
    """**이미 줄에 자리가 있는 행**을 다시 이을 때의 앞 해시 — 그 자리 바로 앞의 행.

    꼬리를 통째로 다시 계산하는 길(`tests/test_s_evidence_chain` 의 앵커 시연 · 사람의
    복구 작업)이 여기로 온다. 그 길에서 줄 끝을 앞으로 삼으면 행이 **자기 뒤로** 붙어
    줄이 꼬인다. 자리가 있는 행은 자리를 지킨다 — 새 자리를 받지 않는다.
    """
    best_key: tuple[int, int] | None = None
    best_hash = ""
    for values in _rows().values("id", "data_after"):
        _, h = _chain_of(values.get("data_after"))
        if not h:
            continue
        key = _order_key(values)
        if key >= (seq, row_id):
            continue
        if best_key is None or key > best_key:
            best_key, best_hash = key, h
    #: 앞에 아무도 없으면 **원래 값을 지킨다.** `GENESIS` 로 덮으면 보존기간이 앞머리를
    #: 지운 줄의 첫 행이 「처음부터 첫 행이었다」로 바뀐다 — 잘린 사실이 지워진다.
    return best_hash or fallback


#: ★ P-191 — 체인 잠금의 열쇠. **하나다.**
#:   체인이 하나이므로(머리말 「왜 테넌트별 체인이 아닌가」) 잠글 것도 하나다.
#:   테넌트별로 가르면 서로 다른 열쇠를 든 두 손이 **같은 줄**에 동시에 붙는다 —
#:   가르는 순간 잠금이 잠그는 시늉이 된다.
#:   ⚠ 이 수를 바꾸면 배포 중 **옛 코드와 새 코드가 서로를 안 막는다.** 고정값이다.
CHAIN_LOCK_KEY = 80_818_008


def lock_chain() -> None:
    """앞 해시를 읽기 **전에** 줄 전체를 잠근다. 같은 순간 둘이 못 지나간다 (P-191).

    ★ 왜 `SELECT … FOR UPDATE` 가 아니라 advisory lock 인가 — 골라야 했고, 이유가 있다
    ------------------------------------------------------------------------------
    ① **잠글 행이 없다.** 앞 해시를 읽는 질의는 `__hash__` 칸이 **있는** 행만 본다.
       같은 순간의 다른 손이 막 넣은 행은 아직 그 칸이 없어 `WHERE` 에서 떨어지고,
       **떨어진 행은 잠기지 않는다.** 그래서 두 손이 서로 다른(또는 같은 옛) 행을 잠그고
       둘 다 통과한다 — 잠근 것처럼 보이지만 아무것도 안 막은 모양이다.
    ② READ COMMITTED 에서 뒤늦게 잠금을 얻어도 PostgreSQL 이 다시 보는 것은 **그 잠근
       행**뿐이다. 그 사이 앞자리에 끼어든 새 행은 다시 안 본다.
    ③ 우리가 지켜야 하는 것은 행 하나가 아니라 **읽고 · 계산하고 · 쓰는 구간**이다.
       구간을 잠그는 물건이 advisory lock 이다.

    ⚠ `pg_advisory_xact_lock` 은 **트랜잭션이 끝날 때** 풀린다. autocommit(트랜잭션 밖)
      에서 부르면 그 한 문장이 끝나는 순간 풀려 **아무것도 안 막는다.** 그 조용한 무잠금이
      이 결함의 얼굴이었으므로, 여기서는 묻고 **아니면 선다.**
    """
    from django.db import connection

    if not connection.in_atomic_block:
        raise RuntimeError(
            "체인 잠금을 트랜잭션 밖에서 걸려 했다 — advisory lock 은 그 문장이 끝나는 "
            "순간 풀리고 아무것도 안 막는다. transaction.atomic 안에서만 부른다")
    if connection.vendor != "postgresql":
        #: sqlite 는 쓰기를 통째로 직렬화한다 — 걸 잠금이 없다. 그리고 그래서
        #: **sqlite 로 돌린 경합 시험은 아무것도 증명하지 못한다**(시험 머리말 참조).
        return
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", [CHAIN_LOCK_KEY])


def append_evidence_hash(*, audit_id: int) -> tuple[str, str]:
    """저장된 감사 행 하나를 **체인에 잇는다.** `(prev_hash, hash)` 를 돌려준다.

    ★ 이 함수는 공개 면이 아니다 — `common/audit_writer.write()` 안쪽에서만 불린다.
      체인을 고르는 인자가 없다는 것이 요점이다: 고를 수 없으면 **남의 체인에 붙일 수
      없다**(머리말 「왜 테넌트별 체인이 아닌가」).

    ★ 실패를 삼키지 않는다. 이을 수 없으면 예외가 올라가고 감사 쓰기가 통째로 실패한다 —
      `audit_writer` 머리말의 규약 그대로다. 체인이 조용히 빠진 행은 **나중에 「그때는
      원래 없었다」로 읽히고**, 그 변명이 한 번 통하면 체인 전체의 값이 사라진다.

    ★ P-191 — 같은 순간 두 손 [실측 2026-09-19 · 운영 DB]
    -----------------------------------------------------
    이 함수는 「앞 해시를 읽고 → 이어 붙인다」였다. 두 요청이 같은 순간에 부르면 **둘 다
    같은 앞 해시를 읽고** 각자 붙여서 줄이 갈라졌다 — 12 밀리초 안에 태어난 세 행이
    같은 `prev_hash` 를 들고 있는 것이 실측이다(`tests/test_law08_chain_race.py` 머리말).
    막는 것은 두 걸음이고, **둘이 같이 있어야 막힌다**:

      ① `lock_chain()` — 앞 해시를 읽기 **전에** 구간을 잠근다. 왜 advisory lock 이고
         왜 `SELECT … FOR UPDATE` 가 아닌지는 그 함수에 적었다.
      ② **자리표**(`SEQ_KEY`) — 줄의 순서를 *붙은 순서*로 못 박는다.
         ⚠ ① 만으로는 **여전히 갈라진다** [실측 · 이 차선이 직접 밟았다]:
           잠금은 「누가 먼저 붙나」만 정하고, 번호(id)는 INSERT 가 **시작될 때** 이미
           나와 있다. 6번이 먼저 잠금을 얻어 붙고 2번이 나중에 붙는 일이 **흔하다**.
           그때 번호로 검증하면 멀쩡한 줄이 「순서가 바뀌었다」로 읽힌다.
           그래서 붙는 순서를 값으로 남기고, 검증도 그 값으로 읽는다(`_order_key`).

    ★ 자리가 **이미 있는 행**을 다시 이으면(꼬리 재계산 · 사람의 복구) 자리표는 그대로
      두고 그 자리 앞의 행에서 다시 잇는다. 새 자리를 주면 행이 자기 뒤로 붙는다.
    """
    from django.db import transaction

    with transaction.atomic():
        lock_chain()                                    # ★① 읽기 전에 잠근다

        values = (_rows().filter(pk=audit_id)
                  .values(*HASHED_FIELDS, "data_after").first())
        if values is None:
            raise ValueError(
                f"감사 행 #{audit_id} 를 못 찾았다 — 체인에 이을 수 없다. "
                f"logger_name 이 {CHAIN_PREFIX!r} 로 시작하지 않는 행은 우리가 쓴 행이 아니다")

        payload = values.get("data_after")
        mine_prev, mine_hash = _chain_of(payload)
        mine_seq = _seq_of(payload)
        if mine_hash and mine_seq is None:
            mine_seq = audit_id                 # 자리표 이전의 행 — 번호가 곧 자리였다

        if mine_seq is not None:                # 자리가 있다 → 그 자리에서 다시 잇는다
            seq = mine_seq
            prev_hash = _prev_for_position(seq=seq, row_id=audit_id,
                                           fallback=mine_prev)
        else:                                   # 새 행 → 줄 끝에 붙는다
            _, prev_hash, head_seq = _hashed_head()
            #: 평시에는 `audit_id` 가 이긴다 — 그래서 자리표 = 번호이고 옛 행과 한 줄이다.
            #: 뒤집힌 순간에만 `앞자리 + 1` 이 이겨 **붙은 순서**가 줄의 순서가 된다.
            seq = max(head_seq + 1, audit_id)

        record = _evidence_of(values)
        row_hash = digest(prev_hash=prev_hash, record=record)
        updated = _rows().filter(pk=audit_id).update(
            data_after=_with_chain(strip_chain(payload), prev_hash=prev_hash,
                                   row_hash=row_hash, seq=seq))
        if updated != 1:
            raise RuntimeError(
                f"감사 행 #{audit_id} 에 두 칸을 쓰지 못했다(갱신 {updated}행). "
                f"체인 없는 감사 행을 남기지 않는다")
    return prev_hash, row_hash


def chain_entries(*, since: datetime | None = None,
                  until: datetime | None = None,
                  limit: int | None = None) -> list[dict]:
    """검증에 넣을 모양으로 행들을 **줄의 순서대로** 읽는다.

    ★ P-191 — 줄의 순서는 **자리표**다(`_order_key`). 자리표가 없던 시절의 행은 번호가
      곧 자리이므로, 평시에는 예전과 **한 글자도 다르지 않은 순서**가 나온다.
      다른 순서가 나오는 경우는 하나뿐이다: 같은 순간에 붙느라 번호와 순서가 뒤집힌 자리.
      그 자리를 번호로 읽으면 멀쩡한 줄이 빨강이 된다.
    """
    qs = _rows()
    if since is not None:
        qs = qs.filter(create_datetime__gte=since)
    if until is not None:
        qs = qs.filter(create_datetime__lt=until)
    qs = qs.order_by("id").values(*HASHED_FIELDS, "data_after")
    if limit:
        qs = qs[:limit]
    out = []
    for values in sorted(qs, key=_order_key):
        prev_hash, row_hash = _chain_of(values.get("data_after"))
        out.append({"id": values["id"], "record": _evidence_of(values),
                    "prev_hash": prev_hash, "hash": row_hash})
    return out


def verify_chain(*, since: datetime | None = None,
                 until: datetime | None = None) -> ChainReport:
    """체인 전체를 다시 계산해 대조한다. **행 하나가 바뀌면 여기서 잡힌다.**"""
    entries = chain_entries(since=since, until=until)
    fresh, kept = split_recorded(verify_sequence(entries))
    chained = sum(1 for e in entries if e["hash"])
    head = next((e["hash"] for e in reversed(entries) if e["hash"]), "")
    tail_prev = next((e["prev_hash"] for e in entries if e["hash"]), "")
    return ChainReport(total=len(entries), chained=chained, breaks=fresh,
                       head=head, tail_prev=tail_prev, recorded=kept)


def daily_anchor(day: date) -> str:
    """**그날의 마지막 해시** — 일일 보고서 꼬리에 인쇄되는 40자다. 없으면 빈 문자열.

    앵커가 종이에 있어야 체인이 값을 갖는다. 체인만 있으면 통째로 다시 계산하면 되고,
    그러면 이 파일이 하는 일은 「고치기를 조금 귀찮게 만드는 것」뿐이다.
    """
    from django.utils import timezone

    start = datetime(day.year, day.month, day.day)
    if timezone.is_aware(timezone.now()):
        start = timezone.make_aware(start, timezone.get_current_timezone())
    end = start + timedelta(days=1)

    #: ★ P-191 — **줄의 순서로** 마지막을 고른다. 번호가 가장 큰 행이 아니다 —
    #:   뒤집힌 순간에는 늦게 붙은 낮은 번호가 그날의 마지막이고, 종이에 찍히는 값은
    #:   그것이어야 한다. 종이와 코드가 다른 규칙으로 고르면 대조가 불가능해진다.
    qs = (_rows().filter(create_datetime__gte=start, create_datetime__lt=end)
          .order_by("-id").values("id", "data_after"))
    best_key: tuple[int, int] | None = None
    best_hash = ""
    for values in qs[:200]:
        _, h = _chain_of(values.get("data_after"))
        if not h:
            continue
        key = _order_key(values)
        if best_key is None or key > best_key:
            best_key, best_hash = key, h
    return best_hash


def anchor_line(day: date, anchor: str) -> str:
    """보고서 꼬리에 찍히는 **한 줄**. 모양을 여기서만 만든다 —
    두 곳에서 만들면 종이와 화면이 다른 문자열을 갖게 되고, 그 순간 대조가 불가능해진다.
    """
    if not anchor:
        return f"[LAW-08] {day.isoformat()} 증거 해시 앵커 — 그날 감사 기록 없음"
    return f"[LAW-08] {day.isoformat()} 증거 해시 앵커 SHA-256: {anchor}"


def iter_hashed_fields() -> Iterable[str]:      # pragma: no cover - 읽는 편의
    return HASHED_FIELDS
