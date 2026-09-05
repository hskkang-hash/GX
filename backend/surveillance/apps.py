from django.apps import AppConfig


class SurveillanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'surveillance'
    verbose_name = 'Surveillance & GCS Management'

    def ready(self):
        """UX-08 — **두 번째 겹을 여기서 연다.**

        시그널 파일이 있고 데코레이터가 붙어 있어도, **아무도 그 모듈을 import
        하지 않으면 시그널은 붙지 않는다.** 코드에는 있고 돌지는 않는 상태 —
        이 저장소가 「잠자는 기능」이라 이름 붙인 그 모양이다.

        ⚠ `try/except ImportError: pass` 로 감싸지 않는다. 감싸면 import 오류를
          삼켜 **다시 조용히 꺼진다.** 꺼진 것을 모르는 것이 꺼진 것보다 나쁘다.
        """
        from surveillance import signals  # noqa: F401
