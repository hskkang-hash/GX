# -*- coding: utf-8 -*-
"""UX-24 — **역할별 동시 세션 상한**. 새 인증 문이 아니라 있는 문 뒤의 정책이다.

무엇이 문제였나 [실측 2026-09-05]
---------------------------------
관제실의 실제 모습은 **월 모드 대형 화면 · 자리 데스크톱 · 이동 중 휴대전화를 동시에**
켜 두는 것이다. 그런데 이 제품은 **동시 접속이 1개**다 — 월 모드를 켜면 자리 화면이
튕기고, 자리에서 다시 로그인하면 월이 죽는다.

★ 그 1개는 설정이 아니라 **자료구조**다 (§0.4 · 고칠 수 없다)
-------------------------------------------------------------
    core/user/models.py:577   user.token = enc("<session_id>:<access_jti>")   ← 한 칸. 한 벌.
    core/api/v1/auth.py:706   로그인이 그 칸을 **덮어쓴다**
    core/auth.py:63           토큰의 session_id ≠ user.token 의 session_id → 401
                              "Token from different session"
    core/api/v1/auth.py:630   end_previous_session=false 이고 앞선 세션이 있으면
                              **200 · success:false** — 토큰을 아예 안 준다

즉 갈래는 둘뿐이고 **둘 다 진다**: 거절당하거나, 앞 화면을 죽이거나.
두 기기가 동시에 사는 길은 `core/auth.py` 의 대조를 고치거나 `user.token` 을 여러 벌로
바꾸는 것인데 **둘 다 dj-core(§0.4)** 다. 그래서 이 파일이 하지 **못하는** 것을 먼저 적는다:

    ⚠ 이 모듈은 「2대가 동시에 산다」를 만들지 못한다. 그것은 **판정 불가**다.
      지어내지 않는다. 대장(`docs/agent/authn_paths.md` §8)에 그대로 적어 두었다.

그러면 우리 층이 얹을 수 있는 것은 무엇인가 — **넷**
----------------------------------------------------
  ① **상한 표 한 벌.** 역할이 몇 대까지 함께 쓰는가. 지금은 정책이 코드 어디에도 없고
     「1」이 우연히 자료구조에서 나온다. 상한이 **선언되어 있어야** dj-core 의 벽이
     걷히는 날 그 자리가 이미 서 있다.
  ② **월 모드 세션 12시간.** 사람이 없는 화면의 수명은 사람이 앉은 화면과 다르다.
  ③ **초과 시 가장 오래된 세션을 끊는다** — 순수 함수 `admit`. 대장이 어디에 있든
     이 판정은 같아야 하므로 저장소와 분리한다(시험이 이 함수만으로 전부 잰다).
  ④ **끊긴 화면이 왜 끊겼는지 말한다.** [실측] 그 화면이 실제로 받는 것은
     `401 {"detail": "Unauthorized"}` **한 줄**이다 — dj-core 가 안에서 만든 사유
     ("Token from different session")는 두 겹의 `except` 가 삼켜 밖으로 못 나온다
     (`core/auth.py:119` · `core/api/v1/auth.py:197`). 즉 밀려난 화면과 토큰이 깨진
     화면이 **글자 하나까지 똑같다.** 사람은 고장과 구별하지 못한다.
     우리 미들웨어가 **요청이 들고 온 토큰**으로 그 둘을 갈라 사전 문구를 넣는다.

★ ④ 는 오늘 당장 제품이 달라지는 유일한 칸이다. ①②③ 은 벽이 걷히는 날을 위한 것이고,
  **그 사실을 숨기지 않는다** — 시험이 「지금은 1개다」를 characterization 으로 고정한다.

낱말은 만들지 않았다 (GX-COPY 규칙 1)
-------------------------------------
`docs/design/GX-COPY_v1.md` §5 「2026-09-05 턴 E 추가」에 조율자가 넣은 두 문장만 쓴다.
새 문구를 여기서 지어내면 사전과 화면이 갈라진다.

토큰 수명은 한 값도 안 바꿨다
-----------------------------
월 모드 12시간이 `NINJA_JWT` 를 요구하는지부터 쟀다 — **요구하지 않는다.**
접근 200분 < 12시간이지만 재발급 7일 + 회전이 그 사이를 잇고, 앞단이 실제로 재발급을
부른다(`docs/agent/evidence/UX-16/session_12h.md` 가 번들에서 확인했다).
접근 토큰을 720분으로 올리면 월 모드 한 장을 위해 **제품 전체의 탈취 창**이 넓어진다.
`tests/test_s_session_limit.py::test_token_lifetime_unchanged` 가 세 값을 못박는다.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Iterable, Sequence

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# 사전 — GX-COPY §5 「2026-09-05 턴 E 추가」. **여기서 문구를 만들지 않는다**
# ═══════════════════════════════════════════════════════════════════════════

#: 다른 기기가 로그인해 이 화면이 밀려났을 때. 「세션 만료」는 원인을 안 말한다.
COPY_EVICTED = "다른 기기에서 로그인되었습니다"

#: 상한을 넘겨 가장 오래된 화면을 닫았을 때. 무엇이 일어났는지와 무엇이 닫혔는지를 함께.
COPY_OVER_CAP = (
    "이 계정으로 함께 쓸 수 있는 기기 수를 넘었습니다. 가장 오래 켜 둔 화면을 닫았습니다."
)


# ═══════════════════════════════════════════════════════════════════════════
# 상한 표 — 세종 판정 (U1 3 · U2 3 · U4 2 · U5 2)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 역할 코드를 **여기에 베끼지 않는다.** `config/k3_roles` 한 곳이 답한다 —
#   두 벌이 되면 반드시 어긋나고, 어긋난 쪽이 조용히 아무것도 안 본다 (D-369).
#   U1~U5 ↔ 코드 묶음의 대응은 `common/menu_exposure.py` 가 이미 쓰는 것과 같다.

from config.k3_roles import (  # noqa: E402  — 상한 표가 이 묶음을 그대로 쓴다
    K3_ROLE_EXECUTIVES,  # U4 재난안전과 (열람 전용)
    K3_ROLE_MANAGERS,    # U2 관제팀장
    K3_ROLE_OPERATORS,   # U1 관제요원
    K3_ROLE_SYSOPS,      # U5 시스템 관리자
)

#: 사람 갈래별 상한. **판정이지 추측이 아니다** — 세종 판정 2026-09-05 턴 E.
#:   U1 3 · U2 3  월 + 자리 + 휴대전화. 셋이 이 사람의 실제 자리다
#:   U4 2 · U5 2  열람과 운영은 자리와 휴대전화 둘이면 된다 — 월 모드를 안 켠다
ROLE_SESSION_CAPS: dict[str, int] = {
    **{code: 3 for code in K3_ROLE_OPERATORS},
    **{code: 3 for code in K3_ROLE_MANAGERS},
    **{code: 2 for code in K3_ROLE_EXECUTIVES},
    **{code: 2 for code in K3_ROLE_SYSOPS},
}

#: 매핑되지 않은 역할의 상한. **1 이다 — 지금 제품이 그렇기 때문이다.**
#:
#: ★ 여기에 2 나 3 을 적으면 그것은 판정이 아니라 **추측**이 된다. 배송·주문 역할은
#:   이 제품(재난안전)의 사람이 아니고(`K3_UNMAPPED_BY_DECISION`), 그들에게 몇 대를
#:   줄지는 아무도 정한 적이 없다. 「모른다」의 값은 **오늘의 값**이다 (D-280).
DEFAULT_SESSION_CAP = 1

#: 월 모드 세션의 수명. 사람이 앉아 있지 않은 화면이라 자리 화면과 다르다.
#: 세종 판정 12시간 — 한 교대(8h)를 넘기고 이틀은 못 넘긴다.
WALL_MODE_SESSION_TTL_SECONDS = 12 * 60 * 60

#: 자리 화면 세션의 수명 상한. 재발급 토큰(7일)을 넘지 않게만 잡는다 —
#: 이 값이 토큰보다 길면 대장에는 살아 있고 서버는 거절하는 유령 행이 생긴다.
DEFAULT_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


def cap_for_role_codes(codes: Iterable[str]) -> tuple[int, str]:
    """이 역할 묶음의 동시 세션 상한과 **그 근거 한 줄**.

    근거를 함께 돌려주는 이유: 수만 돌려주면 다음 사람이 「왜 2인가」를 다시 캐야 한다.
    사람이 역할을 여럿 가지면 **넓은 쪽**을 준다 — 관제팀장이 관제요원 역할을 겸할 때
    좁은 쪽을 주면 겸직이 벌이 된다.
    """
    known = [(c, ROLE_SESSION_CAPS[c]) for c in codes if c in ROLE_SESSION_CAPS]
    if not known:
        return DEFAULT_SESSION_CAP, "상한 표에 없는 역할 — 오늘의 값(1)을 그대로 둔다"
    code, cap = max(known, key=lambda kv: kv[1])
    return cap, f"역할 `{code}` (config/k3_roles)"


def cap_for_user(user) -> tuple[int, str]:
    """사용자 하나의 상한. 역할을 못 읽으면 **좁은 쪽**으로 떨어진다 (D-343 ②)."""
    try:
        codes = [r.code for r in user.roles.all()]
    except Exception:  # 역할 표를 못 읽는 상황은 「넓다」가 아니라 「모른다」다
        return DEFAULT_SESSION_CAP, "역할을 읽지 못했다 — 좁은 쪽"
    return cap_for_role_codes(codes)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수**. 저장소가 무엇이든 이 답은 같아야 한다
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SessionRecord:
    """대장 한 줄. `session_id` 는 dj-core 가 토큰에 심는 그 값이다."""

    session_id: str
    user_id: int
    started_at: float          # epoch 초
    wall_mode: bool = False
    device: str = ""           # User-Agent 앞머리 — 사람이 「어느 화면인가」를 알아보게

    def ttl_seconds(self) -> int:
        return WALL_MODE_SESSION_TTL_SECONDS if self.wall_mode else DEFAULT_SESSION_TTL_SECONDS

    def expired_at(self, now: float) -> bool:
        return (now - self.started_at) >= self.ttl_seconds()


def admit(
    existing: Sequence[SessionRecord],
    incoming: SessionRecord,
    cap: int,
    now: float,
) -> tuple[list[SessionRecord], list[SessionRecord]]:
    """새 세션을 들인다. **(남는 것, 끊는 것)** 을 돌려준다.

    순서가 곧 정책이다 — 이 순서를 바꾸면 답이 달라진다:

      ① **만료 먼저 걷어낸다.** 12시간 지난 월 모드가 자리를 차지한 채로 상한을 세면
         살아 있는 화면이 죽은 화면 때문에 밀려난다.
      ② 같은 `session_id` 가 이미 있으면 **갱신**이지 새 기기가 아니다 (재발급 회전).
      ③ 상한을 넘으면 **가장 오래 켜 둔 것**부터 끊는다 — 사전 문구가 그렇게 말한다
         (「가장 오래 켜 둔 화면을 닫았습니다」). 최근에 앉은 사람을 쫓아내지 않는다.

    ★ 만료로 사라진 것은 **끊긴 것이 아니다.** 둘을 한 자루에 담으면 「다른 기기가
      밀어냈다」와 「12시간이 지났다」가 같은 안내를 받고, 사람은 있지도 않은 다른
      기기를 찾는다.
    """
    alive = [s for s in existing if not s.expired_at(now)]
    kept = [s for s in alive if s.session_id != incoming.session_id]

    # 오래된 것이 앞. 같은 시각이면 session_id 로 갈라 **판정을 결정적으로** 만든다.
    kept.sort(key=lambda s: (s.started_at, s.session_id))

    evicted: list[SessionRecord] = []
    room = max(cap - 1, 0)           # 새 세션 한 자리를 뺀 나머지
    while len(kept) > room:
        evicted.append(kept.pop(0))

    return kept + [incoming], evicted


# ═══════════════════════════════════════════════════════════════════════════
# 대장 — 캐시. **모델을 만들지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 표가 아니라 캐시인가: 세션은 태생이 임시다. 표로 만들면 마이그레이션이 붙고,
# 그 마이그레이션은 §0.4 의 `user` 앱과 같은 DB 를 건드린다. 그리고 이 대장이
# 비어도 **제품은 지금과 똑같이 돈다**(상한 판정만 못 한다) — 비어도 안전한 것을
# 영속 저장소에 두지 않는다.
#
# ⚠ 재기동하면 대장이 빈다. 그 사실을 숨기지 않는다 — `active()` 가 빈 목록을 주면
#   그것은 「세션이 없다」가 아니라 **「모른다」**이고, 상한 판정은 그때 관대해진다.
#   dj-core 의 1개 벽이 그대로 서 있는 동안 이 관대함은 아무것도 열지 않는다.

_KEY = "gx:ux24:sessions:%s"


class SessionRegistry:
    """사용자별 세션 대장. 캐시 한 칸에 목록 하나."""

    def __init__(self, backend=None):
        self._cache = backend if backend is not None else cache

    def active(self, user_id: int, now: float | None = None) -> list[SessionRecord]:
        now = time.time() if now is None else now
        raw = self._cache.get(_KEY % user_id)
        if not raw:
            return []
        try:
            rows = json.loads(raw)
        except (TypeError, ValueError):
            return []
        out = []
        for row in rows:
            try:
                rec = SessionRecord(**row)
            except TypeError:
                continue
            if not rec.expired_at(now):
                out.append(rec)
        return out

    def _write(self, user_id: int, rows: Sequence[SessionRecord]) -> None:
        payload = json.dumps([r.__dict__ for r in rows])
        self._cache.set(_KEY % user_id, payload, DEFAULT_SESSION_TTL_SECONDS)

    def record(
        self,
        incoming: SessionRecord,
        cap: int,
        now: float | None = None,
    ) -> list[SessionRecord]:
        """새 세션을 대장에 넣고 **끊긴 것들**을 돌려준다."""
        now = time.time() if now is None else now
        kept, evicted = admit(self.active(incoming.user_id, now), incoming, cap, now)
        self._write(incoming.user_id, kept)
        return evicted

    def drop(self, user_id: int, session_id: str, now: float | None = None) -> None:
        """세션 한 줄을 지운다.

        ★ `now` 를 받는 이유 — 시험이 잡았다. `active()` 는 만료된 행을 걸러 내는데,
          지금 시각을 안에서 읽으면 **부르는 쪽이 재현할 수 없다.** 첫 판은 그래서
          「지웠더니 나머지도 사라졌다」를 냈다. 시각을 인자로 받는 함수는 재현된다.
        """
        rows = [s for s in self.active(user_id, now) if s.session_id != session_id]
        self._write(user_id, rows)

    def clear(self, user_id: int) -> None:
        self._cache.delete(_KEY % user_id)


# ═══════════════════════════════════════════════════════════════════════════
# 미들웨어 — 오늘 제품이 달라지는 한 칸
# ═══════════════════════════════════════════════════════════════════════════

#: dj-core 안쪽에서 「다른 세션의 토큰」에 붙는 영문 문구 (`core/auth.py:63`).
#:
#: ★ [실측 2026-09-05] **이 글자는 화면에 절대 닿지 않는다.** 두 겹이 삼킨다:
#:     core/auth.py:119        바깥 `except Exception` 이 그것을 잡아 "Token invalid" 로 바꾼다
#:     core/api/v1/auth.py:197 `CustomJWTAuth.authenticate` 의 `except Exception: pass` 가
#:                             그것마저 삼키고 None 을 돌려준다 → ninja 가 낸다:
#:                                 401 {"detail": "Unauthorized"}
#:   그래서 **응답 본문으로는 「밀려남」과 「토큰이 깨졌다」를 가를 수 없다.**
#:   가르는 자리는 응답이 아니라 **요청**이다 — 아래 `_eviction_of` 가 그것을 한다.
DJCORE_DIFFERENT_SESSION = "Token from different session"

#: 화면이 실제로 받는 401 본문. dj-core 의 사유가 여기까지 오지 못한 결과다.
DJCORE_WIRE_DETAIL = "Unauthorized"

#: 로그인 문. 대장에 행을 남길 자리다 (`authn_paths.md` §8 — 문은 이것 하나다).
LOGIN_PATH = "/api/v1/auth/login"

#: 로그아웃 문. 사람이 스스로 닫은 화면은 **대장에서도 지운다** — 안 지우면 닫힌 화면이
#: 상한 한 자리를 계속 먹고, 그러면 사람은 「두 대만 켰는데 밀려난다」를 겪는다.
LOGOUT_PATH = "/api/v1/auth/logout"


def session_limit_enabled() -> bool:
    """되돌리기는 이 한 줄이다 (`settings.SESSION_LIMIT_ENABLED = False`)."""
    return bool(getattr(settings, "SESSION_LIMIT_ENABLED", True))


def _wall_mode(request) -> bool:
    """이 로그인이 **월 모드**인가.

    앞단이 아직 이 표식을 안 보낸다 — 그래서 기본값은 거짓이고, 그 사실을 여기 적는다.
    ⚠ **조율자 배선 필요**: 월 모드 화면이 로그인에 `X-GX-Surface: wall` 을 실으면
      12시간 수명이 그 세션에 붙는다. 안 실으면 자리 화면과 같은 수명이다 —
      **없는 배선을 있는 척하지 않는다.**
    """
    return request.headers.get("X-GX-Surface", "").strip().lower() == "wall"


class SessionLimitMiddleware:
    """UX-24 의 두 칸: **대장 기록**과 **끊긴 화면의 한 줄**.

    ★ 배치 — `ApiContractStatusMiddleware` **바로 위**(즉 `UniversalCacheMiddleware`
      보다 바깥, `GZipMiddleware` 보다 안쪽). 이유는 그 파일의 배치 주석과 같다:
      압축된 본문은 JSON 으로 읽을 수 없고, 캐시 안쪽에 두면 적중한 응답에서
      아예 불리지 않는다.

    ★ **상태코드는 건드리지 않는다.** 401 은 401 그대로 나간다 — 앞단의 재로그인
      경로가 상태로 판정하기 때문이다. 우리가 바꾸는 것은 사람이 읽는 글자뿐이다.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.registry = SessionRegistry()

    def __call__(self, request):
        response = self.get_response(request)
        if not session_limit_enabled():
            return response
        try:
            if response.status_code == 401:
                return self._name_the_eviction(request, response)
            if request.path.rstrip("/") == LOGIN_PATH and response.status_code == 200:
                self._record_login(request, response)
            elif request.path.rstrip("/") == LOGOUT_PATH and response.status_code == 200:
                self._forget_session(request)
        except Exception:  # 정책 한 겹이 제품을 못 세운다
            logger.exception("[UX-24] 세션 상한 층에서 예외 — 응답은 그대로 내보낸다")
        return response

    # ── ④ 끊긴 화면이 왜 끊겼는지 말한다 ────────────────────────────────
    def _name_the_eviction(self, request, response: HttpResponse) -> HttpResponse:
        """401 하나를 보고 **「밀려남」인지 아닌지**를 가른다.

        ★ 응답 본문으로 가르지 않는다 — 위 `DJCORE_WIRE_DETAIL` 주석의 이유로
          모든 401 이 똑같이 `"Unauthorized"` 다. 넓게 잡으면 비밀번호를 틀린 사람이
          있지도 않은 다른 기기를 찾는다. 그래서 **요청이 들고 온 토큰**을 본다.
        """
        if not _eviction_of(request):
            return response
        body = _json_body(response)
        if not isinstance(body, dict):
            body = {"detail": DJCORE_WIRE_DETAIL}
        # 원문을 지우지 않는다 — 로그·연동자가 읽던 값이 사라지면 그것도 계약 파손이다.
        body["origin_detail"] = body.get("detail", DJCORE_WIRE_DETAIL)
        body["detail"] = COPY_EVICTED
        body["reason_code"] = "session_evicted"
        logger.info("[UX-24] 밀려난 세션에 사유를 붙였다: %s %s", request.method, request.path)
        return JsonResponse(body, status=401)

    # ── 사람이 스스로 닫은 화면은 대장에서도 지운다 ──────────────────────
    def _forget_session(self, request) -> None:
        """로그아웃. 안 지우면 **닫힌 화면이 상한 한 자리를 계속 먹는다** —
        그러면 사람은 「두 대만 켰는데 밀려난다」를 겪고, 그 원인을 아무도 못 찾는다.
        """
        claims = _claims_of(bearer_of(request))
        if claims is None:
            return
        session_id, user_id = claims
        self.registry.drop(user_id, session_id)
        logger.info("[UX-24] 로그아웃 — 대장에서 세션 한 줄을 지웠다")

    # ── ①②③ 대장에 남긴다 ─────────────────────────────────────────────
    def _record_login(self, request, response: HttpResponse) -> None:
        body = _json_body(response)
        if not isinstance(body, dict) or body.get("success") is not True:
            return
        # ★ 세션과 사람을 **토큰에서** 읽는다 — 본문의 `user_id` 를 믿지 않는다.
        #   대장의 열쇠는 서명된 값이어야 한다(두 벌을 만들지 않는다 · D-369).
        claims = _claims_of((body.get("user") or {}).get("access_token"))
        if claims is None:
            return
        session_id, user_id = claims
        user = getattr(request, "user", None)
        cap, why = cap_for_user(user) if user is not None else (DEFAULT_SESSION_CAP, "사용자 없음")
        incoming = SessionRecord(
            session_id=session_id,
            user_id=user_id,
            started_at=time.time(),
            wall_mode=_wall_mode(request),
            device=(request.META.get("HTTP_USER_AGENT") or "")[:80],
        )
        evicted = self.registry.record(incoming, cap)
        if evicted:
            # 사전 문구 그대로. 앞단이 이 칸을 그리면 사람이 읽는다 (조율자 배선 필요).
            body["session_notice"] = COPY_OVER_CAP
            response.content = json.dumps(body).encode("utf-8")
            response["Content-Length"] = str(len(response.content))
            logger.info(
                "[UX-24] 상한 %d(%s) 초과 — 가장 오래된 세션 %d개를 끊었다",
                cap, why, len(evicted),
            )


