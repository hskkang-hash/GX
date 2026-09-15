# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **U56(관리자 · 연계)** 라우터 모듈. 이 파일은 U56 차선만 고친다.

규약은 `api_u1.py` 머리말과 같다: 기존 라우트는 옮기지 않는다 · `DsmAPI`·`DsmLawAPI` 뒤에
붙으므로 기존 경로에 다른 메서드를 더하지 않는다(405 삼킴) · 새 경로는 ISO-03·SEC-04·계약
도달을 태어날 때 통과한다.
"""
from ninja_extra import api_controller


@api_controller("", tags=["DSM — U5·U6 관리자·연계 (WO-01 차선 U56)"])
class DsmU56API:
    """U56 차선의 새 라우트가 태어나는 자리(턴 Q 조율자 분할 · 처음엔 비어 있다)."""
