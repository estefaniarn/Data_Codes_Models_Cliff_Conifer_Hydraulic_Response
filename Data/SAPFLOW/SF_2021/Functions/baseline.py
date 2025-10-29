
import numpy as np
import plotly.express as px

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
    for week in week_vals: #another potential way     SF_wd_min.loc[(week_ind,day_ind)]
        sf_week=SF_wd_min.xs(week).reset_index() 
        sf_week=sf_week.astype({'day':'float','HPVO':'float','HPVI':'float'})
        if ((sf_week[nam].values.all())==False)&((np.isnan(sf_week[nam].values).all())==False): #weeks with zero values and that are not ALL NaN
            sf_week_nz=sf_week.loc[~(sf_week==0).any(axis=1)].copy() #get only non-zero values 
            if sf_week_nz.empty==False: 
                #LINEAR REGRESSION day vs min flow (by week)
                #PLOTS AND RETRIEVES SLOPE AND INTERCEPT FOR LR 
                fig = px.scatter(sf_week_nz, x=sf_week_nz['day'], y=sf_week_nz[nam], trendline="ols")#fig.show()
                model = px.get_trendline_results(fig)
                results=model.iloc[0]["px_fit_results"]###############################
                b_lr=results.params[0] #parameters to adjust missing values
                m_lr=results.params[1]
                LR_w_b_m.append((week,b_lr,m_lr))

                #DLR
                sf_week_nz['LR_hpvo']=sf_week_nz['day']*m_lr+b_lr
                sf_dlr=sf_week_nz.loc[(sf_week_nz['LR_hpvo']>sf_week_nz[nam])] 
                try:
                    if ((sf_dlr[nam].values.all())==True)&((np.isnan(sf_dlr[nam].values).all())==False)&((len(sf_dlr[nam].values))>1): #weeks with the above conditions and more than one point 
                        fig_dlr = px.scatter(sf_dlr, x=sf_dlr['day'], y=sf_dlr[nam], trendline="ols")#fig_dlr.show()
                        model_dlr = px.get_trendline_results(fig_dlr)
                        results_dlr=model_dlr.iloc[0]["px_fit_results"]###############################
                        b_dlr=results_dlr.params[0] #parameters to adjust missing values
                        m_dlr=results_dlr.params[1]
                        DLR_w_b_m.append((week,b_dlr,m_dlr))#***
                    else: 
                        b_dlr=b_lr
                        m_dlr=m_lr 
                        DLR_w_b_m.append((week,b_dlr,m_dlr)) 
                except Exception as e:
                        b_dlr=b_lr
                        m_dlr=m_lr   
                        DLR_w_b_m.append((week,b_dlr,m_dlr)) 

        elif ((sf_week[nam].values.all())==True)&((np.isnan(sf_week[nam].values).all())==False): #weeks with NON zero values and that are not ALL NaN
            #LR
            fig = px.scatter(sf_week, x=sf_week['day'], y=sf_week[nam], trendline="ols")#fig.show()
            model = px.get_trendline_results(fig)
            results=model.iloc[0]["px_fit_results"]###############################
            b_lr=results.params[0] #parameters to adjust missing values
            m_lr=results.params[1]
            LR_w_b_m.append((week,b_lr,m_lr)) 


            #DLR 
            sf_week['LR_hpvo']=(sf_week['day']*m_lr)+b_lr
            sf_dlr=sf_week.loc[(sf_week['LR_hpvo']>sf_week[nam])] 
            try:
                if ((sf_dlr[nam].values.all())==True)&((np.isnan(sf_dlr[nam].values).all())==False)&((len(sf_dlr[nam].values))>1): #weeks with the above conditions and more than one point 
                    fig_dlr = px.scatter(sf_dlr, x=sf_dlr['day'], y=sf_dlr[nam], trendline="ols")#fig_dlr.show()
                    model_dlr = px.get_trendline_results(fig_dlr)
                    results_dlr=model_dlr.iloc[0]["px_fit_results"]###############################
                    b_dlr=results_dlr.params[0] #parameters to adjust missing values
                    m_dlr=results_dlr.params[1]
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



    ## LR & DLR 
    # https://notebook.community/Mashimo/datascience/01-Regression/LRinference

    # fig = px.line()
    # fig.add_scatter(x=SF_corr.index.to_series(), y=SF_corr['HPVI'],name="uncorrected")
    # fig.add_scatter(x=SF_corr.index.to_series(), y=SF_corr['HPVI_LR'],name="hpvo_LR")
    # fig.add_scatter(x=SF_corr.index.to_series(), y=SF_corr['HPVI_DLR'],name="hpvo_DLR")
    # #fig.write_html(str(path_cwd) + tree +'_baseline'+'.html')
    # #fig.show()

        # OP#1: list of small dfs with grouped by week and day
        # ls_gb_wd=[list(df.groupby(['day'])) for df in [list(SF_wd.groupby(['week']))[i][1] for i in range(len(list(week_vals)))]]
        # for i in range(len(ls_gb_wd)):
        #     unzipped = zip(*ls_gb_wd[i]) #to get 1st element of list of tuples 
        #     ls_subdfs=list(list(unzipped)[1])
        #     print(tree,len(ls_subdfs))

        # OP#2: list of small dfs with grouped by week and day
        # for i in list(week_vals): 
        #     SF_w=SF_wd.loc[(SF_wd['week']==i)]
        #     for j in list(day_vals): 
        #         SF_d=SF_w.loc[(SF_w['day']==j)]
        #         print(SF_d)


