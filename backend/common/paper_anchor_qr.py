# -*- coding: utf-8 -*-
"""LAW-08 일일 종이 앵커 **QR 구현 1** — 설계 v1.0 의 `cmp.`/`ref.` 형식을 코드로 세운다.

- 설계: `docs/design/GX-LAW-08_일일종이앵커_QR_설계_v1.0.md` (§ 번호는 그 쪽을 가리킨다)
- 앞 쪽: `docs/design/GX-LAW-08_일일종이앵커_사람절차_v1.0.md`
- 차선 S · 2026-09-21(기계)

한 줄 — **QR 은 증명이 아니라 옮기는 도구다**
---------------------------------------------
사람 칸에는 앵커 **앞 16자**만 적는다. 손으로 64자를 옮기면 반드시 틀리기 때문이다.
QR 이 종이에 실제로 더하는 것은 **나머지 48자 하나뿐**이다. 그 이상은 안 한다.

★ 이 모듈이 **하지 않는 일** — 안 하는 것이 설계의 본체다
---------------------------------------------------------
1. **검증 URL 을 담지 않는다.** `_reject_url_scheme()` 가 payload 에 `http`·`www.`·`://`
   가 한 글자라도 섞이면 **payload 를 만들지 않는다**(§1 · §7②).

   왜인가 — 사유는 둘이고, 둘 다 이 파일이 지켜야 할 것이다:

     ① **원이 닫힌다.** URL 은 우리 서버를 가리킨다. 체인을 통째로 재계산한 기계가
        QR 도 찍고 그 URL 에 「맞습니다」도 답한다. 「코드가 영원히 못 잡는 경우」를
        잡자고 만든 종이가 URL 하나로 다시 그 기계 안으로 들어간다.
     ② **종이는 10년 뒤에 읽힌다 — 그때 도메인은 없다.** 값은 남는다.
        URL 이 죽은 종이는 「읽을 수 없는 증거」가 된다.

2. **판정하지 않는다.** 이 모듈은 「맞음/틀림」을 payload 에 넣지 않는다.
   `compare_with_human_cell()` 은 사람이 종이를 들고 하는 대조를 **거들 뿐**이고,
   칸을 채우고 서명하는 것은 언제나 사람이다(§4-2).

3. **외부에 보내지 않는다.** QR 은 **오프라인 생성**이다(§7③). 외부 QR 생성 API 를
   한 번도 부르지 않는다 — 보내는 순간 그것은 편의가 아니라 유출이다.
   `render_qr_ascii()` 는 로컬 `qrcode` 만 쓰고, 없으면 **회색**(None)이다.

4. **판정기를 빨갛게 만들지 않는다.** QR 생성 실패는 체인 판정의 색을 못 바꾼다(§7⑥).
   섞으면 다음 사람은 빨강을 끄려고 **QR 을 끄거나 대조를 끈다.**

★ `cmp.` 와 `ref.` — **머리 해시 함정을 형식 안에 박았다**
----------------------------------------------------------
`cmp.` = 대조하는 칸 · `ref.` = 참고 칸이고 **대조하지 않는다.**
접두를 관행이 아니라 **형식**에 박은 이유는 하나다 — 다음 사람이 형식만 보고도
머리 해시를 대 보지 않게 하려는 것이다.

  실측(차선 S · 2026-09-20 앵커를 네 번 떴다):

    | 잰 때      | 앵커 앞 16자       | 머리 해시 앞 16자   |
    |-----------|-------------------|--------------------|
    | 턴 Z 오전  | 014cf31d3e94d46b  | 2a10f5d596474534   |
    | 턴 Z 오후  | 014cf31d3e94d46b  | d90b5f405574a34e   |
    | 턴 AA     | 014cf31d3e94d46b  | 12aa35fc3568f56d   |
    | 턴 AB     | 014cf31d3e94d46b  | (아래 판정기 출력)  |

  **앵커는 네 번 다 글자 하나까지 같다. 머리 해시는 잴 때마다 다르다.**
  매일 「다름」이 나는 칸은 매일 나는 빨강이고, 매일 나는 빨강은 아무도 안 본다 —
  그 칸이 생기는 순간 **진짜 빨강도 같이 안 보이게 된다.**

  그래서 `compare_with_human_cell()` 은 `ref.` 칸을 **아예 안 읽는다.**
  읽더라도 「다름」을 못 낸다 — 시험으로 박았다(`test_law08_qr_anchor.py`).

★ 상태는 셋이다 — **못 읽음을 「같음」으로 접지 않는다**
--------------------------------------------------------
`STATE_SAME` / `STATE_DIFFERENT` / `STATE_UNREADABLE`.
QR 이 찢겼거나 번졌거나 리더가 고장 났으면 그것은 **「못 읽음」**이고,
그 줄은 **사람 칸 앞 16자로** 대조한다(§5). 못 읽음을 초록으로 접는 순간
이 절차는 「매일 눌리는 초록」이 되고, 그러면 절차가 아니라 의식이 된다.

  **「QR 과 16자가 다르면 그것이 사건이다」** — 「QR 이 고장났다」가 아니다.
  누가 그 QR 을 만들었는지를 묻는 자리다(§5 · 설계 §2).

★ QR 옆에는 사람이 읽는 16자가 **반드시 나란히** 있어야 한다
-------------------------------------------------------------
QR 만 있는 종이는 **QR 이 거짓말해도 아무도 모른다.** 16자가 옆에 있으면 QR 안의 값이
그 16자와 다른 순간 사람이 그것을 본다 — **QR 은 이렇게 해서 스스로 감시당한다.**
그래서 `printable_block()` 은 **둘을 한 덩어리로만** 낸다. 하나만 내는 갈래가 없다(§7④).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Mapping

#: payload 의 첫 줄. 판이 바뀌면 이 글자가 바뀌고, 옛 종이는 옛 글자로 남는다.
VERSION_LINE = "GX-LAW08 v1"

#: 대조하는 칸의 접두 · 참고 칸의 접두. **형식이 곧 규칙이다**(모듈 머리말).
CMP = "cmp."
REF = "ref."

#: 사람이 종이에 손으로 옮겨 적는 길이. 절차의 바닥은 **언제나 16자**다(설계 §5).
HUMAN_LEN = 16

#: sha256 한 벌의 길이.
DIGEST_LEN = 64

#: 대조 상태 셋. **못 읽음은 같음이 아니다.**
STATE_SAME = "같음"
STATE_DIFFERENT = "다름"
STATE_UNREADABLE = "못 읽음"
STATES = (STATE_SAME, STATE_DIFFERENT, STATE_UNREADABLE)

#: ★ payload 에 있으면 **payload 를 안 만든다.** 카메라가 「열기」를 권하는 순간
#:   탭 한 번이 대조를 대신하고, 대조 칸은 매일 초록으로 채워진다(설계 §1-2).
#:   소문자로 낮춘 뒤 검사한다 — `HTTP://` 도 같은 것이다.
URL_MARKERS = ("http", "www.", "://", "ftp:", "mailto:")

#: `cmp.` 칸 가운데 **반드시 있어야 하는 것들.** 하나라도 없으면 그 QR 은 무효다.
REQUIRED_CMP = ("for", "anchor", "prev", "prev_anchor", "rows", "chain", "gaps")


class PayloadError(ValueError):
    """payload 를 **만들 수 없다.** 만들어서 내보내는 것보다 안 만드는 것이 낫다."""


def _is_hex_digest(value: str) -> bool:
    if len(value) != DIGEST_LEN:
        return False
    return all(c in "0123456789abcdef" for c in value.lower())


def human_cell(anchor: str) -> str:
    """사람 칸에 손으로 적는 **앞 16자**.

    ★ 이 함수가 QR 형식과 **같은 한 벌**에서 나와야 한다. 두 벌을 두면 종이의 16자와
      QR 안 64자의 앞 16자가 어느 날 갈라지고, 갈라진 날 그것은 **사건으로 읽힌다** —
      실제로는 아무도 안 고쳤는데도 그렇다.
    """
    raw = (anchor or "").strip().lower()
    if not _is_hex_digest(raw):
        raise PayloadError(
            f"앵커가 sha256 64자가 아니다(길이 {len(raw)}). 16자를 잘라내지 않는다 — "
            f"자르면 틀린 값이 종이에 박힌다")
    return raw[:HUMAN_LEN]


def _reject_url_scheme(text: str, where: str) -> None:
    """**설계 §7② 를 코드로.** 한 글자라도 있으면 멈춘다."""
    low = text.lower()
    for marker in URL_MARKERS:
        if marker in low:
            raise PayloadError(
                f"{where} 에 URL 스킴 문자열 «{marker}» 가 있다 — QR 에 링크를 담지 않는다. "
                f"담는 순간 뚫린 기계가 QR 도 찍고 「맞습니다」도 답한다(설계 §1)")


def _clean_value(value, where: str) -> str:
    """한 칸의 값. **줄바꿈·`=` 를 못 넣는다** — 넣으면 칸 하나가 두 칸으로 읽힌다."""
    text = "" if value is None else str(value)
    text = text.strip()
    if "\n" in text or "\r" in text:
        raise PayloadError(f"{where} 에 줄바꿈이 있다 — 한 칸은 한 줄이다")
    if "=" in text:
        raise PayloadError(f"{where} 에 «=» 가 있다 — 칸 하나가 두 칸으로 읽힌다")
    _reject_url_scheme(text, where)
    return text


def build_payload(
    *,
    for_day: date,
    anchor: str,
    prev_day: date,
    prev_anchor: str,
    rows: int,
    chain: int,
    gaps: int,
    head: str = "",
    exit_code: int = 0,
    read_at: str = "",
    by: str = "",
) -> str:
    """QR 하나에 담을 **대장 한 줄**. 평문 ASCII · 줄바꿈으로 나눈다(설계 §2).

    `cmp.*` 는 **언제나 전부** 나온다 — 빠진 칸이 「없는 것」으로 읽히면 안 된다.
    `ref.by` 는 값이 있을 때만 나온다: **없는 당번 이름을 지어내지 않는다.**
    (수행자의 진짜 흔적은 종이 위의 **서명**이고, 그것은 저장소가 못 만든다.)

    `cmp.for` 와 `cmp.prev` 가 **하루 차이가 아니면 만들지 않는다** — 연휴에 줄을 몰아
    적다가 하루를 건너뛰면 여기서 걸린다(설계 §2 · §5).
    """
    if not isinstance(for_day, date) or not isinstance(prev_day, date):
        raise PayloadError("날짜 두 칸은 date 여야 한다")
    if for_day - prev_day != timedelta(days=1):
        raise PayloadError(
            f"cmp.for({for_day}) 와 cmp.prev({prev_day}) 가 하루 차이가 아니다 — "
            f"하루도 건너뛰지 않는다(설계 §2)")

    anchor_h = human_cell(anchor)           # 64자가 아니면 여기서 멈춘다
    prev_h = human_cell(prev_anchor)        # 어제 칸도 같은 잣대로 잰다
    del anchor_h, prev_h                    # 검사만 하고 값은 아래에서 통째로 쓴다

    for label, number in (("cmp.rows", rows), ("cmp.chain", chain), ("cmp.gaps", gaps)):
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise PayloadError(f"{label} 는 0 이상 정수여야 한다 (받은 값: {number!r})")

    lines = [
        VERSION_LINE,
        f"{CMP}for={for_day.isoformat()}",
        f"{CMP}anchor={anchor.strip().lower()}",
        f"{CMP}prev={prev_day.isoformat()}",
        f"{CMP}prev_anchor={prev_anchor.strip().lower()}",
        f"{CMP}rows={rows}",
        f"{CMP}chain={chain}",
        f"{CMP}gaps={gaps}",
    ]

    #: ★ 참고 칸. **대조 금지**다. `ref.head` 는 잴 때마다 달라지는 값이고,
    #:   어제와 달라도 **아무것도 하지 않는다**(설계 §5 마지막 줄).
    head_clean = _clean_value(head, "ref.head")
    if head_clean and not _is_hex_digest(head_clean):
        raise PayloadError("ref.head 는 sha256 64자이거나 비어 있어야 한다")
    lines.append(f"{REF}head={head_clean.lower()}")
    lines.append(f"{REF}exit={int(exit_code)}")
    read_at_clean = _clean_value(read_at, "ref.read_at")
    if read_at_clean:
        lines.append(f"{REF}read_at={read_at_clean}")
    by_clean = _clean_value(by, "ref.by")
    if by_clean:
        lines.append(f"{REF}by={by_clean}")

    payload = "\n".join(lines)
    #: 마지막 문. 조립하다 섞인 것이 있으면 **여기서 멈춘다.**
    _reject_url_scheme(payload, "payload 전체")
    if not payload.isascii():
        raise PayloadError("payload 는 평문 ASCII 다 — 10년 뒤 아무 리더로도 읽혀야 한다")
    return payload


@dataclass(frozen=True)
class Payload:
    """읽어 들인 QR 한 장. **`cmp` 와 `ref` 를 갈라서 들고 있다.**

    가르는 자리를 자료 구조에 둔 이유: 부르는 쪽이 `ref` 를 대조에 쓰려면
    **일부러** 그래야 하게 만든다. 한 사전에 섞어 두면 다음 사람이 반드시 섞어 쓴다.
    """

    version: str
    cmp: Mapping[str, str] = field(default_factory=dict)
    ref: Mapping[str, str] = field(default_factory=dict)

    @property
    def anchor(self) -> str:
        return self.cmp.get("anchor", "")

    @property
    def prev_anchor(self) -> str:
        return self.cmp.get("prev_anchor", "")

    def human_sixteen(self) -> str:
        """이 QR 이 주장하는 **앞 16자**. 종이의 사람 칸과 대 볼 값이다."""
        return self.anchor[:HUMAN_LEN]

    def days_are_consecutive(self) -> bool:
        try:
            a = date.fromisoformat(self.cmp["for"])
            b = date.fromisoformat(self.cmp["prev"])
        except (KeyError, ValueError):
            return False
        return a - b == timedelta(days=1)

    def is_well_formed(self) -> tuple[bool, str]:
        if self.version != VERSION_LINE:
            return False, f"첫 줄이 «{VERSION_LINE}» 가 아니다"
        missing = [k for k in REQUIRED_CMP if k not in self.cmp]
        if missing:
            return False, "cmp 칸이 빠졌다: " + ", ".join(missing)
        if not _is_hex_digest(self.anchor):
            return False, "cmp.anchor 가 sha256 64자가 아니다"
        if not _is_hex_digest(self.prev_anchor):
            return False, "cmp.prev_anchor 가 sha256 64자가 아니다"
        if not self.days_are_consecutive():
            return False, "cmp.for 와 cmp.prev 가 하루 차이가 아니다"
        return True, ""


def parse_payload(text: str | None) -> Payload | None:
    """QR 에서 읽어 낸 글자를 판다. **못 읽으면 None** 이고, None 은 「같음」이 아니다.

    ★ `ref.` 줄도 **읽기는 한다**(사람이 종이에서 보는 값이므로). 그러나 `ref` 에
      담기고, 아래 `compare_with_human_cell()` 은 `ref` 를 **쳐다보지 않는다.**
      「읽지 않는다」를 「담지 않는다」로 구현하면, 다음 사람이 담기만 하면 대조에 쓴다.
    """
    if text is None:
        return None
    lines = [ln.strip() for ln in str(text).replace("\r\n", "\n").split("\n")]
    lines = [ln for ln in lines if ln]
    if not lines:
        return None
    version = lines[0]
    cmp_cells: dict[str, str] = {}
    ref_cells: dict[str, str] = {}
    for line in lines[1:]:
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key.startswith(CMP):
            cmp_cells[key[len(CMP):]] = value
        elif key.startswith(REF):
            ref_cells[key[len(REF):]] = value
        #: 접두가 없는 줄은 **버린다.** 「어느 구역인지 모르는 칸」을 대조에 쓸 수는 없다.
    return Payload(version=version, cmp=cmp_cells, ref=ref_cells)


def compare_with_human_cell(qr_text: str | None, human_sixteen: str) -> tuple[str, str]:
    """★ 이 모듈의 심장 — **QR 과 종이의 16자를 댄다.** 상태는 셋이다.

    반환: `(상태, 사람이 읽을 사유)`.

    - QR 이 없거나·안 읽히거나·모양이 틀렸다 → **`STATE_UNREADABLE`**.
      **절대 `STATE_SAME` 으로 접지 않는다.** 그 줄은 사람 칸 16자로 대조한다(설계 §5).
    - 16자가 같다 → `STATE_SAME`.
    - 16자가 다르다 → **`STATE_DIFFERENT` = 사건**(설계 §5). 「QR 이 고장났다」가 아니다.

    ★ `ref.*` 는 **한 칸도 안 본다.** 머리 해시는 잴 때마다 달라지고,
      그것을 대조에 쓰면 매일 「다름」이 난다 — 매일 나는 빨강은 아무도 안 본다.
    """
    want = (human_sixteen or "").strip().lower()
    if len(want) != HUMAN_LEN or not all(c in "0123456789abcdef" for c in want):
        return STATE_UNREADABLE, (
            f"종이의 사람 칸이 16자 16진수가 아니다(길이 {len(want)}) — "
            f"대조할 것이 없다. 「같음」으로 접지 않는다")

    payload = parse_payload(qr_text)
    if payload is None:
        return STATE_UNREADABLE, "QR 을 못 읽었다 — 사람 칸 16자로 대조한다(설계 §5)"
    ok, why = payload.is_well_formed()
    if not ok:
        return STATE_UNREADABLE, f"QR 모양이 형식과 다르다: {why}"

    got = payload.human_sixteen().lower()
    if got == want:
        return STATE_SAME, f"QR 앞 16자 = 종이 16자 = {want}"
    return STATE_DIFFERENT, (
        f"★ 사건 — QR 은 «{got}» 인데 종이는 «{want}» 다. 두 값을 여백에 둘 다 적고 "
        f"서명한다. 「QR 이 고장났다」가 아니라 **누가 이 QR 을 만들었는가**를 묻는다")


def compare_to_yesterday(today_qr: str | None, yesterday_qr: str | None) -> tuple[str, str]:
    """설계 §3 ① — **매일 만나는 자리.** 오늘 QR 의 `cmp.prev_anchor` ↔ 어제 QR 의 `cmp.anchor`.

    어제 종이는 다른 건물 잠긴 서랍에 있는 **물건**이다. 저장소는 그것을 못 고친다.
    체인을 통째로 재계산한 기계도 **어제 종이는 못 속인다** — 여기가 이 절차의 심장이다.
    """
    today = parse_payload(today_qr)
    yday = parse_payload(yesterday_qr)
    if today is None or yday is None:
        return STATE_UNREADABLE, "두 QR 가운데 하나를 못 읽었다 — 16자 대조로 내려간다"
    for label, p in (("오늘", today), ("어제", yday)):
        ok, why = p.is_well_formed()
        if not ok:
            return STATE_UNREADABLE, f"{label} QR 모양이 형식과 다르다: {why}"
    if today.cmp.get("prev") != yday.cmp.get("for"):
        return STATE_DIFFERENT, (
            f"★ 사건 — 오늘 QR 의 cmp.prev({today.cmp.get('prev')}) 가 "
            f"어제 QR 의 cmp.for({yday.cmp.get('for')}) 와 다르다. 줄이 건너뛰었다")
    if today.prev_anchor == yday.anchor:
        return STATE_SAME, f"오늘 cmp.prev_anchor = 어제 cmp.anchor = {yday.anchor[:HUMAN_LEN]}…"
    return STATE_DIFFERENT, (
        f"★ 사건 — 오늘이 기억하는 어제는 «{today.prev_anchor[:HUMAN_LEN]}…» 인데 "
        f"어제 종이는 «{yday.anchor[:HUMAN_LEN]}…» 다")


def render_qr_ascii(payload: str) -> str | None:
    """QR 을 **오프라인으로** 그린다. 못 그리면 **None(회색)** 이고, 예외를 안 던진다.

    ★ 설계 §7③ · §7⑥ 둘을 한 함수에 박았다:
      · 외부 QR 생성 API 를 **한 번도 안 부른다.** 로컬 `qrcode` 만 쓴다 —
        앵커 값을 남의 서버에 보내는 순간 그것은 편의가 아니라 **유출**이다.
      · **실패해도 빨강을 안 낸다.** QR 실패가 체인 판정을 빨갛게 만들면,
        다음 사람은 빨강을 끄려고 QR 을 끄거나 **대조를 끈다.** 두 색은 섞지 않는다.

    오류정정은 **Q(25 %)** 다 — 종이는 서랍에서 몇 년을 난다. 아낄 자리가 아니다.
    """
    #: ★ [실측 2026-09-21 · 턴 AB · 이 시험이 잡았다] `qrcode` 는 무엇을 줘도 받는다 —
    #:   `None` 을 주면 **글자 「None」을 담은 QR 을 그려 낸다.** 그런 QR 은 리더에
    #:   읽히고, 읽힌 값은 16자와 다르니 **사건으로 읽힌다.** 없는 값은 없는 것이지
    #:   「None」이 아니다. 그래서 문을 여기서 먼저 닫는다.
    if not isinstance(payload, str) or not payload.strip():
        return None
    try:
        import qrcode                                   # noqa: PLC0415 — 없어도 서야 한다
        from qrcode.constants import ERROR_CORRECT_Q    # noqa: PLC0415
    except Exception:                                   # noqa: BLE001 — 회색이지 빨강이 아니다
        return None
    try:
        code = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=2)
        code.add_data(payload)
        code.make(fit=True)
        rows = code.get_matrix()
    except Exception:                                   # noqa: BLE001
        return None
    #: 반 칸 블록으로 두 줄을 한 줄에 겹쳐 그린다 — 종이 폭에 들어가게.
    out: list[str] = []
    for i in range(0, len(rows), 2):
        top = rows[i]
        bottom = rows[i + 1] if i + 1 < len(rows) else [False] * len(top)
        line = []
        for t, b in zip(top, bottom):
            line.append({(True, True): "█", (True, False): "▀",
                         (False, True): "▄", (False, False): " "}[(bool(t), bool(b))])
        out.append("".join(line))
    return "\n".join(out)


def qr_unavailable_note() -> str:
    """QR 을 못 그렸을 때 **종이에 적는 말.** 설계 §5 첫 줄 그대로다."""
    return ("[QR 없음 — 이 자리에 QR 을 못 그렸다] 사유를 적고 **나머지 열한 칸을 손으로 "
            "채운다. 그 줄은 유효하다.** 사건이 아니다(설계 §5)")


def printable_block(payload: str, *, qr: str | None = None) -> str:
    """★ 종이에 나가는 **한 덩어리.** QR 과 사람 16자를 **둘 중 하나만 내는 갈래가 없다**(§7④).

    QR 만 있는 종이는 **QR 이 거짓말해도 아무도 모른다.** 16자가 나란히 있으면
    QR 안의 값이 그 16자와 다른 순간 사람이 그것을 본다 —
    **QR 은 이렇게 해서 스스로 감시당한다.**
    """
    parsed = parse_payload(payload)
    if parsed is None:
        raise PayloadError("payload 를 못 읽었다 — 종이에 못 내보낸다")
    ok, why = parsed.is_well_formed()
    if not ok:
        raise PayloadError(f"payload 가 형식과 다르다: {why} — 종이에 못 내보낸다")

    drawn = render_qr_ascii(payload) if qr is None else qr
    lines = ["[LAW-08] 일일 종이 앵커 — 열두 번째 칸(QR)",
             "",
             drawn if drawn else qr_unavailable_note(),
             "",
             f"사람 칸 앞 16자 : {parsed.human_sixteen()}",
             f"그날(cmp.for)   : {parsed.cmp.get('for', '')}",
             f"어제(cmp.prev)  : {parsed.cmp.get('prev', '')}",
             "",
             "─ QR 안 글자(평문) ────────────────────────────────",
             payload,
             "───────────────────────────────────────────────────",
             "",
             "· 상태는 셋이다 — 같음 / 다름 / **못 읽음**. 못 읽음을 「같음」으로 접지 않는다.",
             "· **QR 과 위 16자가 다르면 그것이 사건이다**(절차서 §5). 두 값을 여백에 다 적고 서명한다.",
             "· `ref.` 로 시작하는 줄은 **대조하지 않는다** — 머리 해시는 잴 때마다 달라진다.",
             "· QR 이 안 읽히면 **사람 칸 16자로 대조한다.** 절차의 바닥은 언제나 16자다.",
             "· 서명 없는 줄은 QR 이 있어도 **무효**다. QR 은 서명을 대신하지 않는다."]
    return "\n".join(lines)
