import numpy as np
import pandas as pd
import requests # Para acceder a la API de Google
import re # Para usar regular expressions
import geopandas as gpd # Para leer y manipular shapefiles
from shapely.geometry import Point # Para crear un punto con latitud y longitud
import yaml # Para leer datos como keys y paths
import time
from tabulate import tabulate


def RadiousUnidadesEconomicas(*,path_shp_denue:str,codigo_act_dict:dict,lat:[float,list],lon:[float,list],metros=2000,google_api_key=None,google=False)->dict:
    '''
    A partir de un radio fijo cuenta el número de unidades económicas del código especificado
    y la mínima duración en coche a alguna de las unidades, no solo en la circunferencia
    La duración se da en minutos.
    Si no hay unidades devuelve NaN en la duración. 
    ----------
    Inputs: 
            - path_shp_denue_estado: str, path al shapefile de la denue, de preferencia de un estado específico
            - codigo_act_dict: dict, código de 6 dígitos del DENUE, key=clave y value=nombre
            - lat: list o float, latitudes 
            - lon: list o float, longitudes 
            - metros: float, metros a buscar
            - google_api_key: str, key de google para usar Distance Matrix API
            - google: boole, si usa o no la API de Google 
    Outputs: 
            - DataFrame con duración mínima y número de unidades 
    '''

    # Cargamos el shapefile del DENUE 
    denue = gpd.read_file(path_shp_denue)

    # Convertimos en lista el código de actividad
    codigo_act = list(codigo_act_dict.keys())
    
    # Ver si lat,lon son iterables, sino crea una lista
    try: 
        iter(lat)
    except: 
        lat = [lat]

    try: 
        iter(lon)
    except: 
        lon = [lon]

    # DataFrame de resultados
    df = pd.DataFrame()

    for codigo in codigo_act: 
        actividad = codigo_act_dict[codigo]
        # Filtramos el DENUE con código de actividad 
        denue_codigo = denue[denue['codigo_act']==codigo].copy()

        # Si no hay esta unidad en el estado devolvemos 0's y NaN's
        if len(denue_codigo)==0:
            numero_unidades_radius = [0 for _ in range(len(lat))]
            distance = [np.nan for _ in range(len(lat))]

        else: 
            # Cambiamos el sistema de coordenadas
            denue_codigo.to_crs("EPSG:4326",inplace=True)

            numero_unidades_radius = []
            distance = []
            for Lat,Lon in zip(lat,lon):
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
                inter = gpd.overlay(denue_codigo, circle, how='intersection')
                # El número de unidades al rededor del punto es len(inter)
                numero_unidades_radius.append(len(inter))
                
                # Usamos la API Distance Matrix de Google para medir el tiempo en vehículo a la UE más cercana
                # (no necesariemnte en la circunferencia)
                # La API tiene un límite de 100=(origenes)*(destinos) elementos, así que filtramos los 100 
                # destinos más cercanos en el sentido lineal
                # La API se usa sólo si google = True
                # (Sé que es tonto poner el if adentro del for, pero fue mi solución rápida) 
                denue_codigo['distance_to_point'] = denue_codigo['geometry'].apply(lambda p: np.sqrt((p.x-pt.x)**2+(p.y-pt.y)**2)/alpha)
                denue_codigo = denue_codigo.sort_values(by='distance_to_point',ascending=True)
                denue_codigo.reset_index(drop=True,inplace=True)
                denue_codigo = denue_codigo.loc[0:99,:]

                if google: 
                    # Hacemos un string con los destinos a los que se quiere medir la distancia
                    destinations = ''
                    for x in denue_codigo[['latitud','longitud']].values:
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
                    distance.append(duration.min())

                else: 
                    distance.append(denue_codigo.loc[0,'distance_to_point'])
        
            # Devolvemos el número de unidades y la duración mínima
            df.loc[:,actividad+'_numero'] = numero_unidades_radius
            if google: 
                df.loc[:,actividad+'_duracion'] = distance
            else: 
                df.loc[:,actividad+'_distancia'] = distance

    return df

if __name__=='__main__':
    # Estado: Yucatán 
    # Ubicación: mi casa
    # Unidades económicas: 462111 supermercado, 462112 minisuper
    # Radio fijo: 1 km
    
    # Leemos shapefile de la denue de un yaml
    with open("denue_shapefile.yaml") as f: 
        path = yaml.load(f,Loader=yaml.FullLoader)
        path_shp_denue = path['denue_31']

    codigo_act_dict = {'462111':'supermercado','462112':'minisuper'}
    lat = [21.015963,20.994841]
    lon = [-89.590495,-89.612894]
    metros = 1000

    # Para leer mi API key del archivo yaml
    with open("google_api_keys.yaml","r") as f:
        keys = yaml.load(f,Loader=yaml.FullLoader)
        google_api_key = keys['Distance Matrix']

    start = time.time()
    rue = RadiousUnidadesEconomicas(path_shp_denue=path_shp_denue,
                                    codigo_act_dict=codigo_act_dict,
                                    lat=lat,lon=lon,
                                    metros=metros)
    end = time.time()

    print('Running time: {:.2f} seconds'.format(end-start))
    print(tabulate(rue, headers='keys', tablefmt='psql'))
# +----+-----------------------+--------------------------+--------------------+-----------------------+
# |    |   supermercado_numero |   supermercado_distancia |   minisuper_numero |   minisuper_distancia |
# |----+-----------------------+--------------------------+--------------------+-----------------------|
# |  0 |                     2 |                  904.303 |                  4 |               253.328 |
# |  1 |                     4 |                  888.521 |                  6 |               389.087 |
# +----+-----------------------+--------------------------+--------------------+-----------------------+