def bearer_of(request) -> str | None:
    """`Authorization: Bearer <…>` 의 토큰.

    ⚠ **들어오는 키**(`inbound_api_key` — 남이 우리를 부르는 자리)는 이 절의 것이 아니다.
      이름에 방향을 붙여 적는다: 나가는 키와 들어오는 키는 다른 것이고, 방향 없이
      「키」라고만 적으면 다음 사람이 둘을 같은 것으로 읽는다 (동음이의 게이트 · D-337).
    """
    value = request.META.get("HTTP_AUTHORIZATION") or ""
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _claims_of(token: str | None) -> tuple[str, int] | None:
    """서명을 검증하고 `(session_id, user_id)` 를 돌려준다. 못 읽으면 None.

    ★ 검증 없이 읽지 않는다 — 검증을 빼면 아무나 남의 대장 행을 지우거나 남의 401
      문구를 바꿔 볼 수 있다. 만료(`exp`)는 보지 않는다: 밀려난 화면의 토큰도,
      방금 발급된 토큰도 이 함수의 손님이다.
    """
    if not token:
        return None
    try:
        import jwt

        payload = jwt.decode(
            token,
            settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")],
            options={"verify_exp": False},
            leeway=60,
        )
    except Exception:
        return None
    session_id = payload.get("session_id")
    user_id = payload.get("user_id")
    if isinstance(session_id, str) and session_id and isinstance(user_id, int):
        return session_id, user_id
    return None


