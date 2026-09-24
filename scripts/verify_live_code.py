#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-314 ② — **옛 코드가 돌고 있지 않은가.** 살아 있는 서버의 코드 신선도 (턴 AH).

한 문장
-------
    `backend/**` 에서 가장 늦게 고친 파일이 **앱을 올린 프로세스**보다 뒤면,
    지금 요청을 받는 것은 **옛 코드**다 → 빨강.

이 게이트를 만든 사고 [실측 2026-09-24 · 턴 AH]
-----------------------------------------------
조율자가 P-289 로 `common/billing_marks.py` 와 `stream_monitors/services/camera_pulse.py`
를 고치고 **gunicorn 을 다시 세우지 않았다.** `backend/` 는 gunicorn 에 그대로 물려
있다. 그 뒤 `/api/dsm/cameras/pulse` 가 **500** 을 냈다:

    ImportError: cannot import name 'exclude_not_counted' from 'common.billing_marks'

파일에는 그 이름이 **있었다.** 마스터가 부팅 때 올린 **옛** `common.billing_marks` 는
메모리에 남았고, 늦게 import 된 `camera_pulse` 만 **새 파일**에서 읽혔다 — 옛 코드도
새 코드도 아닌 **반쪽** 상태다. 그 사이 **전량 2,182건은 전부 초록**이었다. 시험은
매번 새로 import 하므로 **이 고장을 구조적으로 못 잡는다.** 살아 있는 서버 하나가 잡는다.

★★ 기준 시각은 **마스터**다 — 워커가 아니다 (`preload_app = True`)
------------------------------------------------------------------
[실측 2026-09-24] `/app/gunicorn.conf.py:101` 이 `preload_app = True` 이고, gunicorn
23.0.0 은 작업 디렉터리(`/app`)의 그 파일을 기본으로 읽는다. preload 에서는 앱이
**마스터에** 올라가고 워커는 마스터를 **복제**한다. 그래서:

    · `kill -HUP 1` 은 워커만 새로 띄운다 — **앱 코드는 다시 안 읽는다**
    · `max_requests = 200` 으로 워커가 저절로 바뀌어도 — **여전히 옛 마스터의 복제**다

워커 시작 시각과 견주면 HUP 뒤 이 게이트는 **초록을 거짓말한다** — 워커는 방금
떴지만 코드는 부팅 때 것이기 때문이다. 오늘의 사고를 HUP 으로 「고쳤다면」 그렇게
보였을 것이다. 그래서 preload 이면 마스터와 견주고, 모르면 **마스터와 견준다**
(마스터 시각이 언제나 더 이르므로 거짓 초록이 안 난다 — 틀려도 빨강 쪽으로 틀린다).

    python scripts/verify_live_code.py              # 판정 (호스트에서 — docker 를 부른다)
    python scripts/verify_live_code.py --self-test  # 판정 규칙만 · 어디서 돌아도 같다

종료 코드: 0 신선하다 · 1 **옛 코드가 돌고 있다** · 2 못 쟀다(서버·docker 없음 · 자리 틀림)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
CONTAINER = "gx-gunicorn-e"
#: 재는 서버가 사는 곳. 게이트 여럿이 `GX_API=http://localhost:8000` 으로 여기를 두드린다.
SHELL_CONTAINER = "gx-shell"
TAG = "[LIVE]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 앱이 **요청 시각에 읽지 않는** 자리. 시험을 고쳐도 서버는 옛 코드가 아니다.
EXCLUDE_PARTS = ("tests", "__pycache__")

#: 파일 시각과 프로세스 시각의 허용 차이(초). [실측 2026-09-24] 호스트와 컨테이너의
#: 시계 차이는 **0초**였다 — 이 값은 저장 직후 재기동이 같은 초 안에 겹칠 때의 여유다.
TOLERANCE_S = 2.0

#: 재는 자리 표지 (P-320). 이 게이트는 **호스트**에서 돈다 — 호스트 파일 시각을 읽고
#: docker 로 컨테이너를 부른다. gx-shell 안에는 docker 가 없다.
WHERE_MARKERS = ("backend/config/settings.py",)

