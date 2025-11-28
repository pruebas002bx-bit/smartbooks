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
    if not url:
        print("Error: DATABASE_URL no configurada.")
        return None
    try:
        return psycopg2.connect(url)
    except Exception as e:
        print(f"Error conectando a DB: {e}")
        return None

@app.route('/')
def index(): return render_template('index.html')

@app.route('/<page_name>.html')
def serve_pages(page_name): return render_template(f'{page_name}.html')

@app.route('/api/admin/login', methods=['POST'])
def login():
    data = request.json
    password = data.get('password')
    if password == "Smartbooks2025*":
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

# --- API PRODUCTOS (Existente) ---
@app.route('/api/products', methods=['GET', 'POST', 'DELETE'])
def api_products():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB Connection failed"}), 500
    try:
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM products ORDER BY id DESC")
            res = cur.fetchall()
            return jsonify(res)
        if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
        if request.method == 'POST':
            data = request.json
            cur = conn.cursor()
            cur.execute("INSERT INTO products (title, editorial, price, image_url, description) VALUES (%s, %s, %s, %s, %s)",
                        (data['title'], data.get('editorial', ''), float(data['price']), data.get('image_url', ''), data.get('description', '')))
            conn.commit()
            return jsonify({"success": True})
        if request.method == 'DELETE':
            pid = request.args.get('id')
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE id = %s", (pid,))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error API Products: {e}")
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# --- API COLEGIOS (Existente) ---
@app.route('/api/schools', methods=['GET', 'POST', 'DELETE'])
def api_schools():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB Connection failed"}), 500
    try:
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, name, logo_url FROM schools ORDER BY id DESC")
            schools = cur.fetchall()
            for school in schools:
                cur.execute("SELECT k.id, k.grade_name, k.price, k.discount, k.description FROM school_kits k WHERE k.school_id = %s ORDER BY k.grade_name", (school['id'],))
                school['kits'] = cur.fetchall()
                for kit in school['kits']:
                    cur.execute("SELECT p.id, p.title, p.price, p.image_url, p.editorial FROM products p JOIN kit_items ki ON p.id = ki.product_id WHERE ki.kit_id = %s", (kit['id'],))
                    kit['products'] = cur.fetchall()
            return jsonify(schools)
        if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
        if request.method == 'POST':
            data = request.json
            cur = conn.cursor()
            cur.execute("INSERT INTO schools (name, logo_url) VALUES (%s, %s)", (data['name'], data.get('logo_url', '')))
            conn.commit()
            return jsonify({"success": True})
        if request.method == 'DELETE':
            sid = request.args.get('id')
            cur = conn.cursor()
            cur.execute("DELETE FROM schools WHERE id = %s", (sid,))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error API Schools: {e}")
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# --- API KITS (Existente) ---
@app.route('/api/kits', methods=['POST', 'DELETE'])
def api_kits():
    if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    try:
        if request.method == 'POST':
            data = request.json
            action = data.get('action')
            cur = conn.cursor()
            if action == 'create_kit':
                cur.execute("INSERT INTO school_kits (school_id, grade_name, price, discount, description) VALUES (%s, %s, %s, %s, %s)", 
                            (data['school_id'], data['grade_name'], float(data['price']), float(data.get('discount', 0)), data.get('description', '')))
            elif action == 'add_item':
                cur.execute("INSERT INTO kit_items (kit_id, product_id) VALUES (%s, %s) ON CONFLICT (kit_id, product_id) DO NOTHING", (data['kit_id'], data['product_id']))
            elif action == 'remove_item':
                cur.execute("DELETE FROM kit_items WHERE kit_id = %s AND product_id = %s", (data['kit_id'], data['product_id']))
            conn.commit()
            return jsonify({"success": True})
        if request.method == 'DELETE':
            kid = request.args.get('id')
            cur = conn.cursor()
            cur.execute("DELETE FROM school_kits WHERE id = %s", (kid,))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# --- NUEVA API: EDITORIALES (CMS) ---
@app.route('/api/editorials', methods=['GET', 'POST', 'DELETE'])
def api_editorials():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    try:
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM editorials ORDER BY id DESC")
            return jsonify(cur.fetchall())
        
        if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
        
        if request.method == 'POST':
            data = request.json
            cur = conn.cursor()
            cur.execute("INSERT INTO editorials (image_url, name) VALUES (%s, %s)", (data['image_url'], data.get('name', '')))
            conn.commit()
            return jsonify({"success": True})
            
        if request.method == 'DELETE':
            eid = request.args.get('id')
            cur = conn.cursor()
            cur.execute("DELETE FROM editorials WHERE id = %s", (eid,))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# --- NUEVA API: SECCIONES DESTACADAS (CMS) ---
@app.route('/api/features', methods=['GET', 'POST'])
def api_features():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB error"}), 500
    try:
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM featured_sections ORDER BY id ASC")
            return jsonify(cur.fetchall())
        
        if not session.get('admin'): return jsonify({"error": "Unauthorized"}), 401
        
        if request.method == 'POST':
            # Actualizar una tarjeta específica
            data = request.json
            cur = conn.cursor()
            cur.execute("""
                UPDATE featured_sections 
                SET title=%s, description=%s, image_url=%s, button_text=%s, modal_content=%s 
                WHERE id=%s
            """, (data['title'], data['description'], data['image_url'], data['button_text'], data['modal_content'], data['id']))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)