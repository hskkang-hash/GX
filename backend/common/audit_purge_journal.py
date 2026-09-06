# -*- coding: utf-8 -*-
"""OPS-07b — **파기는 되돌릴 수 있어야 한다** (되돌림 저널 · 2026-09-06 · 차선 E).

    ga_readiness OPS-07b 제목:
      「DB 감사 로그 보존 — 보존 일수를 **선언하고** 파기가 **되돌릴 수 있어야 한다**」

앞 두 조건은 턴 G 에 갚았다(① 선언 · ② 미선언이면 호출 0). 남은 것이 이 파일이다.

★ 왜 「되돌림」이 따로 필요한가 — **삭제가 하드다**
--------------------------------------------------
[실측 2026-09-05 · OPS-07b] 실제로 지우는 손은 dj-core `purge_old_audit_logs` 이고,
그 함수는 이렇게 지운다:

    AuditLogs._base_manager.filter(create_datetime__lt=cutoff).delete()

`_base_manager` 는 safedelete 의 매니저가 아니라 **평범한 `Manager`** 다[실측
2026-09-06 · `type(AuditLogs._base_manager).__name__ == "Manager"`]. 그러므로 이
`delete()` 는 소프트 삭제가 아니라 **행을 지운다.** 그리고 그 함수는 §0.4 이관
자산이라 우리가 고칠 수 없다.

    즉 우리가 쥔 손잡이는 둘뿐이다: **부르지 않는 것**(턴 G) 과
    **부르기 전에 떠 두는 것**(이 파일).

★ 이 파일이 지키는 규약 — **되돌릴 수 없으면 지우지 않는다**
------------------------------------------------------------
`ops_audit_purge_beat` 은 dj-core 를 부르기 **전에** 이 모듈로 저널을 뜬다.
저널을 못 뜨면 **dj-core 를 부르지 않는다**(`SKIPPED_UNREVERSIBLE` · 호출 0).
「지웠는데 되돌릴 수 없다」보다 「안 지웠다」가 언제나 낫다 — 감사 기록은
지운 뒤에 아쉬워할 수 있는 자료가 아니다.

★ 저널이 어디에 사는가 — **선언이다. 기본값이 아니다** (P-67)
-------------------------------------------------------------
`settings.OPS_BACKUP_DIR` 아래 `audit_purge_journal/` 하나다. **그 칸이 비면
`None`** 이고, 그때 파기는 돌지 않는다. 경로를 지어내지 않는다 — 어디 뜨는지
모르는 저널은 저널이 아니고, 컨테이너 루트에 떨어진 저널은 재생성 한 번에
사라진다(OPS-12a 의 착시와 같다).

⚠ **설정 이름을 하나 더 만들지 않았다.** 처음에는 `OPS_AUDIT_JOURNAL_DIR` 을
  따로 두었는데, 그것은 **아무도 안 채우는 이름**이 된다 — 잠자는 기능 래칫이
  그 자리에서 빨간불을 냈고(D-377 착시 ⑨ · `C OPS_AUDIT_JOURNAL_DIR`), 그 지적이
  옳았다. 저널의 자리가 백업과 갈라질 이유가 없다.

★ 무엇으로 뜨는가 — `django.core.serializers`
---------------------------------------------
직렬화 판(`json`)은 **기본키를 보존**하고 FK 를 pk 로 적는다. 되살릴 때
`DeserializedObject.save()` 는 `Model.save_base(raw=True)` 를 부르므로
`auto_now_add=True` 인 `create_datetime` 이 **다시 찍히지 않는다** — 되살린 행의
시각이 오늘이 되면 그것은 같은 행이 아니라 새 행이다.

★ 못 하는 것 — 지우지 않고 적는다
---------------------------------
㉠ 이 저널은 **감사 로그 표 하나**를 위한 것이다. 다른 표의 파기는 여기 없다.
㉡ 저널 파일 자체의 보존기간은 `OPS_BACKUP_RETENTION_DAYS`(14일) **선언을 따르라고
   적어 두었을 뿐 이 모듈이 지우지는 않는다.** 지우는 손을 여기 두면 「되돌림을
   지우는 코드」가 되고, 그것은 이 파일의 존재 이유와 반대다.
㉢ 저널은 **평문 JSON** 이다. 감사 로그에는 사용자명·IP 가 들어 있다 — 저널이
   사는 볼륨은 백업과 같은 취급을 받아야 한다(D-204).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings

logger = logging.getLogger("ops")

#: 저널 파일 이름의 앞머리. 사람이 `ls` 로 보고 무엇인지 알아야 한다.
JOURNAL_PREFIX = "audit_purge_"

#: 저널이 `OPS_BACKUP_DIR` 아래로 떨어질 때 쓰는 칸 이름.
JOURNAL_SUBDIR = "audit_purge_journal"


# ═══════════════════════════════════════════════════════════════════════════
# 1. 어디에 뜨는가 — **선언이 없으면 `None`**
# ═══════════════════════════════════════════════════════════════════════════
def journal_dir():
    """되돌림 저널의 자리. **선언이 없으면 `None`** 이고 그것은 빈 경로가 아니다.

    Returns:
        `str` 또는 `None`. `None` 이면 파기는 **돌면 안 된다**.
    """
    backup = (getattr(settings, "OPS_BACKUP_DIR", "") or "").strip()
    if backup:
        return str(Path(backup) / JOURNAL_SUBDIR)
    return None


def journal_dir_is_separate_volume(path: str):
    """그 자리가 **정말 붙은 볼륨인가.** 못 재면 `None`(참이 아니다).

    `common.ops_tasks.backup_dir_is_separate_volume` 과 같은 잣대다. 두 벌로 두지
    않으려면 그쪽을 부르는 것이 옳지만, 이 모듈은 `ops_tasks` 를 `import` 하지
    않는다(반대 방향으로 부른다) — 그래서 규칙 한 줄만 여기 다시 적는다.
    """
    try:
        target = Path(path)
        probe = target if target.exists() else target.parent
        if not probe.exists():
            return None
        return os.stat(str(probe)).st_dev != os.stat("/").st_dev
    except OSError as exc:                                  # noqa: BLE001
        logger.warning("[OPS][AUDIT] 저널 자리가 별도 볼륨인지 못 쟀다: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 2. 무엇이 지워질 것인가 — **dj-core 와 같은 조건으로 센다**
# ═══════════════════════════════════════════════════════════════════════════
def expiring_queryset(retention_days: int):
    """dj-core `purge_old_audit_logs` 가 **지울 바로 그 행들**.

    ★ 조건을 여기서 새로 짓지 않는다. dj-core 는
      `AuditLogs._base_manager.filter(create_datetime__lt=cutoff)` 로 지운다 —
      같은 매니저·같은 칸·같은 부등호를 쓴다. 조건이 갈리면 저널이 뜬 행과 지워진
      행이 달라지고, **그 차이만큼이 되돌릴 수 없는 삭제**가 된다(D-369).
    """
    from django.utils import timezone as dj_timezone

    from core.logger.models import AuditLogs

    cutoff = dj_timezone.now() - timedelta(days=int(retention_days))
    return AuditLogs._base_manager.filter(create_datetime__lt=cutoff), cutoff


def count_boundary_crossed(retention_days: int, journal_cutoff: str) -> int:
    """저널을 뜬 뒤 **만료선을 넘어간 행**의 수. 그만큼이 되돌릴 수 없는 삭제다.

    dj-core 는 자기가 불리는 시각으로 `cutoff` 를 다시 잰다. 우리가 저널을 뜬
    시각보다 늦으므로, 그 사이에 `create_datetime` 이 새 `cutoff` 아래로 들어간
    행은 **저널에 없는 채로 지워진다.** 창은 밀리초이고 그 행은 이미 보존 일수를
    지난 행이라 거의 언제나 0이지만, **0일 것 같은 것을 0으로 적지 않는다**(D-301).

    ⚠ 순증감(`rows_before - rows_after`)으로 이 수를 대신하면 안 된다 — 표가
      살아 있어서 남이 쓴 줄만큼 틀린다[실측 2026-09-06 · 저널 3행을 지웠는데
      순증감은 2였다].
    """
    from django.utils import timezone as dj_timezone

    from core.logger.models import AuditLogs

    if not journal_cutoff:
        return 0
    try:
        old = datetime.fromisoformat(journal_cutoff)
    except (TypeError, ValueError):
        return 0
    now_cutoff = dj_timezone.now() - timedelta(days=int(retention_days))
    if now_cutoff <= old:
        return 0
    return AuditLogs._base_manager.filter(
        create_datetime__gte=old, create_datetime__lt=now_cutoff).count()


# ═══════════════════════════════════════════════════════════════════════════
# 3. 뜨는 손
# ═══════════════════════════════════════════════════════════════════════════
def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_journal(retention_days: int, out_dir: str = "", *, stamp: str = "",
                  require_separate_volume: bool = True) -> dict:
    """지워질 행을 **먼저** 뜬다. 뜨지 못하면 예외를 던진다 — 조용히 넘기지 않는다.

    Args:
        retention_days: 선언된 보존 일수. 이 수로 자른 행을 뜬다.
        out_dir: 저널 자리. 비우면 `journal_dir()`.
        stamp: 파일 이름에 쓸 시각(시험이 고정할 수 있게).
        require_separate_volume: 저널 자리가 **붙은 볼륨**이어야 하는가.
            기본 참이고 그것이 이 모듈의 판단이다 — 컨테이너 루트에 떨어진
            저널은 재생성 한 번에 사라지고, 그 전까지 「저널이 있다」가 초록으로
            보인다(OPS-12a 의 착시와 같은 모양). 거짓으로 내리는 것은 **시험**뿐이고,
            시험은 임시 폴더가 볼륨이 아님을 알고 부른다.

    Returns:
        `{"path", "rows", "sha256", "bytes", "cutoff", "separate_volume"}`.
        `rows` 가 0 이면 파일을 **만들지 않는다**(`path` 는 `None`) — 지울 것이
        없는 날 빈 파일을 쌓으면 저널 칸이 곧 쓰레기통이 된다. 대신 그 자리가
        **쓸 수 있는 자리인지**는 탐침 파일로 확인하고 지운다.

    Raises:
        RuntimeError: 저널 자리가 선언되지 않았다.
        OSError: 그 자리에 쓸 수 없다.
    """
    from django.core import serializers

    target_dir = (out_dir or journal_dir() or "").strip()
    if not target_dir:
        raise RuntimeError(
            "되돌림 저널 자리가 **선언되지 않았다**(`OPS_BACKUP_DIR`). "
            "되돌릴 수 없는 파기는 돌리지 않는다 (OPS-07b · P-67)")

    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = Path(target_dir)
    directory.mkdir(parents=True, exist_ok=True)

    #: ★ 쓸 수 있는 자리인지 **먼저** 확인한다. 0건인 날에도 이 확인은 한다 —
    #:   지울 것이 없어서 안 터진 것을 「자리가 멀쩡하다」로 읽으면, 지울 것이
    #:   생긴 첫날에 처음 터진다.
    probe = directory / (JOURNAL_PREFIX + ".writable-probe")
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()

    separate = journal_dir_is_separate_volume(str(directory))
    if require_separate_volume and separate is not True:
        raise RuntimeError(
            f"저널 자리 {str(directory)!r} 가 **별도 볼륨으로 안 붙어 있다**"
            + ("(못 쟀다)" if separate is None else "")
            + " — 여기 뜨면 컨테이너를 다시 만드는 순간 저널이 사라지고, 그 전까지 "
              "「되돌릴 수 있다」가 초록으로 보인다. 붙이는 법은 docker-compose 의 "
              "볼륨 선언(OPS_BACKUP_VOLUME)이고 그것은 컨테이너 재생성이 필요하다")

    queryset, cutoff = expiring_queryset(retention_days)
    rows = queryset.count()

    if rows == 0:
        return {"path": None, "rows": 0, "sha256": None, "bytes": 0,
                "cutoff": cutoff.isoformat(), "dir": str(directory),
                "separate_volume": separate,
                "why": "지울 행이 0건이라 저널을 만들지 않았다 — 자리는 확인했다"}

    path = directory / f"{JOURNAL_PREFIX}{stamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        serializers.serialize("json", queryset.iterator(), stream=handle,
                              indent=None)
    digest = _sha256_of(path)
    (path.with_suffix(".json.sha256")).write_text(
        f"{digest}  {path.name}\n", encoding="utf-8")

    logger.info("[OPS][AUDIT] 되돌림 저널 %s — %d행", path, rows)
    return {"path": str(path), "rows": rows, "sha256": digest,
            "bytes": path.stat().st_size, "cutoff": cutoff.isoformat(),
            "dir": str(directory), "separate_volume": separate, "why": ""}


# ═══════════════════════════════════════════════════════════════════════════
# 4. 되돌리는 손
# ═══════════════════════════════════════════════════════════════════════════
def verify_journal(path: str) -> dict:
    """저널이 **적힌 그대로인가.** sha256 이 어긋나면 되돌리지 않는다."""
    target = Path(path)
    side = target.with_suffix(".json.sha256")
    if not target.is_file():
        return {"ok": False, "why": f"저널 파일이 없다: {path}"}
    actual = _sha256_of(target)
    if not side.is_file():
        return {"ok": None, "actual": actual,
                "why": "sha256 곁파일이 없다 — **못 쟀다**이지 통과가 아니다"}
    expected = side.read_text(encoding="utf-8").split()[0]
    return {"ok": actual == expected, "actual": actual, "expected": expected,
            "why": "" if actual == expected else "저널이 적힌 것과 다르다"}


def restore_journal(path: str, *, dry_run: bool = True) -> dict:
    """저널을 **되돌린다**. 기본값은 `dry_run=True` (D-209).

    ★ 기본값이 dry-run 인 이유는 파기와 같다: 되돌리기도 DB 를 바꾸는 일이다.
      이미 있는 행은 다시 쓰지 않는다 — 되돌림이 **덮어쓰기**가 되면, 파기 뒤에
      같은 pk 로 들어온 새 행을 옛 행이 덮는다.

    Returns:
        `{"in_journal", "restored", "already_present", "dry_run", "pks"}`.
    """
    from django.core import serializers

    from core.logger.models import AuditLogs

    check = verify_journal(path)
    if check.get("ok") is False:
        raise RuntimeError(f"저널을 믿을 수 없다 — {check.get('why')}")

    raw = Path(path).read_text(encoding="utf-8")
    objects = list(serializers.deserialize("json", raw))
    pks = [obj.object.pk for obj in objects]
    present = set(AuditLogs._base_manager.filter(pk__in=pks)
                  .values_list("pk", flat=True))
    to_restore = [obj for obj in objects if obj.object.pk not in present]

    if not dry_run:
        for obj in to_restore:
            #: `DeserializedObject.save()` → `Model.save_base(raw=True)`.
            #: `raw=True` 라서 `auto_now_add` 가 **다시 찍히지 않는다** —
            #: 되살린 행의 `create_datetime` 이 오늘이 되면 그것은 같은 행이 아니다.
            obj.save()

    return {"in_journal": len(objects), "restored": (0 if dry_run else len(to_restore)),
            "would_restore": len(to_restore), "already_present": len(present),
            "dry_run": dry_run, "pks": pks, "sha256_check": check}


def fingerprint(pks) -> str:
    """되살린 행이 **같은 행인가**를 한 수로 답한다.

    pk 만 견주면 「행이 있다」까지만 안다. 칸 값이 달라졌으면 그것은 되돌림이
    아니라 다시 쓰기다. 그래서 직렬화한 본문 전체의 sha256 을 견준다.
    """
    from django.core import serializers

    from core.logger.models import AuditLogs

    queryset = AuditLogs._base_manager.filter(pk__in=list(pks)).order_by("pk")
    blob = serializers.serialize("json", queryset, indent=None)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# 5. 자기시험 — **도커도 DB 도 없이 도는 부분만**
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    """판정 규칙만 시험한다. 0 통과 · 1 실패."""
    from types import SimpleNamespace

    failures = []

    class _Settings(SimpleNamespace):
        pass

    global settings                                       # noqa: PLW0603
    original = settings
    try:
        settings = _Settings(OPS_BACKUP_DIR="")
        if journal_dir() is not None:
            failures.append("① 선언이 비었는데 자리를 지어냈다")

        settings = _Settings(OPS_BACKUP_DIR="/backup")
        if journal_dir() != str(Path("/backup") / JOURNAL_SUBDIR):
            failures.append("② OPS_BACKUP_DIR 아래로 안 떨어진다")

        settings = _Settings()
        if journal_dir() is not None:
            failures.append("③ 이름이 아예 없을 때도 `None` 이어야 한다")
    finally:
        settings = original

    for line in failures:
        print("  실패 —", line)
    print("자기시험 %s (%d갈래)" % ("통과" if not failures else "실패", 3))
    return 1 if failures else 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(self_test())
