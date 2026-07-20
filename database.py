import sqlite3
import json
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="rosebot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                warns INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                muted INTEGER DEFAULT 0,
                joined_date TEXT,
                last_active TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT,
                settings TEXT,
                total_messages INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                message_type TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captcha (
                user_id INTEGER,
                group_id INTEGER,
                code TEXT,
                expires_at TEXT,
                verified INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, group_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                keyword TEXT,
                response TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, last_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, now, now))
        
        conn.commit()
        conn.close()
    
    def update_user_activity(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
        conn.commit()
        conn.close()
    
    def warn_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET warns = warns + 1 WHERE user_id = ?', (user_id,))
        cursor.execute('SELECT warns FROM users WHERE user_id = ?', (user_id,))
        warns = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        return warns
    
    def reset_warns(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET warns = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_group_settings(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT settings FROM groups WHERE group_id = ?', (group_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return json.loads(result[0])
        return None
    
    def set_group_settings(self, group_id, group_name, settings):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        settings_json = json.dumps(settings)
        
        cursor.execute('''
            INSERT OR REPLACE INTO groups (group_id, group_name, settings, created_at)
            VALUES (?, ?, ?, ?)
        ''', (group_id, group_name, settings_json, now))
        
        conn.commit()
        conn.close()
    
    def log_message(self, group_id, user_id, message_type="text"):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO messages (group_id, user_id, message_type, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (group_id, user_id, message_type, now))
        
        cursor.execute('''
            UPDATE groups SET total_messages = total_messages + 1 WHERE group_id = ?
        ''', (group_id,))
        
        conn.commit()
        conn.close()
    
    def get_group_stats(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT total_messages FROM groups WHERE group_id = ?', (group_id,))
        total = cursor.fetchone()
        total_messages = total[0] if total else 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE group_id = ? AND date(timestamp) = ?
        ''', (group_id, today))
        today_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM messages WHERE group_id = ?
        ''', (group_id,))
        active_users = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_messages": total_messages,
            "today_messages": today_count,
            "active_users": active_users
        }
    
    def set_captcha(self, user_id, group_id, code, expires_at):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO captcha (user_id, group_id, code, expires_at, verified)
            VALUES (?, ?, ?, ?, 0)
        ''', (user_id, group_id, code, expires_at))
        
        conn.commit()
        conn.close()
    
    def verify_captcha(self, user_id, group_id, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, expires_at FROM captcha 
            WHERE user_id = ? AND group_id = ? AND verified = 0
        ''', (user_id, group_id))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, "No pending captcha"
        
        stored_code, expires_at = result
        now = datetime.now().isoformat()
        
        if now > expires_at:
            cursor.execute('DELETE FROM captcha WHERE user_id = ? AND group_id = ?', (user_id, group_id))
            conn.commit()
            conn.close()
            return False, "Captcha expired"
        
        if code != stored_code:
            conn.close()
            return False, "Wrong code"
        
        cursor.execute('UPDATE captcha SET verified = 1 WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        conn.commit()
        conn.close()
        return True, "Verified"
    
    def add_filter(self, group_id, keyword, response):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO filters (group_id, keyword, response)
            VALUES (?, ?, ?)
        ''', (group_id, keyword, response))
        
        conn.commit()
        conn.close()
    
    def get_filters(self, group_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT keyword, response FROM filters WHERE group_id = ?', (group_id,))
        results = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in results}
    
    def remove_filter(self, group_id, keyword):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM filters WHERE group_id = ? AND keyword = ?', (group_id, keyword))
        conn.commit()
        conn.close()

db = Database()
