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
#gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/Feb_2025_GIPT_update (GCPT)/Global Integrated Power February 2025.xlsx',sheet_name='Power facilities')
gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/Feb_2025_GIPT_update (GSPT.GWPT)/Global Integrated Power February 2025 update II.xlsx',sheet_name='Power facilities')

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




##########
##CONVERT SOLAR ALL TO MWac FOR SUMMARY TABLES FOLLOWING: https://github.com/GlobalEnergyMonitor/Renewables_Others/blob/main/SolarCode/ConvertToMWac.py
## ***NOTE*** HAVE TO UPDATE THIS WITH NEW SOLAR FILE EACH GIPT UPDATE
##########

df_file="C:/Users/james/Documents/GEM/GIPT/Feb_2025_GIPT_update (GSPT.GWPT)/Global-Solar-Power-Tracker-February-2025.xlsx"

dfs=[pandas.read_excel(df_file, sheet_name=i) for i in ['20 MW+','1-20 MW']]
df = pandas.concat(dfs).reset_index()

# this is the conversion between DC to AC. Value from TransitionZero
conversionFactor = 0.87

# this is the minimum count number in order to use country or subregion value rather than subregion or region value
minval = 30

# save original capacity to a new column
df['Capacity (MW) orig'] = df['Capacity (MW)']

# if capacity rating is DC, convert to AC
df.loc[df['Capacity Rating'] == 'MWp/dc', 'Capacity (MW)'] = df['Capacity (MW) orig']*conversionFactor

# if capacity rating is unknown convert the value based on the probability it's MWac based on the country/subregion/region

# I think we don't want to have government datasets biasing this, so we won't include projects that have an other location or phase ID that's not WEPP or WikiSolar
## replace nans with blanks
df.fillna("", inplace=True)
## loop through every Other IDs location and Other IDs phase and remove WEPP & WKSL so that we can ignore anything with an entry in the Other IDs columns
for index, row in df.iterrows():
    loc_id = row['Other IDs (location)']
    phase_id = row['Other IDs (unit/phase)']
    # split the ID by commas
    loc_id_list = loc_id.split(",")
    phase_id_list = phase_id.split(",")
    # create a temporary list
    loc_tmp_lst = []
    phase_tmp_lst = []
    # remove any location ID that start with WEPP or WKSL
    for id in loc_id_list:
        id = id.strip()
        if id.startswith("WEPP") | id.startswith("WKSL"):
            pass
        else:
            loc_tmp_lst.append(id)
    # remove any location ID that start with WEPP
    for id in phase_id_list:
        id = id.strip()
        if id.startswith("WEPP") | id.startswith("WKSL"):
            pass
        else:
            phase_tmp_lst.append(id)
    # join tmp_lst together as a comma delimited string
    new_loc_id = ",".join(map(str, loc_tmp_lst))
    new_phase_id = ",".join(map(str, phase_tmp_lst))
    # write this to the dataframe row
    df.loc[index, 'Other IDs (location)'] = new_loc_id
    df.loc[index, 'Other IDs (unit/phase)'] = new_phase_id


## compute liklihood based on the region
regions = df['Region'].unique().tolist()
region_prob = []
for region in regions:
    countsac = len(df[(df['Region'] == region) & (df['Capacity Rating'] == 'MWac') & (df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    countsdc = len(df[(df['Region'] == region) & (df['Capacity Rating'] == 'MWp/dc') & (df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    region_prob.append(countsac/(countsac+countsdc))


## compute liklihood based on the sub-region. If ac+dc counts are less than minval use region numbers
subregions = df['Subregion'].unique().tolist()
subregion_prob = []
for subregion in subregions:
    countsac = len(df[(df['Subregion'] == subregion) & (df['Capacity Rating'] == 'MWac') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    countsdc = len(df[(df['Subregion'] == subregion) & (df['Capacity Rating'] == 'MWp/dc') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    if countsac+countsdc >= minval:
        subregion_prob.append(countsac / (countsac + countsdc))
    else:
        # get the region associated with subregions
        rgn = df.loc[df['Subregion'] == subregion, 'Region'].iloc[0]
        # find that region's probability
        idx = regions.index(rgn)
        subregion_prob.append(region_prob[idx])


## compute liklihood based on the country. If ac+dc counts are less than 50 use subregion numbers
countries = df['Country/Area'].unique().tolist()
country_prob = []
for country in countries:
    countsac = len(df[(df['Country/Area'] == country) & (df['Capacity Rating'] == 'MWac') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    countsdc = len(df[(df['Country/Area'] == country) & (df['Capacity Rating'] == 'MWp/dc') & (
                df['Other IDs (unit/phase)'] == '') & (df['Other IDs (location)'] == '')])
    if countsac+countsdc >= minval:
        country_prob.append(countsac / (countsac + countsdc))
    else:
        # get the subregion associated with country
        subr = df.loc[df['Country/Area'] == country, 'Subregion'].iloc[0]
        # find that region's probability
        idx = subregions.index(subr)
        country_prob.append(subregion_prob[idx])

# Adjust 'unknown' capacities to MWac
for index, row in df.iterrows():
    if row['Capacity Rating'] == 'unknown':
        idx = countries.index(row['Country/Area'])
        df.at[index, 'Capacity (MW)'] = ((1-conversionFactor)*country_prob[idx] + conversionFactor)*row['Capacity (MW) orig']

# save original capacity rating to a new column and set capacity rating to MWac
df['Capacity Rating orig'] = df['Capacity Rating']
df['Capacity Rating'] = 'MWac'

#Replace gipt capacity values for solar with AC converted values
gipt=gipt.set_index('GEM unit/phase ID')
gipt.loc[df['GEM phase ID'],'Capacity (MW)']=df['Capacity (MW)'].values



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

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_data_ticker_feb2025_v3.json", 'w') as f:
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


pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T,pandas.concat(res_country,axis=1).T]).fillna(0.)[['Country/Area','coal', 'oil/gas', 'solar', 'wind', 'hydropower','nuclear', 'bioenergy', 'geothermal']].to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_operating_feb2025_v3.csv")

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_operating_feb2025_v3.json", 'w') as f:
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


pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T,pandas.concat(res_country,axis=1).T]).fillna(0.)[['Country/Area','coal', 'oil/gas', 'solar', 'wind', 'hydropower','nuclear', 'bioenergy', 'geothermal']].to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_construction_feb2025_v3.csv")

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_construction_feb2025_v3.json", 'w') as f:
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

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_development_feb2025_v3.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))

tmp.fillna(0.).to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_dev_feb2025_v3.csv")


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

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_fossil_nonfossil_feb2025_v3.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))



tmp['Non-fossil share']=tmp['Non-fossil'].astype(float).divide(tmp['Non-fossil'].astype(float)+tmp['Fossil'].astype(float))
tmp['Fossil share']=tmp['Fossil'].astype(float).divide(tmp['Non-fossil'].astype(float)+tmp['Fossil'].astype(float))
tmp.fillna(0.).to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_share_feb2025_v3.csv")



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


