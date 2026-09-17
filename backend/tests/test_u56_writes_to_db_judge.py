# -*- coding: utf-8 -*-
"""`_writes_to_db` 판별기의 사각 둘을 메운 판 — **한 단계 위임(함수 안 import)** · **`.update(` 오인**
(턴 T · 차선 U56 · P-164).

어디에 사는가 — 그리고 왜 여기인가
-----------------------------------
지시서는 판별기를 `scripts/verify_write_auth.py` 라 적었지만 **실물은 다른 곳이다**
[실측 · grep]: `backend/tests/test_tenant_isolation.py::TenantIsolationWriteTest._writes_to_db`
(2424행). 그 파일은 모든 차선의 병합 게이트라 이 차선이 고치지 않는다. 그래서 고친 판별기
`writes_to_db()` 를 **여기** 두고, 그 파일의 `_writes_to_db` 가 이 함수를 한 줄로 부르게 하는
것은 **등록 요청**이다(보고 ③). 그 한 줄이 서기 전까지 실물 대장은 옛 판별기로 돈다 —
이 파일은 옛/새 판별기를 **같은 표본**에 대 「쓰기 면 N → M」 을 찍는다.

사각 ① 한 단계 위임 — 함수 **안에서** import 한 이름은 모듈 이름공간에 없다
    옛 판은 `getattr(module, name)` 으로만 찾았다 → `save_rule` 이 `from …rule_admin import
    save_notification_rule` 을 함수 안에서 하면 못 본다(턴 S 실측 · 그래서 손으로 등재했다).
    새 판은 소스의 `from X import A as B` · `import X` 를 **함수 본문에서** 읽어 그 이름도
    풀고, `모듈.함수(` 꼴(예: `audit.record(`)도 그 모듈에서 찾는다. 여전히 **한 단계**다.

사각 ② `.update(` 오인 — `dict.update`·`set.update` 가 쓰기로 잡혔다
    옛 판은 글자 `.update(` 만 봤다(턴 S 에 `my_notify_reach` 가 그렇게 잡혀 커널 글자를
    바꿔 피했다). 새 판은 `.update(` 앞 문장에 **질의 표식**(objects · _base_manager ·
    _default_manager · .filter( · .exclude( · .all() · select_for_update · queryset/qs)이
    있을 때만 쓰기로 센다.

자기시험 표본 4: 위임 양성 · dict.update 음성 · 직접 쓰기 양성 · 읽기 음성.
"""
from __future__ import annotations

import importlib
import inspect
import re

from django.test import SimpleTestCase

# ── 판별기 ────────────────────────────────────────────────────────────────

#: 글자만으로 쓰기인 표식. `.update(` 는 여기 없다 — 아래 `_update_is_queryset` 이 가른다.
WRITE_MARKERS = (".create(", ".save(", ".delete(", ".bulk_create(", ".bulk_update(",
                 ".get_or_create(", ".update_or_create(", "NotImplementedYet")
_QUERYSET_HINT = re.compile(
    r"(objects|_base_manager|_default_manager|\.filter\(|\.exclude\(|\.all\(\)|"
    r"select_for_update|\bqueryset\b|\bqs\b|\brows\b)")
_UPDATE_CALL = re.compile(r"\.update\(")
_LOCAL_FROM_IMPORT = re.compile(
    r"^\s*from\s+([\w.]+)\s+import\s+\(?([^)\n]+)\)?", re.MULTILINE)
