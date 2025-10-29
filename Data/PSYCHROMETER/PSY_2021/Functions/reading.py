
import os
from pathlib import Path

import numpy as np
import pandas as pd


def read_Df1(path_input,DF_cols,name): 
    #read file engine python is to avoid an error with the type of characters in the original file 
    DFr=pd.read_csv(path_input+name,header = None, skiprows=1, names=DF_cols, engine='python',encoding = "ISO-8859-1")#added the ,encoding = "ISO-8859-1" because otherwise it has an error on decoding UTF-8 
    DF=(DFr[~DFr['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])#eliminate all string entries

    #create datetime index with the 2 formats that appear in the original file 
    ind1 = pd.to_datetime(DF['Date'] + ' ' + DF['Time'],errors='coerce',format='%Y-%d-%m %H:%M:%S') #here I deal with the 2 formats but maybe ICT way with parser.parse is more effective if there's some other format
    ind2 = pd.to_datetime(DF['Date'] + ' ' + DF['Time'],errors='coerce',format='%d/%m/%Y %H:%M:%S') 
    
    DF.index=ind1.fillna(ind2) #since index one will fill with NaNs the rows that have a different format (and viceversa) I will fill all the Nans with the other index created 
    #DF=DF.drop(DF.loc[DF.index.year<2019].index)  #this will remove all rows that have a year less than 2019 because the original file has some 2000s value
    DF = DF.drop(DF.loc[DF.index.year < 2019].index.union(DF.loc[DF.index.year >= 2022].index))
    DF=DF.drop(columns=['Date','Time','Intercept','Slope','EDBO','Correction for dT','Correction Factor','IBV','IBT','EPS Present','EPS Voltage','EPS Current','Diagnostic Comment','NA']) #If we want diagnostic for something: 'Date','Time','IBV','IBT','EPS Present','EPS Voltage','EPS Current','Diagnostic Comment','NA'


    DF=DF.apply(lambda x: pd.to_numeric(x, errors='coerce')) #Convert argument to a numeric type.
    DF=DF.astype({'Chamber Temperature':'float','dT':'float','Wet Bulb Depression':'float','Corrected Water Potential':'float'})#,'Intercept':'float','Slope':'float','EDBO':'float','Correction for dT':'float','Correction Factor':'float'}) #specify the numeric type in this case float 
    DF.columns=['Chamber Temperature (C)','dT (C)','Wet Bulb Depression','Corrected Water Potential (MPa)']

    DF.index=DF.index.floor('0.5H') #round 
    DF=DF[~DF.index.duplicated(keep='first')] # keep everything but the duplicated values
    DF=DF.asfreq('30 min') #resample with a nan so gaps are not ploted as a weird interpolation

    return DF


def read_Df2(path_input,DF_cols,name):
        name2=name.rstrip('-initial.CSV')
        name_cont=name2 + ".CSV"
        DF_i=pd.read_csv(path_input+name,header = None, skiprows=1, names=DF_cols,engine='python',encoding = "ISO-8859-1")
        DF_f=pd.read_csv(path_input+name_cont,header = None, skiprows=1, names=DF_cols, engine='python',encoding = "ISO-8859-1")
        DF_i=(DF_i[~DF_i['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])
        DF_f=(DF_f[~DF_f['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])
        
        #concat, index and drop
        DF=pd.concat([DF_i,DF_f], axis=0) #concatenate the 2 separate files 
        ind1 = pd.to_datetime(DF['Date'] + ' ' + DF['Time'],errors='coerce',format='%Y-%d-%m %H:%M:%S') 
        ind2 = pd.to_datetime(DF['Date'] + ' ' + DF['Time'],errors='coerce',format='%d/%m/%Y %H:%M:%S') 
        DF.index=ind1.fillna(ind2)
        DF=DF.drop(DF.loc[DF.index.year<2019].index) 
        
        DF=DF.drop(columns=['Date','Time','Intercept','Slope','EDBO','Correction for dT','Correction Factor','IBV','IBT','EPS Present','EPS Voltage','EPS Current','Diagnostic Comment','NA']) #If we want diagnostic for something: 'Date','Time','IBV','IBT','EPS Present','EPS Voltage','EPS Current','Diagnostic Comment','NA'
        DF=DF.apply(lambda x: pd.to_numeric(x, errors='coerce')) #Convert argument to a numeric type.
        DF=DF.astype({'Chamber Temperature':'float','dT':'float','Wet Bulb Depression':'float','Corrected Water Potential':'float'})#,'Intercept':'float','Slope':'float','EDBO':'float','Correction for dT':'float','Correction Factor':'float'}) #specify the numeric type in this case float 
        DF.columns=['Chamber Temperature (C)','dT (C)','Wet Bulb Depression','Corrected Water Potential (MPa)']


        DF.index=DF.index.floor('0.5H') #round 
        DF=DF[~DF.index.duplicated(keep='first')] # keep everything but the duplicated values
        DF=DF.asfreq('30 min') #resample with a nan so gaps are not ploted as a weird interpolation

        #DF.loc[DF['Corrected Water Potential']==0,'Corrected Water Potential']=np.nan

        return DF,name2
