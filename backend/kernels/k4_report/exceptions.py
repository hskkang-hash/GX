# -*- coding: utf-8 -*-
"""K4 오류 계약. K1·K2·K3·K6 과 같은 형을 쓴다."""
from __future__ import annotations


class K4Error(Exception):
    """K4 가 내는 모든 오류의 뿌리."""


class InvalidReportInput(K4Error):
    """템플릿·기간·대상이 계약을 벗어난 입력. HTTP 400 으로 번역한다."""


class RenderFailed(K4Error):
    """렌더가 실패했다. **빈 PDF 를 돌려주지 않는다** (D-284).

    0바이트 PDF 는 열리기는 하고 내용이 없다 — 받는 사람은 "보고서가 비었다"로 읽고
    시스템은 "생성했다"로 센다. 그 둘이 갈리는 순간 U2(보고서 자동화)의 숫자가 거짓이 된다.
    """


class NotImplementedYet(K4Error):
    """공개 면에 이름은 있는데 구현이 없는 것 (D-284)."""
