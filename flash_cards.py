from __future__ import annotations

import os
import sqlite3
import stat

from flask import flash
from flask import Flask
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user
from flask_login import LoginManager
from flask_login import logout_user
from flask_login import UserMixin


# set up flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'development key'

# set up Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# store open db connections
OPEN_CONNECTIONS = {}


def connect_db(name: str) -> sqlite3.Connection:
    rv = sqlite3.connect(name, check_same_thread=False)
    rv.row_factory = sqlite3.Row
    return rv


def get_db(name: str) -> sqlite3.Connection:
    try:
        return OPEN_CONNECTIONS[name]
    except KeyError:
        OPEN_CONNECTIONS[name] = connect_db(name)
        with open('data/schema.sql') as f:
            OPEN_CONNECTIONS[name].executescript(f.read())
            OPEN_CONNECTIONS[name].commit()
        return OPEN_CONNECTIONS[name]


def process_db_name(name: str, to_user: bool = False) -> str:
    if to_user:
        return name.replace('_', ' ')
    return name.replace(' ', '_')


@app.template_filter()
def pretty_set_name(name: str):
    return process_db_name(name, to_user=True).replace('.db', '')


@app.template_filter()
def half_pretty_set_name(name: str):
    return name.replace('.db', '')


@app.context_processor
def logged_in():
    return {'logged_in': current_user.is_authenticated}


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
        print(name, user, db)
        return cls(user[0], name, user[1])

    @classmethod
    def get_user_by_id(cls, id_: str) -> tuple[str, str]:
        db = get_db('users.db')
        user = db.execute(
            'SELECT username, password FROM users WHERE id=?', (id_,),
        ).fetchone()
        print(id_, user, db)
        return cls(id_, *user)


@login_manager.user_loader
def load_user(id: str):
    return User.get_user_by_id(id)


@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('sets'))
    error = None
    if request.method == 'POST':
        user = User.get_user_by_name(request.form['username'])
        print(user.is_authenticated)
        if user is None or request.form['password'] != user.password:
            error = 'Invalid username or password!'
        else:
            login_user(user)
            resp = make_response(redirect(url_for('sets')))
            resp.set_cookie('username', request.form['username'])
            return resp
    return render_template('login.html', error=error)


@app.route('/cards')
@login_required
def cards():
    query = '''
        SELECT *
        FROM cards where tag_id=?
        ORDER BY id DESC
    '''
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    tag_id = request.args.get('current_tag_id')
    db = get_db(f'{db_path}/{db_name}')
    cards = db.execute(query, (tag_id,)).fetchall()
    resp = make_response(render_template('cards.html', cards=cards))
    resp.set_cookie('current_tag_id', tag_id)
    return resp


@app.route('/cards/add', methods=['POST'])
@login_required
def add_card():
    # TODO: consider programming_language?
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    tag_id = request.cookies.get('current_tag_id')
    db = get_db(f'{db_path}/{db_name}')
    db.execute(
        '''INSERT INTO cards (type, front, back, tag_id)
            VALUES (?,?,?,?)''',
        (
            request.form['type'], request.form['front'],
            request.form['back'], tag_id,
        ),
    )
    db.commit()
    flash('New card was successfully added.')
    return redirect(url_for('cards', current_tag_id=tag_id))


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
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}')
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
    return redirect(
        url_for(
            'cards',
            current_tag_id=request.cookies.get('current_tag_id'),
        ),
    )


@app.route('/cards/delete', methods=['POST'])
@login_required
def delete(card_id):
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('username')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    flash('Card deleted.')
    return redirect(url_for('cards'))


@app.route('/learn')
@login_required
def memorize():
    tag_id = request.cookies.get('tag_id')
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('username')
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
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('username')
    card_id = int(request.form['card_id'])
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()


@app.route('/sets')
@login_required
def sets():
    db_path = request.cookies.get('username')
    os.makedirs(db_path, exist_ok=True)
    os.chmod(db_path, stat.S_IRWXU)
    print(os.listdir(db_path), db_path)
    dbs = [
        f for f in os.listdir(
            db_path,
        ) if os.path.isfile(os.path.join(db_path, f)) and f.endswith('.db')
    ]
    print(dbs)
    return render_template('sets.html', dbs=dbs)


@app.route('/sets/add', methods=['POST'])
@login_required
def add_set():
    db_path = request.cookies.get('username')
    db_name = request.form['name']
    open(os.path.join(db_path, process_db_name(db_name) + '.db'), 'a').close()
    os.chmod(
        os.path.join(
            db_path, process_db_name(
                db_name,
            ) + '.db',
        ), stat.S_IRWXU,
    )
    return redirect(url_for('sets'))


@app.route('/sets/delete', methods=['DELETE'])
@login_required
def delete_set():
    db_path = request.cookies.get('username')
    db_name = request.form['name']
    try:
        os.remove(os.path.join(db_path, db_name + '.db'))
    except OSError:
        pass


@app.route('/sets/edit', methods=['PATCH'])
@login_required
def edit_set():
    db_path = request.cookies.get('username')
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
    db_path = request.cookies.get('username')
    db_name = process_db_name(name) + '.db'
    db = get_db(f'{db_path}/{db_name}')
    tags = db.execute('SELECT id, name FROM tags').fetchall()
    resp = make_response(render_template('set_overview.html', tags=tags))
    resp.set_cookie('current_set', db_name)
    return resp


@app.route('/tags/add', methods=['POST'])
@login_required
def add_tag():
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}')
    db.execute(
        'INSERT INTO tags (name) VALUES (?)',
        [request.form['tagName']],
    )
    db.commit()
    return redirect(
        url_for(
            'set_overview',
            name=process_db_name(db_name, to_user=True).replace('.db', ''),
        ),
    )


@app.route('/tags/delete', methods=['DELETE'])
@login_required
def delete_tag():
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('Delete from tags where id =?', [request.form['tag_id']])
    db.commit()


@app.route('/tags/edit', methods=['PATCH'])
@login_required
def edit_tag():
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute(
        'Update tags set name =? where id = ?', [
            request.form['tagName'], request.form['tag_id'],
        ],
    )
    db.commit()


@app.route('/settings')
@login_required
def settings():
    return 'Hello World...'


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', debug=True)
    except BaseException:
        for connection in OPEN_CONNECTIONS.values():
            connection.close()
