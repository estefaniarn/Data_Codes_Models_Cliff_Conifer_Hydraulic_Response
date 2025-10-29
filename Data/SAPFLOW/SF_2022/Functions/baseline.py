import numpy as np
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
#import plotly.io as pio

def baseline_LR_DLR(SF_raw,nam): 
    SF_wd=SF_raw.copy()
    SF_wd[['week','day']]=(SF_wd.index.isocalendar())[['week','day']] #creates new cols in original df with week of year and day of week

    SF_wd_min=(SF_wd.loc[SF_wd['NR']<5]).groupby(['week','day']).min().filter(['HPVO','HPVI']) #select only low radiation times (i.e night, early morning, late aft, rain days) min value and only hpv
    week_vals=np.unique(SF_wd_min.index.get_level_values(0).values) #gets single number of weeks / #day_vals=np.unique(SF_wd_min.index.get_level_values(1).values)

    LR_w_b_m=[]
    DLR_w_b_m=[]

    import warnings
    warnings.filterwarnings("error")

    #the following loop does a weekly LR and DLR with days as the independent variable and HPVO or HPVI as dependent 
    for week in week_vals: 
        sf_week=SF_wd_min.xs(week).reset_index() #xs selects the week and resets the index to 0,1,2,3,4,5,6
        sf_week=sf_week.astype({'day':'float','HPVO':'float','HPVI':'float'})

        if ((sf_week[nam].values.all())==False)&((np.isnan(sf_week[nam].values).all())==False): #weeks with zero values and that are not ALL NaN
            sf_week_nz=sf_week.loc[~(sf_week==0).any(axis=1)].copy() #get only non-zero values 

            if sf_week_nz.empty==False: 
                #LINEAR REGRESSION day vs min flow (by week)
                sf_week_dnz=sf_week_nz.copy().dropna()
                X_nz = sf_week_dnz['day'].values.reshape(-1, 1)
                y_nz = sf_week_dnz[nam].values
                lr = LinearRegression()
                lr.fit(X_nz, y_nz)                
                b_lr = lr.intercept_
                m_lr = lr.coef_[0]

                LR_w_b_m.append((week,b_lr,m_lr))

                #DLR
                sf_week_nz['LR_hpvo']=sf_week_nz['day']*m_lr+b_lr
                sf_dlr=sf_week_nz.loc[(sf_week_nz['LR_hpvo']>sf_week_nz[nam])] 
                try:
                    if ((sf_dlr[nam].values.all())==True)&((np.isnan(sf_dlr[nam].values).all())==False)&((len(sf_dlr[nam].values))>1): #weeks with the above conditions and more than one point 
                        X_dlr = sf_dlr['day'].values.reshape(-1, 1)
                        y_dlr = sf_dlr[nam].values
                        lr = LinearRegression()
                        lr.fit(X_dlr, y_dlr)                
                        b_dlr = lr.intercept_
                        m_dlr = lr.coef_[0]
                        DLR_w_b_m.append((week,b_dlr,m_dlr))
            
                    else: 
                        b_dlr=b_lr
                        m_dlr=m_lr 
                        DLR_w_b_m.append((week,b_dlr,m_dlr)) 
                except Exception as e:
                        b_dlr=b_lr
                        m_dlr=m_lr   
                        DLR_w_b_m.append((week,b_dlr,m_dlr)) 


        elif ((sf_week[nam].values.all())==True)&((np.isnan(sf_week[nam].values).all())==False)&(len(sf_week)>1): #weeks with NON zero values and that are not ALL NaN
            #LR
            sf_week_dn=sf_week.copy().dropna()
            X = sf_week_dn['day'].values.reshape(-1, 1)
            y = sf_week_dn[nam].values
            lr = LinearRegression()
            lr.fit(X, y)                
            b_lr = lr.intercept_
            m_lr = lr.coef_[0]

            
            LR_w_b_m.append((week,b_lr,m_lr)) 

            #DLR 
            sf_week['LR_hpvo']=(sf_week['day']*m_lr)+b_lr
            sf_dlr=sf_week.loc[(sf_week['LR_hpvo']>sf_week[nam])] 
            try:
                if ((sf_dlr[nam].values.all())==True)&((np.isnan(sf_dlr[nam].values).all())==False)&((len(sf_dlr[nam].values))>1): #weeks with the above conditions and more than one point 
                    X_dlr = sf_dlr['day'].values.reshape(-1, 1)
                    y_dlr = sf_dlr[nam].values
                    lr = LinearRegression()
                    lr.fit(X_dlr, y_dlr)                
                    b_dlr = lr.intercept_
                    m_dlr = lr.coef_[0]
                    DLR_w_b_m.append((week,b_dlr,m_dlr))
                else: 
                    b_dlr=b_lr
                    m_dlr=m_lr
                    DLR_w_b_m.append((week,b_dlr,m_dlr))

            except Exception as e:
                    b_dlr=b_lr
                    m_dlr=m_lr
                    DLR_w_b_m.append((week,b_dlr,m_dlr))
        else: 
            b_dlr=b_lr=np.nan
            m_dlr=m_lr=np.nan
            LR_w_b_m.append((week,b_lr,m_lr))


    weeks_LR=[LR_w_b_m[j][0] for j in range(len(LR_w_b_m))] 
    weeks_DLR=[DLR_w_b_m[j][0] for j in range(len(DLR_w_b_m))]

    
    new_min_LR=list(SF_wd['day'].values.copy())
    new_min_DLR=list(SF_wd['day'].values.copy())

    for i,(week,day) in enumerate(zip(SF_wd['week'],SF_wd['day'])): 
        if len(LR_w_b_m)==len(DLR_w_b_m):
            for j in range(len(weeks_LR)): 
                if week==weeks_LR[j]: 
                    new_min_LR[i]=day*(LR_w_b_m[j][2])+(LR_w_b_m[j][1])
                    new_min_DLR[i]=day*(DLR_w_b_m[j][2])+(DLR_w_b_m[j][1])


        else:
            for j in range(len(weeks_LR)): 
                if week==weeks_LR[j]: 
                    new_min_LR[i]=day*(LR_w_b_m[j][2])+(LR_w_b_m[j][1])
    
                    
            for k in range(len(weeks_DLR)):
                if week==weeks_DLR[k]:
                    new_min_DLR[i]=day*(DLR_w_b_m[k][2])+(DLR_w_b_m[k][1])

    SF_wd['new_min_LR']=new_min_LR
    SF_wd['new_min_DLR']=new_min_DLR
    SF_wd['hpv_lr']=SF_wd[nam]-SF_wd['new_min_LR']
    SF_wd['hpv_dlr']=SF_wd[nam]-SF_wd['new_min_DLR']

    #Extra here with raw values: Cambium T 
    TdO=SF_wd['MaxTdO']-SF_wd['RiseTdO'] #temperature of inner and outer respectively 
    TuO=SF_wd['MaxTuO']-SF_wd['RiseTuO']
    TVC=(TuO+TdO)/2
    #SF_wd['Sapwood Temperature (C)']=TVC 

    return SF_wd['hpv_lr'].values,SF_wd['hpv_dlr'].values,TVC
