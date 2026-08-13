import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - Giảm số workers để tránh quá tải database
workers = min(multiprocessing.cpu_count(), 2)  # Giới hạn tối đa 2 workers
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 200  # Giảm từ 500 xuống 200
max_requests = 200  # Giảm từ 500 xuống 200 để restart workers thường xuyên hơn
max_requests_jitter = 50
preload_app = True

# Timeout settings
timeout = 30
keepalive = 2
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