_LOCAL_IMPORT = re.compile(r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?", re.MULTILINE)
_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
_ATTR_CALL = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(")


def _src(fn) -> str:
    try:
        return inspect.getsource(getattr(fn, "__wrapped__", fn))
    except (OSError, TypeError):
        return ""


def _update_is_queryset(src: str) -> bool:
    """`.update(` 가 **질의**에 붙었는가. 같은 문장(앞 두 줄까지)에 질의 표식이 있어야 참."""
    lines = src.splitlines()
    for i, line in enumerate(lines):
        for m in _UPDATE_CALL.finditer(line):
            before = " ".join(lines[max(0, i - 2):i]) + " " + line[:m.start()]
            # 같은 문장으로 본다: 앞 두 줄 + 이 줄의 앞부분. dict/set 은 표식이 없다.
            if _QUERYSET_HINT.search(before):
                return True
    return False


def _source_writes(src: str) -> bool:
    return any(m in src for m in WRITE_MARKERS) or _update_is_queryset(src)


def _local_names(src: str, module) -> dict:
    """함수 본문의 `from X import A as B` · `import X as Y` 를 이름 → 객체로 푼다."""
    names: dict = dict(vars(module)) if module is not None else {}
    pkg = getattr(module, "__package__", None) or ""
    for m in _LOCAL_FROM_IMPORT.finditer(src):
        target, items = m.group(1), m.group(2)
        try:
            mod = importlib.import_module(target, package=pkg) if target.startswith(".") \
                else importlib.import_module(target)
        except Exception:  # noqa: BLE001 — 못 풀면 그 이름은 못 본다(넓히지 않는다)
            continue
        for item in items.split(","):
            item = item.strip()
            if not item:
                continue
            name, _, alias = item.partition(" as ")
            obj = getattr(mod, name.strip(), None)
            if obj is not None:
                names[(alias or name).strip()] = obj
    for m in _LOCAL_IMPORT.finditer(src):
        target, alias = m.group(1), m.group(2)
        try:
            mod = importlib.import_module(target)
        except Exception:  # noqa: BLE001
            continue
        names[alias or target.split(".")[0]] = mod if alias else importlib.import_module(
            target.split(".")[0])
    return names


def writes_to_db(func) -> bool:
    """이 공개 함수가 DB 를 바꾸는가 — 직접 · 또는 **한 단계** 위임(모듈 이름공간 + 함수 안 import)."""
    src = _src(func)
    if _source_writes(src):
        return True
    module = inspect.getmodule(getattr(func, "__wrapped__", func))
    names = _local_names(src, module)
    for name in set(_CALL.findall(src)):
        helper = names.get(name)
        if callable(helper) and not inspect.isclass(helper) and _source_writes(_src(helper)):
            return True
    for base, attr in set(_ATTR_CALL.findall(src)):
        owner = names.get(base)
        if owner is None:
            continue
        helper = getattr(owner, attr, None)
        if callable(helper) and not inspect.isclass(helper) and _source_writes(_src(helper)):
            return True
    return False


# ── 자기시험 표본 4 ──────────────────────────────────────────────────────

def sample_delegates_via_local_import(scope, **kw):
    """위임 양성 — 쓰는 쪽(**다른 모듈**)을 **함수 안에서** import 한다(옛 판이 못 본 모양).

    `_w` 는 이 모듈의 이름공간에 없다 — 옛 판의 `getattr(module, "_w")` 는 None 이다.
    실물의 `kernels.k2_notify.save_rule` 이 정확히 이 모양이다(턴 S 실측).
    """
    from kernels.k2_notify.services import save_notification_rule as _w

    return _w(scope=scope, **kw)


def sample_dict_update_only(cfg):
    """dict.update 음성 — 옛 판이 쓰기로 오인한 모양."""
    merged = {}
    merged.update(cfg)
    return merged


def sample_direct_create(Model):
    """직접 쓰기 양성."""
    return Model.objects.create(name="x")


def sample_read_only(Model):
    """읽기 음성."""
    return Model._base_manager.filter(pk=1).first()


# ═══════════════════════════════════════════════════════════════════════════
# 옛 판별기 — **보존본** (턴 T 병합 · 조율자). `test_tenant_isolation._writes_to_db` 는 이제 위의
# `writes_to_db` 로 위임하므로 옛 본문은 저기서 사라졌다. 사각 둘을 **실물로** 보이는 아래 시험이
# 계속 살아 있으려면 옛 판이 여기 있어야 한다 — 「고쳐졌다」의 증거는 고치기 전 것과의 대조다.
# 본문은 `git show pre-turn-t:backend/tests/test_tenant_isolation.py` 의 그 함수 그대로다.
# ═══════════════════════════════════════════════════════════════════════════
def legacy_writes_to_db(func) -> bool:
    """이 공개 함수가 DB 를 바꾸는가.

    `@transaction.atomic` 은 **쓰기에만** 붙는다(읽기에 붙일 이유가 없다).
    완벽한 판별은 아니지만 **추측이 아니라 코드에 있는 표식**이고, 놓치는 쪽으로
    틀리면 위의 단언이 조용히 통과한다 — 그래서 소스 본문도 함께 본다.
    """
    import inspect
    import re

    markers = (".create(", ".save(", ".update(", ".delete(", "NotImplementedYet")

    def _src(fn):
        try:
            return inspect.getsource(getattr(fn, "__wrapped__", fn))
        except (OSError, TypeError):
            return ""

    src = _src(func)
    if any(m in src for m in markers):
        return True

    # ★ 2026-09-22 (P-20) — **한 단계 위임까지 따라간다.**
    #
    #   [실측] 이 판별기는 `kernels.k2_notify.send` 를 **읽기로 봤다.** 그 함수는
    #   행을 만들지 않고 `_send_one()` 에게 시키며, 표식은 그 안에 있다. 같은 이유로
    #   `suppress`·`notice_false_positive` 도 안 보였다 — 그런데 그날 시드가
    #   `send` 하나로 **발송 이력 120행**을 만들었다. 즉 대장은 **자기가 안 보는
    #   곳에서 늘어난 쓰기 면을 초록으로 통과**시키고 있었다(D-301 의 이 파일 판).
    #
    #   왜 한 단계만인가 — 끝까지 따라가면 결국 ORM 이 나오므로 **모든 함수가
    #   쓰기**가 된다. 한 단계는 「공개 면이 자기 모듈의 사설 헬퍼에게 시킨다」는
    #   실제 모양을 덮으면서, 판별을 뜻 있게 남긴다. 두 단계가 필요한 자리가
    #   나오면 그때 늘린다 — **그 사례를 보고 나서** 늘린다.
    module = inspect.getmodule(getattr(func, "__wrapped__", func))
    if module is None:
        return False
    # ★ 2026-09-04 (차선 D 가 잡은 남은 반쪽) — **다른 모듈에서 들여온 이름**도 본다.
    #   [실측] `kernels.k2_notify.renotify` 는 `send()` 하나로 `DeliveryRecord` 행을
    #   만드는데 판별기는 그것을 **읽기로 봤다**: 09-22 판은 같은 모듈의 `_` 헬퍼만
    #   따라갔고, `send` 는 `_` 로 시작하지 않으며 다른 모듈에서 들어온 이름이다.
    #   선등재가 없었으면 **조용히 통과했을 자리**다.
    #   → 부르는 이름을 **그 모듈의 이름 공간에서** 찾는다(들여온 것 포함).
    #   ⚠ 여전히 **한 단계만**이다 — 끝까지 따라가면 결국 ORM 이 나오고,
    #     그러면 모든 함수가 쓰기가 된다.
    for name in set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src)):
        helper = getattr(module, name, None)
        if callable(helper) and not inspect.isclass(helper):
            if any(m in _src(helper) for m in markers):
                return True
    return False


