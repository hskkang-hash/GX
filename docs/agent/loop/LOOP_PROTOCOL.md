# GuardianX 자동 루프 v1.0 — 영실 보고 → 세종 검토·지시 → 영실 착수 (2026-09-24 · 세종)

| 항목 | 내용 |
|---|---|
| 문서번호 | GAION-GX-LOOP-2026-001 [추정] |
| 목적 | **지금의 방식(문서·번호·규약·역할)을 그대로 두고** 손으로 하던 세 걸음 — ① 영실 보고서 제출 ② 세종 검토·작업지시서 ③ 영실 지시서 분석·착수 — 를 사람이 붙이지 않아도 이어지게 한다 |
| 바뀌지 않는 것 | 파일 자리(`docs/workorders/WO-*.md` · `_report.md` · `docs/agent/RESUME_NEXT.md` · `작업지시서/*.pdf`) · P-번호·D-번호·세종 오류 누계 · 불변 전부 · **삭제·되돌리기·운영계 외부 행위·`.env` 실제 값·push 는 대표** |
| 바뀌는 것 | 손 대신 **상태 파일 하나**(`docs/agent/loop/LOOP_STATE.json`)가 차례를 넘긴다 · 세종은 예약 작업으로 매시 상태를 보고 · 영실은 PC 의 감시기(PowerShell)가 상태를 보고 Claude Code 를 헤드리스로 띄운다 |

## §1 한 그림
```
 [영실 · Claude Code · 대표 PC]                      [세종 · Cowork 예약 작업 · 매시 08~22 KST]
   지시서 읽고 개발(차선·V·보고)                          LOOP_STATE 읽음
   보고서 WO-…_report.md 저장                             phase == report_ready ?
   LOOP_STATE.phase = report_ready  ───────────────▶       보고서·직전 WO·PRD 읽음 → 판정 → WO-다음.md
                                                           RESUME_NEXT.md · PDF(작업지시서/) 저장
   감시기(yeongsil_watch.ps1 · 5분마다)                    LOOP_STATE.phase = wo_ready ◀──
   phase == wo_ready → claude -p 「RESUME_NEXT 읽고 시작」   대표 폰에 알림(완료율 · 대표 결정)
   phase = code_running …                                  phase 가 waiting_ceo 면 알림만
   대표 결정이 필요하면 → phase = waiting_ceo (멈춤)
   대표가 CEO_INBOX.md 에 한 줄 → 감시기가 이어 띄움
```

## §2 상태 파일 — `docs/agent/loop/LOOP_STATE.json` (차례를 넘기는 유일한 자리)
```json
{ "turn": "AH", "phase": "code_running",
  "wo": "docs/workorders/WO-GX-20260925-11_턴AH_….md",
  "report": null,
  "next_turn": "AI",
  "updated_at": "2026-09-24T15:40:00+09:00", "updated_by": "sejong",
  "ceo_question": null, "pause": false, "notes": "" }
```
| phase | 뜻 | 누가 여기로 바꾸나 | 다음 |
|---|---|---|---|
| `wo_ready` | 지시서가 나왔다 · 영실이 읽을 차례 | 세종 | 감시기 → `code_running` |
| `code_running` | 영실이 개발 중 | 감시기(착수 시) | 영실 → `report_ready` / `waiting_ceo` |
| `report_ready` | 보고서가 나왔다 · 세종이 읽을 차례 | 영실(보고서 저장 직후) | 세종 → `wo_ready` |
| `waiting_ceo` | 대표 결정 없이는 못 간다(삭제·되돌리기·운영계·값·push) | 영실 또는 세종 | 대표 → `CEO_INBOX.md` 한 줄 → 감시기 → `code_running` |
| `rate_limited` | Claude 한도(429) · `retry_after` 시각까지 쉼 | 감시기 | 시각 뒤 감시기 → `code_running` |
| `paused` | 대표가 멈춤(`pause: true`) | 대표 | 대표가 `false` |

규칙: **한 번에 한 주체만 쓴다** · 바꿀 때 `updated_at`·`updated_by` 를 같이 · 상태 파일이 12시간 넘게 안 움직이면 세종 예약 작업이 「멈춤 의심」 알림 1회.

## §3 영실 쪽 — 감시기와 헤드리스 규약
- **감시기** `scripts/loop/yeongsil_watch.ps1`: 5분마다 상태를 읽는다 · `wo_ready` → `claude -p`(헤드리스) 착수 · 08:00~22:00 KST 만(밖이면 기다림) · 하루 최대 3턴 · 출력 로그 `docs/agent/loop/logs/<턴>_<시각>.log` · 「rate limit」·「429」가 보이면 `rate_limited`.
- **헤드리스 권한** `scripts/loop/headless.settings.json`(`--settings` 로만 붙인다 · 대화형 세션엔 영향 0): 허용 = 읽기·편집·python·pytest·node·npm·docker ps/inspect/logs/exec(읽기) · git add/commit/tag/status/log/diff. **거부 = `git push` · `git reset --hard` · `git checkout --` · `git revert` · `--no-verify` · `docker rm` · `docker volume rm` · `docker run` · `docker compose up/down` · `rm -rf` · `dropdb` · `DROP` · `.env*` 쓰기 · 운영 주소 호출.** 거부에 걸리면 영실은 그 자리에서 멈추지 않고 **보고서 §대표 손에 적고 `waiting_ceo`** 로 넘긴다 — 지금의 규약 그대로다.
- **첫 프롬프트**는 `scripts/loop/yeongsil_prompt.txt`(고정) — 「`docs/agent/RESUME_NEXT.md` 와 정본 WO 를 읽고 시작 · 끝나면 `WO-…_report.md` 저장 → LOOP_STATE `report_ready`」.
- **창(재생성)·`-old` 삭제·시험 DB 처분 같은 대표 결정 집행은 헤드리스로 하지 않는다** — 대표가 있는 대화형 세션에서만(지금과 같다). 지시서에 그런 창이 있으면 영실은 그 시각에 `waiting_ceo` 로 넘기고 대표 한 마디를 기다린다.
- **push 는 대표 손**(P-298·P-306). 감시기가 매 사이클 `origin/turn-q..turn-q` 커밋 수를 로그 첫 줄에 적고, 3 이상이면 세종 알림에 실린다.

