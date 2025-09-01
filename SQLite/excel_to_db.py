import pandas as pd
import os
import sqlite3
import re
import unicodedata

# Carpeta con los archivos Excel
excel_folder = os.path.abspath(r"..\SQLite")

# Verificar que la carpeta existe
if not os.path.exists(excel_folder):
    print(f'Error: La carpeta {excel_folder} no existe. Verifica la ruta.')
    exit()

# Ruta absoluta de la base de datos
db_path = os.path.abspath(r"..\SQLite\licitacionesBD.db")

# Verificar y crear el directorio de la base de datos
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
    print(f"Directorio {db_dir} creado.")

# Conectar a la base de datos SQLite
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"Conexión exitosa a {db_path}")
except sqlite3.OperationalError as e:
    print(f"Error al conectar a la base de datos: {e}")
    exit(1)

# Verificar que todas las tablas esperadas existan
required_tables = ['resultados_licitaciones', 'modificados', 'adjudicaciones', 'criterios_adjudicacion']
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
existing_tables = [row[0] for row in cursor.fetchall()]
for table in required_tables:
    if table not in existing_tables:
        print(f"Error: La tabla '{table}' no existe en la base de datos. Ejecuta 'init_sqlite3.py' primero.")
        conn.close()
        exit(1)

# Mapeo de archivos y hojas a tablas
file_sheet_mapping = {
    'resultados_licitaciones_combinado.xlsx': {
        'Resultados': 'resultados_licitaciones',
        'Modificacion': 'modificados',
        'Adjudicacion': 'adjudicaciones'
    },
    'resultados_criterios_licitaciones.xlsx': {
        'Criterios detallados': 'criterios_adjudicacion'
    }
}

# Función para limpiar nombres de columnas y hojas
def clean_name(name):
    # Convertir a str y a minúsculas
    name = str(name).lower()
    # Normalizar el texto para descomponer caracteres acentuados
    name = unicodedata.normalize('NFKD', name)
    # Reemplazar caracteres acentuados por sus equivalentes sin acentos
    name = ''.join(c for c in name if not unicodedata.combining(c))
    # Reemplazar cualquier carácter que no sea alfanumérico o guion bajo por '_'
    name = re.sub(r'[^a-z0-9_]', '_', name)
    # Si comienza con un dígito, añadir 'col_'
    if name and name[0].isdigit():
        name = f'col_{name}'
    # Reemplazar múltiples guiones bajos consecutivos por uno solo
    name = re.sub(r'_+', '_', name)
    # Eliminar guiones bajos al inicio o al final
    name = name.strip('_')
    return name

# Función para limpiar valores numéricos
def clean_numeric_value(value):
    if pd.isna(value):
        return None
    try:
        original = str(value)
        cleaned = re.sub(r'[^\d,.-]', '', original).strip()
        cleaned = cleaned.replace(',', '.')
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        result = float(cleaned) if cleaned and cleaned != '.' else None
        print(f"Original: {original} -> Limpiado: {cleaned} -> Final: {result}")
        return result if result is not None and result >= 0 else None
    except Exception as e:
        print(f"Error al limpiar valor {original}: {e}")
        return None

# Función para verificar y añadir columnas dinámicamente
def ensure_columns_exist(table_name, columns, conn):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    numeric_columns = [
        'importe_total_de_la_modificacion_sin_impuestos',
        'importe_total_de_la_modificacion_con_impuestos',
        'importe_total_sin_impuestos',
        'importe_total_con_impuestos'
    ]
    
    for col in columns:
        if col not in existing_columns:
            col_type = 'REAL' if col in numeric_columns else 'TEXT'
            try:
                cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN "{col}" {col_type}')
                conn.commit()
                print(f"Columna {col} añadida a {table_name} con tipo {col_type}.")
            except sqlite3.OperationalError as e:
                print(f"Error al añadir columna {col} a {table_name}: {e}")

# Función para crear o actualizar la tabla si es necesario
def create_table_if_not_exists(table_name, columns, conn, allow_duplicates=False):
    cursor = conn.cursor()
    numeric_columns = [
        'importe_total_de_la_modificacion_sin_impuestos',
        'importe_total_de_la_modificacion_con_impuestos',
        'importe_total_sin_impuestos',
        'importe_total_con_impuestos'
    ]
    # Asegurar que identificador y link_licitacion estén en la definición
    if 'identificador' not in columns:
        columns = list(columns) + ['identificador']
    if 'link_licitacion' not in columns:
        columns = list(columns) + ['link_licitacion']
    
    columns_def = ', '.join([f'"{col}" {"REAL" if col in numeric_columns else "TEXT"}' for col in columns if col not in ['identificador', 'link_licitacion']])
    
    if allow_duplicates:
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            identificador TEXT,
            link_licitacion TEXT,
            {columns_def}
        )
        '''
    else:
        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            identificador TEXT PRIMARY KEY,
            link_licitacion TEXT,
            {columns_def}
        )
        '''
    try:
        cursor.execute(create_table_query)
        conn.commit()
        print(f"Tabla {table_name} verificada o creada.")
    except sqlite3.OperationalError as e:
        print(f"Error al crear tabla {table_name}: {e}")

