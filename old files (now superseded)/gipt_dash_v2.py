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
#gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/Feb_2025_GIPT_update (GSPT.GWPT)/Global Integrated Power February 2025 update II.xlsx',sheet_name='Power facilities')
#gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/March 2025 GIPT update GGPT/Global Integrated Power March 2025.xlsx',sheet_name='Power facilities')
gipt=pandas.read_excel('C:/Users/james/Documents/GEM/GIPT/April 2025 GIPT update GHPT/Global Integrated Power April 2025.xlsx',sheet_name='Power facilities')

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



(gipt[(gipt.Type.isin(['coal']))&(gipt.Status.isin(['announced','construction','pre-construction']))].groupby(['Country/area'])['Capacity (MW)'].sum()/1000).sort_values()



(gipt[(gipt.Type.isin(['solar']))&(gipt.Status.isin(['construction']))].groupby(['Country/area'])['Capacity (MW)'].sum()/1000).sort_values()



(gipt[(gipt.Type.isin(['solar']))&(gipt.Status.isin(['construction']))].groupby(['Country/area'])['Capacity (MW)'].sum()/1000).sort_values()


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

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_data_ticker_apr2025_v1.json", 'w') as f:
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


pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T,pandas.concat(res_country,axis=1).T]).fillna(0.)[['Country/Area','coal', 'oil/gas', 'solar', 'wind', 'hydropower','nuclear', 'bioenergy', 'geothermal']].to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_operating_apr2025_v1.csv")

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_operating_apr2025_v1.json", 'w') as f:
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


pandas.concat([res_world.to_frame().T,pandas.concat(res_regs,axis=1).T,pandas.concat(res_country,axis=1).T]).fillna(0.)[['Country/Area','coal', 'oil/gas', 'solar', 'wind', 'hydropower','nuclear', 'bioenergy', 'geothermal']].to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_construction_apr2025_v1.csv")

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_construction_apr2025_v1.json", 'w') as f:
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

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_development_apr2025_v1.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))

tmp.fillna(0.).to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_dev_apr2025_v1.csv")


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

with open("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_fossil_nonfossil_apr2025_v1.json", 'w') as f:
    f.write(tmp.to_json(orient='records'))


tmp['Non-fossil share']=tmp['Non-fossil'].astype(float).divide(tmp['Non-fossil'].astype(float)+tmp['Fossil'].astype(float))
tmp['Fossil share']=tmp['Fossil'].astype(float).divide(tmp['Non-fossil'].astype(float)+tmp['Fossil'].astype(float))
tmp.fillna(0.).to_csv("C:/Users/james/Documents/GitHub/gipt-dashboard/gipt_dash_data_prep/gipt_share_apr2025_v1.csv")




################################################################################################
### extra dash #1: #GLOBAL ADDITIONS / RETIREMENTS - PAST 
################################################################################################


#COUNTRY VALUES:

res_country=[]
for country in all_countries:
	to_save=(gipt[(gipt['Country/area']==country)&(gipt.Status.isin(['operating']))].groupby(['Type','Start year'])['Capacity (MW)'].sum().unstack().T/1000.)['2000':'2025']
	columns=[i.capitalize() for i in to_save.columns]
	columns=[i+' added'for i in columns]
	to_save.columns=columns
	retires=(-gipt[(gipt['Country/area']==country)&(gipt.Status.isin(['retired']))].groupby(['Type','Retired year'])['Capacity (MW)'].sum().unstack().T/1000.)['2000':].fillna(0.)
	columns=[i.capitalize() for i in retires.columns]
	columns=[i+' retired'for i in columns]
	retires.columns=columns
	to_save=pandas.concat([to_save,retires],axis=1)
	to_save['Net fossil']=to_save[[col for col in ['Coal added','Oil/gas added'] if col in to_save.columns]].sum(axis=1)+to_save[[col for col in ['Coal retired','Oil/gas retired'] if col in to_save.columns]].sum(axis=1)
	to_save['Net non-fossil']=to_save[[col for col in ['Bioenergy added','Geothermal added','Hydropower added','Nuclear added','Solar added','Wind added'] if col in to_save.columns]].sum(axis=1)+to_save[[col for col in ['Bioenergy retired','Geothermal retired','Hydropower retired', 'Nuclear retired', 'Solar retired', 'Wind retired'] if col in to_save.columns]].sum(axis=1)
	to_save['Region']=country
	res_country.append(to_save)
	country