def _eviction_of(request) -> bool:
    """이 요청은 **밀려난 화면**의 것인가.

    술어는 하나다: 토큰이 말하는 세션과 `user.token` 에 심긴 세션이 **서로 다르다**.
    그것이 dj-core `core/auth.py:63` 이 보는 바로 그 조건이고, 다른 401 사유들과
    깔끔히 갈린다:

        서명이 깨진 토큰      → 여기서 못 읽는다        → 아니다
        헤더가 아예 없다      → 토큰이 없다             → 아니다
        비밀번호 실패          → Bearer 가 아니다        → 아니다
        `user.token` 이 비었다 → 강제 로그아웃           → 아니다 (사유가 다르다)
        세션이 다르다          → **밀려났다**            → 그렇다

    ★ 서명을 **검증한다.** 검증 없이 읽으면 아무나 남의 401 문구를 바꿔 볼 수 있다.
    ★ 만료(`exp`)는 보지 않는다 — 만료된 토큰도 「밀려난 화면」일 수 있고, 그 사람이
      알아야 할 것은 만료가 아니라 **누가 밀어냈나**다.
    """
    claims = _claims_of(bearer_of(request))
    if claims is None:
        return False
    token_session, user_id = claims
    try:
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.filter(id=user_id).only("id", "token").first()
        if user is None or not user.token:
            return False
        stored_session, _jti = user.get_session_token_parts()
    except Exception:
        return False
    if not stored_session:
        return False
    return stored_session != token_session


def _json_body(response: HttpResponse):
    """`common/api_contract._json_body` 와 같은 규약. 스트리밍·압축 본문은 안 만진다."""
    if getattr(response, "streaming", False):
        return None
    if response.has_header("Content-Encoding"):
        return None
    if "json" not in response.headers.get("Content-Type", "").lower():
        return None
    try:
        return json.loads(response.content.decode(response.charset or "utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


__all__ = [
    "COPY_EVICTED",
    "COPY_OVER_CAP",
    "DEFAULT_SESSION_CAP",
    "DJCORE_DIFFERENT_SESSION",
    "DJCORE_WIRE_DETAIL",
    "bearer_of",
    "ROLE_SESSION_CAPS",
    "SessionLimitMiddleware",
    "SessionRecord",
    "SessionRegistry",
    "WALL_MODE_SESSION_TTL_SECONDS",
    "admit",
    "cap_for_role_codes",
    "cap_for_user",
]
