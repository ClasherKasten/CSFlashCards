from __future__ import annotations

import os
import sqlite3

import flask
from flask import flash
from flask import Flask
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask_login import login_required
from flask_login import login_user
from flask_login import LoginManager
from flask_login import UserMixin


# set up flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'development key'

# set up Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# store open db connections
OPEN_CONNECTIONS = []


def connect_db(name: str) -> sqlite3.Connection:
    rv = sqlite3.connect(name)
    OPEN_CONNECTIONS.append(name)
    rv.row_factory = sqlite3.Row
    return rv


def get_db(name: str) -> sqlite3.Connection:
    if not hasattr(g, name):
        setattr(g, name, connect_db(name))
    return getattr(g, name)


def process_db_name(name: str, to_user: bool = False) -> str:
    if to_user:
        return name.replace(' ', '_')
    else:
        return name.replace('_', ' ')


class User(UserMixin):
    def __init__(self, id: int, name: str, password: str) -> None:
        self.id = id
        self.name = name
        self.password = password

    @classmethod
    def get_user_by_name(cls, name: str) -> tuple[str, str]:
        db = get_db('users.db')
        user = db.execute(
            'SELECT id, password FROM users WHERE username=?', (name,),
        ).fetchone()
        return cls(user[0], name, user[1])


@login_manager.user_loader
def load_user(user_name: str):
    return User.get_user_by_name(user_name)


@app.teardown_appcontext
def close_db(error):
    for connection in OPEN_CONNECTIONS:
        getattr(g, connection).close()


@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = User.get_user_by_name(request.form['username'])
        if user is None or request.form['password'] != user.password:
            error = 'Invalid username or password!'
        else:
            login_user(user)
            flask.cookies['username'] = request.form['username']
            return redirect(url_for('sets'))
    return render_template('login.html', error=error)


@app.route('/cards')
@login_required
def cards():
    query = '''
        SELECT *
        FROM cards where tag_id=?
        ORDER BY id DESC
    '''
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    tag_id = int(request.args.get('current_tag_id'))
    flask.cookies['current_tag_id'] = tag_id
    db = get_db(f'{db_path}/{process_db_name(db_name)}.db')
    cards = db.execute(query, (tag_id,)).fetchall()
    return render_template('cards.html', cards=cards)


@app.route('/cards/add', methods=['POST'])
@login_required
def add_card():
    # TODO: consider programming_language?
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    tag_id = int(flask.cookies.get('current_tag_id'))
    db = get_db(f'{db_path}/{process_db_name(db_name)}.db')
    db.execute(
        '''INSERT INTO cards (type, front, back, known, tag_id)
            VALUES (?,?,?,?,?)''',
        (
            request.form['type'], request.form['front'],
            request.form['back'], request.form['known'], tag_id,
        ),
    )
    db.commit()
    flash('New card was successfully added.')
    return redirect(url_for('cards'))


@app.route('/cards/edit', methods=['POST'])
@login_required
def edit_card():
    command = '''
        UPDATE cards
        SET
          type = ?,
          front = ?,
          back = ?,
          known = ?
        WHERE id = ?
    '''
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = get_db(f'{db_path}/{process_db_name(db_name)}.db')
    db.execute(
        command,
        [
            request.form['type'],
            request.form['front'],
            request.form['back'],
            request.form['known'],
            request.form['card_id'],
        ],
    )
    db.commit()
    flash('Card saved.')
    return redirect(url_for('cards'))


@app.route('/cards/delete', methods=['POST'])
@login_required
def delete(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    flash('Card deleted.')
    return redirect(url_for('cards'))


@app.route('/learn')
@login_required
def memorize():
    tag_id = flask.cookies.get('tag_id')
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    db = get_db(f'{db_path}/{db_name}.db')
    cards = db.execute(
        'SELECT front,back,type FROM cards WHERE tag_id = ?', [
            tag_id,
        ],
    ).fetchall()
    db.commit()
    return render_template('memorize.html', cards=cards)


@app.route('/learned', methods=['POST'])
@login_required
def mark_known():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    card_id = int(request.form['card_id'])
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()


@app.route('/sets')
@login_required
def sets():
    db_path = flask.cookies.get('username')
    dbs = [
        f for f in os.listdir(
            db_path,
        ) if os.path.isfile(os.path.join(db_path, f) and f.endswith('.db'))
    ]
    return render_template('sets.html', dbs=dbs)


@app.route('/sets/add', methods=['POST'])
@login_required
def add_set():
    db_path = flask.cookies.get('username')
    db_name = request.form['name']
    open(os.path.join(db_path, db_name + '.db'), 'a').close()


@app.route('/sets/delete', methods=['DELETE'])
@login_required
def delete_set():
    db_path = flask.cookies.get('username')
    db_name = request.form['name']
    try:
        os.remove(os.path.join(db_path, db_name + '.db'))
    except OSError:
        pass


@app.route('/sets/edit', methods=['PATCH'])
@login_required
def edit_set():
    db_path = flask.cookies.get('username')
    old_db_name = request.form['old_name']
    new_db_name = request.form['new_name']
    try:
        os.rename(
            os.path.join(db_path, old_db_name + '.db'),
            os.path.join(db_path, new_db_name + '.db'),
        )
    except OSError:
        pass


@app.route('/sets/<name>')
@login_required
def set_overview(name):
    db_path = flask.cookies.get('username')
    db_name = name + '.db'
    flask.cookies['current_set'] = db_name
    db = get_db(f'{db_path}/{db_name}.db')
    tags = db.execute('SELECT id, name FROM tags').fetchall()
    return render_template('set_overview.html', tags=tags)


@app.route('/tags/add', methods=['POST'])
@login_required
def add_tag():
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute(
        'INSERT INTO tags (tagName) VALUES (?)',
        [request.form['tagName']],
    )
    db.commit()


@app.route('/tags/delete', methods=['DELETE'])
@login_required
def delete_tag():
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('Delete from tags where id =?', [request.form['tag_id']])
    db.commit()


@app.route('/tags/edit', methods=['PATCH'])
@login_required
def edit_tag():
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute(
        'Update tags set name =? where id = ?', [
            request.form['tagName'], request.form['tag_id'],
        ],
    )
    db.commit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
