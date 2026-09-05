# -*- coding: utf-8 -*-
"""SEC-16 — 나가는 웹훅의 **서명·재시도 규약**. 문이 서기 전에 규약을 먼저 짓는다.

intended_caller: UX-19 웹훅 CAP 1.2 · 턴 C (2026-09-05)
--------------------------------------------------------
★ 이 줄은 장식이 아니라 **기한**이다 (P-42 · 2026-09-05).
  이 모듈의 함수 셋(`attempts_from` · `giveup_record` · `outbound_headers`)은
  **부르는 곳 없이 태어났다.** `dormant` 게이트가 그것을 빨강으로 잡고 있고, **그 빨강이
  옳다** — D-377 은 「새로 만드는 것은 켜진 상태로 태어나야 한다」이다.
  기준선(`D-377/dormant_baseline.txt`)에 **넣지 않았다**: 그 파일은 「줄어들기만 한다」고
  스스로 적고, 거기 이름을 더하는 것은 **「규약을 지었다」와 「규약이 쓰인다」의 구별을
  지우는 일**이다 — 이 저장소가 착시 ⑨ 라고 부르는 바로 그것(**함수는 문이 아니다**).

  규칙(P-42): **규약은 부르는 곳과 같은 턴에 태어난다.** 다른 턴에 태어나면 그 사이의
  dormant 빨강이 옳다. 위의 `intended_caller` 가 가리키는 턴이 지나도 안 불리면
  이 모듈은 **삭제 후보 목록**으로 간다(삭제는 대표 승인).

왜 문보다 규약이 먼저인가
-------------------------
    나가는 웹훅은 아직 **0개**다 — 문은 UX-19(CAP 1.2)가 낸다.
    그런데 문이 먼저 서면 규약은 **문에 맞춰** 지어진다. 그때 규약은 「지금 보내는 모양」의
    다른 이름이 되고, 규약이 아니라 기록이 된다.

    · **서명 없는 웹훅은 누구나 보낼 수 있는 경보다.** 우리 이름으로 가짜 경보를 낼 수 있다.
    · **재시도 규약이 없으면** 상대가 한 번 죽었을 때 그 경보는 **조용히 사라진다.**
      조용히 사라지는 것이 이 제품에서 가장 나쁜 실패다 — 아무도 모르기 때문이다.

이 모듈이 강제하는 셋 (정본 `ga_readiness.yaml` SEC-16 의 닫는 조건 그대로)
--------------------------------------------------------------------------
    ① **서명 불일치 거절**            — `verify()` 가 거절 사유를 이름으로 돌려준다
    ② **5회 뒤 포기 기록**            — `RetryPolicy` 가 5회에서 멈추고 `giveup_record()` 를 남긴다
    ③ **스키마 버전 헤더 부재 거절**  — 헤더가 없거나 모르는 판이면 서명을 보기도 전에 거절

★ 함정 하나 (세종 §4-4 · P-37) — **새 인증 경로를 만들지 않는다**
    웹훅은 **F-05 구독 등록 위**에 선다. 구독은 로그인한 계정이 등록하고, 서명키는 그
    구독에 매인다. 무계정 링크(「이 URL 을 아는 사람은 누구나」)를 만들지 않는다 —
    그 순간 URL 하나가 계정이 되고, 그것은 우리가 관리하지 않는 계정이다.
    상대가 우리에게 되쏘는 인바운드 콜백도 **익명이 아니다** — 인바운드 키가 필수다(P-37).

    그래서 이 모듈에는 **라우트가 없다.** 순수 함수와 정책값뿐이다. 문은 UX-19 가 낸다.

★ 함정 둘 — **서명은 본문만 덮으면 안 된다**
    본문만 서명하면 같은 본문을 **다시 보내는 것**(재생 공격)을 막을 수 없다. 그래서
    서명 대상은 `타임스탬프 + 개행 + 스키마판 + 개행 + 본문` 이고, 검증기는 타임스탬프가
    창 밖이면 서명이 맞아도 거절한다.

★ 함정 셋 — **`==` 로 서명을 비교하지 않는다**
    문자열 비교는 첫 다른 글자에서 끝나 시간이 새어 나간다(타이밍 공격).
    `hmac.compare_digest` 만 쓴다. 이 파일에 `sig == expected` 가 나타나면
    `scripts/verify_webhook_contract.py` 가 그것을 잡는다.

★ 함정 넷 — **재시도가 무한이면 재시도가 아니라 폭주다**
    상대가 오래 죽어 있으면 우리가 상대를 때리는 쪽이 된다. 5회에서 멈추고,
    멈춘 사실을 **행으로 남긴다.** 남기지 않으면 「조용히 사라짐」과 같아진다.

이 저장소에서 지금 무엇이 있고 무엇이 없나 [실측 2026-09-05]
------------------------------------------------------------
    **구독 모델도 구독 등록 라우트도 아직 없다.** `Subscription` 클래스 0건이고,
    F-05 진입면 33건(`tests/test_f05_event_api.py` 의 `EVENT_ENTRY_SURFACE`)에
    구독 경로는 한 건도 없다. 있는 것은 **이름뿐인 자리** 셋이다:

      · `kernels/k1_event/services.py` `subscribe(*, scope, webhook_url, filters,
        signing_key_ref)` → `NotImplementedYet`. 그 독스트링이 **선행 셋**을 적어 뒀다:
        ① 서명키 보관처 ② 재시도·지수 백오프와 타임아웃 ③ 구독의 테넌트 소유 판정.
        **이 파일이 ②를 답한다** — 그리고 ①의 「무엇을 서명하는가」를 답한다.
      · `kernels/k2_notify/channels.py` `UNAVAILABLE["webhook"]` — 어댑터 없음
      · `stream_monitors/models.py` `DeliveryRecord.Channel.WEBHOOK` — 열거값만

    **포기 행이 앉을 자리는 이미 있다**: `DeliveryRecord` 에 `retry_count` ·
    `succeeded` · `failure_reason` · `sent_at`(실패면 None) 칸이 이미 있다.
    새 모델을 만들 이유가 아직 없다 — `giveup_record()` 가 그 칸들에 맞는 사전을 낸다.

    **나가는 호출의 표준 자리는 `common/external_http.py`** 다(W0-17 · D-212).
    타임아웃 숫자를 호출부에 적지 않는다 — 값은 `settings.EXTERNAL_HTTP_TIMEOUT` 한 곳.
    ★ 그 모듈에는 **재시도가 없다.** 저장소 전체에 지수 백오프 구현이 0건이었다 —
      `RetryPolicy` 가 그 첫 자리다.

    `X-GX-Schema` 는 코드에 **0건**이었다(PRD v2.5 §6 한 줄에만 있었다).
    이 파일이 그 이름의 첫 구현이다.

쓰는 쪽 (UX-19 가 문을 낼 때)
------------------------------
    headers = outbound_headers(secret, body_bytes)          # 보낼 때
    ok, why = verify(secret, body_bytes, request_headers)   # 받을 때 / 상대가 검증할 때
    for attempt, delay in RetryPolicy().schedule(): ...     # 재시도
    row = giveup_record(subscription_id, event_id, ...)     # 5회 뒤

시험: `backend/tests/test_s_webhook_contract.py` · 판정기: `scripts/verify_webhook_contract.py`
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Iterable, Mapping

# ═══════════════════════════════════════════════════════════════════════════
# 규약의 이름들 — **한 곳에서만 정한다** (D-212 · 판정식 복제 금지)
# ═══════════════════════════════════════════════════════════════════════════

#: 스키마 버전 헤더. PRD v2.5 §6 의 `X-GX-Schema: 1` 그대로.
SCHEMA_HEADER = "X-GX-Schema"

#: 지금 우리가 내는 판. **받는 쪽은 모르는 판을 거절한다** — 조용히 추측하지 않는다.
SCHEMA_VERSION = "1"

#: 우리가 낼 수 있고 받아 줄 수 있는 판 전부. 새 판이 생기면 여기 이름으로 더한다.
SUPPORTED_SCHEMA_VERSIONS = frozenset({"1"})

#: 서명 헤더. 값 모양은 `sha256=<소문자 16진>`. 알고리즘을 값에 적는 이유는
#: 나중에 알고리즘을 바꿀 때 **받는 쪽이 무엇으로 검증할지 알 수 있게** 하기 위해서다.
SIGNATURE_HEADER = "X-GX-Signature"

#: 서명 앞에 붙는 알고리즘 표식.
SIGNATURE_PREFIX = "sha256="

#: 서명이 덮는 타임스탬프(유닉스 초). 재생 공격을 막는다.
TIMESTAMP_HEADER = "X-GX-Timestamp"

#: 타임스탬프 허용 창(초). 이보다 오래된/미래인 것은 서명이 맞아도 거절한다.
#: 5분 — 시계 어긋남은 견디고 녹화된 요청은 못 쓰게 하는 자리.
TIMESTAMP_TOLERANCE_SECONDS = 300

#: 이벤트 식별자 헤더. 상대가 **같은 것을 두 번 처리하지 않게** 한다 —
#: 재시도가 있는 규약에서 중복 도착은 결함이 아니라 정상이다.
EVENT_ID_HEADER = "X-GX-Event-Id"


# ═══════════════════════════════════════════════════════════════════════════
# 거절 사유 — **이름으로 돌려준다** (D-301: 「거절했다」만으로는 못 고친다)
# ═══════════════════════════════════════════════════════════════════════════

REJECT_NO_SCHEMA = "schema_header_missing"        # 스키마 버전 헤더가 없다
REJECT_BAD_SCHEMA = "schema_version_unsupported"  # 모르는 판이다
REJECT_NO_SIGNATURE = "signature_missing"         # 서명 헤더가 없다
REJECT_BAD_SIGNATURE_FORM = "signature_malformed"  # `sha256=…` 모양이 아니다
REJECT_SIGNATURE_MISMATCH = "signature_mismatch"  # 서명이 다르다
REJECT_NO_TIMESTAMP = "timestamp_missing"
REJECT_BAD_TIMESTAMP = "timestamp_malformed"
REJECT_STALE_TIMESTAMP = "timestamp_out_of_window"  # 재생으로 본다
REJECT_NO_SECRET = "secret_missing"               # 우리 쪽에 키가 없다 — 통과가 아니다


def _canonical(timestamp: str, schema: str, body: bytes) -> bytes:
    """서명이 덮는 것. **본문만 덮지 않는다** (함정 둘).

    `<timestamp>\\n<schema>\\n<body>` — 개행으로 가른다. 이어 붙이기만 하면
    `("12", "34")` 와 `("1", "234")` 가 같은 문자열이 된다(경계 모호성).
    """
    head = ("%s\n%s\n" % (timestamp, schema)).encode("utf-8")
    return head + body


def sign(secret: str | bytes, body: bytes, timestamp: str,
         schema: str = SCHEMA_VERSION) -> str:
    """서명 값을 만든다. 돌려주는 모양은 `sha256=<소문자 16진>`."""
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not secret:
        raise ValueError("서명키가 비었다 — 키 없이 서명한 것은 서명이 아니다")
    digest = hmac.new(secret, _canonical(timestamp, schema, body), hashlib.sha256)
    return SIGNATURE_PREFIX + digest.hexdigest()


def outbound_headers(secret: str | bytes, body: bytes, *, event_id: str = "",
                     timestamp: str | None = None,
                     schema: str = SCHEMA_VERSION) -> dict[str, str]:
    """보낼 때 붙이는 헤더 전부. **여기 없는 헤더는 규약이 아니다.**"""
    ts = timestamp if timestamp is not None else str(int(time.time()))
    headers = {
        SCHEMA_HEADER: schema,
        TIMESTAMP_HEADER: ts,
        SIGNATURE_HEADER: sign(secret, body, ts, schema),
    }
    if event_id:
        headers[EVENT_ID_HEADER] = event_id
    return headers


def _get(headers: Mapping[str, str], name: str) -> str:
    """헤더를 대소문자 가리지 않고 읽는다. HTTP 헤더 이름은 대소문자를 안 가린다 —
    가리는 것으로 읽으면 상대의 라이브러리에 따라 **우리 규약이 갈린다.**"""
    if name in headers:
        return headers[name] or ""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value or ""
        # Django 의 `request.META` 모양(`HTTP_X_GX_SCHEMA`)도 같은 이름으로 읽는다.
        if key.lower().replace("http_", "").replace("_", "-") == lowered:
            return value or ""
    return ""


def verify(secret: str | bytes, body: bytes, headers: Mapping[str, str], *,
           now: float | None = None,
           tolerance: int = TIMESTAMP_TOLERANCE_SECONDS) -> tuple[bool, str]:
    """받은 웹훅이 우리 규약을 지켰는가. `(통과?, 사유)` — 통과면 사유는 빈 문자열.

    ★ **순서가 규약이다.** 스키마 판을 서명보다 **먼저** 본다 — 모르는 판의 본문은
      우리가 무엇을 서명 대상으로 삼아야 할지조차 모르는 본문이다. 서명부터 보면
      「모르는 판인데 서명은 맞다」는 통과 아닌 통과가 생긴다.
    """
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not secret:
        # 우리 쪽에 키가 없다. **없으면 열어 주는 것이 아니라 닫는다** —
        # 「키가 아직 없어서 통과시켰다」가 정확히 사고가 나는 자리다.
        return False, REJECT_NO_SECRET

    # ③ 스키마 버전 헤더 부재 거절
    schema = _get(headers, SCHEMA_HEADER).strip()
    if not schema:
        return False, REJECT_NO_SCHEMA
    if schema not in SUPPORTED_SCHEMA_VERSIONS:
        return False, REJECT_BAD_SCHEMA

    raw_ts = _get(headers, TIMESTAMP_HEADER).strip()
    if not raw_ts:
        return False, REJECT_NO_TIMESTAMP
    try:
        ts = int(raw_ts)
    except ValueError:
        return False, REJECT_BAD_TIMESTAMP
    current = time.time() if now is None else now
    if abs(current - ts) > tolerance:
        return False, REJECT_STALE_TIMESTAMP

    # ① 서명 불일치 거절
    given = _get(headers, SIGNATURE_HEADER).strip()
    if not given:
        return False, REJECT_NO_SIGNATURE
    if not given.startswith(SIGNATURE_PREFIX):
        return False, REJECT_BAD_SIGNATURE_FORM
    expected = sign(secret, body, raw_ts, schema)
    # ★ 함정 셋 — 상수시간 비교. `==` 를 쓰면 판정기가 잡는다.
    if not hmac.compare_digest(given, expected):
        return False, REJECT_SIGNATURE_MISMATCH
    return True, ""


# ═══════════════════════════════════════════════════════════════════════════
# ② 재시도 — 5회 지수 백오프, 그리고 **포기를 기록한다**
# ═══════════════════════════════════════════════════════════════════════════

#: 정본이 정한 수. 늘리려면 정본을 고쳐라 — 여기서 조용히 늘리지 않는다.
MAX_ATTEMPTS = 5

#: 첫 재시도까지의 대기(초). 이후 2배씩.
BASE_DELAY_SECONDS = 1.0

#: 지수가 커져도 여기서 멈춘다. 없으면 마지막 대기가 사람의 인내를 넘는다.
MAX_DELAY_SECONDS = 60.0

#: 다시 보내 볼 값어치가 있는 상태들. **4xx 는 다시 보내도 같은 답이 온다** —
#: 재시도는 「상대가 잠깐 죽었다」를 위한 것이지 「우리가 틀렸다」를 위한 것이 아니다.
#: 429(과부하)와 408(시간 초과)만 4xx 중 예외다.
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """지수 백오프 5회. **정책은 값이지 코드가 아니다** — 시험이 값을 읽어 못박는다."""

    max_attempts: int = MAX_ATTEMPTS
    base_delay: float = BASE_DELAY_SECONDS
    max_delay: float = MAX_DELAY_SECONDS
    retryable_status: frozenset = field(default=RETRYABLE_STATUS)

    def delay_for(self, attempt: int) -> float:
        """`attempt` 번째 시도 **뒤** 얼마나 기다리는가 (1부터 센다)."""
        if attempt < 1:
            raise ValueError("시도 번호는 1부터다")
        return min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)

    def schedule(self) -> list[tuple[int, float]]:
        """`(시도번호, 그 뒤 대기초)` 전체. 마지막 시도 뒤에는 **대기가 없다** —
        기다릴 다음 시도가 없기 때문이다. 거기서 포기 기록이 나간다."""
        out: list[tuple[int, float]] = []
        for attempt in range(1, self.max_attempts + 1):
            out.append((attempt, 0.0 if attempt == self.max_attempts
                        else self.delay_for(attempt)))
        return out

    def should_retry(self, attempt: int, status: int | None) -> bool:
        """다시 보내는가.

        `status is None` 은 **응답을 못 받았다**(연결 실패·타임아웃)는 뜻이고,
        그것은 재시도할 자리다 — 상대가 답을 안 한 것과 답을 거절한 것은 다르다.
        """
        if attempt >= self.max_attempts:
            return False
        if status is None:
            return True
        return status in self.retryable_status

    def total_wait(self) -> float:
        """5회를 다 쓰면 몇 초가 지나는가. 보고서와 화면이 이 수를 인용한다."""
        return sum(delay for _, delay in self.schedule())


#: 포기 행의 갈래. **「실패」 한 낱말로 뭉치지 않는다** — 고치는 사람이 달라진다.
GIVEUP_EXHAUSTED = "attempts_exhausted"    # 5회를 다 쓰고도 못 갔다 (상대가 죽어 있다)
GIVEUP_REJECTED = "rejected_by_receiver"   # 상대가 4xx 로 거절했다 (규약이 안 맞는다)


def giveup_record(*, subscription_id, event_id: str, attempts: int,
                  last_status: int | None, last_error: str = "",
                  reason: str = GIVEUP_EXHAUSTED,
                  waited_seconds: float | None = None) -> dict:
    """**포기했다는 사실을 행으로 남긴다.**

    ★ 이 함수가 SEC-16 의 절반이다. 서명은 「가짜를 막는 것」이고 이 행은
      **「조용히 사라지는 것을 막는 것」**이다. 5회를 다 쓰고 못 간 경보가 아무 자국도
      남기지 않으면, 상대는 못 받았고 우리는 보냈다고 믿는다 — 둘 다 모르는 채로.

    행 자체를 만들 뿐 저장하지 않는다. 어디에 저장할지는 문(UX-19)이 정한다 —
    규약이 저장소를 고르면 규약이 저장소에 매인다.
    """
    if attempts < 1:
        raise ValueError("포기 기록에 시도 0회는 없다 — 보내지 않은 것과 못 보낸 것은 다르다")
    return {
        "subscription_id": subscription_id,
        "event_id": event_id,
        "attempts": attempts,
        "max_attempts": MAX_ATTEMPTS,
        "last_status": last_status,
        "last_error": last_error,
        "reason": reason,
        "waited_seconds": (RetryPolicy().total_wait() if waited_seconds is None
                           else waited_seconds),
        "schema_version": SCHEMA_VERSION,
        "gave_up_at": time.time(),
    }


def attempts_from(policy: RetryPolicy, statuses: Iterable[int | None]) -> int:
    """상대가 이 상태들을 차례로 돌려줬을 때 **몇 번 보냈는가.**

    시험이 「5회 뒤 포기」를 셈으로 못박기 위해 쓴다 — 실제 sleep 없이 잰다.
    """
    attempt = 0
    for status in statuses:
        attempt += 1
        if status is not None and 200 <= status < 300:
            return attempt
        if not policy.should_retry(attempt, status):
            return attempt
    return attempt
