import os
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
        # ★ 백업과 달리 **기본으로 켠다.** 보존기간의 답이 제품 안에 이미 있기 때문이다
        #   (`System > security.audit_log_retention_days`, 기본 90일).
        #   꺼 두면 **고객이 정한 보존기간이 아무 일도 하지 않는다** — 그것이 착시 ⑨ 다.
        #   03:10 — 백업(03:30)보다 **앞이다.** 지우기 전의 상태가 백업에 담기면
        #   정리와 백업이 서로를 되돌릴 수 없게 된다.
        "task": "common.ops_audit_purge_beat",
        "schedule": crontab(hour=3, minute=10),
    },
    "ops-backup-daily": {
        # ★ 이 주기는 등록되지만 **태스크가 스스로 꺼져 있다**
        #   (`OPS_BACKUP_SCHEDULE_ENABLED` 기본 False).
        #   여기서 빼지 않고 등록해 두는 이유: 빼 두면 켜는 날 **아무도 이 자리를 못 찾는다.**
        #   등록해 두면 「꺼져 있다」가 로그에 매일 한 줄로 보인다 — 조용한 부재보다 낫다(D-290).
        "task": "common.ops_backup_beat",
        "schedule": crontab(hour=3, minute=30),
    },
    # ── 2파 (2026-09-24) — 차선 Q 가 함수를 짓고 조율자가 주기를 건다 ────────
    "ops14-heartbeat-digest": {
        # ★ OPS-14 생존 알림 — 매일 08:00 한 통. **안 오면 장애다.**
        #   서버 1대다. 죽으면 탐지도 알림도 멈추는데 **침묵과 정상은 같은 모양**이다.
        #   이 한 통이 그 둘을 가른다 — 그래서 이 항목이 꺼지면 감시가 꺼진다.
        "task": "common.heartbeat_digest_beat",
        "schedule": crontab(hour=8, minute=0),
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
