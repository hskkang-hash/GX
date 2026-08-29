BEGIN;
--
-- Add field address_status to detectionevent
--
ALTER TABLE "stream_monitors_detectionevent" DROP COLUMN "address_status" CASCADE;
--
-- Add field address to detectionevent
--
ALTER TABLE "stream_monitors_detectionevent" DROP COLUMN "address" CASCADE;
COMMIT;
