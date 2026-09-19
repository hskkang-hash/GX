#!/bin/sh
# P-183 후반 — 게이트 서버 둘을 **한 줄로** 세우고 죽인다. `gx-shell` **안에서** 돈다.
#
# 세종 P-183:
#     gx-shell 안 게이트 서버 둘(runserver 8000 · SPA 3002)은 컨테이너 entrypoint/supervisor
#     로 올려 재시작 정책이 **프로세스까지** 덮게 — 손으로 띄운 프로세스 0.
#
# ★ 이 파일 혼자로는 「손으로 띄운 프로세스 0」이 되지 않는다. 그건 `gx-shell` 을 **다시
#   만들어야** 되는 일이고(아래 「왜 아직 0 이 아닌가」), 이 파일은 그날 entrypoint 가
#   **그대로 부를** 모양으로 미리 서 있는 것이다. 그때까지는 조율자가 손으로 부르되,
#   **부르는 법이 하나**가 된다 — 지금은 두 서버가 어떻게 떴는지 아무 데도 안 적혀 있다.
#
# ★ 왜 아직 0 이 아닌가 (2026-09-19 실측):
#   ① 도는 컨테이너 **열 개 전부** compose 라벨이 비어 있다 — `docker inspect -f
#      '{{index .Config.Labels "com.docker.compose.project"}}'` 가 전부 빈 값이다.
#      손으로 `docker run` 한 것이다. 그래서 `docker-compose.yml` 을 고쳐도 **지금 도는
#      것에는 닿지 않는다**(compose 파일 자신이 그 사실을 이미 적어 두고 있다).
#   ② `gx-shell` 의 entrypoint 는 `sleep infinity` 이고, 그건 실수가 아니라 **존재 이유**다
#      — compose 주석: 「이 두 줄이 이 서비스의 존재 이유다. entrypoint 를 비워 자동
#      migrate 를 끊는다」. 여기에 서버를 넣는 것은 그 결정을 뒤집는 일이라 같이 판정받아야
#      한다.
#   ③ 다시 만들면 컨테이너 안 상태(pip·캐시·`/tmp/gx_spa_server.py`)가 사라지고, 무엇보다
#      **그 위에서 일하는 차선들이 같이 죽는다.** 「창과 다른 변경을 섞지 않는다」.
#   → 조율자 위임 이의 #3 으로 올린다. 재생성은 **창** 일이다.
#
# 쓰는 법 (호스트에서):
#   docker exec gx-shell sh /repo/scripts/gate_servers.sh status
#   docker exec gx-shell sh /repo/scripts/gate_servers.sh start
#   docker exec gx-shell sh /repo/scripts/gate_servers.sh restart
set -u

RUN_DIR=/tmp/gx_gates
LIVE_DIR="${GX_LIVE_DIR:-/app/_fe_dist}"
SPA_PORT="${GX_SPA_PORT:-3002}"
API_PORT="${GX_API_PORT:-8000}"
SPA_SRC=/repo/scripts/gate_spa_server.py
SPA_RUN=/tmp/gx_spa_server.py

mkdir -p "$RUN_DIR"

# ── 누가 8000/3002 를 물고 있는가 — **pid 파일이 아니라 포트를 본다** ─────────────
# pid 파일은 거짓말한다(프로세스가 죽어도 파일은 남고, 남의 프로세스가 그 번호를 물려받는다).
# 우리가 알고 싶은 것은 「누가 띄웠나」가 아니라 **「지금 그 문이 서 있나」**다.
listener_pid() {   # $1 = port
    for d in /proc/[0-9]*; do
        p=${d#/proc/}
        c=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null) || continue
        case "$c" in
            *"runserver 0.0.0.0:$1"*) echo "$p"; return 0 ;;
            *gx_spa_server.py*)
                if [ "$1" = "$SPA_PORT" ]; then echo "$p"; return 0; fi ;;
        esac
    done
    return 1
}

