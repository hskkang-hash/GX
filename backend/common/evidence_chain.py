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
    rest = {k: v for k, v in payload.items() if k not in (PREV_KEY, HASH_KEY)}
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

    def __str__(self) -> str:      # pragma: no cover - 사람이 읽는 줄
        return f"#{self.audit_id} {self.kind} — {self.detail}"


#: 어긋남의 세 가지 모양. 문자열을 여기서만 만든다 — 부르는 쪽이 새 이름을 지으면
#: 집계가 갈린다.
MISSING = "missing"
PREV_MISMATCH = "prev_mismatch"
HASH_MISMATCH = "hash_mismatch"


def verify_sequence(entries: Sequence[dict]) -> tuple[Break, ...]:
    """행들을 **id 오름차순으로** 받아 어긋난 자리를 전부 돌려준다.

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
                                "두 칸이 없다 — 체인이 시작된 뒤의 행인데 해시가 비었다"))
            continue

        declared_prev = e.get("prev_hash") or ""
        if declared_prev != prev_hash:
            breaks.append(Break(
                e["id"], PREV_MISMATCH,
                f"prev_hash={declared_prev[:12]}… 인데 앞 행의 hash 는 {prev_hash[:12]}… "
                f"— 앞 행이 지워졌거나 순서가 바뀌었다"))

        expect = digest(prev_hash=declared_prev, record=e.get("record") or {})
        if expect != got_hash:
            breaks.append(Break(
                e["id"], HASH_MISMATCH,
                f"저장된 hash={got_hash[:12]}… 인데 내용에서 나오는 값은 {expect[:12]}… "
                f"— **이 행의 내용이 바뀌었다**"))

        prev_hash = got_hash

    return tuple(breaks)


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

    @property
    def ok(self) -> bool:
        return not self.breaks

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


def _with_chain(payload: Any, *, prev_hash: str, row_hash: str) -> dict:
    """두 칸을 붙인 `data_after`. ★ 옮기는 날 고치는 자리 ②."""
    base = dict(payload) if isinstance(payload, dict) else {}
    base[PREV_KEY] = prev_hash
    base[HASH_KEY] = row_hash
    return base


def _evidence_of(values: dict) -> dict:
    """DB 에서 읽은 한 행 → **해시가 덮는 부분**. 두 칸은 빠진다."""
    rec = {k: values.get(k) for k in HASHED_FIELDS}
    rec["data_after"] = strip_chain(values.get("data_after"))
    return rec


def _last_hash(*, before_id: int) -> str:
    """앞 행의 `hash`. 없으면 `GENESIS` — 이 행이 체인의 첫 행이다."""
    qs = (_rows().filter(id__lt=before_id)
          .exclude(data_after__isnull=True)
          .order_by("-id"))
    try:
        qs = qs.filter(data_after__has_key=HASH_KEY)
    except Exception:                                   # pragma: no cover
        pass
    for values in qs.values("data_after")[:1]:
        _, h = _chain_of(values.get("data_after"))
        if h:
            return h
    return GENESIS


def append_evidence_hash(*, audit_id: int) -> tuple[str, str]:
    """저장된 감사 행 하나를 **체인에 잇는다.** `(prev_hash, hash)` 를 돌려준다.

    ★ 이 함수는 공개 면이 아니다 — `common/audit_writer.write()` 안쪽에서만 불린다.
      체인을 고르는 인자가 없다는 것이 요점이다: 고를 수 없으면 **남의 체인에 붙일 수
      없다**(머리말 「왜 테넌트별 체인이 아닌가」).

    ★ 실패를 삼키지 않는다. 이을 수 없으면 예외가 올라가고 감사 쓰기가 통째로 실패한다 —
      `audit_writer` 머리말의 규약 그대로다. 체인이 조용히 빠진 행은 **나중에 「그때는
      원래 없었다」로 읽히고**, 그 변명이 한 번 통하면 체인 전체의 값이 사라진다.
    """
    from django.db import transaction

    with transaction.atomic():
        values = (_rows().filter(pk=audit_id)
                  .values(*HASHED_FIELDS, "data_after").first())
        if values is None:
            raise ValueError(
                f"감사 행 #{audit_id} 를 못 찾았다 — 체인에 이을 수 없다. "
                f"logger_name 이 {CHAIN_PREFIX!r} 로 시작하지 않는 행은 우리가 쓴 행이 아니다")

        prev_hash = _last_hash(before_id=audit_id)
        record = _evidence_of(values)
        row_hash = digest(prev_hash=prev_hash, record=record)

        updated = _rows().filter(pk=audit_id).update(
            data_after=_with_chain(strip_chain(values.get("data_after")),
                                   prev_hash=prev_hash, row_hash=row_hash))
        if updated != 1:
            raise RuntimeError(
                f"감사 행 #{audit_id} 에 두 칸을 쓰지 못했다(갱신 {updated}행). "
                f"체인 없는 감사 행을 남기지 않는다")
    return prev_hash, row_hash


def chain_entries(*, since: datetime | None = None,
                  until: datetime | None = None,
                  limit: int | None = None) -> list[dict]:
    """검증에 넣을 모양으로 행들을 **id 오름차순**으로 읽는다."""
    qs = _rows()
    if since is not None:
        qs = qs.filter(create_datetime__gte=since)
    if until is not None:
        qs = qs.filter(create_datetime__lt=until)
    qs = qs.order_by("id").values(*HASHED_FIELDS, "data_after")
    if limit:
        qs = qs[:limit]
    out = []
    for values in qs:
        prev_hash, row_hash = _chain_of(values.get("data_after"))
        out.append({"id": values["id"], "record": _evidence_of(values),
                    "prev_hash": prev_hash, "hash": row_hash})
    return out


def verify_chain(*, since: datetime | None = None,
                 until: datetime | None = None) -> ChainReport:
    """체인 전체를 다시 계산해 대조한다. **행 하나가 바뀌면 여기서 잡힌다.**"""
    entries = chain_entries(since=since, until=until)
    breaks = verify_sequence(entries)
    chained = sum(1 for e in entries if e["hash"])
    head = next((e["hash"] for e in reversed(entries) if e["hash"]), "")
    tail_prev = next((e["prev_hash"] for e in entries if e["hash"]), "")
    return ChainReport(total=len(entries), chained=chained, breaks=breaks,
                       head=head, tail_prev=tail_prev)


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

    qs = (_rows().filter(create_datetime__gte=start, create_datetime__lt=end)
          .order_by("-id").values("data_after"))
    for values in qs[:200]:
        _, h = _chain_of(values.get("data_after"))
        if h:
            return h
    return ""


def anchor_line(day: date, anchor: str) -> str:
    """보고서 꼬리에 찍히는 **한 줄**. 모양을 여기서만 만든다 —
    두 곳에서 만들면 종이와 화면이 다른 문자열을 갖게 되고, 그 순간 대조가 불가능해진다.
    """
    if not anchor:
        return f"[LAW-08] {day.isoformat()} 증거 해시 앵커 — 그날 감사 기록 없음"
    return f"[LAW-08] {day.isoformat()} 증거 해시 앵커 SHA-256: {anchor}"


def iter_hashed_fields() -> Iterable[str]:      # pragma: no cover - 읽는 편의
    return HASHED_FIELDS
