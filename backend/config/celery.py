import os
from zoneinfo import ZoneInfo

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_prerun, task_postrun, worker_process_init

from dotenv import load_dotenv
load_dotenv()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create the Celery app
app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

def _seoul_crontab(**kw):
    """이 항목 **하나만** `Asia/Seoul` 로 잰다 — 앱 전역 시간대는 그대로 둔다 (P-260).

    ★ 왜 앱 전역(`app.conf.timezone` · `TIME_ZONE=Asia/Ho_Chi_Minh`, `config/settings.py`)을
      안 바꾸는가 — 이 파일의 `beat_schedule` 에는 13개 항목이 있고, celery 는 앱 전체에
      **시간대 하나**만 갖는다. 전역을 Seoul 로 바꾸면 이 크론 문자열(hour=)들은 그대로인 채
      해석만 바뀌어 **다른 열두 항목이 전부 두 시간 밀린다** — 아무도 부탁하지 않은 변경이다.
      이 턴이 맡은 것은 **백업 하나**고(WO-08 §5 E), 그래서 이 항목만 갈라 바꾼다.

    ★ 어떻게 한 항목만 다른 시간대를 갖는가 — `django_celery_beat` 가 이 crontab 객체를
      DB 의 `CrontabSchedule` 행으로 옮겨 심을 때(`schedulers.py::ModelEntry.to_model_schedule`
      → `CrontabSchedule.from_schedule`) **`schedule.tz` 를 그대로 그 행의 `timezone` 칸에
      적는다.** `crontab.tz` 는 `functools.cached_property`(기본값 `self.app.timezone`)라
      **인스턴스 값으로 덮어쓸 수 있다** — data descriptor 가 아니므로 `c.tz = ...` 가
      인스턴스 사전에 바로 앉고, 그 뒤로는 그 값만 읽힌다. 그래서 이 함수가 만든 crontab
      만 `tz=Asia/Seoul` 을 지니고, 나머지 항목은 여전히 `app.timezone`(Ho_Chi_Minh)을 읽는다.
      (검증: `docker exec gx-shell python -c "from django_celery_beat.models import
      CrontabSchedule; import inspect; print(inspect.getsource(CrontabSchedule.from_schedule))"`
      — `spec['timezone'] = schedule.tz`.)

    ⚠ **살아 있는 `gx-beat-e` 도 재시작 없이 이 값을 읽는다** — `DatabaseScheduler` 는
      매 tick 마다 `Changes` 표의 갱신 시각을 보고, DB 행이 바뀌면 다시 읽는다
      (`schedulers.py::DatabaseScheduler.schedule_changed`). 그래서 이 파일을 고치는 것과
      별개로, **실제 적용은 DB 의 `CrontabSchedule` 행이 바뀌어야** 한다 — 이 턴에서는
      코드만 정본으로 세우고, DB 행 적용 여부는 쪽지(조율자.inbox/E.md)에 실측으로 적는다.
    """
    c = crontab(**kw)
    c.tz = ZoneInfo("Asia/Seoul")
    return c


