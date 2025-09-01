import sqlite3
import os

# Ruta relativa de la base de datos
relative_path = r'..\SQLite\licitacionesBD.db'
# Convertir a ruta absoluta
db_path = os.path.abspath(relative_path)

# Verificar y crear el directorio si no existe
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir)
        print(f"Directorio {db_dir} creado.")
    except OSError as e:
        print(f"Error al crear directorio {db_dir}: {e}")
        raise

# Conectar a la base de datos (se crea si no existe)
conn = None  # Inicializar conn para evitar NameError
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"Conexión exitosa a {db_path}")

    # Crear tablas
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS resultados_licitaciones (
            identificador TEXT NOT NULL UNIQUE,
            link_licitacion TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS modificados (
            identificador TEXT NOT NULL,
            link_licitacion TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS adjudicaciones (
            identificador TEXT NOT NULL ,
            link_licitacion TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS criterios_adjudicacion (
            identificador TEXT NOT NULL,
            link_licitacion TEXT NOT NULL
        );
    ''')
    print("Tablas creadas correctamente.")

    # Crear índices
    cursor.executescript('''
        CREATE INDEX IF NOT EXISTS idx_resultados_identificador ON resultados_licitaciones(identificador);
        CREATE INDEX IF NOT EXISTS idx_modificados_identificador ON modificados(identificador);
        CREATE INDEX IF NOT EXISTS idx_adjudicaciones_identificador ON adjudicaciones(identificador);
        CREATE INDEX IF NOT EXISTS idx_criterios_identificador ON criterios_adjudicacion(identificador);
    ''')
    print("Índices creados correctamente.")

    # Guardar cambios
    conn.commit()
    print("Cambios guardados correctamente.")

    # Verificar que el archivo de la base de datos existe
    if os.path.exists(db_path):
        print(f"Archivo de base de datos {db_path} confirmado.")
    else:
        print(f"Error: El archivo de base de datos {db_path} no se creó.")
        raise FileNotFoundError(f"No se encontró el archivo {db_path}")

except sqlite3.OperationalError as e:
    print(f"Error operacional de SQLite: {e}")
    raise
except Exception as e:
    print(f"Error inesperado: {e}")
    raise
finally:
    # Cerrar conexión si existe
    if conn is not None:
        conn.close()
        print("Conexión cerrada.")

print(f'Base de datos y tablas creadas correctamente en {db_path}')