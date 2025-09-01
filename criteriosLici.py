import pandas as pd
import requests
from bs4 import BeautifulSoup, NavigableString
import re
import logging

# Configurar el logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Leer el archivo Excel de entrada
df_links = pd.read_excel('resultados_licitaciones_combinado.xlsx')  # Cambiado al nombre proporcionado

# Listas para almacenar los datos
criterios_data = []  # Detalles de los criterios
summary_data = []    # Resumen por licitación

# Función para extraer los criterios de adjudicación
def extract_criteria(adj_soup, link, identificador):
    # Búsqueda flexible de la sección de criterios
    section_headers = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']
    criteria_section = None
    for tag in section_headers:
        criteria_section = adj_soup.find(tag, string=re.compile(r'(criterios\s*(de\s*adjudicación|adjudicación|evaluables|evaluación))', re.IGNORECASE))
        if criteria_section:
            logging.info(f"Sección encontrada en etiqueta <{tag}> en {link}")
            break

    has_juicio_valor = False
    has_formulas = False
    data_extracted = False

    if criteria_section:
        parent_container = criteria_section.find_parent() or criteria_section.find_parent('div', class_=['boxWithBackground', 'box01', 'content'])
        if not parent_container:
            parent_container = criteria_section.find_next('div') or adj_soup
        ul_elements = parent_container.find_all('ul', recursive=True)
        current_criterio = None
        entry = {
            'Link licitación': link,
            'Identificador': identificador,
            'Categoría': '',
            'Criterio': '',
            'Subtipo Criterio': '',
            'Ponderación': '',
            'Cantidad Mínima': '',
            'Cantidad Máxima': '',
            'Fórmula o Detalle': ''
        }
        for ul in ul_elements:
            prev_h6 = ul.find_previous(['h6', 'h5', 'h4'], string=re.compile(r'(juicio\s*de\s*valor|fórmulas|evaluables)', re.IGNORECASE))
            if prev_h6:
                h6_text = prev_h6.get_text(strip=True).strip()
                if re.search(r'fórmulas', h6_text, re.IGNORECASE):
                    has_formulas = True
                    entry['Categoría'] = 'Criterios evaluables mediante aplicación de fórmulas'
                    logging.info(f"Sección de fórmulas en {link}")
                elif re.search(r'juicio\s*de\s*valor', h6_text, re.IGNORECASE):
                    has_juicio_valor = True
                    entry['Categoría'] = 'Criterios evaluables mediante un juicio de valor'
                    logging.info(f"Sección de juicio de valor en {link}")
                else:
                    continue
            for li in ul.find_all('li', recursive=False):
                div = li.find('div', class_=['noremarca', 'content']) or li
                if div:
                    div_text = div.get_text(strip=True)
                    if not div.find('span'):
                        current_criterio = div_text
                        entry['Criterio'] = current_criterio
                        logging.info(f"Criterio principal encontrado: {current_criterio} en {link}")
                        continue
                    span = div.find('span')
                    if span:
                        span_text = span.get_text(strip=True)
                        value = ''
                        for sibling in span.next_siblings:
                            if isinstance(sibling, NavigableString):
                                value = sibling.strip()
                                break
                            elif sibling.name in ['div', 'span']:
                                value = sibling.get_text(strip=True)
                                break
                        if re.search(r'subtipo\s*criterio', span_text, re.IGNORECASE):
                            entry['Subtipo Criterio'] = value
                        elif re.search(r'ponderación', span_text, re.IGNORECASE):
                            entry['Ponderación'] = value
                        elif re.search(r'(puntuación|cantidad)\s*mínima', span_text, re.IGNORECASE):
                            entry['Cantidad Mínima'] = value
                        elif re.search(r'(puntuación|cantidad)\s*máxima', span_text, re.IGNORECASE):
                            entry['Cantidad Máxima'] = value
                        elif re.search(r'(expresión\s*de\s*evaluación|fórmula)', span_text, re.IGNORECASE) or re.match(r'P\s*=.*', span_text, re.IGNORECASE):
                            entry['Fórmula o Detalle'] = value
                    if entry['Subtipo Criterio'] and entry['Ponderación']:
                        new_entry = entry.copy()
                        if not any(d['Link licitación'] == new_entry['Link licitación'] and
                                   d['Criterio'] == new_entry['Criterio'] and
                                   d['Subtipo Criterio'] == new_entry['Subtipo Criterio'] for d in criterios_data):
                            criterios_data.append(new_entry)
                            data_extracted = True
                            logging.info(f"Datos añadidos para {link}: Categoría={new_entry['Categoría']}, Criterio={new_entry['Criterio']}")
                        entry['Criterio'] = current_criterio
                        entry['Subtipo Criterio'] = ''
                        entry['Ponderación'] = ''
                        entry['Cantidad Mínima'] = ''
                        entry['Cantidad Máxima'] = ''
                        entry['Fórmula o Detalle'] = ''
        if entry['Subtipo Criterio'] and entry['Ponderación']:
            if not any(d['Link licitación'] == entry['Link licitación'] and
                       d['Criterio'] == entry['Criterio'] and
                       d['Subtipo Criterio'] == entry['Subtipo Criterio'] for d in criterios_data):
                criterios_data.append(entry.copy())
                data_extracted = True
                logging.info(f"Datos finales añadidos para {link}: Categoría={entry['Categoría']}, Criterio={entry['Criterio']}")
    else:
        logging.warning(f"No se encontró sección de criterios en {link}. Buscando estructuras alternativas...")
        # Búsqueda alternativa en tablas
        tables = adj_soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells and any(re.search(r'(criterios|ponderación|subtipo)', cell.get_text(strip=True), re.IGNORECASE) for cell in cells):
                    entry = {
                        'Link licitación': link,
                        'Identificador': identificador,
                        'Categoría': 'Desconocida (Tabla)',
                        'Criterio': '',
                        'Subtipo Criterio': '',
                        'Ponderación': '',
                        'Cantidad Mínima': '',
                        'Cantidad Máxima': '',
                        'Fórmula o Detalle': ''
                    }
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if re.search(r'criterio', text, re.IGNORECASE):
                            entry['Criterio'] = text
                        elif re.search(r'subtipo', text, re.IGNORECASE):
                            entry['Subtipo Criterio'] = text
                        elif re.search(r'ponderación', text, re.IGNORECASE):
                            entry['Ponderación'] = text
                        elif re.search(r'(puntuación|cantidad)\s*mínima', text, re.IGNORECASE):
                            entry['Cantidad Mínima'] = text
                        elif re.search(r'(puntuación|cantidad)\s*máxima', text, re.IGNORECASE):
                            entry['Cantidad Máxima'] = text
                        elif re.search(r'(fórmula|evaluación)', text, re.IGNORECASE):
                            entry['Fórmula o Detalle'] = text
                    if entry['Criterio'] or entry['Subtipo Criterio']:
                        criterios_data.append(entry.copy())
                        data_extracted = True
                        logging.info(f"Datos extraídos de tabla para {link}: {entry}")

    # Guardar resumen
    summary_entry = {
        'Link licitación': link,
        'Identificador': identificador,
        'Criterios evaluables mediante un juicio de valor': 'Sí' if has_juicio_valor else 'No',
        'Criterios evaluables mediante aplicación de fórmulas': 'Sí' if has_formulas else 'No',
        'Criterios Adjudicación Error': 'No se encontró sección de criterios' if not criteria_section else ''
    }
    summary_data.append(summary_entry)
    return data_extracted

