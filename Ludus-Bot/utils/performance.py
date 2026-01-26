"""
Performance optimization utilities for Ludus bot
Reduces latency and improves response times
"""
import json
import os
from functools import lru_cache
from datetime import datetime, timedelta

class ConfigCache:
    """Cache for JSON configurations to reduce file I/O"""
    
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(minutes=5)
    
    def get(self, file_path, default=None):
        """Get cached config or load from file"""
        now = datetime.now()
        
        # Check if cached and not expired
        if file_path in self._cache:
            cache_age = now - self._cache_time[file_path]
            if cache_age < self._cache_duration:
                return self._cache[file_path]
        
        # Load from file
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self._cache[file_path] = data
                    self._cache_time[file_path] = now
                    return data
        except Exception as e:
            print(f"[Cache] Error loading {file_path}: {e}")
        
        return default or {}
    
    def invalidate(self, file_path):
        """Invalidate cache for a specific file"""
        if file_path in self._cache:
            del self._cache[file_path]
            del self._cache_time[file_path]
    
    def clear(self):
        """Clear all caches"""
        self._cache.clear()
        self._cache_time.clear()

# Global cache instance
config_cache = ConfigCache()