#: 컨테이너 안에서 gunicorn 프로세스의 **시작 시각(epoch)** 을 읽는다. `ps` 의 표시
#: 시각은 컨테이너 시간대를 타서 해석이 흔들린다 — 커널이 준 수(`/proc/<pid>/stat`
#: 22번째 칸 · 부팅 뒤 틱)와 부팅 시각(`/proc/stat btime`)으로 계산한다.
#: argv 로 안 넘기고 **표준입력으로** 넘긴다(따옴표·백슬래시가 셸을 타지 않게).
_PROC_PROBE = """
import json, os
tck = os.sysconf('SC_CLK_TCK')
bt = [int(l.split()[1]) for l in open('/proc/stat') if l.startswith('btime')][0]
out = []
for d in os.listdir('/proc'):
    if not d.isdigit():
        continue
    try:
        cmd = open('/proc/%s/cmdline' % d, 'rb').read()
        # 첫 인자가 python 인 것만 — `sh -c "... python manage.py runserver ..."` 감싸개는 뺀다
        if b'__TOKEN__' not in cmd or b'python' not in cmd.split(b'\\0')[0]:
            continue
        raw = open('/proc/%s/stat' % d).read()
        rest = raw[raw.rindex(')') + 2:].split()
        out.append([int(d), int(rest[1]), bt + int(rest[19]) / tck,
                    cmd.replace(b'\\0', b' ').decode('utf-8', 'replace')])
    except (OSError, ValueError, IndexError):
        pass
conf = ''
try:
    conf = open('/proc/1/cwd/gunicorn.conf.py').read()
except OSError:
    pass
cmd = open('/proc/1/cmdline', 'rb').read().decode('utf-8', 'replace')
print(json.dumps({'procs': out, 'conf': conf, 'cmd': cmd}))
"""


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수** (자기시험이 docker 없이 이것을 잰다)
# ═══════════════════════════════════════════════════════════════════════════
def preload_from(conf_text: str, cmdline: str) -> bool | None:
    """preload 인가. 명령줄이 이기고, 없으면 설정 파일, 둘 다 말이 없으면 모른다."""
    if "--no-preload" in cmdline:
        return False
    if "--preload" in cmdline:
        return True
    for line in (conf_text or "").splitlines():
        s = line.split("#", 1)[0].strip().replace(" ", "")
        if s == "preload_app=True":
            return True
        if s == "preload_app=False":
            return False
    return None


def split_master(procs: list) -> tuple[float | None, list[float]]:
    """(마스터 시작, 워커 시작들). 마스터는 **부모가 gunicorn 이 아닌** gunicorn 이다.

    `procs` 의 한 줄은 `[pid, ppid, 시작, (명령줄)]` — 앞 셋만 쓴다(명령줄은 runserver 판정용).
    """
    pids = {r[0] for r in procs}
    masters = [r[2] for r in procs if r[1] not in pids]
    workers = [r[2] for r in procs if r[1] in pids]
    return (min(masters) if masters else None), workers


def judge_runserver(newest: float, procs: list) -> tuple[int, str]:
    """gx-shell 안의 **재는 서버**(`manage.py runserver`) 판정. (종료 코드, 판정문)

    ★★ [실측 2026-09-24 · 턴 AH] **같은 사고가 두 번째 서버에서 났다.** 조율자가 P-288 을
      재려고 gx-shell 안에 `runserver 0.0.0.0:8000 --noreload` 를 띄웠고 **잊었다.**
      `--noreload` 라 3시간 57분 동안 한 번도 다시 안 읽었다 — P-289(17:19) 전의 코드다.
      여러 게이트가 기본으로 두드리는 곳(`GX_API=http://localhost:8000`)이 바로 이
      서버라, `verify_contract_route_reach` 가 `/api/dsm/cameras/pulse → 500` 을 받았고
      GA 가 **FAIL 1**(영역 1 · F-05-c1~c3)을 냈다. **재는 서버가 옛 코드면 잰 수가 거짓이다.**
      이 게이트를 처음 지었을 때는 gunicorn 만 봤다 — 그 사각에서 난 일이다.

    기준은 **가장 늦게 뜬 runserver 프로세스**다. `--noreload` 면 프로세스가 하나라 그것이
    곧 기준이고, 자동 재적재면 부모(감시자)는 그대로고 자식이 새로 뜨므로 **늦은 쪽**이
    요청을 받는 코드의 시점이다.

    ⚠ runserver 가 **없으면 초록**이다 — 「못 쟀다」가 아니라 「옛 코드일 수 있는 것이
      없다」이다. 회색은 재려던 것을 못 잰 때만 낸다.
    """
    if not procs:
        return EXIT_OK, "gx-shell 안에 runserver 가 없다 — 옛 코드일 수 있는 재는 서버가 없다"
    ref = max(r[2] for r in procs)
    noreload = any("--noreload" in (r[3] if len(r) > 3 else "") for r in procs)
    gap = newest - ref
    if gap > TOLERANCE_S:
        return (EXIT_FAIL,
                "**재는 서버가 옛 코드다** — 가장 늦게 고친 파일이 runserver 보다 %.0f초 뒤%s. "
                "이 서버를 두드린 게이트의 수는 옛 코드의 수다 — 다시 띄운다"
                % (gap, " (`--noreload` — 스스로 다시 안 읽는다)" if noreload else ""))
    return EXIT_OK, "재는 서버 신선 — 가장 늦게 고친 파일이 runserver 보다 %.0f초 앞" % -gap


