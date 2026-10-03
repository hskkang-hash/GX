# -*- coding: utf-8 -*-
"""QA 10키 — WO-GRDX-20261003-04 §4 (규격 09 M3 · 세종 확정). **계약 한 벌.**

시드(`manage.py qa_seed`) · 진입(`/qa/as/<키>`) · QA 바(`/qa/keys`)가 모두 이 표만 읽는다.
키 이름을 두 곳에 적으면 어긋난다.

규칙:
  - 계정 username = ``qa_<키>`` (``username_for``). 진입은 **이 표에 있는 키**만 받고,
    그 username 의 계정만 찾는다 — 임의 id·메일·username 은 받지 않는다.
  - 모든 데이터는 가짜(``FAKE_`` 접두 · 메일은 ``.invalid`` 도메인). 실제 고객 데이터 0.
  - ``first_path`` 는 진입 뒤 보낼 첫 화면(역할 표 `roleScreens.json` 의 그 역할 첫 메뉴).
"""
from __future__ import annotations

QA_KEYS: dict[str, dict] = {
    "operator_empty_01":   {"type": "관제요원",       "owner": "U1", "org": "FAKE_빈기관",  "state": "빈 기관 — 사건 0 · 카메라 0",                 "first_path": "/dsm/queue"},
    "operator_basic_01":   {"type": "관제요원",       "owner": "U1", "org": "FAKE_기본기관", "state": "소량 — 대기 사건 5 · 카메라 4",               "first_path": "/dsm/queue"},
    "operator_heavy_01":   {"type": "관제요원",       "owner": "U1", "org": "FAKE_대량기관", "state": "대량 — 사건 500+ · 카메라 60",                "first_path": "/dsm/queue"},
    "lead_basic_01":       {"type": "관제팀장",       "owner": "U2", "org": "FAKE_기본기관", "state": "operator_basic_01 과 같은 기관(연결 쌍)",       "first_path": "/dsm/queue"},
    "field_basic_01":      {"type": "현장(이동 중)",  "owner": "U3", "org": "FAKE_기본기관", "state": "같은 기관 — 내게 온 사건 2",                  "first_path": "/m/inbox"},
    "officer_basic_01":    {"type": "지자체 담당자",  "owner": "U4", "org": "FAKE_기본기관", "state": "지난 7일 기록 · 보고서 2건",                  "first_path": "/dsm/events"},
    "admin_basic_01":      {"type": "시스템 관리자",  "owner": "U5", "org": "FAKE_기본기관", "state": "사용자 6 · 알림 규칙 2 · 백업 기록",          "first_path": "/dsm/events"},
    "dev_basic_01":        {"type": "외부 연계 개발자", "owner": "U6", "org": "FAKE_기본기관", "state": "접근 키 둘 — 만료 직전 1 · 만료 직후 1",     "first_path": "/dsm/integrations"},
    "newcomer_pending_01": {"type": "역할 없음(초대만)", "owner": None, "org": "FAKE_기본기관", "state": "승인 전 — 대기 화면",                        "first_path": "/start"},
    "platform_ops_01":     {"type": "플랫폼 운영자",  "owner": "OPS", "org": None,          "state": "기관 3 · 기기 10",                           "first_path": "/ops"},
}

USERNAME_PREFIX = "qa_"


def username_for(key: str) -> str:
    return f"{USERNAME_PREFIX}{key}"


def password_for(key: str) -> str:
    """QA 계정의 비밀번호 — **그 QA 판의 SECRET_KEY 에서 끌어낸다**(어디에도 적지 않는다).

    진입(`/qa/as/<키>`)은 인증을 건너뛰지 않는다: 이 값으로 **실제 로그인 함수**(dj-core
    `login_user`)를 부른다. 그래서 잠금·OTP·세션 1개·감사 로그가 사람의 로그인과 똑같이 돈다.
    SECRET_KEY 가 판마다 다르므로 이 값도 판마다 다르다 — QA 판의 값은 운영에서 쓸모가 없다.
    끝의 「Qa!9」는 비밀번호 규칙(대·소문자·숫자·특수문자)을 맞추려는 것이다.
    """
    import hashlib
    import hmac

    from django.conf import settings

    digest = hmac.new(settings.SECRET_KEY.encode(), f"qa-entry:{key}".encode(), hashlib.sha256).hexdigest()
    return f"{digest[:24]}Qa!9"


def is_known(key: str) -> bool:
    return key in QA_KEYS
