# -*- coding: utf-8 -*-
"""P-57 — **「지운다」는 「그대로 지운다」다** (파기 · 2026-09-05 · 차선 E).

이 파일이 묻는 것 여섯
----------------------
① **행이 진짜로 없어지는가** — 「지움」 표시가 아니라 행이 사라져야 한다.
   그리고 그 사실을 `_base_manager` · `all_objects` · `deleted_objects` **셋으로**
   확인한다. 한 매니저만 보면 소프트 삭제가 그 매니저에만 안 보일 수 있다.
② **선언이 먼저다** — 보존 일수를 선언하지 않은 테넌트는 한 행도 안 지운다.
   ★ 이것이 이 파일의 절반이다. 지우는 것보다 **안 지우는 것**이 더 어렵다.
③ **테넌트 격리** — A 를 파기해도 B 의 행은 남는다. 남의 테넌트 파기는 사고다.
④ **dry-run 이 기본값** — 인자 없이 부른 파기는 아무것도 안 지운다.
⑤ **파기 기록이 남는다** — 부름 하나에 감사 한 줄. 건너뜀도 남는다.
⑥ **바이트를 못 지웠으면 행을 남긴다** — 고아 영상을 만들지 않는다.

★ **출생 표본** (D-310) — 이 시험을 쓰게 한 사례
------------------------------------------------
합성이 아니다. [실측 2026-09-05 · gx-shell · test DB · EventClip 1행]

    clip.delete()  →  _base_manager 1 · all_objects 1 · deleted_objects 1 · objects 1

즉 **`delete()` 를 불렀는데 행이 남아 있었다.** dj-core `BaseModel` 이
`SafeDeleteModel(SOFT_DELETE_CASCADE)` 이기 때문이다 [실측 core/base.py:2059].
게다가 `objects` 가 `CustomManagerGroup(models.Manager)` 로 덮여 있어
**소프트 삭제된 행이 평범한 조회에서도 보인다** [실측 core/base.py:2082].
아래 `TheDeleteIsRealTest.test_plain_delete_is_the_birth_sample` 이 그 상태를
**그대로 재현하고**, 그 다음 시험이 파기가 그것을 넘어서는 것을 잰다.
"""
from datetime import timedelta

from django.apps import apps
from django.test import override_settings
from django.utils import timezone

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다. 합성 더미를 지우지 않는다.
REAL_SAMPLE = (
    "apps.dsm.retention.purge · stream_monitors.StreamMonitorRecord · "
    "stream_monitors.EventClip · stream_monitors.DetectionEvent · "
    "logger.AuditLogs · user.UserGroup — 저장소의 실제 모듈과 표"
)


def _model(name):
    return apps.get_model("stream_monitors", name)


def _age(model, pk, *, field, days):
    """행 하나를 **과거로 민다.** `auto_now_add` 칸은 create 로는 못 정한다."""
    model._base_manager.filter(pk=pk).update(
        **{field: timezone.now() - timedelta(days=days)})


class PurgeFixture(DsmFixture):
    """테넌트 A 에 만료된 녹화 1건 · 안 만료된 녹화 1건 · B 에 만료된 녹화 1건."""

    def setUp(self):
        Record = _model("StreamMonitorRecord")
        self.old_a = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="old-a", object_path="")
        self.new_a = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="new-a", object_path="")
        self.old_b = Record._base_manager.create(
            stream_id=str(self.stream_b.pk), code="old-b", object_path="")
        _age(Record, self.old_a.pk, field="created_at", days=999)
        _age(Record, self.old_b.pk, field="created_at", days=999)

    #: 테넌트 A 만 30일을 선언한 상태. B 는 **선언하지 않았다.**
    def declared_a_only(self):
        return override_settings(
            VIDEO_RETENTION_DAYS_BY_TENANT={self.group_a.pk: 30})


