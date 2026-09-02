# 이벤트 상태 4값 — **이미 4값이었고, 축이 달랐다** (D-399)

**실행 2026-09-14** · 지시서 세종 2026-09-14 「D-394 이벤트 상태 4값」 이행
**번호 대응** 지시서 제안 D-394 → 저장소 정본 **D-399** (D-380)

---

## 1. 착수 전 실측 — 지시서의 전제가 틀렸다 (D-379 의무)

지시서는 「현재 이벤트는 사실상 **2값**(발생/처리)이다 [실측: 2026-09-13 보고 인용]」
이라 적었다. **저장소를 열어 보니 이미 4값이다** [실측 · `stream_monitors/models.py:186`]:

```python
class Status(models.TextChoices):
    NEW = "new" · CONFIRMED = "confirmed" · REJECTED = "rejected" · CLOSED = "closed"
```

| 지시서 항목 | 실측 |
|---|---|
| 상태 「2값」 | **틀림 — 이미 4값** |
| 대응 진행 축 | **없음** |
| 이벤트 감사 테이블 | **이미 있음** — `common/audit_writer.py` + `logger.AuditLogs` |
| 오탐 모델(지시서 D-396) | **이미 있음** — `verdict`/`reviewed_by`/`reviewed_at`/`reject_reason` |

---

## 2. ★ 두 4값은 **다른 것을 묻는다**

```
status          「이 탐지가 진짜인가」   신규 → 확인/기각 → 종료
response_state  「사람이 어디까지 했나」 발생 → 접수 확인 → 조치중 → 종결
```

지시서의 값(occurred/acknowledged/in_progress/closed)을 `status` 에 밀어 넣으면
**판정과 대응이 한 칸에 섞인다.** 그것은 D-293 이 `status` 와 `verdict` 를 가른 것과
**같은 실수**다 — 섞여 있던 동안 종료가 쌓일수록 오탐률이 **저절로 좋아졌다.**
개선이 아니라 나쁜 데이터가 사라진 것이었다.

**한 칸에 두 뜻을 넣으면 마지막에 쓴 사람이 앞사람의 뜻을 덮는다.**

→ **세 번째 칸 `response_state` 를 신설했다** (ⓐ안). 계약 문서
`docs/contracts/detection-event.md` 를 건드리지 않고, 마이그레이션이 **가산적**이다.
⚠ 축 선택은 세종의 판정 자리였고 **답을 받지 못한 채 진행했다** — 되돌리려면
`0025` 를 되감고 칸 하나를 지우면 된다. `status` 는 처음부터 건드리지 않았다.

---

## 3. 무엇을 만들었나

```
backend/stream_monitors/models.py            ResponseState 4값 + response_state 칸
backend/kernels/k1_event/response_flow.py    전이 규칙 · 되돌림 권한 · 감사 (한 자리)
backend/kernels/k1_event/exceptions.py       거절 셋 (커널은 HTTP 를 모른다)
backend/apps/dsm/services.py                 유일한 K1 소비자 — 예외를 재수출
backend/apps/dsm/api.py                      POST /api/dsm/events/{id}/response
migrations/0024 · 0025                       칸 추가(가산) + 기존 행 이관
```

**전이 규칙:** 앞으로만 간다. `occurred → closed` 직행 없음 —
**접수한 사람이 없는 종결**이 생기면 「아무도 안 봤는데 닫힌 이벤트」와
「보고 닫은 이벤트」가 같아진다(D-290).
**되돌림은 「종결 → 조치중」 하나뿐**이고, 관제팀장(K3 MANAGER 이상)만, **사유 필수**.
넓게 열면 감사 이력이 이야기를 잃는다 — 오간 흔적만 남고 「지금 어디까지」를 말할 수 없다.

**감사는 새 표를 만들지 않았다**(D-333). `logger.AuditLogs` 에 `common/audit_writer.py`
로 남긴다 — who·when·from·to·reason 이 전부 거기 있고, 칸에는 **현재 값만** 있다.

---

## 4. ★★ 시험 넷이 설계를 고쳤다 — 넷 다 시험이 옳았다

1차판은 규칙을 `apps/dsm/response_flow.py` 에 두었다. 전 시험을 돌리자 **넷이 빨개졌다:**

```
AppStaysThinTest                        App 이 `_base_manager` 를 만졌다
KernelPublicSurfaceTest(migration)      새 칸이 DB 에 안 들어갔다
EntrySurfaceIsLockedTest ×2             라우트가 하나 늘었는데 진입면 핀은 그대로다
```

