#get the json here: https://gesdb.sandia.gov/projects.html
import pandas
import numpy as np
import glob
from flatten_json import flatten_json
import json

import geopandas
import shapely.geometry
import shapely.ops
import pyproj
import pandas

import time
import numpy

import pygsheets
import cartopy
import matplotlib.pyplot as mp
import matplotlib
from numpy import *

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as grid_spec
import matplotlib.ticker as ticker

from pylab import *
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point, shape, LinearRing,LineString
from matplotlib.ticker import FormatStrFormatter
import matplotlib.gridspec as gridspec
from matplotlib import gridspec
import cartopy.crs as ccrs

from textwrap import wrap
import seaborn as sns
import matplotlib.pyplot as plt
from json import loads, dumps
#LOAD THE GIPT DATA
gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/August update/Global Integrated Power August 2024.xlsx',sheet_name='Power facilities')
#
## ADJUST 'not found' VALUES IN COMPILED EXCEL
gipt.loc[gipt['Capacity (MW)']=='not found','Capacity (MW)']=np.nan
## CHANGE 'Capacity' TO FLOATS
gipt['Capacity (MW)']=gipt['Capacity (MW)'].astype(float)
gipt['Capacity (MW)']=gipt['Capacity (MW)'].fillna(0.0)
# EXCLUDE MISSING START DATES 
gipt.loc[gipt['Start year']=='not found','Start year']=np.nan
gipt['Start year']=gipt['Start year'].astype(float)
gipt.loc[gipt['Retired year']=='not found','Retired year']=np.nan
gipt['Retired year']=gipt['Retired year'].astype(float)


#OPERATING
iea_reg_map=pandas.read_excel("C:/Users/james/Documents/GEM/GIPT/iea_region_code.xlsx")
names=list(iea_reg_map[iea_reg_map['G7']=='Yes'].gem_name.unique())
status=['operating']
#gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))].groupby(['Region','Subregion','Country/area','Type'])['Capacity (MW)'].sum()#.unstack()/1000


types=['coal', 'bioenergy', 'hydropower', 'geothermal', 'wind', 'solar','nuclear', 'oil/gas']
type_names=['Coal', 'Bioenergy', 'Hydropower', 'Geothermal', 'Wind', 'Utility-scale solar','Nuclear', 'Oil and gas']
res=[]
for type,name in zip(types,type_names):
	tmp=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))&(gipt.Type==type)].groupby(['Region','Subregion','Country/area'])['Capacity (MW)'].sum().reset_index()
	tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000
	tmp['Power source']=name
	tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
	tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
	res.append(tmp.to_json(orient='records'))


with open("C:/Users/james/Documents/GEM/GIPT/BRICS/json/gipt_operating_g7_v1.json", 'w') as f:
    f.write('['+','.join(res).replace('[','').replace(']','')+']')



#IN DEVEOPMENT
status=['announced','construction','pre-construction']
result=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))].groupby(['Country/area','Type','Status'])['Capacity (MW)'].sum().reset_index().pivot(index = ['Country/area','Type'], columns='Status',values='Capacity (MW)').reset_index().fillna(0.0)
result.columns=['Country', 'Source', 'Announced', 'Construction','Pre-construction']
result=result[['Country', 'Source', 'Construction','Pre-construction','Announced']]

with open("C:/Users/james/Documents/GEM/GIPT/BRICS/json/gipt_development_g7_v1.json", 'w') as f:
    f.write(result.to_json(orient='records'))



##CONSTRUCTION
iea_reg_map=pandas.read_excel("C:/Users/james/Documents/GEM/GIPT/iea_region_code.xlsx")
names=list(iea_reg_map[iea_reg_map['G7']=='Yes'].gem_name.unique())
status=['construction']

types=['coal', 'bioenergy', 'hydropower', 'geothermal', 'wind', 'solar','nuclear', 'oil/gas']
type_names=['Coal', 'Bioenergy', 'Hydropower', 'Geothermal', 'Wind', 'Utility-scale solar','Nuclear', 'Oil and gas']
res=[]
for type,name in zip(types,type_names):
	tmp=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))&(gipt.Type==type)].groupby(['Region','Subregion','Country/area'])['Capacity (MW)'].sum().reset_index()
	tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000
	tmp['Power source']=name
	tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
	tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
	res.append(tmp.to_json(orient='records'))


with open("C:/Users/james/Documents/GEM/GIPT/BRICS/json/gipt_construction_g7_v1.json", 'w') as f:
    f.write('['+','.join(res).replace('[','').replace(']','')+']')


##OPERATING#
status=['operating','announced','construction','pre-construction']
gipt_copy=gipt.copy()
gipt_copy.loc[gipt_copy.Type=='coal','Type']='Fossil'
gipt_copy.loc[gipt_copy.Type=='oil/gas','Type']='Fossil'
gipt_copy.loc[gipt_copy.Type!='Fossil','Type']='Clean'


result=gipt_copy[(gipt_copy.Status.isin(status))&(gipt_copy['Country/area'].isin(names))].groupby(['Country/area','Status','Type'])['Capacity (MW)'].sum().reset_index().pivot(index = ['Country/area','Status'], columns='Type',values='Capacity (MW)').reset_index().fillna(0.0)
result.columns=['Country','Status','Fossil','Clean']


with open("C:/Users/james/Documents/GEM/GIPT/BRICS/json/gipt_type_status_g7_v1.json", 'w') as f:
    f.write(result.to_json(orient='records'))














