# P-9 시드 — 그리고 **기존 씨앗이 모형이었다** (D-401)

**실행 2026-09-16** · 도구 `backend/stream_monitors/management/commands/seed_dsm_events.py`

---

## 1. 「실제」의 정의로 재니 기존 씨앗이 걸렸다 [실측]

지시서 P-9 [인용]:

> 실제 이벤트 = K1 이벤트 생성 경로를 통과해 DB 에 행이 생긴 이벤트.
> **DB 에 직접 INSERT 하거나 화면 코드에 고정값을 넣으면 모형이다 — 금지.**

그 정의로 저장소를 재니 [실측]: `scripts/capture_screens.py::seed_events` 가
**`DetectionEvent._base_manager.create(...)`** 로 행을 직접 만들고 있었다.
**화면 16장은 그 모형 위에서 찍혔다.**

## 2. 직접 INSERT 가 무엇을 숨겼나 — 우리 경우에 구체적으로

```
· event_type 이 `gxprobe-D384-screen` 이었다. **열거값이 아니다.**
  K1 의 `_validate` 를 안 지나므로 아무 문자열이나 들어가고,
  화면과 통계는 그 값을 「유형」으로 읽는다
· 중복 억제(F-04 · 10초)·주소 조회(FX-5)·클립 참조가 **한 번도 안 돈다**
· 즉 **모형 데이터는 파이프라인을 건너뛴 만큼 결함을 숨긴다**
```

★ 이것이 D-386(화면을 띄우는 것이 가장 강한 시험)을 **정확히 그만큼 약하게 만든다.**
  브라우저는 라우트를 때리지만, 그 라우트가 읽는 행이 파이프라인을 안 지났으면
  파이프라인의 결함은 화면에 나타날 수 없다.

## 3. 고친 것

```
새 도구  seed_dsm_events  — `record_detection` 만 부른다. 상태를 옮길 때도
                            `advance_response`·`review_event` 를 부른다 (칸 직접 쓰기 없음)
고침     capture_screens.seed_events — 직접 INSERT → `record_detection`
고침     clean_events — 유형(`event_type`)으로 고르던 것을 **씨앗 카메라**로 바꿨다.
         유형이 열거값이 되면서 옛 기준으로는 못 고른다 — 그대로 뒀으면 씨앗이
         **안 지워진 채 남아** 다음 실행의 화면에 섞였을 것이다
```

## 4. 심은 것 [실측 2026-09-16]

```
심은 이벤트 20건 (record_detection 호출 20회) · 판정 12건 · 대응 전이 36회
대응 진행: occurred 4 · acknowledged 4 · in_progress 4 · closed 8
탐지 판정: new 8 · confirmed 8 · rejected 4
유형:      fire 5 · flood 5 · intrusion 5 · person 5
카메라:    GX-SEED-DSM · install_address 있음(FX-5) · 소속 4
```

★ **두 축을 모두 채운 이유**: 한 축만 채우면 화면에서 **두 축이 있다는 사실 자체가
  안 보인다.** 「종결」이 대응 종결인지 판정 종료인지 구분되지 않는 채로 검수에 나간다.

★ 스냅샷·구간 재생은 **비어 있다** — 이 환경에 MinIO 가 없다. 지시서대로 **비어 있는
  채로 찍었다**(「없다」로). 있는 척하지 않는다.

## 5. 실측이 도구를 한 번 고쳤다 (D-350)

1차판이 `DataError: value too long for character varying(16)` 로 죽었다.
`address_source` 에 주소 문자열을 넣었기 때문이다 — 그 칸은 **자유 문자열이 아니라
열거값**(`unset`/`manual` · D-330)이고, 설치 주소는 `install_address` 다.
**이름이 비슷한 칸 둘을 섞은 것** — 동음이의의 작은 판이다(D-337).

## 6. 데이터 출처를 화면마다 적는다 (P-9)

`verify_screens.py` 의 필수 메타를 **4칸 → 5칸**으로 늘렸다: `data_source`.
비어 있으면 게이트가 멈춘다. 늘리자마자 **기존 16장이 전부 빨개졌고**(출처 미표기),
실제 경로 씨앗으로 다시 찍어 채웠다 [실측: 16장 · 브라우저 오류 0건 · verify_screens exit 0].

★ 시드로 찍은 화면은 **실제 화면이지만 실제 사고는 아니다.** 그 둘이 구분되지 않으면
  검수 자리에서 시드 화면이 현장 화면으로 읽힌다 — **착시가 아니라 거짓말이다**(D-284).

## 7. 검증

```
단위        553 passed · 1 skipped · exit 0
화면        16/16 · 브라우저 오류 0건 · verify_screens exit 0 (출처 5칸 포함)
시드        20건 [실측] · 전부 K1 공개 면 통과
게이트      아래 D-400 규약대로 — 쟀고 통과 4 · **판정 불가 5**
§0.4 수정   0줄
```
