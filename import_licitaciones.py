import pandas as pd
import sqlite3
import logging
import os

logging.basicConfig(filename='import_licitaciones.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

def import_excel_to_db(input_file='licitaciones_filtradas.xlsx', db_file='licitaciones.db'):
    try:
        if not os.path.exists(input_file):
            logging.error(f"Input file {input_file} not found")
            print(f"Error: Input file {input_file} not found")
            return False
        logging.info(f"Reading Excel file: {input_file}")
        df = pd.read_excel(input_file)
        logging.info(f"Excel file read successfully. {len(df)} rows")
        print(f"Excel file read successfully. {len(df)} rows")
        required_columns = ['Identificador', 'Link licitación']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            logging.error(f"Missing required columns: {missing}")
            print(f"Error: Missing required columns: {missing}")
            # Attempt to rename similar columns
            column_map = {col: col for col in df.columns}
            for col in df.columns:
                if col.lower().replace(' ', '_') in ['link', 'link_licitacion', 'linklicitacion']:
                    column_map[col] = 'Link licitación'
                if col.lower() in ['identificador', 'id']:
                    column_map[col] = 'Identificador'
            df = df.rename(columns=column_map)
            if not all(col in df.columns for col in required_columns):
                logging.error(f"Could not rename columns to match required: {required_columns}")
                print(f"Error: Could not rename columns to match required: {required_columns}")
                return False
        conn = sqlite3.connect(db_file)
        df.to_sql('licitaciones', conn, if_exists='replace', index=False)
        logging.info(f"Imported {len(df)} rows to table 'licitaciones' in {db_file}")
        print(f"Imported {len(df)} rows to table 'licitaciones' in {db_file}")
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error during import: {e}")
        print(f"Error during import: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    if import_excel_to_db():
        print("Import completed successfully")
    else:
        print("Import failed")