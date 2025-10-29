#functions
import statistics
import numpy as np
import pandas as pd
import tomli
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

#reading
def read_sensor(path_input,sensor,name,cols,type): 
        with open(path_input+"config_2022.toml", "rb") as f: #rb:read binary, f: file
            d=tomli.load(f)
        if sensor=='tdr':
                soil_gen=pd.read_csv(path_input+name,header = None, skiprows=2, names=cols, engine='python') 
                soil_gen['Date'] = pd.to_datetime(soil_gen['Date'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                soil_gen.index = pd.to_datetime(soil_gen['Date'],errors='coerce')
                soil_tdr=soil_gen.filter(['WC1','WC2','WC3']).rename(columns={"WC1": "S1", "WC2": "S2", "WC3": "S3"})
                return soil_tdr

        elif sensor=='zentra':
                soil_gen=pd.read_csv(path_input+name,header = None, skiprows=1, names=cols, engine='python', encoding='iso-8859-1') 
                soil_gen=(soil_gen[~soil_gen['Date'].str.contains("[a-zA-Z]").fillna(False)]).dropna(subset=['Date'])
                soil_gen.index = pd.to_datetime(soil_gen['Date'],errors='coerce')
                soil_gen = soil_gen.resample('1H').first().loc[d['dates']['initial_date']:d['dates']['final_date']]
                # 3 sensors
                if type==3:
                        soil_gen['S1'], soil_gen['S2'], soil_gen['S3'] = [soil_gen[col].astype(float).where(soil_gen[col].astype(float) <= 1, np.nan) for col in ['WC1', 'WC2','WC3']]
                        S=soil_gen.filter(['S1','S2','S3'])
                        return S
                
                # 2 sensors
                elif type==2:
                        soil_gen['S1'], soil_gen['S2'] = [soil_gen[col].astype(float).where(soil_gen[col].astype(float) <= 1, np.nan) for col in ['WC1', 'WC2']]
                        S=soil_gen.filter(['S1','S2'])
                        return S

#imputing
def fill_within(DF,type): 
        if type== 2: 
                # Case 1: No action for rows where all three columns are NaN
                df_2=DF.copy()
                case1_mask_2 = df_2[["S1", "S2"]].isnull().all(axis=1)
                df_2.loc[case1_mask_2, ["S1", "S2"]] = np.nan
                # case 1.1: if 24 rows missing or less interpolate linearly
                if case1_mask_2.sum() <= 48:
                        df_2 = df_2.interpolate(method="linear", limit_direction="both", axis=0)
                return df_2
        
        if type== 3:
                df=DF.copy()
                final_fil = df.columns #to not include avg

                # Case 1: No action for rows where all three columns are NaN
                case1_mask = df[df.columns].isnull().all(axis=1) | (df[df.columns] == 0).all(axis=1)
                df.loc[case1_mask, df.columns] = np.nan 
                
                # Case 2: Linear regression for sections with one complete column and two NaN columns
                case2_mask = df[df.columns].isnull().sum(axis=1) == 2 # look for rows with 2 NaNs
                case2_data = df.loc[case2_mask, df.columns].dropna(thresh=1) # df with only rows with 2 NaNs and one complete column (drops the ones with 3 nans), thresh=1: at least one non-NaN value
                if case2_mask.any(): # select dfs that have at least one row with 2 NaNs and one complete column and complete values, loggers where 2 sensors are inactive and one is active
                        complete_data = df.dropna(thresh=3) #thresh=3: at least 3 non-NaN values
                        complete_cols = [] # should have only one element in this case
                        incomplete_cols = [] # should have two elements in this case
                        for col in df.columns:
                                if case2_data[col].notnull().any():
                                        complete_cols.append(col)
                                if case2_data[col].isnull().any():
                                        incomplete_cols.append(col)

                        for icol in incomplete_cols:
                                X = complete_data[complete_cols].values
                                y = complete_data[icol].values
                                lr = LinearRegression()
                                lr.fit(X, y)
                                m = lr.coef_[0]
                                b = lr.intercept_
                                df.loc[case2_mask, icol] = m * df.loc[case2_mask, str.join(",", complete_cols)] + b #the join is to get the column name as a string
                
                
                #Case 3: Linear interpolation for sections with two complete columns and one NaN column
                case3_mask = df[df.columns].isnull().sum(axis=1) == 1 # look for rows with 1 NaN
                case3_data = df.loc[case3_mask, df.columns].dropna(thresh=2) # df with only rows with 1 NaN and two complete columns, thresh=2: at least two non-NaN values
                
                if case3_mask.any(): # select dfs that have at least one row with 1 NaN and two complete columns and complete values
                        complete_data_ = df.dropna(thresh=3) #thresh=3: at least 3 non-NaN values
                        complete_cols_ = [] # should have two elements in this case
                        incomplete_cols_ = [] # should have only one element in this case
                        for col in df.columns:
                                if case3_data[col].notnull().any():
                                        complete_cols_.append(col)
                                if case3_data[col].isnull().any():
                                        incomplete_cols_.append(col)

                        #get average of two complete columns
                        df['avg'] = df[complete_cols_].mean(axis=1)
                        X_ = complete_data_[complete_cols_].mean(axis=1).values
                        y_ = complete_data_[incomplete_cols_].values
                        lr_ = LinearRegression()
                        lr_.fit(X_.reshape(-1,1), y_)
                        m_ = lr_.coef_[0]
                        b_ = lr_.intercept_
                        df.loc[case3_mask, incomplete_cols_] = m_ * df.loc[case3_mask, 'avg'] + b_    
              
                # Case 4: if empty rows between non empty rows are less than 24, interpolate linear
                max_nan = 24

                for col in df.columns:
                        case1=df[col].isna()
                        case_groups = case1.ne(case1.shift()).cumsum() #create groups with dates
                        case_size = case1.groupby(case_groups).transform("size") #size of each group
                        for group,size in case_size.items():
                                if size < max_nan +1:
                                        df.loc[group:group+ pd.offsets.Hour(1)] = df.loc[group:group+ pd.offsets.Hour(1)].interpolate(method="linear", limit_direction="both", axis=0)  
                return df.filter(final_fil)