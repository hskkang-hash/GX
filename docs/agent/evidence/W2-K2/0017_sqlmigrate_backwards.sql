BASE_DIR /app
[MinIO Init] Warning: HTTPConnectionPool(host='minio.invalid', port=80): Max retries exceeded with url: /guardianx-dev?location= (Caused by NameResolutionError("<urllib3.connection.HTTPConnection object at 0x73d2a7a7be10>: Failed to resolve 'minio.invalid' ([Errno -2] Name or service not known)"))
🚀 [DJANGO_READY] Applying backend optimizations...
🌍 [DJANGO_READY] Universal optimization system initialized for ALL models & views
🔗 [DJANGO_READY] Cache invalidation signals registered manually
🧵 [DJANGO_READY] Thread request context propagation installed
BEGIN;
--
-- Create model NotificationRule
--
DROP TABLE "stream_monitors_notificationrule" CASCADE;
--
-- Create model DeliveryRecord
--
DROP TABLE "stream_monitors_deliveryrecord" CASCADE;
COMMIT;
