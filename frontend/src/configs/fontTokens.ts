/**
 * P-454 [N4] — 전역 글씨 토큰. 화면 인라인에 `fontSize: 12` 를 새로 쓰지 않는다.
 * antd `ConfigProvider token.fontSize = FONT_BASE` (main.tsx) · 보조 글씨는 `FONT_SM`.
 * 게이트: scripts/verify_font_tokens.py (인라인 12 px 검출 → 0).
 */
export const FONT_BASE = 14;
export const FONT_SM = 13;
