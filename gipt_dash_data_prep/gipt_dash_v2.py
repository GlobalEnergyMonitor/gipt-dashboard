import pandas
import numpy as np
import glob
from flatten_json import flatten_json
import json
import pandas
import numpy
from numpy import *
from json import loads, dumps

'''
1) text config file (the sentence under the drop down)
2) tickers
3) chart #1: OPERATNG
4) chart #2: CONSTRUCTION
5) chart #3: DEVELOPMENT
6) chart #4: FOSSIL / NON-FOSSIL

'''

################################################################################################################################################
#0: LOAD THE GIPT DATA
#gipt=pandas.read_excel('C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/Global Integrated Power January 2025.xlsx',sheet_name='Power facilities')
gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/Feb_2025_GIPT_update (GCPT)/Global Integrated Power February 2025.xlsx',sheet_name='Power facilities')
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
gipt.loc[gipt.Status=='cancelled - inferred 4 y','Status']='cancelled'
gipt.loc[gipt.Status=='shelved - inferred 2 y','Status']='shelved'


(gipt[(gipt.Type.isin(['wind','solar']))&(gipt.Status.isin(['announced','construction','pre-construction']))].groupby(['Country/area'])['Capacity (MW)'].sum()/1000).sort_values()


(gipt[(gipt['Country/area']=='Japan')&(gipt.Status.isin(['construction','pre-construction','announced']))].groupby(['Type'])['Capacity (MW)'].sum()/1000).sort_values()


(gipt[(gipt['Country/area']=='Japan')&(gipt.Status.isin(['construction']))].groupby(['Type'])['Capacity (MW)'].sum()/1000).sort_values()

##Make a list of all the individual countries to include

exclude=['American Samoa',
'Aruba',
'Bahamas',
'Bonaire, Sint Eustatius, and Saba',
'Christmas Island',
'Comoros',
'Dominica',
'Grenada',
'Greenland',
'Guam',
'Guernsey',
'Holy See',
'Isle of Man',
'Jersey',
'Åland Islands',
'Tonga',
'Timor-Leste',
'Saint Lucia',
'Saint Kitts and Nevis']


all_countries=sort(gipt[~(gipt['Country/area'].isin(exclude))]['Country/area'].unique())



################################################################################################################################################
#1: TEXT CONFIG:
tmp=pandas.DataFrame(columns=['Country','overall_summary'])
for i in ['World','BRICS','EU27','G7','G20','OECD','African Union']+list(all_countries):
	tmp.loc[i]=[i,' ']


with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_textconfig_v3.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))


################################################################################################################################################
#2: TICKERS
iea_reg_map=pandas.read_excel("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/iea_region_code.xlsx")
regions=['BRICS','EU27','G7','G20','OECD','African Union']
status=['construction']
type=['coal','oil/gas']
res=[]
#World
res.append(pandas.DataFrame(['World',gipt[(gipt.Status.isin(status))&(~gipt.Type.isin(type))]['Capacity (MW)'].sum()/1000.,gipt[(gipt.Status.isin(status))&(gipt.Type.isin(type))]['Capacity (MW)'].sum()/1000.],['Country','summary_1','summary_2']).T)
#Regions
for reg in regions:
	names=list(iea_reg_map[iea_reg_map[reg]=='Yes'].gem_name.unique())
	res.append(pandas.DataFrame([reg,gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))&(~gipt.Type.isin(type))]['Capacity (MW)'].sum()/1000.,gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))&(gipt.Type.isin(type))]['Capacity (MW)'].sum()/1000.],['Country','summary_1','summary_2']).T)

#Countries
for country in sort(gipt['Country/area'].unique()):
	res.append(pandas.DataFrame([country,gipt[(gipt.Status.isin(status))&(gipt['Country/area']==country)&(~gipt.Type.isin(type))]['Capacity (MW)'].sum()/1000.,gipt[(gipt.Status.isin(status))&(gipt['Country/area']==country)&(gipt.Type.isin(type))]['Capacity (MW)'].sum()/1000.],['Country','summary_1','summary_2']).T)

tmp=pandas.concat(res)

def rounder(number):
	if number>=100:
		return int(round(number, 0))
	elif ((number<100)&(number>=1)):
		return round(number, 1)
	else:
		return round(number, 2)

#tmp["summary_1"]=tmp["summary_1"].astype(float)
#tmp["summary_2"]=tmp["summary_2"].astype(float)

tmp.summary_1=['<span>{{'+str(rounder(i))+ '}} GW</span><br>non-fossil power capacity<br>under construction' for i in tmp["summary_1"]]
tmp.summary_2=['<span>{{'+str(rounder(i))+ '}} GW</span><br>fossil fuel capacity<br>under construction' for i in tmp["summary_2"]]

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_data_ticker_feb2025_v1.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))


