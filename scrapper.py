#!/usr/bin/env python3
"""
Scraper Blogger CON PAGINACIÓN

Descarga TODOS los posts siguiendo los links de "Entradas antiguas".
Sigue la navegación hasta capturar todos los posts.

Requisitos:
    pip install requests beautifulsoup4
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import sys
import re
import time


BLOG_URL = "https://elpozodeestrellas.blogspot.com"
OUTPUT_DIR = Path("data/textos")
DELAY = 1  # segundos entre requests (respetuoso)


def extraer_posts_de_pagina(url_pagina, numero_pagina=1):
    """
    Extrae posts de una página específica.
    """
    
    print(f"  Página {numero_pagina}: {url_pagina[-50:]}")
    
    try:
        response = requests.get(url_pagina, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return [], None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    posts = []
    
    # Busca todos los posts en esta página
    todos_los_posts = soup.find_all('div', class_='post')
    
    for post_div in todos_los_posts:
        
        # Solo procesa posts válidos (tienen itemprop='blogPost')
        if post_div.get('itemprop') != 'blogPost':
            continue
        
        # Extrae título
        titulo_elem = post_div.find('h3', class_='post-title')
        if not titulo_elem:
            continue
        
        titulo = titulo_elem.get_text(strip=True)
        
        # Extrae contenido
        contenido_div = post_div.find('div', class_='post-body')
        if not contenido_div:
            continue
        
        contenido = limpiar_html(str(contenido_div))
        
        # Intenta extraer fecha del post (si la tiene)
        fecha = "2025-01-01"
        fecha_elem = post_div.find(['span', 'time'], class_=['post-date', 'published'])
        if fecha_elem:
            fecha_str = fecha_elem.get_text(strip=True)
            fecha = parsear_fecha(fecha_str)
        
        if titulo and contenido:
            posts.append({
                'titulo': titulo,
                'contenido': contenido,
                'fecha': fecha
            })
    
    # Busca link a "siguiente página" (posts anteriores)
    siguiente_url = None
    
    # Estrategia 1: Busca por parámetro updated-max (Blogger search)
    todos_los_links = soup.find_all('a')
    for link in todos_los_links:
        href = link.get('href', '')
        # Busca links con parámetro updated-max (Blogger pagination)
        if 'updated-max=' in href and 'search' in href:
            siguiente_url = href
            break
    
    # Estrategia 2: Busca en el paginador (blog-pager)
    if not siguiente_url:
        pager = soup.find('div', class_=['blog-pager', 'pager', 'post-pager'])
        if pager:
            links = pager.find_all('a')
            for link in links:
                texto = link.get_text().lower()
                # Busca links que digan "anterior", "older", "siguientes", "más antiguas"
                if any(word in texto for word in ['anterior', 'older', 'siguientes', 'más antiguas', 'entradas antiguas']):
                    siguiente_url = link.get('href')
                    break
    
    # Estrategia 3: Si aún no encontró, busca cualquier link en blog-pager que no sea la página actual
    if not siguiente_url:
        pager = soup.find('div', class_='blog-pager')
        if pager:
            for link in pager.find_all('a'):
                href = link.get('href', '')
                if href and href != url_pagina:
                    siguiente_url = href
                    break
    
    time.sleep(DELAY)
    
    return posts, siguiente_url


def parsear_fecha(fecha_str):
    """Parsea fecha en formato Blogger español."""
    
    if not fecha_str:
        return "2025-01-01"
    
    meses_es = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    fecha_lower = fecha_str.lower()
    
    mes_num = None
    for mes_nombre, mes_numero in meses_es.items():
        if mes_nombre in fecha_lower:
            mes_num = mes_numero
            break
    
    if not mes_num:
        return "2025-01-01"
    
    numeros = re.findall(r'\d+', fecha_str)
    if len(numeros) >= 2:
        dia = numeros[0].zfill(2)
        año = numeros[-1]
        return f"{año}-{mes_num}-{dia}"
    
    return "2025-01-01"


def limpiar_html(html_text):
    """Convierte HTML a texto limpio."""
    
    soup = BeautifulSoup(html_text, 'html.parser')
    
    for tag in soup(['script', 'style', 'noscript', 'meta']):
        tag.decompose()
    
    for link in soup.find_all('a'):
        href = link.get('href', '#')
        text = link.get_text(strip=True)
        if text:
            link.replace_with(f"[{text}]({href})")
    
    texto = soup.get_text(separator='\n')
    lineas = [linea.strip() for linea in texto.split('\n')]
    lineas = [linea for linea in lineas if linea]
    
    return '\n\n'.join(lineas)


def categorizar(titulo):
    """Categoriza post."""
    
    titulo_lower = titulo.lower()
    fruta_keys = ['fruta', 'estación', 'estacion', 'real', 'histórico', 'historico', 'hecho']
    
    if any(key in titulo_lower for key in fruta_keys):
        return "Fruta de Estacion"
    
    return "Cuento"


def crear_markdown(titulo, contenido, fecha, categoria):
    """Crea Markdown con header YAML."""
    
    titulo_yaml = titulo.replace('"', '\\"')
    
    yaml_header = f"""---
