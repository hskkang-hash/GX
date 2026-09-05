#!/bin/sh
# ============================================================================
# STAGING ① — **빈 기계 하나를 스테이징으로 세운다** (2026-09-05 · 차선 E · 턴 F)
# ============================================================================
#
# ★ 이 파일이 지금 존재하는 이유
#   대표 승인이 아직 안 났고 **서버는 없다.** 그런데 승인이 난 날 사람이 손으로
#   순서를 기억해 세우면, 그 순서는 다음에 재현되지 않는다. 그러므로 승인 전에
#   할 수 있는 것을 다 해 둔다: **순서를 파일로 못박고, 그 파일을 dry-run 으로
#   돌려서 순서 자체에 구멍이 없는지 먼저 잰다.**
#
# ★ **기본값은 dry-run 이다** (D-209). 되돌릴 수 없는 일 — 컨테이너를 세우고
#   마이그레이션을 돌리고 버킷을 만드는 일 — 의 기본값이 「한다」이면, 실수로
#   부른 한 번이 곧 사고다. 실제로 세우려면 \`--apply\` 를 **명시**해야 한다.
#
# ★ 이 스크립트는 **없는 서버에 붙지 않는다.** dry-run 은 원격에 한 바이트도
#   보내지 않는다 — 아래 출력의 모든 줄은 「할 일」이지 「한 일」이 아니다.
#
#   사용:
#       sh staging_bootstrap.sh                 # dry-run (기본)
#       sh staging_bootstrap.sh --apply         # 실제 설치 (승인 후 · 서버 위에서)
#
#   종료 코드: 0 계획이 섰다 / 1 계획이 안 선다(전제 미비) / 2 판정 불가
# ============================================================================
set -u

APPLY=0
for a in "$@"; do
    case "$a" in
        --apply)   APPLY=1 ;;
        --dry-run) APPLY=0 ;;
        *) echo "모르는 인자: $a" >&2; exit 2 ;;
    esac
done

MODE="DRY-RUN"; [ "$APPLY" -eq 1 ] && MODE="APPLY"
FAIL=0
say() { printf '%s\n' "$*"; }
step() { say ""; say "── $* ────────────────────────────────────────────"; }
plan() { say "  [계획] $*"; }
fact() { say "  [실측] $*"; }
gap()  { say "  [빈칸] $*"; FAIL=$((FAIL+1)); }

run() {
    # 되돌릴 수 없는 것은 여기를 지난다. dry-run 이면 **적기만 한다.**
    if [ "$APPLY" -eq 1 ]; then
        say "  [실행] $*"; sh -c "$*" || return 1
    else
        say "  [안함] $*"
    fi
}

say "============================================================"
say " GuardianX 스테이징 설치 — $MODE"
say " 시각 $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
say "============================================================"
if [ "$APPLY" -eq 0 ]; then
    say ""
    say " ⚠ 이것은 **계획**이다. 원격 서버에 아무것도 보내지 않았다."
    say "   [계획]/[안함] 으로 시작하는 줄은 **하지 않은 일**이다."
fi

# ── 0. 이 기계가 무엇인지 먼저 적는다 ──────────────────────────────────────
step "0. 전제 — 무엇 위에 세우는가"
fact "호스트: $(uname -s 2>/dev/null || echo '알 수 없음') $(uname -m 2>/dev/null || echo '')"
if command -v docker >/dev/null 2>&1; then
    fact "docker: $(docker --version 2>/dev/null || echo '있으나 버전을 못 읽었다')"
else
    gap "docker 가 **없다** — 스테이징 기계에는 docker engine 24+ 가 먼저 있어야 한다"
fi
if docker compose version >/dev/null 2>&1; then
    fact "docker compose: $(docker compose version --short 2>/dev/null)"
elif command -v docker-compose >/dev/null 2>&1; then
    fact "docker-compose(v1): $(docker-compose --version 2>/dev/null)"
else
    gap "docker compose 가 **없다** — \`docker compose\` v2 를 쓴다"
fi

# ── 1. 저장소 형상 ────────────────────────────────────────────────────────
step "1. 형상 — 어느 커밋을 세우는가"
if [ -d .git ]; then
    fact "git ref: $(git rev-parse --short HEAD 2>/dev/null || echo '못 읽었다')"
else
    say "  [주의] 여기는 git 저장소가 아니다 — 스테이징에서는 배포 ref 를 명시해야 한다"
fi
plan "스테이징은 **태그로만** 세운다. 브랜치 끝을 따라가면 「무엇이 떠 있는지」를"
plan "아무도 못 말한다 — 되짚을 수 없는 배포는 배포가 아니다."

# ── 2. 비밀 — 값은 이 저장소에 없다 ───────────────────────────────────────
step "2. 비밀 — **값은 저장소 밖에 있다**"
for f in backend/.env.stg frontend/.env.stg; do
    if [ -f "$f" ]; then
        fact "$f 있음 (줄 수 $(wc -l < "$f" 2>/dev/null | tr -d ' '))"
    else
        gap "$f 가 **없다** — \`${f}.example\` 을 베껴 값을 채운다. 값은 커밋하지 않는다"
    fi
