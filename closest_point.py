import numpy as np
import requests # Para acceder a la API de Google
import re # Para usar regular expressions
import geopandas as gpd # Para leer y manipular shapefiles
from shapely.geometry import Point # Para crear un punto con latitud y longitud
import yaml # Para leer datos como keys y paths
import time


def RadiousUnidadesEconomicas(path_shp_denue:str,codigo_act:[str,list],google_api_key:str,lat:[float,list],lon:[float,list],metros=2000)->dict:
    '''
    A partir de un radio fijo cuenta el número de unidades 
    y la mínima duración en coche (a alguna de las unidades).
    Si distance_only=True solo devuelve la duración, pues no nos interesa el número de unidades. En este caso 
    busca hasta un radio de max_metros.
    La duración se da en minutos.
    Si no hay unidades devuelve NaN.
    ----------
    Inputs: 
            - path_shp_denue_estado: str, path al shapefile de la denue, de preferencia de un estado específico
            - codigo_act: list o str, código de 6 dígitos del DENUE
            - google_api_key: str, key de google para usar Distance Matrix API
            - lat: float, latitud 
            - lon: float, longitud 
            - metros: float, metros a buscar
            - max_metros: float, máximo de metros para buscar, solo se usa su distance_only=True
            - distance_only: boole, indica que solo queremos buscar la unidad más cercana
    Outputs: 
            - dict con duración mínima y número de unidades si distance_only=False
    '''

    # Cargamos el shapefile del DENUE 
    denue = gpd.read_file(path_shp_denue)
    # Convertimos en lista el código de actividad
    if type(codigo_act)!=list: 
        codigo_act = [codigo_act]
    # Filtramos el DENUE con código de actividad 
    if len(codigo_act)==1:
        denue = denue[denue['codigo_act']==codigo_act[0]]
    else:
        denue = denue[denue['codigo_act'].apply(lambda x: x in codigo_act)] 
    
    # Ver si lat,lon son iterables, sino crea una lista
    try: 
        iter(lat)
    except: 
        lat = [lat]

    try: 
        iter(lon)
    except: 
        lon = [lon]

    # Si no hay esta unidad en el estado devolvemos 0's y NaN's
    if len(denue)==0:
        return {'numero_unidades_radius':[0 for _ in range(len(lat))],
                'duracion_minima_minutos':[np.nan for _ in range(len(lat))]}
    else: 
        # Cambiamos el sistema de coordenadas
        denue.to_crs("EPSG:4326",inplace=True)

        numero_unidades_radius = []
        duracion_minima_minutos = []
        for Lat,Lon in zip(lat,lon):
            print(Lat,Lon)
            # Creamos un punto el la coordenada proporcionada
            pt = gpd.GeoSeries([Point(Lon,Lat)])

            # alpha es una constante para traducir metros en el crs especificado
            alpha = 0.005/550
            # Creamos la circunferencia con los metros especificados
            circle = pt.buffer(metros*alpha)
            # Convertimos el punto en un GeoDataFrame 
            circle = gpd.GeoDataFrame(circle,columns=['geometry'])
            # Cambiamos el sistema de coordenadas para que coicidan
            circle.set_crs("EPSG:4326",inplace=True)
            # Obtenemos la base con las intersecciones geográficas (puntos que caen en la circunferencia)
            inter = gpd.overlay(denue, circle, how='intersection')
            # El número de unidades al rededor del punto es len(inter)
            numero_unidades_radius.append(len(inter))
            
            # Usamos la API Distance Matrix de Google para medir el tiempo en vehículo a la UE más cercana
            # (no necesariemnte en la circunferencia)
            # La API tiene un límite de 100=(origenes)*(destinos) elementos, así que filtramos los 100 
            # destinos más cercanos en el sentido lineal
            denue['distance_to_point'] = denue['geometry'].apply(lambda p: (p.x-pt.x)**2+(p.y-pt.y)**2)
            denue = denue.sort_values(by='distance_to_point',ascending=True)
            denue.reset_index(drop=True,inplace=True)
            denue = denue.loc[0:99,:]

            # Hacemos un string con los destinos a los que se quiere medir la distancia
            destinations = ''
            for x in denue[['latitud','longitud']].values:
                destinations += str(x[0])+','+str(x[1])+'|'
            destinations = destinations[:-1]
            # Especificamos los otros parámetros de la API
            outputFormat = 'json'
            units = 'imperial'
            origins = f'{Lat},{Lon}'
            mode = 'driving'
            parameters = f'units={units}&origins={origins}&destinations={destinations}&mode={mode}&key={google_api_key}'
            url_google = f'https://maps.googleapis.com/maps/api/distancematrix/{outputFormat}?{parameters}'
            # Llamamos a la API con requests
            r_google = requests.get(url_google)
            # Leemos el resultado de la API como JSON
            d = r_google.json()
            # Almacenamos las duraciones en coche (en minutos) a cada destino, i.e., unidad económica
            duration = []
            for z in d['rows'][0]['elements']: 
                d = z['duration']['text']
                # quitamos letras y nos quedamos con números
                if 'hour' in d:
                    h = re.sub('[a-z]','',d).strip().split()[0]
                    m = re.sub('[a-z]','',d).strip().split()[1]
                    h = float(h)
                    m = float(m)
                    d = 60*h+m
                else:
                    d = re.sub('[a-z]','',d) 
                    d = float(d)
                duration.append(d)
            # Obtenemos la dración mínima 
            duration = np.array(duration)
            duracion_minima_minutos.append(duration.min())
        
        # Devolvemos el número de unidades y la duración mínima
        return {'numero_unidades_radius':numero_unidades_radius,'duracion_minima_minutos':duracion_minima_minutos}


if __name__=='__main__':
    # Estado: Yucatán 
    # Ubicación: mi casa
    # Unidades económicas: 462111 supermercado
    # Radio fijo: 1 km
    
    # Leemos shapefile de la denue de un yaml
    with open("denue_shapefile.yaml") as f: 
        path = yaml.load(f,Loader=yaml.FullLoader)
        path_shp_denue = path['denue_31']

    codigo_act = '462111'
    lat = [21.015963,20.994841]
    lon = [-89.590495,-89.612894]
    metros = 1000

    # Para leer mi API key del archivo yaml
    with open("google_api_keys.yaml","r") as f:
        keys = yaml.load(f,Loader=yaml.FullLoader)
        google_api_key = keys['Distance Matrix']

    start = time.time()
    rue = RadiousUnidadesEconomicas(path_shp_denue,codigo_act,google_api_key,lat,lon,metros)
    end = time.time()

    print('Running time: {:.2f} seconds'.format(end-start))
    print(rue)
    # {'numero_unidades_radius': 2, 'duracion_minima_minutos': 4.0}
