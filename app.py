import os
import sys
from flask import Flask, render_template, jsonify, request, abort
import psycopg2 
from datetime import datetime
from dotenv import load_dotenv

# =================================================================
# 0. CONFIGURACIÓN INICIAL Y AMBIENTE
# =================================================================

# Cargar variables de entorno desde el archivo .env (solo para desarrollo local)
load_dotenv()

# Inicialización de la aplicación Flask
# Flask buscará los archivos HTML en la carpeta 'templates' por defecto
app = Flask(__name__)

# Configuración del Puerto (Render inyecta la variable PORT automáticamente)
PORT = int(os.environ.get('PORT', 5000))

# =================================================================
# 1. UTILIDADES Y CONEXIÓN A LA BASE DE DATOS
# =================================================================

def get_db_connection():
    """
    Establece la conexión a la base de datos PostgreSQL.
    Prioriza la variable DATABASE_URL que provee Render automáticamente.
    """
    # 1. Intento de conexión automática para Render (Estándar de Producción)
    database_url = os.environ.get("DATABASE_URL")
    
    # 2. Variables individuales (Fallback para desarrollo local con .env)
    db_host = os.environ.get("DB_HOST")
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")

    try:
        if database_url:
            # Conexión usando la URL completa (Render)
            conn = psycopg2.connect(database_url, sslmode='require')
            # print("INFO: Conexión establecida usando DATABASE_URL (Render).")
            return conn
        
        elif all([db_host, db_name, db_user, db_pass]):
            # Conexión usando variables individuales (Local)
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_pass,
                port=os.environ.get("DB_PORT", 5432),
                sslmode='require' if db_host != 'localhost' else 'allow',
                connect_timeout=10
            )
            # print("INFO: Conexión establecida usando variables individuales.")
            return conn
        else:
            print("ADVERTENCIA: No se encontraron credenciales de base de datos.", file=sys.stderr)
            return None

    except psycopg2.OperationalError as e:
        print(f"ERROR: Fallo operacional al conectar a PostgreSQL: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Error desconocido al conectar a DB: {e}", file=sys.stderr)
        return None

def format_price(price):
    """Formatea números a formato moneda (ej: 15000 -> $15.000)"""
    if price is None or price == 0:
        return "$0"
    try:
        price_int = int(price)
        return f"${price_int:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"

# =================================================================
# 2. DATOS DE FALLBACK (SIMULACIÓN POR SI FALLA LA DB)
# =================================================================

FALLBACK_CONFIG_URLS = {
    "url_editorial1": "https://placehold.co/150x50/3498db/ffffff?text=Editorial+1",
    "url_editorial2": "https://placehold.co/150x50/2ecc71/ffffff?text=Editorial+2",
    "url_editorial3": "https://placehold.co/150x50/f1c40f/ffffff?text=Editorial+3",
    "url_editorial4": "https://placehold.co/150x50/e74c3c/ffffff?text=Editorial+4",
    "url_editorial5": "https://placehold.co/150x50/9b59b6/ffffff?text=Editorial+5",
    "url_banner1": "https://placehold.co/1920x600/163D6A/ffffff?text=BANNER+1", 
    "url_banner2": "https://placehold.co/1920x600/2C5E8C/ffffff?text=BANNER+2",
    "url_banner3": "https://placehold.co/1920x600/447FAD/ffffff?text=BANNER+3",
    "url_banner4": "https://placehold.co/1920x600/5BA0CD/ffffff?text=BANNER+4",
    "url_banner5": "https://placehold.co/1920x600/73C1EE/ffffff?text=BANNER+5",
    "url_banner6": "https://placehold.co/1920x600/8BD3FF/ffffff?text=BANNER+6",
    "url_recuadro1": "https://placehold.co/400x300/F39C12/ffffff?text=Recuadro+1",
    "url_recuadro2": "https://placehold.co/400x300/C0392B/ffffff?text=Recuadro+2",
    "url_recuadro3": "https://placehold.co/400x300/8E44AD/ffffff?text=Recuadro+3",
}

SIMULATED_SCHOOLS = [
    {"ID_COLEGIO": 1, "COLEGIO": "Colegio Demo Render", "CIUDAD": "Bogotá", "IMAGEN": "", "UBICACION": "", "PREJARDIN": "Kit Demo"},
    {"ID_COLEGIO": 2, "COLEGIO": "Liceo Prueba", "CIUDAD": "Medellín", "IMAGEN": "", "UBICACION": "", "PREJARDIN": "0"}
]

def get_simulated_featured_products(count=8):
    """Genera productos falsos para que el diseño no se rompa"""
    base = {"titulo": "Producto Demo", "descripcion_corta": "Descripción de prueba", "url_imagen": "https://placehold.co/300x400", "rating": 5, "precio": 50000, "categoria": "General"}
    return [ {**base, "precio_formateado": "$50.000"} for _ in range(count) ]

def simulate_package_data(school_id, grade_name):
    """Simula un paquete de libros"""
    return {
        "package_id": f"PK-{school_id}",
        "school_id": school_id,
        "grade": grade_name,
        "price_total": 250000, 
        "price_formateado": "$250.000",
        "books_count": 4,
        "books_list": [
            {"name": "Matemáticas Demo", "author": "Autor X"},
            {"name": "Inglés Demo", "author": "Autor Y"}
        ],
        "available": True
    }