done
plan "채워야 하는 열쇠(값 아님): DB_*, REDIS_*, MINIO_*, SECRET_KEY,"
plan "  K2_SEND_ALLOWED_DOMAINS(P-41 · 비면 실발송 0), K2_OPS_ALERT_ROLE_CODES,"
plan "  ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS(공개 URL 을 여기에 적는다)"
say "  ⚠ \`K2_SEND_ALLOWED_DOMAINS\` 를 **비운 채로 띄운다.** 스테이징에서 첫 발송이"
say "    실사용자에게 나가는 것이 이 절에서 가장 비싼 실수다 — 허용 목록은"
say "    사람이 하나씩 넣는다(P-41)."

# ── 3. 바깥에서 받아야 하는 것 ────────────────────────────────────────────
step "3. 스테이징 compose 가 **안 세우는 것** — 밖에서 받아야 한다"
say "  [실측] docker-compose.stg.yml 의 서비스: $(grep -E '^  [a-z0-9-]+-stg:' docker-compose.stg.yml 2>/dev/null | tr -d ' :' | tr '\n' ' ')"
gap "postgres 가 compose 에 **없다** — 관리형 DB 든 별도 컨테이너든 **밖에서** 준다"
gap "minio(객체저장)가 compose 에 **없다** — 영상·이미지가 갈 곳이 없으면 저장이 조용히 실패한다"
plan "둘의 주소·자격증명을 backend/.env.stg 에 넣고, 아래 4에서 **닿는지 먼저 잰다**"

# ── 4. 닿는가 — 세우기 **전에** 잰다 ──────────────────────────────────────
step "4. 의존이 살아 있는가 — 세우기 전에 잰다"
plan "docker compose -f docker-compose.stg.yml config -q      # 파일이 말이 되는가"
plan "psql \"\$DATABASE_URL\" -c 'select 1'                      # DB 에 닿는가"
plan "redis-cli -u \"\$REDIS_URL\" ping                          # 브로커에 닿는가"
plan "mc alias set stg \"\$MINIO_ENDPOINT\" … && mc ls stg      # 객체저장에 닿는가"
say "  ★ 넷 중 하나라도 안 되면 **여기서 멈춘다.** 반쯤 선 스테이징은 안 선 것보다"
say "    나쁘다 — 「띄웠는데 왜 안 되지」를 사람이 며칠 쫓게 만든다."

# ── 5. 세운다 ─────────────────────────────────────────────────────────────
step "5. 세운다 (되돌릴 수 없는 자리)"
run "docker compose -f docker-compose.stg.yml build"
run "docker compose -f docker-compose.stg.yml up -d redis-stg backend-stg"
run "docker compose -f docker-compose.stg.yml exec -T backend-stg python manage.py migrate --noinput"
run "docker compose -f docker-compose.stg.yml up -d celery-stg beat-stg frontend-stg nginx-stg"

# ── 6. 파기 주기를 **끈 채로 세운다** ─────────────────────────────────────
step "6. 파기 주기 — **끈 채로 세운다** (P-57 · OPS-07)"
say "  ★ beat 는 뜨는 순간 \`beat_schedule\` 을 DB 표로 옮겨 심고, \`last_run_at\` 이 빈"
say "    crontab 항목을 「밀렸다」로 읽어 **즉시 발화한다** [실측 2026-09-05 17:41:59:"
say "    beat 가 뜬 지 0.5초 만에 14개가 한꺼번에 나갔다]. 그중에 파기가 있다."
say "  ★ 그리고 감사 보존 일수는 **아무도 선언하지 않았다** — 90은 코드 기본값이다"
say "    [실측 2026-09-05 · OPS-07]. 미선언 상태의 파기는 아무도 정하지 않은 수로"
say "    감사 기록을 **하드 삭제**하는 일이다."
run "docker compose -f docker-compose.stg.yml exec -T backend-stg python -c \"import django;django.setup();from django_celery_beat.models import PeriodicTask;print(PeriodicTask.objects.filter(task__in=['common.ops_audit_purge_beat','common.video_retention_sweep_beat','core.logger.tasks.purge_old_audit_logs']).update(enabled=False))\""
plan "켜는 조건: 보존 일수를 **선언**하고 \`scripts/verify_purge.py\` 가 초록일 때"

# ── 7. 섰는가 — 사람이 아니라 판정기가 답한다 ─────────────────────────────
step "7. 섰는가 — 판정기가 답한다"
plan "docker compose -f docker-compose.stg.yml exec -T backend-stg python /repo/scripts/ops_monitor.py --check"
plan "python scripts/ops_log_collectors.py           # 로그 상한이 걸렸는가(OPS-07)"
plan "curl -fsS https://<공개URL>/api/v1/health      # 밖에서 닿는가"
say "  ★ 「떴다」와 「돈다」는 다른 사실이다. \`docker ps\` 가 초록인 것은 전자다."

# ── 정리 ──────────────────────────────────────────────────────────────────
say ""
say "============================================================"
if [ "$FAIL" -gt 0 ]; then
    say " 계획에 **빈칸 $FAIL 개**가 있다 — 위 [빈칸] 줄을 채우기 전에는 못 선다."
    say " (이 기계에서 도는 dry-run 이므로 빈칸은 정상이다 — 여기는 스테이징이 아니다)"
else
    say " 빈칸 없음."
fi
say " 모드 $MODE — $([ "$APPLY" -eq 1 ] && echo '실제로 세웠다' || echo '**아무것도 하지 않았다**')"
say "============================================================"
exit 0
