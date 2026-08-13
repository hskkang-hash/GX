"""
🧹 CLEAR CACHE COMMAND
Manual cache clearing for debugging and maintenance
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from common.universal_optimization import UniversalCacheManager
import redis
from django.conf import settings

class Command(BaseCommand):
    help = 'Clear cache manually - all types and systems'

    def add_arguments(self, parser):
        parser.add_argument('--django-cache', action='store_true', help='Clear Django cache only')
        parser.add_argument('--redis-cache', action='store_true', help='Clear Redis cache only')
        parser.add_argument('--universal-cache', action='store_true', help='Clear universal cache only')
        parser.add_argument('--measure-cache', action='store_true', help='Clear measure-related cache only')
        
        parser.add_argument('--system', type=str, choices=['core', 'guardianx', 'all'], default='all', help='Which system cache to clear')
        parser.add_argument('--pattern', type=str, help='Clear cache keys matching pattern')

    def handle(self, *args, **options):
        print("🧹 MANUAL CACHE CLEARING")
        print("=" * 30)

        cleared_total = 0

        # Default: clear all if no specific options
        if not any([options['django_cache'], options['redis_cache'], 
                   options['universal_cache'], options['measure_cache']]):
            options['django_cache'] = True
            options['redis_cache'] = True
            options['universal_cache'] = True
            options['unified_cache'] = True

        if options['django_cache']:
            cleared_total += self.clear_django_cache()

        if options['redis_cache']:
            cleared_total += self.clear_redis_cache(options['system'], options['pattern'])

        if options['universal_cache']:
            cleared_total += self.clear_universal_cache()

        if options['measure_cache']:
            cleared_total += self.clear_measure_cache()



        print(f"\n✅ SUMMARY:")
        print(f"   Total keys cleared: {cleared_total}")
        print(f"   Cache status: Fresh and clean! 🎉")

    def clear_django_cache(self):
        """Clear Django default cache"""
        print("\n🎯 CLEARING DJANGO CACHE:")
        try:
            cache.clear()
            print("   ✅ Django cache cleared successfully")
            return 1  # Approximation since cache.clear() doesn't return count
        except Exception as e:
            print(f"   ❌ Error clearing Django cache: {e}")
            return 0

    def clear_redis_cache(self, system='all', pattern=None):
        """Clear Redis cache directly"""
        print(f"\n🔴 CLEARING REDIS CACHE (System: {system}):")
        
        try:
            # Get Redis connection info from settings
            redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
            redis_port = getattr(settings, 'REDIS_PORT', 6379)
            redis_db = getattr(settings, 'REDIS_DB', 1)
            
            # Build Redis URL
            if redis_host.startswith('redis://'):
                redis_url = f"{redis_host}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            
            redis_client = redis.Redis.from_url(redis_url)
            
            # Define patterns to clear
            patterns = []
            if system == 'all' or system == 'core':
                patterns.append("core:*")
            if system == 'all' or system == 'guardianx':
                patterns.append("guardianx:*")
            if system == 'all':
                patterns.extend(["universal:*", "*cache*", "*measure*"])
            
            if pattern:
                patterns = [pattern]
                
            total_cleared = 0
            for pat in patterns:
                keys = redis_client.keys(pat)
                if keys:
                    deleted = redis_client.delete(*keys)
                    total_cleared += deleted
                    print(f"   🔑 Pattern '{pat}': {deleted} keys cleared")
                else:
                    print(f"   📭 Pattern '{pat}': No keys found")
            
            print(f"   ✅ Redis cache cleared: {total_cleared} keys")
            return total_cleared
            
        except Exception as e:
            print(f"   ❌ Error clearing Redis cache: {e}")
            return 0

    def clear_universal_cache(self):
        """Clear universal cache using built-in manager"""
        print(f"\n🌍 CLEARING UNIVERSAL CACHE:")
        
        try:
            cleared = UniversalCacheManager.force_refresh_cache("/")
            print(f"   ✅ Universal cache cleared: {cleared} keys")
            return cleared
        except Exception as e:
            print(f"   ❌ Error clearing universal cache: {e}")
            return 0

    def clear_measure_cache(self):
        """Clear measure-specific cache patterns"""
        print(f"\n📏 CLEARING MEASURE-SPECIFIC CACHE:")
        
        try:
            redis_client = self.get_redis_client()
            
            # Measure-specific patterns
            measure_patterns = [
                "*measure*",
                "*time_stops*", 
                "*dimensions*",
                "*weight*",
                "*terminal*sort*",
                "*device*measure*"
            ]
            
            total_cleared = 0
            for pattern in measure_patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    deleted = redis_client.delete(*keys)
                    total_cleared += deleted
                    print(f"   📐 Pattern '{pattern}': {deleted} keys cleared")
            
            print(f"   ✅ Measure cache cleared: {total_cleared} keys")
            return total_cleared
            
        except Exception as e:
            print(f"   ❌ Error clearing measure cache: {e}")
            return 0

    def get_redis_client(self):
        """Get Redis client connection"""
        redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
        redis_port = getattr(settings, 'REDIS_PORT', 6379)
        redis_db = getattr(settings, 'REDIS_DB', 1)
        
        if redis_host.startswith('redis://'):
            redis_url = f"{redis_host}/{redis_db}"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        return redis.Redis.from_url(redis_url)