# Procesar los archivos Excel
for filename in os.listdir(excel_folder):
    if filename in file_sheet_mapping:
        file_path = os.path.join(excel_folder, filename)
        print(f'Procesando archivo: {filename}')
        
        try:
            xls = pd.ExcelFile(file_path)
        except Exception as e:
            print(f'    Error al leer el archivo {filename}: {e}')
            continue
        
        sheet_names_normalized = {clean_name(sheet): sheet for sheet in xls.sheet_names}
        for expected_sheet, table_name in file_sheet_mapping[filename].items():
            sheet_key = clean_name(expected_sheet)
            sheet_name = sheet_names_normalized.get(sheet_key)
            if not sheet_name:
                print(f'    Error: La hoja {expected_sheet} no existe en {filename}. Hojas disponibles: {xls.sheet_names}')
                continue
            print(f'  Procesando hoja: {sheet_name} -> Tabla: {table_name}')
            
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            except Exception as e:
                print(f'    Error al leer la hoja {sheet_name}: {e}')
                continue
            
            # Limpiar nombres de columnas
            df.columns = [clean_name(col) for col in df.columns]
            
            print(f"Columnas en el DataFrame para {table_name}: {list(df.columns)}")
            
            # Limpiar columnas numéricas específicas en la tabla modificados
            if table_name == 'modificados':
                numeric_columns = [
                    'importe_total_de_la_modificacion_sin_impuestos',
                    'importe_total_de_la_modificacion_con_impuestos',
                    'importe_total_sin_impuestos',
                    'importe_total_con_impuestos'
                ]
                for col in numeric_columns:
                    if col in df.columns:
                        print(f"Limpiando columna {col}...")
                        df[col] = df[col].apply(clean_numeric_value)
                        print(f"Valores en {col} después de limpieza:\n{df[col].head(10).to_string()}")
            
            # Verificar columnas clave
            columns_normalized = {clean_name(col): col for col in df.columns}
            identificador_col = columns_normalized.get(clean_name('Identificador'))
            link_licitacion_col = columns_normalized.get(clean_name('Link licitación'))
            
            if not identificador_col or not link_licitacion_col:
                print(f'    Error: La hoja {sheet_name} no tiene las columnas "Identificador" o "Link licitación". Columnas disponibles: {list(df.columns)}')
                continue
            
            df.rename(columns={identificador_col: 'identificador', link_licitacion_col: 'link_licitacion'}, inplace=True)
            
            df = df.dropna(subset=['identificador', 'link_licitacion'])
            
            # Crear tabla con la configuración adecuada
            create_table_if_not_exists(table_name, df.columns, conn, allow_duplicates=(table_name in ['modificados', 'adjudicaciones', 'criterios_adjudicacion']))
            
            ensure_columns_exist(table_name, df.columns, conn)
            
            # Función para actualizar o insertar datos
            def update_or_insert_data(df, table_name, conn):
                cursor = conn.cursor()
                
                # Para todas las tablas, comparar todas las columnas para evitar duplicados exactos
                existing_data_query = f"SELECT * FROM {table_name}"
                existing_data = pd.read_sql_query(existing_data_query, conn)
                existing_data.columns = [clean_name(col) for col in existing_data.columns]
                
                df = df.fillna('').astype(str)
                if not existing_data.empty:
                    existing_data = existing_data.fillna('').astype(str)
                
                df_combined = df.merge(
                    existing_data,
                    on=list(df.columns),
                    how='left',
                    indicator=True
                )
                
                df_new = df_combined[df_combined['_merge'] == 'left_only'][df.columns]
                df_existing = df_combined[df_combined['_merge'] == 'both'][df.columns]
                
                if not df_new.empty:
                    try:
                        df_new.to_sql(table_name, conn, if_exists='append', index=False, chunksize=1000)
                        print(f'    {len(df_new)} nuevos registros insertados en {table_name}.')
                    except Exception as e:
                        print(f'    Error al insertar nuevos datos en {table_name}: {e}')
                
                if not df_existing.empty:
                    print(f'    {len(df_existing)} registros ya existían en {table_name} y no se modificaron.')
                
                conn.commit()
            
            update_or_insert_data(df, table_name, conn)

# Verificar datos insertados en todas las tablas
for table in required_tables:
    print(f"Verificando datos en la tabla {table}...")
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        print(f"Columnas en {table}: {columns}")
        print(f"Primeros 5 registros en {table}:")
        for row in rows[:5]:
            print(row)
    except sqlite3.OperationalError as e:
        print(f"Error al verificar la tabla {table}: {e}")

# Cerrar conexión
conn.close()
print('Proceso completado.')