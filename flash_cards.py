from __future__ import annotations

import os
import random
import sqlite3
import stat

from flask import flash
from flask import Flask
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_login import AnonymousUserMixin
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user
from flask_login import LoginManager
from flask_login import logout_user
from flask_login import UserMixin


# set up flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'development key'


class AnonymousUser(AnonymousUserMixin):
    def __init__(self):
        self.color_scheme = '0,0,0'
        self.light_scheme = 0


# set up Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
login_manager.anonymous_user = AnonymousUser

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


def create_hex_color():
    data = [hex(int(x)) for x in current_user.color_scheme.split(',')]
    return f'#{"".join(data)}'


@app.context_processor
def fill_jinja():
    return {
        'logged_in': current_user.is_authenticated,
        'user_color': current_user.color_scheme,
        'hex_user_color': create_hex_color(),
        'light_scheme': current_user.light_scheme,
    }


class User(UserMixin):
    def __init__(
            self,
            id: int,
            name: str,
            password: str,
            color_scheme: str,
            light_scheme: str,
    ) -> None:
        self.id = id
        self.name = name
        self.password = password
        self.color_scheme = color_scheme
        self.light_scheme = light_scheme

    @classmethod
    def get_user_by_name(cls, name: str) -> tuple[str, str]:
        query = '''\
            SELECT id, password, color_scheme, light_scheme
            FROM users
            WHERE username=?
        '''
        db = get_db('users.db')
        user = db.execute(query, (name,)).fetchone()
        print('name:', name, user, db)
        if user is None:
            return None
        return cls(user[0], name, *user[1:])

    @classmethod
    def get_user_by_id(cls, id_: str) -> tuple[str, str]:
        query = '''\
            SELECT id, password, color_scheme, light_scheme
            FROM users
            WHERE id=?
        '''
        db = get_db('users.db')
        user = db.execute(query, (id_,)).fetchone()
        print('id:', id_, user, db)
        if user is None:
            return None
        return cls(id_, *user)


@login_manager.user_loader
def load_user(id: str):
    return User.get_user_by_id(id)


@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('sets'))
    error = None
    if request.method == 'POST':
        user = User.get_user_by_name(request.form['username'])
        if user is None or request.form['password'] != user.password:
            error = 'Invalid username or password!'
        else:
            login_user(user)
            resp = make_response(redirect(url_for('sets')))
            resp.set_cookie('username', request.form['username'])
            return resp
    return render_template('login.html', error=error, thing2=True)


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
    tag_name = db.execute(
        'SELECT name FROM tags WHERE id=?', (tag_id,),
    ).fetchone()[0]
    resp = make_response(render_template('cards.html', cards=cards))
    resp.set_cookie('current_tag_id', tag_id)
    resp.set_cookie('current_tag_name', tag_name)
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
    db = get_db(f'{db_path}/{db_name}')
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    flash('Card deleted.')
    return redirect(url_for('cards'))


@app.route('/learn')
@login_required
def memorize():
    dickt = {
        '0': '1',
        '1': 'known=1',
        '2': 'known=0',
    }
    tag_id = request.cookies.get('current_tag_id')
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    ltype = request.args.get('ltype')
    db = get_db(f'{db_path}/{db_name}')
    cards = db.execute(
        'SELECT front,back,type FROM cards WHERE tag_id=? AND ?',
        (tag_id, dickt[ltype]),
    ).fetchall()
    if not cards:
        flash("You've learned all cards")
        return redirect(url_for('cards', current_tag_id=tag_id))
    return render_template(
        'memorize.html',
        card=random.choice(cards),
        ltype=ltype,
    )


@app.route('/learned')
@login_required
def mark_known():
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('username')
    card_id = request.args.get('card_id')
    ltype = request.args.get('ltype')
    db = get_db(f'{db_path}/{db_name}.db')
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()
    return redirect(url_for('memorize', ltype=ltype))


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
    resp = make_response(render_template('sets.html', dbs=dbs, thing2=True))
    resp.delete_cookie('current_set')
    resp.delete_cookie('current_tag_name')
    resp.delete_cookie('current_tag_id')
    return resp


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


@app.route('/sets/delete')
@login_required
def delete_set():
    db_path = request.cookies.get('username')
    db_name = request.form['name']
    try:
        os.remove(os.path.join(db_path, db_name + '.db'))
    except OSError:
        pass
    return redirect(url_for('sets'))


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
    return redirect(url_for('sets'))


@app.route('/sets/<name>')
@login_required
def set_overview(name):
    db_path = request.cookies.get('username')
    db_name = process_db_name(name) + '.db'
    db = get_db(f'{db_path}/{db_name}')
    tags = db.execute('SELECT id, name FROM tags').fetchall()
    resp = make_response(render_template('set_overview.html', tags=tags))
    resp.set_cookie('current_set', db_name)
    resp.delete_cookie('current_tag_name')
    resp.delete_cookie('current_tag_id')
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
    db = get_db(f'{db_path}/{db_name}')
    db.execute('Delete from tags where id =?', [request.form['tag_id']])
    db.commit()


@app.route('/tags/edit', methods=['PATCH'])
@login_required
def edit_tag():
    db_path = request.cookies.get('username')
    db_name = request.cookies.get('current_set')
    db = get_db(f'{db_path}/{db_name}')
    db.execute(
        'Update tags set name =? where id = ?', [
            request.form['tagName'], request.form['tag_id'],
        ],
    )
    db.commit()


# @app.route('/settings')
# @login_required
# def settings():
#     return render_template(
#         'settings.html',
#         username=current_user.name,
#         thing2=True
#     )
#
#
# @app.route('/settings/change-light', methods=['POST'])
# @login_required
# def change_lightscheme():
#     db_path = request.cookies.get('username')
#     db_name = request.cookies.get('current_set')
#     light_scheme = request.form.get('lightscheme')
#     db = get_db('users.db')
#     db.execute(
#         'UPDATE users SET light_scheme=? WHERE id=?',
#         (light_scheme, current_user.id)
#     )
#     db.commit()
#     return redirect(url_for('settings'))


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
