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

with open('estado_shapefile.yaml') as f: 
    path = yaml.load(f,Loader=yaml.FullLoader)
    path = path['shp_mza_31']
shp_mza = gpd.read_file(path)
shp_mza.to_crs('EPSG:4326',inplace=True)
shp_mza = shp_mza[shp_mza['CVE_MUN']=='050']

start = time.time()
n_samples = 100
shp_mza = shp_mza.sample(n_samples,random_state=12345).reset_index(drop=True)
shp_mza['centroid'] = shp_mza.centroid
latitud = []
longitud = []
for p in shp_mza['centroid']:
    latitud.append(p.y)
    longitud.append(p.x)
points = pd.DataFrame({'CVEGEO':shp_mza['CVEGEO'],'latitud':latitud,'longitud':longitud})

# unidades_economicas = {'supermercados':'462111','minisupers':'462112','vinos_licores':'461211',
#                        'cerveza':'461212','corporativos':'551111','primarias_privadas':'611121',
#                        'primarias_publicas':'611122','hospitales_privados':'622111','hospitales_publicos':'622112'}
# unidades_economicas = {v,k in k,v for zip(unidades_economicas.keys(),unidades_economicas.values())}

unidades_economicas = {'522110':'bancos','primarias_privadas':'611121','611131':'secundarias_privadas',
                       '462111':'supermercados','463310':'calzado_minoreo','463211':'ropa_minoreo',
                       '464121':'lentes_minoreo','622111':'hospitales_privados','461212':'cerveza'}

df = pd.DataFrame()
df['CVEGEO'] = points['CVEGEO']
df['latitud'] = points['latitud']
df['longitud'] = points['longitud']

with open("denue_shapefile.yaml") as f: 
        path = yaml.load(f,Loader=yaml.FullLoader)
path_shp_denue = path['denue_31']

lat = df['latitud']
lon = df['longitud']
metros = 1000
codigo_act = list(unidades_economicas.values())
rue = RadiousUnidadesEconomicas(path_shp_denue=path_shp_denue,
                                codigo_act_dict=unidades_economicas,
                                lat=lat,lon=lon,
                                metros=metros)

df = pd.concat([df,rue],axis=1)

end = time.time()
print('Running time: {:.2f} seconds'.format(end-start))

df.to_csv('casas_sample.csv',index=False)