port_answers() {   # $1 = port · 실제로 **대답하는가**. 떠 있는 것과 대답하는 것은 다르다
    python - "$1" <<'PY' 2>/dev/null
import sys, urllib.request
port = sys.argv[1]
try:
    urllib.request.urlopen("http://127.0.0.1:%s/" % port, timeout=3)
except urllib.error.HTTPError:
    pass                      # 4xx/5xx 도 **대답한 것**이다
except Exception:
    sys.exit(1)
sys.exit(0)
PY
}

started_by() {     # 손인가 이 파일인가 — 표식으로 가른다
    [ -f "$RUN_DIR/$1.by" ] && cat "$RUN_DIR/$1.by" || echo "손(표식 없음)"
}

cmd_status() {
    rc=0
    for pair in "api:$API_PORT" "spa:$SPA_PORT"; do
        name=${pair%%:*}; port=${pair##*:}
        pid=$(listener_pid "$port" || true)
        if [ -n "${pid:-}" ]; then
            if port_answers "$port"; then ans="대답한다"; else ans="**안 대답한다**"; rc=1; fi
            echo "[GATES] $name  $port  pid $pid  $ans  · 띄운 것: $(started_by "$name")"
        else
            echo "[GATES] $name  $port  **없다**"
            rc=1
        fi
    done
    return $rc
}

start_one() {      # $1=name $2=port $3=명령...
    name=$1; port=$2; shift 2
    pid=$(listener_pid "$port" || true)
    if [ -n "${pid:-}" ]; then
        echo "[GATES] $name 이미 서 있다 (pid $pid) — 두 번 띄우지 않는다"
        return 0
    fi
    echo "[GATES] $name 띄운다: $*"
    ( cd /app && "$@" > "$RUN_DIR/$name.log" 2>&1 & echo $! > "$RUN_DIR/$name.pid" )
    echo "gate_servers.sh $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RUN_DIR/$name.by"
    # ★ 띄운 직후는 아직 안 선다. **대답할 때까지 기다렸다가** 대답을 본 뒤 초록이라 한다.
    i=0
    while [ $i -lt 20 ]; do
        if port_answers "$port"; then echo "[GATES] $name 대답한다 ($port)"; return 0; fi
        i=$((i+1)); sleep 1
    done
    echo "[GATES] $name **안 선다** — 자취: $RUN_DIR/$name.log"
    tail -5 "$RUN_DIR/$name.log" 2>/dev/null
    return 1
}

cmd_start() {
    # SPA 서버 본문은 **저장소 것을 쓴다.** `/tmp` 사본이 낡으면 거짓 초록의 씨가 된다
    # (D-493 · 턴 V 에 `deploy.sh` 안에서 같은 씨를 뽑았다).
    if [ -f "$SPA_SRC" ]; then
        cp "$SPA_SRC" "$SPA_RUN"
    else
        echo "[GATES] **$SPA_SRC 가 없다** — /repo/scripts 가 안 붙었다. 멈춘다"; return 2
    fi
    rc=0
    start_one api "$API_PORT" python manage.py runserver "0.0.0.0:$API_PORT" --noreload || rc=1
    GX_LIVE_DIR="$LIVE_DIR" GX_SPA_PORT="$SPA_PORT" \
        start_one spa "$SPA_PORT" python "$SPA_RUN" || rc=1
    return $rc
}

cmd_stop() {
    for pair in "api:$API_PORT" "spa:$SPA_PORT"; do
        name=${pair%%:*}; port=${pair##*:}
        pid=$(listener_pid "$port" || true)
        if [ -n "${pid:-}" ]; then
            echo "[GATES] $name 죽인다 (pid $pid)"; kill "$pid" 2>/dev/null || true
        else
            echo "[GATES] $name 없다 — 죽일 것 없음"
        fi
        rm -f "$RUN_DIR/$name.by" "$RUN_DIR/$name.pid"
    done
    sleep 2
}

case "${1:-status}" in
    status)  cmd_status ;;
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_stop; cmd_start ;;
    *) echo "쓰는 법: $0 status|start|stop|restart"; exit 2 ;;
esac
