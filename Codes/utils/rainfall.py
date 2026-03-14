import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_cumulative_rainfall_with_periods(trees_data):
    """
    Plot cumulative rainfall for each year, identify dry and wet periods, and overlay colored boxes.
    Dry periods are defined as periods of >= 15 days with <= 3 mm rainfall increase, using a variable window
    to find the longest possible dry periods. All dry periods are plotted in red, with the longest dry period
    having higher opacity. Wet periods are all other periods. Returns figures for 2021 and 2022 and a dictionary
    of dry periods with labels (e.g., D1_21, D2_21 for 2021).

    Parameters:
    trees_data (dict): Dictionary containing tree data with 'SF' (including 'Rain') for each tree-year

    Returns:
    tuple: (figures, dry_periods)
        - figures: Dictionary containing Plotly figures for 2021 and 2022 with keys 'rainfall_2021' and 'rainfall_2022'
        - dry_periods: Dictionary with years as keys and lists of (start_date, end_date, rainfall_increase, label) tuples
    """
    # Group trees by year
    trees_by_year = {}
    for tree_key, data in trees_data.items():
        year = str(data['year'])
        if year not in trees_by_year:
            trees_by_year[year] = []
        trees_by_year[year].append((tree_key, data))

    # Dictionary to store figures for 2021 and 2022
    figures = {}
    # Dictionary to store dry periods
    dry_periods = {'2021': [], '2022': []}

    # Create a plot for each year
    for year in sorted(trees_by_year.keys()):
        trees = trees_by_year[year]
        print(f"Cumulative Rainfall with Dry Periods for {year}")

        # Create a subplot with a single y-axis
        fig = make_subplots(specs=[[{"secondary_y": False}]])

        # Get rainfall data (use the first tree's SF data for rainfall, assuming rainfall is the same for all trees in a year)
        rainfall_added = False
        cumrain = None
        for tree_key, data in trees:
            if 'SF' in data and isinstance(data['SF'], pd.DataFrame) and not data['SF'].empty and 'Rain' in data['SF'].columns:
                rain = data['SF']['Rain'].copy()
                # Ensure the index is datetime
                if not pd.api.types.is_datetime64_any_dtype(rain.index):
                    rain.index = pd.to_datetime(rain.index, errors='coerce')
                # Remove any NaT values
                rain = rain[rain.index.notna()]
                if not rain.empty:
                    cumrain = rain.cumsum()
                    # Add cumulative rainfall to primary y-axis
                    fig.add_trace(go.Scatter(
                        x=cumrain.index, 
                        y=cumrain.values, 
                        mode='lines', 
                        name='Cumulative Rainfall (mm)', 
                        line=dict(color='blue')
                    ), secondary_y=False)
                    rainfall_added = True
                    break
        if not rainfall_added:
            print(f"Warning: No valid rainfall data available for year {year}")
            continue

        # Identify dry and wet periods
        if cumrain is not None:
            # Resample to daily frequency to simplify period detection
            cumrain_daily = cumrain.resample('D').last().ffill()
            
            # Parameters for dry period detection
            min_days_dry = 21  # Minimum duration for a dry period (in days)
            max_rain_increase = 3  # Maximum rainfall increase (mm) for a dry period
            
            # Initialize lists to store periods
            dry_periods_list = []
            wet_periods = []
            
            # Convert to a list of (date, value) for easier iteration
            dates = cumrain_daily.index
            values = cumrain_daily.values
            start_idx = 0
            
            while start_idx < len(dates):
                start_date = dates[start_idx]
                start_value = values[start_idx]
                longest_dry_end_idx = None
                longest_dry_end_date = None
                
                # Look for the longest possible dry period starting at start_idx
                for end_idx in range(start_idx + min_days_dry, len(dates)):
                    end_date = dates[end_idx]
                    time_diff = (end_date - start_date).days
                    rain_increase = values[end_idx] - start_value
                    
                    if time_diff >= min_days_dry and rain_increase <= max_rain_increase:
                        longest_dry_end_idx = end_idx
                        longest_dry_end_date = end_date
                    elif rain_increase > max_rain_increase:
                        break
                
                if longest_dry_end_idx is not None:
                    dry_periods_list.append((start_date, longest_dry_end_date))
                    start_idx = longest_dry_end_idx + 1
                else:
                    end_idx = start_idx + 1
                    while end_idx < len(dates):
                        rain_increase = values[end_idx] - start_value
                        time_diff = (dates[end_idx] - start_date).days
                        if rain_increase > max_rain_increase or time_diff >= min_days_dry:
                            break
                        end_idx += 1
                    
                    if end_idx < len(dates):
                        wet_periods.append((start_date, dates[end_idx]))
                    else:
                        wet_periods.append((start_date, dates[-1]))
                    start_idx = end_idx + 1
            
            # Find the longest dry period and assign labels
            longest_period = None
            max_duration = 0
            for start_date, end_date in dry_periods_list:
                duration = (end_date - start_date).days
                if duration > max_duration:
                    max_duration = duration
                    longest_period = (start_date, end_date)
            
            # Add boxes for all dry periods
            for start_date, end_date in dry_periods_list:
                opacity = 0.4 if (start_date, end_date) == longest_period else 0.2
                fig.add_shape(
                    type="rect",
                    x0=start_date,
                    x1=end_date,
                    y0=0,
                    y1=cumrain.max() * 1.05,
                    fillcolor="red",
                    opacity=opacity,
                    line=dict(width=0),
                    layer="below"
                )

            # Store dry periods with labels and rainfall increase
            if year in ['2021', '2022']:
                for i, (start_date, end_date) in enumerate(sorted(dry_periods_list, key=lambda x: x[0]), 1):
                    rain_increase = cumrain[end_date] - cumrain[start_date] if start_date in cumrain.index and end_date in cumrain.index else 0
                    label = f"D{i}_{year[-2:]}"
                    dry_periods[year].append((start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), round(rain_increase, 1), label))

        # Set x-axis title
        fig.update_xaxes(title_text="Date")

        # Set y-axes titles
        fig.update_yaxes(title_text="Cumulative Rainfall (mm)", secondary_y=False)

        # Update layout
        fig.update_layout(
            showlegend=False,
            height=400,
            width=800
        )
                
        # Store figures for 2021 and 2022
        if year == '2021':
            figures['rainfall_2021'] = fig
        elif year == '2022':
            figures['rainfall_2022'] = fig
        
        #fig.show() # UNCOMMENT TO SHOW FIGURES IN JUPYTER NOTEBOOK
        
        # Print all identified dry periods for reference
        # print(f"\nDry periods for {year}:")
        # for start, end in dry_periods_list:
        #     duration = (end - start).days
        #     rain_increase = cumrain[end] - cumrain[start] if start in cumrain.index and end in cumrain.index else 0
        #     print(f"  {start.date()} to {end.date()} ({duration} days, {rain_increase:.1f} mm)")
        
        # print(f"\nWet periods for {year}:")
        # for start, end in sorted(wet_periods, key=lambda x: x[0]):
        #     duration = (end - start).days
        #     rain_increase = cumrain[end] - cumrain[start] if start in cumrain.index and end in cumrain.index else 0
        #     print(f"  {start.date()} to {end.date()} ({duration} days, {rain_increase:.1f} mm)")


    return figures, dry_periods