#GLOBAL VALUES:

to_save=(gipt[(gipt.Status.isin(['operating']))].groupby(['Type','Start year'])['Capacity (MW)'].sum().unstack().T/1000.)['2000':'2025']
columns=[i.capitalize() for i in to_save.columns]
columns=[i+' added'for i in columns]
to_save.columns=columns

retires=(-gipt[(gipt.Status.isin(['retired']))].groupby(['Type','Retired year'])['Capacity (MW)'].sum().unstack().T/1000.)['2000':].fillna(0.)
columns=[i.capitalize() for i in retires.columns]
columns=[i+' retired'for i in columns]
retires.columns=columns

to_save=pandas.concat([to_save,retires],axis=1)

to_save['Net fossil']=to_save[['Coal added','Oil/gas added']].sum(axis=1)+to_save[['Coal retired','Oil/gas retired']].sum(axis=1)
to_save['Net non-fossil']=to_save[['Bioenergy added','Geothermal added','Hydropower added','Nuclear added','Solar added','Wind added']].sum(axis=1)+to_save[['Bioenergy retired','Geothermal retired','Hydropower retired', 'Nuclear retired', 'Solar retired', 'Wind retired']].sum(axis=1)
to_save['Region']='Global'
res_country.append(to_save)


to_save=pandas.concat(res_country)[['Region','Net fossil','Net non-fossil','Coal added','Oil/gas added','Solar added','Wind added','Hydropower added','Nuclear added','Bioenergy added','Geothermal added','Coal retired','Oil/gas retired','Solar retired','Wind retired','Hydropower retired','Nuclear retired','Bioenergy retired','Geothermal retired']]

to_save.to_csv("C:/Users/james/Documents/GEM/GIPT/Viz/net_capacity_V2.csv",encoding='utf-8-sig')






################################################################################################
### extra dash #2: #GLOBAL ADDITIONS FUTURE
################################################################################################

# status=['announced','construction','pre-construction']
# gipt_future=gipt[(gipt.Status.isin(status))]
# gipt_future=gipt_future.loc[gipt_future['Start year']<=2024]
# (gipt_future.groupby(['Type','Start year'])['Capacity (MW)'].sum().unstack().T/1000.).fillna(0.)



# #GLOBAL ADDITIONS / RETIREMENTS - FUTURE
# status=['announced','construction','pre-construction']
# gipt_future=gipt[(gipt.Status.isin(status))]
# #gipt_future.loc[gipt_future['Start year']==2024,'Start year']=2025



# to_save=(gipt_future[(gipt_future.Status.isin(status))].groupby(['Type','Start year'])['Capacity (MW)'].sum().unstack().T/1000.)['2025':'2036']
# columns=[i.capitalize() for i in to_save.columns]
# columns=[i+' added'for i in columns]
# to_save.columns=columns

# retires=(-gipt[(gipt.Status.isin(['operating']))].groupby(['Type','Retired year'])['Capacity (MW)'].sum().unstack().T/1000.)['2025':'2036'].fillna(0.)
# columns=[i.capitalize() for i in retires.columns]
# columns=[i+' retired'for i in columns]
# retires.columns=columns

# to_save=pandas.concat([to_save,retires],axis=1)


# to_save['Net fossil']=to_save[['Coal added','Oil/gas added']].sum(axis=1)+to_save[['Coal retired','Oil/gas retired']].sum(axis=1)
# to_save['Net non-fossil']=to_save[['Bioenergy added','Geothermal added','Hydropower added','Nuclear added','Solar added','Wind added']].sum(axis=1)+to_save[['Bioenergy retired','Geothermal retired','Nuclear retired', 'Solar retired', 'Wind retired']].sum(axis=1)


