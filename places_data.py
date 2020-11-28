import numpy as np
import requests # Para acceder a la API de Google
import re # Para usar regular expressions
import geopandas as gpd # Para leer y manipular shapefiles
from shapely.geometry import Point # Para crear un punto con latitud y longitud
import yaml # Para leer datos como keys y paths
import matplotlib.pyplot as plt 
import pandas as pd
from closest_point import RadiousUnidadesEconomicas
import time

# Cargamos el shapefile
estado = 9
with open('estado_shapefile.yaml') as f: 
    path = yaml.load(f,Loader=yaml.FullLoader)
    path = path[f'shp_mza_{estado}']
shp_mza = gpd.read_file(path)
# Cambiamos el crs
shp_mza.to_crs('EPSG:4326',inplace=True)
# Filtramos por municipio
# mun = '050'
# shp_mza = shp_mza[shp_mza['CVE_MUN']==mun]

start = time.time()
# Tomamos n_sample manzanas al azar
n_samples = 200
shp_mza = shp_mza.sample(n_samples,random_state=12345).reset_index(drop=True)
# Calculamos el centroide
shp_mza['centroid'] = shp_mza.centroid
# Guardamos las coordenadas
latitud = []
longitud = []
for p in shp_mza['centroid']:
    latitud.append(p.y)
    longitud.append(p.x)
points = pd.DataFrame({'CVEGEO':shp_mza['CVEGEO'],'latitud':latitud,'longitud':longitud})

end = time.time()
print('Simulation running time: {:.2f} minutes'.format((end-start)/60))

# Definimos las unidades economicas con un diccionario
# unidades_economicas = {'supermercados':'462111','minisupers':'462112','vinos_licores':'461211',
#                        'cerveza':'461212','corporativos':'551111','primarias_privadas':'611121',
#                        'primarias_publicas':'611122','hospitales_privados':'622111','hospitales_publicos':'622112'}
# unidades_economicas = {v,k in k,v for zip(unidades_economicas.keys(),unidades_economicas.values())}

unidades_economicas = {'522110':'bancos','primarias_privadas':'611121','611131':'secundarias_privadas',
                       '462111':'supermercados','463310':'calzado_minoreo','463211':'ropa_minoreo',
                       '464121':'lentes_minoreo','622111':'hospitales_privados','512130':'cines',
                       '722511':'restaurantes','722515':'cafeterias','721111':'hoteles'}

# Creamos el data frame a imprimir 
df = pd.DataFrame()
df['CVEGEO'] = points['CVEGEO']
df['latitud'] = points['latitud']
df['longitud'] = points['longitud']

# Leemos el shapefile del DENUE
with open("denue_shapefile.yaml") as f: 
        path = yaml.load(f,Loader=yaml.FullLoader)
path_shp_denue = path[f'denue_{estado}']

lat = df['latitud']
lon = df['longitud']
metros = 1000

# Creamos los fetures de número de unidades y distancia 
start = time.time()
rue = RadiousUnidadesEconomicas(path_shp_denue=path_shp_denue,
                                codigo_act_dict=unidades_economicas,
                                lat=lat,lon=lon,
                                metros=metros)
end = time.time()
print('Features running time: {:.2f} minutes'.format((end-start)/60))

df = pd.concat([df,rue],axis=1)

# Exportamos el csv
df.to_csv('casas_sample.csv',index=False)

