# -*- coding: utf-8 -*-
"""FWS App 의 URL 등록. `config/urls.py` 가 `api/fws/` 로 include 한다.

`apps/dsm/urls.py` 와 같은 모양(`NinjaExtraAPI` + `register_controllers`)을 쓴다 —
라우트 열거기(`common.tenant_scope.enumerate_operations`)가 아는 배선이 하나뿐이라야
한다.
"""
from django.urls import path
from ninja_extra import NinjaExtraAPI

from apps.fws.api import FwsAPI

fws_api = NinjaExtraAPI(urls_namespace="fws")
fws_api.register_controllers(FwsAPI)

urlpatterns = [
    path("", fws_api.urls),
]
