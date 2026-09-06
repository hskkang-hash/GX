/**
 * 로그인 화면 (데스크톱) — **실패를 말하는 화면** (P-78 ② ③ · 2026-09-06 턴 H).
 *
 * 무엇이 이 파일을 만들었나 [실측 · 직전 턴]
 * ------------------------------------------
 *   500 · 503 · 403 · 타임아웃 · 서버 다운 **다섯 갈래 전부**에서 본문이 203자
 *   그대로였다. 아이디·비밀번호가 틀려도 문구가 없었다. 빈 값은 영문이었다.
 *   그리고 빠르게 두 번 누르면 요청이 **두 번** 나갔다.
 *
 * ★ 왜 인수 화면을 **고치지 않고 우리 층에 세웠나**
 * -------------------------------------------------
 * 인수 화면은 남의 것이고, 고치면 그것은 인수 자산이 아니라 우리 빚이 된다
 * (이 저장소가 여덟 화면에 이미 세운 규약). 그런데 이 화면에서 고쳐야 할 것은
 * **글자 몇 줄이 아니라 사실이 흐르는 길**이었다 — 그 화면이 쓰는 로그인 훅은 실패를
 * 접으면서 **상태 코드를 버린다.** 감싸는 것으로는 못 고친다. 그래서 같은 문을
 * 우리 층에서 부르고, **성공한 뒤의 절차는 그 부품의 훅을 그대로 쓴다.**
 *
 * ★ 지키는 것 셋 — 이 화면을 도구들이 두드린다
 * --------------------------------------------
 *   ① 입력칸은 **둘**이고 순서는 아이디 · 비밀번호다.
 *   ② 단추의 이름은 언제나 같다 — 제출 중에도 바뀌지 않는다.
 *   ③ 단추를 **잠그지 않는다.** 잠그면 두 번째 누름이 갈 곳을 잃고, 그 기다림은
 *      화면의 결함이 아니라 도구의 정지가 된다. 이중 제출은 **요청 자리**에서 막는다
 *      (같은 폴더의 요청 파일) — 그것이 리액트 상태보다 빠르고 확실하다.
 *
 * ★ 오류는 **머무는 줄**로 그린다. 토스트로 띄우면 몇 초 뒤 사라지고, 사라진 문구는
 *   「말한 적 없음」과 구별되지 않는다 — 직전 턴이 1.5초·6초 두 번 읽은 이유가 그것이다.
 */
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDispatch } from 'react-redux';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBtn,
  CustomButton,
  CustomModal,
  CustomRouters,
  fetchActivePayment,
  useAPILogin,
  useConfigGroupSystem,
  useLogin,
  useProfile,
  useUpdateUserInfo,
} from 'rj-core';

import { CustomRoutes } from '@/services/API';

import {
  ALREADY_SUBMITTING,
  EMPTY_PASSWORD,
  EMPTY_USERNAME,
  judgeLoginFailure,
  SUBMITTING,
} from './loginCopy';
import { loginInFlight, requestLogin } from './loginRequest';

interface AuthStatus {
  existing_session?: boolean;
  generate_otp_qrcode?: boolean;
  allowpopupotp?: boolean;
  must_change_password?: boolean;
}

