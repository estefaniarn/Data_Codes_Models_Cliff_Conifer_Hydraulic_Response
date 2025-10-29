SAPFLOW
FOLDERS 
	** Data_input: 
		- inputfiles:(for more information see README_inputfiles.xlsx in LATEST)
			-filenames: inputfiles.csv
				-column names:
					Filename: SENSORNAME.CSV, e.g SFM1J20P.CSV 
					Tree: Assigned tree name,number, and site e.g DF49GT/ES51US (string)
					Start_date: Documented in field notes or data files when instrument was installed/started measuring, e.g 2021-05-05 15:30 (string)
					Soil: Name of soil sensor in that tree, e.g z122 TDR (string)
					Reading: Number of files per sensor 1 or 2  (numerical)
					Output: Number of files per sens 1 or 2 (numerical)
					FW: Fresh weight (kg) (DIFFUSIVITY.CSV) (numerical)
					DW: Dry weight (kg ) (DIFFUSIVITY.CSV) (numerical)
					Vol: Volume (cm3) (DIFFUSIVITY.CSV) (numerical)
					Bark_depth: Depth of bark (cm) (SAPWOOD_AREAS.CSV) (numerical)	
					SW_depth: Sapwood depth (cm) (SAPWOOD_AREAS.CSV) (numerical)	
					Diameter: Diameter outer bark (cm) (SAPWOOD_AREAS.CSV) (numerical)	
		- SFM1 instrument data 
            -filenames: 'SFM1J20P.CSV','SFM1I60R.CSV','SFM1I60Q-initial.CSV','SFM1K308.CSV','SFM1I60T.CSV','SFM1J406-initial.CSV','SFM1J20O.CSV','SFM1J20N.CSV','SFM1I60S.CSV'
                    -original variables with units: 
						Date:
						Time:
						UO/UI:
						CO/CI:
						SFO/SFI:
						MaxTdO/MaxTuO:
						RiseTdO/RiseTuO:
						RatioOut:
						MaxTdI/MaxTuI:
						RiseTdI/RiseTuI:
						RatioIn:
						Pulse:
						BatteryVolt:
						BatteryT:
						ExternalPowerPresent:
						ExternalPowerVoltage:
						ExternalPowerCurrent:
						Message: 
		- Environmental and soil data (they are automatically generated when soil and weather scripts are run)


	** Functions: 
		-baseline.py: 
			- baseline_LR_DLR (SF_raw,column_name): 
				Corrects baseline values through linear and double-linear regression in a moving window of 1 week throughout the season (methods in Merlin et al. (2020) and Lu et al. (2004))								
				Sapwood/'cambium' Temp is calculated as (TVC=AVG_up-down_out(MaxT_recorded-T_rise)) 

			- #baseline_rain (k,SF_raw):
				Localizes heat ratio values when VPD and NR is low on rainy days (dates specified by user INSIDE function: new_df[(new_df['VPD'] < 0.1) & (new_df['NR'] < 1)].loc['2021-08-16 22:00:00':'2021-08-18 00:00:00']) 
				Gets average and min of these values then substracts it from original values. Makes really negative vals NaN. 

		-reading.py: 
			- read_sf1(pathinput,SF_cols, name): 
				create df for instruments that have a single input csv file
			
			- read_sf2(path_input,SF_cols,name): 
				create df for instruments that have two input csv files

			- sf_env_soil(path_input,ini_date,soil,SF,k): 
				Reads environmental and soil data. (path to input files should have same name )
				Crops all the data frames to the same size (when we have available data)
				Transform raw heat ratio (RatioIn or RatioOut) to heat pulse (HPVI, HPVO) using the calculated diffusivity (k)
				Return separately SF_W: saplflow and weather cropped and SM: just soil moisture data 


	** Data_output (corrected)
		- Saves files from SF as ORIGINAL_NAME-DF/ES##-corr.csv
		- Saves into: 
			ANALYSIS-CORRECTEDLOOP-Data_input
			DATA OUTPUT OF CURRENT WD

	** Literature:
	-Merlin et al. (2020)-Quantification of uncertainties introduced by data-processing procedures of sap flow measurements using the cut-tree method on a large mature tree
	-Lu et al. (2004)-Grainer's Thermal Dissipation Probe (TDP) Method for Measuring Sap Flow in Trees

Note: the time series for some instruments are not complete. 
We created another script to fill the missing data CLEANING/SAPFLOW/SF_2021/Data_output/fill_ts.py
and CLEANING/SAPFLOW/SF_2022/Data_output/fill_ts.py