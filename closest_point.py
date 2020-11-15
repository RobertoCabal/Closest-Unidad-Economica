import numpy as np
import requests # Para acceder a la API de Google
import re # Para usar regular expressions
import geopandas as gpd # Para leer y manipular shapefiles
from shapely.geometry import Point # Para crear un punto con latitud y longitud
import yaml # Mi API key la guardo en un archivo yaml


def RadiousUnidadesEconomicas(path_shp_denue,codigo_act,google_api_key,lat,lon,metros=2000,max_metros=20000,distance_only=False):
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
    denue = denue[denue['codigo_act'].apply(lambda x: x in codigo_act)] 
    # Cambiamos el sistema de coordenadas
    denue.to_crs("EPSG:4326",inplace=True)
    # Creamos un punto el la coordenada proporcionada
    pt = gpd.GeoSeries([Point(lon,lat)])

    # Si sólo queremos la distancia mínima cambiamos los metros
    if distance_only: 
        metros = max_metros

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

    # Si no hay intersecciones entonces devolvemos NaN
    if len(inter)==0:
        if distance_only:
            return {'duracion_minima_minutos':np.nan}
        else:
            return {'numero_unidades':0,'duracion_minima_minutos':np.nan}
    # Si sí hay intersecciones entonces usamos la API Distance Matrix de Google
    else: 
        # Hacemos un string con los destinos a los que se quiere medir la distancia
        destinations = ''
        for x in inter[['latitud','longitud']].values:
            destinations += str(x[0])+','+str(x[1])+'|'
        destinations = destinations[:-1]
        # Especificamos los otros parámetros de la API
        outputFormat = 'json'
        units = 'imperial'
        origins = '{},{}'.format(lat,lon)
        mode = 'driving'
        parameters = 'units={}&origins={}&destinations={}&mode={}&key={}'.format(units,origins,destinations,mode,google_api_key)
        url_google = 'https://maps.googleapis.com/maps/api/distancematrix/{}?{}'.format(outputFormat,parameters)
        # Llamamos a la API con requests
        r_google = requests.get(url_google)
        # Leemos el resultado de la API como JSON
        d = r_google.json()
        # Almacenamos las duraciones en coche (en minutos) a cada destino, i.e., unidad económica
        duration = []
        for z in d['rows'][0]['elements']: 
            d = z['duration']['text']
            # quitamos letras y nos quedamos con números
            d = re.sub('[a-z]','',d) 
            d = float(d)
            duration.append(d)
        # Obtenemos la dración mínima 
        duration = np.array(duration)
        closest_duration = duration.min()
        if distance_only:
            return {'duracion_minima_minutos':closest_duration}
        else:
            return {'numero_unidades':len(inter),'duracion_minima_minutos':closest_duration}


if __name__=='__main__':
    # Estado: Yucatán 
    # Ubicación: mi casa
    # Unidades económicas: 61211 Comercio al por menor de vinos y licores
    #                      461212 Comercio al por menor de cerveza
    #                      461213 Comercio al por menor de bebidas no alcohólicas y hielo
    # Radio fijo: 1 km
    
    # El path del shapefile lo guardo en un yaml
    with open("denue_shapefile.yaml") as f: 
        path = yaml.load(f,Loader=yaml.FullLoader)
        path_shp_denue = path['denue_31']

    codigo_act = ['461211','461212','461213']
    lat,lon = 21.015963,-89.590495
    metros = 1000
    # Para leer mi API key del archivo yaml
    with open("google_api_keys.yaml","r") as f:
        keys = yaml.load(f,Loader=yaml.FullLoader)
        google_api_key = keys['Distance Matrix']

    rue = RadiousUnidadesEconomicas(path_shp_denue,codigo_act,google_api_key,lat,lon,metros)
    print(rue)
    # {'numero_unidades': 7, 'duracion_minima_minutos': 2.0}
