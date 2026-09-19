/**
 * 403 이 **읽기 거부인가 쓰기 거부인가** — 그 갈래와 「한 거절은 한 자리에서만」 규약을
 * 돌려서 재는 자리. (턴 V · 차선 U24)
 *
 * 왜 이 파일이 있나
 * -----------------
 * 이 저장소의 앞판에는 시험 달리개가 없다(`vitest`·`jest` 둘 다 없다). 그래서 갈래를
 * 정하는 순수 함수들이 **한 번도 돌아 본 적 없이** 화면에만 실렸다. 화면에만 실린 규칙은
 * 눈으로 읽어야 하고, 눈으로 읽은 것은 초록이 아니다.
 *
 * ⚠ 타입 검사(`tsc`)는 이 저장소에서 게이트가 아니다 — 인수 자산에 이미 3,200건이 넘는
 *   오류가 살아 있고 `vite` 는 타입을 안 본다. 그래서 여기서 재는 것은 **동작**이다.
 *
 * 어떻게 돌리나 — 컨테이너 `gx-fe-build` 안 (node 18 · `src` 를 `/tmp/gxb` 로 옮긴 뒤)
 * -----------------------------------------------------------------------------------
 *   1) 묶는다:  ./node_modules/.bin/esbuild src/features/session/permissionDenied.ts
 *                 --bundle --format=esm --outfile=/tmp/out_denial.mjs
 *   2) 돌린다:  node <이 파일> /tmp/out_denial.mjs
 *
 * 마지막 줄이 「통과 N · 실패 0」이면 통과다. 실패가 하나라도 있으면 exit 1.
 */
const bundle = process.argv[2];
if (!bundle) {
  console.error('쓰는 법: node check_denial_kind.mjs <esbuild 로 묶은 permissionDenied 번들>');
  process.exit(2);
}
const M = await import(bundle);


let pass = 0, fail = 0;
const t = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  ok ? pass++ : fail++;
  console.log((ok ? 'PASS ' : 'FAIL ') + name + '  got=' + JSON.stringify(got) + ' want=' + JSON.stringify(want));
};

// ① 메서드가 갈래를 정한다
t('GET 은 읽기',    M.denialKindOf('GET'), 'read');
t('get 은 읽기',    M.denialKindOf('get'), 'read');
t('HEAD 는 읽기',   M.denialKindOf('HEAD'), 'read');
t('POST 는 쓰기',   M.denialKindOf('POST'), 'write');
t('put 은 쓰기',    M.denialKindOf('put'), 'write');
t('DELETE 는 쓰기', M.denialKindOf('DELETE'), 'write');
t('없으면 읽기(옛 부르는 쪽)', M.denialKindOf(undefined), 'read');

// ② 결과줄이 최소쌍이다
t('읽기 결과줄', M.COPY_DENIED_CONSEQUENCE.read,  '이 자료는 지금 계정의 권한으로 볼 수 없습니다.');
t('쓰기 결과줄', M.COPY_DENIED_CONSEQUENCE.write, '이 자료는 지금 계정의 권한으로 고칠 수 없습니다.');
t('두 줄은 다르다', M.COPY_DENIED_CONSEQUENCE.read !== M.COPY_DENIED_CONSEQUENCE.write, true);

// ③ 서버가 말이 없을 때의 대체 문장도 갈린다
t('읽기 대체 문장', M.messageOfDenial(null, 'read'),  '볼 권한이 없습니다');
t('쓰기 대체 문장', M.messageOfDenial(null, 'write'), '고칠 권한이 없습니다');
// 서버가 말하면 서버의 말이 먼저다 (실측 본문 그대로)
t('서버 말이 먼저 — 쓰기', M.messageOfDenial(
    {message: {ko: '읽기 전용 계정입니다 — 이 작업은 수행할 수 없습니다.', en: 'x'}}, 'write'),
    '읽기 전용 계정입니다 — 이 작업은 수행할 수 없습니다.');

// ④ 알림: 갈래+문이 열쇠다 — 같은 문의 읽기와 쓰기가 서로를 안 삼킨다
const seen = [];
globalThis.window = { dispatchEvent: (e) => { if (e && e.detail) seen.push(e.detail); return true; } };
globalThis.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } };
globalThis.Event = class { constructor(type) { this.type = type; } };
M.resetPermissionDeniedForTest();
M.announcePermissionDenied({}, '/api/dsm/reports/runs', 'get');
M.announcePermissionDenied({}, '/api/dsm/reports/runs', 'post');
M.announcePermissionDenied({}, '/api/dsm/reports/runs', 'post');   // 같은 것은 한 번만
t('읽기+쓰기 둘 다 알린다', seen.map((d) => d.kind), ['read', 'write']);
t('같은 갈래는 한 번만',    seen.length, 2);
t('알린 목록',              M.deniedPaths(), ['read /api/dsm/reports/runs', 'write /api/dsm/reports/runs']);

// ⑤ 임자 — 선언한 앞머리는 띠가 안 그린다. 선언을 풀면 다시 그린다.
t('선언 전에는 임자 없음', M.hasDenialOwner('/api/dsm/reports/runs'), false);
const release = M.ownDenialPaths(['/api/dsm/reports/']);
t('선언 뒤 임자 있음',      M.hasDenialOwner('/api/dsm/reports/runs'), true);
t('남의 문은 그대로',       M.hasDenialOwner('/api/dsm/audit'), false);
const release2 = M.ownDenialPaths(['/api/dsm/reports/']);   // 두 화면이 같은 앞머리를
release();
t('하나가 떠나도 남은 선언이 산다', M.hasDenialOwner('/api/dsm/reports/runs'), true);
release2();
t('둘 다 떠나면 띠가 다시 그린다',  M.hasDenialOwner('/api/dsm/reports/runs'), false);
release();  // 두 번 풀어도 셈이 안 깨진다
t('두 번 풀어도 그대로', M.hasDenialOwner('/api/dsm/reports/runs'), false);

console.log('----');
console.log('통과 ' + pass + ' · 실패 ' + fail);
process.exit(fail ? 1 : 0);
