# -*- coding: utf-8 -*-
"""QA 진입 URL — `config/urls.py` 가 `settings.QA_BUILD` 가 참일 때만 `qa/` 로 include 한다(M1 잠금 ①).

`/qa/enter` 는 여기 없다 — 화면(QA 번들의 `QaEntry`) 자리다. QA 앞문이 그 한 주소만 화면으로 보낸다.
"""
from django.urls import path

from apps.qa import views

urlpatterns = [
    path("as/<str:key>", views.qa_as, name="qa_as"),
    path("handoff", views.qa_handoff, name="qa_handoff"),
    path("keys", views.qa_keys_list, name="qa_keys"),
    path("outbox", views.qa_outbox, name="qa_outbox"),
]