class TheDeleteIsRealTest(PurgeFixture):
    """① 행이 **진짜로** 없어지는가."""

    def test_plain_delete_is_the_birth_sample(self):
        """★ **출생 표본** — `delete()` 를 불렀는데 행이 남아 있다.

        이 시험이 초록이면 그것은 「소프트 삭제가 고쳐졌다」가 아니라
        **이 저장소가 여전히 그 상태다**라는 사실의 기록이다. 언젠가 dj-core 가
        바뀌어 이 시험이 빨개지면, 그때 이 파일이 존재하는 이유가 사라진 것이고
        **그 사실을 이 시험이 알려 준다.**
        """
        Clip = _model("EventClip")
        clip = Clip._base_manager.create(
            event_id=self._event(self.stream_a), object_key="",
            clip_status="referenced", start_offset=0.0, duration=30.0)
        pk = clip.pk
        clip.delete()
        self.assertTrue(
            Clip._base_manager.filter(pk=pk).exists(),
            "출생 표본이 재현되지 않았다 — delete() 가 이제 행을 지운다면 "
            "이 파일의 전제가 바뀐 것이다. 머리말을 다시 쓸 것")
        self.assertTrue(
            Clip.objects.filter(pk=pk).exists(),
            "소프트 삭제된 행이 objects 에서 사라졌다 — dj-core 의 매니저 덮어쓰기가 "
            "바뀐 것이다. metering._alive() 의 전제를 다시 잴 것")

    def test_purge_actually_removes_the_row_from_every_manager(self):
        """파기는 **세 매니저 전부에서** 행을 없앤다."""
        from apps.dsm.retention import purge

        Record = _model("StreamMonitorRecord")
        with self.declared_a_only():
            result = purge(group_id=self.group_a.pk, dry_run=False,
                           actor=self.user_a, reason="시험 — 파기")

        self.assertEqual(result["verdict"], "PURGED")
        self.assertGreaterEqual(result["deleted_total"], 1)
        for name in ("_base_manager", "objects", "all_objects", "deleted_objects"):
            manager = getattr(Record, name, None)
            if manager is None:
                continue
            self.assertFalse(
                manager.filter(pk=self.old_a.pk).exists(),
                f"{name} 에 아직 남아 있다 — 파기가 아니라 지운 척이다")

    def test_fresh_rows_survive(self):
        """★ 음성 대조 — **안 지난 것까지 지우면** 그것은 「다 버린다」이다."""
        from apps.dsm.retention import purge

        Record = _model("StreamMonitorRecord")
        with self.declared_a_only():
            purge(group_id=self.group_a.pk, dry_run=False, actor=self.user_a,
                  reason="시험 — 음성 대조")
        self.assertTrue(Record._base_manager.filter(pk=self.new_a.pk).exists(),
                        "기간이 안 지난 녹화까지 지웠다")


class DeclarationComesFirstTest(PurgeFixture):
    """② ★ **선언이 먼저다** — 이 절의 절반이다 (지시서 §4 함정 ㉡)."""

    def test_an_undeclared_tenant_is_not_purged(self):
        """선언하지 않은 테넌트는 **한 행도** 안 지워진다."""
        from apps.dsm.retention import SKIPPED_UNDECLARED, purge

        Record = _model("StreamMonitorRecord")
        with self.declared_a_only():
            result = purge(group_id=self.group_b.pk, dry_run=False,
                           actor=self.user_a, reason="시험 — 미선언 테넌트")

        self.assertEqual(result["verdict"], SKIPPED_UNDECLARED)
        self.assertEqual(result["deleted_total"], 0)
        self.assertIsNone(result["retention_days"],
                          "선언이 없는데 수가 나왔다 — 제품 기본값이 파기 명령이 됐다")
        self.assertTrue(Record._base_manager.filter(pk=self.old_b.pk).exists(),
                        "★ 선언하지 않은 테넌트의 영상을 지웠다 — 우리가 남의 자료를 "
                        "버린 것이다")

    def test_the_product_default_is_not_a_purge_order(self):
        """제품 기본값 30일이 있어도 **선언이 없으면 파기하지 않는다.**

        `retention_days()` 는 언제나 30을 낸다(안내판에는 그것이 옳다).
        `declared_retention_days()` 는 `None` 을 내야 한다 — 두 함수가 같은 값을
        내기 시작하면 「선언이 먼저다」가 사라진다.
        """
        from apps.dsm.retention import (DEFAULT_RETENTION_DAYS,
                                        declared_retention_days, retention_days)

        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={}):
            self.assertEqual(retention_days(), DEFAULT_RETENTION_DAYS)
            self.assertIsNone(declared_retention_days(self.group_a.pk))

    def test_declared_tenants_lists_only_the_declared(self):
        from apps.dsm.retention import declared_tenants

        with self.declared_a_only():
            ids = {r["group_id"] for r in declared_tenants()}
        self.assertIn(self.group_a.pk, ids)
        self.assertNotIn(self.group_b.pk, ids,
                         "선언하지 않은 테넌트가 파기 대상 목록에 올랐다")

    def test_a_zero_declaration_is_not_a_declaration(self):
        """0일 선언은 「즉시 파기」다 — **선언으로 세지 않는다.**"""
        from apps.dsm.retention import declared_retention_days

        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={
                self.group_a.pk: 0}):
            self.assertIsNone(declared_retention_days(self.group_a.pk))

    def test_the_periodic_run_only_touches_declared_tenants(self):
        """주기 집행이 **선언한 테넌트만** 돈다 (celery 가 서면 실제로 돈다)."""
        from apps.dsm.retention import purge_all_declared

        Record = _model("StreamMonitorRecord")
        with self.declared_a_only():
            result = purge_all_declared(dry_run=False, actor=None,
                                        reason="시험 — 주기 집행")

        self.assertGreaterEqual(result["skipped_undeclared"], 1,
                                "미선언 테넌트가 하나도 없다고 말한다")
        self.assertFalse(Record._base_manager.filter(pk=self.old_a.pk).exists())
        self.assertTrue(Record._base_manager.filter(pk=self.old_b.pk).exists(),
                        "★ 주기 집행이 미선언 테넌트를 지웠다")


