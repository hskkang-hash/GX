/**
 * 플랫폼 운영(U0) 화면 문구 사전 — 턴 AO · 차선 N3.
 *
 * `features/dsm/copy.ts` 머리말과 같은 규칙: **사전에 없는 문구는 화면에 만들지
 * 않는다.** 개발 용어·절 번호(`O-01`)·영문 라벨은 화면에 내지 않는다(§0.4 규약
 * 셋째 조건) — 여기서 사람이 읽을 한국어로만 옮긴다.
 */

export const OPS_TITLE = '플랫폼 운영';

export const OPS_SECTION_LABEL = {
  tenants: '테넌트',
  health: '건강 보드',
  incidents: '인시던트',
  backups: '백업·복구',
  onboarding: '온보딩 관제',
  releases: '릴리스·배포',
};

export const OPS_HEALTH_COLOR_LABEL: Record<string, string> = {
  green: '정상',
  red: '점검 필요',
};

export const OPS_INCIDENT_STATUS_LABEL: Record<string, string> = {
  open: '접수',
  acknowledged: '조치 중',
  escalated: '에스컬레이션',
  closed: '종결',
};

export const OPS_SEVERITY_LABEL: Record<string, string> = {
  critical: '긴급',
  major: '중요',
  minor: '경미',
};

export const OPS_EMPTY = '표시할 데이터가 없습니다.';
export const OPS_LOADING = '불러오는 중입니다…';
export const OPS_ERROR_PREFIX = '불러오지 못했습니다: ';
export const OPS_FORBIDDEN = '플랫폼 운영자만 볼 수 있는 화면입니다.';

// ── 턴 AQ · 차선 N2 — 보드 배선 문구 ────────────────────────────────────
export const OPS_RELOAD = '다시 불러오기';
export const OPS_DONE = '처리했습니다 — 보드를 다시 불러왔습니다.';
export const OPS_FAILED_PREFIX = '처리하지 못했습니다: ';
export const OPS_NOT_READ = '기록을 아직 읽지 못했습니다';

export const OPS_TAB_LABEL = {
  tenants: '테넌트 발급',
  apps: '앱 설치·버전',
  health: '건강 보드',
  incidents: '인시던트',
  backups: '백업·복구',
  onboarding: '온보딩 관제',
  audit: '플랫폼 감사',
  keys: '키·자격 회전',
  releases: '릴리스·배포',
  seed: '시드·훈련 데이터',
};

export const OPS_TENANT_COPY = {
  code: '테넌트 코드',
  name: '테넌트 이름(시군구)',
  region: '시도',
  departments: '부서(쉼표로 구분)',
  domain: '도메인',
  publicUrl: '공개 주소',
  adminUsername: '초기 관리자 아이디',
  adminEmail: '초기 관리자 이메일',
  adminPassword: '초기 관리자 비밀번호',
  issue: '테넌트 발급',
  members: '구성원',
  certificate: '인증서',
  certificateNote: '인증서는 외부 인증기관에서 발급합니다 — 이 화면은 도메인만 등록합니다.',
};

export const OPS_APP_COPY = {
  tenant: '테넌트',
  app: '앱',
  version: '버전',
  status: '상태',
  install: '설치·업그레이드',
  activate: '활성화',
  deactivate: '비활성화',
  upgradedFrom: '이전 버전',
  markedProbe: '표식됨',
  markedUnknown: '못 쟀다',
  markedProbeLabel: '탐침',
  markedSeedLabel: '씨앗',
  markedHint: '유령 시드는 지우지 않고 표식합니다(삭제는 대표).',
};

export const OPS_APP_STATUS_LABEL: Record<string, string> = {
  active: '사용 중',
  inactive: '사용 안 함',
};

export const OPS_HEALTH_COPY = {
  cameras: '카메라 맥박(활성/전체)',
  queueLag: '큐 지연(초)',
  storage: '저장 %',
  backupReceipt: '백업 회수증',
  survival: '생존 알림 지연',
  color: '상태',
  autoIncident: '자동 인시던트',
  notMeasured: '측정하지 않는 항목',
  fiveXx: '서버 오류(5xx) 최근 24시간',
  fiveXxUnmeasured: '아직 재지 못했습니다(카운터가 켜진 뒤 요청이 없거나 읽지 못함)',
  fiveXxScope: '앞문이 낸 응답 기준 — 프록시가 스스로 낸 502·504 는 빠집니다',
};

export const OPS_HEALTH_NOT_MEASURED_LABEL: Record<string, string> = {
  '5xx': '서버 오류 응답 비율 — 이 보드는 아직 재지 않습니다.',
  gate_16_colors: '테넌트별 점검 16색 — 이 보드는 아직 재지 않습니다.',
};

