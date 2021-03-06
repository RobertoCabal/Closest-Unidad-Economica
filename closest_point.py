import numpy as np
import pandas as pd
import requests # Para acceder a la APIs
import re # Para usar regular expressions
import geopandas as gpd # Para leer y manipular shapefiles
from shapely.geometry import Point # Para crear un punto con latitud y longitud
import yaml # Para leer datos como keys y paths
import time
from tabulate import tabulate


def RadiousUnidadesEconomicas(*,path_shp_denue:str,codigo_act_dict:dict,lat:[float,list],lon:[float,list],metros=2000):
    '''
    A partir de un radio fijo cuenta el número de unidades económicas del código especificado
    y la mínima distancia lineal al punto (posiblemente fuera de la circunferencia)
    Si no hay unidades devuelve NaN en la distancia. 
    ----------
    Inputs: 
            - path_shp_denue_estado: str, path al shapefile de la denue, de preferencia de un estado específico
            - codigo_act_dict: dict, código de 6 dígitos del DENUE, key=clave y value=nombre
            - lat: list o float, latitudes 
            - lon: list o float, longitudes 
            - metros: float, metros a buscar
    Outputs: 
            - DataFrame con duración mínima y número de unidades 
    '''

    # Cargamos el shapefile del DENUE 
    denue = gpd.read_file(path_shp_denue)

    # Convertimos en lista el código de actividad
    codigo_act = list(codigo_act_dict.keys())
    
    # Ver si lat,lon son iterables, sino crea una lista
     if isinstance(lat,str): 
        lat = float(lat)
    
    if isinstance(lon,str): 
        lon = float(lon)

    try: 
        for i,x in enumerate(lat): 
            lat[i] = float(x)
    except: 
        lat = [lat]

    try: 
       for i,x in enumerate(lon): 
            lon[i] = float(x)
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

                # Calculamos la distancia euclediana 
                denue_codigo['distance_to_point'] = denue_codigo['geometry'].apply(lambda p: np.sqrt((p.x-pt.x)**2+(p.y-pt.y)**2)/alpha)
                # Ordenamos por la distancia de menor a mayor
                denue_codigo = denue_codigo.sort_values(by='distance_to_point',ascending=True)
                denue_codigo.reset_index(drop=True,inplace=True)
                # Nos quedamos con la distancia lineal más pequeña
                distance.append(np.round(denue_codigo.loc[0,'distance_to_point'],2))
        
            # Devolvemos el número de unidades y la duración mínima
            df.loc[:,actividad+'_numero'] = numero_unidades_radius
            df.loc[:,actividad+'_distancia'] = distance

    return df


def RadiousKeyWord(*,path_shp_denue:str,key_words_list:list,lat:[float,list],lon:[float,list],metros=2000):
    '''
    A partir de un radio fijo cuenta el número de unidades económicas con la palabra clave especificada
    y la mínima distancia lineal al punto (posiblemente fuera de la circunferencia)
    Si no hay unidades devuelve NaN en la distancia. 
    ----------
    Inputs: 
            - path_shp_denue_estado: str, path al shapefile de la denue, de preferencia de un estado específico
            - key_words_list: list, palabras clave sobre el nombre del establecimiento
            - lat: list o float, latitudes 
            - lon: list o float, longitudes 
            - metros: float, metros a buscar
    Outputs: 
            - DataFrame con duración mínima y número de unidades 
    '''

    # Cargamos el shapefile del DENUE 
    denue = gpd.read_file(path_shp_denue)

    # Convertimos en lista las palabras clave 
    if isinstance(key_words_list, list):
        pass 
    else: 
        key_words_list = [key_words_list] 
    
    # Ver si lat,lon son iterables, sino crea una lista
    if isinstance(lat,str): 
        lat = float(lat)
    
    if isinstance(lon,str): 
        lon = float(lon)

    try: 
        for i,x in enumerate(lat): 
            lat[i] = float(x)
    except: 
        lat = [lat]

    try: 
       for i,x in enumerate(lon): 
            lon[i] = float(x)
    except: 
        lon = [lon]

    # DataFrame de resultados
    df = pd.DataFrame()

    for k in key_words_list: 
        # Filtramos el DENUE con el nombre clave 
        k = k.strip().upper()
        denue_codigo = denue[denue['nom_estab'].str.contains(k)].copy()

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

                # Calculamos la distancia euclediana 
                denue_codigo['distance_to_point'] = denue_codigo['geometry'].apply(lambda p: np.sqrt((p.x-pt.x)**2+(p.y-pt.y)**2)/alpha)
                # Ordenamos por la distancia de menor a mayor
                denue_codigo = denue_codigo.sort_values(by='distance_to_point',ascending=True)
                denue_codigo.reset_index(drop=True,inplace=True)
                # Nos quedamos con la distancia lineal más pequeña
                distance.append(np.round(denue_codigo.loc[0,'distance_to_point'],2))
        
            # Devolvemos el número de unidades y la duración mínima
            df.loc[:,actividad+'_numero'] = numero_unidades_radius
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
