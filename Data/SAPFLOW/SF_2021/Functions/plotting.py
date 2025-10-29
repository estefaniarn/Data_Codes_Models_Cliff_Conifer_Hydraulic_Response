import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#########PLOTING########

#FUNCTION TO PLOT TIME SERIES FOR 2 DATA SETS AND A SPECIFIED COLUMN FOR EACH  
def visually_compare(df1,df2,col_name_df1, col_name_df2):
    figR = make_subplots(rows=2, cols=1)

    figR.append_trace(go.Scatter(
        x=df1.index.to_series(),
        y=df1[col_name_df1],
        name="Original"
    ), row=1, col=1)

    figR.append_trace(go.Scatter(
        x=df2.index.to_series(),
        y=df2[col_name_df2],
        name="Extra"
    ), row=2, col=1)
    return(figR.show())

#plot of a single time series 
def plot_ts(df,col_name): 
    fig = go.Figure([go.Scatter(x=df.index.to_series(), y=df[col_name])])
    return(fig)#.show())