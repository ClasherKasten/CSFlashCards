from __future__ import annotations

import sqlite3
# import secrets


def main():
    db = sqlite3.connect('users.db')
    c = db.cursor()
    with open('data/users_schema.sql')as f:
        c.executescript(f.read())
        db.commit()
    while True:
        username = input('Enter username: ').replace('\n', '')
        if username == 'exit':
            break
        password = 'tinf23ai2'
        print(password)
        c.execute(
            'INSERT INTO users (username, password) VALUES (?,?)',
            (username, password),
        )
        db.commit()


if __name__ == '__main__':
    raise SystemExit(main())
