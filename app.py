from flask import Flask, request, jsonify, send_file, send_from_directory
import sqlite3, os, base64, uuid

app     = Flask(__name__)
DB      = 'store.db'
UPLOADS = 'uploads'
os.makedirs(UPLOADS, exist_ok=True)

# ── CREATE TABLES ─────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        price       INTEGER NOT NULL,
        category    TEXT    DEFAULT '',
        badge       TEXT    DEFAULT '',
        description TEXT    DEFAULT '',
        image       TEXT    DEFAULT '',
        created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS posts (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT NOT NULL,
        body    TEXT NOT NULL,
        image   TEXT DEFAULT '',
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    con.commit()
    con.close()

init_db()

# ── SERVE FRONTEND ────────────────────────────────────────
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS, filename)

# ── SAVE BASE64 IMAGE ─────────────────────────────────────
def save_image(b64_str):
    if not b64_str or not b64_str.startswith('data:image'):
        return ''
    try:
        ext      = b64_str.split(';')[0].split('/')[1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        data     = base64.b64decode(b64_str.split(',')[1])
        with open(os.path.join(UPLOADS, filename), 'wb') as f:
            f.write(data)
        return f"/uploads/{filename}"
    except Exception:
        return ''

def delete_image(path):
    if path:
        filepath = path.lstrip('/')
        if os.path.exists(filepath):
            os.remove(filepath)

# ══════════════════════════════════════════════════════════
#   PRODUCTS API
# ══════════════════════════════════════════════════════════

@app.route('/api/products', methods=['GET'])
def get_products():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute('SELECT * FROM products ORDER BY created DESC').fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/products', methods=['POST'])
def add_product():
    d     = request.json
    name  = d.get('name','').strip()
    price = d.get('price', 0)
    if not name or not price:
        return jsonify({'error': 'Name and price required'}), 400
    img_path = save_image(d.get('image',''))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        'INSERT INTO products (name,price,category,badge,description,image) VALUES (?,?,?,?,?,?)',
        (name, int(price), d.get('category',''), d.get('badge',''), d.get('description',''), img_path)
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return jsonify({'id': new_id, 'message': 'Product added'})

@app.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    d   = request.json
    con = sqlite3.connect(DB)
    if 'price' in d:
        con.execute('UPDATE products SET price=? WHERE id=?', (int(d['price']), pid))
    if 'name' in d:
        con.execute('UPDATE products SET name=? WHERE id=?', (d['name'], pid))
    con.commit()
    con.close()
    return jsonify({'message': 'Updated'})

@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    con = sqlite3.connect(DB)
    row = con.execute('SELECT image FROM products WHERE id=?', (pid,)).fetchone()
    if row: delete_image(row[0])
    con.execute('DELETE FROM products WHERE id=?', (pid,))
    con.commit()
    con.close()
    return jsonify({'message': 'Deleted'})

# ══════════════════════════════════════════════════════════
#   POSTS API
# ══════════════════════════════════════════════════════════

@app.route('/api/posts', methods=['GET'])
def get_posts():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute('SELECT * FROM posts ORDER BY created DESC').fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/posts', methods=['POST'])
def add_post():
    d     = request.json
    title = d.get('title','').strip()
    body  = d.get('body','').strip()
    if not title or not body:
        return jsonify({'error': 'Title and body required'}), 400
    img_path = save_image(d.get('image',''))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('INSERT INTO posts (title,body,image) VALUES (?,?,?)', (title, body, img_path))
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return jsonify({'id': new_id, 'message': 'Published'})

@app.route('/api/posts/<int:pid>', methods=['DELETE'])
def delete_post(pid):
    con = sqlite3.connect(DB)
    row = con.execute('SELECT image FROM posts WHERE id=?', (pid,)).fetchone()
    if row: delete_image(row[0])
    con.execute('DELETE FROM posts WHERE id=?', (pid,))
    con.commit()
    con.close()
    return jsonify({'message': 'Deleted'})

# ── MESSAGES / CHAT ────────────────────────────────────────
def ensure_messages_table():
    con = sqlite3.connect(DB)
    con.execute('''CREATE TABLE IF NOT EXISTS messages (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        sender   TEXT NOT NULL,
        text     TEXT NOT NULL,
        created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    con.commit()
    con.close()

ensure_messages_table()

@app.route('/api/messages/<username>', methods=['GET'])
def get_messages(username):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute('SELECT * FROM messages WHERE username=? ORDER BY created ASC', (username,)).fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/messages', methods=['POST'])
def send_message():
    d = request.json
    username = d.get('username','').strip()
    sender   = d.get('sender','').strip()
    text     = d.get('text','').strip()
    if not username or not sender or not text:
        return jsonify({'error': 'Missing fields'}), 400
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('INSERT INTO messages (username,sender,text) VALUES (?,?,?)', (username, sender, text))
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return jsonify({'id': new_id})

@app.route('/api/messages/conversations', methods=['GET'])
def get_conversations():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute('''
        SELECT username, MAX(created) as last_msg, COUNT(*) as count,
               SUM(CASE WHEN sender="user" THEN 1 ELSE 0 END) as unread
        FROM messages GROUP BY username ORDER BY last_msg DESC
    ''').fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/messages/<username>', methods=['DELETE'])
def delete_conversation(username):
    con = sqlite3.connect(DB)
    con.execute('DELETE FROM messages WHERE username=?', (username,))
    con.commit()
    con.close()
    return jsonify({'message': 'Deleted'})
    
# ── RUN ───────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n╔══════════════════════════════════════╗")
    print("║   Kamanzi's Vifaa — Server Running   ║")
    print("╠══════════════════════════════════════╣")
    print("║  Store  →  http://localhost:5000      ║")
    print("╚══════════════════════════════════════╝\n")
    app.run(debug=True, port=5000)
