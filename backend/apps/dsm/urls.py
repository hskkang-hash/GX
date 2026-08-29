# -*- coding: utf-8 -*-
"""DSM App 의 URL 등록. `config/urls.py` 가 `api/dsm/` 로 include 한다.

기존 앱들과 같은 모양(`NinjaExtraAPI` + `register_controllers`)을 쓴다 —
새 방식을 들이면 라우트 열거기(`common.tenant_scope.enumerate_operations`)가
그 방식을 모르고, 모르는 라우트는 **트립와이어의 눈 밖**이 된다.
"""
from django.urls import path
from ninja_extra import NinjaExtraAPI

from apps.dsm.api import DsmAPI

dsm_api = NinjaExtraAPI(urls_namespace="dsm")
dsm_api.register_controllers(DsmAPI)

urlpatterns = [
    path("", dsm_api.urls),
]
