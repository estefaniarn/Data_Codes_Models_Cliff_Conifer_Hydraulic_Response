import pandas as pd
import numpy as np

def clean_psy_data(psy, tree: str, year: str) -> pd.DataFrame:
    """
    Clean the PSY data for a specific tree and year.
    
    Args:
        psy (pd.DataFrame): DataFrame containing PSY data.
        tree (str): Tree identifier (e.g., 'DF49').
        year (str): Year of the data (e.g., '2021').
    
    Returns:
        pd.DataFrame: Cleaned PSY DataFrame.
    """
    #print(f"Cleaning PSY data for {tree}-{year}")

    if psy is None:
        print(f"  PSY data for {tree}-{year} is None")
        return pd.DataFrame(columns=['PSY'])

    psy_cleaned = psy.copy()

    if psy_cleaned.empty or psy_cleaned['PSY'].isna().all():
        print(f"  PSY data for {tree}-{year} is empty or all NaN")
        return psy_cleaned

    # Step 1: Truncate data based on year
    if year == '2021':
        psy_cleaned = psy_cleaned.loc[:'2021-10-01 00:00:00']
    elif year == '2022':
        psy_cleaned = psy_cleaned.loc[:'2022-10-01 00:00:00']
    #print(f"  After truncation: {len(psy_cleaned)} rows")

    # Step 2: Apply special conditions (NaN ranges and start dates)
    special_conditions = {
        ('DF49', '2022'): {'start': '2022-05-25 17:00:00'},
        ('ES48', '2021'): {'nan_range': ('2021-09-03 00:00:00', None)},
        ('DF21', '2021'): {
            'nan_ranges': [
                ('2021-08-14 00:00:00', '2021-08-17 23:30:00'),
                ('2021-07-19 00:00:00', '2021-07-20 23:30:00')
            ]
        },
        ('DF27', '2021'): {
            'nan_ranges': [
                ('2021-08-10 23:00:00', '2021-08-18 19:00:00'),
                ('2021-06-22 21:00:00', '2021-06-24 18:00:00')
            ]
        },
        ('DF27', '2022'): {
            'nan_ranges': [
                (psy_cleaned.index.min(), '2022-07-05 23:30:00')  # Replaced 'start' with index.min()
            ]
        },
        ('ES51', '2021'): {
            'nan_ranges': [
                ('2021-07-22 00:00:00', '2021-07-24 5:30:00'),
                ('2021-08-01 00:00:00', '2021-08-18 23:30:00'),
                ('2021-08-12 00:00:00', '2021-08-19 11:30:00'),
                ('2021-09-30 00:00:00', '2021-09-30 23:30:00'),
            ]
        },
        ('ES50', '2021'): {
            'nan_ranges': [
                ('2021-08-12 00:00:00', '2021-08-18 00:00:00')
            ]
        },
        ('ES50', '2022'): {
            'nan_ranges': [
                ('2022-07-06 00:00:00', '2022-08-28 11:00:00')
            ]
        },
        ('ES48', '2022'): {
            'start': '2022-05-30 00:00:00',
            'nan_ranges': [
                ('2022-06-20 00:00:00', '2022-07-13 23:30:00'),
                ('2022-07-29 21:00:00', '2022-08-05 23:30:00'),
                ('2022-08-07 00:00:00', '2022-08-22 00:00:00'),
                ('2022-08-22 18:00:00', '2022-09-09 07:30:00'),
            ]
        },
        ('DF21', '2022'): {'nan_range': ('2022-08-18 00:00:00', None)},
        ('ES42', '2022'): {
            'nan_ranges': [
                ('2022-07-13 00:00:00', '2022-07-22 23:30:00'),
                ('2022-07-29 00:00:00', '2022-08-27 23:30:00')
            ]
        },
        ('DF03', '2022'): {'nan_range': ('2022-07-05 00:00:00', '2022-07-05 23:00:00')}
    }

    condition = special_conditions.get((tree, year))
    if condition:
        if 'start' in condition:
            #print(f"  Applying start condition for {tree}-{year}: {condition['start']}")
            psy_cleaned = psy_cleaned.loc[condition['start']:]
        if 'nan_range' in condition:
            start, end = condition['nan_range']
            #print(f"  Setting NaN range for {tree}-{year}: {start} to {end}")
            psy_cleaned.loc[start:end, 'PSY'] = np.nan
        if 'nan_ranges' in condition:
            for start, end in condition['nan_ranges']:
                if start == 'start':
                    start = psy_cleaned.index.min()  # Handle 'start' dynamically
                #print(f"  Setting NaN range for {tree}-{year}: {start} to {end}")
                psy_cleaned.loc[start:end, 'PSY'] = np.nan
    #print(f"  After special conditions: {len(psy_cleaned)} rows (non-NaN: {psy_cleaned['PSY'].notna().sum()})")

    # Step 3: Midday Water Potential (remove days without midday measurements)
    # Find the daily minimum water potential
    psy_dmin = psy_cleaned.groupby(pd.Grouper(freq='24H'))['PSY'].transform('min')
    # Find the times where PSY equals the daily minimum
    psyh = psy_cleaned[psy_cleaned['PSY'] == psy_dmin]
    # Select dates where the minimum occurs between 8 AM and 8 PM
    selected_dates = psyh.index.date[(psyh.index.hour >= 8) & (psyh.index.hour <= 20)]
    
    # Create a mask for dates with midday measurements
    if len(selected_dates) > 0:
        mask = psy_cleaned.index.date == selected_dates[0]
        for date in selected_dates[1:]:
            mask |= psy_cleaned.index.date == date
        # Set non-midday days to NaN
        psy_nmd = psy_cleaned.copy()
        psy_nmd.loc[~mask, 'PSY'] = np.nan
    else:
        #print(f"  No midday measurements found for {tree}-{year}")
        psy_nmd = psy_cleaned.copy()
        psy_nmd['PSY'] = np.nan
    #print(f"  After removing non-midday days: {len(psy_nmd)} rows (non-NaN: {psy_nmd['PSY'].notna().sum()})")

    # Step 4: Remove days with low values (> -0.3 MPa)
    psy_low = psy_nmd.copy()
    value_condition = psy_low['PSY'] > -0.3  # This should now work as a Series comparison
    # Calculate the percentage of low values per day
    daily_counts = psy_low.groupby(pd.Grouper(freq='D'))['PSY'].count()
    low_value_counts = psy_low[value_condition].groupby(pd.Grouper(freq='D'))['PSY'].count()
    # Avoid division by zero by filling NaN with 0
    low_value_counts = low_value_counts.fillna(0)
    daily_counts = daily_counts.replace(0, np.nan)  # Avoid division by zero
    perc_condition = (low_value_counts / daily_counts) >= 1.0
    select_dates_low = perc_condition.index[perc_condition].date  # Dates with all low values
    
    if len(select_dates_low) > 0:
        mask_low = psy_low.index.date == select_dates_low[0]
        for date in select_dates_low[1:]:
            mask_low |= psy_low.index.date == date
        psy_low.loc[mask_low, 'PSY'] = np.nan
        #print(f"  Removed {len(select_dates_low)} days with low values (> -0.3 MPa)")
    #print(f"  After removing low value days: {len(psy_low)} rows (non-NaN: {psy_low['PSY'].notna().sum()})")

    return psy_low

def clean_psy_in_dict(trees_data):
    """
    Apply PSY data cleaning to all trees in the trees_data dictionary.
    
    Args:
        trees_data (dict): Dictionary with tree keys and nested dictionaries containing processed data.
    
    Returns:
        dict: Updated trees_data dictionary with cleaned PSY data stored as 'PSY_cleaned'.
    """
    #print("Starting PSY data cleaning...")
    for tree_key, data in trees_data.items():
        try:
            cleaned_psy = clean_psy_data(data['PSY'], data['tree'], str(data['year']))
            data['PSY_cleaned'] = cleaned_psy
            #print(f"Assigned PSY_cleaned for {tree_key}: {len(cleaned_psy)} rows (non-NaN: {cleaned_psy['PSY'].notna().sum()})")
        except Exception as e:
            print(f"Error cleaning PSY data for {tree_key}: {e}")
            data['PSY_cleaned'] = pd.DataFrame(columns=['PSY'])
    #print("Finished cleaning PSY data.")
    return trees_data