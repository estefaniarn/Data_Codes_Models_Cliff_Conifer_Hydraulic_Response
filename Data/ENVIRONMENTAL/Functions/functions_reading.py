import pandas as pd 
import numpy as np
from pathlib import Path
path_cwd=Path.cwd()
str(path_cwd)+'/Data_input'
#########READING########
#Units Rain: mm    Temp:°C     RH: %     Wind Speed:m/s 	Gust Speed:m/s 
#FUNCTION FOR READING HOBO WEATHER STATION DATA 



def reading_hobo():
    dfs_cols=['#','DateTime','Rain(mm)','Temp(C)','RH','WS','GS', 'DP']
    dfs_year=[pd.read_table(str(path_cwd)+'/Data_input'+'/'+name,sep=',',skiprows=2, names=dfs_cols) for name in ['WEATHER19.csv','WEATHER20.csv','WEATHER21_22.csv']]
    DF=pd.concat(dfs_year, axis=0)
    DF= DF.drop(columns=['#'])
    DF.index = pd.to_datetime(DF['DateTime'])
    DF.index=DF.index.ceil('0.5H') 
    df=DF.resample('30min').ffill(limit=1)
    df=df.drop(columns='DateTime')
    return(df)



#FUNCTION FOR READING DATA FROM BIOGEOSCIENCE INSTITUTE https://research.ucalgary.ca/biogeoscience-institute/research/environmental-data
#data was modified before in excel to get the right Date and Time format
#units C, mm, W/m2
def reading_BGI(): 
    dfs_cols=['Date','Time','Temp_BGI(C)','AvgT','MaxT','MinT','Rad_BGI', 'Rain_BGI(mm)'] #important to name different or it will replace our station values when merging 
    dfs_year=[pd.read_table(str(path_cwd)+'/Data_input'+'/'+name,sep=',',skiprows=1, names=dfs_cols) for name in ['BGI19.csv','BGI20.csv','BGI21.csv']] #add BGI22.csv when available 
    DF=pd.concat(dfs_year, axis=0)
    DF.index  = pd.to_datetime(DF['Date'] + ' ' + DF['Time']) 
    DF=DF.drop(columns=['Date','Time','AvgT','MaxT','MinT'])
    DF=DF.resample('30min').ffill(limit=1)
    DF['Rad_BGI']=DF['Rad_BGI'].replace(0,0.2) 
    return(DF)

#FUNCTION FOR READING JUMPINGPOUND WEATHER STATION DATA https://scholar.uc.edu/concern/parent/2227mq412/file_sets/tx31qj85c?locale=en
#units Temp: C,	RH: %	Rain: mm	Wind Speed:m/s	Gust Speed:m/s
def reading_JP():
    dfs_cols=['DateTime','V','current','PAR','Temp_JP','RH_JP','Rain_JP','WS_JP','GS_JP','winddir']
    DF=pd.read_table(str(path_cwd)+'/Data_input'+'/'+'JP.csv',sep=',',skiprows=2, names=dfs_cols)#,low_memory=False) 
    DF= DF.drop(columns=['V','current','PAR','winddir','Rain_JP'])
    DF.index = pd.to_datetime(DF['DateTime'])
    columns_to_mean = ['Temp_JP', 'RH_JP', 'WS_JP', 'GS_JP']
    df = DF[columns_to_mean].resample('30min').mean()
    #df=DF.resample('30min').mean()
    df['DP_JP']=df['Temp_JP'] - ((100 - df['RH_JP'])/5)
    df=df.drop(columns=['Temp_JP'])
    return(df)

#FUNCTION TO READ RADIATION DATA FROM CAMPBELL SCIENTIFIC RADIOMETERS 
#THEY ARE SEPARATE FILES BECAUSE THE DATA IS COLLECTED IN PIECES 
#BE SURE FILES ARE NAMED RAD# 
def reading_RAD():
    R_cols = ['Date', 'Record', 'NetRad', 'NetRadAvg']  # general for all
    names_rad = [str(path_cwd) + '/Data_input' + '/' + 'RAD' + str(i) for i in range(1, 9)]  # list of names, RAD#, range(1, number of RAD files +1)
    dfs_rad = [pd.read_table(filename + '.csv', sep=',', skiprows=1, names=R_cols) for filename in names_rad]  # list of dfs for each file
    RAD = pd.concat(dfs_rad, axis=0)  #
    RAD = ((RAD[~RAD['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna()).drop(columns=['Record'])

    # Try parsing with multiple formats
    RAD.index = pd.to_datetime(RAD['Date'], errors='coerce', format='%Y-%m-%d %H:%M:%S')  # First try the full format with seconds
    # For rows that failed parsing (NaT), try the format without seconds
    mask = RAD.index.isna()  # Identify rows where parsing failed
    if mask.any():
        print("Some timestamps failed to parse with '%Y-%m-%d %H:%M:%S'. Trying '%Y-%m-%d %H:%M'...")
        RAD.loc[mask, 'Date'] = pd.to_datetime(RAD.loc[mask, 'Date'], errors='coerce', format='%Y-%m-%d %H:%M')
        RAD.index = pd.to_datetime(RAD['Date'], errors='coerce')  # Recompute the index

    # Check for remaining NaT values
    if RAD.index.isna().any():
        print("Warning: Some timestamps could not be parsed and are NaT:", RAD[RAD.index.isna()]['Date'])

    # Check for duplicate timestamps
    if RAD.index.duplicated().any():
        print("Duplicate timestamps found:", RAD[RAD.index.duplicated()].index)
        RAD = RAD.groupby(RAD.index).mean()  # Aggregate duplicates by taking the mean

    IRR = RAD.apply(lambda x: pd.to_numeric(x, errors='coerce'))  # changes argument to numeric type
    IRR = IRR.astype({'NetRad': 'float', 'NetRadAvg': 'float'})  # changes values to float
    IRR = IRR.clip(lower=0.2)  # make negative values 0.2 (min value for PAR)
    IRR = IRR.drop(columns='Date', errors='ignore')  # Drop 'Date' column if it still exists
    rad = IRR.resample('30min').ffill(limit=1)
    rad['NetRad'] = rad['NetRad'].replace(0, 0.2)
    return rad

#FUNCTION FOR READING DATA FROM SOLCAST https://toolkit.solcast.com.au/
# Direct Normal Irradiance (DNI) Irradiance received from the direction of the sun (10th percentile clearness). Also referred to as beam radiation.
# Global Horizontal Irradiance (GHI) Total irradiance on a horizontal surface. The sum of direct and diffuse irradiance components received on a horizontal surface.
#units C, W/m2 , W/m2
def reading_solcast(): 
    df_cols=['Date','T','DNI','GHI'] #important to name different or it will replace our station values when merging 
    DF=pd.read_table(str(path_cwd)+'/Data_input'+'/'+'Global_radiation.csv',sep=',',skiprows=1, names=df_cols) 
    DF['Date'] = pd.to_datetime(DF['Date'],format='%Y-%m-%dT%H:%M:%SZ') 
    DF['Date'] = DF['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    DF.index  = pd.to_datetime(DF['Date'],format='%Y-%m-%d %H:%M:%S')
    #specify datetime format yyyy-mm-dd hh:mm:ss
    DF=DF.drop(columns=['Date','T'])
    return(DF)