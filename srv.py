import googlemaps
import pandas as pd
import time
import os
from datetime import datetime

API_KEY = 'AIzaSyCk6f-HbfNYzNdaOxqVDWyd1h98jKtQ0iE'  

try:
    gmaps = googlemaps.Client(key=API_KEY)
except Exception as e:
    print(f"Error al inicializar el cliente de Google Maps: {e}")
    exit()

def buscar_empresas_zona(lat, lng, radius=5000, tipo=None):
    """
    Busca empresas en un radio específico
    radius: en metros (máximo 50000)
    """
    resultados = []
    
    try:
        if tipo:
            response = gmaps.places_nearby(
                location=(lat, lng),
                radius=radius,
                type=tipo
            )
        else:
            response = gmaps.places_nearby(
                location=(lat, lng),
                radius=radius
            )
        
        resultados.extend(response.get('results', []))
        
        page_count = 1
        while 'next_page_token' in response and page_count < 3:
            time.sleep(2)  
            try:
                response = gmaps.places_nearby(
                    page_token=response['next_page_token']
                )
                resultados.extend(response.get('results', []))
                page_count += 1
            except Exception as e:
                print(f"\nError obteniendo página adicional: {e}")
                break
                
    except googlemaps.exceptions.ApiError as e:
        print(f"\nError de API en coordenadas ({lat}, {lng}): {e}")
    except Exception as e:
        print(f"\nError inesperado en búsqueda: {e}")
    
    return resultados

def extraer_detalles(place_id):
    """
    Obtiene detalles completos de un negocio - SOLO TELEFONO Y WEB
    """
    try:
        result = gmaps.place(place_id, language='es')['result']
        return {
            'telefono': result.get('formatted_phone_number'),
            'telefono_internacional': result.get('international_phone_number'),
            'website': result.get('website'),
        }
    except googlemaps.exceptions.ApiError as e:
        print(f"\nError de API obteniendo detalles: {e}")
        return {}
    except Exception as e:
        print(f"\nError obteniendo detalles de {place_id}: {e}")
        return {}

def buscar_por_texto(query, ciudad, coords):
    """
    Búsqueda por texto en una ciudad específica
    """
    resultados = []
    try:
        response = gmaps.places(
            query=f"{query} en {ciudad}",
            location=coords,
            radius=20000,
            language='es'
        )
        
        resultados.extend(response.get('results', []))
        
        page_count = 1
        while 'next_page_token' in response and page_count < 2:
            time.sleep(2)
            try:
                response = gmaps.places(
                    query=f"{query} en {ciudad}",
                    page_token=response['next_page_token']
                )
                resultados.extend(response.get('results', []))
                page_count += 1
            except:
                break
                
    except Exception as e:
        print(f"\nError en búsqueda por texto '{query}' en {ciudad}: {e}")
    
    return resultados


ciudades_galicia = {
    'A Coruña': (43.3623, -8.4115),
    'Santiago de Compostela': (42.8782, -8.5448),
    'Vigo': (42.2406, -8.7207),
    'Ourense': (42.3367, -7.8648),
    'Lugo': (43.0096, -7.5567),
    'Pontevedra': (42.4298, -8.6446),
    'Ferrol': (43.4847, -8.2330)
}

tipos_negocio = [
    None,  
    'restaurant',
    'store', 
    'lodging',
    'health',
    'finance',
    'shopping_mall',
    'car_repair',
    'gas_station',
    'pharmacy'
]

terminos_busqueda = [
    'empresas', 'industria', 'fábrica', 'oficinas',
    'servicios', 'consultoria', 'tecnologia'
]

print("=== RECOPILADOR DE EMPRESAS DE GALICIA (CON TELÉFONOS Y WEBS) ===")
print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Ciudades a procesar: {len(ciudades_galicia)}")
print("-" * 50)

todas_empresas = []
empresas_procesadas = set()

total_busquedas = len(ciudades_galicia) * 9 * len(tipos_negocio)
busqueda_actual = 0

print("\nFASE 1: Búsqueda por ubicación y tipos de negocio...")

