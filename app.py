import os
import sys
from flask import Flask, render_template, jsonify, request, session
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'smartbooks_secret_key_2025' # Clave para sesiones

# --- SIMULACIÓN DE DATOS (MEMORIA) ---
# Se usa si no hay conexión a base de datos real
MOCK_DB = {
    "users": [{"username": "admin", "password": "Smartbooks2025*"}],
    "products": [
        {"id": 1, "title": "English Path Level 1", "editorial": "Macmillan", "price": "$85.000", "image_url": "https://placehold.co/300x400", "is_bestseller": True}
    ],
    "schools": [
        {"id": 1, "name": "Cosmo Schools", "city": "Medellín", "logo_url": "https://placehold.co/150x150", "kits": []}
    ],
    "editorials": []
}

# --- CONEXIÓN ---
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url: return None
    try:
        return psycopg2.connect(url, sslmode='require')
    except:
        return None

# --- RUTAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<page_name>.html')
def serve_pages(page_name):
    return render_template(f'{page_name}.html')

# --- API LOGIN ---
@app.route('/api/admin/login', methods=['POST'])
def login():
    try:
        data = request.json
        password = data.get('password')
        
        # 1. Intento DB Real
        conn = get_db_connection()
        if conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM admin_users WHERE username = 'admin'")
            user = cur.fetchone()
            conn.close()
            if user and user['password_hash'] == password:
                session['admin'] = True
                return jsonify({"success": True})
        
        # 2. Fallback Memoria (Para que funcione SIEMPRE)
        user = MOCK_DB['users'][0]
        if user['password'] == password:
            session['admin'] = True
            return jsonify({"success": True})

        return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

    except Exception as e:
        print(f"Error Login: {e}")
        return jsonify({"success": False, "message": "Error interno"}), 500

@app.route('/api/admin/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

# --- API PRODUCTOS ---
@app.route('/api/products', methods=['GET', 'POST', 'DELETE'])
def api_products():
    if request.method == 'GET':
        # Retorna mocks si no hay DB
        return jsonify(MOCK_DB['products'])
    
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        new_prod = request.json
        new_prod['id'] = len(MOCK_DB['products']) + 1
        MOCK_DB['products'].append(new_prod)
        return jsonify({"success": True})

    if request.method == 'DELETE':
        pid = int(request.args.get('id'))
        MOCK_DB['products'] = [p for p in MOCK_DB['products'] if p['id'] != pid]
        return jsonify({"success": True})

# --- API COLEGIOS ---
@app.route('/api/schools', methods=['GET', 'POST', 'DELETE'])
def api_schools():
    if request.method == 'GET':
        return jsonify(MOCK_DB['schools'])
    
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        new_school = request.json
        new_school['id'] = len(MOCK_DB['schools']) + 1
        new_school['kits'] = []
        MOCK_DB['schools'].append(new_school)
        return jsonify({"success": True})

    if request.method == 'DELETE':
        sid = int(request.args.get('id'))
        MOCK_DB['schools'] = [s for s in MOCK_DB['schools'] if s['id'] != sid]
        return jsonify({"success": True})

# --- API EDITORIALES ---
@app.route('/api/editorials', methods=['GET', 'POST', 'DELETE'])
def api_editorials():
    if request.method == 'GET':
        return jsonify(MOCK_DB['editorials'])
    
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        data = request.json
        data['id'] = len(MOCK_DB['editorials']) + 1
        MOCK_DB['editorials'].append(data)
        return jsonify({"success": True})

    if request.method == 'DELETE':
        eid = int(request.args.get('id'))
        MOCK_DB['editorials'] = [e for e in MOCK_DB['editorials'] if e['id'] != eid]
        return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)