class TenantIsolationTest(PurgeFixture):
    """③ A 를 파기해도 **B 는 그대로다.**"""

    def test_purging_a_does_not_touch_b(self):
        from apps.dsm.retention import purge

        Record = _model("StreamMonitorRecord")
        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={
                self.group_a.pk: 30, self.group_b.pk: 30}):
            purge(group_id=self.group_a.pk, dry_run=False, actor=self.user_a,
                  reason="시험 — 격리")
        self.assertFalse(Record._base_manager.filter(pk=self.old_a.pk).exists())
        self.assertTrue(Record._base_manager.filter(pk=self.old_b.pk).exists(),
                        "★ 남의 테넌트 영상을 지웠다 — 되돌릴 수 없는 사고다")

    def test_every_target_is_tenant_scoped_or_untouched(self):
        """좁힐 수 없는 표는 **UNKNOWN 이고 한 행도 안 건드린다.**"""
        from apps.dsm.retention import purge

        with self.declared_a_only():
            result = purge(group_id=self.group_a.pk, dry_run=True,
                           actor=self.user_a, reason="시험 — 좁히기")
        for target in result["targets"]:
            if target["verdict"] == "UNKNOWN":
                self.assertEqual(target["deleted"], 0)
                continue
            self.assertTrue(
                target["tenant_scoped"],
                f"{target['model']} 이 테넌트로 안 좁혀진 채 파기 대상이 됐다")


class DryRunIsTheDefaultTest(PurgeFixture):
    """④ **되돌릴 수 없는 일의 기본값은 「안 한다」이다** (D-209)."""

    def test_calling_purge_without_dry_run_argument_deletes_nothing(self):
        from apps.dsm.retention import purge

        Record = _model("StreamMonitorRecord")
        with self.declared_a_only():
            result = purge(group_id=self.group_a.pk)      # ★ 인자 없이
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["verdict"], "PREVIEWED")
        self.assertEqual(result["deleted_total"], 0)
        self.assertGreater(result["expired_total"], 0,
                           "만료 건수를 세지도 못했다면 미리보기가 아니다")
        self.assertTrue(Record._base_manager.filter(pk=self.old_a.pk).exists(),
                        "미리보기가 행을 지웠다")


class ThePurgeIsRecordedTest(PurgeFixture):
    """⑤ **파기 기록** — 부름 하나에 감사 한 줄."""

    def _count(self, action):
        AuditLogs = apps.get_model("logger", "AuditLogs")
        return AuditLogs._base_manager.filter(api_name=action).count()

    def test_one_purge_writes_exactly_one_record(self):
        from apps.dsm.retention import PURGE_ACTION, purge

        before = self._count(PURGE_ACTION)
        with self.declared_a_only():
            result = purge(group_id=self.group_a.pk, dry_run=False,
                           actor=self.user_a, reason="시험 — 파기 기록")
        self.assertEqual(self._count(PURGE_ACTION), before + 1)

        AuditLogs = apps.get_model("logger", "AuditLogs")
        row = AuditLogs._base_manager.get(pk=result["audit_id"])
        after = row.data_after or {}
        self.assertEqual(after.get("group_id"), self.group_a.pk)
        self.assertFalse(after.get("dry_run"))
        self.assertGreaterEqual(after.get("deleted_total", 0), 1)
        #: ★ LAW-08 체인 위에 얹혔는가. 안 얹히면 뒤에서 조용히 고칠 수 있다.
        self.assertTrue(result["row_hash"])

    def test_a_skip_is_also_recorded(self):
        """건너뜀도 남는다 — 「안 지웠다」와 「부른 적 없다」는 다른 사실이다."""
        from apps.dsm.retention import PURGE_SKIPPED_ACTION, purge

        before = self._count(PURGE_SKIPPED_ACTION)
        with self.declared_a_only():
            purge(group_id=self.group_b.pk, dry_run=False, actor=self.user_a,
                  reason="시험 — 건너뜀 기록")
        self.assertEqual(self._count(PURGE_SKIPPED_ACTION), before + 1)

    def test_the_history_is_readable_and_tenant_narrowed(self):
        """「지운 기록」이 읽히고, 테넌트로 좁힐 수 있다."""
        from apps.dsm.retention import purge, purge_history

        with self.declared_a_only():
            purge(group_id=self.group_a.pk, dry_run=False, actor=self.user_a,
                  reason="시험 — 이력")
            purge(group_id=self.group_b.pk, dry_run=False, actor=self.user_a,
                  reason="시험 — 이력(미선언)")

        mine = purge_history(group_id=self.group_a.pk, limit=20)
        self.assertTrue(mine, "내 테넌트 파기 기록이 하나도 안 나온다")
        self.assertTrue(all(r["group_id"] == self.group_a.pk for r in mine),
                        "★ 남의 테넌트 파기 기록이 섞여 나왔다")


