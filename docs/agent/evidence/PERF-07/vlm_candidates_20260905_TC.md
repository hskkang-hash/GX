# PERF-07 — VLM 모델 후보 **2종 실측 표** (라이선스 · 오프라인 · 한국어)

[2026-09-05 · 턴 TC · 차선 Q] 정본 `docs/agent/evidence/D-346/ga_readiness.yaml :: PERF-07`

> **대표 결정 ④(VLM 도입 · GPU 1장) 전에는 착수하지 않는다.**
> 이번에 내는 것은 **모델 후보 2종 실측 표(라이선스·오프라인 가능 여부·한국어)뿐**이다.

**모델을 받지 않았고 돌리지 않았다.** 그러므로 이 문서에 **속도·VRAM·정확도는 없다.**
PERF-07 의 본 목표(사유 시간 p95 ≤ 2초 · GPU 1장)는 **여전히 미측정**이며, 이 표는
그 측정을 시작해도 되는지를 **라이선스·배포 형태·언어**로 먼저 가르는 자리다.

---

## 0. 무엇을 어디서 봤는가 — **문서와 호출을 갈라 적는다** (D-316)

| 표시 | 뜻 |
|---|---|
| `[호출]` | 이 턴에 **HTTP 로 직접 받아** 읽은 값 (Hugging Face 모델 메타데이터 API · 2026-09-05) |
| `[문서]` | 공개 모델 카드·블로그·라이선스 **문서에 적힌 문장** |
| `[미확인]` | 이 턴에 **확인하지 못했다.** 「없다」가 아니라 **「못 봤다」**다 (D-301) |
| `[미측정]` | 재려면 모델을 받아 돌려야 한다 — **이번 몫이 아니다** |

⚠ 이 표의 거의 전부가 `[문서]`·`[호출]`이다. **한 건도 우리 GPU 에서 돌려 본 것이 아니다.**
그 사실을 숨기면 다음 사람이 이 표를 성능 근거로 읽는다.

---

## 1. 후보 2종

### 후보 A — **Qwen2.5-VL-7B-Instruct** (Alibaba Qwen)

| 항목 | 값 | 근거 |
|---|---|---|
| 라이선스 | **apache-2.0** | `[호출]` `GET huggingface.co/api/models/Qwen/Qwen2.5-VL-7B-Instruct` → `"license": "apache-2.0"` |
| 상업 이용·재배포 | 허용 (Apache-2.0) · **사용자 수 제한 조항 없음** | `[문서]` Apache-2.0 원문 |
| 오프라인(폐쇄망) | **가능** — 가중치를 내려받아 `transformers` 로 로컬 추론. 외부 API 호출 없음 | `[문서]` 모델 카드 Quickstart(`transformers` + `qwen-vl-utils`) |
| 한국어 | **직접 표기 없음.** 카드의 `language` 는 `["en"]` 하나뿐 | `[호출]` 같은 메타데이터 |
| 한국어 (앞 세대) | 앞 세대 Qwen2-VL 카드에는 명시돼 있다: *"besides English and Chinese, Qwen2-VL now supports the understanding of texts in different languages inside images, including most European languages, Japanese, **Korean**, Arabic, Vietnamese, etc."* | `[문서]` Qwen2-VL-7B-Instruct 모델 카드 |
| 한국어 (2.5 세대) | 블로그는 *"multi-scenario, multi-language and multi-orientation text recognition"* 이라고만 하고 **한국어를 이름으로 부르지 않는다** | `[문서]` qwenlm.github.io/blog/qwen2.5-vl/ |
| 우리 화면의 한국어 성능 | **`[미측정]`** — 한국어 프롬프트·한국어 출력 품질은 재 본 적 없다 | — |

### 후보 B — **InternVL2_5-8B** (OpenGVLab / Shanghai AI Lab)

| 항목 | 값 | 근거 |
|---|---|---|
| 라이선스 | **mit** | `[호출]` `GET huggingface.co/api/models/OpenGVLab/InternVL2_5-8B` → `"license": "mit"` |
| 구성요소 라이선스 | *"This project is released under the MIT License. This project uses the pre-trained internlm2_5-7b-chat as a component, which is licensed under the Apache License 2.0."* | `[문서]` 모델 카드 |
| 오프라인(폐쇄망) | **가능** — `transformers` 예제 + `LMDeploy` 로 로컬 서빙 | `[문서]` 모델 카드 배포 절 |
| 한국어 | **직접 표기 없음.** 언어 태그는 `multilingual` 한 낱말이고, 평가표의 다국어 절에도 **한국어가 이름으로 없다** | `[호출]`·`[문서]` |
| 우리 화면의 한국어 성능 | **`[미측정]`** | — |

