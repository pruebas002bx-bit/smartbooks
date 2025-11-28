import os
import sys
from flask import Flask, render_template, jsonify, request, session
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'smartbooks_secret_key_2025'

# --- CONEXIÓN ---
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url: return None
    try:
        return psycopg2.connect(url, sslmode='require')
    except:
        return None

# --- FALLBACK MOCK DATA (Por si no hay DB) ---
MOCK_DB = {
    "users": [{"username": "admin", "password": "Smartbooks2025*"}],
    "products": [],
    "schools": [],
    "editorials": []
}

# --- RUTAS VISTAS ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/<page_name>.html')
def serve_pages(page_name): return render_template(f'{page_name}.html')

# --- API LOGIN ---
@app.route('/api/admin/login', methods=['POST'])
def login():
    data = request.json
    password = data.get('password')
    conn = get_db_connection()
    
    if conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM admin_users WHERE username = 'admin'")
        user = cur.fetchone()
        conn.close()
        if user and user['password_hash'] == password:
            session['admin'] = True
            return jsonify({"success": True})
            
    # Fallback
    if MOCK_DB['users'][0]['password'] == password:
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

# --- API PRODUCTOS (Actualizada con DESCRIPTION) ---
@app.route('/api/products', methods=['GET', 'POST', 'DELETE'])
def api_products():
    conn = get_db_connection()
    
    if request.method == 'GET':
        if conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM products ORDER BY id DESC")
            res = cur.fetchall()
            conn.close()
            return jsonify(res)
        return jsonify(MOCK_DB['products'])
    
    # --- ADMIN ONLY ---
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        data = request.json
        if conn:
            cur = conn.cursor()
            # AQUI SE AGREGA LA DESCRIPCIÓN AL INSERT
            cur.execute(
                "INSERT INTO products (title, editorial, price, image_url, description) VALUES (%s, %s, %s, %s, %s)",
                (data['title'], data.get('editorial', ''), data['price'], data.get('image_url', ''), data.get('description', ''))
            )
            conn.commit()
            conn.close()
        else:
            data['id'] = len(MOCK_DB['products']) + 1
            MOCK_DB['products'].append(data)
        return jsonify({"success": True})

    if request.method == 'DELETE':
        pid = request.args.get('id')
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE id = %s", (pid,))
            conn.commit()
            conn.close()
        return jsonify({"success": True})

# --- API COLEGIOS ---
@app.route('/api/schools', methods=['GET', 'POST', 'DELETE'])
def api_schools():
    conn = get_db_connection()
    
    if request.method == 'GET':
        if conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM schools ORDER BY id DESC")
            schools = cur.fetchall()
            
            # Anidar Kits y Productos
            for school in schools:
                cur.execute("""
                    SELECT k.id, k.grade_name, k.price, 
                           (SELECT COUNT(*) FROM kit_items ki WHERE ki.kit_id = k.id) as book_count
                    FROM school_kits k 
                    WHERE k.school_id = %s
                """, (school['id'],))
                school['kits'] = cur.fetchall()
                
                for kit in school['kits']:
                    cur.execute("""
                        SELECT p.id, p.title, p.price, p.image_url 
                        FROM products p 
                        JOIN kit_items ki ON p.id = ki.product_id 
                        WHERE ki.kit_id = %s
                    """, (kit['id'],))
                    kit['products'] = cur.fetchall()

            conn.close()
            return jsonify(schools)
        return jsonify(MOCK_DB['schools'])
    
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        data = request.json
        if conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("INSERT INTO schools (name, city, logo_url) VALUES (%s, %s, %s) RETURNING id",
                        (data['name'], data.get('city', 'Bogotá'), data.get('logo_url', '')))
            new_id = cur.fetchone()['id']
            conn.commit()
            conn.close()
            return jsonify({"success": True, "id": new_id})
        return jsonify({"success": True})

    if request.method == 'DELETE':
        sid = request.args.get('id')
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM schools WHERE id = %s", (sid,))
            conn.commit()
            conn.close()
        return jsonify({"success": True})

# --- API KITS ---
@app.route('/api/kits', methods=['POST', 'DELETE'])
def api_kits():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.json
        action = data.get('action')
        
        if conn:
            cur = conn.cursor()
            if action == 'create_kit':
                cur.execute("INSERT INTO school_kits (school_id, grade_name, price) VALUES (%s, %s, %s)",
                            (data['school_id'], data['grade_name'], data['price']))
            elif action == 'add_item':
                cur.execute("INSERT INTO kit_items (kit_id, product_id) VALUES (%s, %s)",
                            (data['kit_id'], data['product_id']))
            elif action == 'remove_item':
                cur.execute("DELETE FROM kit_items WHERE kit_id = %s AND product_id = %s",
                            (data['kit_id'], data['product_id']))
            conn.commit()
            conn.close()
        return jsonify({"success": True})
    
    if request.method == 'DELETE':
        kid = request.args.get('id')
        if conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM school_kits WHERE id = %s", (kid,))
            conn.commit()
            conn.close()
        return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)