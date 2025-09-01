import pandas as pd

# Ruta del archivo Excel de entrada
input_file = 'Licitaciones2021.xlsx'  # Reemplaza con la ruta de tu archivo
output_file = 'licitaciones_filtradas.xlsx'   # Nombre del archivo de salida

try:
    # Leer la hoja 'Licitaciones' del archivo Excel
    df = pd.read_excel(input_file, sheet_name='Licitaciones')
    
    # Filtrar por Estado = 'Resuelta' y Tipo de contrato = 'Obras'
    filtered_df = df[(df['Estado'] == 'Resuelta') & (df['Tipo de contrato'] == 'Obras')]
    
    # Guardar los datos filtrados en un nuevo archivo Excel
    filtered_df.to_excel(output_file, index=False)
    
    print(f"Datos filtrados exportados correctamente a {output_file}")
    
except FileNotFoundError:
    print("Error: El archivo de entrada no se encuentra. Verifica la ruta.")
except ValueError as ve:
    if "No sheet named" in str(ve):
        print("Error: La hoja 'Licitaciones' no existe en el archivo Excel.")
    else:
        print("Error: Verifica que las columnas 'Estado' y 'Tipo de contrato' existan en la hoja.")
except Exception as e:
    print(f"Error inesperado: {str(e)}")