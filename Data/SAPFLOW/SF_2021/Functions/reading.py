
import os
from pathlib import Path

import numpy as np
import pandas as pd


def read_sf1(path_input,SF_cols,name): 
    #read file engine python is to avoid an error with the type of characters in the original file 
    SFr=pd.read_csv(path_input+name,header = None, skiprows=1, names=SF_cols, engine='python',encoding = "ISO-8859-1")
    SF=(SFr[~SFr['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])#eliminate all string entries

    #create datetime index with the 2 formats that appear in the original file 
    ind1 = pd.to_datetime(SF['Date'] + ' ' + SF['Time'],errors='coerce',format='%Y-%d-%m %H:%M:%S') #here I deal with the 2 formats but maybe ICT way with parser.parse is more effective if there's some other format
    ind2 = pd.to_datetime(SF['Date'] + ' ' + SF['Time'],errors='coerce',format='%d/%m/%Y %H:%M:%S') 
    
    SF.index=ind1.fillna(ind2) #since index one will fill with NaNs the rows that have a different format (and viceversa) I will fill all the Nans with the other index created 
    SF=SF.drop(SF.loc[SF.index.year<2019].index)  #this will remove all rows that have a year less than 2019 because the original file has some 2000s value
    SF=SF.drop(columns=['Date','Time'])
    SF=SF.apply(lambda x: pd.to_numeric(x, errors='coerce')) #Convert argument to a numeric type.
    SF=SF.astype({'UO':'float','UI':'float','CO':'float','CI':'float','SFO':'float','SFI':'float','MaxTdO':'float','MaxTuO':'float','RiseTdO':'float','RiseTuO':'float','RatioOut':'float','MaxTdI':'float','MaxTuI':'float','RiseTdI':'float','RiseTuI':'float','RatioIn':'float'}) #specify the numeric type in this case float 
    return SF

def read_sf2(path_input,SF_cols,name):
        name2=name.rstrip('-initial.CSV')
        name_cont=name2 + ".CSV"
        SF_i=pd.read_csv(path_input+name,header = None, skiprows=1, names=SF_cols,engine='python',encoding = "ISO-8859-1")
        SF_f=pd.read_csv(path_input+name_cont,header = None, skiprows=1, names=SF_cols, engine='python',encoding = "ISO-8859-1")
        SF_i=(SF_i[~SF_i['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])
        SF_f=(SF_f[~SF_f['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])
        
        #concat, index and drop
        SF=pd.concat([SF_i,SF_f], axis=0) #concatenate the 2 separate files 
        ind1 = pd.to_datetime(SF['Date'] + ' ' + SF['Time'],errors='coerce',format='%Y-%d-%m %H:%M:%S') 
        ind2 = pd.to_datetime(SF['Date'] + ' ' + SF['Time'],errors='coerce',format='%d/%m/%Y %H:%M:%S') 
        SF.index=ind1.fillna(ind2)
        SF=SF.drop(SF.loc[SF.index.year<2019].index) 
        SF=SF.drop(columns=['Date','Time'])
        SF=SF.apply(lambda x: pd.to_numeric(x, errors='coerce')) #Convert argument to a numeric type.
        SF=SF.astype({'UO':'float','UI':'float','CO':'float','CI':'float','SFO':'float','SFI':'float','MaxTdO':'float','MaxTuO':'float','RiseTdO':'float','RiseTuO':'float','RatioOut':'float','MaxTdI':'float','MaxTuI':'float','RiseTdI':'float','RiseTuI':'float','RatioIn':'float'}) #specify the numeric type in this case float 
        return SF,name2

def sf_env_soil(path_input,ini_date,soil,SF,k):
    #1.1 Read Environmental data 
    ENV_cols=['Rain','Temp','RH','WS','NR','NetRad(MJ/m2h)','VPD','PET'] #units:Rain(mm),Temp(C),RH(%),NetRad(W/m2),NetRad(MJ/m2h),VPD(kPa),PET(mm/h)
    ENV=pd.read_csv(path_input+'ENVIRONMENTAL_tidy.csv',header = None, skiprows=1, names=ENV_cols,engine='python',encoding = "ISO-8859-1")
    ENV.index = pd.to_datetime(ENV.index,errors='coerce')
    ENV=ENV.drop(columns=['RH','NetRad(MJ/m2h)']).loc['2021-05-01 00:30:00':] #### change if we want them 
    env=ENV.copy()

    #1.2 Read soil data 
    soil_cols=['S1','S2','S3']
    sm_file=soil+'.csv'
    SM=pd.read_csv(path_input+sm_file,header = None, skiprows=1, names=soil_cols,engine='python',encoding = "ISO-8859-1")
    SM.index = pd.to_datetime(SM.index,errors='coerce')
    SM=SM.asfreq(freq='30 min',method='ffill')
    SM['S_avg']=SM.mean(axis=1).values.copy()
    sm=SM.copy()   


    #2. Filter, round and resample original sf data. 
    sf=SF.copy().loc[ini_date:].filter(['UO','UI','MaxTdO','MaxTuO','RiseTdO','RiseTuO','RatioOut','MaxTdI','MaxTuI','RiseTdI','RiseTuI','RatioIn'])# We keep only the HPV calculated by ICT UO and UI (k/x*ln(ratio)*3600 k=0.00025 x=0.6 units=cm/h) and the RAW values to recalculate with corrections
    sf.index=sf.index.floor('0.5H') #round because some values have extra seconds or minutes after :00:00 or :30:00
    ####REMOVE DUPLICATED VALUES AND KEEP FIRST (IF EXISTING)
    sf=sf[~sf.index.duplicated(keep='first')] # ~: makes false true and true false.  The df[] just filters, basically it says keep everything but the duplicated values (only true) 
    sf=sf.asfreq('30 min') #resamples with a nan to avoid graphed interpolation


    #3. Create a df with sap, environmental and soil information cropped to same size 
    min_date = pd.to_datetime('1900-01-01 00:00:00') #dummies 
    max_date = pd.to_datetime('2100-01-01 00:00:00')
    for df in [sf,env]: #establish min and max dates of smaller df 
        if df.index.max() < max_date:
            max_date = df.index.max()
        if df.index.min() > min_date:
            min_date = df.index.min()
        
    new_df = pd.DataFrame()
    for df in [sf,env]:
        cut_df = df[(df.index >= min_date) & (df.index <= max_date)] #cut both df the same size 
        for col in cut_df.columns:
            new_df[col] = cut_df[col].copy()

     #transform raw heat ratio to heat pulse using the calculated diffusivity 
    import warnings
    warnings.filterwarnings("error")
    try:
        new_df['HPVI']=np.log(new_df['RatioIn'])*(k/0.6)*3600
        new_df['HPVO']=np.log(new_df['RatioOut'])*(k/0.6)*3600
    except Exception as e:
        new_df['HPVI']=np.nan
        new_df['HPVO']=np.nan
    
    return new_df,sm #returns cropped SF+Weather & SF+WEATHER+SM