# -*- coding: utf-8 -*-
"""FWS App 의 URL 등록. `config/urls.py` 가 `api/fws/` 로 include 한다.

`apps/dsm/urls.py` 와 같은 모양(`NinjaExtraAPI` + `register_controllers`)을 쓴다 —
라우트 열거기(`common.tenant_scope.enumerate_operations`)가 아는 배선이 하나뿐이라야
한다.
"""
from django.urls import path
from ninja_extra import NinjaExtraAPI

from apps.fws.api import FwsAPI
from apps.fws.api_admin import FwsAdminAPI
from apps.fws.api_office import FwsOfficeAPI
from apps.fws.api_office2 import FwsOffice2API
from apps.fws.api_n1 import FwsN1API
from apps.fws.api_command import FwsCommandAPI
from apps.fws.api_ap import FwsApAPI

fws_api = NinjaExtraAPI(urls_namespace="fws")
fws_api.register_controllers(FwsAPI)
# 턴 AN · 차선마다 제 파일 하나(조율자 등록 · 한 파일은 한 차선)
fws_api.register_controllers(FwsOfficeAPI, FwsOffice2API, FwsAdminAPI, FwsN1API)
# 턴 AO · 차선 N2
fws_api.register_controllers(FwsCommandAPI)
# 턴 AP · 차선 N4
fws_api.register_controllers(FwsApAPI)

urlpatterns = [
    path("", fws_api.urls),
]
