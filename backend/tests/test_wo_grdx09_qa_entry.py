# -*- coding: utf-8 -*-
"""WO-GRDX-20261003-04 레인 C — 규격 09 M2 진입 `/qa/as/<키>` (QA 판에서만).

잰다:
  · 표의 키 + 그 판의 비밀번호로 **실제 로그인 함수**가 통과 → 302 `/qa/enter?h=<인계표>` (주소에 토큰 0)
  · 인계표는 한 번만 — 두 번째 수령 404
  · 표 밖의 키 404 · 계정이 없거나 비밀번호가 맞지 않으면 들여보내지 않는다(409 · 인계표 0)
  · 같은 키로 다시 들어가면 앞 세션이 끊긴다(동시 세션 1개 — 사람의 로그인과 같다)
  · `/qa/keys` 는 비밀 없이 표만 · 지금 키를 안다

캐시 처리: 인계표는 장고 캐시에 둔다 — 시험마다 지운다(아래 fixture).
"""
import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import include, path

from apps.qa import keys as qa_keys

urlpatterns = [path("qa/", include("apps.qa.urls"))]

KEY = "operator_basic_01"


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


def _make_user(key: str, password: str | None = None):
    from core.user.models import CoreUser

    user = CoreUser.objects.create_user(
        username=qa_keys.username_for(key),
        email=f"{key}@fake.qa.invalid",
        password=password or qa_keys.password_for(key),
    )
    for name, value in (("is_active", True), ("otp_exempt", True)):
        if hasattr(user, name):
            setattr(user, name, value)
    if hasattr(user, "last_password_reset"):
        from django.utils import timezone
        user.last_password_reset = timezone.now()
    user.save()
    return user


def _enter(client: Client, key: str = KEY):
    return client.get(f"/qa/as/{key}", REMOTE_ADDR="10.9.9.9")


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_known_key_signs_in_through_the_real_login_and_hands_off_once():
    _make_user(KEY)
    c = Client()
    r = _enter(c)
    assert r.status_code == 302, r.content[:300]
    loc = r["Location"]
    assert loc.startswith("/qa/enter?h=")
    assert "token" not in loc.lower() and "eyJ" not in loc  # 주소에 토큰 0
    h = loc.split("h=", 1)[1]

    got = c.post("/qa/handoff", data={"h": h}, content_type="application/json")
    assert got.status_code == 200
    body = got.json()
    assert body["key"] == KEY and body["first_path"] == qa_keys.QA_KEYS[KEY]["first_path"]
    assert body["user"]["access_token"] and body["user"]["refresh_token"]
    assert body["user"]["username"] == qa_keys.username_for(KEY)

    again = c.post("/qa/handoff", data={"h": h}, content_type="application/json")
    assert again.status_code == 404


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_unknown_key_is_404_and_no_arbitrary_username():
    _make_user(KEY)
    assert _enter(Client(), "admin").status_code == 404
    assert _enter(Client(), qa_keys.username_for(KEY)).status_code == 404  # username 으로는 못 들어간다


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_missing_account_is_refused_without_handoff():
    r = _enter(Client())
    assert r.status_code == 409
    assert "Location" not in r


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_wrong_password_is_refused():
    _make_user(KEY, password="Different-pass-123!")
    r = _enter(Client())
    assert r.status_code == 409


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_reentry_ends_the_previous_session():
    user = _make_user(KEY)
    _enter(Client())
    user.refresh_from_db()
    first = user.token
    _enter(Client())
    user.refresh_from_db()
    assert user.token and user.token != first  # 한 칸 — 새 세션이 덮었다(앞 탭은 끊긴다)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__, QA_BUILD=True)
def test_keys_lists_the_table_without_secrets_and_knows_current():
    _make_user(KEY)
    c = Client()
    before = c.get("/qa/keys").json()
    assert before["current"] is None
    assert [row["key"] for row in before["keys"]] == list(qa_keys.QA_KEYS)
    assert "password" not in str(before).lower()
    _enter(c)
    after = c.get("/qa/keys").json()
    assert after["current"]["key"] == KEY
