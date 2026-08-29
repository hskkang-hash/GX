BEGIN;
--
-- Add field address to detectionevent
--
ALTER TABLE "stream_monitors_detectionevent" ADD COLUMN "address" varchar(512) NULL;
--
-- Add field address_status to detectionevent
--
ALTER TABLE "stream_monitors_detectionevent" ADD COLUMN "address_status" varchar(16) DEFAULT 'pending' NOT NULL;
ALTER TABLE "stream_monitors_detectionevent" ALTER COLUMN "address_status" DROP DEFAULT;
CREATE INDEX "stream_monitors_detectionevent_address_status_6576c47f" ON "stream_monitors_detectionevent" ("address_status");
CREATE INDEX "stream_monitors_detectionevent_address_status_6576c47f_like" ON "stream_monitors_detectionevent" ("address_status" varchar_pattern_ops);
COMMIT;