## §4 세종 쪽 — 예약 작업 규약
- **예약 작업** 「GuardianX 세종 루프」: 매시 정각 08~22 KST · **이 컴퓨터 필요**(저장소 폴더 `C:\GuardianX\guardianx-source` 읽고 쓴다) · 알림 = 폰 푸시 + 메일.
- 매 실행: `LOOP_STATE.json` 읽음 → `report_ready` 가 아니면 **아무것도 쓰지 않고** 끝(12시간 정지 의심 · `waiting_ceo` 6시간 경과 · push 대기 ≥ 3 만 알림) → `report_ready` 면 `docs/agent/loop/sejong/SEJONG_METHOD.md` 절차대로 보고서 검토 → 판정 → WO 다음 번호 · `RESUME_NEXT.md`(+ 날짜 사본) · PDF(`작업지시서/`) → `wo_ready` → 알림(완료율 한 줄 · 대표 결정 N건 · 결정 문장 그대로).
- 세종이 결정을 대표께 올릴 때는 **`CEO_INBOX.md` 에 답할 문장을 미리 적어 둔다**(대표는 그 줄 앞의 `[ ]` 를 `[x]` 로 바꾸거나 다른 말을 적는다).
- 두 세종 세션이 같은 저장소에 쓰지 않는다 — **지시서 발행은 이 예약 작업 하나**가 한다(대표가 대화로 세종을 부르면 그 세션은 판정·문서만 내고 `LOOP_STATE` 는 건드리지 않는다).

## §5 대표 쪽 — 세 자리만
| 자리 | 무엇 |
|---|---|
| `docs/agent/loop/CEO_INBOX.md` | 세종·영실이 올린 질문에 **한 줄** 답한다(`[x]` 또는 문장). 삭제·되돌리기·창 일시·push 완료 보고가 여기로 온다 |
| 폰 알림 | 턴이 끝날 때마다 완료율 한 줄 + 대표 결정 N건 · `waiting_ceo` 6시간 · 정지 의심 |
| `LOOP_STATE.json` 의 `pause` | `true` 로 바꾸면 둘 다 멈춘다(메모장으로 열어 한 글자) |
대표가 **하지 않게 되는 것**: 보고서 스크린샷 붙이기 · 「지시서 써라」 · 「RESUME_NEXT 읽고 시작」. **여전히 하는 것**: push · 삭제·되돌리기 결정 · 창 한 마디 · 값(금고).

## §6 지키는 선(자동이어도 바뀌지 않는다)
① 세종은 [실측]이 없다 — 판정·인용·추정만(P-0) ② 수는 영실이 낸다(D-380) ③ 게이트를 초록으로 고치지 않는다 · `--no-verify` 0(D-327) ④ 값은 저장소·보고·알림에 0(D-204) ⑤ 운영 서버(115.21.49.115)는 헤드리스에서 부르지 않는다(P-90 승인 뒤 · 대화형만) ⑥ 대장은 줄지 않는다 ⑦ 삭제·되돌리기·운영계·`.env` 실제 값·push 는 대표 ⑧ 한 번에 한 턴 · 한도 09-26 10:00 뒤 8차선 · 하루 3턴 상한 ⑨ 자동으로 낸 지시서에도 세종 오류 누계는 이어진다 — 대표가 대화에서 잡으면 그 자리에서 +1.

## §7 처음 켜는 순서(대표 · 한 번)
1. `claude --version` 이 PowerShell 에서 답하는지(Claude Code 설치 확인 · 안 되면 `npm i -g @anthropic-ai/claude-code`).
2. 관리자 PowerShell 한 줄(로그온 시 감시기 자동 시작):
   `schtasks /Create /TN "GuardianX-Yeongsil" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\GuardianX\guardianx-source\scripts\loop\yeongsil_watch.ps1" /SC ONLOGON /RL HIGHEST /F` → 바로 시작: `schtasks /Run /TN "GuardianX-Yeongsil"`.
3. Claude 앱 → 예약 작업 「GuardianX 세종 루프」 → **「자동으로 승인」 켬** · 「이 컴퓨터 필요」 켜져 있는지 확인(세종이 등록해 두었다).
4. `docs/agent/loop/LOOP_STATE.json` 을 열어 `pause` 가 `false` 인지 · `phase` 가 지금 상태(턴 AH 진행 중이면 `code_running`)인지 본다.
5. 첫 사이클은 지켜본다 — 영실이 AH 보고서를 내고 `report_ready` 로 바꾸면 다음 정각에 세종이 턴 AI 를 다시 읽어 갱신하거나(이미 있으면 그대로 두고 `wo_ready`) 감시기가 착수한다.

## §8 멈추는 법 · 되돌리는 법
- 멈춤: `LOOP_STATE.json` 의 `"pause": true` 또는 Claude 앱에서 예약 작업 끔 + `schtasks /End /TN "GuardianX-Yeongsil"`.
- 완전히 되돌림: `schtasks /Delete /TN "GuardianX-Yeongsil" /F` + 예약 작업 삭제. 파일은 그대로 남고, 손으로 하던 방식이 그대로 이어진다(이 루프는 파일 자리를 바꾸지 않았다).