class ObjectFailureKeepsTheRowTest(PurgeFixture):
    """⑥ **바이트를 못 지웠으면 행을 남긴다** — 고아 영상을 만들지 않는다."""

    def test_a_failed_object_delete_does_not_delete_the_row(self):
        from unittest.mock import patch

        from apps.dsm import retention

        Record = _model("StreamMonitorRecord")
        row = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="obj",
            object_path="gx-bucket/old/video.mp4")
        _age(Record, row.pk, field="created_at", days=999)

        with self.declared_a_only(), patch.object(
                retention, "_remove_object", return_value="저장소가 죽었다"):
            result = retention.purge(group_id=self.group_a.pk, dry_run=False,
                                     actor=self.user_a,
                                     reason="시험 — 저장소가 죽었을 때")

        self.assertTrue(Record._base_manager.filter(pk=row.pk).exists(),
                        "바이트를 못 지웠는데 행을 지웠다 — 그 영상은 이제 고아다")
        self.assertGreaterEqual(result["object_failure_total"], 1,
                                "못 지운 사실이 응답에 안 남았다 — 조용한 실패다")

    def test_the_object_is_removed_before_the_row(self):
        """바이트가 지워지면 **객체 수가 센다.** 「행만 지웠다」와 가른다."""
        from unittest.mock import patch

        from apps.dsm import retention

        Record = _model("StreamMonitorRecord")
        row = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="obj-ok",
            object_path="gx-bucket/old/video.mp4")
        _age(Record, row.pk, field="created_at", days=999)

        with self.declared_a_only(), patch.object(
                retention, "_remove_object", return_value="") as removed:
            result = retention.purge(group_id=self.group_a.pk, dry_run=False,
                                     actor=self.user_a, reason="시험 — 객체 삭제")

        self.assertGreaterEqual(result["objects_deleted_total"], 1)
        self.assertFalse(Record._base_manager.filter(pk=row.pk).exists())
        self.assertIn("gx-bucket/old/video.mp4",
                      [c.args[0] for c in removed.call_args_list])

    def test_dry_run_never_touches_the_object_store(self):
        """미리보기는 **저장소를 부르지도 않는다.** 부르면 그것은 이미 쓰기다."""
        from unittest.mock import patch

        from apps.dsm import retention

        Record = _model("StreamMonitorRecord")
        row = Record._base_manager.create(
            stream_id=str(self.stream_a.pk), code="obj-dry",
            object_path="gx-bucket/old/video.mp4")
        _age(Record, row.pk, field="created_at", days=999)

        with self.declared_a_only(), patch.object(
                retention, "_remove_object", return_value="") as removed:
            retention.purge(group_id=self.group_a.pk, dry_run=True,
                            actor=self.user_a, reason="시험 — 미리보기")
        self.assertEqual(removed.call_count, 0,
                         "미리보기가 객체저장소를 불렀다 — 되돌릴 수 없는 쪽으로 샜다")


