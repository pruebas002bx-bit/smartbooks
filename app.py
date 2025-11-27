import os
import sys
from flask import Flask, render_template, jsonify, request
import psycopg2 
from datetime import datetime
from dotenv import load_dotenv

# =================================================================
# 0. CONFIGURACIÓN INICIAL Y AMBIENTE
# =================================================================

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de la base de datos y el servidor
DB_HOST = os.environ.get("DB_HOST", "localhost") 
DB_NAME = os.environ.get("DB_NAME", "smartbooks_db_duns") 
DB_USER = os.environ.get("DB_USER", "tu_usuario_postgres") 
DB_PASS = os.environ.get("DB_PASS", "tu_contraseña_postgres") 
DB_PORT = os.environ.get("DB_PORT", "5432") 

# Configuración del hosting (necesario para Render/Heroku)
PORT = int(os.environ.get('PORT', 5000))
HOST = '0.0.0.0' 

# Inicialización de la aplicación Flask
app = Flask(__name__)

# =================================================================
# 1. UTILIDADES Y CONEXIÓN A LA BASE DE DATOS
# =================================================================

def get_db_connection():
    """
    Intenta establecer la conexión a la base de datos PostgreSQL.
    Configura el modo SSL para conexiones remotas (ej. Render).

    Returns:
        psycopg2.connection or None: Objeto de conexión si es exitosa, None en caso contrario.
    """
    # Verificar que las variables de conexión estén disponibles
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT]):
        print("ADVERTENCIA: Faltan variables de entorno de DB. No se puede conectar.", file=sys.stderr)
        return None

    try:
        # Configurar sslmode='require' para hosting en la nube como Render
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            sslmode='require' if DB_HOST != 'localhost' else 'allow',
            connect_timeout=10 # Tiempo de espera para la conexión
        )
        print("INFO: Conexión a la base de datos establecida con éxito.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERROR: Fallo operacional al conectar a PostgreSQL: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Error desconocido al conectar a PostgreSQL: {e}", file=sys.stderr)
        return None

def format_price(price):
    """
    Formatea un número a string de precio en formato español ($150.000).
    Acepta None o 0 y devuelve un formato limpio.
    """
    if price is None or price == 0:
        return "$0"
    try:
        # Convertir a entero (si es decimal) y formatear con puntos como separador de miles
        # Nota: El precio en la imagen es entero, por lo que int() es seguro.
        price_int = int(price)
        return f"${price_int:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"

# =================================================================
# 2. DATOS DE FALLBACK Y SIMULACIÓN (MOCKS)
# =================================================================

# 2.1 MOCK: Configuración Web (configuracion_web) - Banners y Editoriales
FALLBACK_CONFIG_URLS = {
    # URLs de Editoriales - Seis items para la marquesina, siguiendo la lógica del HTML
    "url_editorial1": "https://placehold.co/150x50/3498db/ffffff?text=Editorial+1",
    "url_editorial2": "https://placehold.co/150x50/2ecc71/ffffff?text=Editorial+2",
    "url_editorial3": "https://placehold.co/150x50/f1c40f/ffffff?text=Editorial+3",
    "url_editorial4": "https://placehold.co/150x50/e74c3c/ffffff?text=Editorial+4",
    "url_editorial5": "https://placehold.co/150x50/9b59b6/ffffff?text=Editorial+5",
    "url_editorial6": "https://placehold.co/150x50/1abc9c/ffffff?text=Editorial+6", # Se añadió uno extra por si el loop es de 6
    # URLs de Banners - 6 items para el slider principal
    "url_banner1": "https://placehold.co/1920x600/163D6A/ffffff?text=BANNER+PRINCIPAL+1", 
    "url_banner2": "https://placehold.co/1920x600/2C5E8C/ffffff?text=BANNER+PRINCIPAL+2",
    "url_banner3": "https://placehold.co/1920x600/447FAD/ffffff?text=BANNER+PRINCIPAL+3",
    "url_banner4": "https://placehold.co/1920x600/5BA0CD/ffffff?text=BANNER+PRINCIPAL+4",
    "url_banner5": "https://placehold.co/1920x600/73C1EE/ffffff?text=BANNER+PRINCIPAL+5",
    "url_banner6": "https://placehold.co/1920x600/8BD3FF/ffffff?text=BANNER+PRINCIPAL+6",
    # URLs de Recuadros (Tarjetas de Servicios)
    "url_recuadro1": "https://placehold.co/400x300/F39C12/ffffff?text=Recuadro+1",
    "url_recuadro2": "https://placehold.co/400x300/C0392B/ffffff?text=Recuadro+2",
    "url_recuadro3": "https://placehold.co/400x300/8E44AD/ffffff?text=Recuadro+3",
}