---

## 2. 이 표가 말하는 것 — **한 줄로**

- **라이선스는 둘 다 문제 없다.** Apache-2.0 과 MIT 는 폐쇄망 설치·상업 납품·재배포에
  추가 협의가 필요 없다. 이것이 이 두 개를 고른 **첫 번째** 이유다.
- **오프라인도 둘 다 된다.** 지자체 관제망은 외부로 못 나간다 — 클라우드 API 형
  모델은 이 자리에서 후보가 아니다.
- **한국어는 둘 다 「확인되지 않았다」.** 한쪽은 앞 세대 문서에만 이름이 있고, 다른
  한쪽은 `multilingual` 이라는 낱말뿐이다. **「한국어를 지원한다」고 적으면 그것은
  실측이 아니라 희망이다** — 재려면 우리 화면의 한국어 이미지로 돌려 봐야 한다.

### 왜 이 둘인가 — **떨어진 후보와 그 사유** (안 한 것과 못 한 것을 가른다)

| 후보 | 사유 |
|---|---|
| Llama-3.2-11B-Vision-Instruct | 라이선스가 커뮤니티 라이선스다. `[문서]` *"If, on the Llama 3.2 version release date, the monthly active users … is greater than 700 million … you must request a license from Meta."* 우리 규모에는 걸리지 않지만 **조건부 허가**라 납품 계약서에 조항이 따라붙는다. 멀티모달 모델의 **EU 관련 추가 지역 제한**이 있다고 알려져 있으나 **이 턴에 원문에서 확인하지 못했다 `[미확인]`** — 도입을 검토한다면 그 조항부터 원문으로 확인할 것. |
| 클라우드 API 형(GPT-4o·Gemini 등) | **폐쇄망에서 안 돈다.** 재난 영상은 밖으로 내보내지 않는다. 라이선스 이전에 배포 형태에서 걸린다. |

---

## 3. 도입해도 **바뀌지 않는 것** — 정본이 못 박은 제약

이 표를 읽고 다음 사람이 착각할 자리가 셋 있다. 정본(`ga_readiness.yaml :: PERF-07`)
그대로 옮겨 둔다.

1. **VLM 은 판정을 쓰지 않는다.** `verdict` · `status` · `severity` **어느 칸에도**
   VLM 의 출력이 들어가지 않는다. 사람이 판정하고, VLM 은 **사유(문장)만** 만든다.
   모델이 좋아져도 이 선은 안 움직인다 — 움직이면 그날부터 오탐의 책임자가 사라진다.
2. **예산을 못 지키면 「사유 없음」으로 간다.** 사유 생성이 늦으면 사유를 **버리고**
   알림을 보낸다. **알림은 사유를 기다리지 않는다** — F-10 의 30초가 먼저다.
   (즉 VLM 장애는 알림 장애가 되지 않아야 하고, 그 배선이 도입의 전제다.)
3. **착수 자체가 대표 결정 ④ 뒤다.** GPU 1장을 사는 결정이 없으면 p95 2초는
   잴 대상이 없다. 이 표는 그 결정을 위한 입력이지, 착수의 신호가 아니다.

## 4. 다음에 재야 하는 것 (결정 ④ 이후)

    · 한국어 실물 대조 — 우리 이벤트 스냅샷 N장 · 한국어 프롬프트 · 사람이 읽는 문장인가
    · 사유 시간 p95 — GPU 1장 · 동시 1/2/4 · **F-10 30초 안에 드는가가 아니라
      「사유가 늦어도 알림이 제 시간에 갔는가」**를 함께 잰다 (둘은 다른 수다)
    · VRAM · 동시 처리 수 · 모델 로딩 시간(재기동 뒤 첫 사유까지)
    · 실패 경로 — 모델이 죽었을 때 알림이 그대로 나가는가(저하 운전)

**출처**
- [Qwen/Qwen2.5-VL-7B-Instruct (Hugging Face)](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)
- [Qwen/Qwen2-VL-7B-Instruct (Hugging Face · 앞 세대 한국어 문장)](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct)
- [Qwen2.5-VL 블로그](https://qwenlm.github.io/blog/qwen2.5-vl/)
- [OpenGVLab/InternVL2_5-8B (Hugging Face)](https://huggingface.co/OpenGVLab/InternVL2_5-8B)
- [Llama 3.2 커뮤니티 라이선스](https://developer.meta.com/ai/llama3_2/license/)
