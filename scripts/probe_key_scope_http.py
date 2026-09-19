# -*- coding: utf-8 -*-
"""[실측] 범위 밖 들어오는 키가 **HTTP 로 403** 을 받는가 — 실 서버(nginx 8500)로 누른다.

값은 출력하지 않는다 — 키는 sha256 앞 12자로만 적는다.
"""
import hashlib, json, os, sys, urllib.error, urllib.request

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from common.tenant_scope import TenantScope
from kernels.k5_trust import issue_key, revoke_key, set_key_scopes

BASES = [b for b in (os.environ.get("GX_BASE") or "http://gx-nginx-e:8500,http://gx-gunicorn-e:8000").split(",") if b]
PATH = "/api/dsm/events"

User = get_user_model()
actor = None
for u in User.objects.filter(is_active=True).order_by("pk"):
    try:
        s = TenantScope.of(u)
        s.require_actor()
        from common.tenant_filters import require_user_group
        require_user_group(u)
    except Exception:
        continue
    actor = u
    break
if actor is None:
    sys.exit("소속 있는 활성 사용자를 못 찾았다 — 분모 0 이다.")
scope = TenantScope.of(actor)
print("[actor] user_id=%s" % actor.pk)


def press(secret, label, base):
    req = urllib.request.Request(base + PATH, headers={"X-API-Key": secret,
                                                       "X-No-Cache": "true"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    try:
        detail = json.loads(body.decode("utf-8")).get("detail", "")
    except Exception:
        detail = body[:120].decode("utf-8", "replace")
    print("[%s] fp=%s  GET %s%s -> %s  detail=%s"
          % (label, hashlib.sha256(secret.encode()).hexdigest()[:12], base, PATH, code, detail))
    assert secret not in body.decode("utf-8", "replace"), "본문에 키가 실렸다"
    return code


made = []
try:
    inside = issue_key(scope=scope, name="u56-turnv-probe-inside")
    set_key_scopes(scope=scope, key_id=inside.view.key_id, scopes="events:read")
    made.append(inside.view.key_id)
    outside = issue_key(scope=scope, name="u56-turnv-probe-outside")
    set_key_scopes(scope=scope, key_id=outside.view.key_id, scopes="stats:read")
    made.append(outside.view.key_id)
    unset = issue_key(scope=scope, name="u56-turnv-probe-unset")
    made.append(unset.view.key_id)

    res = {}
    for base in BASES:
        res[base] = {
            "inside": press(inside.secret, "범위 안 events:read", base),
            "outside": press(outside.secret, "범위 밖 stats:read", base),
            "unset": press(unset.secret, "미설정(옛 키)", base),
        }
finally:
    for kid in made:
        try:
            revoke_key(scope=scope, key_id=kid)
        except Exception as exc:
            print("[cleanup] key_id=%s 폐기 실패: %s" % (kid, exc))

print("GX_SCOPE_HTTP " + json.dumps(res, ensure_ascii=False))
ok = all(v["inside"] not in (401, 403) and v["outside"] == 403 and v["unset"] == 403
         for v in res.values())
print("VERDICT " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
