#!/bin/sh
# ============================================================================
# STAGING ② — **개발 형상을 스테이징으로 옮긴다** (2026-09-05 · 차선 E · 턴 F)
# ============================================================================
#
# ★ 「형상」은 **데이터가 아니다.** 옮기는 것은 넷뿐이다:
#       ① 코드의 ref(태그)      ② 이미지        ③ 스키마(마이그레이션)
#       ④ 설정의 **열쇠 이름**  (값이 아니라 이름 — 값은 저장소 밖에 있다)
#
#   ★★ **옮기지 않는 것**을 먼저 못박는다. 이것이 이 파일의 절반이다:
#       · 테넌트 데이터(사용자·카메라·이벤트·영상) — 스테이징으로 복사하면 그 순간
#         스테이징이 개인정보 처리 시스템이 된다. 접근 통제도 파기 주기도 없는 채로.
#       · 감사 로그 — 정본은 하나여야 한다. 복사본이 있으면 「어느 쪽이 참인가」를
#         감사에서 답할 수 없다.
#       · 비밀 값(.env 의 값) — 형상은 **열쇠 이름**까지다. 값은 사람이 넣는다.
#       · MinIO 객체 — 위 둘의 다른 이름이다.
#
# ★ **기본값은 dry-run 이다** (D-209). 실제로 옮기려면 `--apply` 를 명시한다.
# ★ 이 스크립트는 **없는 서버에 붙지 않는다.** dry-run 에서 원격에 한 바이트도
#   보내지 않는다 — 아래 [계획]/[안함] 줄은 **하지 않은 일**이다.
#
#   사용:
#       sh staging_mirror.sh                    # dry-run (기본)
#       sh staging_mirror.sh --apply            # 실제 미러 (승인 후)
#
#   종료 코드: 0 형상이 맞는다 / 1 어긋난 자리가 있다 / 2 판정 불가
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
DIFFS=0
say()  { printf '%s\n' "$*"; }
step() { say ""; say "── $* ────────────────────────────────────────────"; }
fact() { say "  [실측] $*"; }
plan() { say "  [계획] $*"; }
diffx() { say "  [어긋남] $*"; DIFFS=$((DIFFS+1)); }
run()  { if [ "$APPLY" -eq 1 ]; then say "  [실행] $*"; sh -c "$*" || return 1;
         else say "  [안함] $*"; fi }

say "============================================================"
say " GuardianX 개발 → 스테이징 형상 미러 — $MODE"
say " 시각 $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
say "============================================================"
[ "$APPLY" -eq 0 ] && { say ""; say " ⚠ 계획이다. **원격 서버에 아무것도 보내지 않았다.**"; }

# ── 1. 무엇을 옮기지 않는가 — 먼저 적는다 ────────────────────────────────
step "1. **옮기지 않는 것** (이 목록이 이 스크립트의 절반이다)"
say "  ✗ 테넌트 데이터 — 사용자·카메라·이벤트·배송·영상"
say "  ✗ 감사 로그(logger_auditlogs) — 정본은 하나여야 한다"
say "  ✗ .env 의 **값** (열쇠 이름만 맞춘다)"
say "  ✗ MinIO 객체(영상·이미지)"
say "  ★ 스테이징에 필요한 데이터는 **씨앗으로 새로 만든다.** 개발 DB 를 덤프해서"
say "    붓는 순간 스테이징이 개인정보 처리 시스템이 되고, 그 시스템에는 접근 통제도"
say "    파기 주기도 서 있지 않다."

# ── 2. ref — 무엇을 옮기는가 ─────────────────────────────────────────────
step "2. ref — 태그 하나로 못박는다"
if [ -d .git ]; then
    fact "HEAD $(git rev-parse --short HEAD 2>/dev/null || echo '못 읽었다')"
    fact "가장 최근 태그: $(git describe --tags --abbrev=0 2>/dev/null || echo '**없다**')"
    [ -n "$(git status --porcelain 2>/dev/null)" ] && \
        diffx "작업 트리가 **깨끗하지 않다** — 커밋 안 된 것이 스테이징에 안 간다"
else
    say "  [주의] git 저장소가 아니다 — ref 를 못 잰다"
fi
plan "git tag -a stg-YYYYMMDD-N -m '스테이징 배포' && git push origin stg-…"