# ═══════════════════════════════════════════════════════════════════════════
# 문 — **되돌릴 수 없는 문에는 문지기가 둘이다** (D-275 §5-1)
#
# 캐시 처리: 우회 — `X-No-Cache`(`tests.no_cache.NO_CACHE`). 적중한 본문은 언제나
# 200 이고(P-19), 200 뒤에 숨은 파기 실패는 아무도 못 본다.
# ═══════════════════════════════════════════════════════════════════════════
class PurgeDoorIsGuardedTest(PurgeFixture):
    """★ 이 시험이 **화면이 처음 뜨는 순간**을 대신 잰다 (D-378).

    단위 시험은 `purge()` 를 직접 부른다. 라우트가 질의 인자를 만드는 순간에
    죽는 결함은 그 길로는 안 잡히고, 화면을 띄운 그날에 나온다.
    """

    READ_PATHS = ("/api/dsm/law/purge/tenants", "/api/dsm/law/purge/history")
    WRITE_PATH = "/api/dsm/law/purge"

    def setUp(self):
        super().setUp()
        from django.test import Client

        from tests.no_cache import NO_CACHE

        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _admin_user(self):
        """이 테넌트의 **관리자**. 파기 문은 관리자만 두드린다.

        ★ 역할 코드는 `tenant_admin_<group_id>` 규약이고, **그 역할의 group 이
          요청자의 group 과 같아야** 참이다 [실측 common/tenant_roles.py:98].
          코드만 붙이고 소유를 안 붙이면 여전히 403 이고, 그 403 을 「문이 잘 막혔다」로
          읽으면 정작 관리자 경로를 한 번도 안 재고 지나간다.
        """
        from common.tenant_roles import tenant_admin_role_code

        role = self._own(self._role(tenant_admin_role_code(self.group_a.pk)),
                         self.group_a)
        self.user_a.roles.add(role)
        return self.user_a

    def _bearer(self, user):
        """접근 토큰 하나. **세션까지 묶는다** — 안 묶으면 토큰이 있어도 401 이다."""
        import jwt as pyjwt
        from django.conf import settings
        from ninja_jwt.tokens import RefreshToken

        session_id = "gx-p57-test"
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        user.set_encrypted_session_token(session_id, decoded.get("jti"))
        user.save()
        return f"Bearer {access}"

    def test_anonymous_cannot_reach_any_purge_door(self):
        """익명에게는 **200 이 아니다** — 읽는 문도 지우는 문도."""
        for path in self.READ_PATHS:
            self.assertEqual(401, self.client.get(path).status_code,
                             f"익명이 {path} 를 200 으로 받았다")
        self.assertEqual(401, self.client.post(self.WRITE_PATH).status_code,
                         "★ 익명이 파기 문을 두드릴 수 있다")

    def test_every_purge_door_is_in_the_route_ledger_with_both_guards(self):
        from common.tenant_scope import enumerate_operations

        ledger = {(r.path, r.method): r for r in enumerate_operations()}
        wanted = [(p, "GET") for p in self.READ_PATHS] + [(self.WRITE_PATH, "POST")]
        for key in wanted:
            row = ledger.get(key)
            self.assertIsNotNone(row, f"{key} 가 라우트 대장에 없다")
            self.assertTrue(row.has_auth, f"{key} 는 인증 없는 진입면이다")
            self.assertIsNotNone(row.scope, f"{key} 에 테넌트 문지기가 없다")

    def test_the_declared_list_answers_over_http(self):
        """대상 목록이 **문으로** 나온다. 500 이면 여기서 빨개진다."""
        import json

        from django.test import override_settings

        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={
                self.group_a.pk: 30}):
            resp = self.client.get(
                "/api/dsm/law/purge/tenants",
                HTTP_AUTHORIZATION=self._bearer(self._admin_user()),
                **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertIn(self.group_a.pk, [r["group_id"] for r in body["declared"]])

    def test_the_write_door_refuses_a_purge_without_a_reason(self):
        """★ 되돌릴 수 없는 일에는 **사유가 남아야 한다** — 없으면 422."""
        with self.declared_a_only():
            resp = self.client.post(
                f"{self.WRITE_PATH}?dry_run=false&reason=",
                HTTP_AUTHORIZATION=self._bearer(self._admin_user()),
                **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(422, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))

    def test_the_preview_door_answers_and_deletes_nothing(self):
        """미리보기는 문으로도 **아무것도 안 지운다.**"""
        import json

        Record = _model("StreamMonitorRecord")
        with self.declared_a_only():
            resp = self.client.post(
                f"{self.WRITE_PATH}?dry_run=true",
                HTTP_AUTHORIZATION=self._bearer(self._admin_user()),
                **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(body["dry_run"])
        self.assertEqual(body["deleted_total"], 0)
        self.assertTrue(Record._base_manager.filter(pk=self.old_a.pk).exists())

    def test_a_tenant_admin_cannot_purge_another_tenant(self):
        """★ 403 — 남의 테넌트 영상은 이 문으로 나가지 않는다."""
        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={
                self.group_a.pk: 30, self.group_b.pk: 30}):
            resp = self.client.post(
                f"{self.WRITE_PATH}?group_id={self.group_b.pk}&dry_run=true",
                HTTP_AUTHORIZATION=self._bearer(self._admin_user()),
                **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(403, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))