################################################################################################################################################
#3: OPERATING
status=['operating']
types=['coal', 'bioenergy', 'hydropower', 'geothermal', 'wind', 'solar','nuclear', 'oil/gas']
type_names=['Coal', 'Bioenergy', 'Hydropower', 'Geothermal', 'Wind', 'Utility-scale solar','Nuclear', 'Oil and gas']
res=[]
#World
for type,name in zip(types,type_names):
	tmp=pandas.DataFrame(array(['Region','subregion','World',''])).T
	tmp.columns=['Region', 'Sub-region', 'Country','Capacity (MW)']
	tmp['Capacity (MW)']=gipt[(gipt.Status.isin(status))&(gipt.Type==type)]['Capacity (MW)'].sum()
	tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000.
	tmp['Power source']=name
	tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
	tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
	res.append(tmp.to_json(orient='records'))

res_world=gipt[(gipt.Status.isin(status))].groupby('Type')['Capacity (MW)'].sum()
res_world['Country/Area']='World'

#Region
regions=['BRICS','EU27','G7','G20','OECD','African Union']
res_regs=[]
for reg in regions:
	names=list(iea_reg_map[iea_reg_map[reg]=='Yes'].gem_name.unique())
	for type,name in zip(types,type_names):
		tmp=pandas.DataFrame(array(['Region','subregion',reg,''])).T
		tmp.columns=['Region', 'Sub-region', 'Country','Capacity (MW)']
		tmp['Capacity (MW)']=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))&(gipt.Type==type)]['Capacity (MW)'].sum()
		tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000.
		tmp['Power source']=name
		tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
		tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
		res.append(tmp.to_json(orient='records'))
	res_reg=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))].groupby('Type')['Capacity (MW)'].sum()
	res_reg['Country/Area']=reg
	res_regs.append(res_reg)

pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T])


#Countries
res_country=[]
for country in all_countries:
	for type,name in zip(types,type_names):
		tmp=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin([country]))&(gipt.Type==type)].groupby(['Region','Subregion','Country/area'])['Capacity (MW)'].sum().reset_index()
		if len(tmp)==0:
			tmp=pandas.DataFrame(array(['Region','subregion',country,''])).T
			tmp.columns=['Region', 'Sub-region', 'Country','Capacity (MW)']
			tmp['Capacity (MW)']=0.
			tmp['Power source']=name
			tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
			tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
			res.append(tmp.to_json(orient='records'))
		else:
			tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000
			tmp['Power source']=name
			tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
			tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
			res.append(tmp.to_json(orient='records'))
	res_c=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin([country]))].groupby('Type')['Capacity (MW)'].sum()
	res_c['Country/Area']=country
	res_country.append(res_c)


pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T,pandas.concat(res_country,axis=1).T]).fillna(0.)[['Country/Area','coal', 'oil/gas', 'solar', 'wind', 'hydropower','nuclear', 'bioenergy', 'geothermal']].to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_operating_feb2025_v1.csv")

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_operating_feb2025_v1.json", 'w') as f:
    f.write('['+','.join(res).replace('[','').replace(']','')+']')


################################################################################################################################################
##4: CONSTRUCTION
status=['construction']
types=['coal', 'bioenergy', 'hydropower', 'geothermal', 'wind', 'solar','nuclear', 'oil/gas']
type_names=['Coal', 'Bioenergy', 'Hydropower', 'Geothermal', 'Wind', 'Utility-scale solar','Nuclear', 'Oil and gas']
res=[]
#World
for type,name in zip(types,type_names):
	tmp=pandas.DataFrame(array(['Region','subregion','World',''])).T
	tmp.columns=['Region', 'Sub-region', 'Country','Capacity (MW)']
	tmp['Capacity (MW)']=gipt[(gipt.Status.isin(status))&(gipt.Type==type)]['Capacity (MW)'].sum()
	tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000.
	tmp['Power source']=name
	tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
	tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
	res.append(tmp.to_json(orient='records'))

res_world=gipt[(gipt.Status.isin(status))].groupby('Type')['Capacity (MW)'].sum()
res_world['Country/Area']='World'

#Region
res_regs=[]
regions=['BRICS','EU27','G7','G20','OECD','African Union']
for reg in regions:
	names=list(iea_reg_map[iea_reg_map[reg]=='Yes'].gem_name.unique())
	for type,name in zip(types,type_names):
		tmp=pandas.DataFrame(array(['Region','subregion',reg,''])).T
		tmp.columns=['Region', 'Sub-region', 'Country','Capacity (MW)']
		tmp['Capacity (MW)']=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))&(gipt.Type==type)]['Capacity (MW)'].sum()
		tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000.
		tmp['Power source']=name
		tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
		tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
		res.append(tmp.to_json(orient='records'))
	res_reg=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))].groupby('Type')['Capacity (MW)'].sum()
	res_reg['Country/Area']=reg
	res_regs.append(res_reg)