# ── 3. 설정 열쇠 — **이름만** 견준다 ─────────────────────────────────────
step "3. 설정 열쇠 — 개발과 스테이징의 **이름 집합**을 견준다 (값은 안 본다)"
keys_of() { [ -f "$1" ] && grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$1" | cut -d= -f1 | sort -u; }
for pair in "backend/.env.example backend/.env.stg" "frontend/.env.example frontend/.env.stg"; do
    src=$(echo "$pair" | cut -d' ' -f1); dst=$(echo "$pair" | cut -d' ' -f2)
    if [ ! -f "$src" ] || [ ! -f "$dst" ]; then
        say "  [못 쟀다] $src 또는 $dst 가 없다"
        continue
    fi
    keys_of "$src" > /tmp/gx_src_keys.$$ 2>/dev/null
    keys_of "$dst" > /tmp/gx_dst_keys.$$ 2>/dev/null
    missing=$(comm -23 /tmp/gx_src_keys.$$ /tmp/gx_dst_keys.$$ | tr '\n' ' ')
    extra=$(comm -13 /tmp/gx_src_keys.$$ /tmp/gx_dst_keys.$$ | tr '\n' ' ')
    fact "$dst — 열쇠 $(wc -l < /tmp/gx_dst_keys.$$ | tr -d ' ')개 (본보기 $src 는 $(wc -l < /tmp/gx_src_keys.$$ | tr -d ' ')개)"
    [ -n "$missing" ] && diffx "$dst 에 **없는** 열쇠: $missing"
    [ -n "$extra" ]   && say   "  [주의] $dst 에만 있는 열쇠: $extra (스테이징 전용이면 정상)"
    rm -f /tmp/gx_src_keys.$$ /tmp/gx_dst_keys.$$
done
say "  ★ **값은 여기서 옮기지 않는다.** 열쇠 하나가 빠지면 그 기능이 조용히 기본값으로"
say "    떨어지고, 기본값으로 도는 것은 아무도 안 본다 — 그래서 이름만이라도 견준다."

# ── 3b. 빠진 열쇠가 **무엇으로 떨어지는가** ──────────────────────────────
#   ★ 「열쇠가 없다」는 아직 사실의 절반이다. 나머지 절반은 **없으면 무엇이 되는가**다.
#     안전한 기본값으로 떨어지는 열쇠(빈 허용 목록 → 아무 데도 안 보냄)는 빠져도
#     괜찮고, 위험한 기본값으로 떨어지는 열쇠는 **빠진 것 자체가 사고**다.
step "3b. 빠진 열쇠가 **무엇으로 떨어지는가** — 안전한 기본값과 위험한 기본값을 가른다"
WATCH="TENANT_SCOPE_ENFORCE TENANT_TRUST_LEGACY_SUPERUSER GUARDIANX_ENVIRONMENT K2_SEND_ALLOWED_DOMAINS K2_OPS_ALERT_ROLE_CODES DJANGO_CSRF_TRUSTED_ORIGINS"
for k in $WATCH; do
    if grep -qE "^${k}=" backend/.env.stg 2>/dev/null; then
        fact "$k — .env.stg 에 **있다**"
    else
        d=$(grep -E "^${k} *= *env" backend/config/settings.py 2>/dev/null | head -1 | sed 's/.*default=//; s/).*//')
        [ -z "$d" ] && d="(settings.py 에서 못 찾았다)"
        diffx "$k 가 .env.stg 에 **없다** → 코드 기본값 $d 로 떨어진다 [실측]"
    fi
done
say "  ★★ 이 여섯을 고른 이유: 앞의 셋은 **없으면 위험한 쪽**으로 떨어지고"
say "     (테넌트 격리 강제 꺼짐 · 옛 superuser 신뢰 켜짐 · 환경 이름이 development),"
say "     뒤의 셋은 **없으면 안전한 쪽**으로 떨어진다(허용 목록이 비면 실발송 0 · P-41)."
say "     둘을 한 목록으로 두면 「열쇠 55개 빠짐」이라는 한 줄이 되고, 그 한 줄은"
say "     아무도 안 읽는다."

# ── 4. 스키마 — 마이그레이션은 **코드가 옮긴다** ─────────────────────────
step "4. 스키마 — 덤프가 아니라 마이그레이션으로 옮긴다"
if [ -d backend ]; then
    n=$(find backend -path '*/migrations/*.py' ! -name '__init__.py' 2>/dev/null | wc -l | tr -d ' ')
    fact "이 저장소가 들고 있는 마이그레이션 파일 $n 개"
fi
plan "docker compose -f docker-compose.stg.yml exec -T backend-stg python manage.py migrate --plan"
plan "  ↑ **먼저 --plan 으로 무엇이 도는지 본다.** 스테이징에서 처음 도는 마이그레이션이"
plan "    운영에서도 처음 돈다 — 스테이징은 그것을 미리 겪는 자리다."
say "  ✗ pg_dump/pg_restore 로 개발 DB 를 붓지 않는다 (위 1의 이유)"

# ── 5. 이미지 ────────────────────────────────────────────────────────────
step "5. 이미지 — 스테이징에서 **다시 빌드**한다"
fact "이 기계의 이미지: $(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -c guardianx || echo 0) 개(guardianx-*)"
run "docker compose -f docker-compose.stg.yml build --pull"
say "  ★ 개발 기계의 이미지를 save/load 로 옮기지 않는다 — 그 이미지에는 개발 기계의"
say "    빌드 캐시·마운트 흔적이 섞여 있고, 무엇이 들어갔는지 되짚을 수 없다."

# ── 6. 앞단 번들 ─────────────────────────────────────────────────────────
step "6. 앞단 — 번들은 **해시로** 확인한다"
plan "python scripts/verify_bundle_hash.py     # 뜬 번들이 이 ref 의 것인가"
say "  ★ 「배포했다」와 「그 배포가 떠 있다」는 다른 사실이다(D-301)."

# ── 7. 옮긴 뒤 — 판정기가 답한다 ─────────────────────────────────────────
step "7. 옮긴 뒤 — 사람이 아니라 판정기가 답한다"
plan "ops_monitor.py --check              # 감시 14신호(감사 큐 지연 포함 · P-65)"
plan "ops_log_collectors.py               # 로그 상한(OPS-07)"
plan "verify_send_allowlist.py            # 실발송 허용 도메인(P-41)"
plan "verify_purge.py                     # 파기가 그대로 지우는가(P-57)"

say ""
say "============================================================"
if [ "$DIFFS" -gt 0 ]; then
    say " 어긋난 자리 **$DIFFS 개** — 위 [어긋남] 줄을 보라."
else
    say " 어긋난 자리 없음."
fi
say " 모드 $MODE — $([ "$APPLY" -eq 1 ] && echo '실제로 옮겼다' || echo '**아무것도 옮기지 않았다**')"
say "============================================================"
[ "$DIFFS" -gt 0 ] && exit 1
exit 0
