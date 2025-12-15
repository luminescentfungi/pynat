import requests, json, re

def obtener_coords(city):
    # Esta es la API que usa Leaflet por detrás para buscar ciudades
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': city,
        'format': 'json',
        'limit': 1
    }
    HEADERS = {'User-Agent': 'MiScriptPython/1.0'} # Nominatim requiere User-Agent
    
    resp = requests.get(url, params=params, HEADERS=HEADERS)
    data = resp.json()
    
    if data:
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        print(f"Coordenadas de {city}: {lat}, {lon}")
        return lat, lon
    print("No se encontraron resultados.",resp)
    return None, None

city = input('Ingrese ciudad: ')
lat, lon = obtener_coords(city)
archivo = 'ohnat-map.js'

with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
    contenido = f.read()

# Buscamos el patrón donde empieza la lista de usuarios (buscando la clave única "KeyWho")
# Esto extrae todo el bloque JSON que está mezclado entre el código Javascript
match = re.search(r'(\[\s*\{.*?KeyWho.*?\}\s*\])', contenido, re.DOTALL)

if match:
    # Convertimos ese texto a una lista real de Python
    datos_usuarios = json.loads(match(1))
    margen = 0.15 # Unos 5km a la redonda

    ids = []
    
    print(f"Total de usuarios en la base de datos: {len(datos_usuarios)}")
    
    for user in datos_usuarios:
        try:
            lat_ = float(user['latitude'])
            lon_ = float(user['longitude'])
            
            # Filtramos los que caen cerca de Barcelona
            if (lat - margen < lat_ < lat + margen) and \
               (lon - margen < lon_ < lon + margen):
                ids.append(user['KeyWho'])
        except:
            continue

    print(f"Usuarios encontrados en {city}: {len(ids)}")
    print("IDs:", ids)
else:
    print("No pude encontrar la variable de datos dentro del JS.")