export const OPS_INCIDENT_COPY = {
  open: '인시던트 접수',
  respond: '1차 대응',
  escalate: '에스컬레이션',
  close: '종결',
  cause: '원인',
  prevention: '재발 방지',
  firstDue: '1차 대응 기한',
  escalationDue: '에스컬레이션 기한',
  report: '종결 보고서',
  summary: '요약',
  showAll: '종결 포함 전체',
};

export const OPS_BACKUP_COPY = {
  receipt: '최근 백업 회수증',
  measuredAt: '회수 시각',
  verdict: '판정',
  bytes: '덤프 크기(바이트)',
  destination: '저장 목적지',
  fresh24h: '하루 안 회수',
  drill: '최근 복원 시험',
  rto: '복원 소요(초)',
  tables: '복원된 표 수',
  fresh31d: '한 달 안 시험',
  destinationNote: '다른 호스트 목적지로의 이관은 외부 저장소 연동 뒤에 붙습니다.',
  yes: '예',
  no: '아니오',
  unknown: '모름',
};

export const OPS_ONBOARDING_COPY = {
  score: '48행 재측 결과',
  roleProgress: '역할별 진행률',
  blocked: '막힌 카드',
  tenants: '테넌트별 진행(D-7~D+30)',
  dayN: '진행 일수',
  stage: '단계',
  role: '역할',
  none: '막힌 카드가 없습니다.',
};

export const OPS_AUDIT_COPY = {
  entries: '운영자 행위 전건',
  kind: '구분',
  actor: '누가',
  at: '언제',
  action: '무엇을',
  tenant: '테넌트',
  requestAccess: '열람 요청',
  approve: '승인',
  viewMembers: '구성원 열람',
  reason: '사유',
  members: '구성원',
};

export const OPS_AUDIT_KIND_LABEL: Record<string, string> = {
  'guardianx.ops.tenants': '테넌트',
  'guardianx.ops.apps': '앱 설치',
  'guardianx.ops.incidents': '인시던트',
  'guardianx.ops.seed': '시드·훈련',
  'guardianx.ops.tenant_access': '테넌트 열람',
  'guardianx.ops.keys': '키 회전',
};

export const OPS_AUDIT_ACTION_LABEL: Record<string, string> = {
  issue: '테넌트 발급',
  issue_denied_stale_proxy: '테넌트 발급 거절(오래된 로그인)',
  install: '앱 설치',
  status: '앱 상태 변경',
  open: '인시던트 접수',
  respond: '1차 대응',
  escalate: '에스컬레이션',
  close: '종결',
  request: '열람 요청',
  approve: '열람 승인',
  rotate: '키 회전',
  plant: '시드 심기',
  hide: '시드 숨김',
  deploy_scenario: '훈련 시나리오 배포',
  end_scenario: '훈련 종료',
};

export const OPS_KEY_COPY = {
  owner: '테넌트',
  prefix: '키 앞자리',
  age: '발급 뒤 일수',
  nextDue: '다음 회전일',
  why: '사유',
  rotate: '회전',
  policy: '회전 주기(일)',
  due: '회전 필요',
  lastRotation: '최근 회전 기록',
  rotationCount: '회전 감사 줄 수',
  runbookTitle: '회전 절차',
  runbook: [
    '1. 회전이 필요한 키를 표에서 고릅니다(다음 회전일이 지난 키).',
    '2. 「회전」을 누르면 새 키가 발급되고 옛 키는 바로 멈춥니다.',
    '3. 새 키를 그 기관 담당자에게 전달합니다(이 화면에는 키 값이 나타나지 않습니다).',
    '4. 회전 기록은 플랫폼 감사에 한 줄로 남습니다.',
  ],
};

export const OPS_RELEASE_COPY = {
  at: '배포 시각',
  commit: '버전',
  reason: '사유',
  exit: '배포',
  smoke: '걷기 확인',
  drill: '되돌리기 시험',
  gate: '배포 합격',
  latest: '최근 배포',
  pass: '통과',
  fail: '실패',
};

export const OPS_SEED_COPY = {
  tenant: '테넌트',
  scenario: '시나리오 이름',
  note: '메모·사유',
  plant: '검수 시드 심기',
  hide: '시드 숨기기',
  deploy: '훈련 시나리오 배포',
  end: '훈련 종료',
  drill: '훈련 중',
  live: '실운영',
  history: '시드·훈련 기록',
  contamination: '데이터 출처 분포',
  seedCount: '시드',
  liveCount: '실데이터',
  since: '시작',
  by: '누가',
};

export const OPS_SEED_ACTION_LABEL: Record<string, string> = {
  plant: '시드 심기',
  hide: '시드 숨김',
  deploy_scenario: '훈련 시나리오 배포',
  end_scenario: '훈련 종료',
};
