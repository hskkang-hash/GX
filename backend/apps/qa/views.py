# -*- coding: utf-8 -*-
"""QA 진입(`/qa/*`) — WO-GRDX-20261002-09 · 규격 09 M1(이중 잠금)의 뒷단 자리.

이 파일은 **잠금의 뼈대**다. `/qa/as/<사용자키>` 가 실제로 세션을 내주는 일(M2)은 AC-2 몫이고,
지금은 QA 빌드에서도 「아직 없음」(501)만 답한다 — 인증을 건너뛰는 코드는 여기 한 줄도 없다.

잠금 둘:
  ① 등록 — `config/urls.py` 가 `settings.QA_BUILD` 가 참일 때만 `qa/` 조각을 include 한다.
     거짓이면 라우트 자체가 없다 → 장고 404(고객 말 「없는 화면입니다」).
  ② 런타임 — 등록됐더라도 요청마다 `settings.QA_BUILD` 를 다시 본다. 거짓이면 404.
     (설정이 실행 중에 바뀌거나, 누가 urls 를 손으로 고쳐도 문은 열리지 않는다.)
운영 프로필(`settings_prod`)에는 `QA_BUILD` 가 없다 — 기본값 거짓.
"""
from django.conf import settings
from django.http import Http404, JsonResponse


def _locked() -> bool:
    return not bool(getattr(settings, "QA_BUILD", False))


def qa_as(request, key: str):
    if _locked():
        raise Http404()
    return JsonResponse({"detail": "QA entry not implemented yet (WO-GRDX-20261002-09 AC-2)"}, status=501)
