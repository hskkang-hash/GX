# 턴 W · 차선 S (LAW-08 / P-191 감사 체인 경합)

## 닫음
- **빨강을 먼저 봤다** — 경합 재현 시험을 새로 쓰고 **잠금 넣기 전에** 실패를 확인
  (`backend/tests/test_law08_chain_race.py` · 6 손 × 6 라운드 · 실제 postgres):
  `2 failed` ·
  `여러 행이 **같은 앞 해시**를 읽었다: 000000000000…→[37,38,42] · 9db672c1535f…→[39,40,41] · 5603e0493d2f…→[43,44,45] …`
  → 운영 DB 에서 본 얼굴(#260977·978·979 가 같은 prev)과 **같은 모양**.
- **그 뒤 초록** — `tests/test_law08_chain_race.py tests/test_s_evidence_chain.py` → **32 passed**
  (새 시험 10 + 기존 22). 경합 시험만 따로 3회 연속 초록으로 재현.
- **잠금이 운영 postgres 에서 실제로 선다** (아무것도 안 쓰고 롤백한 실측):
  `LOCKWAIT [('A', 0.001), ('B', 1.301)]` — A 가 1.5초 쥐는 동안 B 가 1.3초 기다렸다.
  `OUTSIDE_ATOMIC raised OK` — 트랜잭션 밖에서는 **선다**(조용한 무잠금 금지).
- **새 코드가 운영에서 돌고 있다** — `docker restart gx-gunicorn-e` (08:31Z) 뒤 태어난 행에
  자리표가 붙어 있다: `row 265517 … seq 265517`.
- **끊김 22건을 64자 두 개와 함께 등재**(`RECORDED_BREAKS`). **과거 행은 한 줄도 안 고쳤다.**
- 게이트: `--db` → **어긋남 0건 · exit 0** (등재 전 22건) · `--self-test` → **17건 통과**.
- 관련 시험 **220건 초록** (`test_s_evidence_chain` · `test_role_gate` · `test_tenant_isolation` ·
  `test_u24_reports` · `test_evidence_guard` · `test_dsm_app` · `test_k5_credential_store` ·
  `test_be_purge` · `test_l_retention`) — `evidence_chain` 을 부르는 자리를 전부 덮는다.

## 손 위
- 없음. `backend/common/evidence_chain.py` · `backend/tests/test_law08_chain_race.py` 둘 다 마무리.

## 안 한 것
- **전체 단위 시험(`pytest tests --ignore=tests/e2e`)은 끝까지 못 봤다.** 같은 시험 DB
  (`test_gx_s`)에 내가 겹쳐 돌린 탓에 결과를 못 믿게 됐고, 그래서 **중단시켰다**.
  회색이지 초록이 아니다. 위 220건은 겹침 없이 단독으로 돈 결과다.
- **게이트가 「기록된 끊김 22건」을 안 인쇄한다** — `scripts/verify_evidence_chain.py` 의
  `_DB_SNIPPET` 이 `r.breaks` 만 싣는다. `r.recorded` 한 줄을 더해야 그 초록이 정직하다.
  그 파일은 내 파일이 아니라 못 고쳤다. **조율자 요청 ①**
- **`common/audit_writer.write()` 의 `create` 를 잠금 구간 안으로.** 지금은 INSERT 가
  잠금 밖이라 번호와 붙은 순서가 뒤집힐 수 있고, 그 뒤집힘은 자리표가 받아 낸다.
  잠금이 INSERT 앞으로 가면 자리표는 예비가 된다. 내 파일이 아니다. **조율자 요청 ②**
- **판정문은 「끊김 4건」인데 실측은 22건**이었다(전부 같은 원인·전부 잠금 이전).
  판정문의 수를 넘겨 등재했으므로 **확인이 필요하다**. **조율자 요청 ③**
- 새 쓰기 면(모델·마이그레이션·엔드포인트)은 **만들지 않았다** → WS-28 해당 없음.