# to_save.to_csv("C:/Users/james/Documents/GEM/GIPT/Viz/net_capacity_future_V2.csv",encoding='utf-8-sig')


#filter: country
#grouping 1: type
#grouping 2: status
#size: capacity

gipt_dev=gipt[(gipt.Status.isin(['announced','construction','pre-construction']))]
gipt_dev['Capacity (MW)']=['Capacity (MW)']/1000.
type_replacements = {
    'hydropower': 'Hydropower',
    'solar': 'Utility-scale solar',
    'wind': 'Wind',
    'oil/gas': 'Oil/gas',
    'bioenergy': 'Bioenergy',
    'coal': 'Coal',
    'nuclear': 'Nuclear',
    'geothermal': 'Geothermal'
}

# Replace the values in the 'Type' column
gipt_dev['Type'] = gipt_dev['Type'].replace(type_replacements)


# # Reapply the stratification logic
# def stratify_status(row):
#     status = row['Status'].lower()
#     year = row['Start year']
#     if pandas.isna(year):
#         return f"{status}: unknown"
#     elif year <= 2030:
#         return f"{status}: pre-2030"
#     else:
#         return f"{status}: post-2030"

# gipt_dev['Stratified Status']=gipt_dev.apply(stratify_status, axis=1)

# Reapply the stratification logic
def stratify_status(row):
    year = row['Start year']
    if pandas.isna(year):
        return "Unknown start year"
    elif year <= 2030:
        return "Pre-2030"
    else:
        return "Post-2030"

gipt_dev['Starts']=gipt_dev.apply(stratify_status, axis=1)


grouped_gipt_dev = (
    gipt_dev
    .groupby(['Country/area', 'Type', 'Status','Starts'], as_index=False)['Capacity (MW)']
    .sum()
    .sort_values(by=['Country/area', 'Type'])
)


global_tmp=grouped_gipt_dev.groupby(['Type', 'Status','Starts'], as_index=False)['Capacity (MW)'].sum()
global_tmp['Country/area']='Global'

pandas.concat([global_tmp,grouped_gipt_dev]).to_csv("C:/Users/james/Documents/GEM/GIPT/Viz/in_dev_startyear_v1.csv",encoding='utf-8-sig')





################################################################################################
### extra dash #3: breakdown by age
################################################################################################

# Filter for operating facilities
df_operating = gipt[gipt["Status"].str.lower() == "operating"][["Country/area", "Type", "Capacity (MW)", "Status", "Start year"]]

# Drop rows with missing start year
df_operating = df_operating.dropna(subset=["Start year"])

# Calculate age of each facility
df_operating["Age"] = 2025 - df_operating["Start year"]

# Categorize age groups
def categorize_age(age):
    if age >= 50:
        return "50+ years"
    elif age >= 40:
        return "40-49 years"
    elif age >= 30:
        return "30-39 years"
    elif age >= 20:
        return "20-29 years"
    elif age >= 10:
        return "10-19 years"
    else:
        return "0-9 years"

df_operating["Age Category"] = df_operating["Age"].apply(categorize_age)

# Group by country, type, and age category
grouped_by_age = df_operating.groupby(["Country/area", "Type", "Age Category"])["Capacity (MW)"].sum().reset_index()

global_tmp=grouped_by_age.groupby(["Type", "Age Category"])["Capacity (MW)"].sum().reset_index()
global_tmp['Country/area']='Global'
grouped_by_age=pandas.concat([global_tmp,grouped_by_age])


# Pivot the data to have 'Type' as columns
pivoted_by_type = grouped_by_age.pivot_table(
    index=["Country/area", "Age Category"],
    columns="Type",
    values="Capacity (MW)",
    aggfunc="sum",
    fill_value=0
).reset_index()

# Identify numeric columns to scale (excluding the first two)
numeric_cols = pivoted_by_type.columns.difference(["Country/area", "Age Category"])

