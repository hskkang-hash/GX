# -*- coding: utf-8 -*-
"""K3 오류 계약. K1·K2·K6 과 같은 형을 쓴다."""
from __future__ import annotations


class K3Error(Exception):
    """K3 이 내는 모든 오류의 뿌리."""


class InvalidLayoutInput(K3Error):
    """프리셋·앱·위젯 이름이 계약을 벗어난 입력. HTTP 400 으로 번역한다."""


class NotImplementedYet(K3Error):
    """공개 면에 이름은 있는데 구현이 없는 것 (D-284)."""