export default function LoginDesktop({ logoImage }: { logoImage: string }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();

  const { getProfileAPI, userProfileAPI } = useAPILogin();
  const login = useLogin();
  const updateUserInfo = useUpdateUserInfo();
  const { saveProfile } = useProfile();
  const { fetchFreshConfigGroup } = useConfigGroupSystem();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [usernameError, setUsernameError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  /** 다섯 갈래 중 하나. **머무는 줄이다.** */
  const [failure, setFailure] = useState('');
  const [progress, setProgress] = useState('');
  const [showEndSession, setShowEndSession] = useState(false);
  /**
   * 일회용 비밀번호 갈래. 그 갈래는 화면 두 장이 더 딸려 있고 이 턴에 우리가 다시
   * 지을 자리가 아니다. **없는 갈래를 있는 척 그리지 않는다** — 사실을 말한다.
   */
  const [otpBranch, setOtpBranch] = useState(false);

  /** 성공한 뒤 — **인수 부품의 절차를 그대로 따른다.** 여기서 다시 짓지 않는다. */
  const afterLogin = useCallback(
    async (user: Record<string, any>) => {
      login({
        token: user.access_token,
        refreshToken: user.refresh_token,
        isAuthenticated: true,
        userInfo: user,
      });
      i18n.changeLanguage(user?.language?.code || 'en');

      const [profile, extra] = await Promise.all([
        getProfileAPI(user.user_id),
        userProfileAPI(user.user_id).catch(() => ({ success: false, data: null })),
      ]);
      if (extra?.success && extra.data) saveProfile(extra.data);
      if (!profile?.success) {
        // 토큰은 받았는데 프로필을 못 받았다. **첫 화면을 지어내지 않는다.**
        setFailure('로그인은 됐지만 사용자 정보를 불러오지 못했습니다. 다시 시도해 주십시오.');
        setProgress('');
        return;
      }
      const info = profile.data;
      updateUserInfo(info);
      if (info?.profile__group_id) {
        dispatch(fetchActivePayment(info.profile__group_id) as never);
        fetchFreshConfigGroup(info.profile__group_id);
      }
      const qr = new URLSearchParams(location.search).get('dataQRCode');
      if (qr) {
        navigate(`${CustomRoutes.qrCode}?dataQRCode=${qr}`);
        return;
      }
      const home = info?.settings?.home_screen_setting__path;
      const homeId = info?.settings?.home_screen_setting_id;
      navigate(
        home && home !== '/' && homeId
          ? `${home}?menuId=${homeId}`
          : CustomRouters.profile.path,
      );
    },
    [
      dispatch,
      fetchFreshConfigGroup,
      getProfileAPI,
      i18n,
      location.search,
      login,
      navigate,
      saveProfile,
      updateUserInfo,
      userProfileAPI,
    ],
  );

  const submit = useCallback(
    async (endPreviousSession: boolean) => {
      // ① 빈 값 — **서버를 부르기 전에** 화면이 말한다.
      const id = username.trim();
      const pw = password;
      const missingId = id ? '' : EMPTY_USERNAME;
      const missingPw = pw ? '' : EMPTY_PASSWORD;
      setUsernameError(missingId);
      setPasswordError(missingPw);
      if (missingId || missingPw) {
        setFailure('');
        setProgress('');
        return;
      }

      // ③ 이중 제출 — 이미 날아가 있으면 **새 요청을 만들지 않는다.**
      //   삼킨 것을 삼켰다고 말한다: 아무 말 없는 단추는 고장으로 읽힌다.
      if (loginInFlight()) {
        setProgress(ALREADY_SUBMITTING);
        return;
      }

      setFailure('');
      setProgress(SUBMITTING);
      const outcome = await requestLogin(id, pw, endPreviousSession);
      setProgress('');

      const body = (outcome.body ?? null) as Record<string, any> | null;
      const auth: AuthStatus = (body?.auth_status ?? {}) as AuthStatus;

      if (outcome.status === 200 && body?.success && body?.user) {
        setShowEndSession(false);
        await afterLogin(body.user);
        return;
      }
      if (auth.existing_session) {
        setShowEndSession(true);
        return;
      }
      if (auth.generate_otp_qrcode || auth.allowpopupotp) {
        setOtpBranch(true);
        return;
      }

      // ②③④⑤ — 다섯 갈래는 **한 곳에서** 갈린다.
      setFailure(judgeLoginFailure(outcome).text);
    },
    [afterLogin, password, username],
  );

  if (otpBranch) {
    return (
      <div className="login-container" id="login-page">
        <div className="login-card">
          <div className="error-message" role="alert">
            <span>
              이 계정은 일회용 비밀번호가 필요합니다. 화면을 새로 고친 뒤 다시 로그인해
              주십시오.
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container" id="login-page">
      <div className="login-card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1em' }}>
          <img className="logo-image" src={logoImage} alt="logo-img" />
        </div>
        <form
          style={{ display: 'flex', flexDirection: 'column', gap: '.5em' }}
          onSubmit={(ev) => {
            ev.preventDefault();
            void submit(false);
          }}
        >
          <label style={{ display: 'flex', flexDirection: 'column', gap: '.25em' }}>
            <span>{t('ID-Login')}</span>
            <input
              className="ant-input"
              style={{ padding: '.5em', width: '100%' }}
              type="text"
              name="username"
              autoComplete="username"
              value={username}
              placeholder={t('ID-Login')}
              onChange={(ev) => setUsername(ev.target.value)}
            />
          </label>
          {usernameError ? (
            <div className="error-message">
              <span>{usernameError}</span>
            </div>
          ) : null}

          <label style={{ display: 'flex', flexDirection: 'column', gap: '.25em' }}>
            <span>{t('Password')}</span>
            <input
              className="ant-input"
              style={{ padding: '.5em', width: '100%' }}
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              placeholder={t('Password')}
              onChange={(ev) => setPassword(ev.target.value)}
            />
          </label>
          {passwordError ? (
            <div className="error-message">
              <span>{passwordError}</span>
            </div>
          ) : null}

          {/* 다섯 갈래 중 하나. **사라지지 않는다.** */}
          {failure ? (
            <div className="error-message" role="alert">
              <span>{failure}</span>
            </div>
          ) : null}
          {progress ? (
            <div
              role="status"
              style={{ fontSize: 13, opacity: 0.8 }}
            >
              {progress}
            </div>
          ) : null}

          <div className="forgot-password-container">
            <a
              className="forgot-password-link"
              onClick={() => navigate('/forgot-password')}
            >
              {t('Forgot Password')}
            </a>
          </div>
          <div className="login-button-container">
            {/*
              ⚠ 이 단추에 잠금·회전자를 걸지 않는다. 걸면 이름과 눌림이 바뀌고,
                두 번째 누름이 **갈 곳을 잃는다.** 이중 제출은 요청 자리가 막는다.
            */}
            <CustomButton
              type="primary"
              htmlType="submit"
              className="login-button"
              text={t('Login')}
            />
          </div>
        </form>
      </div>

      <CustomModal
        title={t('End Session')}
        show={showEndSession}
        onHide={() => setShowEndSession(false)}
        id="setting-modal-user"
      >
        <div style={{ width: '25rem' }}>
          {t(
            'This account is active on another device. Would you like to terminate the previous session and log in?',
          )}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              key="confirm"
              type="button"
              variant="outline"
              color="primary"
              size="lg"
              label={t('Confirm')}
              onClick={() => {
                setShowEndSession(false);
                void submit(true);
              }}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              key="cancel"
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              label={t('Cancel')}
              onClick={() => setShowEndSession(false)}
            />,
          ]}
        />
      </CustomModal>
    </div>
  );
}