# Scale numeric columns by dividing by 1000
pivoted_by_type[numeric_cols] = pivoted_by_type[numeric_cols] / 1000

# Define a custom order for age categories from youngest to oldest
age_order = ["0-9 years", "10-19 years", "20-29 years", "30-39 years", "40-49 years", "50+ years"]

# Convert 'Age Category' to a categorical type with the specified order
pivoted_by_type["Age Category"] = pandas.Categorical(pivoted_by_type["Age Category"], categories=age_order[::-1], ordered=True)

# Sort the DataFrame by country and age category (in reverse order)
pivoted_by_type_sorted = pivoted_by_type.sort_values(by=["Country/area", "Age Category"])

#rename columns

pivoted_by_type_sorted.columns=['Country/area', 'Age Category', 'Bioenergy', 'Coal', 'Geothermal','Hydropower', 'Nuclear', 'Oil & gas', 'Utility-scale solar', 'Wind']


#
pivoted_by_type_sorted.to_csv('C:/Users/james/Documents/GEM/GIPT/Viz/age_breakdown_v1.csv',encoding='utf-8-sig')




################################################################################################
### extra dash #4: ownership
################################################################################################

#function to handle combustion: Parents
#loop status and append

res=[]
for tech in ['coal','oil/gas']:
	for status in ['operating','construction','pre-construction','announced']:
		df_tmp=gipt[(gipt.Type==tech)&(gipt.Status==status)]
		df_tmp.loc[df_tmp.Parent.isnull(),'Parent']='unknown'
		# Helper function to parse owners and calculate proportional shares
		def parse_owners_with_percentages(row):
		    owners_raw = str(row["Parent"])
		    capacity = row["Capacity (MW)"]
		    # Find all owners and optional percentages
		    pattern = r'([^;\[]+?)(?:\s*\[\s*(\d+(?:\.\d+)?)\s*%\s*\])?(?:;|$)'
		    matches = re.findall(pattern, owners_raw)
		    owners = []
		    total_percent = 0
		    percent_info = []
		    for owner, pct in matches:
		        owner = owner.strip()
		        if pct:
		            percent = float(pct)
		            total_percent += percent
		            percent_info.append((owner, percent))
		        else:
		            owners.append(owner)
		    # Normalize capacity by percentage or equally split if no percentages
		    result = []
		    if percent_info:
		        for owner, percent in percent_info:
		            share = capacity * (percent / 100)
		            result.append({
		                "Country/area": row["Country/area"],
		                "Parent": owner,
		                "Capacity (MW)": share
		            })
		    elif owners:
		        share = capacity / len(owners)
		        for owner in owners:
		            result.append({
		                "Country/area": row["Country/area"],
		                "Parent": owner,
		                "Capacity (MW)": share
		            })
		    return result
		# Expand rows using the helper function
		tmp_rows = []
		for _, row in df_tmp.iterrows():
		    tmp_rows.extend(parse_owners_with_percentages(row))
		df_tmp_expanded = pandas.DataFrame(tmp_rows)
		# Aggregate capacity
		df_tmp_aggregated = df_tmp_expanded.groupby(["Country/area", "Parent"], as_index=False)["Capacity (MW)"].sum()
		# Add rank per country
		df_tmp_aggregated["Rank"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].rank(method="dense", ascending=False).astype(int)
		# Sort
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		# Calculate percentage of total capacity per country
		df_tmp_aggregated["Total Capacity (MW)"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].transform("sum")
		df_tmp_aggregated["Percentage of Total Capacity (%)"] = (df_tmp_aggregated["Capacity (MW)"] / df_tmp_aggregated["Total Capacity (MW)"])
		# Calculate cumulative percentage of total capacity per country
		df_tmp_aggregated["Cumulative Percentage (%)"] = df_tmp_aggregated.groupby("Country/area")["Percentage of Total Capacity (%)"].cumsum()
		# Sort again for clarity
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		df_tmp_aggregated['Technology']=tech
		df_tmp_aggregated['Status']=status
		res.append(df_tmp_aggregated)



