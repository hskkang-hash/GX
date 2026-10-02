# -*- coding: utf-8 -*-
"""GCS 경유의 URL 등록. `config/urls.py` 가 `api/gcs/` 로 include 한다 (WO-GRDX-20261002-10).

`apps/dsm/urls.py` · `apps/fws/urls.py` 와 같은 모양(`NinjaExtraAPI` + `register_controllers`) —
라우트 열거기가 아는 배선이 하나뿐이라야 한다.
"""
from django.urls import path
from ninja_extra import NinjaExtraAPI

from apps.gcs.api import GcsProxyAPI

gcs_api = NinjaExtraAPI(urls_namespace="gcs")
gcs_api.register_controllers(GcsProxyAPI)

urlpatterns = [
    path("", gcs_api.urls),
]
