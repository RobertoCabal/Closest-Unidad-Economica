import numpy as np
import requests # Para acceder a la API de Google
import re # Para usar regular expressions
import geopandas as gpd # Para leer y manipular shapefiles
from shapely.geometry import Point # Para crear un punto con latitud y longitud
import yaml # Para leer datos como keys y paths
import matplotlib.pyplot as plt 
import pandas as pd
from closest_point import RadiousUnidadesEconomicas

with open('estado_shapefile.yaml') as f: 
    path = yaml.load(f,Loader=yaml.FullLoader)
    path = path['shp_mza_31']
shp_mza = gpd.read_file(path)
shp_mza.to_crs('EPSG:4326',inplace=True)
shp_mza = shp_mza[shp_mza['CVE_MUN']=='050']

n_samples = 100
shp_mza = shp_mza.sample(n_samples,random_state=12345).reset_index(drop=True)
shp_mza['centroid'] = shp_mza.centroid
latitud = []
longitud = []
for p in shp_mza['centroid']:
    latitud.append(p.y)
    longitud.append(p.x)
points = pd.DataFrame({'CVEGEO':shp_mza['CVEGEO'],'latitud':latitud,'longitud':longitud})

unidades_economicas = {'supermercados':'462111','minisupers':'462112','vinos_licores':'461211',
                       'cerveza':'461212','corporativos':'551111','primarias_privadas':'611121',
                       'primarias_publicas':'611122','hospitales_privados':'622111','hospitales_publicos':'622112'}

df = pd.DataFrame()
df['CVEGEO'] = points['CVEGEO']
df['latitud'] = points['latitud']
df['longitud'] = points['longitud']
for k in unidades_economicas.keys():
    df[k] = np.nan
    df[k+'_tiempo'] = np.nan

metros = 1000
with open("denue_shapefile.yaml") as f: 
        path = yaml.load(f,Loader=yaml.FullLoader)
path_shp_denue = path['denue_31']

with open("google_api_keys.yaml","r") as f:
    keys = yaml.load(f,Loader=yaml.FullLoader)
google_api_key = keys['Distance Matrix']


for i in range(len(df)):
    for k in unidades_economicas.keys():
        codigo_act = unidades_economicas[k]
        lat = df.loc[i,'latitud']
        lon = df.loc[i,'longitud']
        rue = RadiousUnidadesEconomicas(path_shp_denue,codigo_act,google_api_key,lat,lon,metros)
        df.loc[i,k] = rue['numero_unidades']
        df.loc[i,k+'_tiempo'] = rue['duracion_minima_minutos']

# df.to_csv('casas_sample.csv',index=False)

