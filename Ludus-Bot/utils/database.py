
import os
import datetime
import logging
import sqlite3
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LudusDB")

# helper to adapt datetime objects to sqlite
def adapt_datetime(ts):
    return ts.isoformat()

def convert_datetime(ts):
    return datetime.datetime.fromisoformat(ts.decode())

sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        # Use a local SQLite file in the data/ folder
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "database.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections to ensure they are closed properly."""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path, 
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            conn.row_factory = sqlite3.Row # Enable name-based access
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            yield None
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, commit: bool = False):
        """Context manager for database cursors."""
        with self.get_connection() as conn:
            if conn is None:
                yield None
                return
                
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database query error: {e}")
                # Don't raise, just log, to keep bot running
                # raise 
            finally:
                cursor.close()

    def initialize_schema(self):
        """Create the necessary tables if they do not exist."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                total_commands INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                daily_longest_streak INTEGER DEFAULT 0,
                total_coins_earned INTEGER DEFAULT 0,
                total_coins_spent INTEGER DEFAULT 0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                stat_name TEXT NOT NULL,
                stat_value NUMERIC DEFAULT 0,
                UNIQUE(user_id, stat_name)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL,
                name TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS game_states (
                user_id INTEGER,
                game_name TEXT,
                state_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, game_name)
            );
            """
        ]
        
        with self.get_cursor(commit=True) as cursor:
            if cursor:
                for query in queries:
                    cursor.execute(query)
                logger.info("Database schema initialized successfully (SQLite).")

    def upsert_user(self, user_id: int, username: str):
        """Insert a new user or update connection details."""
        query = """
        INSERT INTO users (user_id, username, created_at, updated_at, last_active)
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            updated_at = CURRENT_TIMESTAMP,
            last_active = CURRENT_TIMESTAMP;
        """
        with self.get_cursor(commit=True) as cursor:
            if cursor:
                cursor.execute(query, (user_id, username))

    def update_stat(self, user_id: int, stat_name: str, value: Any, increment: bool = False):
        """Update or insert a specific stat for a user."""
        if increment:
            query = """
            INSERT INTO stats (user_id, stat_name, stat_value)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, stat_name) DO UPDATE SET
                stat_value = stats.stat_value + excluded.stat_value;
            """
        else:
            query = """
            INSERT INTO stats (user_id, stat_name, stat_value)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, stat_name) DO UPDATE SET
                stat_value = excluded.stat_value;
            """
            
        with self.get_cursor(commit=True) as cursor:
            if cursor:
                cursor.execute(query, (user_id, stat_name, value))

    def increment_stat(self, user_id: int, stat_name: str, amount: int = 1):
        """Increment a stat by a specific amount."""
        self.update_stat(user_id, stat_name, amount, increment=True)

    def log_activity(self, user_id: int, activity_type: str, activity_name: str, timestamp: Optional[str] = None):
        """Log a user activity."""
        if timestamp:
            query = """
            INSERT INTO activity (user_id, type, name, time)
            VALUES (?, ?, ?, ?);
            """
            params = (user_id, activity_type, activity_name, timestamp)
        else:
            query = """
            INSERT INTO activity (user_id, type, name)
            VALUES (?, ?, ?);
            """
            params = (user_id, activity_type, activity_name)
            
        with self.get_cursor(commit=True) as cursor:
            if cursor:
                cursor.execute(query, params)
            
    def increment_command_count(self, user_id: int):
        """Increment the command usage counter."""
        query = """
        UPDATE users SET total_commands = total_commands + 1 WHERE user_id = ?;
        """
        with self.get_cursor(commit=True) as cursor:
            if cursor:
                cursor.execute(query, (user_id,))
    
    def save_game_state(self, user_id: int, game_name: str, state_json: str):
        """Save a game state to the database."""
        query = """
        INSERT INTO game_states (user_id, game_name, state_json, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, game_name) DO UPDATE SET
            state_json = excluded.state_json,
            updated_at = CURRENT_TIMESTAMP;
        """
        with self.get_cursor(commit=True) as cursor:
            if cursor:
                cursor.execute(query, (user_id, game_name, state_json))

    def get_user_data(self, user_id: int) -> Dict:
        """Retrieve all data for a user including stats, simulating the JSON structure."""
        with self.get_cursor() as cursor:
            if not cursor:
                return {}

            # Get main user data
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {}
                
            # Get stats
            cursor.execute("SELECT stat_name, stat_value FROM stats WHERE user_id = ?", (user_id,))
            stats = cursor.fetchall()
            
            # Get game states
            cursor.execute("SELECT game_name, state_json FROM game_states WHERE user_id = ?", (user_id,))
            games = cursor.fetchall()

            # Format data to match old JSON structure somewhat
            user_data = dict(user)
            
            # Stats dictionary
            stats_dict = {s['stat_name']: float(s['stat_value']) for s in stats}
            user_data['stats'] = stats_dict
            
            # Games dictionary
            games_dict = {}
            import json
            for g in games:
                try:
                    games_dict[g['game_name']] = json.loads(g['state_json'])
                except:
                    games_dict[g['game_name']] = {}
            user_data['games'] = games_dict
            
            # Mock other structures if needed for compatibility
            user_data['minigames'] = {"by_game": {}, "recent_plays": []}
            user_data['activity'] = {"counts": {}, "by_name": {}, "recent": []}
            user_data['meta'] = {
                "created_at": str(user['created_at']),
                "updated_at": str(user['updated_at']),
                "last_active": str(user['last_active'])
            }
            
            return user_data

# Global instance
db = DatabaseManager()
