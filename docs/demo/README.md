# 데모 자료 (배포 대상 아님)

W0-4 로 저장소 루트에서 이곳으로 옮긴 데모 파일을 보관한다.
**여기 있는 파일은 어떤 배포 산출물에도 포함되지 않는다.**

| 파일 | 원래 위치 | 성격 |
|---|---|---|
| `drone-monitoring.html` | 저장소 루트 | 단독 실행 데모 페이지(34KB). CDN chart.js + 하드코딩 값. 프런트엔드 빌드·nginx 서빙 경로 어디에도 연결되어 있지 않았다 |

> 이 파일은 백엔드의 `/api/delivery/drone-monitoring/*` 엔드포인트와 **무관하다.**
> 이름만 같고 참조 관계가 없다(W0-4 REVIEW 확인).

## 왜 옮겼나

GS 인증은 **미완성 기능이 UI 에 노출되는 것을 결함으로 처리**한다.
저장소 루트의 데모 HTML 은 배포 이미지에 실릴 위험이 있고, 그 자체로 심사 시 설명 부담이 된다.
삭제하지 않고 옮긴 이유는 화면 구성 참고 자료로서의 가치가 남아 있기 때문이다.

## 앱 안의 데모 화면은 어떻게 되는가

`frontend/src/features/mockupDemoUi/` 와 `setup-demo-file` / `setup-demo-url` 화면은
빌드 플래그로 격리되어 있다.

```bash
npm run build                          # 프로덕션 — 데모 라우트·청크 모두 없음
VITE_ENABLE_DEMO=true npm run build    # 데모 포함 (영업 시연·내부 확인용)
```

검사: `python scripts/check_demo_isolation.py`