# Configure Celery Beat schedule
app.conf.beat_schedule = {
    "surveillance-auto-launch-processor": {
        "task": "surveillance.tasks.process_surveillance_auto_launch",
        "schedule": 60.0,  # run every minute to honour 5-minute preflight window
    },
    "surveillance-recurring-profile-generator": {
        "task": "surveillance.tasks.process_surveillance_recurring_profiles",
        "schedule": crontab(hour=0, minute=0),  # run at midnight to ensure all profiles with start_time up to 23:59 are processed
    },
    "surveillance-overdue-profile-check-scheduler": {
        "task": "surveillance.tasks.schedule_surveillance_profile_overdue_checks",
        "schedule": 300.0,  # run every 5 minutes to schedule overdue cancellations with updated config
    },
    "surveillance-overdue-profile-processor": {
        "task": "surveillance.tasks.process_surveillance_profile_overdue",
        "schedule": 60.0,  # run every minute to check and cancel overdue profiles immediately (backup/fallback)
    },
    "terminal-activation-scheduler": {
        "task": "terminals.tasks.schedule_terminal_activation_tasks",
        "schedule": 3600.0,  # run every hour to schedule activation tasks for next hour using ETA
    },
    "terminal-auto-activation-processor": {
        "task": "terminals.tasks.process_terminal_auto_activation",
        "schedule": 60.0,  # run every minute to check and update terminal status (backup/fallback)
    },
    # ── 잠자는 기능 전수에서 나온 자리 (D-377 착시 ⑨ · ㉡ 주기 없음) ────────
    #
    #   ★ 아래 두 줄은 **주석으로 꺼진 beat 항목**이었다. 누군가 켰다가 껐고 사유가
    #     어디에도 없었다. `scripts/verify_dormant.py` 가 이런 항목을 따로 세는 이유다 —
    #     세지 않으면 영원히 안 보인다.
    #
    #   ① 감사 로그 정리 → **켰다.** 다만 `common.ops_audit_purge_beat` 로 감싸서 켠다:
    #      dj-core 태스크는 몇 건을 지웠는지 말하지 않고, 끄는 손잡이도 없다.
    #      (사유 전문은 `common/ops_tasks.py` 의 그 자리에 있다)
    #
    #   ② 비행로그 수집 → **켜지 않는다.** 그리고 그 사유가 둘이다:
    #      · 이 환경의 `OPENSEARCH` 는 `opensearch.invalid` 다 — 닿지 못한다 [실측]
    #      · ★ **이 주석은 켜도 안 돌아간다.** `flight_log.task…` 는 오타이고
    #        실제 모듈은 `flight_log.tasks` 다(`backend/flight_log/task.py` 는 없다).
    #        그대로 풀면 beat 가 15분마다 `NotRegistered` 를 낸다 — **꺼진 채로 틀린**
    #        항목이라 아무도 몰랐다. 이름을 고쳐 두되 끈 채로 둔다: 켜는 날
    #        오타부터 다시 만나지 않게.
    # "flight-log-data-fetch-scheduler": {
    #     "task": "flight_log.tasks.fetch_flight_log_data_from_opensearch",
    #     "schedule": 900.0,  # run every 15 minutes to fetch flight log data from OpenSearch
    # },
    "flight-log-anomaly-prediction-scheduler": {
        "task": "flight_log.tasks.task_update_pending_anomaly_predictions",
        "schedule": 300.0,  # run every 15 minutes to update anomaly predictions
    },
    # ── 운영 자동화 (D-373) ─────────────────────────────────────────────
    #   ★ 도구는 이미 있었다(scripts/ops_*.py · D-354 ①). 없던 것은 **주기**다.
    #     「백업 스크립트가 있다」와 「백업이 매일 돈다」는 다른 사실이고,
    #     사람이 손으로 부르는 백업은 **바쁜 날 안 돌아간다.**
    "ops-monitor-3signals": {
        # 감시 3종 — 살아 있는가 · 밀리는가 · 채워지는가. 읽기만 하므로 **기본 켬**.
        # 5분: 1분이면 로그가 소음이 되고, 1시간이면 죽은 것을 한 시간 뒤에 안다.
        "task": "common.ops_monitor_beat",
        "schedule": 300.0,
    },
    "ops-audit-purge-daily": {
        # ⛔ **여기 「기본 90일」이라고 적혀 있었다. 거짓이었다** (P-67 · 2026-09-06).
        #   지우지 않고 남긴다: `AdminConfig::System` 에 `security.audit_log_retention_days`
        #   가 **없었고**[실측 2026-09-05 OPS-07b · 재확인 09-06], 90은 dj-core
        #   `purge_old_audit_logs` 의 **코드 기본값**이었다 — 아무도 정한 적이 없다.
        #   즉 이 줄은 「고객이 정한 보존기간을 집행한다」가 아니라
        #   **「아무도 안 정한 수로 감사 기록을 하드 삭제한다」**였다.
        #
        # ★ 지금은 `common.ops_audit_purge_beat` 가 **선언을 먼저 묻는다.**
        #   미선언이면 dj-core 태스크를 **부르지 않는다**(호출 0) — 그리고
        #   「미선언이라 건너뛴다」를 증거에 남긴다. 조용히 넘기지 않는다(D-290).
        #
        #   02:40 — 백업(03:00)보다 **앞이다.** 지우기 전의 상태가 백업에 담기면
        #   정리와 백업이 서로를 되돌릴 수 없게 된다. (백업이 03:30 → 03:00 으로
        #   당겨졌으므로 이 줄도 함께 당긴다 — 순서가 뜻이지 시각이 뜻이 아니다.)
        "task": "common.ops_audit_purge_beat",
        "schedule": crontab(hour=2, minute=40),
    },
    "law02a-video-retention-sweep": {
        # ★ LAW-02a 영상 보존기간 집행 — **안내판에 인쇄되는 수가 여기서 참이 된다.**
        #   02:50 — 감사 정리(02:40) 뒤, 백업(03:00) **앞**이다. 앞에 두는 이유는
        #   위가 적어 둔 것과 같다: 지우기 전의 상태가 백업에 담기면 정리와 백업이
        #   서로를 되돌릴 수 없게 된다.
        #   ⚠ 이 줄을 지우면 「보관 기간이 지난 영상은 자동으로 지워집니다」가
        #     거짓이 된다. 지우려면 그 문장을 화면에서 함께 내려야 한다 —
        #     `retention.policy()['enforced']` 가 이 줄의 실재를 그대로 잰다.
        #   ★ P-67 뒤로 `policy()['enforced']` 는 **두 조건이 다 참일 때만** 참이다:
        #     이 줄이 있고(주기) 보존 일수가 선언돼 있을 것(수). 주기만 있고 수가
        #     없으면 아무것도 안 지워지는데 「지워집니다」가 초록으로 나갔다.
        "task": "common.video_retention_sweep_beat",
        "schedule": crontab(hour=2, minute=50),
    },
    "sec-key-rotation-watch-daily": {
        # SEC-07 — 돌려야 할 들어오는 키를 **말한다.** 돌리지는 않는다.
        #   03:50 — 정리(03:10)·백업(03:30) 뒤다. 하루의 정리가 끝난 뒤에 내일의 빚을 센다.
        #   ★ 자동 회전을 걸지 않는 이유: 회전은 상대의 연동을 흔들고,
        #     끊긴 쪽에서는 **우리 잘못으로 보이지 않는다.** 흔드는 시각은 사람이 정한다.
        "task": "common.key_rotation_watch_beat",
        "schedule": crontab(hour=3, minute=50),
    },
    "ops-backup-daily": {
        # ★ **매일 05:00 (Asia/Seoul 정본 · P-260 · 턴 AE 차선 E)** — 세종 판정 P-67 이
        #   정한 순간은 그대로다. 옛 표기는 **03:00 (Asia/Ho_Chi_Minh)** — 두 표기는
        #   **같은 순간**이다(HCM +07:00 03:00 = UTC 20:00(전날) = Seoul +09:00 05:00).
        #   이 항목만 `_seoul_crontab()` 로 짓는다 — 그 이유·검증은 그 함수의 docstring.
        #   ⚠ 소리 없이 바꾸지 않는다: 옛 03:00 도 새 05:00 도 **가리키는 순간은 하나**이고,
        #     이전 실측 기록(예: OPS-19 자동덤프 · `2026-09-23 03:00:00 Ho_Chi_Minh`)을
        #     KST 로 다시 읽으면 **05:00 KST** 다. 기록을 고치는 것이 아니라 읽는 잣대를
        #     하나로 세우는 것이다.
        #
        #   그 전까지 이 줄은 03:30 에 있었고 **태스크가 스스로 꺼져 있었다**
        #   (`OPS_BACKUP_SCHEDULE_ENABLED` 기본 False · `OPS_BACKUP_DIR` 빈 문자열).
        #   그래서 「등록돼 있는데 백업이 한 번도 저장된 적 없다」였다 — OPS-19 가
        #   태어난 자리이자 착시 ⑨(등록만 하고 안 도는 것)의 원형이다.
        #
        # ★ 지금 켜 주는 것은 코드의 기본값이 **아니다.** 개발·스테이징이 선언했다:
        #   `backend/config/retention_seed.py` (켬 · 목적지 `/backup` · 보존 14일).
        #   운영에서는 그 시드가 한 칸도 안 읽히므로 **여전히 꺼져 있고**, 그것이 옳다 —
        #   「어디에 얼마나 오래 쌓을 것인가」는 고객이 U5 에서 정한다.
        #
        # ★ 호출자 칸(P-264) — beat 이 이 항목으로 부를 때만 `invoked_by="beat"` 가 실린다.
        #   사람이 셸에서 `ops_backup_beat()` 를 바로 부르면 이 kwargs 가 없으니 함수
        #   기본값 `"manual"` 이 판정문에 남는다 — 판정문 한 장으로 beat 과 사람이 갈린다.
        "task": "common.ops_backup_beat",
        "kwargs": {"invoked_by": "beat"},
        "schedule": _seoul_crontab(hour=5, minute=0),
    },
    "ops-restore-drill-weekly": {
        # ★ **복구 시험 주 1회 자동** — 세종 판정 P-67 (2026-09-06).
        #   「복구를 해 보지 않은 백업은 백업이 아니다」(D-354 ①)를 **주기로** 만든 자리다.
        #   백업(03:00)에서 세 시간 뒤 일요일 06:00 — 그날치 백업이 다 뜬 뒤에 잰다.
        #
        # ⚠ 이 태스크는 **원본 DB 를 건드리지 않는다.** `restore_check_` 로 시작하는
        #   임시 DB 에 되살리고 지운다(`scripts/ops_restore.py` 의 세 겹 안전장치와 같은 규약).
        #   그리고 **RTO 를 분으로 재서 기록한다** — 「살아난다」만으로는 SLA 의
        #   복구 목표(GX-LAW-05 · RTO 30분)를 약속할 수 없다.
        "task": "common.ops_restore_drill_beat",
        "schedule": crontab(hour=6, minute=0, day_of_week=0),
    },
    # ── 2파 (2026-09-24) — 차선 Q 가 함수를 짓고 조율자가 주기를 건다 ────────
    "ops14-heartbeat-digest": {
        # ★ OPS-14 생존 알림 — 매일 08:00 한 통. **안 오면 장애다.**
        #   서버 1대다. 죽으면 탐지도 알림도 멈추는데 **침묵과 정상은 같은 모양**이다.
        #   이 한 통이 그 둘을 가른다 — 그래서 이 항목이 꺼지면 감시가 꺼진다.
        "task": "common.heartbeat_digest_beat",
        "schedule": crontab(hour=8, minute=0),
    },
    "u24-monthly-report": {
        # ★ UX-40 월간 자동본 — **매월 1일 03:00** (턴 U · 결정 ⑤ DOCX 정본).
        #   재난안전과(U4)는 `view_only_*` 라 **스스로 만들 수 없다**(문지기 403) — 배치가
        #   만들어 두고 사람은 내려받는다. 이 줄이 빠지면 U4 의 월간 보고는 조용히 사라진다.
        #   백업(03:00)과 같은 시각이지만 다른 큐·다른 자원이고, 집계는 DB 읽기뿐이다.
        "task": "common.monthly_report_beat",
        "schedule": crontab(day_of_month="1", hour=3, minute=0),
    },
    "law08-evidence-anchor": {
        # ★ LAW-08 일일 앵커 — 00:05. 자정 **직후**에 어제 것을 닫는다.
        #   00:00 정각에 두면 그 순간 쓰이는 감사 행이 어제인지 오늘인지 갈린다.
        "task": "common.evidence_anchor_beat",
        "schedule": crontab(hour=0, minute=5),
    },
    "ops15-camera-pulse-scan": {
        # ★ OPS-15 카메라 맥박 군집 두절 — **1분**. 규칙의 창이 5분이라 5분 주기로 재면
        #   창 하나를 통째로 놓칠 수 있고, 놓친 군집 두절은 아무 흔적도 안 남긴다.
        "task": "stream_monitors.camera_pulse_scan_beat",
        "schedule": 60.0,
    },
}