# Contador de accesos y límite
access_count = 0
max_access = 6000

# Procesar cada enlace del Excel
for index, row in df_links.iterrows():
    if access_count >= max_access:
        logging.info(f"Límite de {max_access} accesos alcanzado.")
        break
    link = row['Link licitación']
    identificador = row['Identificador']
    try:
        # Obtener el contenido de la página de licitación
        response = requests.get(link)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')

        # Buscar el enlace de adjudicación
        adj_link_tag = soup.find('a', href=re.compile('GetDocumentByIdServlet'))
        if adj_link_tag:
            adj_url = adj_link_tag['href']
            # Obtener el contenido de la página de adjudicación
            adj_response = requests.get(adj_url)
            adj_response.raise_for_status()
            adj_soup = BeautifulSoup(adj_response.content, 'html.parser', from_encoding='utf-8')

            # Extraer la información de los criterios
            data_extracted = extract_criteria(adj_soup, link, identificador)

            # Incrementar el contador solo si se extrajeron datos
            if data_extracted:
                access_count += 1
                logging.info(f"Acceso exitoso #{access_count} para {link}")
        else:
            logging.warning(f"No se encontró enlace de adjudicación en {link}")
    except requests.RequestException as e:
        logging.error(f"Error al acceder a {link}: {e}")

# Crear DataFrames y guardar en un nuevo Excel
df_criterios = pd.DataFrame(criterios_data)
df_summary = pd.DataFrame(summary_data)

with pd.ExcelWriter('resultados_criterios_licitaciones.xlsx') as writer:
    df_criterios.to_excel(writer, sheet_name='Criterios Detallados', index=False)
    df_summary.to_excel(writer, sheet_name='Resumen por Licitación', index=False)

logging.info(f"Procesamiento completado. Se procesaron {access_count} licitaciones.")