# 2.2 MOCK: Productos Destacados (productos_escolares - FALLBACK)
def get_simulated_featured_products(count=8):
    """Genera datos de productos simulados con la estructura necesaria para index.html."""
    
    # Estructura basada en las columnas de 'productos_escolares' y el loop del HTML
    base_products = [
        # Data simulada con estructura de productos_escolares
        {"titulo": "Give Me Five International 3 - Pupil's Book", "descripcion_corta": "Guía para directores que buscan calidad, alineación pedagógica y adaptabilidad en textos.", "url_imagen": "https://placehold.co/300x400/163D6A/ffffff?text=Producto+1", "rating": 5, "precio": 149900, "categoria": "Give Me Five, MacMillan"},
        {"titulo": "INSTA ENGLISH - 4th EDITION (8 SPLIT)", "descripcion_corta": "Análisis y proyecciones del sector educativo, modelos híbridos y tecnología en el aula.", "url_imagen": "https://placehold.co/300x400/2C5E8C/ffffff?text=Producto+2", "rating": 4, "precio": 99900, "categoria": "Insta English, MacMillan"},
        {"titulo": "Doodle Town - Student Book 3", "descripcion_corta": "Solución integral para la implementación de programas bilingües de alta calidad.", "url_imagen": "https://placehold.co/300x400/447FAD/ffffff?text=Producto+3", "rating": 5, "precio": 199900, "categoria": "Doodle Town, MacMillan"},
        {"titulo": "FERNS WHEEL - WORKBOOK 1", "descripcion_corta": "Combina la experiencia del papel con el poder de las plataformas digitales interactivas.", "url_imagen": "https://placehold.co/300x400/5BA0CD/ffffff?text=Producto+4", "rating": 4, "precio": 75900, "categoria": "Ferns Wheel, MacMillan"},
    ]

    simulated_products = []
    # Duplicar y modificar para tener al menos 'count' productos
    for i in range(count):
        product = base_products[i % len(base_products)].copy()
        product["titulo"] = f"{product['titulo']} (Ref. {i+1})"
        product["precio"] = product["precio"] + (i * 1000)
        product["precio_formateado"] = format_price(product["precio"])
        # 'url_imagen' ya es el nombre correcto para el template
        simulated_products.append(product)
        
    return simulated_products

# 2.3 MOCK: Colegios (colegios)
SIMULATED_SCHOOLS = [
    # Datos de colegios simulados, incluyendo los kits por grado
    {"ID_COLEGIO": 1, "COLEGIO": "Colegio Mayor del Sol", "CIUDAD": "Bogotá", "IMAGEN": "url_imagen_sol", "UBICACION": "https://maps.google.com/?q=Colegio+Mayor+del+Sol", "PREJARDIN": "Kit Preescolar A", "JARDIN": "Kit Preescolar A", "TRANSICION": "Kit Preescolar B", "PRIMERO": "Kit Primaria 1", "SEGUNDO": "Kit Primaria 2", "TERCERO": "Kit Primaria 3", "CUARTO": "0", "QUINTO": "0", "SEXTO": "Kit Bachillerato", "SEPTIMO": "Kit Bachillerato", "OCTAVO": "0", "NOVENO": "0", "DECIMO": "0", "ONCE": "0"},
    {"ID_COLEGIO": 2, "COLEGIO": "Instituto Británico", "CIUDAD": "Medellín", "IMAGEN": "url_imagen_britanico", "UBICACION": "https://maps.google.com/?q=Instituto+Británico", "PREJARDIN": "0", "JARDIN": "0", "TRANSICION": "Kit Cambridge Pre", "PRIMERO": "Kit Cambridge 1", "SEGUNDO": "Kit Cambridge 2", "TERCERO": "Kit Cambridge 3", "CUARTO": "Kit Cambridge 4", "QUINTO": "Kit Cambridge 5", "SEXTO": "Kit Bachillerato A", "SEPTIMO": "Kit Bachillerato A", "OCTAVO": "0", "NOVENO": "Kit IGCSE", "DECIMO": "Kit A-Levels", "ONCE": "Kit A-Levels"},
]

