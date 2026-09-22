FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"

# Set work directory
WORKDIR /app

# Setup SSH for git
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh

# Install system dependencies
# add ffmpeg for video/image processing
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    openssh-client \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    libglib2.0-0 \
    # Font support packages
    fontconfig \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-nanum \
    fonts-nanum-extra \
    fonts-dejavu \
    fonts-liberation \
    # Additional font tools
    fontconfig-config \
    # Additional dependencies
    libpython3.7 \
    pkg-config \
    libicu-dev \
    wget \
    libgdiplus \
    ffmpeg \
    && fc-cache -fv \
    && wget http://ftp.de.debian.org/debian/pool/contrib/m/msttcorefonts/ttf-mscorefonts-installer_3.8_all.deb \
    && apt-get install -y ./ttf-mscorefonts-installer_3.8_all.deb \
    && wget https://archive.debian.org/debian-archive/debian-security/pool/updates/main/o/openssl/libssl1.1_1.1.0l-1~deb9u6_amd64.deb \
    && dpkg -i ./libssl1.1_1.1.0l-1~deb9u6_amd64.deb \
    && wget https://archive.debian.org/debian-security/pool/updates/main/o/openssl/libssl-dev_1.1.0l-1~deb9u6_amd64.deb \
    && dpkg -i ./libssl-dev_1.1.0l-1~deb9u6_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# ═══════════════════════════════════════════════════════════════════════════
# ★★ [턴 AD · 2026-09-23 창 2a · P-247] **pg_dump 는 서버 판보다 낮으면 안 된다**
# ═══════════════════════════════════════════════════════════════════════════
#
#   이 이미지의 기본 저장소(Debian 13 trixie)는 `postgresql-client-17` 을 준다.
#   그런데 우리 DB 서버는 **18.1** 이다. 낮은 판은 높은 판을 못 뜬다:
#
#       pg_dump: error: aborting because of server version mismatch
#       server version: 18.1 ; pg_dump version: 17.7
#
#   ★ 그 결과가 무엇이었나 [실측 2026-09-22 · 턴 AC]:
#     `ops_backup_beat` 이 이 컨테이너 안에서 매일 돌았고 매일 실패했다.
#     `pg_dump -f` 는 **파일을 먼저 만들고** 판 검사에서 죽으므로,
#     금고에는 **0바이트 덤프 30개**가 쌓여 `ls` 로는 「매일 백업이 있다」처럼 보였다.
#     바이트가 있는 마지막 정기 덤프는 **09-07**(15일 전)이었다.
#
#   ★ 왜 「어디서 뜨는가」(`--via docker:postgres`)로 안 푸나:
#     이 컨테이너에는 **docker 소켓도 CLI 도 없다**(실측). 컨테이너 안에서는
#     그 갈래를 부를 수 없다. 그래서 **클라이언트를 올린다** — 세종 P-247.
#
#   ⚠ 17 을 지우지 않는다. 18 을 **더한다** — `pg_wrapper` 가 높은 판을 고른다.
#     그 선택이 실제로 18 인지는 **지은 뒤 이미지 안에서 눌러 확인한다**
#     (`docker run --rm <태그> pg_dump --version` → 18 이어야 한다). 가정하지 않는다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
         -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" \
         > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-18 \
    && rm -rf /var/lib/apt/lists/*


ENV LD_LIBRARY_PATH /lib/x86_64-linux-gnu

# Copy requirements.txt
COPY requirements.txt .

# Install packages from requirements.txt (bao gồm cả các repo Git)
RUN --mount=type=ssh \
    GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


ENTRYPOINT ["/entrypoint.sh"]