out=pandas.concat(res)
out["Technology"] = out["Technology"].str.title()


out[out["Country/area"]=='United States']

out[['Technology','Country/area','Status','Rank','Parent','Capacity (MW)','Percentage of Total Capacity (%)','Cumulative Percentage (%)']].to_csv('C:/Users/james/Documents/GEM/GIPT/Viz/combustion_breakdown_v1.csv',encoding='utf-8-sig')




#function to handle others: Owner
#loop status and append
res=[]
for tech in ['solar','wind','hydropower','bioenergy','geothermal','nuclear']:
	for status in ['operating','construction','pre-construction','announced']:
		df_tmp=gipt[(gipt.Type==tech)&(gipt.Status==status)]
		df_tmp.loc[df_tmp.Owner.isnull(),'Owner']='unknown'
		# Helper function to parse owners and calculate proportional shares
		def parse_owners_with_percentages(row):
		    owners_raw = str(row["Owner"])
		    capacity = row["Capacity (MW)"]
		    # Find all owners and optional percentages
		    pattern = r'([^;\[]+?)(?:\s*\[\s*(\d+(?:\.\d+)?)\s*%\s*\])?(?:;|$)'
		    matches = re.findall(pattern, owners_raw)
		    owners = []
		    total_percent = 0
		    percent_info = []
		    for owner, pct in matches:
		        owner = owner.strip()
		        if pct:
		            percent = float(pct)
		            total_percent += percent
		            percent_info.append((owner, percent))
		        else:
		            owners.append(owner)
		    # Normalize capacity by percentage or equally split if no percentages
		    result = []
		    if percent_info:
		        for owner, percent in percent_info:
		            share = capacity * (percent / 100)
		            result.append({
		                "Country/area": row["Country/area"],
		                "Owner": owner,
		                "Capacity (MW)": share
		            })
		    elif owners:
		        share = capacity / len(owners)
		        for owner in owners:
		            result.append({
		                "Country/area": row["Country/area"],
		                "Owner": owner,
		                "Capacity (MW)": share
		            })
		    return result
		# Expand rows using the helper function
		tmp_rows = []
		for _, row in df_tmp.iterrows():
		    tmp_rows.extend(parse_owners_with_percentages(row))
		df_tmp_expanded = pandas.DataFrame(tmp_rows)
		# Aggregate capacity
		df_tmp_aggregated = df_tmp_expanded.groupby(["Country/area", "Owner"], as_index=False)["Capacity (MW)"].sum()
		# Add rank per country
		df_tmp_aggregated["Rank"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].rank(method="dense", ascending=False).astype(int)
		# Sort
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		# Calculate percentage of total capacity per country
		df_tmp_aggregated["Total Capacity (MW)"] = df_tmp_aggregated.groupby("Country/area")["Capacity (MW)"].transform("sum")
		df_tmp_aggregated["Percentage of Total Capacity (%)"] = (df_tmp_aggregated["Capacity (MW)"] / df_tmp_aggregated["Total Capacity (MW)"])
		# Calculate cumulative percentage of total capacity per country
		df_tmp_aggregated["Cumulative Percentage (%)"] = df_tmp_aggregated.groupby("Country/area")["Percentage of Total Capacity (%)"].cumsum()
		# Sort again for clarity
		df_tmp_aggregated.sort_values(by=["Country/area", "Rank"], inplace=True)
		df_tmp_aggregated['Technology']=tech
		df_tmp_aggregated['Status']=status
		res.append(df_tmp_aggregated)



out=pandas.concat(res)
out["Technology"] = out["Technology"].str.title()


out[out["Country/area"]=='United States']

out[['Technology','Country/area','Status','Rank','Owner','Capacity (MW)','Percentage of Total Capacity (%)','Cumulative Percentage (%)']].to_csv('C:/Users/james/Documents/GEM/GIPT/Viz/non_combustion_breakdown_v1.csv',encoding='utf-8-sig')





























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


