

WEATHER+RADIATION 
FOLDERS
    **Data_input: Make sure that files (depending on origin:Wasootch,BGI,or Jumpingpound) have the same format than existing ones 
	 * THIS FOLDER NEEDS TO BE UPDATED WITH THE LATEST DATA
        -Wasootch: Same format as the HOBO station gives 
            -Met station 
                -filenames: WEATHER19.csv,WEATHER20.csv,WEATHER21.csv
                    -original variables with units: 
                        Date Time: format variable yyyy-mm-dd hh:mm and yyyy/mm/dd hh:mm:ss AM/PM
                        Rain: mm (Rain gauge)
                        Temp: °C (Temp)
                        RH: % (Relative humidity )	
                        Wind Speed: m/s (Vwind)	
                        Gust Speed: m/s (10796394)	
                        DewPt: °C (10698881)
            -Radiation
                -filenames: RAD# 
                    -variables with units: yyyy-mm-dd hh:mm
                    TIMESTAMP: 
                    NR_Wm2: W/meter^2
                    NR_Wm2_Avg: W/meter^2

        -BGI: Data downloaded from:https://research.ucalgary.ca/biogeoscience-institute/research/environmental-data
        Check in folder the .xlsx file named:'BGI-Weather-instructions-format' to modify format from excel (save as CSV with appropriate name)
            -Metstation with radiation data
                -filenames: BGI19.csv,BGI20.csv,BGI21.csv
                    -original variables with units: 
                        Air Temp Current: C 
                        Air Temp Avg: C
                        Air Temp Max: C	
                        Air Temp Min: C
                        Solar Rad: 	w/m2
                        Rainfall: mm	
                        Soil Temp: C (50 cm	30 cm	10 cm)
        -JumpingPound: Data downloaded from:https://scholar.uc.edu/concern/parent/2227mq412/file_sets/tx31qj85c?locale=en
        Delete 1st col from original file, remove comas from names (colname,unit to colname) and delete cols K to S in excel 
            -Metstation with Photosynthetic Active Radiation (PAR) Data
                -filename: Jumpingpound2010-2022
                    -original variables with units: 
                        Date Time: yyyy/mm/dd hh:mm
                        Voltage: V	
                        Current: mA	
                        PAR: uE	
                        Temp: C	
                        RH: %	
                        Rain: mm	
                        Wind Speed: m/s	
                        Gust Speed: m/s	
                        Wind Direction: ?

    **Functions: 
        -functions_reading.py
            -reading_hobo(): Wasootch data 
                *in line 
                dfs_year=[pd.read_table(str(path_cwd)+'/Data_input'+'/'+name,sep=',',skiprows=2, names=dfs_cols) for name in ['WEATHER19.csv','WEATHER20.csv','WEATHER21.csv']] add WEATHER22.csv when available 
                
            -reading_BGI(): BiogeoScience Institute data 
                *in line: 
                dfs_year=[pd.read_table(str(path_cwd)+'/Data_input'+'/'+name,sep=',',skiprows=1, names=dfs_cols) for name in ['BGI19.csv','BGI20.csv','BGI21.csv']] add BGI22.csv when available 

            -reading_JP(): Jumping Pound 
                *slightly modify function if we add a new file 
            
            -readind_rad(): Campbell radiometer at Wasootch 
                *change range based on no. of files: range(1,number of RAD files +1)
                names_rad=[str(path_cwd)+'/Data_input'+'/'+'RAD'+str(i) for i in range(1,8)] 

        -functions_plotting.py
            Includes 2 plotly functions to plot time series quickly 
            -visually_compare(df1,df2,col_name_df1, col_name_df2)

            -plot_ts(df,col_name)

        -functions_data.py
            -cut_merge(all_dfs=[list of all the dfs to cut and merge])

            -replace_nans_one(df,col_df_nan,col_df_replace): choose df that has 2 columns with the same variable and the one with nans is refilled with the complete one 

            -replace_nans_list(df,cols_nan=[list of all the variables with gaps],cols_replace=[list of complete columns]): 
            *check that lists are in correct order e.g cols_nan=['Rain(mm)','Temp(C)','RH','WS','GS','DP']   cols_replace=['Rain_BGI(mm)','Temp_BGI(C)','RH_JP','WS_JP','GS_JP','DP_JP'
            
            -correlation_fun(df,cname_W,cname_BGI):Function that calculates correlation. Returns pearson r coeficient and graphs incomplete data from one station vs the complete one from another station. cname_W=incomplete cname_BGI=complete

        -functions_calculations.py
            -vpd(df)
            -pet(df) 
            *Formulas used are from 'THE ASCE STANDARDIZED REFERENCE EVAPOTRANSPIRATION EQUATION' (in Literature for calculations folder)
            Make sure units of T are in C, ws in m/s, and NetRad in W/m2 (the function pet converts radiation from W/m2 to MJ/m2h) 


    ** Data_output:
	-ENVIRONMENTAL.csv: Includes all variables generated for VPD and PET calculations
	-ENVIRONMENTAL_tidy.csv: Just kept VPD1 and PET1 	
		-variables:
			DateTime	
			Rain(mm)	
			Temp(C)	
			RH(%)	
			NetRad(W/m2)	
			NetRad(MJ/m2h)	
			VPD(kPa)
			PET(mm/h)

    ** Literature for calculations: 
	-ASCE manual 
	-FAO manual 
	-Rodriguez Iturbe paper for Poisson

            


    