def judge(newest: float, master: float | None, workers: list[float],
          preload: bool | None) -> tuple[int, str, str]:
    """(종료 코드, 판정문, 기준 이름).

    ★ 기준은 preload 이거나 **모르면** 마스터다. 워커는 preload 가 **아니라고 확인된**
      때만 기준이 된다 — 그때는 HUP 이 정말로 코드를 다시 읽기 때문이다.
    """
    if master is None:
        return EXIT_UNDECIDABLE, "gunicorn 마스터를 못 찾았다 — 못 쟀다", "(없음)"
    if preload is False and workers:
        ref, ref_name = min(workers), "가장 오래된 워커(preload 아님 확인)"
    else:
        ref = master
        ref_name = ("마스터(preload_app=True — 워커는 마스터의 복제)" if preload
                    else "마스터(preload 여부 모름 — 더 이른 쪽으로 엄하게)")
    gap = newest - ref
    if gap > TOLERANCE_S:
        return (EXIT_FAIL,
                "**옛 코드가 돌고 있다** — 가장 늦게 고친 파일이 기준보다 %.0f초 뒤다. "
                "gunicorn 을 다시 세운다(preload 이면 HUP 으로는 안 된다)" % gap,
                ref_name)
    return EXIT_OK, "신선하다 — 가장 늦게 고친 파일이 기준보다 %.0f초 앞" % -gap, ref_name


# ═══════════════════════════════════════════════════════════════════════════
# 재기 — 호스트 파일 · 컨테이너 프로세스
# ═══════════════════════════════════════════════════════════════════════════
def newest_backend_file(root: Path = BACKEND) -> tuple[float, str] | None:
    best = None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_PARTS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = Path(dirpath) / fn
            try:
                m = p.stat().st_mtime
            except OSError:
                continue
            if best is None or m > best[0]:
                best = (m, p.relative_to(ROOT).as_posix())
    return best


