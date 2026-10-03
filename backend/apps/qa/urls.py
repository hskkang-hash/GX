# -*- coding: utf-8 -*-
"""QA 진입 URL — `config/urls.py` 가 `settings.QA_BUILD` 가 참일 때만 `qa/` 로 include 한다(M1 잠금 ①)."""
from django.urls import path

from apps.qa import views

urlpatterns = [
    path("as/<str:key>", views.qa_as, name="qa_as"),
]
