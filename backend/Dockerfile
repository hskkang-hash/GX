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
