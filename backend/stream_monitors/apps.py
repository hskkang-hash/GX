from django.apps import AppConfig


class StreamMonitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stream_monitors'

    def ready(self):
        # ★ 오탐 결합 소비자를 **여기서 잇는다** (P-16 · 2026-09-20).
        #   신호 수신자는 모듈이 import 될 때 등록된다. 아무도 import 하지 않으면
        #   결합은 **코드에는 있고 돌지는 않는 상태**가 된다 — 이 저장소가 D-377 에서
        #   326건으로 만난 「잠자는 기능」의 모양 그대로다. 그래서 앱이 설 때 잇는다.
        from stream_monitors.services import false_positive_closer  # noqa: F401

        # ★ UX-25 — **테넌트가 생기면 제품 메뉴가 함께 선다** (세종 P-61 §4).
        #   같은 이유로 여기서 잇는다: 수신자는 모듈이 import 될 때 등록되고,
        #   아무도 import 하지 않으면 「코드에는 있고 돌지는 않는 상태」가 된다.
        #   ⚠ 이 줄을 지우면 새 테넌트·새 역할의 사이드바가 조용히 빈다.
        from common import product_menu_signals  # noqa: F401