# ATTEMPT TO CORRECT WITH ONLY RAIN DAY WHEN WE KNOW FLOW IS MOSTLY ZERO (IT CHANGES THROUGHTOUT THE SEASON SO THE RESULTS ARE NOT THE BEST)
# SIMILAR TO MERLIN ET AL. PRE-DAWN VALUE- not used because in drought periods flow does not seem to go to zero (which is the premise of PD-value)
#from baseline import baseline_rain 
#SF_corr,noise_T=baseline_rain(k,SF_raw) # IN: thermal diff and SF_df; OUT: corrected SF_df,zero_flow_stats
    

def baseline_rain (k,SF_raw): 
    new_df=SF_raw.copy()

    #4. Filter for raw values close to 1, low VPD and low radiation days during days we know it rained a lot 
    SF_red=new_df[(new_df['VPD'] < 0.1) & (new_df['NR'] < 1)].loc['2021-08-16 22:00:00':'2021-08-18 00:00:00'] #reduced
         
    #5. Get average value for those days (and std)
    mean_zero_in,std_zero_in=SF_red['RatioIn'].describe().loc[['mean','std']]
    mean_zero_out,std_zero_out=SF_red['RatioOut'].describe().loc[['mean','std']]
    min_zero_out=np.min(SF_red['RatioOut'])

    #6. Move inner probe with the above condition to 1 and the outer one relatively 
    new_df['RatioIn_corr_mean']=new_df['RatioIn']-(mean_zero_in-1)
    new_df['RatioOut_corr_mean']=new_df['RatioOut']-(mean_zero_out-1) #correct out with mean 
    new_df['RatioOut_corr_min']=new_df['RatioOut']-(min_zero_out-1)

    new_df.loc[new_df['RatioOut_corr_min']<= 0.9,'RatioOut_corr_min']=np.nan
    new_df.loc[new_df['RatioIn_corr_mean']<= 0.9,'RatioIn_corr_mean']=np.nan #both lines remove really negative values

    #7. Create new col with sensor T to see T variation in outer sensor and sort of calculate noise #think this further it doesn't make a lot of sense/
    TdO=new_df['MaxTdO']-new_df['RiseTdO'] #temperature of inner and outer respectively 
    TuO=new_df['MaxTuO']-new_df['RiseTuO']
    new_df['T_var']=TdO/TuO 
    new_df['Diff_Tvar_Ratio']=new_df['RatioOut_corr_min']-(new_df['T_var']-1)
    noise_T=np.mean((new_df['Diff_Tvar_Ratio']-new_df['RatioOut_corr_min']).loc['2021-06-01 00:00:00':'2021-09-10 23:30:00'])

    #7.1 SW/VC temp
    TVC=(TuO+TdO)/2
    new_df['Cambium Temperature (C)']=TVC 
    
    #8.Calculate Heat Pulse Velocity

    new_df['HPVI']=np.log(new_df['RatioIn_corr_mean'])*(k/0.6)*3600 #heat pulse velocity cm/h
    new_df['HPVO']=np.log(new_df['RatioOut_corr_min'])*(k/0.6)*3600
    new_df_hpv=new_df
    #new_df_sf=new_df.drop(columns=['NR','RatioOut_corr_mean','Diff_Tvar_Ratio','T_var']) #,'VPD'

    return new_df_hpv,noise_T