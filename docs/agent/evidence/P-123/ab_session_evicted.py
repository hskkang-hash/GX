# -*- coding: utf-8 -*-
"""A/B — 같은 계정으로 **두 번째 로그인**이 들어오면 첫 토큰의 목록 호출이 어떻게 되나."""
import json, os, urllib.request, urllib.error
BASE="http://gx-nginx-e:8500"; USER=os.environ["U"]; PW=os.environ["GX_SEED_ROLE_PASSWORD"]
def req(method,p,tok=None,body=None):
    data=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(BASE+p,data=data,method=method,
      headers={"Content-Type":"application/json",**({"Authorization":"Bearer "+tok} if tok else {})})
    try:
        resp=urllib.request.urlopen(r,timeout=30); return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
def login():
    st,b=req("POST","/api/v1/auth/login",body={"username":USER,"password":PW,"end_previous_session":True})
    return json.loads(b).get("user",{}).get("access_token")
def peek(tag,tok):
    for p in ("/api/v1/user/list/","/api/roles/"):
        st,b=req("GET",p,tok)
        try:
            j=json.loads(b); n=j.get("count")
            rc=j.get("reason_code")
            print("  %-8s %-22s %s count=%s reason_code=%s" % (tag,p,st,n,rc))
        except Exception:
            print("  %-8s %-22s %s RAW %r" % (tag,p,st,b[:120]))
t1=login(); print("[A] 첫 로그인 tok?",bool(t1)); peek("A",t1)
t2=login(); print("[B] 같은 계정으로 **두 번째** 로그인 tok?",bool(t2))
print("[A'] 첫 토큰으로 다시:"); peek("A'",t1)
print("[B'] 둘째 토큰으로:");   peek("B'",t2)