# Additional Celery configurations to fix timeout issues
app.conf.update(
    # Worker settings
    worker_prefetch_multiplier=1,  # Cần = 1 để priority hoạt động đúng
    task_acks_late=True,
    worker_disable_rate_limits=True,

    # Task priority settings (số nhỏ hơn = priority cao hơn)
    task_default_priority=10,  # Priority mặc định cho các task thông thường
    task_inherit_parent_priority=True,  # Task con kế thừa priority từ task cha

    # 🔐 FIX: Database connection settings for multiprocessing
    worker_pool_restarts=True,  # Restart workers periodically to prevent connection issues
    worker_max_tasks_per_child=1000,  # Limit tasks per worker to prevent connection leaks
    worker_concurrency=4,  # Limit concurrent workers to manage connections

    # Connection and retry settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_connection_timeout=30,
    broker_transport_options={
        'socket_connect_timeout': 30,
        'socket_timeout': 30,
        'socket_keepalive': True,
        'socket_keepalive_options': {},
        'retry_on_timeout': True,
        'max_connections': 20,
    },

    # Task cancellation on connection loss
    worker_cancel_long_running_tasks_on_connection_loss=True,

    # Tất cả tasks sẽ được gửi đến default queue
    # task_routes={
    #     'orders.tasks.*': {'queue': 'orders'},
    #     'delivery.tasks.*': {'queue': 'delivery'},
    #     'delivery.signals.*': {'queue': 'delivery'},
    #     'stream_monitors.tasks.*': {'queue': 'stream'},
    # },

    # Chỉ sử dụng default queue
    task_default_queue='default',

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': "mymaster",
        'visibility_timeout': 3600,
    },

    # Beat settings
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
    beat_sync_every=1,
    beat_max_loop_interval=300,
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# 🔐 Database connection management for Celery tasks
@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize worker process and close any stale database connections."""
    from django.db import connections
    # Close all existing connections when worker starts
    connections.close_all()


@task_prerun.connect
def close_db_connections_before_task(**kwargs):
    """
    Close old database connections before each task runs.
    This prevents 'server closed the connection unexpectedly' errors.
    """
    from django.db import close_old_connections
    close_old_connections()


@task_postrun.connect
def close_db_connections_after_task(**kwargs):
    """
    Close database connections after each task completes.
    This ensures connections are properly cleaned up.
    """
    from django.db import connections
    connections.close_all()
