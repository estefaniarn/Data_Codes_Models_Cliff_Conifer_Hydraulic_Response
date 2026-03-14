# utils/read_and_create_dict.py
# utils/read_and_create_dict.py

import os
import sys
from pathlib import Path
from csv import DictReader
import pandas as pd
import numpy as np

def read_and_create_dict():
    """
    Define paths, create the trees_data dictionary from inputfiles.csv, read data files,
    and store the data in the dictionary.
    
    Returns:
        dict: trees_data dictionary with metadata and processed data (SF, SM, PSY, SF_HR, SF_W_SM_PSY).
        dict: Dictionary containing the paths (path_input, path_output_data, etc.).
    """
    # Step 1: Define paths
    path_cwd = Path.cwd()
    path_input = str(path_cwd) + '/Input_files/'
    path_output_graphs = str(path_cwd) + '/Output_graphs/'
    path_output_data = str(path_cwd) + '/Output_files/'
    path_latex = str(path_cwd.parents[0]) + '/TEX_file/Figures/'
    
    paths = {
        'path_input': path_input,
        'path_output_graphs': path_output_graphs,
        'path_output_data': path_output_data,
        'path_latex': path_latex
    }
    
    # Step 2: Define column names
    sf_cols = ['Date', 'Rain', 'Temp', 'WS', 'NR', 'VPD', 'PET', 'SV']
    sf_cols_complete = sf_cols + ['SF_complete']
    sf_cols_incomplete = sf_cols + ['SF_incomplete']
    sf_cols_combined = sf_cols + ['SF_complete', 'SF_incomplete']
    psy_cols = ['Date', 'PSY']
    
    # Step 3: Initialize dictionary to store all tree data
    trees_data = {}
    
    # Required columns in inputfiles.csv
    required_columns = ['Tree', 'Species', 'Site', 'Year', 'SF_W', 'SF_W_incomplete', 'Soil', 'Psy', 'Reading', 'Type_year', 'Compare', 'Bark_depth', 'SW_depth', 'Diameter','Leaf_areas']
  
    # Step 4: Read inputfiles.csv and build the dictionary
    with open(path_input + 'inputfiles.csv', encoding='utf-8-sig') as read_obj:
        dict_reader = DictReader(read_obj)
        list_of_dict = list(dict_reader)
    
        # Validate columns
        missing_columns = [col for col in required_columns if col not in list_of_dict[0]]
        if missing_columns:
            raise ValueError(f"Missing required columns in inputfiles.csv: {missing_columns}")
    
        for entry in list_of_dict:
            tree = entry['Tree']
            year = entry['Year']
            tree_key = f"{tree}-{year}"
    
            # Convert numerical options
            options = {}
            for key, value in entry.items():
                if key not in ['Tree', 'Species', 'Site', 'Year', 'SF_W', 'SF_W_incomplete', 'Soil', 'Psy']:
                    try:
                        # Replace commas with dots for numerical parsing (e.g., "3,1" -> "3.1")
                        if isinstance(value, str):
                            value = value.replace(',', '.')
                        options[key] = float(value) if value and value != 'NA' else None
                    except (ValueError, TypeError):
                        print(f"Warning: Non-numerical value '{value}' for {key} in {tree_key}, keeping as string")
                        options[key] = value
    
            # Handle 'NA' values in file paths and validate existing files
            for file_key in ['SF_W', 'SF_W_incomplete', 'Soil', 'Psy']:
                file_value = entry[file_key]
                if file_value == 'NA' or not file_value:  # Handle 'NA' or empty strings
                    print(f"Info: No {file_key} file specified for {tree_key} (value: {file_value})")
                    entry[file_key] = None
                else:
                    file_path = path_input + file_value
                    if not os.path.exists(file_path):
                        print(f"Warning: File {file_path} for {tree_key} does not exist")
                        entry[file_key] = None
    
            # Store metadata in the dictionary
            trees_data[tree_key] = {
                'tree': tree,
                'species': entry['Species'],
                'site': entry['Site'],
                'year': year,
                'sf_w': entry['SF_W'],
                'sf_i': entry['SF_W_incomplete'],
                'sm': entry['Soil'],
                'psy': entry['Psy'],
                'leaf_area': entry['Leaf_areas'],
                'options': options,
                'SF': None,
                'SM': None,
                'PSY': None,
                'SF_HR': None,
                'SF_W_SM_PSY': None,
                'PSY_cleaned': None
            }
    
    # Step 5: Read data files and store in the dictionary
    for tree_key, data in trees_data.items():
        #print(f"\nReading data for {tree_key}")
        
        options = data['options']
        reading_mode = options.get('Reading')
        
        # Initialize SF, SM, PSY, SF_HR, SF_W_SM_PSY as empty DataFrames with correct columns
        sf_cols_no_date = sf_cols_combined[1:]  # Exclude 'Date' for columns
        SF = pd.DataFrame(columns=sf_cols_no_date)
        SM = pd.DataFrame(columns=['S1', 'S2', 'S3', 'Soil_moisture'])
        PSY = pd.DataFrame(columns=['PSY'])
        SF_HR = pd.DataFrame(columns=sf_cols_no_date + ['PSY'])
        SF_W_SM_PSY = pd.DataFrame(columns=sf_cols_no_date + ['S1', 'S2', 'S3', 'Soil_moisture', 'PSY'])
        
        if reading_mode == 3:  # SF+W mostly complete, SM, PSY
            # Read SF (complete)
            SF_complete = pd.DataFrame(columns=sf_cols[1:])  # Temporary DataFrame for complete data
            if data['sf_w']:
                file_path = os.path.join(path_input, data['sf_w'])
                #print(f"Attempting to load SF complete file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SF_complete = pd.read_csv(file_path, header=None, skiprows=1, names=sf_cols_complete, engine='python', index_col='Date')
                        SF_complete.index = pd.to_datetime(SF_complete.index, errors='coerce')
                        #print(f"Successfully loaded SF complete for {tree_key}: {len(SF_complete)} rows")
                    except Exception as e:
                        print(f"Error reading SF complete file for {tree_key}: {e}")
                        SF_complete = pd.DataFrame(columns=sf_cols[1:])
                else:
                    print(f"SF complete file does not exist: {file_path}")
                    SF_complete = pd.DataFrame(columns=sf_cols[1:])
            else:
                print(f"No SF complete file specified for {tree_key}")
                SF_complete = pd.DataFrame(columns=sf_cols[1:])
            
            # Read SF (incomplete)
            SF_incomplete = pd.DataFrame(columns=sf_cols[1:])  # Temporary DataFrame for incomplete data
            if data['sf_i']:
                file_path = os.path.join(path_input, data['sf_i'])
                #print(f"Attempting to load SF incomplete file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SF_incomplete = pd.read_csv(file_path, header=None, skiprows=1, names=sf_cols_incomplete, engine='python', index_col='Date')
                        SF_incomplete.index = pd.to_datetime(SF_incomplete.index, errors='coerce')
                        #print(f"Successfully loaded SF incomplete for {tree_key}: {len(SF_incomplete)} rows")
                    except Exception as e:
                        print(f"Error reading SF incomplete file for {tree_key}: {e}")
                        SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
                else:
                    print(f"SF incomplete file does not exist: {file_path}")
                    SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            else:
                print(f"No SF incomplete file specified for {tree_key}")
                SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            
            # Merge SF_complete and SF_incomplete into a single DataFrame
            if not SF_complete.empty and not SF_incomplete.empty:
                # Align indices and merge
                SF = SF_complete.copy()
                SF['SF_incomplete'] = SF_incomplete['SF_incomplete']
            elif not SF_complete.empty:
                SF = SF_complete.copy()
                SF['SF_incomplete'] = np.nan
            elif not SF_incomplete.empty:
                SF = SF_incomplete.copy()
                SF.rename(columns={'SF_incomplete': 'SF_complete'}, inplace=True)
                SF['SF_incomplete'] = SF['SF_complete'].copy()
            else:
                SF = pd.DataFrame(columns=sf_cols_no_date)
            
            # Read SM
            if data['sm']:
                file_path = os.path.join(path_input, data['sm'])
                #print(f"Attempting to load SM file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SM = pd.read_csv(file_path, engine='python', index_col='Date')
                        SM.index = pd.to_datetime(SM.index, errors='coerce')
                        #print(f"Successfully loaded SM for {tree_key}: {len(SM)} rows")
                    except Exception as e:
                        print(f"Error reading SM file for {tree_key}: {e}")
                        SM = pd.DataFrame(columns=['S1', 'S2', 'S3', 'Soil_moisture'])
                else:
                    print(f"SM file does not exist: {file_path}")
                    SM = pd.DataFrame(columns=['S1', 'S2', 'S3', 'Soil_moisture'])
            else:
                print(f"No SM file specified for {tree_key}")
                SM = pd.DataFrame(columns=['S1', 'S2', 'S3', 'Soil_moisture'])
            
            # Read PSY
            if data['psy']:
                file_path = os.path.join(path_input, data['psy'])
                #print(f"Attempting to load PSY file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        PSY = pd.read_csv(file_path, header=None, skiprows=1, names=psy_cols, engine='python', index_col='Date')
                        PSY.index = pd.to_datetime(PSY.index, errors='coerce')
                        #print(f"Successfully loaded PSY for {tree_key}: {len(PSY)} rows")
                    except Exception as e:
                        print(f"Error reading PSY file for {tree_key}: {e}")
                        PSY = pd.DataFrame(columns=['PSY'])
                else:
                    print(f"PSY file does not exist: {file_path}")
                    PSY = pd.DataFrame(columns=['PSY'])
            else:
                print(f"No PSY file specified for {tree_key}")
                PSY = pd.DataFrame(columns=['PSY'])
            
            # SF+W+SM
            if not SF.empty and not SM.empty:
                SF_W_, SM_ = SF.copy(), SM.copy()
                SM_ = SM_.loc[SF_W_.index[0]:SF_W_.index[-1]]
                SM_ = SM_.resample('0.5H').ffill()
                SF_W_ = SF_W_.loc[SM_.index[0]:SM_.index[-1]]
                SF_W_SM = pd.merge(SF_W_, SM_, left_index=True, right_index=True, how='outer')
            else:
                SF_W_SM = pd.DataFrame(columns=sf_cols_no_date + ['S1', 'S2', 'S3'])
            
            # SF+PSY for hydraulic response
            if not SF.empty and not PSY.empty:
                SF_HR, PSY_ = SF.copy(), PSY.copy()
                PSY_ = PSY_.loc[SF_HR.index[0]:SF_HR.index[-1]]
                SF_HR = SF_HR.loc[PSY_.index[0]:PSY_.index[-1]]
                SF_HR['PSY'] = PSY_['PSY'].values
                SF_HR.loc[(SF_HR['PSY'] == 0), 'PSY'] = np.nan
            else:
                SF_HR = pd.DataFrame(columns=sf_cols_no_date + ['PSY'])
            
            # ALL (SF+W+SM+PSY)
            if not SF_W_SM.empty and not PSY.empty:
                SF_W_SM_PSY, PSY_c = SF_W_SM.copy(), PSY.copy()
                PSY_c = PSY_c.loc[SF_W_SM_PSY.index[0]:SF_W_SM_PSY.index[-1]]
                SF_W_SM_PSY = SF_W_SM_PSY.loc[PSY_c.index[0]:PSY_c.index[-1]]
                SF_W_SM_PSY['PSY'] = PSY_c['PSY'].values
                SF_W_SM_PSY.loc[(SF_W_SM_PSY['PSY'] == 0), 'PSY'] = np.nan
            else:
                SF_W_SM_PSY = pd.DataFrame(columns=sf_cols_no_date + ['S1', 'S2', 'S3', 'Soil_moisture', 'PSY'])
            
            # Compute Soil Moisture
            if not SF_W_SM_PSY.empty and not SM.empty and 'S1' in SM.columns:
                if data['tree'] != 'ES42':
                    SF_W_SM_PSY['Soil_moisture'] = [(i + j + k) / 3 for i, j, k in zip(SF_W_SM_PSY['S1'], SF_W_SM_PSY['S2'], SF_W_SM_PSY['S3'])]
                    SM['Soil_moisture'] = [(i + j + k) / 3 for i, j, k in zip(SM['S1'], SM['S2'], SM['S3'])]
                else:
                    SF_W_SM_PSY['Soil_moisture'] = [(i + j) / 2 for i, j in zip(SF_W_SM_PSY['S1'], SF_W_SM_PSY['S2'])]
                    SM['Soil_moisture'] = [(i + j) / 2 for i, j in zip(SM['S1'], SM['S2'])]
            
            # Save for model
            if not SF_W_SM_PSY.empty:
                model_df = SF_W_SM_PSY.filter(['Date', 'Rain', 'PET', 'SV', 'SF_complete', 'Soil_moisture', 'PSY'], axis=1)
                model_df.to_csv(os.path.join(path_output_data, f"{data['tree']}-{data['year']}-ALL.csv"), index=True)
            
            # Store data in the dictionary
            data['SF'] = SF
            data['SM'] = SM
            data['PSY'] = PSY
            data['SF_HR'] = SF_HR
            data['SF_W_SM_PSY'] = SF_W_SM_PSY
        
        elif reading_mode == 2:  # No soil moisture
            # Read SF (complete)
            SF_complete = pd.DataFrame(columns=sf_cols[1:])
            if data['sf_w']:
                file_path = os.path.join(path_input, data['sf_w'])
                #print(f"Attempting to load SF complete file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SF_complete = pd.read_csv(file_path, header=None, skiprows=1, names=sf_cols_complete, engine='python', index_col='Date')
                        SF_complete.index = pd.to_datetime(SF_complete.index, errors='coerce')
                        #print(f"Successfully loaded SF complete for {tree_key}: {len(SF_complete)} rows")
                    except Exception as e:
                        print(f"Error reading SF complete file for {tree_key}: {e}")
                        SF_complete = pd.DataFrame(columns=sf_cols[1:])
                else:
                    print(f"SF complete file does not exist: {file_path}")
                    SF_complete = pd.DataFrame(columns=sf_cols[1:])
            else:
                print(f"No SF complete file specified for {tree_key}")
                SF_complete = pd.DataFrame(columns=sf_cols[1:])
            
            # Read SF (incomplete)
            SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            if data['sf_i']:
                file_path = os.path.join(path_input, data['sf_i'])
                #print(f"Attempting to load SF incomplete file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SF_incomplete = pd.read_csv(file_path, header=None, skiprows=1, names=sf_cols_incomplete, engine='python', index_col='Date')
                        SF_incomplete.index = pd.to_datetime(SF_incomplete.index, errors='coerce')
                        #print(f"Successfully loaded SF incomplete for {tree_key}: {len(SF_incomplete)} rows")
                    except Exception as e:
                        print(f"Error reading SF incomplete file for {tree_key}: {e}")
                        SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
                else:
                    print(f"SF incomplete file does not exist: {file_path}")
                    SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            else:
                print(f"No SF incomplete file specified for {tree_key}")
                SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            
            # Merge SF_complete and SF_incomplete into a single DataFrame
            if not SF_complete.empty and not SF_incomplete.empty:
                SF = SF_complete.copy()
                SF['SF_incomplete'] = SF_incomplete['SF_incomplete']
            elif not SF_complete.empty:
                SF = SF_complete.copy()
                SF['SF_incomplete'] = np.nan
            elif not SF_incomplete.empty:
                SF = SF_incomplete.copy()
                SF.rename(columns={'SF_incomplete': 'SF_complete'}, inplace=True)
                SF['SF_incomplete'] = SF['SF_complete'].copy()
            else:
                SF = pd.DataFrame(columns=sf_cols_no_date)
            
            # Read PSY
            if data['psy']:
                file_path = os.path.join(path_input, data['psy'])
                #print(f"Attempting to load PSY file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        PSY = pd.read_csv(file_path, header=None, skiprows=1, names=psy_cols, engine='python', index_col='Date')
                        PSY.index = pd.to_datetime(PSY.index, errors='coerce')
                        #print(f"Successfully loaded PSY for {tree_key}: {len(PSY)} rows")
                    except Exception as e:
                        print(f"Error reading PSY file for {tree_key}: {e}")
                        PSY = pd.DataFrame(columns=['PSY'])
                else:
                    print(f"PSY file does not exist: {file_path}")
                    PSY = pd.DataFrame(columns=['PSY'])
            else:
                print(f"No PSY file specified for {tree_key}")
                PSY = pd.DataFrame(columns=['PSY'])
            
            # SF+PSY for hydraulic response
            if not SF.empty and not PSY.empty:
                SF_HR, PSY_ = SF.copy(), PSY.copy()
                PSY_ = PSY_.loc[SF_HR.index[0]:SF_HR.index[-1]]
                SF_HR = SF_HR.loc[PSY_.index[0]:PSY_.index[-1]]
                SF_HR['PSY'] = PSY_['PSY'].values
                SF_HR.loc[(SF_HR['PSY'] == 0), 'PSY'] = np.nan
            else:
                SF_HR = pd.DataFrame(columns=sf_cols_no_date + ['PSY'])
            
            SM = pd.DataFrame(columns=['S1', 'S2', 'S3', 'Soil_moisture'])
            SF_W_SM_PSY = pd.DataFrame(columns=sf_cols_no_date + ['S1', 'S2', 'S3', 'Soil_moisture', 'PSY'])
            
            # Store data in the dictionary
            data['SF'] = SF
            data['SM'] = SM
            data['PSY'] = PSY
            data['SF_HR'] = SF_HR
            data['SF_W_SM_PSY'] = SF_W_SM_PSY
        
        elif reading_mode == 1:  # No soil moisture, no PSY
            # Read SF (complete)
            SF_complete = pd.DataFrame(columns=sf_cols[1:])
            if data['sf_w']:
                file_path = os.path.join(path_input, data['sf_w'])
                #print(f"Attempting to load SF complete file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SF_complete = pd.read_csv(file_path, header=None, skiprows=1, names=sf_cols_complete, engine='python', index_col='Date')
                        SF_complete.index = pd.to_datetime(SF_complete.index, errors='coerce')
                        #print(f"Successfully loaded SF complete for {tree_key}: {len(SF_complete)} rows")
                    except Exception as e:
                        print(f"Error reading SF complete file for {tree_key}: {e}")
                        SF_complete = pd.DataFrame(columns=sf_cols[1:])
                else:
                    print(f"SF complete file does not exist: {file_path}")
                    SF_complete = pd.DataFrame(columns=sf_cols[1:])
            else:
                print(f"No SF complete file specified for {tree_key}")
                SF_complete = pd.DataFrame(columns=sf_cols[1:])
            
            # Read SF (incomplete)
            SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            if data['sf_i']:
                file_path = os.path.join(path_input, data['sf_i'])
                #print(f"Attempting to load SF incomplete file: {file_path}")
                if os.path.exists(file_path):
                    try:
                        SF_incomplete = pd.read_csv(file_path, header=None, skiprows=1, names=sf_cols_incomplete, engine='python', index_col='Date')
                        SF_incomplete.index = pd.to_datetime(SF_incomplete.index, errors='coerce')
                        #print(f"Successfully loaded SF incomplete for {tree_key}: {len(SF_incomplete)} rows")
                    except Exception as e:
                        print(f"Error reading SF incomplete file for {tree_key}: {e}")
                        SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
                else:
                    print(f"SF incomplete file does not exist: {file_path}")
                    SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            else:
                print(f"No SF incomplete file specified for {tree_key}")
                SF_incomplete = pd.DataFrame(columns=sf_cols[1:])
            
            # Merge SF_complete and SF_incomplete into a single DataFrame
            if not SF_complete.empty and not SF_incomplete.empty:
                SF = SF_complete.copy()
                SF['SF_incomplete'] = SF_incomplete['SF_incomplete']
            elif not SF_complete.empty:
                SF = SF_complete.copy()
                SF['SF_incomplete'] = np.nan
            elif not SF_incomplete.empty:
                SF = SF_incomplete.copy()
                SF.rename(columns={'SF_incomplete': 'SF_complete'}, inplace=True)
                SF['SF_incomplete'] = SF['SF_complete'].copy()
            else:
                SF = pd.DataFrame(columns=sf_cols_no_date)
            
            PSY = pd.DataFrame(columns=['PSY'])
            SF_HR = pd.DataFrame(columns=sf_cols_no_date + ['PSY'])
            SM = pd.DataFrame(columns=['S1', 'S2', 'S3', 'Soil_moisture'])
            SF_W_SM_PSY = pd.DataFrame(columns=sf_cols_no_date + ['S1', 'S2', 'S3', 'Soil_moisture', 'PSY'])
            
            # Store data in the dictionary
            data['SF'] = SF
            data['SM'] = SM
            data['PSY'] = PSY
            data['SF_HR'] = SF_HR
            data['SF_W_SM_PSY'] = SF_W_SM_PSY
    
    #print("\nFinished reading data files.")
    return trees_data, paths