고친 뒤 다시 넷:

```
TenantIsolationWriteTest                새 **쓰기 면**이 격리 탐침 대장에 없다
EntrySurfaceIsOneTest ×3                라우트 모듈이 K1 을 직접 import 했다 ·
                                        K1 소비자가 등재 없이 늘었다
```

★ 전부 **설계 지적**이지 잔소리가 아니었다:
  · `DetectionEvent` 의 수명주기는 K1 의 것이다 — `review_event`·`close_event` 가
    이미 거기 산다. App 에 두면 **같은 표의 규칙이 두 층에 나뉜다**
  · 새 쓰기 면은 **남의 이벤트를 접수 확인으로 밀 수 있는지**를 재야 한다.
    심어진 행보다 나쁘다 — 그 이벤트는 원래 그 테넌트의 것이라 **어떤 읽기 시험도
    이상하다고 하지 않는다.** 탐침을 등재했다
  · K1 의 App 소비자는 **하나뿐**이어야 한다. 그것이 F-05 「진입면 하나」의 집행이다

같은 커밋에서 함께 고친 것(문서·코드가 갈리지 않게): `DA-04 §2 K1 표` ·
`kernels/k1_event/__init__.__all__` · `KernelPublicSurfaceTest.SURFACE` ·
`EVENT_ENTRY_SURFACE` · `K1_CONSUMERS` · `WRITE_PROBES`.

---

## 5. 거절은 **실제 4xx** 다 (지시서가 못박은 자리)

```
409  그 전이 자체가 없다 — 다시 보내도 같다
400  되돌림인데 사유가 비었다 — 채워 다시 보내면 된다
403  되돌림인데 관제팀장이 아니다
404  남의 테넌트 이벤트 (403 이 아니다 — 존재 여부가 새는 것도 누출이다)
```

★ 셋을 **한 코드로 묶지 않은 이유**: 부르는 쪽이 할 일이 다르다. 400 만 내면
화면이 「무엇을 고쳐 다시 보낼지」를 모른다(D-290). `200 + {"success": false}` 는
만들지 않았다 — 이 App 이 처음부터 금지한 모양이고 착시 ⑧의 자리다.

---

## 6. 이관 [실측]

개발 DB 의 `DetectionEvent` 는 **0행**이다 [실측 2026-09-14].
그래서 마이그레이션을 돌려도 「0행 이관」이 나오고 — **0건은 검증이 아니다**(D-301).
대신 네 상태를 심어 놓고 **이관 함수를 직접 돌려** 표대로 옮기는지 봤다
(`BackfillMappingTest`). 매핑은 **[판정]이다 — 인용이 아니라 우리가 정했다**:

```
new       → occurred       아직 아무도 안 봤다
confirmed → acknowledged   사람이 「진짜다」라고 판정했다 = 접수한 것이다.
                           in_progress 로 올리지 않는다 — 판정은 「봤다」이지 「조치했다」가
                           아니고, **안 한 일을 했다고 적지 않는다**
rejected  → closed         오탐이므로 대응은 끝났다
closed    → closed         이미 끝났다
```

★ 기본값(`occurred`)만으로 부족한 이유: 그대로 두면 **이미 판정하고 종료한 이벤트도
「아무도 안 봤다」로 보인다.** 그 상태에서 화면을 열면 당직자가 끝난 일을 다시 접수한다.

---

## 7. 검증 [실측 2026-09-14]

```
단위          553 passed · 1 skipped · exit 0   (직전 542 · 새 시험 11)
E2E           23 passed · exit 0
게이트 9종     전부 exit 0
마이그레이션    verify_migrations — 모델 = 그래프 = DB 정합 (①0건 ②0건)
파괴적 연산    **0건** — dry-run 결과가 AddField 하나뿐이었다 (D-209)
§0.4 수정     0줄
```

## 8. 안 한 것과 그 사유

· **지시서 D-396(오탐)** — 데이터 모델이 **이미 있다**(`verdict` 계열 · D-293).
  지시대로 `false_positive: bool` 을 새로 만들면 **오탐 뜻이 두 칸에 섞이고**,
  그것은 D-293 이 명시적으로 금지한 실수다. 세종의 판정을 기다린다.
· **지시서 D-395(모바일 3장)·D-397·D-398(HWPX)** — 이번 턴 범위 밖이다.
