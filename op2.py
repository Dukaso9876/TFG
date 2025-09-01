#!/usr/bin/env python3
import import_licitaciones
import pandas as pd
import requests
import aiohttp
import asyncio
from bs4 import BeautifulSoup, NavigableString
import sys
import re
from urllib.parse import urljoin
import logging
from tqdm import tqdm
import time
import sqlite3
import html
import openpyxl
import urllib3
import os

# Suppress InsecureRequestWarning (optional)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(filename='licitaciones.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Global counters
cache_hits = 0
cache_misses = 0
retry_count = 0
modificaciones = []
adjudicaciones = []
failed_urls = []

# Set up SQLite cache
def setup_cache():
    conn = sqlite3.connect('url_cache.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS cache
                      (url TEXT PRIMARY KEY, content TEXT)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_url ON cache(url)''')
    conn.commit()
    return conn

# SQLite cache functions
def get_cached_content(conn, url):
    global cache_hits, cache_misses
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM cache WHERE url = ?', (url,))
        cached = cursor.fetchone()
        if cached:
            cache_hits += 1
            return cached[0]
        cache_misses += 1
        logging.warning(f"Cache miss for {url}")
        return None
    except sqlite3.Error as e:
        logging.error(f"SQLite error reading cache for {url}: {e}")
        return None

def cache_content(conn, url, content):
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO cache (url, content) VALUES (?, ?)', (url, content))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"SQLite error saving cache for {url}: {e}")

# Fetch URL content asynchronously
async def fetch_url_async(session, url, timeout, conn):
    global retry_count, failed_urls
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    for attempt in range(3):
        try:
            async with session.get(url, timeout=timeout, headers=headers, ssl=False) as response:
                response.raise_for_status()
                content = await response.text()
                cache_content(conn, url, content)
                logging.info(f"Fetched content from {url}")
                return content
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            retry_count += 1
            logging.warning(f"Attempt {attempt+1} failed for {url}: {e}")
            if attempt < 2:
                await asyncio.sleep(0.3 * (2 ** attempt))
            else:
                logging.error(f"Failed to fetch {url} after 3 attempts: {e}")
                failed_urls.append(url)
                return None
    return None

# Fetch URL content synchronously
def fetch_url_sync(url, timeout, conn):
    global retry_count, failed_urls
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=timeout, headers=headers, verify=False)
            response.raise_for_status()
            content = response.text
            cache_content(conn, url, content)
            logging.info(f"Fetched content from {url}")
            return content
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.warning(f"Attempt {attempt+1} failed for {url}: {e}")
            if attempt < 2:
                time.sleep(0.3 * (2 ** attempt))
            else:
                logging.error(f"Failed to fetch {url} after 3 attempts: {e}")
                failed_urls.append(url)
                return None
    return None

# Pre-fetch URLs with concurrency
async def prefetch_urls(rows, timeout, conn):
    global failed_urls
    failed_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    unique_urls = set()
    new_urls = set()
    
    for row in rows:
        link = row[1]
        unique_urls.add(link)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for link in tqdm(list(unique_urls), desc="Pre-fetching main pages"):
            content = get_cached_content(conn, link)
            if not content:
                tasks.append(fetch_url_async(session, link, timeout, conn))
            if len(tasks) >= 10:
                await asyncio.gather(*tasks)
                tasks = []
        if tasks:
            await asyncio.gather(*tasks)
        
        for link in unique_urls:
            content = get_cached_content(conn, link)
            if content:
                try:
                    soup = BeautifulSoup(content, 'lxml')
                except Exception as e:
                    logging.warning(f"Error with lxml on {link}: {e}. Using html.parser")
                    soup = BeautifulSoup(content, 'html.parser')
                
                modificacion_rows = soup.find_all('td', string=re.compile('Modificaci', re.IGNORECASE))
                for row in modificacion_rows:
                    html_link = row.find_next('td').find('a', 
                        attrs={'title': 'Este documento se abrirá en una nueva ventana', 'target': '_blank'},
                        string='Html'
                    )
                    if html_link and 'href' in html_link.attrs:
                        html_url = urljoin(link, html_link['href'])
                        new_urls.add(html_url)
                        logging.info(f"Found modification URL: {html_url}")
                
                adjudicacion_rows = soup.find_all('td', string=re.compile('Adjudicaci', re.IGNORECASE))
                for row in adjudicacion_rows:
                    html_link = row.find_next('td').find('a', 
                        attrs={'title': 'Este documento se abrirá en una nueva ventana', 'target': '_blank'},
                        string='Html'
                    )
                    if html_link and 'href' in html_link.attrs:
                        html_url = urljoin(link, html_link['href'])
                        new_urls.add(html_url)
                        logging.info(f"Found adjudication URL: {html_url}")
    
        unique_urls.update(new_urls)
        logging.info(f"Collected {len(new_urls)} additional URLs (total: {len(unique_urls)})")
        
        tasks = []
        for url in tqdm(unique_urls, desc="Pre-fetching remaining URLs"):
            if not get_cached_content(conn, url):
                tasks.append(fetch_url_async(session, url, timeout, conn))
            if len(tasks) >= 10:
                await asyncio.gather(*tasks)
                tasks = []
        if tasks:
            await asyncio.gather(*tasks)
    
    logging.info(f"Pre-fetched {len(unique_urls)} unique URLs")
    if failed_urls:
        with open('failed_urls.txt', 'w') as f:
            f.write('\n'.join(failed_urls))
        logging.warning(f"{len(failed_urls)} URLs failed to fetch, saved to failed_urls.txt")
        print(f"{len(failed_urls)} URLs failed to fetch, saved to failed_urls.txt")

# Process a single row
def process_row_sync(row, timeout, conn):
    global retry_count, modificaciones, adjudicaciones, failed_urls
    link = row[1]  # Link licitación
    identificador = row[0]  # Identificador
    
    logging.info(f"Processing link (sync): {link}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        cached_content = get_cached_content(conn, link)
        if cached_content:
            logging.info(f"Using cache for {link}")
            content = cached_content
        else:
            logging.warning(f"Cache miss for main page {link}, fetching now")
            content = fetch_url_sync(link, timeout, conn)
            if not content:
                logging.error(f"Failed to fetch main page {link}")
                return {
                    'Identificador': identificador,
                    'Link licitación': link,
                    'Modificado': 'Error - Failed to fetch main page'
                }
        
        try:
            soup = BeautifulSoup(content, 'lxml', from_encoding='utf-8')
        except Exception as e:
            logging.warning(f"Error with lxml on {link}: {e}. Using html.parser as fallback")
            soup = BeautifulSoup(content, 'html.parser', from_encoding='utf-8')
        
        datos_mod = {}
        datos_adjudicacion = {}
        fechas_por_documento = {}
        
        texto_pagina = soup.get_text(strip=True)
        modificado = 'No'
        
        table = soup.find('table', id='myTablaDetalleVISUOE')
        if table:
            logging.info(f"Table myTablaDetalleVISUOE found on {link}")
            rows = table.find_all('tr')
            mod_num = 0
            adj_num = 0
            for r in rows:
                cells = r.find_all('td')
                if len(cells) >= 2:
                    fecha_text = cells[0].get_text(strip=True)
                    documento_text = cells[1].get_text(strip=True)
                    if re.match(r'(\d{2}/\d{2}/\d{4}\s*\d{2}:\d{2}(:\d{2})?)|(\d{2}/\d{2}/\d{4})', fecha_text):
                        if re.search(r'Modificaci', documento_text, re.IGNORECASE):
                            modificado = 'Sí'
                            mod_num += 1
                            prefix = f"Mod {mod_num}"
                            documento_text = 'Modificación'
                            fechas_por_documento[documento_text] = fechas_por_documento.get(documento_text, []) + [fecha_text]
                            logging.info(f"Date found on {link}: {fecha_text}, Document: {documento_text}")
                            
                            html_link = cells[1].find_next('td').find('a', 
                                attrs={'title': 'Este documento se abrirá en una nueva ventana', 'target': '_blank'},
                                string='Html'
                            )
                            if html_link and 'href' in html_link.attrs:
                                html_url = urljoin(link, html_link['href'])
                                logging.info(f"Accessing modification link (sync): {html_url}")
                                
                                cached_mod_content = get_cached_content(conn, html_url)
                                if cached_mod_content:
                                    logging.info(f"Using cache for {html_url}")
                                    mod_content = cached_mod_content
                                else:
                                    logging.warning(f"Cache miss for modification page {html_url}, fetching now")
                                    mod_content = fetch_url_sync(html_url, timeout, conn)
                                    if not mod_content:
                                        logging.error(f"Failed to fetch modification page {html_url}")
                                        datos_mod[f"{prefix}/Error"] = 'Failed to fetch modification page'
                                        continue
                                
                                if mod_content:
                                    try:
                                        mod_soup = BeautifulSoup(mod_content, 'lxml', from_encoding='utf-8')
                                    except Exception as e:
                                        logging.warning(f"Error with lxml on {html_url}: {e}. Falling back to html.parser")
                                        mod_soup = BeautifulSoup(mod_content, 'html.parser', from_encoding='utf-8')
                                    
                                    h3_mod = mod_soup.find('h3', string=re.compile('Modificaci.*', re.IGNORECASE))
                                    if not h3_mod:
                                        h3_tags = mod_soup.find_all('h3')
                                        if h3_tags:
                                            logging.warning(f"No <h3> matched 'Modificaci.*' on {html_url}. Found {len(h3_tags)} <h3> tags with texts: {[h3.get_text(strip=True) for h3 in h3_tags]}")
                                        else:
                                            logging.warning(f"No <h3> tags found at all on {html_url}")
                                        logging.debug(f"HTML content (first 1000 chars) for {html_url}: {mod_content[:1000]}")
                                        logging.info(f"Forcing re-fetch of {html_url} to bypass cache")
                                        mod_content = fetch_url_sync(html_url, timeout, conn)
                                        if not mod_content:
                                            logging.error(f"Failed to re-fetch modification page {html_url}")
                                            datos_mod[f"{prefix}/Error"] = 'Failed to re-fetch modification page'
                                            continue
                                        try:
                                            mod_soup = BeautifulSoup(mod_content, 'lxml', from_encoding='utf-8')
                                        except Exception as e:
                                            logging.warning(f"Error with lxml on re-fetch {html_url}: {e}. Using html.parser")
                                            mod_soup = BeautifulSoup(mod_content, 'html.parser', from_encoding='utf-8')
                                        h3_mod = mod_soup.find('h3', string=re.compile('Modificaci.*', re.IGNORECASE))
                                        if not h3_mod:
                                            logging.error(f"Still no <h3> matched 'Modificaci.*' after re-fetch on {html_url}")
                                            datos_mod[f"{prefix}/Error"] = 'No <h3> found after re-fetch'
                                            continue
                                    
                                    ul_mod = h3_mod.find_next('ul')
                                    if ul_mod:
                                        logging.info(f"Section Modificación del contrato found on {html_url}")
                                        mod_data = {'Link licitación': link, 'Identificador': identificador}
                                        for li in ul_mod.find_all('li', recursive=False):
                                            span = li.find('span')
                                            if span:
                                                span_text = span.get_text(strip=True)
                                                next_text = ''
                                                for sibling in span.next_siblings:
                                                    if isinstance(sibling, NavigableString):
                                                        next_text += sibling.strip()
                                                    elif sibling.name == 'span':
                                                        break
                                                next_text = next_text.strip()
                                                if next_text:
                                                    key = f"{prefix}/{span_text}"
                                                    datos_mod[key] = next_text
                                                    mod_data[span_text] = next_text
                                                    logging.info(f"Column on {html_url}: {key}, Value: {next_text}")
                                                else:
                                                    logging.warning(f"No direct value found for span: {span_text} on {html_url}")
                                                
                                                nested_ul = li.find('ul')
                                                if nested_ul:
                                                    logging.info(f"Nested <ul> found under {span_text} on {html_url}")
                                                    for nested_li in nested_ul.find_all('li', recursive=False):
                                                        nested_span = nested_li.find('span')
                                                        nested_div = nested_li.find('div', class_='noremarca')
                                                        if nested_span and nested_div:
                                                            nested_span_text = nested_span.get_text(strip=True)
                                                            nested_value = nested_div.get_text(strip=True)
                                                            if nested_value:
                                                                key = f"{prefix}/{nested_span_text}"
                                                                datos_mod[key] = nested_value
                                                                mod_data[nested_span_text] = nested_value
                                                                logging.info(f"Nested column on {html_url}: {key}, Value: {nested_value}")
                                                        elif nested_div:
                                                            nested_value = nested_div.get_text(strip=True)
                                                            if nested_value:
                                                                key = f"{prefix}/{span_text}"
                                                                datos_mod[key] = nested_value
                                                                mod_data[span_text] = nested_value
                                                                logging.info(f"Nested column (no span) on {html_url}: {key}, Value: {nested_value}")
                                        if not any(k in mod_data for k in ['Error']):
                                            modificaciones.append(mod_data)
                                            logging.info(f"Added modification data for {link} to modificaciones list")
                                    else:
                                        datos_mod[f"{prefix}/Error"] = 'No <ul> found'
                                        logging.warning(f"No <ul> found on {html_url}")
                            else:
                                datos_mod[f"{prefix}/Error"] = 'Html link not found'
                                logging.warning(f"Html link not found for modification {mod_num} on {link}")
                        
                        elif re.search(r'Adjudicaci', documento_text, re.IGNORECASE):
                            adj_num += 1
                            prefix = f"Adj {adj_num}"
                            documento_text = 'Adjudicación'
                            fechas_por_documento[documento_text] = fechas_por_documento.get(documento_text, []) + [fecha_text]
                            logging.info(f"Date found on {link}: {fecha_text}, Document: {documento_text}")
                            
                            html_link = cells[1].find_next('td').find('a', 
                                attrs={'title': 'Este documento se abrirá en una nueva ventana', 'target': '_blank'},
                                string='Html'
                            )
                            if html_link and 'href' in html_link.attrs:
                                html_url = urljoin(link, html_link['href'])
                                logging.info(f"Accessing adjudication link (sync): {html_url}")
                                
                                cached_adj_content = get_cached_content(conn, html_url)
                                if cached_adj_content:
                                    logging.info(f"Using cache for {html_url}")
                                    adj_content = cached_adj_content
                                else:
                                    logging.warning(f"Cache miss for adjudication page {html_url}, fetching now")
                                    adj_content = fetch_url_sync(html_url, timeout, conn)
                                    if not adj_content:
                                        logging.error(f"Failed to fetch adjudication page {html_url}")
                                        datos_adjudicacion[f"{prefix}/Error"] = 'Failed to fetch adjudication page'
                                        continue
                                
                                if adj_content:
                                    try:
                                        adj_soup = BeautifulSoup(adj_content, 'lxml', from_encoding='utf-8')
                                    except Exception as e:
                                        logging.warning(f"Error with lxml on {html_url}: {e}. Falling back to html.parser")
                                        adj_soup = BeautifulSoup(adj_content, 'html.parser', from_encoding='utf-8')
                                    
                                    h5_ofertas = None
                                    for tag in ['h5', 'h4', 'h3']:
                                        h5_ofertas = adj_soup.find(tag, string=re.compile(r'(Informaci|Datos).*Oferta.*', re.IGNORECASE))
                                        if h5_ofertas:
                                            h5_text = html.unescape(h5_ofertas.get_text(strip=True))
                                            h5_text_normalized = re.sub(r'[\s\xa0]+', ' ', h5_text).strip()
                                            logging.info(f"Matched <{tag}> with text: '{h5_text_normalized}' on {html_url}")
                                            break
                                    
                                    if not h5_ofertas:
                                        heading_tags = adj_soup.find_all(['h5', 'h4', 'h3'])
                                        heading_texts = [html.unescape(h.get_text(strip=True)) for h in heading_tags]
                                        if heading_tags:
                                            logging.warning(f"No <h5/h4/h3> matched '(Informaci|Datos).*Oferta.*' on {html_url}. Found {len(heading_tags)} heading tags with texts: {heading_texts}")
                                        else:
                                            logging.warning(f"No <h5/h4/h3> tags found at all on {html_url}")
                                        logging.debug(f"HTML content (first 2000 chars) for {html_url}: {adj_content[:2000]}")
                                        if 'Informaci' in adj_content or 'Oferta' in adj_content:
                                            logging.info(f"Raw HTML contains 'Informaci' or 'Oferta', indicating possible parsing issue on {html_url}")
                                    
                                    parent_container = None
                                    if h5_ofertas:
                                        parent_container = h5_ofertas.find_parent('div', class_='boxWithBackground')
                                        if not parent_container:
                                            parent_container = h5_ofertas.find_parent('div')
                                            logging.info(f"No <div class='boxWithBackground'> parent found for <{h5_ofertas.name}> on {html_url}, using nearest <div>")
                                    else:
                                        parent_container = adj_soup.find('div', class_='boxWithBackground')
                                        if parent_container:
                                            logging.info(f"No <h5/h4/h3> found, but located <div class='boxWithBackground'> on {html_url}")
                                        else:
                                            parent_container = adj_soup.find('body')
                                            logging.info(f"No <div class='boxWithBackground'> found, falling back to <body> on {html_url}")
                                    
                                    adj_data = {'Link licitación': link, 'Identificador': identificador}
                                    data_found = False
                                    
                                    for col_class in ['leftCol', 'rigCol','leftCo1', 'rigCo1']:
                                        col_div = parent_container.find('div', class_=col_class)
                                        if col_div:
                                            logging.info(f"Found <div class='{col_class}'> on {html_url}")
                                            ul_elements = col_div.find_all('ul', recursive=False)
                                            for ul in ul_elements:
                                                logging.info(f"Processing <ul> in <div class='{col_class}'> on {html_url}")
                                                for li in ul.find_all('li', recursive=False):
                                                    span = li.find('span')
                                                    if span:
                                                        span_text = span.get_text(strip=True)
                                                        value = None
                                                        for sibling in span.next_siblings:
                                                            if isinstance(sibling, NavigableString):
                                                                text_value = sibling.strip()
                                                                if text_value and text_value != '== $0':
                                                                    value = text_value
                                                                    logging.info(f"Found value as plain text for span '{span_text}' in {col_class} on {html_url}: {value}")
                                                                    break
                                                            elif sibling.name == 'div' and 'noremarca' in sibling.get('class', []):
                                                                value = sibling.get_text(strip=True)
                                                                logging.info(f"Found value in <div class='noremarca'> for span '{span_text}' in {col_class} on {html_url}: {value}")
                                                                break
                                                            elif sibling.name == 'span':
                                                                value = sibling.get_text(strip=True)
                                                                logging.info(f"Found value in <span> for span '{span_text}' in {col_class} on {html_url}: {value}")
                                                                break
                                                        if value:
                                                            key = f"{prefix}/{span_text}"
                                                            datos_adjudicacion[key] = value
                                                            adj_data[span_text] = value
                                                            logging.info(f"Column in {col_class} on {html_url}: {key}, Value: {value}")
                                                            data_found = True
                                                        else:
                                                            logging.warning(f"No value found for span '{span_text}' in {col_class} on {html_url}")
                                                        
                                                        nested_ul = li.find('ul')
                                                        if nested_ul:
                                                            logging.info(f"Nested <ul> found under {span_text} in {col_class} on {html_url}")
                                                            for nested_li in nested_ul.find_all('li', recursive=False):
                                                                nested_span = nested_li.find('span')
                                                                nested_div = nested_li.find('div', class_='noremarca')
                                                                if nested_span and nested_div:
                                                                    nested_span_text = nested_span.get_text(strip=True)
                                                                    nested_value = nested_div.get_text(strip=True)
                                                                    if nested_value:
                                                                        key = f"{prefix}/{nested_span_text}"
                                                                        datos_adjudicacion[key] = nested_value
                                                                        adj_data[nested_span_text] = nested_value
                                                                        logging.info(f"Nested column in {col_class} on {html_url}: {key}, Value: {nested_value}")
                                                                        data_found = True
                                                                elif nested_div:
                                                                    nested_value = nested_div.get_text(strip=True)
                                                                    if nested_value:
                                                                        key = f"{prefix}/{span_text}"
                                                                        datos_adjudicacion[key] = nested_value
                                                                        adj_data[span_text] = nested_value
                                                                        logging.info(f"Nested column (no span) in {col_class} on {html_url}: {key}, Value: {nested_value}")
                                                                        data_found = True
                                        else:
                                            logging.warning(f"No <div class='{col_class}'> found in parent container on {html_url}")
                                    
                                    if data_found and not any(k in adj_data for k in ['Error']):
                                        adjudicaciones.append(adj_data)
                                        logging.info(f"Added adjudication data for {link} to adjudicaciones list")
                                    else:
                                        if not data_found:
                                            datos_adjudicacion[f"{prefix}/Error"] = 'No data found in leftCol or rigCol'
                                            logging.warning(f"No data found in <div class='leftCol'> or <div class='rigCol'> on {html_url}")
                                        if not h5_ofertas:
                                            datos_adjudicacion[f"{prefix}/Error"] = datos_adjudicacion.get(f"{prefix}/Error", '') + '; No <h5/h4/h3> found for Información Sobre las Ofertas'
                            else:
                                datos_adjudicacion[f"{prefix}/Error"] = 'Html link not found'
                                logging.warning(f"Html link not found for adjudication {adj_num} on {link}")
                        else:
                            if documento_text not in fechas_por_documento:
                                fechas_por_documento[documento_text] = []
                            fechas_por_documento[documento_text].append(fecha_text)
                            logging.info(f"Date found on {link}: {fecha_text}, Document: {documento_text}")
        else:
            logging.warning(f"Table myTablaDetalleVISUOE not found on {link}")
        
        resultado = {
            'Identificador': identificador,
            'Link licitación': link,
            'Modificado': modificado
        }
        resultado.update(datos_mod)
        resultado.update(datos_adjudicacion)
        
        for doc, fechas in fechas_por_documento.items():
            col_name = f"Fecha {doc}"
            resultado[col_name] = ', '.join(fechas) if fechas else ''
            if fechas:
                logging.info(f"Dates for {doc} on {link}: {fechas}")
        
        return resultado
    
    except requests.exceptions.SSLError as e:
        logging.error(f"SSL error on {link}: {e}")
        return {
            'Identificador': identificador,
            'Link licitación': link,
            'Modificado': 'Error - SSL Verification Failed'
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error on {link}: {e}")
        return {
            'Identificador': identificador,
            'Link licitación': link,
            'Modificado': 'Error'
        }
    except Exception as e:
        logging.error(f"Unexpected error processing {link}: {e}")
        return {
            'Identificador': identificador,
            'Link licitación': link,
            'Modificado': f'Error - {str(e)}'
        }

# Main function
def main():
    global cache_hits, cache_misses, retry_count, modificaciones, adjudicaciones, failed_urls
    modificaciones = []
    adjudicaciones = []
    failed_urls = []
    conn_cache = setup_cache()
    resultados = []
    
    try:
        conn_data = sqlite3.connect('licitaciones.db')
        cursor = conn_data.cursor()
        cursor.execute("PRAGMA table_info('licitaciones')")
        columns = [info[1] for info in cursor.fetchall()]
        required_columns = ['Identificador', 'Link licitación']
        if not all(col in columns for col in required_columns):
            missing = [col for col in required_columns if col not in columns]
            logging.error(f"Missing required columns in 'licitaciones': {missing}")
            print(f"Error: Missing required columns in 'licitaciones': {missing}")
            conn_data.close()
            conn_cache.close()
            sys.exit(1)
        cursor.execute("SELECT Identificador, [Link licitación] FROM licitaciones")
        rows = cursor.fetchall()
        if not rows:
            logging.error("Database table 'licitaciones' is empty. No rows to process.")
            print("Error: Database table 'licitaciones' is empty. No rows to process.")
            conn_data.close()
            conn_cache.close()
            return resultados
        rows = rows[:100] #-------------------------------------------------------------------------> Modificacar esto para cambiar el numero de filas que procesa
        logging.info(f"Database has {len(rows)} rows (limited to {len(rows)} for testing)")
        print(f"Database has {len(rows)} rows (limited to {len(rows)} for testing)")
    except sqlite3.Error as e:
        logging.error(f"Error accessing database: {e}")
        print(f"Error accessing database: {e}")
        conn_cache.close()
        sys.exit(1)
    
    print("Pre-fetching URLs to populate cache...")
    try:
        asyncio.run(prefetch_urls(rows, TIMEOUT, conn_cache))
    except Exception as e:
        logging.error(f"Error in pre-fetching URLs: {e}")
        print(f"Error in pre-fetching URLs: {e}")
        conn_data.close()
        conn_cache.close()
        sys.exit(1)
    
    for i, row in enumerate(tqdm(rows, total=len(rows), desc="Processing rows")):
        logging.info(f"Processing row {i+1}/{len(rows)}")
        try:
            result = process_row_sync(row, TIMEOUT, conn_cache)
            resultados.append(result)
            logging.info(f"Completed row {i+1}: {row[1]}")
        except Exception as e:
            logging.error(f"Error processing row {i+1} ({row[1]}): {e}")
            print(f"Error processing row {i+1} ({row[1]}): {e}")
            result = {
                'Identificador': row[0],
                'Link licitación': row[1],
                'Modificado': f'Error - {str(e)}'
            }
            resultados.append(result)
    
    logging.info(f"Processed {len(resultados)} rows out of {len(rows)}")
    print(f"Processed {len(resultados)} rows out of {len(rows)}")
    
    output_file = 'resultados_licitaciones.xlsx'
    try:
        df_resultados = pd.DataFrame(resultados)
        df_modificaciones = pd.DataFrame(modificaciones) if modificaciones else pd.DataFrame()
        df_adjudicaciones = pd.DataFrame(adjudicaciones) if adjudicaciones else pd.DataFrame()
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_resultados.to_excel(writer, sheet_name='Resultados', index=False)
            if not df_modificaciones.empty:
                df_modificaciones.to_excel(writer, sheet_name='Modificacion', index=False)
                logging.info(f"Modification data saved to sheet 'Modificacion' in {output_file}")
            else:
                df_modificaciones.to_excel(writer, sheet_name='Modificacion', index=False)
                logging.info(f"No modification data found, 'Modificacion' sheet created with headers")
            if not df_adjudicaciones.empty:
                df_adjudicaciones.to_excel(writer, sheet_name='Adjudicacion', index=False)
                logging.info(f"Adjudication data saved to sheet 'Adjudicacion' in {output_file}")
            else:
                df_adjudicaciones.to_excel(writer, sheet_name='Adjudicacion', index=False)
                logging.info(f"No adjudication data found, 'Adjudicacion' sheet created with headers")
        logging.info(f"Results saved to {output_file} with {len(df_resultados)} rows")
        print(f"Results saved to {output_file} with {len(df_resultados)} rows")
    except Exception as e:
        logging.error(f"Error saving results: {e}")
        print(f"Error saving results: {e}")
    
    total_requests = cache_hits + cache_misses
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    logging.info(f"Cache stats: Hits={cache_hits}, Misses={cache_misses}, Hit Rate={hit_rate:.2f}%")
    logging.info(f"Total retries: {retry_count}")
    print(f"Cache stats: Hits={cache_hits}, Misses={cache_misses}, Hit Rate={hit_rate:.2f}%")
    print(f"Total retries: {retry_count}")
    
    try:
        conn_cache.close()
        if os.path.exists('url_cache.db'):
            os.remove('url_cache.db')
            logging.info("Cache file 'url_cache.db' deleted successfully")
            print("Cache file 'url_cache.db' deleted successfully")
        else:
            logging.info("Cache file 'url_cache.db' does not exist, no cleanup needed")
    except Exception as e:
        logging.error(f"Error deleting cache file 'url_cache.db': {e}")
        print(f"Error deleting cache file 'url_cache.db': {e}")
    
    conn_data.close()
    return resultados

# Run the program
if __name__ == "__main__":
    try:
        conn = sqlite3.connect('licitaciones.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='licitaciones'")
        if not cursor.fetchone():
            logging.error("Table 'licitaciones' not found in database")
            print("Error: Table 'licitaciones' not found in database")
            conn.close()
            sys.exit(1)
        cursor.execute("PRAGMA table_info('licitaciones')")
        columns = [info[1] for info in cursor.fetchall()]
        required_columns = ['Identificador', 'Link licitación']
        if not all(col in columns for col in required_columns):
            logging.error(f"Missing required columns: {[col for col in required_columns if col not in columns]}")
            print(f"Error: Missing required columns: {[col for col in required_columns if col not in columns]}")
            conn.close()
            sys.exit(1)
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        print(f"Error connecting to database: {e}")
        sys.exit(1)
    
    TIMEOUT = 30
    
    start_time = time.time()
    try:
        resultados = main()
    except Exception as e:
        logging.error(f"Error in processing: {e}")
        print(f"Error in processing: {e}")
    
    print(f"Analysis completed. Total time: {time.time() - start_time:.2f} seconds")