# =================================================================
# 3. FUNCIONES DE CONSULTA A DB
# =================================================================

def get_config_urls_from_db(conn):
    config_urls = {}
    if conn is None: return config_urls
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT clave, valor FROM configuracion_web;')
            for clave, valor in cur.fetchall():
                # Reemplazamos guiones por guiones bajos para compatibilidad con Jinja2
                config_urls[clave.replace('-', '_')] = valor 
            return config_urls
    except Exception as e:
        print(f"Error DB config: {e}")
        return {}

def get_featured_products_from_db(conn):
    productos = []
    if conn is None: return productos
    try:
        with conn.cursor() as cur:
            # Asegúrate de que los nombres de columna coincidan con tu tabla real
            sql_query = """
            SELECT titulo, a2_titulo, url_imagen, precio, editorial
            FROM productos_escolares ORDER BY id_producto DESC LIMIT 8; 
            """
            cur.execute(sql_query)
            for row in cur.fetchall():
                productos.append({
                    "titulo": row[0],
                    "descripcion_corta": row[1] if row[1] else "Sin descripción",
                    "url_imagen": row[2], 
                    "rating": 5, # Rating simulado ya que no está en DB
                    "precio": row[3],
                    "precio_formateado": format_price(row[3]),
                    "categoria": row[4] if row[4] else "General" 
                })
        return productos
    except Exception as e:
        print(f"Error DB productos: {e}")
        return []

def get_schools_from_db(conn):
    data = []
    if conn is None: return data
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM colegios ORDER BY "COLEGIO";')
            colnames = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                school = dict(zip(colnames, row))
                # Limpiar valores None para evitar errores en el JSON
                for k, v in school.items():
                    if v is None: school[k] = "0" if k not in ["COLEGIO", "CIUDAD"] else ""
                data.append(school)
        return data
    except Exception as e:
        print(f"Error DB colegios: {e}")
        return []

# =================================================================
# 4. RUTAS (VIEWS)
# =================================================================

@app.route('/')
def index():
    """
    Ruta raíz: Carga el esqueleto (index.html) con los datos del Home.
    """
    conn = None
    config_urls = {}
    destacados = []

    try:
        conn = get_db_connection()
        if conn:
            config_urls = get_config_urls_from_db(conn)
            destacados = get_featured_products_from_db(conn)
        
        # Aplicar fallbacks si la DB no devolvió datos
        if not config_urls: config_urls = FALLBACK_CONFIG_URLS
        if not destacados: destacados = get_simulated_featured_products()

        return render_template('index.html', **config_urls, productos_destacados=destacados)
    except Exception as e:
        print(f"Error FATAL en index: {e}")
        # Renderiza con puros datos simulados para que no salga Error 500
        return render_template('index.html', **FALLBACK_CONFIG_URLS, productos_destacados=get_simulated_featured_products())
    finally:
        if conn: conn.close()

# ---------------------------------------------------------------
# RUTA DINÁMICA PARA LA SPA (IMPORTANTE)
# ---------------------------------------------------------------
# Esta ruta captura cualquier petición que termine en .html
# Ejemplo: si el JS pide /QuienesSomos.html, esta función lo maneja.
@app.route('/<page_name>.html')
def serve_html_pages(page_name):
    """
    Sirve los fragmentos HTML (templates) solicitados por el JavaScript loadPage().
    Busca el archivo {page_name}.html dentro de la carpeta /templates.
    """
    try:
        # Flask busca automáticamente en la carpeta 'templates'
        return render_template(f'{page_name}.html')
    except Exception as e:
        print(f"Error sirviendo {page_name}.html: {e}")
        abort(404) # Devuelve error 404 si el archivo no existe

# ---------------------------------------------------------------
# RUTAS DE API (JSON)
# ---------------------------------------------------------------

@app.route('/api/colegios', methods=['GET'])
def api_colegios():
    """API que devuelve la lista de colegios en formato JSON"""
    conn = get_db_connection()
    if conn:
        data = get_schools_from_db(conn)
        conn.close()
        if data:
            return jsonify(data)
    
    # Si falla la DB, devolvemos simulación
    return jsonify(SIMULATED_SCHOOLS)

@app.route('/api/paquete', methods=['GET'])
def api_paquete():
    """API para buscar un kit específico (Simulado por ahora)"""
    school_id = request.args.get('school_id')
    grade_name = request.args.get('grade_name')
    
    if not school_id or not grade_name:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    # Aquí iría la consulta real a la DB para armar el kit
    # Por ahora usamos la simulación
    data = simulate_package_data(school_id, grade_name)
    return jsonify(data)

# =================================================================
# 5. CONFIGURACIÓN DE EJECUCIÓN
# =================================================================

if __name__ == '__main__':
    # Esto solo se ejecuta en local. En Render, Gunicorn toma el control.
    # El modo debug se activa solo si la variable FLASK_ENV es 'development'
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    print(f"--- Iniciando Servidor Local en puerto {PORT} ---")
    app.run(host='0.0.0.0', port=PORT, debug=debug_mode)