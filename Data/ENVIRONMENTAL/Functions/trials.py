#this code will calculate the potential evapotranspiration out of our data and also the vapor pressure deficit and plot it as a time series 

import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

#to_dt = lambda s: pd.to_datetime(s, format='%d/%m/%Y %H:%M:%S') #see if it's useful 

#GET SAP FLOW 
SF_cols=['Date','Time','UO','UI','CO','CI','SFO','SFI','SFTOT']
SF=pd.read_csv(r'SFLOW.csv',skiprows=1, names=SF_cols)

SF.index = pd.to_datetime(SF['Date'] + ' ' + SF['Time'], format='%d/%m/%Y %H:%M:%S') #creo un indice para plot 
SF_in_pandas = SF.drop(columns=['Date', 'Time'])

#PLOT
fig = make_subplots(rows=5, cols=1)

fig.append_trace(go.Scatter(
    x=W_in_pandas.key_0,
    y=W_in_pandas['VPD1'],
    name="VPD (Tdew)"
), row=1, col=1)

fig.append_trace(go.Scatter(
    x=W_in_pandas.key_0,
    y=W_in_pandas['Rain'],
    name="Rain (mm)"
), row=2, col=1)

fig.append_trace(go.Scatter(
    x=W_in_pandas.key_0,
    y=W_in_pandas["PET1"],
    name="PET 1 (mm)"
), row=3, col=1)

#fig.append_trace(go.Scatter(
#    x=W_in_pandas.key_0,
#    y=W_in_pandas['VPD2'],
#    name="VPD (RH)"
#), row=2, col=1)

#fig.append_trace(go.Scatter(
#    x=W_in_pandas.key_0,
#    y=W_in_pandas["NetRad"],
#    name="NetRad(MJ m-2 day-1)"
#), row=3, col=1)



#fig.append_trace(go.Scatter(
#    x=W_in_pandas.key_0,
#    y=W_in_pandas["PET2"],
#    name="PET 2 (mm)"
#), row=5, col=1)

fig.append_trace(go.Scatter(
    x=SF_in_pandas.index,
    y=SF_in_pandas['UO'],
    name="uncorrected out (cm/h)"
), row=4, col=1)

fig.append_trace(go.Scatter(
    x=SF_in_pandas.index,
    y=SF_in_pandas['UI'],
    name="uncorrected in (cm/h)"
), row=5, col=1)



fig.update_layout(height=900, width=1800, title_text="Wasootch Creek, Stem Sap Flow for Lower site")
fig.show()
fig.write_html("/home/estefania/Documents/PhD/Estefania data/ANALYSIS/Analysis Sep02/Lower Site/pet_wasootch_LS.html")
____________________________________________________

#extras/trials
A=W_in_pandas.resample('D').max() 
B=W_in_pandas.resample('D').min()


W_in_pandas.describe() #gives a summary of all the values of the data base of those months
W_in_pandas.resample('D').sum() #takes the total daily=('D') values of each variable 
A=W_in_pandas.resample('D').max() #maximum daily=('D') values of each variable 
B=W_in_pandas.resample('D').min() #minimum daily=('D') values of each variable 

W_in_pandas['formula']=W_in_pandas['TMIN']+W_in_pandas['TMAX']
