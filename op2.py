import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import os
from datetime import datetime

class DirectoriosScraper:
    def __init__(self, usar_selenium=False):
        self.usar_selenium = usar_selenium
        if usar_selenium:
            self.setup_selenium()
        else:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
    
    def setup_selenium(self):
        """Configura Selenium para sitios con JavaScript"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Sin ventana
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def scrape_infobel(self, localidad, categoria=None):
        """Scraper para Infobel España"""
        print(f"\nBuscando en Infobel: {localidad}")
        empresas = []
        
        base_url = "https://www.infobel.com/es/spain"
        
        # Construir URL de búsqueda
        if categoria:
            url = f"{base_url}/business/{categoria.lower()}/{localidad.lower()}"
        else:
            url = f"{base_url}/city/{localidad.lower()}"
        
        try:
            if self.usar_selenium:
                self.driver.get(url)
                time.sleep(3)
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            else:
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar listados de empresas
            for item in soup.find_all('div', class_=['listing-item', 'vcard', 'result-item']):
                empresa = {
                    'fuente': 'Infobel',
                    'localidad': localidad,
                    'categoria': categoria or ''
                }
                
                # Nombre
                nombre_elem = item.find(['h2', 'h3', 'a'], class_=['fn', 'org', 'company-name'])
                if nombre_elem:
                    empresa['nombre'] = nombre_elem.get_text(strip=True)
                
                # Teléfono
                tel_elem = item.find(['span', 'a'], class_=['tel', 'phone'])
                if tel_elem:
                    empresa['telefono'] = tel_elem.get_text(strip=True)
                
                # Dirección
                addr_elem = item.find(['span', 'div'], class_=['adr', 'address'])
                if addr_elem:
                    empresa['direccion'] = addr_elem.get_text(strip=True)
                
                if empresa.get('nombre'):
                    empresas.append(empresa)
            
        except Exception as e:
            print(f"Error en Infobel: {e}")
        
        return empresas
    
    def scrape_qdq(self, localidad, categoria=None):
        """Scraper para QDQ"""
        print(f"\nBuscando en QDQ: {localidad}")
        empresas = []
        
        base_url = "https://www.qdq.com"
        
        # URL de búsqueda
        if categoria:
            url = f"{base_url}/buscar/{categoria}/{localidad}/"
        else:
            url = f"{base_url}/buscar/empresas/{localidad}/"
        
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar listados
            for item in soup.find_all(['div', 'article'], class_=['listado-item', 'vcard', 'listing']):
                empresa = {
                    'fuente': 'QDQ',
                    'localidad': localidad,
                    'categoria': categoria or ''
                }
                
                # Extraer datos según estructura de QDQ
                nombre_elem = item.find(['h2', 'h3', 'span'], class_=['fn', 'org'])
                if nombre_elem:
                    empresa['nombre'] = nombre_elem.get_text(strip=True)
                
                # Teléfono
                tel_elem = item.find('span', class_='tel')
                if not tel_elem:
                    tel_elem = item.find('a', href=lambda x: x and 'tel:' in x)
                if tel_elem:
                    empresa['telefono'] = tel_elem.get_text(strip=True)
                
                # Email
                email_elem = item.find('a', href=lambda x: x and 'mailto:' in x)
                if email_elem:
                    empresa['email'] = email_elem.get('href').replace('mailto:', '')
                
                if empresa.get('nombre'):
                    empresas.append(empresa)
                    
        except Exception as e:
            print(f"Error en QDQ: {e}")
        
        return empresas
    
    def scrape_paginas_amarillas(self, localidad, categoria=None):
        """Scraper para Páginas Amarillas"""
        print(f"\nBuscando en Páginas Amarillas: {localidad}")
        empresas = []
        
        base_url = "https://www.paginasamarillas.es"
        
        # Construir URL
        if categoria:
            url = f"{base_url}/search/{categoria}/all-ma/{localidad}/all-is/all-ci/all-ba/all-pu/all-nc/1"
        else:
            url = f"{base_url}/search/empresas/all-ma/{localidad}/all-is/all-ci/all-ba/all-pu/all-nc/1"
        
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar listados
            for item in soup.find_all('div', class_=['listado-item', 'item', 'row']):
                empresa = {
                    'fuente': 'Páginas Amarillas',
                    'localidad': localidad,
                    'categoria': categoria or ''
                }
                
                # Nombre
                nombre_elem = item.find(['h2', 'h3', 'a'], itemprop='name')
                if not nombre_elem:
                    nombre_elem = item.find('a', class_='business-name')
                if nombre_elem:
                    empresa['nombre'] = nombre_elem.get_text(strip=True)
                
                # Teléfono
                tel_elem = item.find(['span', 'a'], itemprop='telephone')
                if tel_elem:
                    empresa['telefono'] = tel_elem.get_text(strip=True)
                
                # Dirección
                addr_elem = item.find(['span', 'div'], itemprop='address')
                if addr_elem:
                    empresa['direccion'] = addr_elem.get_text(strip=True)
                
                # Web
                web_elem = item.find('a', itemprop='url')
                if web_elem and 'paginasamarillas' not in web_elem.get('href', ''):
                    empresa['web'] = web_elem.get('href')
                
                if empresa.get('nombre'):
                    empresas.append(empresa)
                    
        except Exception as e:
            print(f"Error en Páginas Amarillas: {e}")
        
        return empresas
    
    def scrape_todos(self, localidades=None, categorias=None):
        """Ejecuta scraping en todos los directorios"""
        if not localidades:
            localidades = [
                'A Coruña', 'Santiago de Compostela', 'Vigo', 'Ourense',
                'Lugo', 'Pontevedra', 'Ferrol', 'Narón', 'Vilagarcía de Arousa'
            ]
        
        if not categorias:
            categorias = [
                'restaurantes', 'hoteles', 'construccion', 'informatica',
                'salud', 'educacion', 'transporte', 'industria'
            ]
        
        todas_empresas = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("=== SCRAPER MULTI-DIRECTORIO ===")
        print(f"Localidades: {len(localidades)}")
        print(f"Categorías: {len(categorias)}")
        print("-" * 50)
        
        total = len(localidades) * len(categorias) * 3  # 3 directorios
        actual = 0
        
        for localidad in localidades:
            for categoria in categorias:
                print(f"\n[{actual}/{total}] {localidad} - {categoria}")
                
                # Infobel
                actual += 1
                empresas = self.scrape_infobel(localidad, categoria)
                todas_empresas.extend(empresas)
                time.sleep(2)
                
                # QDQ
                actual += 1
                empresas = self.scrape_qdq(localidad, categoria)
                todas_empresas.extend(empresas)
                time.sleep(2)
                
                # Páginas Amarillas
                actual += 1
                empresas = self.scrape_paginas_amarillas(localidad, categoria)
                todas_empresas.extend(empresas)
                time.sleep(2)
                
                # Guardar progreso cada 10 iteraciones
                if actual % 10 == 0:
                    df_temp = pd.DataFrame(todas_empresas)
                    df_temp.to_csv(f"progreso_scraping_{timestamp}.csv", index=False)
                    print(f"  → Progreso guardado: {len(todas_empresas)} empresas")
        
        # Procesar resultados finales
        if todas_empresas:
            df = pd.DataFrame(todas_empresas)
            
            # Eliminar duplicados
            df['nombre_limpio'] = df['nombre'].str.lower().str.strip()
            df['tel_limpio'] = df['telefono'].str.replace(r'\D', '', regex=True)
            df.drop_duplicates(subset=['nombre_limpio', 'tel_limpio'], inplace=True)
            df.drop(['nombre_limpio', 'tel_limpio'], axis=1, inplace=True)
            
            # Guardar resultados
            archivo_csv = f"empresas_multidirectorio_{timestamp}.csv"
            archivo_excel = f"empresas_multidirectorio_{timestamp}.xlsx"
            
            df.to_csv(archivo_csv, index=False, encoding='utf-8-sig')
            df.to_excel(archivo_excel, index=False)
            
            print(f"\n=== RESUMEN FINAL ===")
            print(f"Total empresas únicas: {len(df)}")
            print(f"Por fuente:")
            for fuente in df['fuente'].unique():
                count = len(df[df['fuente'] == fuente])
                print(f"  - {fuente}: {count}")
            print(f"\nCon teléfono: {df['telefono'].notna().sum()}")
            print(f"Con email: {df['email'].notna().sum() if 'email' in df else 0}")
            print(f"Con web: {df['web'].notna().sum() if 'web' in df else 0}")
            
            print(f"\nArchivos guardados:")
            print(f"  - {archivo_csv}")
            print(f"  - {archivo_excel}")
        
        if self.usar_selenium:
            self.driver.quit()

# Instalación de dependencias necesarias
def instalar_dependencias():
    print("Instalando dependencias necesarias...")
    import subprocess
    import sys
    
    packages = ['requests', 'beautifulsoup4', 'pandas', 'selenium', 'openpyxl', 'lxml']
    
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("\nPara usar Selenium, también necesitas:")
    print("1. Descargar ChromeDriver: https://chromedriver.chromium.org/")
    print("2. Añadirlo al PATH o especificar la ruta en el código")

if __name__ == "__main__":
    print("=== SCRAPER DE DIRECTORIOS EMPRESARIALES ===")
    print("\n1. Scraping básico (sin JavaScript)")
    print("2. Scraping avanzado (con Selenium)")
    print("3. Instalar dependencias")
    
    opcion = input("\nElige opción (1-3): ")
    
    if opcion == '1':
        scraper = DirectoriosScraper(usar_selenium=False)
        scraper.scrape_todos()
    elif opcion == '2':
        scraper = DirectoriosScraper(usar_selenium=True)
        scraper.scrape_todos()
    elif opcion == '3':
        instalar_dependencias()
    else:
        print("Opción no válida")