#Countries
res_country=[]
for country in all_countries:
	for type,name in zip(types,type_names):
		tmp=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin([country]))&(gipt.Type==type)].groupby(['Region','Subregion','Country/area'])['Capacity (MW)'].sum().reset_index()
		if len(tmp)==0:
			tmp=pandas.DataFrame(array(['Region','subregion',country,''])).T
			tmp.columns=['Region', 'Sub-region', 'Country','Capacity (MW)']
			tmp['Capacity (MW)']=0.
			tmp['Power source']=name
			tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
			tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
			res.append(tmp.to_json(orient='records'))
		else:
			tmp['Capacity (MW)']=tmp['Capacity (MW)'].fillna(0.0)/1000
			tmp['Power source']=name
			tmp.columns=['Region', 'Sub-region', 'Country', name,'Power source']
			tmp=tmp[['Region', 'Sub-region', 'Country', 'Power source',name]]
			res.append(tmp.to_json(orient='records'))
	res_c=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin([country]))].groupby('Type')['Capacity (MW)'].sum()
	res_c['Country/Area']=country
	res_country.append(res_c)


pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T,pandas.concat(res_country,axis=1).T]).fillna(0.)[['Country/Area','coal', 'oil/gas', 'solar', 'wind', 'hydropower','nuclear', 'bioenergy', 'geothermal']].to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_construction_feb2025_v1.csv")

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_construction_feb2025_v1.json", 'w') as f:
    f.write('['+','.join(res).replace('[','').replace(']','')+']')

################################################################################################################################################
#5: DEVEOPMENT
status=['announced','construction','pre-construction']
res=[]
#World
result=gipt[(gipt.Status.isin(status))].groupby(['Type','Status'])['Capacity (MW)'].sum().reset_index()
result['Country/area']='World'
result=result.pivot(index = ['Country/area','Type'], columns='Status',values='Capacity (MW)').reset_index().fillna(0.0)
result.columns=['Country', 'Source', 'Announced', 'Construction','Pre-construction']
result=result[['Country', 'Source', 'Construction','Pre-construction','Announced']]
res.append(result)

#Region
regions=['BRICS','EU27','G7','G20','OECD','African Union']
for reg in regions:
	names=list(iea_reg_map[iea_reg_map[reg]=='Yes'].gem_name.unique())
	result=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin(names))].groupby(['Type','Status'])['Capacity (MW)'].sum().reset_index()
	result['Country/area']=reg
	result=result.pivot(index = ['Country/area','Type'], columns='Status',values='Capacity (MW)').reset_index().fillna(0.0)
	result.columns=['Country', 'Source', 'Announced', 'Construction','Pre-construction']
	result=result[['Country', 'Source', 'Construction','Pre-construction','Announced']]
	res.append(result)

#Country
types=['coal', 'bioenergy', 'hydropower', 'geothermal', 'wind', 'solar','nuclear', 'oil/gas']
for country in all_countries:
	result=gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin([country]))].groupby(['Country/area','Type','Status'])['Capacity (MW)'].sum().reset_index().pivot(index = ['Country/area','Type'], columns='Status',values='Capacity (MW)').reset_index().fillna(0.0)
	missing=set(status)-set(list(gipt[(gipt.Status.isin(status))&(gipt['Country/area'].isin([country]))].Status.unique()))
	if len(missing)>0:
		for i in missing:
			result[i]=0
	missing=set(types)-set(list(result.Type))
	if len(missing)>1:
		for i in missing:
			result=pandas.concat([result,pandas.DataFrame([country,i,0,0,0],index=['Country/area', 'Type', 'announced', 'construction','pre-construction']).T])
	result=result[['Country/area','Type','construction','pre-construction','announced']]
	result.columns=['Country', 'Source', 'Construction','Pre-construction','Announced']
	res.append(result)

tmp=pandas.concat(res)
tmp.loc[tmp.Source=='bioenergy','Source'] = 'Bioenergy'
tmp.loc[tmp.Source=='coal','Source'] = 'Coal'
tmp.loc[tmp.Source=='oil/gas','Source'] = 'Oil and gas'
tmp.loc[tmp.Source=='geothermal','Source'] = 'Geothermal'
tmp.loc[tmp.Source=='hydropower','Source'] = 'Hydropower'
tmp.loc[tmp.Source=='nuclear','Source'] = 'Nuclear'
tmp.loc[tmp.Source=='solar','Source'] = 'Utility-scale solar'
tmp.loc[tmp.Source=='wind','Source'] = 'Wind'

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_development_feb2025_v1.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))