titulo: "{titulo_yaml}"
categoria: "{categoria}"
fecha: "{fecha}"
tema: []
---

"""
    
    return yaml_header + contenido


def main():
    
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Scraper Blogger CON PAGINACIÓN                      ║")
    print("║  (Sigue 'Entradas antiguas' hasta fin)               ║")
    print("╚═══════════════════════════════════════════════════════╝\n")
    
    print(f"📚 Blog: {BLOG_URL}\n")
    print("🔍 Siguiendo paginación...\n")
    
    todos_posts = []
    pagina_actual = BLOG_URL
    numero_pagina = 1
    max_paginas = 10  # Límite de seguridad (5-10 páginas debería ser suficiente para 30 posts)
    
    # Descarga todas las páginas
    while pagina_actual and numero_pagina <= max_paginas:
        
        posts, siguiente_url = extraer_posts_de_pagina(pagina_actual, numero_pagina)
        
        todos_posts.extend(posts)
        print(f"    ✓ Encontrados {len(posts)} posts")
        
        if not siguiente_url:
            print(f"    (Fin de paginación)")
            break
        
        pagina_actual = siguiente_url
        numero_pagina += 1
    
    # Quita duplicados
    vistos = set()
    posts_unicos = []
    for post in todos_posts:
        if post['titulo'] not in vistos:
            vistos.add(post['titulo'])
            posts_unicos.append(post)
    
    if not posts_unicos:
        print("\n❌ No se encontraron posts")
        sys.exit(1)
    
    # Ordena por fecha
    posts_unicos.sort(key=lambda p: p['fecha'])
    
    print(f"\n✓ Total: {len(posts_unicos)} posts únicos encontrados\n")
    
    # Crea carpeta
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"📝 Generando archivos Markdown...\n")
    
    # Escribe archivos
    for i, post in enumerate(posts_unicos, 1):
        
        titulo = post['titulo']
        contenido = post['contenido']
        fecha = post['fecha']
        categoria = categorizar(titulo)
        
        nombre_archivo = titulo.lower()
        nombre_archivo = re.sub(r'[^a-záéíóúñ0-9\s]', '', nombre_archivo)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)[:40]
        
        filename = OUTPUT_DIR / f"{i:03d}_{nombre_archivo}.md"
        
        markdown = crear_markdown(titulo, contenido, fecha, categoria)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            cat_icon = "📖" if categoria == "Cuento" else "📰"
            print(f"  {cat_icon} [{i:2d}] {titulo[:50]:50} | {fecha}")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n{'='*70}")
    print(f"✅ ÉXITO: {len(posts_unicos)} archivos en {OUTPUT_DIR}/")
    print(f"{'='*70}")
    print(f"\n📋 Próximos pasos:")
    print(f"  1. Revisa los archivos")
    print(f"  2. Agrega tus 10 textos locales")
    print(f"  3. Estás listo para Fase 1 (MVP RAG)\n")


if __name__ == '__main__':
    main()