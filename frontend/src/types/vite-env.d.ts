/// <reference types="vite/client" />

/**
 * W0-4 — 데모·목업 화면 격리 플래그.
 * vite.config.ts 의 define 이 빌드 시점에 리터럴로 치환한다(환경변수 VITE_ENABLE_DEMO).
 * 런타임 조회가 아니라 컴파일 상수이므로 false 일 때 해당 분기가 번들에서 제거된다.
 */
declare const __DEMO_ENABLED__: boolean;

declare module '*.svg?react' {
  import * as React from 'react';
  const ReactComponent: React.FunctionComponent<
    React.SVGProps<SVGSVGElement> & { title?: string }
  >;
  export default ReactComponent;
}
