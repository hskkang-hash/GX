# D-373 `backup_last.json` 은 **오염된 증거다** — 지우지 않고 이름을 붙인다

[실측 2026-09-06 · 턴 I · 차선 E 가 잡고 차선 Q 가 막음 · P-87 ④]

## 1. 파일에 남은 것

```json
{
  "measured_at": "2026-09-06T13:49:34+00:00",   ← 처음 잡혔을 때는 11:06:45 였다
  "verdict": "SKIPPED_UNDECLARED",
  "reason": "백업 목적지가 **선언되지 않았다**(`OPS_BACKUP_DIR`) …"
}
```

## 2. 같은 순간 이 환경의 사실 [실측]

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell python -c "…"
  OPS_BACKUP_DIR='/backup'
  ENABLED=True
  DB='database_guardianx'
```

**둘이 어긋난다.** 파일을 읽은 사람은 「개발 환경이 미선언이라 백업을 건너뛰었다」로
읽는다 — 그렇지 않다.

## 3. 누가 썼나 — 판정기다

```
scripts/verify_retention_declared.py:371
    with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=True, OPS_BACKUP_DIR=""):
        out = ops_tasks.ops_backup_beat()
```

이 판정기는 「목적지가 미선언이면 백업 도구를 **한 번도 안 부르는가**」를 재려고
설정을 일부러 비워 놓고 백업 주기를 부른다. 그 호출이
`ops_tasks._write_evidence("backup_last", …)` 를 타고 **이 파일에 그대로 떨어졌다.**

## 4. 왜 앞선 가드가 못 막았나 — **질문이 틀렸다**

`_write_evidence` 에는 이미 가드가 있었다:

```python
if os.environ.get("PYTEST_CURRENT_TEST"):
    return None
```

**판정기는 시험이 아니다.** 그래서 이 줄을 그냥 지나갔다.
물어야 할 것은 「시험 중인가」가 아니라 **「이 수가 진짜 상태에서 났는가」**였다.

## 5. 무엇을 고쳤나 (턴 I · 차선 Q)

| 자리 | 무엇 |
|---|---|
| `backend/common/evidence_guard.py` | 술어를 **한 자리**로 모으고 셋을 묻는다 — ① 지어낸 상태(`synthetic_run`) ② 시험 DB(`test_…`) ③ 시험 중 |
| `backend/conftest.py` | 쓰기 원시함수(`open`·`os.replace`·`os.rename`·`os.remove`)에 **바닥 그물**. 술어를 안 부르는 경로까지 잡는다 |
| `scripts/verify_retention_declared.py` | 새던 그 한 줄을 `evidence_guard.synthetic_run(...)` 안에 넣었다 |
| `backend/common/ops_tasks.py` | 증거 payload 에 `_written_from` 을 박는다 — `{"db": …, "under_pytest": …}` |
| `backend/tests/test_evidence_guard.py` | **출생 표본 2** — 깃발 둘을 지우고 그날의 자리를 그대로 만들어 ㉠ 실제로 새는 것을 보이고 ㉡ `synthetic_run` 이 그것을 막는 것을 보인다. 그리고 **다음에 또 다른 경로로 새지 않게** `scripts/` 전수 검사를 둔다 |

## 5-1. ⚠ 가드가 서기 **직전에 한 번 더 덮였다** [실측 2026-09-06 13:49:34 UTC]

차선 E 가 11:06:45 판을 잡아 알렸고, 차선 Q 가 가드를 세우는 사이 **같은 판정기가
한 번 더 돌아** 13:49:34 판으로 덮였다(옆 차선의 게이트 실행). 그 뒤 같은 판정기를
돌리면 이제 이렇게 적힌다 [실측]:

```
INFO [OPS] 증거를 안 남겼다 — **지어낸 상태**에서 난 수는 증거가 아니다
  (ops_tasks._write_evidence) — /docs/agent/evidence/D-373/backup_last.json.
  지금 열려 있는 것: verify_retention_declared — OPS_BACKUP_DIR 을 비워 놓고 물어본다
```

**한 번 더 덮인 것이 이 절의 값이다.** 「잡았다」와 「막았다」 사이에도 시간이 흐르고,
그 사이에 같은 일이 또 난다 — 그래서 알리는 것으로는 부족하고 **막아야** 한다.

## 6. 이 파일을 어떻게 읽을 것인가

- **지우지 않았다.** 지우면 「이런 일이 있었다」가 함께 사라진다.
- 이 파일에는 `_written_from` 칸이 **없다** — 그 칸이 없는 D-373 파일은 전부
  **턴 I 이전**의 것이고, 어느 DB·어느 상태에서 났는지 되짚을 수 없다.
- 진짜 값은 **가드가 선 뒤 한 바퀴를 돌려** 다시 받아야 한다(OPS-19 · 재기동 창).
  그때까지 `backup_last.json` 의 `SKIPPED_UNDECLARED` 는 **회색이지 사실이 아니다.**