for ciudad, coords in ciudades_galicia.items():
    print(f"\n--- Procesando {ciudad} ---")
    empresas_ciudad = 0
    
    for lat_offset in [-0.05, 0, 0.05]:
        for lng_offset in [-0.05, 0, 0.05]:
            lat = coords[0] + lat_offset
            lng = coords[1] + lng_offset
            
            for tipo in tipos_negocio:
                busqueda_actual += 1
                tipo_str = tipo if tipo else "general"
                print(f"Búsqueda {busqueda_actual}/{total_busquedas} - {ciudad} - Tipo: {tipo_str}", end='\r')
                
                empresas = buscar_empresas_zona(lat, lng, radius=5000, tipo=tipo)
                
                for empresa in empresas:
                    place_id = empresa.get('place_id')
                    
                    if place_id and place_id not in empresas_procesadas:
                        empresas_procesadas.add(place_id)
                        
                       
                        detalles = extraer_detalles(place_id)
                        
                        datos = {
                            'ciudad': ciudad,
                            'place_id': place_id,
                            'nombre': empresa.get('name'),
                            'direccion': empresa.get('vicinity'),
                            'tipos': ', '.join(empresa.get('types', [])),
                            'lat': empresa['geometry']['location']['lat'],
                            'lng': empresa['geometry']['location']['lng'],
                            'rating': empresa.get('rating'),
                            'num_reviews': empresa.get('user_ratings_total'),
                            'abierto_ahora': empresa.get('opening_hours', {}).get('open_now') if empresa.get('opening_hours') else None,
                            'telefono': detalles.get('telefono'),
                            'telefono_internacional': detalles.get('telefono_internacional'),
                            'website': detalles.get('website')
                        }
                        todas_empresas.append(datos)
                        empresas_ciudad += 1
                
                time.sleep(0.5)
    
    print(f"\nEncontradas {empresas_ciudad} empresas únicas en {ciudad}")
    
  
    if todas_empresas:
        df_temp = pd.DataFrame(todas_empresas)
        df_temp.to_csv(f'empresas_galicia_progreso_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', index=False)

print("\n\nFASE 2: Búsqueda por términos específicos...")

for ciudad, coords in ciudades_galicia.items():
    print(f"\n--- Búsqueda por texto en {ciudad} ---")
    
    for termino in terminos_busqueda:
        print(f"Buscando '{termino}' en {ciudad}...", end=' ')
        
        empresas = buscar_por_texto(termino, ciudad, coords)
        nuevas = 0
        
        for empresa in empresas:
            place_id = empresa.get('place_id')
            
            if place_id and place_id not in empresas_procesadas:
                empresas_procesadas.add(place_id)
                
               
                detalles = extraer_detalles(place_id)
                
                datos = {
                    'ciudad': ciudad,
                    'place_id': place_id,
                    'nombre': empresa.get('name'),
                    'direccion': empresa.get('formatted_address', empresa.get('vicinity')),
                    'tipos': ', '.join(empresa.get('types', [])),
                    'lat': empresa['geometry']['location']['lat'],
                    'lng': empresa['geometry']['location']['lng'],
                    'rating': empresa.get('rating'),
                    'num_reviews': empresa.get('user_ratings_total'),
                    'termino_busqueda': termino,
                    'telefono': detalles.get('telefono'),
                    'telefono_internacional': detalles.get('telefono_internacional'),
                    'website': detalles.get('website')
                }
                todas_empresas.append(datos)
                nuevas += 1
        
        print(f"{nuevas} nuevas empresas")
        time.sleep(1)

print("\n\nGuardando resultados finales...")

df = pd.DataFrame(todas_empresas)
df.drop_duplicates(subset=['place_id'], inplace=True)
df.sort_values(['ciudad', 'nombre'], inplace=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# CSV
df.to_csv(f'empresas_galicia_completo_con_telefonos_{timestamp}.csv', index=False, encoding='utf-8-sig')


archivo_excel = f'empresas_galicia_con_telefonos_{timestamp}.xlsx'
df.to_excel(archivo_excel, sheet_name='Empresas Galicia', index=False)

print("\n=== RESUMEN FINAL ===")
print(f"Total empresas encontradas: {len(df)}")
print(f"\nEmpresas por ciudad:")
for ciudad in ciudades_galicia.keys():
    count = len(df[df['ciudad'] == ciudad])
    print(f"  {ciudad}: {count}")


con_telefono = df['telefono'].notna().sum()
con_web = df['website'].notna().sum()
print(f"\nEmpresas con teléfono: {con_telefono} ({con_telefono/len(df)*100:.1f}%)")
print(f"Empresas con website: {con_web} ({con_web/len(df)*100:.1f}%)")

print(f"\nEmpresas por tipo (top 10):")
tipos_split = df['tipos'].str.split(', ', expand=True).stack()
tipo_counts = tipos_split.value_counts().head(10)
for tipo, count in tipo_counts.items():
    print(f"  {tipo}: {count}")

print(f"\nArchivos guardados:")
print(f"  - empresas_galicia_completo_con_telefonos_{timestamp}.csv")
print(f"  - {archivo_excel}")

print(f"\nFinalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")