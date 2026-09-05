# STAGING ③ — 공개 URL 의 TLS 인증서: 어떻게 받고 어떻게 갱신하는가

**작성 2026-09-05 · 차선 E(턴 F).**
**서버는 아직 없다.** 이 문서의 [실측]은 **이 저장소에서 잰 것**뿐이고,
「받았다」·「붙였다」는 한 줄도 없다.

## 0. 지금 상태 — 잰 것

    [실측] nginx 설정에 `listen 443 ssl` 이 **한 줄도 없다**
           nginx/nginx.conf     : listen 3002 · listen 8002   (평문)
           nginx/gx-front.conf  : listen 8500                 (평문)
    [실측] `ssl_certificate` 지시자 **0개**
    [실측] certbot·letsencrypt·acme 를 쓰는 설정·스크립트 **없다**
           (앞단 번들 안의 문자열 몇 개는 지도 라이브러리의 것이고 우리 것이 아니다)
    [실측] `DJANGO_CSRF_TRUSTED_ORIGINS` 가 `backend/.env.stg` 에 **없다**
           — 공개 URL 을 https 로 세우는 순간 이 칸이 비면 POST 가 전부 막힌다

즉 **TLS 는 아직 아무 데도 서 있지 않다.** 이 문서는 그것을 세우는 절차다.

## 1. 무엇을 고르는가 — 갈래 셋

| 갈래 | 언제 | 갱신 | 이 제품에서의 값 |
|---|---|---|---|
| ㉠ Let's Encrypt (ACME · HTTP-01) | 공개 인터넷에서 80/443 이 열릴 때 | 60일마다 자동 | **스테이징의 기본값** |
| ㉡ Let's Encrypt (ACME · DNS-01) | 80을 못 여는 망 · 와일드카드가 필요할 때 | 자동(DNS API 필요) | 폐쇄망 스테이징 |
| ㉢ 기관 발급 인증서 (공공/사설 CA) | 고객이 인증서를 준다 | **사람이 손으로** | 운영에서 흔함 |

★ **갱신 방식이 갈래를 고른다.** ㉠㉡은 자동이고 ㉢은 사람이다. 사람이 갱신하는
인증서는 **반드시 만료된다** — 잊기 때문이다. 그래서 ㉢을 고른다면 만료 감시를
같이 세워야 한다(아래 4).

## 2. ㉠ Let's Encrypt · HTTP-01 — 스테이징의 기본 절차

