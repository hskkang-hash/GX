#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


# Start Celery worker in background
echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A config worker -l INFO -n worker@%h &    

# Start Celery beat in background
echo -e "${YELLOW}Starting Celery beat...${NC}"
celery -A config beat -l INFO &

# Wait a moment for Celery to start
sleep 3

python manage.py migrate
python manage.py initialize_base_data 
# python manage.py initialize_menu_data
python manage.py initialize_grid_data --grid-data-path=./common/grid_data.py
python manage.py migrate_menu_translations 
python manage.py add_use_group_config
python manage.py generate_unit_config --update
python devices/init_base_device_data.py
# python manage.py init_operation_settings
python manage.py init_system_default_formats
python manage.py setup_default_formats
python manage.py init_system_currency
python manage.py create_sample_order_item_types
python manage.py create_default_location_types
python manage.py init_checklist_categories
# python manage.py create_test_session
# python manage.py setup_default_formats --clean-outdated    #clear old format
# python manage.py initialize_base_data --fix_timezones      #fix timezone
# python manage.py initialize_system_config                  #init system config
python manage.py initialize_allow_register
python manage.py create_default_template
python manage.py close_idle_connections --force
python manage.py create_ai_models
python manage.py create_sample_drone_anomaly_predictions
python manage.py init_default_speed_wp
python manage.py update_usergroup_settings
python manage.py create_default_deactivate_reasons
python manage.py init_surveillance_data
# python manage.py create_dashboard_config
# python manage.py create_delivery_inquiry_refresh_config
# Sử dụng file cấu hình Gunicorn tối ưu
exec gunicorn -c gunicorn.conf.py config.asgi:application
