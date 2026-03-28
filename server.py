"""
AI Smart Debugger - Flask Server with SQLite Database
Data syncs across all devices!
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DATABASE = 'ai_debugger.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            user_class TEXT,
            skill_level TEXT DEFAULT 'beginner',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_code TEXT,
            fixed_code TEXT,
            errors TEXT,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mistake TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER,
            message TEXT,
            sender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# User Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '')
    user_class = data.get('userClass', '')
    skill = data.get('skill', 'beginner')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO users (username, password_hash, name, user_class, skill_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password_hash, name, user_class, skill))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'user': {'id': user_id, 'username': username, 'name': name, 'skill': skill}
        })
    except:
        conn.close()
        return jsonify({'error': 'Username already exists'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', (username, password_hash))
    user = c.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'userClass': user['user_class'],
                'skill': user['skill_level']
            }
        })
    return jsonify({'error': 'Invalid credentials'}), 401

# Session Routes
@app.route('/api/sessions', methods=['POST'])
def save_session():
    data = request.json
    user_id = data.get('userId')
    original_code = data.get('originalCode', '')
    fixed_code = data.get('fixedCode', '')
    errors = data.get('errors', '')
    explanation = data.get('explanation', '')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO sessions (user_id, original_code, fixed_code, errors, explanation)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, original_code, fixed_code, errors, explanation))
    conn.commit()
    session_id = c.lastrowid
    conn.close()
    
    return jsonify({'success': True, 'sessionId': session_id})

@app.route('/api/sessions/<int:user_id>', methods=['GET'])
def get_sessions(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50
    ''', (user_id,))
    sessions = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(sessions)

# Mistakes Routes
@app.route('/api/mistakes', methods=['POST'])
def save_mistake():
    data = request.json
    user_id = data.get('userId')
    mistake = data.get('mistake', '')
    
    if not user_id or not mistake:
        return jsonify({'error': 'Required fields missing'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO mistakes (user_id, mistake) VALUES (?, ?)', (user_id, mistake))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/mistakes/<int:user_id>', methods=['GET'])
def get_mistakes(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM mistakes WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    mistakes = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(mistakes)

@app.route('/api/mistakes/<int:mistake_id>', methods=['DELETE'])
def delete_mistake(mistake_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM mistakes WHERE id = ?', (mistake_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Chat History Routes
@app.route('/api/chat', methods=['POST'])
def save_chat():
    data = request.json
    user_id = data.get('userId')
    session_id = data.get('sessionId')
    message = data.get('message', '')
    sender = data.get('sender', 'user')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_history (user_id, session_id, message, sender)
        VALUES (?, ?, ?, ?)
    ''', (user_id, session_id, message, sender))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/chat/<int:session_id>', methods=['GET'])
def get_chat(session_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at ASC
    ''', (session_id,))
    messages = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(messages)

# Delete All Data
@app.route('/api/delete-account/<int:user_id>', methods=['DELETE'])
def delete_account(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM mistakes WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'database': 'connected'})

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("AI Smart Debugger Server")
    print("=" * 60)
    print("Database: ai_debugger.db (SQLite)")
    print("Works on multiple devices!")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
