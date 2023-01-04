import sqlite3
import os

import bcrypt
import dotenv


dotenv.load_dotenv()
SALT = os.getenv('SALT')


with sqlite3.connect('bot.db') as con:
    CREATE_USER_TABLE = """CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER UNIQUE,
        username VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        is_logged_in INTEGER NOT NULL DEFAULT 0 
    )"""

    cur = con.cursor()
    cur.execute(CREATE_USER_TABLE)


class DBClient:
    CREATE_USER = """INSERT INTO user (username, password) VALUES (?, ?)"""
    GET_USER = """SELECT id, username, password FROM user WHERE username = ?"""
    CHECK_LOGGED_IN = """SELECT is_logged_in FROM user WHERE id = ?"""
    UPDATE_IS_LOGGED_IN = """UPDATE user SET is_logged_in = 1 WHERE id = ?"""
    UPDATE_CHAT_ID = """UPDATE user SET chat_id = ? WHERE id = ?"""

    def create_user(self, username, password):
        password = bcrypt.hashpw(password.encode(), SALT.encode())

        with sqlite3.connect('bot.db') as con:
            cur = con.cursor()
            cur.execute(self.CREATE_USER, (username, password))

    def check_username(self, username):
        with sqlite3.connect('bot.db') as con:
            cur = con.cursor()
            cur.execute(self.GET_USER, (username, ))

        return cur.fetchall()

    def check_password(self, username, password):
        user = self.check_username(username)
        if not user:
            return False

        user_id = user[0][0]
        user_password = user[0][2]

        is_valid = bcrypt.checkpw(password.encode(), user_password)
        if not is_valid:
            return False

        return user_id

    def is_logged_in(self, user_id):
        with sqlite3.connect('bot.db') as con:
            cur = con.cursor()
            cur.execute(self.CHECK_LOGGED_IN, (user_id, ))

        return cur.fetchone()[0]

    def log_in(self, user_id, chat_id):
        if not self.is_logged_in(user_id):
            with sqlite3.connect('bot.db') as con:
                cur = con.cursor()
                cur.execute(self.UPDATE_IS_LOGGED_IN, (user_id,))
                cur.execute(self.UPDATE_CHAT_ID, (chat_id, user_id))
