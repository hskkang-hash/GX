# -*- coding: utf-8 -*-
"""테넌트 교차 노출 프로브 — WP-1 goal 을 HTTP 레벨에서 직접 묻는다.

  결과 문서: docs/agent/evidence/W0-14/http_leak_probe.md
  원자료   : docs/agent/evidence/W0-14/leak_matrix.json

⚠ **운영 DB 에서 실행하지 말 것.** 이 스크립트는 대상 사용자의 비밀번호를 재설정한다.
   반드시 로컬 복제본(probe_guardianx)에서만 쓴다.

왜 저장소 시험이 아니라 이 스크립트인가:
  tests/test_tenant_isolation.py 의 API 시험이 픽스처 결함으로 죽어 있고(P-LOCAL-2),
  그 파일은 절대금지 #5 로 수정이 막혀 있다. 그래서 저장소 밖에서 같은 질문을 물었다.
  부수 효과로 합성 픽스처가 아니라 실제 테넌트·실제 사용자로 재게 되었다.
"""
import os, json, sys, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import requests
from django.apps import apps
from django.db import connection

BASE = os.environ.get("PROBE_BASE", "http://127.0.0.1:8000")
# 비밀번호는 반드시 인자로 받는다. 기본값을 두지 않는다 (D-204 · 금지 #2).
# 대상 사용자의 비밀번호를 이 값으로 재설정한다 — **운영 DB 에서 절대 실행하지 말 것.**
# 비밀번호 재사용 금지 정책은 끄지 않는다. 회차마다 다른 값을 넘겨라.
if len(sys.argv) < 2:
    raise SystemExit("사용법: python scripts/probe_tenant_isolation.py '<이번 회차 비밀번호>'")
PW = sys.argv[1]
CoreUser = apps.get_model("user", "CoreUser")

# --- 진실 대장 --------------------------------------------------------------
with connection.cursor() as c:
    c.execute("""SELECT id, name, group_id, created_by_id
                 FROM stream_monitors_streammonitor WHERE deleted IS NULL""")
    TRUTH = {r[0]: {"name": r[1], "group": r[2], "cb": r[3]} for r in c.fetchall()}
    c.execute("""SELECT l.group_id, g.name, min(u.id)
                 FROM user_profile_link l
                 JOIN user_coreuser u ON u.id = l.user_id
                 LEFT JOIN user_usergroup g ON g.id = l.group_id
                 WHERE l.deleted IS NULL AND l.group_id IS NOT NULL
                   AND u.is_active AND NOT u.is_superuser
                   AND EXISTS (SELECT 1 FROM user_coreuser_roles r WHERE r.coreuser_id = u.id)
                 GROUP BY 1, 2 ORDER BY 1""")
    ACTORS = [(r[0], r[1], r[2]) for r in c.fetchall()]

print("TRUTH monitors=%d  created_by_null=%d  group_null=%d"
      % (len(TRUTH),
         sum(1 for v in TRUTH.values() if v["cb"] is None),
         sum(1 for v in TRUTH.values() if v["group"] is None)))
print("ACTORS %d개 테넌트" % len(ACTORS))


def collect(obj, out):
    if isinstance(obj, dict):
        if isinstance(obj.get("id"), int) and "code" in obj:
            out.add(obj["id"])
        for v in obj.values():
            collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect(v, out)


rows = []
for gid, gname, uid in ACTORS:
    u = CoreUser.objects.get(pk=uid)
    try:
        u.set_password(PW)
        u.is_active = True
        u.save()
    except Exception as e:
        rows.append({"gid": gid, "group": gname, "user": u.username,
                     "error": "set_password: %s" % str(e)[:80]})
        print("SKIP  %-14s %-12s %s" % (gname, u.username, str(e)[:70]))
        continue
    roles = ",".join(sorted(u.roles.values_list("code", flat=True)))
    r = requests.post(BASE + "/api/v1/auth/login",
                      json={"username": u.username, "password": PW,
                            "end_previous_session": True}, timeout=90)
    try:
        tok = (r.json().get("user") or {}).get("access_token")
    except Exception:
        tok = None
        print("SKIP  %-14s %-12s login HTTP %s (비JSON 응답)" % (gname, u.username, r.status_code))
    if not tok:
        rows.append({"gid": gid, "group": gname, "user": u.username,
                     "error": "login %s" % r.status_code})
        print("SKIP  %-14s %-12s login %s" % (gname, u.username, r.status_code))
        continue
    g = requests.get(BASE + "/api/stream-monitors/stream-monitors",
                     headers={"Authorization": "Bearer " + tok},
                     params={"page_size": 500, "limit": 500}, timeout=300)
    seen = set()
    try:
        collect(g.json(), seen)
    except Exception:
        pass
    own = {i for i in seen if TRUTH.get(i, {}).get("group") == gid}
    orph = {i for i in seen if TRUTH.get(i) and TRUTH[i]["group"] is None}
    fore = {i for i in seen if TRUTH.get(i) and TRUTH[i]["group"] not in (gid, None)}
    fnull = {i for i in fore if TRUTH[i]["cb"] is None}
    fset = {i for i in fore if TRUTH[i]["cb"] is not None}
    rows.append({"gid": gid, "group": gname, "user": u.username, "roles": roles,
                 "db_is_superuser": u.is_superuser, "http": g.status_code,
                 "seen": len(seen), "own": len(own), "orphan": len(orph),
                 "foreign": len(fore),
                 "foreign_cb_null": sorted((i, TRUTH[i]["name"], TRUTH[i]["group"]) for i in fnull),
                 "foreign_cb_set": sorted((i, TRUTH[i]["name"], TRUTH[i]["group"]) for i in fset)})
    print("%-14s %-11s %-22s HTTP %-3s seen=%-3d own=%-3d orphan=%-2d FOREIGN=%-2d (cb_null=%d cb_set=%d)"
          % (gname, u.username, roles[:22], g.status_code, len(seen), len(own), len(orph),
             len(fore), len(fnull), len(fset)))

print("MATRIX_JSON " + json.dumps(rows, ensure_ascii=False))
