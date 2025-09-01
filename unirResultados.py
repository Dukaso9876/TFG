import pandas as pd

# Definir las rutas de los archivos Excel
ruta_excel_1 = 'licitaciones_filtradas.xlsx'  # Cambia por la ruta real del primer Excel
ruta_resultados_licitaciones = 'resultados_licitaciones.xlsx'  # Cambia por la ruta real del segundo Excel

# Columnas que se desean añadir desde el primer Excel a resultados_licitaciones
columnas_a_anadir = [
    'Estado',
    'Número de expediente',
    'Objeto del Contrato',
    'Identificador único TED',
    'Lugar de ejecución',
    'Órgano de Contratación',
    'ID OC en PLACSP',
    'NIF OC',
    'DIR3'
]

# Nombre de la columna identificadora común en ambos archivos
columna_identificador = 'Identificador'  # Ajusta si el nombre exacto es diferente

# Leer el primer archivo Excel
try:
    df_excel_1 = pd.read_excel(ruta_excel_1)
    print("Columnas en el primer Excel:", df_excel_1.columns.tolist())
    print("\nPrimeras 5 filas del primer Excel:\n", df_excel_1.head().to_string())
except Exception as e:
    print(f"Error al leer el primer Excel: {e}")
    exit()

# Verificar las hojas disponibles en resultados_licitaciones.xlsx
with pd.ExcelFile(ruta_resultados_licitaciones) as xls:
    print("\nHojas disponibles en resultados_licitaciones.xlsx:", xls.sheet_names)

# Leer la hoja 'Resultados' del segundo Excel
try:
    df_resultados = pd.read_excel(ruta_resultados_licitaciones, sheet_name='Resultados')
    print("\nColumnas en la hoja 'Resultados' de resultados_licitaciones.xlsx:", df_resultados.columns.tolist())
    print("\nPrimeras 5 filas de la hoja 'Resultados':\n", df_resultados.head().to_string())
except ValueError as e:
    print(f"Error: No se encontró la hoja 'Resultados' en {ruta_resultados_licitaciones}. Error: {e}")
    exit()

# Verificar que la columna identificadora existe en ambos DataFrames
if columna_identificador not in df_excel_1.columns:
    print(f"Error: La columna '{columna_identificador}' no se encuentra en el primer Excel.")
    print("Intenta con uno de estos nombres de columnas:", df_excel_1.columns.tolist())
    exit()
if columna_identificador not in df_resultados.columns:
    print(f"Error: La columna '{columna_identificador}' no se encuentra en la hoja 'Resultados' de resultados_licitaciones.xlsx.")
    exit()

# Verificar que las columnas solicitadas existen en el primer Excel
columnas_faltantes = [col for col in columnas_a_anadir if col not in df_excel_1.columns]
if columnas_faltantes:
    print(f"Error: Las siguientes columnas no se encuentran en el primer Excel: {columnas_faltantes}")
    exit()

# Realizar la unión (merge) de los DataFrames usando la columna identificadora
df_combinado = pd.merge(
    df_resultados,
    df_excel_1[[columna_identificador] + columnas_a_anadir],
    on=columna_identificador,
    how='left'
)

# Limpiar columnas que contengan 'Error' en su nombre
print("\nColumnas antes de la limpieza:", df_combinado.columns.tolist())
columnas_error = [col for col in df_combinado.columns if 'error' in str(col).lower().replace('/', '').replace('\\', '')]
if columnas_error:
    df_combinado = df_combinado.drop(columns=columnas_error, errors='ignore')
    print(f"Se eliminaron {len(columnas_error)} columnas que contenían 'Error': {columnas_error}")
else:
    print("No se encontraron columnas con 'Error' en el nombre.")
print("Columnas después de la limpieza:", df_combinado.columns.tolist())

# Leer el archivo resultados_licitaciones como un libro de Excel para mantener todas las hojas
with pd.ExcelFile(ruta_resultados_licitaciones) as xls:
    hojas = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

# Reemplazar la hoja 'Resultados' con los datos combinados y limpios
hojas['Resultados'] = df_combinado

# Guardar el nuevo archivo Excel con todas las hojas
ruta_salida = 'resultados_licitaciones_combinado.xlsx'
try:
    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        for sheet_name, df in hojas.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"\nArchivo combinado y limpio guardado en: {ruta_salida}")
except Exception as e:
    print(f"Error al guardar el archivo: {e}")