# -*- coding: utf-8 -*-
"""DSM App 의 URL 등록. `config/urls.py` 가 `api/dsm/` 로 include 한다.

기존 앱들과 같은 모양(`NinjaExtraAPI` + `register_controllers`)을 쓴다 —
새 방식을 들이면 라우트 열거기(`common.tenant_scope.enumerate_operations`)가
그 방식을 모르고, 모르는 라우트는 **트립와이어의 눈 밖**이 된다.
"""
from django.urls import path
from ninja_extra import NinjaExtraAPI

from apps.dsm.api import DsmAPI
from apps.dsm.law_api import DsmLawAPI

dsm_api = NinjaExtraAPI(urls_namespace="dsm")
#: ★ 컨트롤러 둘. 법·인증 면(LAW-02a · LAW-06 · LAW-07)은 별도 파일에 산다 —
#:   같은 턴에 두 차선이 한 라우트 파일을 고치면 충돌하고, 충돌한 라우트는
#:   **라우팅 침묵**으로 나타난다(경로가 사라졌는데 오류도 안 난다).
dsm_api.register_controllers(DsmAPI, DsmLawAPI)

urlpatterns = [
    path("", dsm_api.urls),
]