def simulate_package_data(school_id, grade_name):
    """
    Simula la obtención de un paquete de libros detallado
    basado en el ID del colegio y el nombre del grado.
    """
    base_price = 150000 
    
    # Ajuste de precio simulado
    if school_id == 2: base_price *= 1.2
    if grade_name.startswith("Pre") or grade_name.startswith("Jardin"): base_price *= 0.7
    
    package_id = f"PK-{school_id}-{grade_name.replace(' ', '-').lower()}"
    
    # Lista simulada de los libros que componen el paquete
    books = [
        {"name": f"Matemáticas para {grade_name}", "author": "Dr. Álgebra", "isbn": "978-1234567890"},
        {"name": f"Lengua y Literatura de {grade_name}", "author": "A. Machado", "isbn": "978-0987654321"},
        {"name": f"Ciencias Naturales - Volumen I", "author": "B. Franklin", "isbn": "978-5555555555"},
        {"name": f"Sociales y Cívica", "author": "H. Arendt", "isbn": "978-1111111111"},
        {"name": f"Música y Artes", "author": "L. Mozart", "isbn": "978-2222222222"},
        {"name": f"Plataforma Digital Premium", "author": "Smart Books Tech", "isbn": "N/A"},
    ]
    
    # Datos que necesita el frontend para mostrar el paquete
    return {
        "package_id": package_id,
        "school_id": school_id,
        "grade": grade_name,
        "price_total": base_price + (len(books) * 5000), 
        "price_formateado": format_price(base_price + (len(books) * 5000)),
        "books_count": len(books),
        "books_list": books,
        "shipping_time": "3-5 días hábiles (Nacional)",
        "available": True,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# =================================================================
# 3. FUNCIONES DE CONSULTA A LA BASE DE DATOS
# =================================================================

def get_config_urls_from_db(conn):
    """
    Obtiene todas las URLs de configuración de la tabla configuracion_web.
    Convierte las claves a snake_case para Jinja2.
    """
    config_urls = {}
    if conn is None:
        return config_urls

    try:
        with conn.cursor() as cur:
            # Query para obtener clave y valor
            sql_query = 'SELECT clave, valor FROM configuracion_web;'
            cur.execute(sql_query)
            
            # Mapear los resultados
            for clave, valor in cur.fetchall():
                # Reemplazar '-' por '_' para compatibilidad con Jinja2 en el HTML
                config_urls[clave.replace('-', '_')] = valor 
            
            return config_urls
    except psycopg2.Error as e:
        print(f"ERROR DB: Fallo al obtener URLs de configuracion_web: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"ERROR: Fallo inesperado al obtener configuracion_web: {e}", file=sys.stderr)
        return {}

def get_featured_products_from_db(conn):
    """
    Obtiene los productos destacados de la tabla productos_escolares, ordenados por ID
    (asumiendo que ID alto = reciente/popular).
    Usa 'a2_titulo' como 'descripcion_corta' y 'editorial' como 'categoria'.
    """
    productos = []
    if conn is None:
        return productos

    try:
        with conn.cursor() as cur:
            # Columnas requeridas por index.html y disponibles en productos_escolares:
            # titulo, a2_titulo (como descripcion_corta), url_imagen, precio, editorial (como categoria)
            sql_query = """
            SELECT 
                titulo, 
                a2_titulo AS descripcion_corta, 
                url_imagen, 
                precio,
                editorial AS categoria
            FROM 
                productos_escolares
            ORDER BY 
                id_producto DESC 
            LIMIT 8; 
            """
            cur.execute(sql_query)
            
            # Datos simulados de metadatos (rating), ya que no están en la tabla
            simulated_ratings = [5, 4, 5, 4, 5, 4, 5, 4]
            
            # Mapeo y enriquecimiento de datos
            for i, row in enumerate(cur.fetchall()):
                producto = {
                    "titulo": row[0],
                    # Usamos a2_titulo de la DB como la descripción corta para la tarjeta
                    "descripcion_corta": row[1] if row[1] else "Libro de texto escolar de alta calidad.",
                    "url_imagen": row[2], 
                    "rating": simulated_ratings[i % len(simulated_ratings)],
                    "precio": row[3],
                    "precio_formateado": format_price(row[3]),
                    # Usamos la editorial de la DB como la categoría para la tarjeta
                    "categoria": row[4] if row[4] else "Educación General" 
                }
                productos.append(producto)

        return productos
    except psycopg2.ProgrammingError as e:
        # Esto ocurre si la tabla o las columnas no existen (ej. productos_escolares)
        print(f"ERROR DB: Fallo de programación (tabla o columnas faltantes en productos_escolares): {e}", file=sys.stderr)
        return []
    except psycopg2.Error as e:
        print(f"ERROR DB: Fallo al obtener productos de productos_escolares: {e}", file=sys.stderr)
        return []

def get_schools_from_db(conn):
    """
    Obtiene la lista de todos los colegios con sus kits de libros por grado.
    """
    colegios_data = []
    if conn is None:
        return colegios_data

    try:
        with conn.cursor() as cur:
            # Selecciona todas las columnas relevantes de la tabla colegios. 
            # Asegúrate de que los nombres de las columnas coincidan con tu DB real.
            sql_query = """
            SELECT 
                "ID_COLEGIO", "COLEGIO", "CIUDAD", "IMAGEN", "UBICACION",
                "PREJARDIN", "JARDIN", "TRANSICION", "PRIMERO", "SEGUNDO", 
                "TERCERO", "CUARTO", "QUINTO", "SEXTO", "SEPTIMO", 
                "OCTAVO", "NOVENO", "DECIMO", "ONCE"
            FROM 
                colegios
            ORDER BY 
                "COLEGIO";
            """
            cur.execute(sql_query)
            
            # Obtener los nombres de las columnas para crear diccionarios
            column_names = [desc[0] for desc in cur.description]
            
            for row in cur.fetchall():
                school_data = dict(zip(column_names, row))
                # Limpiar valores None para que JSON/JavaScript funcione correctamente
                for key, value in school_data.items():
                    if value is None:
                        # '0' para grados sin kit, cadena vacía para otros campos NULL
                        school_data[key] = "0" if key in ["PREJARDIN", "JARDIN", "TRANSICION", "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO", "SEPTIMO", "OCTAVO", "NOVENO", "DECIMO", "ONCE"] else ""
                
                colegios_data.append(school_data)
        
        return colegios_data
    except psycopg2.Error as e:
        print(f"ERROR DB: Fallo al obtener la lista de colegios: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"ERROR: Fallo inesperado al obtener colegios: {e}", file=sys.stderr)
        return []


# =================================================================
# 4. RUTAS PRINCIPALES Y LÓGICA DE DATOS
# =================================================================

@app.route('/')
def index():
    """
    Ruta principal (index.html). Carga todos los datos dinámicos 
    (Banners, Editoriales, Recuadros y Productos Destacados) de la DB.
    Utiliza fallbacks si la conexión o los datos fallan.
    """
    config_urls = {}
    productos_destacados = []
    conn = None # Inicializar la conexión fuera del try

    try:
        conn = get_db_connection()
        if conn is not None:
            # 1. Obtener URLs de configuracion_web
            config_urls = get_config_urls_from_db(conn)
            
            # 2. Obtener productos de productos_escolares (¡CORREGIDO!)
            productos_destacados = get_featured_products_from_db(conn)
        
        # 3. Aplicar Fallback si faltan datos
        if not config_urls:
            print("INFO: Usando URLs de configuración simuladas (Datos vacíos o DB Fallida).")
            config_urls = FALLBACK_CONFIG_URLS

        if not productos_destacados:
            print("INFO: Usando productos destacados simulados (Datos vacíos o DB Fallida).")
            productos_destacados = get_simulated_featured_products(count=8)

        # 4. Renderizar el template
        return render_template(
            'index.html', 
            **config_urls, # Pasa todas las URLs de configuracion_web a Jinja2
            productos_destacados=productos_destacados
        ) 
    
    except Exception as e:
        print(f"ERROR FATAL en la ruta '/': {e}", file=sys.stderr)
        # Fallback de emergencia en caso de error de servidor
        return render_template(
            'index.html', 
            **FALLBACK_CONFIG_URLS,
            productos_destacados=get_simulated_featured_products(count=8)
        )
    finally:
        # 5. Cerrar la conexión
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"ERROR: No se pudo cerrar la conexión a la DB: {e}", file=sys.stderr)


# =================================================================
# 5. RUTAS DE API (JSON)
# =================================================================

@app.route('/api/colegios', methods=['GET'])
def get_colegios_api():
    """
    Ruta API para obtener la lista de todos los colegios.
    Utilizada por el frontend para la búsqueda de kits.
    """
    conn = None
    try:
        conn = get_db_connection()
        colegios_data = []

        if conn is not None:
            colegios_data = get_schools_from_db(conn)
        
        if not colegios_data:
            print("INFO: Usando datos simulados de colegios (DB Fallida o Datos Vacíos).")
            return jsonify(SIMULATED_SCHOOLS), 200 # Devuelve 200 OK con datos simulados

        return jsonify(colegios_data), 200

    except Exception as e:
        print(f"ERROR FATAL en /api/colegios: {e}", file=sys.stderr) 
        # Fallback a datos simulados en caso de error grave
        return jsonify(SIMULATED_SCHOOLS), 200 
    finally:
        if conn:
            conn.close()

@app.route('/api/paquete', methods=['GET'])
def get_course_package_api():
    """
    Ruta API para obtener el paquete de libros específico para un colegio y curso.
    Dado que esta lógica es compleja (depende de tablas 'kits', 'productos', 'precios'),
    se utiliza solo la simulación de datos.
    """
    school_id_str = request.args.get('school_id')
    grade_name = request.args.get('grade_name') # Nombre del grado (ej. '1° (Primero)')

    if not school_id_str or not grade_name:
        return jsonify({"error": "Parámetros 'school_id' y 'grade_name' son requeridos."}), 400

    try:
        school_id = int(school_id_str)
    except ValueError:
        return jsonify({"error": "El 'school_id' debe ser un número entero válido."}), 400

    # Usar simulación de datos (Mock de búsqueda de libros específicos)
    # En un entorno real, aquí iría una consulta compleja a múltiples tablas de la DB.
    package_data = simulate_package_data(school_id, grade_name)

    if package_data:
        return jsonify(package_data), 200
    else:
        # En caso de no encontrar un kit, se devuelve un 404
        return jsonify({"error": f"No se encontró un paquete para el Colegio ID {school_id} y Grado {grade_name}."}), 404


# =================================================================
# 6. RUTAS DE PÁGINAS ESTÁTICAS (Templates)
# =================================================================

@app.route('/quienes-somos')
def quienes_somos():
    """Ruta para la página Quiénes Somos."""
    return render_template('QuienesSomos.html') 

@app.route('/terminos-y-condiciones')
def terminos_y_condiciones():
    """Ruta para la página de Términos y Condiciones."""
    return render_template('TerminosYCondiciones.html')

@app.route('/preguntas-frecuentes')
def preguntas_frecuentes():
    """Ruta para la página de Preguntas Frecuentes."""
    return render_template('PreguntasFrecuentes.html')

@app.route('/aliados/castillo')
def aliados_castillo():
    """Ruta para la página de Aliados Castillo."""
    return render_template('AliadosCastillo.html') 

@app.route('/aliados/macmillan')
def aliados_macmillan():
    """Ruta para la página de Aliados MacMillan."""
    return render_template('AliadosMacmillan.html') 

@app.route('/tienda')
def tienda():
    """Ruta para la página de la Tienda."""
    return render_template('Tienda.html')

@app.route('/colegios')
def colegios():
    """Ruta para la página de Colegios (buscador de kits)."""
    return render_template('Colegios.html')

@app.route('/contactanos')
def contactanos():
    """Ruta para la página de Contáctanos."""
    return render_template('Contactanos.html')

@app.route('/intranet')
def intranet():
    """Ruta para la página de Intranet/Login."""
    return render_template('Intranet.html')

@app.route('/blog')
def blog():
    """Ruta para la página principal del Blog."""
    # En un entorno real, esta ruta cargaría la lista de articulos_blog
    return render_template('Blog.html')

# =================================================================
# 7. MANEJO DE ERRORES GLOBAL
# =================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Manejo de la página no encontrada (404)."""
    print(f"ERROR: Ruta no encontrada: {request.url}", file=sys.stderr)
    # Asume que existe un template 404.html
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Manejo de errores internos del servidor (500)."""
    print(f"ERROR: Error interno del servidor: {e}", file=sys.stderr)
    return render_template('500.html'), 500

# =================================================================
# 8. INICIALIZACIÓN DEL SERVIDOR
# =================================================================

if __name__ == '__main__':
    # Mensaje de inicio para el entorno local
    print("=====================================================")
    print("  Smart Books Flask Server Inicializando")
    print("=====================================================")
    print(f"  HOST: {HOST}, PORT: {PORT}")
    print(f"  DB: {DB_NAME}@{DB_HOST}:{DB_PORT} (User: {DB_USER})")
    print("=====================================================")
    
    # Iniciar la aplicación en modo debug si es local
    app.run(host=HOST, port=PORT, debug=True)