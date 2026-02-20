
import os
import datetime
import logging
from typing import Optional, Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PsyvrseDB")

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.host = os.getenv("DATABASE_HOST")
            cls._instance.database = os.getenv("DATABASE_NAME")
            cls._instance.user = os.getenv("DATABASE_USER")
            cls._instance.password = os.getenv("DATABASE_PASSWORD")
            cls._instance.port = os.getenv("DATABASE_PORT", "5432")
            cls._instance.connection = None
        return cls._instance

    @contextmanager
    def get_connection(self):
        """Context manager for database connections to ensure they are closed properly."""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, commit: bool = False):
        """Context manager for database cursors."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database query error: {e}")
                raise
            finally:
                cursor.close()

    def initialize_schema(self):
        """Create the necessary tables if they do not exist."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                total_commands INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                daily_longest_streak INTEGER DEFAULT 0,
                total_coins_earned BIGINT DEFAULT 0,
                total_coins_spent BIGINT DEFAULT 0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS stats (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                stat_name TEXT NOT NULL,
                stat_value NUMERIC DEFAULT 0,
                UNIQUE(user_id, stat_name)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS activity (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type TEXT NOT NULL,
                name TEXT NOT NULL
            );
            """
        ]
        
        with self.get_cursor(commit=True) as cursor:
            for query in queries:
                cursor.execute(query)
            logger.info("Database schema initialized successfully.")

    def upsert_user(self, user_id: int, username: str):
        """Insert a new user or update connection details."""
        query = """
        INSERT INTO users (user_id, username, created_at, updated_at, last_active)
        VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            updated_at = CURRENT_TIMESTAMP,
            last_active = CURRENT_TIMESTAMP;
        """
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(query, (user_id, username))

    def update_stat(self, user_id: int, stat_name: str, value: Any, increment: bool = False):
        """Update or insert a specific stat for a user."""
        if increment:
            query = """
            INSERT INTO stats (user_id, stat_name, stat_value)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, stat_name) DO UPDATE SET
                stat_value = stats.stat_value + EXCLUDED.stat_value;
            """
        else:
            query = """
            INSERT INTO stats (user_id, stat_name, stat_value)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, stat_name) DO UPDATE SET
                stat_value = EXCLUDED.stat_value;
            """
            
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(query, (user_id, stat_name, value))

    def log_activity(self, user_id: int, activity_type: str, activity_name: str):
        """Log a user activity."""
        query = """
        INSERT INTO activity (user_id, type, name)
        VALUES (%s, %s, %s);
        """
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(query, (user_id, activity_type, activity_name))
            
    def increment_command_count(self, user_id: int):
        """Increment the command usage counter."""
        query = """
        UPDATE users SET total_commands = total_commands + 1 WHERE user_id = %s;
        """
        with self.get_cursor(commit=True) as cursor:
            cursor.execute(query, (user_id,))
            
    def get_user_data(self, user_id: int) -> Optional[Dict]:
        """Retrieve all data for a user including stats."""
        with self.get_cursor() as cursor:
            # Get main user data
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return None
                
            # Get stats
            cursor.execute("SELECT stat_name, stat_value FROM stats WHERE user_id = %s", (user_id,))
            stats = cursor.fetchall()
            
            user['stats'] = {s['stat_name']: s['stat_value'] for s in stats}
            return user

# Global instance for easy import
db = DatabaseManager()

if __name__ == "__main__":
    # Ensure env vars are loaded if running directly
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Testing DB Connection...")
    try:
        db.initialize_schema()
        print("Schema initialized.")
        
        # Test User
        test_id = 123456789
        db.upsert_user(test_id, "TestUser")
        print("User upserted.")
        
        db.update_stat(test_id, "test_stat", 10)
        db.update_stat(test_id, "test_stat", 5, increment=True)
        print("Stats updated.")
        
        db.log_activity(test_id, "command", "test_cmd")
        print("Activity logged.")
        
        data = db.get_user_data(test_id)
        print(f"Retrieved Data: {data}")
        
    except Exception as e:
        print(f"Failed: {e}")
