from __future__ import annotations

import secrets
import sqlite3


def main():
    db = sqlite3.connect('users.db')
    c = db.cursor()
    with open('data/users_schema.sql')as f:
        c.executescript(f.read())
        db.commit()
    while True:
        username = input('Enter username: ')
        if username == 'exit':
            break
        password = secrets.token_urlsafe(15)
        c.execute(
            'INSERT INTO users (username, password) VALUES (?,?)',
            (username, password),
        )
        db.commit()
