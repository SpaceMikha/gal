import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from datetime import datetime
import json
from urllib.parse import urljoin, quote
import re

class PaxinasGalegasScraper:
    def __init__(self):
        self.base_url = "https://www.paxinasgalegas.es"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.empresas = []
        self.delay = 1  # Segundos entre requests
        
    def obtener_categorias(self):
        """Obtiene todas las categorías principales del sitio"""
        print("Obteniendo categorías principales...")
        
        try:
            # La página de categorías suele estar en /empresas o similar
            urls_a_probar = [
                f"{self.base_url}/empresas",
                f"{self.base_url}/categorias",
                f"{self.base_url}/directorio",
                self.base_url
            ]
            
            for url in urls_a_probar:
                response = self.session.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Buscar enlaces de categorías (adaptar según estructura real)
                    categorias = []
                    
                    # Patrones comunes para encontrar categorías
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        texto = link.get_text(strip=True)
                        
                        # Filtrar enlaces que parecen categorías
                        if any(palabra in href.lower() for palabra in ['categoria', 'sector', 'empresas', 'actividad']):
                            if texto and len(texto) > 2:
                                categorias.append({
                                    'nombre': texto,
                                    'url': urljoin(self.base_url, href)
                                })
                    
                    if categorias:
                        print(f"Encontradas {len(categorias)} categorías")
                        return categorias
                        
                time.sleep(self.delay)
                
        except Exception as e:
            print(f"Error obteniendo categorías: {e}")
        
        # Si no encontramos categorías, usar una lista predefinida
        return self.categorias_predefinidas()
    
    def categorias_predefinidas(self):
        """Lista de categorías comunes en directorios gallegos"""
        categorias_comunes = [
            "Alimentación", "Automoción", "Construcción", "Educación",
            "Hostelería", "Industria", "Informática", "Inmobiliaria",
            "Salud", "Servicios", "Textil", "Transporte", "Turismo"
        ]
        
        return [
            {
                'nombre': cat,
                'url': f"{self.base_url}/empresas/{quote(cat.lower())}"
            }
            for cat in categorias_comunes
        ]
    
    def buscar_por_localidad(self, localidad):
        """Busca empresas por localidad"""
        print(f"\nBuscando empresas en {localidad}...")
        
        # Intentar diferentes formatos de URL
        urls_busqueda = [
            f"{self.base_url}/buscar?q={quote(localidad)}",
            f"{self.base_url}/empresas/{quote(localidad.lower())}",
            f"{self.base_url}/localidad/{quote(localidad.lower())}",
            f"{self.base_url}/search?location={quote(localidad)}"
        ]
        
        for url in urls_busqueda:
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    return self.extraer_empresas_de_pagina(response.content, localidad)
                time.sleep(self.delay)
            except Exception as e:
                print(f"Error en búsqueda de {localidad}: {e}")
                
        return []
    
    def extraer_empresas_de_pagina(self, html_content, localidad=""):
        """Extrae información de empresas de una página"""
        soup = BeautifulSoup(html_content, 'html.parser')
        empresas_encontradas = []
        
        # Patrones comunes para encontrar empresas
        # Opción 1: Divs o articles con clase específica
        for contenedor in soup.find_all(['div', 'article', 'li'], class_=re.compile(r'empresa|company|listing|result|negocio', re.I)):
            empresa = self.extraer_datos_empresa(contenedor, localidad)
            if empresa and empresa.get('nombre'):
                empresas_encontradas.append(empresa)
        
        # Opción 2: Si no encontramos con clases, buscar por estructura
        if not empresas_encontradas:
            # Buscar patrones de teléfono para identificar bloques de empresas
            telefonos = soup.find_all(text=re.compile(r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{3}\b'))
            for telefono in telefonos:
                parent = telefono.parent
                while parent and parent.name not in ['div', 'article', 'li', 'section']:
                    parent = parent.parent
                if parent:
                    empresa = self.extraer_datos_empresa(parent, localidad)
                    if empresa and empresa.get('nombre'):
                        empresas_encontradas.append(empresa)
        
        return empresas_encontradas
    
    def extraer_datos_empresa(self, contenedor, localidad=""):
        """Extrae los datos de una empresa de su contenedor HTML"""
        empresa = {
            'nombre': '',
            'direccion': '',
            'telefono': '',
            'email': '',
            'web': '',
            'categoria': '',
            'localidad': localidad,
            'descripcion': ''
        }
        
        # Extraer nombre (usualmente en h2, h3, o strong)
        for tag in ['h2', 'h3', 'h4', 'strong', 'a']:
            nombre_elem = contenedor.find(tag)
            if nombre_elem and nombre_elem.get_text(strip=True):
                empresa['nombre'] = nombre_elem.get_text(strip=True)
                break
        
        # Extraer teléfono
        telefono_pattern = re.compile(r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{3}\b')
        telefono_match = telefono_pattern.search(contenedor.get_text())
        if telefono_match:
            empresa['telefono'] = telefono_match.group()
        
        # Extraer email
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        email_match = email_pattern.search(contenedor.get_text())
        if email_match:
            empresa['email'] = email_match.group()
        
        # Extraer web
        for link in contenedor.find_all('a', href=True):
            href = link['href']
            if 'http' in href and 'paxinasgalegas' not in href:
                empresa['web'] = href
                break
        
        # Extraer dirección (buscar texto que contenga palabras clave)
        texto_completo = contenedor.get_text()
        direccion_keywords = ['Rúa', 'Rua', 'Avenida', 'Av.', 'Plaza', 'Praza', 'C/', 'Calle']
        for keyword in direccion_keywords:
            if keyword in texto_completo:
                # Extraer línea que contiene la palabra clave
                lineas = texto_completo.split('\n')
                for linea in lineas:
                    if keyword in linea:
                        empresa['direccion'] = linea.strip()
                        break
        
        return empresa
    
    def scrape_completo(self, localidades=None):
        """Ejecuta el scraping completo"""
        if not localidades:
            localidades = [
                'A Coruña', 'Santiago de Compostela', 'Vigo', 'Ourense',
                'Lugo', 'Pontevedra', 'Ferrol', 'Vilagarcía de Arousa',
                'Narón', 'Oleiros', 'Carballo', 'Redondela', 'Cangas',
                'Marín', 'Ponteareas', 'Lalín', 'Monforte de Lemos'
            ]
        
        print(f"=== SCRAPER DE PÁGINAS GALEGAS ===")
        print(f"Localidades a procesar: {len(localidades)}")
        print("-" * 50)
        
        # Crear directorio para guardar progreso
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        progreso_dir = f"scraping_paxinas_{timestamp}"
        os.makedirs(progreso_dir, exist_ok=True)
        
        todas_empresas = []
        
        for i, localidad in enumerate(localidades):
            print(f"\n[{i+1}/{len(localidades)}] Procesando {localidad}")
            
            empresas_localidad = self.buscar_por_localidad(localidad)
            
            if empresas_localidad:
                todas_empresas.extend(empresas_localidad)
                print(f"  → Encontradas {len(empresas_localidad)} empresas")
                
                # Guardar progreso
                df_temp = pd.DataFrame(todas_empresas)
                df_temp.to_csv(f"{progreso_dir}/progreso_{i+1}.csv", index=False)
            else:
                print(f"  → No se encontraron empresas")
            
            # Pausa entre localidades
            time.sleep(self.delay * 2)
        
        # Guardar resultado final
        if todas_empresas:
            df_final = pd.DataFrame(todas_empresas)
            
            # Eliminar duplicados
            df_final.drop_duplicates(subset=['nombre', 'telefono'], inplace=True)
            
            # Guardar en diferentes formatos
            archivo_csv = f"empresas_paxinas_galegas_{timestamp}.csv"
            archivo_excel = f"empresas_paxinas_galegas_{timestamp}.xlsx"
            
            df_final.to_csv(archivo_csv, index=False, encoding='utf-8-sig')
            df_final.to_excel(archivo_excel, index=False)
            
            print(f"\n=== RESUMEN FINAL ===")
            print(f"Total empresas encontradas: {len(df_final)}")
            print(f"Empresas con teléfono: {df_final['telefono'].notna().sum()}")
            print(f"Empresas con email: {df_final['email'].notna().sum()}")
            print(f"Empresas con web: {df_final['web'].notna().sum()}")
            print(f"\nArchivos guardados:")
            print(f"  - {archivo_csv}")
            print(f"  - {archivo_excel}")
        else:
            print("\nNo se encontraron empresas")
    
    def busqueda_avanzada(self, termino_busqueda):
        """Realiza una búsqueda por término específico"""
        print(f"\nBuscando: {termino_busqueda}")
        
        url_busqueda = f"{self.base_url}/buscar"
        params = {
            'q': termino_busqueda,
            'tipo': 'empresas'
        }
        
        try:
            response = self.session.get(url_busqueda, params=params)
            if response.status_code == 200:
                return self.extraer_empresas_de_pagina(response.content)
        except Exception as e:
            print(f"Error en búsqueda: {e}")
        
        return []

# Función principal
def main():
    print("=== SCRAPER DE PÁGINAS GALEGAS ===")
    print("\nOpciones:")
    print("1. Buscar por localidades predefinidas")
    print("2. Buscar por localidad específica")
    print("3. Buscar por término")
    print("4. Scraping completo")
    
    opcion = input("\nElige una opción (1-4): ")
    
    scraper = PaxinasGalegasScraper()
    
    if opcion == '1':
        scraper.scrape_completo()
    elif opcion == '2':
        localidad = input("Introduce la localidad: ")
        empresas = scraper.buscar_por_localidad(localidad)
        if empresas:
            df = pd.DataFrame(empresas)
            archivo = f"empresas_{localidad.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(archivo, index=False)
            print(f"\nEncontradas {len(empresas)} empresas")
            print(f"Guardado en: {archivo}")
    elif opcion == '3':
        termino = input("Introduce el término de búsqueda: ")
        empresas = scraper.busqueda_avanzada(termino)
        if empresas:
            df = pd.DataFrame(empresas)
            archivo = f"empresas_busqueda_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(archivo, index=False)
            print(f"\nEncontradas {len(empresas)} empresas")
            print(f"Guardado en: {archivo}")
    elif opcion == '4':
        print("\n⚠️  ADVERTENCIA:")
        print("El scraping completo puede tardar varias horas")
        print("Se respetarán los tiempos de espera para no sobrecargar el servidor")
        
        confirmar = input("\n¿Continuar? (si/no): ")
        if confirmar.lower() == 'si':
            scraper.scrape_completo()
    else:
        print("Opción no válida")

if __name__ == "__main__":
    main()