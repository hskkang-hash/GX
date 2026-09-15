#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting GuardianX Backend Setup...${NC}"

# Check Python and pip
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python3 is not installed. Installing Python3...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    virtualenv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update the .env file with your configuration${NC}"
    exit 1
fi

# Create database if not exists
echo -e "${YELLOW}Checking database...${NC}"
# W0-0: 자격증명은 .env 에서만 읽는다. 스크립트에 실값을 두지 않는다.
set -a; . ./.env; set +a
: "${DB_PASSWORD:?DB_PASSWORD 가 .env 에 없습니다}"
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-postgres}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -tc "SELECT 1 FROM pg_database WHERE datname = 'guardianx_dev_31'" | grep -q 1 || \
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -c "CREATE DATABASE \"guardianx_dev_31\""

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py makemigrations
python manage.py migrate user
python manage.py migrate

# Check superuser
echo -e "${YELLOW}Checking for superuser...${NC}"
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('Superuser exists' if User.objects.filter(is_superuser=True).exists() else 'No superuser found')"

# Start development server
echo -e "${GREEN}Starting development server...${NC}"

# Start Celery worker in background
echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A config worker -l INFO &

# Start Celery beat in background
echo -e "${YELLOW}Starting Celery beat...${NC}"
celery -A config beat -l INFO &

# Wait a moment for Celery to start
sleep 3

# grid_data path: backend/common/grid_data.py
# python manage.py initialize_base_data
# python manage.py initialize_menu_data
# python manage.py initialize_grid_data --grid-data-path=backend/common/grid_data.py
# python manage.py add_use_group_config
python devices/init_base_device_data.py
# ★ [턴 O · 2026-09-10 · 영실] **여기가 공유 비밀번호 74개의 발원지였다.**
#   위 다섯 줄은 주석이지만, 주석은 다음 사람이 **그대로 복사하는 서식**이다.
#   실측: 계정 114개 중 **74개**가 한 단어를 쓰고 있었고(73 활성), 그 안에 이
#   저장소의 **유일한 superuser 와 역할 superuser 13개 중 8개**가 들어 있었다.
#   값은 회전으로 무력화했다(74/74 검증 · 새 값은 저장소 밖). 서식도 함께 고친다 —
#   값을 지우고 패턴을 남기면 같은 일이 다음 설치에서 다시 벌어진다.
#   ⚠ `GX_SEED_ADMIN_PASSWORD` 는 **선언하지 않으면 빈 값**이고, 그러면 이 명령은
#     계정을 만들지 못한다 — 그것이 의도다(자리표로 계정이 태어나지 않는다).
# python manage.py create_default_superuser --is-superuser --is-staff
# python manage.py create_default_superuser --username=phatlh --email=phatlh@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Phat --last-name=Le --language=en
# python manage.py create_default_superuser --username=man --email=man@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Man --last-name=Lu --language=en
# python manage.py create_default_superuser --username=son --email=son@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Son --last-name=Nguyen --language=en
# python manage.py create_default_superuser --username=tuan --email=tuan@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Tuan --last-name=Tran --language=en
# python manage.py create_default_superuser --username=huy --email=huy@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Huy --last-name=Nguyen --language=en
# python manage.py create_default_superuser --username=thanh --email=thanh@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Thanh --last-name=Tran --language=en
# python manage.py create_default_superuser --username=rin --email=rin@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Rin --last-name=Tran --language=en
# python manage.py create_default_superuser --username=thao --email=thao@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Thao --last-name=Tran --language=en
# python manage.py create_default_superuser --username=chi --email=chi@yopmail.com --password="$GX_SEED_ADMIN_PASSWORD" --first-name=Chi --last-name=Nguyen --language=en


# # initialize default data
# python manage.py create_default_delivery_options
# python manage.py create_sample_order_item_types
# python manage.py create_default_payment_types
# python manage.py create_default_order_status
# python manage.py create_sample_terminals
# python manage.py create_operation_config
# python manage.py generate_unit_config --update
# python manage.py create_default_location_types
python manage.py initialize_allow_register
python manage.py init_days_of_week
# python manage.py runserver 0.0.0.0:8000
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload
