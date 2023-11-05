from __future__ import annotations

import enum
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


app = Flask(__name__)
nameDB = 'None'
pathDB = 'db'


class CardTypes(enum.Enum):
    TEXT = 0
    CODE = 1
    MATH = 2


def load_config():
    app.config.update(
        dict(
            SECRET_KEY='development key',
        ),
    )


def connect_db():
    rv = sqlite3.connect('users.db')
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('cards'))
    else:
        return redirect(url_for('login'))


@app.route('/cards')
def cards():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    query = '''
        SELECT *
        FROM cards where tag_id = ?
        ORDER BY id DESC
    '''
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    tag_id = int(request.args.get('tag_id'))
    db = sqlite3.connect(os.path.join(db_path, db_name))
    c = db.cursor()
    c.execute(query, (tag_id,))

    return render_template(
        'cards.html',
        cards=cards,
    )


@app.route('/cards/add', methods=['POST'])
def add_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    tag_id = flask.cookies.get('tag_id')
    db = sqlite3.connect(os.path.join(db_path, db_name))
    c = db.cursor()
    c.execute(
        '''insert into cards (type, front, back, known, tag_id)
            values (?,?,?,?,?)''',
        (
            request.form['type'], request.form['front'],
            request.form['back'], request.form['known'], tag_id,
        ),
    )
    db.commit()
    flash('New card was successfully added.')
    return redirect(url_for('cards'))


@app.route('/cards/edit', methods=['POST'])
def edit_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
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
    db_name = flask.cookies.get('username')
    db = sqlite3.connect(os.path.join(db_path, db_name))
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
def delete(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    db = sqlite3.connect(os.path.join(db_path, db_name))
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    flash('Card deleted.')
    return redirect(url_for('cards'))


@app.route('/learn')
def memorize():

    tag_id = flask.cookies.get('tag_id')
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    db = sqlite3.connect(os.path.join(db_path, db_name))
    cards = db.execute(
        'SELECT front,back,type FROM cards WHERE tag_id = ?', [
            tag_id,
        ],
    ).fetchall()
    db.commit()
    return render_template('memorize.html', cards=cards)


@app.route('/learned', methods=['POST'])
def mark_known():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('username')
    card_id = int(request.form['card_id'])
    db = sqlite3.connect(os.path.join(db_path, db_name))
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()


@app.route('/login', methods=['GET', 'POST'])
def login():
    userdata = g.sqlite_db.execute(
        'select username, password from users where username =?', (
            request.form['username'],
        ),
    ).fetchone()
    error = None
    if request.method == 'POST':
        if (
                userdata is None
                or request.form['password'] != userdata[1]
        ):
            error = 'Invalid username or password!'
        else:
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You've logged out")
    return redirect(url_for('index'))


@app.route('/sets')
def sets():
    db_path = flask.cookies.get('username')
    dbs = [
        f for f in os.listdir(
            db_path,
        ) if os.path.isfile(os.path.join(db_path, f) and f.endswith('.db'))
    ]
    return render_template('sets.html', dbs=dbs)


@app.route('/sets/add', methods=['POST'])
def add_set():
    db_path = flask.cookies.get('username')
    db_name = request.form['name']
    open(os.path.join(db_path, db_name + '.db'), 'a').close()


@app.route('/sets/delete', methods=['DELETE'])
def delete_set():
    db_path = flask.cookies.get('username')
    db_name = request.form['name']
    try:
        os.remove(os.path.join(db_path, db_name + '.db'))
    except OSError:
        pass


@app.route('/sets/edit', methods=['PATCH'])
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
def set_overview(name):
    db_path = flask.cookies.get('username')
    db_name = name + '.db'
    db = sqlite3.connect(os.path.join(db_path, db_name))
    c = db.cursor()
    tags = c.execute('SELECT id, name FROM tags').fetchall()
    return render_template('set_overview.html', tags=tags)


@app.route('/tags/add', methods=['POST'])
def add_tag():
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = sqlite3.connect(os.path.join(db_path, db_name))
    c = db.cursor()
    c.execute(
        'INSERT INTO tags (tagName) VALUES (?)',
        [request.form['tagName']],
    )
    db.commit()


@app.route('/tags/delete', methods=['DELETE'])
def delete_tag():
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = sqlite3.connect(os.path.join(db_path, db_name))
    c = db.cursor()
    c.execute('Delete from tags where id =?', [request.form['tag_id']])
    db.commit()


@app.route('/tags/edit', methods=['PATCH'])
def edit_tag():
    db_path = flask.cookies.get('username')
    db_name = flask.cookies.get('current_set')
    db = sqlite3.connect(os.path.join(db_path, db_name))
    c = db.cursor()
    c.execute(
        'Update tags set name =? where id = ?', [
            request.form['tagName'], request.form['tag_id'],
        ],
    )
    db.commit()


if __name__ == '__main__':
    load_config()
    app.run(host='0.0.0.0', debug=True)
