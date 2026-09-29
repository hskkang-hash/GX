# -*- coding: utf-8 -*-
"""DSM App 의 URL 등록. `config/urls.py` 가 `api/dsm/` 로 include 한다.

기존 앱들과 같은 모양(`NinjaExtraAPI` + `register_controllers`)을 쓴다 —
새 방식을 들이면 라우트 열거기(`common.tenant_scope.enumerate_operations`)가
그 방식을 모르고, 모르는 라우트는 **트립와이어의 눈 밖**이 된다.
"""
from django.urls import path
from ninja_extra import NinjaExtraAPI

from apps.dsm.api import DsmAPI
from apps.dsm.api_f import DsmFAPI
from apps.dsm.api_f_ops import DsmFOpsAPI
from apps.dsm.api_u1 import DsmU1API
from apps.dsm.api_u3 import DsmU3API
from apps.dsm.api_u4 import DsmU4API
from apps.dsm.api_u24 import DsmU24API
from apps.dsm.api_u56 import DsmU56API
from apps.dsm.api_u5_perm import DsmU5PermAPI
from apps.dsm.api_u5_an import DsmU5AnAPI
from apps.dsm.api_ops_an import DsmOpsAnAPI
from apps.dsm.api_u36_an import DsmU36AnAPI
from apps.dsm.law_api import DsmLawAPI

dsm_api = NinjaExtraAPI(urls_namespace="dsm")
#: ★ 컨트롤러 둘. 법·인증 면(LAW-02a · LAW-06 · LAW-07)은 별도 파일에 산다 —
#:   같은 턴에 두 차선이 한 라우트 파일을 고치면 충돌하고, 충돌한 라우트는
#:   **라우팅 침묵**으로 나타난다(경로가 사라졌는데 오류도 안 난다).
#: ★ [턴 Q · WO-01 §4.2] 사용자축 차선 라우터 넷은 기존 둘 **뒤에** 붙인다 — 선언 순서가
#:   곧 라우팅이라, 뒤에 붙은 것은 앞의 경로를 가리지 못한다. 기존 라우트는 `api.py` 에
#:   그대로 둔다(옮기면 무엇이 무엇을 삼키는지가 바뀐다). 한 파일은 한 차선.
#: ★ [턴 R · 차선 F] `DsmFAPI`(온보딩 진행률)도 **뒤에** 붙인다 — 같은 규약이다.
#:   새 경로(`/onboarding/...`)는 앞 컨트롤러의 변수 조각 밑에 없으므로 삼킴이 없다.
#: ★ [턴 V · 차선 F] `DsmFOpsAPI`(점검 창 기록 문) — **맨 뒤**다. 새 경로
#:   (`/system/requests/{id}/handled`)를 삼킬 변수 조각이 앞에 없다 [실측: `/system/`
#:   경로 넷 전부 고정 조각]. 온보딩 라우터와 **다른 파일**인 이유는 그 파일에
#:   쓰기 문이 있으면 `verify_onboarding_walk` 가 옳게 빨개지기 때문이다(api_f_ops 머리말).
#: ★ [턴 AM · 차선 O · P-376] `DsmU5PermAPI`(사람별 카메라·기능 권한) — **맨 뒤**다.
#:   새 경로(`/access-log/permissions`)는 `api_u24.py` 의 `/access-log`·
#:   `/access-log/export.csv`(둘 다 완전한 리터럴, 변수 조각 없음) 뒤에 안전하게
#:   붙는다[실측 확인]. `api_u24.py` 는 차선 N1 소유라 이번 턴은 그 파일을 고치지
#:   않고 새 컨트롤러로 연다.
#: ★ [턴 AM · 차선 N4 · WO-15 §5] `DsmU4API`(U4 재난안전과 담당 — 상황보고서
#:   제N보·CBS 초안·통제현황판·영상제공대장·근무표 CSV) — **맨 뒤**다. 새 경로
#:   (`situation-reports`·`cbs-drafts`·`control-points`·`video-access-requests`·
#:   `shifts`·`shifts/import`)는 앞의 어느 리터럴·변수 조각과도 안 겹친다
#:   (`api_u4.py` 머리말의 grep 전수 실측).
dsm_api.register_controllers(
    DsmAPI, DsmLawAPI,
    DsmU1API, DsmU3API, DsmU24API, DsmU56API,
    DsmFAPI, DsmFOpsAPI,
    DsmU5PermAPI, DsmU4API,
    DsmU5AnAPI,  # 턴 AN · 차선 N4 — 맨 뒤(새 리터럴은 차선이 겹침 grep)
    DsmOpsAnAPI, DsmU36AnAPI,  # 턴 AO · 차선 N3 · N4 — 맨 뒤
)

urlpatterns = [
    path("", dsm_api.urls),
]
