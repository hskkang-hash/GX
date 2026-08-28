# -*- coding: utf-8 -*-
"""K2 오류 계약. K1·K6 과 같은 형을 쓴다 — App 이 커널마다 다른 계보를 외우지 않게."""
from __future__ import annotations


class K2Error(Exception):
    """K2 가 내는 모든 오류의 뿌리."""


class InvalidNotifyInput(K2Error):
    """등급·채널·기간이 계약을 벗어난 입력. HTTP 400 으로 번역한다."""


class NoRecipients(K2Error):
    """수신자가 0명이다 — **조용한 무력화를 막는다** (DA-03 §3-2).

    ★ 빈 목록을 돌려주지 않는 이유: 그러면 "보냈는데 대상이 없었다"가 성공으로 보인다.
      규칙이 비었거나 역할에 사람이 없는 상태는 **알림 체계가 꺼져 있는 것**이고,
      그것은 재난 시스템에서 가장 조용한 고장이다. 없는 것과 실패한 것을 같은 값으로
      표현하지 않는다 (D-290).
    """


class NotImplementedYet(K2Error):
    """공개 면에 이름은 있는데 구현이 없는 것 (D-284)."""