def probe_container(name: str = CONTAINER, token: str = "gunicorn") -> dict | None:
    try:
        r = subprocess.run(["docker", "exec", "-i", name, "python", "-"],
                           input=_PROC_PROBE.replace("__TOKEN__", token),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def _stamp(epoch: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(epoch).strftime("%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **오늘의 사고가 출생 표본이다** (D-310)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    fails = 0
    T0 = 1_790_000_000.0

    # ① ★ 출생 표본 — 그날의 모양 그대로. preload · 마스터는 부팅 때 ·
    #    워커는 max_requests 로 방금 바뀜 · 파일은 그 사이에 고쳐짐.
    #    **워커와 견주는 판정이면 여기서 초록이 난다** — 그것이 이 표본의 이유다.
    code, _v, _r = judge(newest=T0 + 50, master=T0, workers=[T0 + 100, T0 + 120],
                         preload=True)
    if code != EXIT_FAIL:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 출생 표본(preload · 워커는 새것 · 마스터는 옛것)을 "
              "초록으로 읽었다 — 워커와 견주고 있다")

    # ② 음성 — 다시 세운 뒤: 마스터가 파일보다 뒤다 → 초록
    code, _v, _r = judge(newest=T0 + 50, master=T0 + 60, workers=[T0 + 61], preload=True)
    if code != EXIT_OK:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 다시 세운 서버를 옛 코드로 읽었다")

    # ③ preload 가 **아니라고 확인된** 때 HUP 은 정말 코드를 다시 읽는다 → 워커가 기준
    code, _v, _r = judge(newest=T0 + 50, master=T0, workers=[T0 + 100], preload=False)
    if code != EXIT_OK:
        fails += 1
        print(f"{TAG} 자기시험 FAIL preload 가 아닌데 HUP 뒤 워커를 안 봤다 — 거짓 빨강")

    # ④ preload 를 **모르면** 마스터(엄한 쪽) → ①과 같은 모양이면 빨강
    code, _v, _r = judge(newest=T0 + 50, master=T0, workers=[T0 + 100], preload=None)
    if code != EXIT_FAIL:
        fails += 1
        print(f"{TAG} 자기시험 FAIL preload 를 모르는데 느슨한 쪽(워커)으로 판정했다")

    # ⑤ 허용 차이 안 — 같은 초에 저장과 재기동이 겹친 것은 옛 코드가 아니다
    code, _v, _r = judge(newest=T0 + 1, master=T0, workers=[], preload=True)
    if code != EXIT_OK:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 허용 차이({TOLERANCE_S}초) 안을 빨강으로 읽었다")

    # ⑥ 마스터를 못 찾으면 **회색** — 초록도 빨강도 아니다
    code, _v, _r = judge(newest=T0, master=None, workers=[], preload=True)
    if code != EXIT_UNDECIDABLE:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 마스터 없음을 회색이 아닌 {code} 로 냈다")

    # ⑦ 설정 읽기 — 그날의 파일 모양 · 명령줄이 이긴다 · 주석은 안 센다
    if preload_from("max_requests = 200\npreload_app = True\n", "gunicorn app") is not True:
        fails += 1
        print(f"{TAG} 자기시험 FAIL `preload_app = True` 를 못 읽었다")
    if preload_from("preload_app = True\n", "gunicorn --no-preload app") is not False:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 명령줄 --no-preload 가 설정 파일을 못 이겼다")
    if preload_from("# preload_app = True\n", "gunicorn app") is not None:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 주석 속 preload 를 설정으로 읽었다")

    # ⑧ 마스터 가르기 — 부모가 gunicorn 이 아닌 쪽이 마스터
    m, w = split_master([[1, 0, T0], [16, 1, T0 + 5], [17, 1, T0 + 9]])
    if m != T0 or sorted(w) != [T0 + 5, T0 + 9]:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 마스터·워커를 잘못 갈랐다: {m} · {w}")

    # ⑨ ★ 출생 표본 ② — **잊힌 재는 서버**. 그날 모양 그대로: `--noreload` · 15:47 에 떴고
    #    파일은 17:19 에 고쳐졌다(≈ 5,500초 뒤). 게이트를 처음 지었을 때 이 서버를 안 봤다.
    _rs_day = [[40989, 40983, T0, "python manage.py runserver 0.0.0.0:8000 --noreload"]]
    code, _v = judge_runserver(T0 + 5_500, _rs_day)
    if code != EXIT_FAIL:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 출생 표본 ②(잊힌 --noreload runserver)를 신선하다고 읽었다")

    # ⑩ 음성 — 다시 띄운 뒤 · runserver 가 아예 없을 때 (없으면 옛 코드일 것도 없다)
    code, _v = judge_runserver(T0 + 50, [[1, 0, T0 + 60, "python manage.py runserver"]])
    if code != EXIT_OK:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 다시 띄운 재는 서버를 옛 코드로 읽었다")
    code, _v = judge_runserver(T0 + 50, [])
    if code != EXIT_OK:
        fails += 1
        print(f"{TAG} 자기시험 FAIL runserver 가 없는 것을 {code} 로 냈다 — 없으면 초록이다")

    # ⑪ 자동 재적재 — 부모(감시자)는 옛것 · 자식은 새것 → **늦은 쪽**이 기준이라 초록
    code, _v = judge_runserver(T0 + 50, [[10, 1, T0, "python manage.py runserver"],
                                         [11, 10, T0 + 60, "python manage.py runserver"]])
    if code != EXIT_OK:
        fails += 1
        print(f"{TAG} 자기시험 FAIL 자동 재적재의 새 자식을 안 보고 옛 부모로 판정했다")

    if fails:
        print(f"{TAG} 자기시험 {fails}건 실패")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 출생 표본 2(반쪽 gunicorn · 잊힌 runserver) · 판정 5 · "
          "재는 서버 3 · 설정 읽기 3 · 가르기 1")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="P-314 ② 살아 있는 서버의 코드 신선도")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--container", default=CONTAINER)
    ap.add_argument("--shell", default=SHELL_CONTAINER)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    missing = [m for m in WHERE_MARKERS if not (ROOT / m).exists()]
    if missing:
        print(f"{TAG} **판정 불가 · 회색** — 재는 자리가 틀렸다(없는 표지: "
              f"{' · '.join(missing)}) · 호스트에서 다시 (P-320)")
        return EXIT_UNDECIDABLE

    newest = newest_backend_file()
    if newest is None:
        print(f"{TAG} **판정 불가 · 회색** — backend 에서 .py 를 한 개도 못 읽었다")
        return EXIT_UNDECIDABLE

    got = probe_container(args.container)
    if got is None:
        print(f"{TAG} **판정 불가 · 회색** — {args.container} 안을 못 읽었다(서버가 "
              "없거나 docker 를 못 부른다). 못 잰 것은 신선한 것이 아니다")
        return EXIT_UNDECIDABLE

    preload = preload_from(got.get("conf", ""), got.get("cmd", ""))
    master, workers = split_master(got.get("procs") or [])
    code, verdict, ref_name = judge(newest[0], master, workers, preload)

    def _mark(c: int) -> str:
        return "OK  " if c == EXIT_OK else ("FAIL" if c == EXIT_FAIL else "GRAY")

    print(f"{TAG} [입력] 가장 늦게 고친 backend 파일: {newest[1]} ({_stamp(newest[0])}) "
          f"· 시험·캐시는 안 센다")
    print(f"{TAG} ── ① 제품 서버 {args.container} ──")
    if master is not None:
        print(f"{TAG} [입력] 마스터 시작 {_stamp(master)} · 워커 "
              f"{len(workers)}개 (가장 오래된 것 "
              f"{_stamp(min(workers)) if workers else '없음'})")
    print(f"{TAG} [입력] preload_app = {preload} → 기준: {ref_name}")
    print(f"{TAG} {_mark(code)} {verdict}")

    #: ② 재는 서버 — 게이트들이 기본으로 두드리는 gx-shell 안의 runserver(`GX_API`).
    print(f"{TAG} ── ② 재는 서버 {args.shell} (runserver) ──")
    rs = probe_container(args.shell, token="runserver")
    if rs is None:
        code2, verdict2 = EXIT_UNDECIDABLE, f"{args.shell} 안을 못 읽었다 — 못 쟀다"
    else:
        rprocs = rs.get("procs") or []
        for r in rprocs:
            print(f"{TAG} [입력] runserver pid {r[0]} 시작 {_stamp(r[2])}"
                  f"{' · --noreload' if '--noreload' in r[3] else ''}")
        code2, verdict2 = judge_runserver(newest[0], rprocs)
    print(f"{TAG} {_mark(code2)} {verdict2}")

    #: 둘을 한 색으로 — 빨강이 하나라도 있으면 빨강 · 아니면 회색이 하나라도 있으면 회색.
    if EXIT_FAIL in (code, code2):
        return EXIT_FAIL
    if EXIT_UNDECIDABLE in (code, code2):
        return EXIT_UNDECIDABLE
    return EXIT_OK


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="살아 있는 서버 %s (호스트 docker 로 부른다) · 비교 대상 저장소 backend/"
               % CONTAINER,
        as_="(자격증명 없음 — 컨테이너 /proc 과 호스트 파일 시각을 읽는다)",
        source="호스트 backend/**/*.py 의 mtime · 컨테이너 /proc/<pid>/stat · "
               "/app/gunicorn.conf.py",
        measured="요청을 받는 코드가 **저장소의 코드와 같은 시점인가** — 기준은 "
                 "preload 이면 마스터, 확인된 비-preload 이면 가장 오래된 워커 · 분모 1(서버)",
    )
    raise SystemExit(main())