class WritesToDbJudgeSelfTest(SimpleTestCase):
    def test_four_samples(self):
        self.assertTrue(writes_to_db(sample_delegates_via_local_import), "위임 양성")
        self.assertFalse(writes_to_db(sample_dict_update_only), "dict.update 음성")
        self.assertTrue(writes_to_db(sample_direct_create), "직접 쓰기 양성")
        self.assertFalse(writes_to_db(sample_read_only), "읽기 음성")

    def test_queryset_update_still_counts(self):
        def qs_update(Model):
            Model.objects.filter(pk=1).update(x=1)

        self.assertTrue(writes_to_db(qs_update))

    def test_old_judge_had_the_two_blind_spots(self):
        """옛 판별기의 사각을 **실물로** 적는다 — 이 시험이 빨강이 되면 옛 판이 고쳐진 것이다."""
        from kernels.k2_notify import save_rule

        old = legacy_writes_to_db   # (턴 T 병합) 옛 판은 이 파일의 보존본이다
        self.assertFalse(old(sample_delegates_via_local_import), "옛 판: 함수 안 import 위임을 못 본다")
        self.assertFalse(old(save_rule), "옛 판: 실물 save_rule 도 못 본다(턴 S 실측 그대로)")
        self.assertTrue(writes_to_db(save_rule), "새 판: 실물 save_rule 을 본다")
        self.assertTrue(old(sample_dict_update_only), "옛 판: dict.update 를 쓰기로 오인한다")

    def test_before_after_on_the_real_registry_packages(self):
        """실물 전/후 — 옛 판이 훑는 여섯 꾸러미의 `__all__` 에 두 판별기를 대 본다."""
        old = legacy_writes_to_db   # (턴 T 병합) 옛 판은 이 파일의 보존본이다
        packages = ("kernels.k1_event", "kernels.k2_notify",
                    "stream_monitors.services.zones",
                    "stream_monitors.services.camera_pulse",
                    "stream_monitors.services.drill",
                    "stream_monitors.services.bulk_register")
        before, after, total = [], [], 0
        for package in packages:
            module = importlib.import_module(package)
            for name in getattr(module, "__all__", []):
                func = getattr(module, name, None)
                if not callable(func) or inspect.isclass(func):
                    continue
                total += 1
                dotted = f"{package}.{name}"
                if old(func):
                    before.append(dotted)
                if writes_to_db(func):
                    after.append(dotted)
        gained = sorted(set(after) - set(before))
        lost = sorted(set(before) - set(after))
        print("\n[WRITES-JUDGE] 공개 함수 %d · 쓰기 면 %d → %d · 새로 보임 %s · 빠짐 %s"
              % (total, len(before), len(after), gained, lost))
        self.assertGreater(total, 0, "분모 0")
