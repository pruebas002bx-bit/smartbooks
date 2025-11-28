import os
import sys
from flask import Flask, render_template, jsonify, request, session
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'smartbooks_secret_key_2025'

def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url: return None
    try:
        return psycopg2.connect(url, sslmode='require')
    except:
        return None

# --- RUTAS PRINCIPALES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/<page_name>.html')
def serve_pages(page_name): return render_template(f'{page_name}.html')

# --- LOGIN ---
@app.route('/api/admin/login', methods=['POST'])
def login():
    data = request.json
    # En producción usar hash (bcrypt), aquí texto plano para demo
    password = data.get('password')
    if password == "Smartbooks2025*": # Contraseña quemada o verificar en DB
        session['admin'] = True
        return jsonify({"success": True})
    
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM admin_users WHERE username = 'admin'")
        user = cur.fetchone()
        conn.close()
        if user and user['password_hash'] == password:
            session['admin'] = True
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

# --- API PRODUCTOS ---
@app.route('/api/products', methods=['GET', 'POST', 'DELETE'])
def api_products():
    conn = get_db_connection()
    if not conn: return jsonify([])

    if request.method == 'GET':
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id DESC")
        res = cur.fetchall()
        conn.close()
        return jsonify(res)

    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'POST':
        data = request.json
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (title, editorial, price, image_url, description) VALUES (%s, %s, %s, %s, %s)",
            (data['title'], data.get('editorial', ''), data['price'], data.get('image_url', ''), data.get('description', ''))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        pid = request.args.get('id')
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

# --- API COLEGIOS (CORREGIDA) ---
@app.route('/api/schools', methods=['GET', 'POST', 'DELETE'])
def api_schools():
    conn = get_db_connection()
    if not conn: return jsonify([])

    if request.method == 'GET':
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # 1. Traer colegios
        cur.execute("SELECT * FROM schools ORDER BY id DESC")
        schools = cur.fetchall()
        
        # 2. Estructura anidada robusta: Colegio -> Kits -> Productos
        for school in schools:
            cur.execute("""
                SELECT k.id, k.grade_name, k.price, k.discount, k.description,
                       (SELECT COUNT(*) FROM kit_items ki WHERE ki.kit_id = k.id) as book_count
                FROM school_kits k 
                WHERE k.school_id = %s ORDER BY k.grade_name
            """, (school['id'],))
            school['kits'] = cur.fetchall()
            
            for kit in school['kits']:
                cur.execute("""
                    SELECT p.id, p.title, p.price, p.image_url, p.editorial 
                    FROM products p 
                    JOIN kit_items ki ON p.id = ki.product_id 
                    WHERE ki.kit_id = %s
                """, (kit['id'],))
                kit['products'] = cur.fetchall()

        conn.close()
        return jsonify(schools)

    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'POST':
        data = request.json
        cur = conn.cursor()
        # CORRECCIÓN: Asegurar que logo_url se guarda
        cur.execute("INSERT INTO schools (name, city, logo_url) VALUES (%s, %s, %s)",
                    (data['name'], data.get('city', ''), data.get('logo_url', '')))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        sid = request.args.get('id')
        cur = conn.cursor()
        cur.execute("DELETE FROM schools WHERE id = %s", (sid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

# --- API KITS (CORREGIDA) ---
@app.route('/api/kits', methods=['POST', 'DELETE'])
def api_kits():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500

    if request.method == 'POST':
        data = request.json
        action = data.get('action')
        cur = conn.cursor()

        if action == 'create_kit':
            # CORRECCIÓN: Insertar descuento y descripción
            cur.execute("""
                INSERT INTO school_kits (school_id, grade_name, price, discount, description) 
                VALUES (%s, %s, %s, %s, %s)
            """, (data['school_id'], data['grade_name'], data['price'], data.get('discount', 0), data.get('description', '')))
        
        elif action == 'add_item':
            # Insertar producto en kit ignorando duplicados
            cur.execute("INSERT INTO kit_items (kit_id, product_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (data['kit_id'], data['product_id']))
        
        elif action == 'remove_item':
            cur.execute("DELETE FROM kit_items WHERE kit_id = %s AND product_id = %s",
                        (data['kit_id'], data['product_id']))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        kid = request.args.get('id')
        cur = conn.cursor()
        cur.execute("DELETE FROM school_kits WHERE id = %s", (kid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)