import json
import os
from typing import Dict, List, Tuple

class LeaderboardManager:
    def __init__(self, filename: str = "leaderboard_stats.json"):
        # Use persistent directory if available
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        self.filename = os.path.join(data_dir, filename)
        print(f"[LeaderboardManager] Loading stats from: {self.filename}")
        self.stats = self.load_stats()
    
    def load_stats(self) -> Dict:
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return {}
    
    def save_stats(self):
        with open(self.filename, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def get_server_stats(self, guild_id: int) -> Dict:
        guild_key = str(guild_id)
        if guild_key not in self.stats:
            self.stats[guild_key] = {
                "counting_peak": 0,
                "music_plays": 0,
                "pet_adoptions": 0,
                "gtn_wins": 0,
                "tod_uses": 0,
                "server_name": ""
            }
            self.save_stats()
        return self.stats[guild_key]
    
    def increment_stat(self, guild_id: int, stat_name: str, amount: int = 1, server_name: str = None):
        guild_key = str(guild_id)
        server_stats = self.get_server_stats(guild_id)
        
        if stat_name in server_stats:
            server_stats[stat_name] += amount
        
        if server_name:
            server_stats["server_name"] = server_name
        
        self.save_stats()
    
    def update_peak(self, guild_id: int, stat_name: str, value: int, server_name: str = None):
        guild_key = str(guild_id)
        server_stats = self.get_server_stats(guild_id)
        
        if stat_name in server_stats:
            if value > server_stats[stat_name]:
                server_stats[stat_name] = value
        
        if server_name:
            server_stats["server_name"] = server_name
        
        self.save_stats()
    
    def get_top_servers(self, stat_name: str, limit: int = 10) -> List[Tuple[str, str, int]]:
        sorted_servers = sorted(
            self.stats.items(),
            key=lambda x: x[1].get(stat_name, 0),
            reverse=True
        )
        
        top_servers = []
        for guild_id, data in sorted_servers[:limit]:
            stat_value = data.get(stat_name, 0)
            if stat_value > 0:
                server_name = data.get("server_name", f"Unknown Server ({guild_id})")
                top_servers.append((guild_id, server_name, stat_value))
        
        return top_servers

leaderboard_manager = LeaderboardManager()