전제: 공개 도메인 하나(`stg.<도메인>`)가 스테이징 기계의 공인 IP 를 가리키고,
80/443 이 인터넷에서 닿는다.

    ① DNS A 레코드를 세운다.        (사람 · 승인 후)
       dig +short stg.<도메인>       ← 나온 IP 가 그 기계인지 **먼저 확인한다**
       ★ 이것을 안 하고 certbot 을 부르면 실패 횟수만 쌓이고, Let's Encrypt 는
         **실패에도 한도**가 있다(시간당 5회 · 주당 50회). 한도에 걸리면 몇 시간을
         기다려야 하고, 그 몇 시간이 승인 당일의 몇 시간이다.

    ② **먼저 staging 엔드포인트로 연습한다.** (--dry-run 이 아니라 --test-cert)
       certbot certonly --webroot -w /var/www/certbot \
               -d stg.<도메인> --test-cert --agree-tos -m <운영자메일>
       ★ 이 인증서는 브라우저가 안 믿는다 — **그것이 목적이다.** 배선(80 포트가
         닿는가 · webroot 가 맞는가)만 먼저 재고, 발급 한도는 안 쓴다.

    ③ 진짜로 받는다.
       certbot certonly --webroot -w /var/www/certbot \
               -d stg.<도메인> --agree-tos -m <운영자메일>
       → /etc/letsencrypt/live/stg.<도메인>/{fullchain.pem,privkey.pem}

    ④ nginx 에 붙인다. **이 저장소에는 아직 이 블록이 없다** — 세울 때 만든다.
       server {
           listen 443 ssl http2;
           server_name stg.<도메인>;
           ssl_certificate     /etc/letsencrypt/live/stg.<도메인>/fullchain.pem;
           ssl_certificate_key /etc/letsencrypt/live/stg.<도메인>/privkey.pem;
           ssl_protocols       TLSv1.2 TLSv1.3;     # TLS 1.0/1.1 은 안 켠다
           # … 기존 location 블록(nginx/gx-front.conf)을 그대로 옮긴다
       }
       server {                                       # 80 은 갱신용 + 되돌림
           listen 80;
           server_name stg.<도메인>;
           location /.well-known/acme-challenge/ { root /var/www/certbot; }
           location / { return 301 https://$host$request_uri; }
       }

    ⑤ **장고 쪽을 함께 고친다.** 이 줄을 빼면 화면은 뜨는데 저장이 전부 막힌다:
       backend/.env.stg
           DJANGO_CSRF_TRUSTED_ORIGINS=https://stg.<도메인>
           ALLOWED_HOSTS=stg.<도메인>
       ★ [실측] 지금 `.env.stg` 에 이 열쇠가 **없다**(staging_mirror.sh 3b).

## 3. 갱신 — **자동이 도는지 사람이 확인한다**

    certbot renew --dry-run        ← 갱신 경로가 도는지 **미리** 잰다
    systemctl list-timers | grep certbot    ← 타이머가 실재하는가

★ **「certbot 을 깔았다」와 「갱신이 돈다」는 다른 사실이다**(D-301). 이 저장소가
반복해서 만난 실패의 모양 그대로다 — 설치는 선언이고 갱신은 실행이다.
갱신은 만료 30일 전부터 시도되므로, **한 달 동안 조용히 실패해도 아무 일이 없다가**
어느 날 사이트가 죽는다. 그러므로 갱신 성공 자체를 재야 한다(아래 4).

갱신 뒤 nginx 는 **다시 읽어야** 새 인증서를 쓴다:

    certbot renew --deploy-hook "nginx -s reload"

★ `reload` 는 컨테이너를 다시 만들지 않는다 — 그것이 이 자리에서 중요하다.
  [실측 2026-09-05] 이 기계에서 `gx-nginx-e` 를 reload 했을 때 컨테이너는 그대로
  살아 있었고 설정만 바뀌었다.

## 4. 만료를 **감시한다** — 이 절의 나머지 절반

인증서는 「받았다」로 끝나지 않는다. **만료일은 반드시 온다.**

    권고 신호: `tls_cert_days_left` — `scripts/ops_monitor.py` 의 열다섯 번째 신호
    임계: 14일. 왜 14인가 — Let's Encrypt 는 만료 30일 전부터 갱신을 시도한다.
          30일과 14일 사이에 **자동 갱신이 두 주 동안 실패할 수 있고**, 14일은
          그 실패를 사람이 알아채고 손으로 고칠 수 있는 마지막 폭이다.

    재는 법(서버에서):
        openssl s_client -connect stg.<도메인>:443 -servername stg.<도메인> \
            </dev/null 2>/dev/null | openssl x509 -noout -enddate

★ **이 신호는 아직 안 붙였다.** 붙일 대상(공개 URL)이 없기 때문이다 —
  **없는 것을 재는 신호는 언제나 「못 쟀다」를 내고, 그 회색이 쌓이면 사람이
  감시 전체를 안 본다**(D-290). 서버가 서는 날 URL 과 함께 붙인다.
  그때까지는 **못 잰 것**으로 남긴다.

## 5. ㉢ 기관 발급 인증서를 받는 경우

    ① 개인키와 CSR 을 **스테이징 기계에서** 만든다. 개인키는 그 기계를 떠나지 않는다.
       openssl req -new -newkey rsa:2048 -nodes \
           -keyout stg.key -out stg.csr -subj "/CN=stg.<도메인>"
    ② CSR 만 기관에 낸다. **개인키를 메일로 보내지 않는다** — 보낸 순간 그 인증서는
       우리 것이 아니다.
    ③ 받은 인증서와 **중간 인증서를 이어 붙인다**(fullchain). 이것을 빠뜨리면
       데스크톱 브라우저는 되는데 **모바일에서만 안 되는** 고전적 증상이 난다.
       cat stg.crt intermediate.crt > fullchain.pem
    ④ 만료일을 달력에 넣는다 — 그리고 4의 신호를 **반드시** 함께 세운다.
       사람이 갱신하는 인증서에서 감시는 선택이 아니다.

## 6. 이 문서가 **아직 못 하는 것**

    · 인증서를 실제로 받아 보지 못했다 — 도메인도 서버도 없다.
    · `listen 443` 블록을 이 저장소에 아직 안 넣었다. 도메인 이름이 정해지지 않은
      채로 넣으면 그 파일은 **틀린 이름으로 굳는다**.
    · `tls_cert_days_left` 신호를 아직 안 붙였다(위 4의 이유).

**이 셋은 승인 뒤 첫 30분의 일이다.** 지금 적어 두는 이유는, 그 30분에 이 순서를
다시 생각하지 않기 위해서다.