tmp.fillna(0.).to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_dev_feb2025_v1.csv")


################################################################################################################################################
##6: FOSSIL / NON-FOSISL SPLIT
status=['operating','announced','construction','pre-construction']
gipt_copy=gipt.copy()
gipt_copy.loc[gipt_copy.Type=='coal','Type']='Fossil'
gipt_copy.loc[gipt_copy.Type=='oil/gas','Type']='Fossil'
gipt_copy.loc[gipt_copy.Type!='Fossil','Type']='Non-fossil'
res=[]
#World
result=gipt_copy[(gipt_copy.Status.isin(status))].groupby(['Status','Type'])['Capacity (MW)'].sum().reset_index().pivot(index = ['Status'], columns='Type',values='Capacity (MW)').reset_index().fillna(0.0)
result['Country']='World'
result=result[['Country','Status','Fossil','Non-fossil']]
res.append(result.loc[[0,3,1,2]])
#Regions
for reg in regions:
	names=list(iea_reg_map[iea_reg_map[reg]=='Yes'].gem_name.unique())
	result=gipt_copy[(gipt_copy.Status.isin(status))&(gipt['Country/area'].isin(names))].groupby(['Status','Type'])['Capacity (MW)'].sum().reset_index().pivot(index = ['Status'], columns='Type',values='Capacity (MW)').reset_index().fillna(0.0)
	result['Country']=reg
	result=result[['Country','Status','Fossil','Non-fossil']]
	res.append(result.loc[[0,3,1,2]])

#Countries
for country in all_countries:
	result=gipt_copy[(gipt_copy.Status.isin(status))&(gipt['Country/area'].isin([country]))].groupby(['Country/area','Status','Type'])['Capacity (MW)'].sum().reset_index().pivot(index = ['Country/area','Status'], columns='Type',values='Capacity (MW)').reset_index().fillna(0.0)
	missing=set(['Country/area', 'Status', 'Fossil','Non-fossil'])-set(result.columns)
	if len(missing)>0:
		for i in missing:
			result[i]=0
	missing=set(['operating','announced','construction','pre-construction'])-set(list(result.Status))
	if len(missing)>0:
		for i in missing:
			result=pandas.concat([result,pandas.DataFrame([country,i,0,0],index=['Country/area','Status','Fossil','Non-fossil']).T])
	result=result[['Country/area', 'Status', 'Fossil','Non-fossil']]
	result.columns=['Country', 'Status', 'Fossil','Non-fossil']
	res.append(result.sort_values('Status').reset_index()[['Country', 'Status', 'Fossil','Non-fossil']].loc[[0,3,1,2]])



tmp=pandas.concat(res)
tmp=tmp[['Country', 'Status','Non-fossil', 'Fossil']]

tmp.loc[tmp.Status=='announced','Status'] = 'Announced'
tmp.loc[tmp.Status=='construction','Status'] = 'Construction'
tmp.loc[tmp.Status=='pre-construction','Status'] = 'Pre-construction'
tmp.loc[tmp.Status=='operating','Status'] = 'Operating'

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_fossil_nonfossil_feb2025_v1.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))



tmp['Non-fossil share']=tmp['Non-fossil'].astype(float).divide(tmp['Non-fossil'].astype(float)+tmp['Fossil'].astype(float))
tmp['Fossil share']=tmp['Fossil'].astype(float).divide(tmp['Non-fossil'].astype(float)+tmp['Fossil'].astype(float))
tmp.fillna(0.).to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_share_feb2025_v1.csv")



################################################################################################



iea_reg_map=pandas.read_excel("C:/Users/james/Documents/GEM/GIPT/iea_region_code.xlsx")
names=list(iea_reg_map[iea_reg_map['OECD']=='Yes'].gem_name.unique())
status=['announced','construction','pre-construction']

gipt[(gipt['Country/area'].isin(names))&(gipt.Type.isin(['coal','oil/gas']))&(gipt.Status.isin(status))]['Capacity (MW)'].sum()


gipt[(gipt['Country/area'].isin(names))&(gipt.Status.isin(status))]['Capacity (MW)'].sum()



status=['construction']

gipt[(gipt['Country/area'].isin(['China']))&(gipt.Type.isin(['coal','oil/gas']))&(gipt.Status.isin(status))]['Capacity (MW)'].sum()
gipt[(gipt['Country/area'].isin(['United States']))&(gipt.Type.isin(['wind','solar','hydropower']))&(gipt.Status.isin(status))]['Capacity (MW)'].sum()





gipt[(gipt.Type.isin(['solar']))&(gipt.Status.isin(status))].groupby('Country/area')['Capacity (MW)'].sum().sort_values()[-50:]


