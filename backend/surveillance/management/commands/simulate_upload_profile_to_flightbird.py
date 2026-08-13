"""
Django management command to simulate record video + detect logs that are related to
SurveillanceProfileService.upload_profile_to_flightbird.

Examples:
  - Simulate by profile id (will use assigned drones' unit_id and mission purpose mapping for detection_type):
      python manage.py simulate_upload_profile_to_flightbird --profile-id 123 --duration 30 --limit 1
"""

import json
from django.core.management.base import BaseCommand, CommandError

from surveillance.services.surveillance_profile_service import SurveillanceProfileService


class Command(BaseCommand):
    help = "Simulate record video + detect flow to inspect logs (no Flightbird upload)"

    def add_arguments(self, parser):
        parser.add_argument("--profile-id", type=int, required=True, help="Surveillance profile ID")
        parser.add_argument(
            "--duration",
            type=int,
            default=10,
            help="Duration seconds to wait before stopping (default: 10)",
        )
        parser.add_argument(
            "--wait-analysis",
            type=int,
            default=15,
            help="Seconds to wait after stopping so background detect can persist analysis_path (default: 15)",
        )
        parser.add_argument("--limit", type=int, help="Max number of streams to simulate (default: all assigned drones)")
        parser.add_argument("--pretty", action="store_true", help="Pretty print JSON result")

    def handle(self, *args, **options):
        profile_id = int(options.get("profile_id"))
        duration = int(options.get("duration") or 10)
        wait_analysis = int(options.get("wait_analysis") or 15)
        limit = options.get("limit")
        limit = int(limit) if limit is not None else None
        pretty = bool(options.get("pretty", False))

        self.stdout.write(self.style.SUCCESS("\n🚀 Starting simulation (record video + detect)\n"))
        self.stdout.write(f"- profile_id: {profile_id}\n")
        self.stdout.write(f"- duration: {duration}s\n")
        self.stdout.write(f"- wait_analysis: {wait_analysis}s\n")
        self.stdout.write(f"- limit: {limit}\n")

        try:
            result = SurveillanceProfileService.simulate_upload_profile_to_flightbird(
                profile_id=profile_id,
                duration_seconds=duration,
                limit=limit,
                wait_analysis_seconds=wait_analysis,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if pretty:
            payload = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            payload = json.dumps(result, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS("\n✅ Simulation finished. Result:\n"))
        self.stdout.write(payload)
        self.stdout.write(self.style.SUCCESS("\n\n🧪 Analysis file check (per stream):\n"))
        for item in (result or {}).get("items", []) or []:
            stream_id = item.get("stream_monitor_id")
            analysis_path = item.get("analysis_path")
            ok = bool(analysis_path)
            self.stdout.write(f"- stream_monitor_id={stream_id} analysis_path={analysis_path} has_analysis_file={ok}\n")
        self.stdout.write("\n")


