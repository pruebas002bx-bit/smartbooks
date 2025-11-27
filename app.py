import os
import sys
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_smartbooks') # Necesario para sesiones
PORT = int(os.environ.get('PORT', 5000))

# --- CONEXIÓN BASE DE DATOS ---
def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    try:
        conn = psycopg2.connect(database_url, sslmode='require')
        return conn
    except Exception as e:
        print(f"Error DB: {e}", file=sys.stderr)
        return None

# --- RUTAS PÚBLICAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<page_name>.html')
def serve_html_pages(page_name):
    # Protege la ruta admin si no está logueado
    if page_name == 'admin' and not session.get('logged_in'):
        return render_template('admin.html', show_login=True)
    return render_template(f'{page_name}.html')

# --- API ADMINISTRADOR (Login) ---
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get('password')
    
    # En un entorno real, usa hash (bcrypt). Aquí comparamos directo según tu requerimiento.
    # Si deseas cambiar la clave, actualiza la tabla admin_users
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM admin_users WHERE username = 'admin'")
    user = cur.fetchone()
    conn.close()

    if user and user['password_hash'] == password:
        session['logged_in'] = True
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Contraseña incorrecta"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/admin/change-password', methods=['POST'])
def change_password():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    new_password = data.get('new_password')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE admin_users SET password_hash = %s WHERE username = 'admin'", (new_password,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- API PRODUCTOS (Tienda y Bestsellers) ---
@app.route('/api/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_products():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'GET':
        cur.execute("SELECT * FROM products ORDER BY id DESC")
        data = cur.fetchall()
        conn.close()
        return jsonify(data)
    
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'POST': # Crear
        d = request.json
        cur.execute("INSERT INTO products (title, editorial, price, image_url, description, is_bestseller) VALUES (%s, %s, %s, %s, %s, %s)",
                    (d['title'], d['editorial'], d['price'], d['image_url'], d['description'], d['is_bestseller']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'PUT': # Editar
        d = request.json
        cur.execute("UPDATE products SET title=%s, editorial=%s, price=%s, image_url=%s, description=%s, is_bestseller=%s WHERE id=%s",
                    (d['title'], d['editorial'], d['price'], d['image_url'], d['description'], d['is_bestseller'], d['id']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE': # Borrar
        id = request.args.get('id')
        cur.execute("DELETE FROM products WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

# --- API COLEGIOS Y KITS ---
@app.route('/api/schools', methods=['GET', 'POST', 'DELETE'])
def manage_schools():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'GET':
        # Obtener colegios con sus kits anidados (JSON structure)
        cur.execute("""
            SELECT s.id, s.name, s.city, s.logo_url as img, 
            COALESCE(json_agg(k.*) FILTER (WHERE k.id IS NOT NULL), '[]') as kits
            FROM schools s
            LEFT JOIN kits k ON s.id = k.school_id
            GROUP BY s.id
        """)
        data = cur.fetchall()
        conn.close()
        return jsonify(data)

    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO schools (name, city, logo_url) VALUES (%s, %s, %s)", (d['name'], d['city'], d['img']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
        
    if request.method == 'DELETE':
        id = request.args.get('id')
        cur.execute("DELETE FROM schools WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

@app.route('/api/kits', methods=['POST', 'DELETE'])
def manage_kits():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO kits (school_id, grade_name, kit_name, price, book_count, description) VALUES (%s, %s, %s, %s, %s, %s)",
                    (d['school_id'], d['grade_name'], d['kit_name'], d['price'], d['book_count'], d['description']))
        conn.commit()
    
    if request.method == 'DELETE':
        id = request.args.get('id')
        cur.execute("DELETE FROM kits WHERE id = %s", (id,))
        conn.commit()
        
    conn.close()
    return jsonify({"success": True})

# --- API EDITORIALES ---
@app.route('/api/editorials', methods=['GET', 'POST', 'DELETE'])
def manage_editorials():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'GET':
        cur.execute("SELECT * FROM editorials")
        data = cur.fetchall()
        conn.close()
        return jsonify(data)

    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO editorials (name, logo_url) VALUES (%s, %s)", (d['name'], d['logo_url']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        id = request.args.get('id')
        cur.execute("DELETE FROM editorials WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)