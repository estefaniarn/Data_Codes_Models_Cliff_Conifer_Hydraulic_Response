import pandas as pd 
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#########DATA MANIPULATION########

#FUNCTION TO:
# CUT 2 DFs to the same initial day to the same final day 
# MERGE BOTH by adding the columns of the second to the first 
def cut_merge(all_dfs):
    # Extract datetime boundaries
    min_date = pd.to_datetime('1900-01-01 00:00:00') #defino variable inicial para sobreescribir
    max_date = pd.to_datetime('2100-01-01 00:00:00')
    for df in all_dfs:
        if df.index.max() < max_date:
            max_date = df.index.max()
        if df.index.min() > min_date:
            min_date = df.index.min()
    
    # Cut and merge
    new_df = pd.DataFrame()
    for df in all_dfs:
        cut_df = df[(df.index >= min_date) & (df.index <= max_date)]
        for col in cut_df.columns:
            new_df[col] = cut_df[col].copy()
    return new_df


# FUNCTION TO REFILL NANS with complete Data set, in this case it's specific to Temperature and Rain from the complete one (BGI)
def replace_nans_one(df,col_df_nan,col_df_replace):
    new_col=df[col_df_nan].values.copy()
    for i,(col_nan,col_rep) in enumerate(zip(df[col_df_nan],df[col_df_replace])):
        if np.isnan(col_nan):
            new_col[i]=col_rep

    df[col_df_nan]=new_col
    df=df.drop(columns=[col_df_replace]) 
    
    return(df)

def replace_nans_list(df,cols_nan,cols_replace):
    for cname_nan,cname_rep in zip(cols_nan,cols_replace):
        new_col=df[cname_nan].values.copy()
        for i,(row_nan,row_rep) in enumerate(zip(df[cname_nan],df[cname_rep])):
            if np.isnan(row_nan):
                new_col[i]=row_rep
        df[cname_nan]=new_col
        df=df.drop(columns=[cname_rep])
    return(df)

#Function that calculates correlation and graphs Wasootch vs BGI data 
def correlation_fun(df,cname_W,cname_BGI):
    import scipy.stats
    import plotly.express as px
    df_nn=df.loc[df.isna().any(axis=1)==False]
    bgi=df_nn[cname_BGI]
    wasootch=df_nn[cname_W]
    
    corr_matrix=np.corrcoef(bgi,wasootch)
    pearsoncc=scipy.stats.pearsonr(bgi, wasootch)
    pc='r=' + str(round(pearsoncc[0],3))
    spearmanrho=scipy.stats.spearmanr(bgi, wasootch)
    kendalltau= scipy.stats.kendalltau(bgi, wasootch)
    fig = px.scatter(x=bgi, y=wasootch,labels=dict(x=cname_BGI, y=cname_W),title=pc)
    return fig

# to check dates that are NaNs and to select specific date range 
#print(rad.loc[rad.isna().any(axis=1)==True],rad['2020-04-05 00:00:00':'2020-04-06 00:00:00']) 