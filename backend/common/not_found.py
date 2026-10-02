# -*- coding: utf-8 -*-
"""없는 주소 · 서버 오류가 **고객 말의 화면**을 내게 한다 — WO-GRDX-20261002-06 AC-2·AC-3.

출생 표본 [실측 2026-10-02 19:3x · 세종 클릭 · 영실 20:3x 재측]
    GET http://localhost:8500/start          -> 404 · 장고 디버그 화면(「Django tried these URL patterns」 29줄)
    GET http://localhost:8500/no-such-page   -> 404 · 같은 화면
    GET http://localhost:8500/api/x          -> 404 · 같은 화면
8500 의 gunicorn 이 개발 프로필(`DJANGO_DEBUG=True`)로 떠 있어 주소 규칙 목록과
「DEBUG = True」 문장이 고객 화면에 그대로 나갔다. 바깥 주소를 여는 순간 S1 이다.

두 겹으로 막는다.
  (1) 운영 모양 서버를 `DEBUG=False` 로 띄운다(금고 env-file · 재생성 창). 그래야 장고가
      이 처리기를 부른다 — DEBUG 가 켜져 있으면 장고는 처리기를 건너뛰고 디버그 화면을 낸다.
  (2) 이 처리기: 사람 화면 주소는 한국어 「없는 화면입니다 · 로그인으로」(제품 로고 · 404),
      `/api/` 는 JSON. **주소 규칙 · 예외 문장 · 경로를 본문에 싣지 않는다.**

문구: 지시서 AC-2 의 글자 그대로(「없는 화면입니다 · 로그인으로」). 서버 오류 화면의 문구는
제품 사전에 없어 지어내지 않고 같은 틀에 「잠시 뒤 다시 시도해 주세요」 한 줄만 둔다 — 보고서에 제안으로 적는다.
되돌리기: `config/urls.py` 의 `handler404` · `handler500` 두 줄을 지운다.
"""
from django.http import HttpResponse, JsonResponse

API_PREFIX = "/api/"

_PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GuardianX</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
         font-family: Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
         background: #f5f6f8; color: #1f2329; }}
  main {{ text-align: center; padding: 32px 16px; }}
  img {{ height: 40px; margin-bottom: 24px; }}
  h1 {{ font-size: 20px; margin: 0 0 12px; }}
  p {{ margin: 0 0 24px; color: #4e5562; }}
  a {{ display: inline-block; padding: 12px 20px; border-radius: 8px; background: #1f6feb; color: #fff;
       text-decoration: none; font-weight: 600; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #15181d; color: #e6e8eb; }}
    p {{ color: #a9b0bb; }}
  }}
</style>
</head>
<body>
<main>
  <img src="/logoguax.svg" alt="GuardianX">
  <h1>{title}</h1>
  {line}
  <a href="/login">로그인으로</a>
</main>
</body>
</html>
"""


def _is_api(request) -> bool:
    return request.path.startswith(API_PREFIX)


def page_not_found(request, exception=None):
    if _is_api(request):
        return JsonResponse({"detail": "Not Found"}, status=404)
    body = _PAGE.format(title="없는 화면입니다", line="")
    return HttpResponse(body, status=404, content_type="text/html; charset=utf-8")


def server_error(request):
    if _is_api(request):
        return JsonResponse({"detail": "Internal Server Error"}, status=500)
    body = _PAGE.format(title="잠시 뒤 다시 시도해 주세요", line="")
    return HttpResponse(body, status=500, content_type="text/html; charset=utf-8")
