import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - Giảm số workers để tránh quá tải database
workers = min(multiprocessing.cpu_count(), 2)  # Giới hạn tối đa 2 workers
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 200  # Giảm từ 500 xuống 200
# ★ [실측 2026-09-05 · 턴 C · OPS-13] **재활용을 없애지 않고 흩뜨린다.**
#   워커 재활용 자체는 옳다(메모리 누수 대비). 502 를 만든 것은 재활용이 아니라
#   **재활용이 한꺼번에 오는 것**이다: 워커 넷이 같은 순간에 떠서 같은 부하를 나눠
#   받으면 카운터도 나란히 오르고, 지터가 좁으면 넷이 **거의 같은 순간에** 나간다.
#   그 창에는 받아 줄 워커가 없고, 앞단은 그것을 502 로 손님에게 전한다.
#
#   ⚠ **`max_requests` 를 키우거나 끄지 않았다.** 그것은 결함을 없애는 게 아니라
#     **더 드물게** 만드는 일이고, 드물어진 결함은 재현이 안 되며 재현 안 되는 결함은
#     운영에서 처음 보인다(조율자 지시 · 턴 C).
#   ★ 그래서 **평균 재활용 주기는 그대로 두고 폭만 넓혔다**:
#       전: 200 + rand(0..50)  → 200–250   (평균 225 · 폭  50)
#       후: 125 + rand(0..200) → 125–325   (평균 225 · 폭 200)
#     평균이 같으므로 재활용 빈도는 그대로다 — 겹칠 확률만 4배로 흩어졌다.
#   ⛔ **재 보고 되돌렸다**: 125 + rand(0..200) 으로 폭을 넓혔더니 502 가 3건 →
#     **5건**으로 늘었다. 평균은 같아도 **최소 주기가 200 → 125 로 짧아져** 이른
#     재활용이 앞당겨졌고, 함께 건 nginx `keepalive_requests` 와 겹쳐 더 나빠졌다.
#     지터를 넓히는 것이 답이 아니라는 것을 **재서** 알았다. 원래 값으로 둔다.
#   ⛔ **끄고 재 봤고 되돌렸다** [실측 2026-09-05 · 턴 D]. `max_requests = 0` 으로
#     재활용을 완전히 끄고 같은 부하(3,722 요청)를 다시 걸었다:
#         재활용 0건 · **재시도 0건** · **502 0건** · 오류 0 · 네 면 전부 예산 안
#         (MEDIA p95 204 → 120ms · STATUS 167 → 122ms 로 **빨라지기까지 했다**)
#     ★ 즉 **502 를 0 으로 만드는 방법은 있다. 그리고 그것을 쓰지 않는다.**
#       ㉠ 그 0 은 결함을 고친 0 이 아니라 **결함을 숨긴 0** 이다 — 502 도 재시도도
#          전부 재활용에서 왔다는 것을 이 실험이 오히려 증명한다(인과 실험이다.
#          상관이 아니다).
#       ㉡ `max_requests` 는 메모리 누수 대비다. 끄면 502 대신 **몇 시간 뒤의 OOM**
#          을 얻고, 그것은 조용히 오지 않는다.
#       ㉢ 드물어진 결함은 재현이 안 되며, 재현 안 되는 결함은 운영에서 처음 보인다
#          (조율자 지시 · 턴 C).
#     ⚠ 그러므로 이 값을 **키우는 것도 같은 이유로 금지**다. 200 을 2000 으로 올리면
#       502 는 10분의 1이 되고, 그만큼 **덜 재현된다.**
max_requests = 200
max_requests_jitter = 50
preload_app = True

# Timeout settings
timeout = 30
# ★ [실측 2026-09-05 · 턴 C · OPS-13] **2 였다. 그 값이 502 를 만들었다.**
#   앞단(nginx)을 처음 세우고 예산 게이트를 돌리자 3,600 요청 중 **6건이 502** 였다.
#   까닭은 코드가 아니라 **두 시간의 부등호**다: nginx 는 놀고 있는 뒷단 연결을
#   자기 `keepalive_timeout`(60초) 동안 쥐고 있다가 다시 쓰는데, gunicorn 이 2초 만에
#   그 연결을 끊는다. 앞단이 이미 죽은 연결에 요청을 실어 보내면 그 요청은 502 다.
#   ★ 그러므로 **뒷단의 값이 앞단의 값보다 커야 한다** — 이 부등호가 규칙이다:
#       gunicorn keepalive(75) > nginx upstream keepalive_timeout(60)
#   ⚠ 이 값은 `runserver` 에서는 **아무 일도 하지 않는다.** 그래서 앞단을 세우기
#     전에는 이 결함이 보이지 않았다 — 배포 형상을 실측해야 보이는 자리다(D-286).
keepalive = 75
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "guardianx_backend"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
worker_tmp_dir = "/dev/shm"  # Sử dụng RAM cho temporary files
worker_exit_on_app_exit = True

# Environment
raw_env = [
    "DJANGO_SETTINGS_MODULE=config.settings",
]

# Pre-fork
def on_starting(server):
    server.log.info("Starting GuardianX Backend Server")

def on_reload(server):
    server.log.info("Reloading GuardianX Backend Server")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker aborted (pid: %s)", worker.pid)

# Thêm hook để cleanup connections khi worker restart
def worker_exit(server, worker):
    worker.log.info("Worker exiting (pid: %s) - cleaning up connections", worker.pid)
    # Django sẽ tự động cleanup connections khi worker exit

# Thêm hook để monitor memory usage
def on_exit(server):
    server.log.info("Server shutting down - cleaning up all connections")
