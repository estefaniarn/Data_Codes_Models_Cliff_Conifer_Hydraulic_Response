# utils/predawn.py

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression

def calculate_predawn_water_potential(trees_data):
    """
    Calculate daily predawn water potential (Ψ_pd) by performing linear regression on nighttime data (10 PM to 7 AM)
    between SF_incomplete (independent) and PSY_cleaned (dependent) for each tree. Only use days with at least 90% non-NaN data.
    The intercept of the regression (PSY = slope * SF + intercept) is the predawn water potential.
    If the intercept is positive, set it to a small negative value (-0.0001 MPa) to represent wet soil.
    
    Parameters:
    trees_data (dict): Dictionary containing tree data with 'SF' and 'PSY_cleaned'
    
    Returns:
    dict: Updated trees_data with 'PSY_predawn' key containing daily predawn water potentials
    """
    for tree_year, data in trees_data.items():
        # Check if SF and PSY_cleaned data exist
        sf_data = data.get('SF')
        psy_data = data.get('PSY_cleaned')
        
        if (sf_data is None or 
            not isinstance(sf_data, pd.DataFrame) or 
            sf_data.empty or 
            'SF_incomplete' not in sf_data.columns or 
            sf_data['SF_incomplete'].isna().all() or
            psy_data is None or 
            not isinstance(psy_data, pd.DataFrame) or 
            psy_data.empty or 
            'PSY' not in psy_data.columns or 
            psy_data['PSY'].isna().all()):
            data['PSY_predawn'] = pd.Series(dtype=float, index=psy_data.index if psy_data is not None else pd.Index([]))
            continue
        
        # Align SF and PSY_cleaned data
        sf_df = sf_data[['SF_incomplete']].copy()
        sf_df = sf_df[sf_df['SF_incomplete'] >= 0]  # Ensure non-negative sap flow
        psy_df = psy_data[['PSY']].copy()
        
        # Align by index
        aligned_df = sf_df.join(psy_df, how='inner')
        
        if aligned_df.empty:
            data['PSY_predawn'] = pd.Series(dtype=float, index=psy_data.index)
            continue
        
        # Filter for nighttime (10 PM to 7 AM)
        night_time_data = aligned_df[(aligned_df.index.hour >= 22) | (aligned_df.index.hour <= 7)].copy()
        if night_time_data.empty:
            data['PSY_predawn'] = pd.Series(dtype=float, index=psy_data.index)
            continue
        
        # Add day column for grouping
        night_time_data['day'] = night_time_data.index.date
        
        # Calculate expected number of nighttime measurements per day
        # Nighttime is 10 PM to 7 AM = 9 hours = 18 half-hourly measurements (assuming 30-minute intervals)
        expected_measurements_per_day = 18
        
        # Initialize series to store daily predawn water potentials
        daily_intercept_series = pd.Series(dtype=float, index=psy_data.index)
        
        # Process each day
        for day in night_time_data['day'].unique():
            day_data = night_time_data[night_time_data['day'] == day].copy()
            
            # Check data completeness (at least 90% non-NaN for both SF and PSY)
            non_nan_count = day_data[['SF_incomplete', 'PSY']].notna().all(axis=1).sum()
            completeness = non_nan_count / expected_measurements_per_day
            if completeness < 0.9:
                continue  # Skip days with insufficient data
            
            # Drop rows with NaN values for regression
            day_data = day_data.dropna(subset=['SF_incomplete', 'PSY'])
            
            if len(day_data) < 2:  # Need at least 2 points for regression
                continue
            
            # Perform linear regression: PSY (y) on SF_incomplete (x)
            X = day_data['SF_incomplete'].values.reshape(-1, 1)  # Independent variable (SF_incomplete, cm³/h)
            y = day_data['PSY'].values                           # Dependent variable (PSY, MPa)
            model = LinearRegression().fit(X, y)
            
            # The intercept represents Ψ_pd (PSY when SF_incomplete = 0)
            psy_predawn = model.intercept_
            
            ######### Print the intercept for verification
            #print(f"Tree {tree_year}, Day {day}: Initial Ψ_pd = {psy_predawn:.4f} MPa")
            
            # Adjust the intercept if it's positive
            if psy_predawn > 0:
                psy_predawn = -0.2  # Set to a small negative value for wet soil 0.0001
                ########print(f"Adjusted Ψ_pd to {psy_predawn} MPa (was positive)")
            
            # Assign the predawn water potential to all timestamps on this day
            daily_filter = (psy_data.index.date == day)
            daily_intercept_series[daily_filter] = psy_predawn
        
        # Store in trees_data
        data['PSY_predawn'] = daily_intercept_series
    
    return trees_data

###############################################################################
###############################################################################
###############################################################################
def plot_predawn_scatter(trees_data, year):
    """
    Plot nighttime SF_incomplete (x-axis) vs. PSY (y-axis) (10 PM to 7 AM) for each tree, colored by day of year with a color bar representing months.
    
    Parameters:
    trees_data (dict): Dictionary containing tree data with 'SF' and 'PSY_cleaned'
    year (str): Year to filter data ('2021' or '2022')
    
    Returns:
    list: List of tuples, each containing a plotly figure and the corresponding tree name
    """
    import plotly.graph_objects as go
    import pandas as pd
    import numpy as np
    import calendar
    from datetime import datetime

    results = []
    
    for tree_year, data in trees_data.items():
        if data['year'] != year:
            continue
        
        tree_name = data['tree']
        sf_data = data.get('SF')
        psy_data = data.get('PSY_cleaned')
        
        if (sf_data is None or 
            not isinstance(sf_data, pd.DataFrame) or 
            sf_data.empty or 
            'SF_incomplete' not in sf_data.columns or 
            sf_data['SF_incomplete'].isna().all() or
            psy_data is None or 
            not isinstance(psy_data, pd.DataFrame) or 
            psy_data.empty or 
            'PSY' not in psy_data.columns or 
            psy_data['PSY'].isna().all()):
            continue
        
        # Align SF and PSY_cleaned data
        sf_df = sf_data[['SF_incomplete']].copy()
        sf_df = sf_df[sf_df['SF_incomplete'] >= 0]
        psy_df = psy_data[['PSY']].copy()
        aligned_df = sf_df.join(psy_df, how='inner')
        
        if aligned_df.empty:
            continue
        
        # Filter for nighttime (10 PM to 7 AM)
        night_time_data = aligned_df[(aligned_df.index.hour >= 22) | (aligned_df.index.hour <= 7)].copy()
        if night_time_data.empty:
            continue
        
        night_time_data['day'] = night_time_data.index.date
        
        # Expected measurements per day (for completeness check)
        expected_measurements_per_day = 18  # 9 hours at 30-minute intervals
        
        # Group by day and filter complete days
        grouped = night_time_data.groupby('day')
        valid_data = []
        
        for day, day_data in grouped:
            day_data = day_data.copy()
            non_nan_count = day_data[['SF_incomplete', 'PSY']].notna().all(axis=1).sum()
            completeness = non_nan_count / expected_measurements_per_day
            if completeness < 0.9:
                continue
            
            day_data = day_data.dropna(subset=['SF_incomplete', 'PSY'])
            if len(day_data) < 2:
                continue
            
            valid_data.append(day_data)
        
        if not valid_data:
            continue
        
        all_valid_data = pd.concat(valid_data)
        if all_valid_data.empty:
            continue
        
        # Add dayofyear
        all_valid_data['dayofyear'] = all_valid_data.index.dayofyear
        all_valid_data['month'] = all_valid_data.index.month
        
        # Get unique months and set colorbar ticks
        unique_months = sorted(all_valid_data['month'].unique())
        tickvals = []
        ticktext = []
        
        for m in unique_months:
            _, days_in_month = calendar.monthrange(int(year), m)
            mid_day = (1 + days_in_month) / 2
            first_day = datetime(int(year), m, 1)
            mid_doy = first_day.timetuple().tm_yday + mid_day - 1
            tickvals.append(mid_doy)
            ticktext.append(first_day.strftime('%b'))
        
        # Plotting
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=all_valid_data['SF_incomplete'],  # x-axis: Sap Flow (SF, cm³/h)
            y=all_valid_data['PSY'],            # y-axis: Water Potential (PSY_cleaned, MPa)
            mode='markers',
            marker=dict(
                color=all_valid_data['dayofyear'],
                colorscale='hsv',
                size=5,
                colorbar=dict(
                    title='Month',
                    tickmode='array',
                    tickvals=tickvals,
                    ticktext=ticktext
                )
            ),
            showlegend=False
        ))
        
        # Update layout
        fig.update_layout(
            xaxis_title='Sap Flow (cm³/h)',
            yaxis_title='Water Potential Ψx (MPa)'
        )

        results.append((fig, tree_name))
        print(tree_name)
        fig.show()
    return results

##ORIGINAL FOR PLOTTIG WITH DAY LABELS 
# ###############################################################################
# def plot_predawn_scatter(trees_data, year):
#     """
#     Plot nighttime SF_incomplete (x-axis) vs. PSY (y-axis) (10 PM to 7 AM) for each tree, colored by day.
    
#     Parameters:
#     trees_data (dict): Dictionary containing tree data with 'SF' and 'PSY_cleaned'
#     year (str): Year to filter data ('2021' or '2022')
    
#     Returns:
#     list: List of tuples, each containing a plotly figure and the corresponding tree name
#     """
#     import plotly.graph_objects as go
#     import pandas as pd
#     import numpy as np

#     results = []
    
#     for tree_year, data in trees_data.items():
#         if data['year'] != year:
#             continue
        
#         tree_name = data['tree']
#         sf_data = data.get('SF')
#         psy_data = data.get('PSY_cleaned')
        
#         if (sf_data is None or 
#             not isinstance(sf_data, pd.DataFrame) or 
#             sf_data.empty or 
#             'SF_incomplete' not in sf_data.columns or 
#             sf_data['SF_incomplete'].isna().all() or
#             psy_data is None or 
#             not isinstance(psy_data, pd.DataFrame) or 
#             psy_data.empty or 
#             'PSY' not in psy_data.columns or 
#             psy_data['PSY'].isna().all()):
#             continue
        
#         # Align SF and PSY_cleaned data
#         sf_df = sf_data[['SF_incomplete']].copy()
#         sf_df = sf_df[sf_df['SF_incomplete'] >= 0]
#         psy_df = psy_data[['PSY']].copy()
#         aligned_df = sf_df.join(psy_df, how='inner')
        
#         if aligned_df.empty:
#             continue
        
#         # Filter for nighttime (10 PM to 7 AM)
#         night_time_data = aligned_df[(aligned_df.index.hour >= 22) | (aligned_df.index.hour <= 7)].copy()
#         if night_time_data.empty:
#             continue
        
#         night_time_data['day'] = night_time_data.index.date
        
#         # Plotting
#         fig = go.Figure()
        
#         # Generate colors for each day
#         unique_days = sorted(night_time_data['day'].unique())
#         colors = ['hsl('+str(h)+',50%,50%)' for h in np.linspace(0, 360, len(unique_days))]
        
#         # Expected measurements per day (for completeness check)
#         expected_measurements_per_day = 18  # 9 hours at 30-minute intervals
        
#         for day, color in zip(unique_days, colors):
#             day_data = night_time_data[night_time_data['day'] == day].copy()
            
#             # Check data completeness
#             non_nan_count = day_data[['SF_incomplete', 'PSY']].notna().all(axis=1).sum()
#             completeness = non_nan_count / expected_measurements_per_day
#             if completeness < 0.9:
#                 continue
            
#             day_data = day_data.dropna(subset=['SF_incomplete', 'PSY'])
#             if len(day_data) < 2:
#                 continue
            
#             # Scatter plot of SF_incomplete (x) vs. PSY (y)
#             fig.add_trace(go.Scatter(
#                 x=day_data['SF_incomplete'],  # x-axis: Sap Flow (SF, cm³/h)
#                 y=day_data['PSY'],            # y-axis: Water Potential (PSY_cleaned, MPa)
#                 mode='markers',
#                 name=f'Day {day}',
#                 marker=dict(color=color, size=5)
#             ))
            
#         if not fig.data:  # Skip if no data to plot
#             continue
        
#         # Update layout
#         fig.update_layout(
#             xaxis_title='Sap Flow (cm³/h)',
#             yaxis_title='Water Potential Ψx (MPa)',
#             legend=dict(
#                 orientation="v",
#                 x=1.05,
#                 y=1,
#                 xanchor="left",
#                 yanchor="top",
#                 itemsizing='constant'
#             ),
#             margin=dict(r=200)  # Add margin on the right for the legend
#         )

#         results.append((fig, tree_name))
#         print(tree_name)
#         fig.show()
#     return results

###############################################################################

###############################################################################

###############################################################################
#Visualizing time series  
def plot_psy_matric_daily(trees_data, year):
    """
    Plot the daily average predawn water potential (from intercepts) and matric potential (from van Genuchten model)
    for each tree in a given year, using nighttime data (10 PM to 7 AM) for matric potential.

    Parameters:
    trees_data (dict): Dictionary containing tree data with 'PSY_predawn' and 'PSY_matric' for each tree-year
    year (str): Year to filter data ('2021' or '2022')
    
    Returns:
    fig: Plotly figure object
    """
    import plotly.graph_objects as go
    import pandas as pd
    import numpy as np

    fig = go.Figure()

    # Define a custom color palette with paired colors (bright for PSY_predawn, dark for PSY_matric)
    base_colors = [
        # Red
        ('hsl(359, 100%, 70%)', 'hsl(359, 100%, 40%)'),  # Bright: #FF6B6D, Dark: #CC3D3F
        # Orange
        ('hsl(35, 100%, 70%)', 'hsl(35, 100%, 40%)'),    # Bright: #FFBB66, Dark: #CC8633
        # Gold
        ('hsl(45, 100%, 60%)', 'hsl(45, 100%, 40%)'),    # Bright: #FFCD39, Dark: #CC9A06
        # Green
        ('hsl(144, 70%, 60%)', 'hsl(144, 70%, 40%)'),    # Bright: #54D98C, Dark: #24A35A
        # Teal
        ('hsl(187, 75%, 70%)', 'hsl(187, 75%, 45%)'),    # Bright: #4DD0E1, Dark: #1E9AAE
        # Purple
        ('hsl(270, 50%, 70%)', 'hsl(270, 50%, 45%)'),    # Bright: #B399CC, Dark: #8C66A3
        # Brown
        ('hsl(12, 25%, 60%)', 'hsl(12, 25%, 40%)'),      # Bright: #A68A80, Dark: #70574F
        # Light Pink (replacing Coral)
        ('hsl(340, 70%, 85%)', 'hsl(340, 70%, 60%)'),    # Bright: #F7C9D6, Dark: #EB91AB
        # Grey
        ('hsl(0, 0%, 70%)', 'hsl(0, 0%, 45%)'),          # Bright: #B3B3B3, Dark: #737373
    ]

    # Create a mapping of tree names to color pairs for consistency across years
    all_tree_names = sorted(set(data['tree'] for data in trees_data.values()))
    num_trees_total = len(all_tree_names)
    color_pairs = base_colors * (num_trees_total // len(base_colors) + 1)  # Repeat palette if needed
    color_pairs = color_pairs[:num_trees_total]  # Trim to the number of unique trees
    tree_color_map = {tree_name: color_pair for tree_name, color_pair in zip(all_tree_names, color_pairs)}

    for tree_year, data in trees_data.items():
        if data['year'] != year:
            continue
        
        tree_name = data['tree']
        daily_intercept_series = data.get('PSY_predawn')
        psy_matric_df = data.get('PSY_matric')  # This is a DataFrame
        
        if (daily_intercept_series is None or daily_intercept_series.empty or 
            psy_matric_df is None or psy_matric_df.empty):
            print(f"Skipping {tree_name} ({tree_year}) for {year} due to no data.")
            continue
        
        # Process predawn water potential (intercepts) series
        df_intercept = daily_intercept_series.to_frame(name='Intercept').dropna()
        df_intercept['Intercept'] = df_intercept['Intercept'].where((df_intercept['Intercept'] <= 0))
        df_intercept['day'] = df_intercept.index.date
        daily_mean_intercept = df_intercept.groupby('day')['Intercept'].mean().reset_index()
        daily_mean_intercept['day'] = pd.to_datetime(daily_mean_intercept['day'])

        # Process matric potential DataFrame
        if 'PSY_matric' not in psy_matric_df.columns:
            print(f"Skipping {tree_name} ({tree_year}) for {year}: 'PSY_matric' column not found in PSY_matric DataFrame.")
            continue
        
        # Filter for nighttime (10 PM to 7 AM)
        psy_matric = psy_matric_df[(psy_matric_df.index.hour >= 22) | (psy_matric_df.index.hour <= 7)][['PSY_matric']].dropna()
        if psy_matric.empty:
            print(f"Skipping {tree_name} ({tree_year}) for {year}: No nighttime data for PSY_matric.")
            continue
        
        psy_matric['day'] = psy_matric.index.date
        daily_mean_matric = psy_matric.groupby('day')['PSY_matric'].mean().reset_index()
        daily_mean_matric['day'] = pd.to_datetime(daily_mean_matric['day'])

        # Get the colors for this tree from the color map
        color_predawn, color_matric = tree_color_map[tree_name]

        # Plotting with consistent colors
        fig.add_trace(go.Scatter(
            x=daily_mean_intercept['day'], 
            y=daily_mean_intercept['Intercept'], 
            mode='markers', 
            name=f'Ψ pd {tree_name}',
            marker=dict(color=color_predawn)
        ))
        fig.add_trace(go.Scatter(
            x=daily_mean_matric['day'], 
            y=daily_mean_matric['PSY_matric'], 
            mode='markers', 
            name=f'Ψ matric {tree_name}', 
            marker_symbol='square',
            marker=dict(color=color_matric)
        ))

    # Update figure layout
    fig.update_layout(
       #title=f'Daily Average of Intercept and Nighttime Matric Potential for {year}',
        xaxis_title='Date',
        yaxis_title='Soil Water Potential (MPa)',
        legend_title="Legend",
        xaxis=dict(type='date'),
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.3,
            xanchor="center",
            yanchor="top",
            itemsizing='constant'
        )
    )
    
    fig.show()
    return fig


#######################################################################################
#######################################################################################
###################Hydraulic Disconnection-regression  ##############################

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import kruskal

def plot_hydraulic_disconnection(trees_data, year):
    """
    Visualize Ψ_pd vs. Ψ_matric scatter plots for trees with complete pre-dry, dry, and post-dry data
    in the specified year, using a 1:1 line to highlight hydraulic disconnection. Performs KW tests
    within each tree for pre-dry vs. dry, dry vs. post, and pre-dry vs. post.

    Parameters:
    trees_data (dict): Dictionary with 'PSY_matric', 'PSY_predawn', 'tree', and 'year' for each tree-year.
    year (str): Year to filter data ('2021' or '2022').

    Returns:
    dict: Metrics including average ΔΨ per period for the year, total days with data, and KW test results.
    """
    # Define dry periods based on rainfall data
    dry_periods = {
        '2021': [('2021-07-13', '2021-08-15', 5.6)],
        '2022': [('2022-07-30', '2022-08-20', 2.4)]  # Updated dry period for 2022
    }

    # Define trees with complete data for the year
    complete_trees = {
        '2021': ['DF27', 'ES50'],  # Cliff trees
        '2022': ['DF49', 'ES48']   # Soil trees
    }
    target_trees = complete_trees.get(year, [])

    # Convert dry periods to bins and labels
    periods = dry_periods.get(year, [])
    if not periods:
        print(f"No dry periods defined for {year}. Skipping.")
        return {}
    
    start_year = pd.Timestamp(f'{year}-01-01')
    end_year = pd.Timestamp(f'{year}-12-31')
    bins = [start_year]
    for start, end, _ in periods:
        bins.append(pd.to_datetime(start))
        bins.append(pd.to_datetime(end))
    bins.append(end_year + pd.Timedelta(days=1))
    labels = ['Pre-Dry', 'Dry', 'Post-Dry']
    period_def = {'bins': bins, 'labels': labels}

    # Define soil and cliff trees
    soil_trees = {'DF49', 'ES48'}
    cliff_trees = {'DF27', 'ES50'}

    metrics = {}

    for tree_name in target_trees:
        tree_data = next((data for data in trees_data.values() if data['tree'] == tree_name and data['year'] == year), None)
        if not tree_data:
            print(f"No data for {tree_name} in {year}. Skipping.")
            continue
        
        psy_matric_df = tree_data.get('PSY_matric')
        psy_predawn_series = tree_data.get('PSY_predawn')
        
        if psy_matric_df is None or psy_matric_df.empty or psy_predawn_series is None or psy_predawn_series.empty:
            print(f"Skipping {tree_name} ({year}): Missing or empty data.")
            continue
        
        # Nighttime filter (10 PM to 7 AM)
        nighttime_filter = (psy_matric_df.index.hour >= 22) | (psy_matric_df.index.hour <= 7)
        psy_matric_night = psy_matric_df[nighttime_filter][['PSY_matric']].copy()
        
        # Align Ψ_pd to daily values
        psy_predawn_daily = psy_predawn_series.resample('D').mean()
        psy_matric_night['Ψ_pd'] = psy_matric_night.index.map(lambda x: psy_predawn_daily.get(pd.Timestamp(x.date()), np.nan))
        
        # Calculate ΔΨ and assign periods
        psy_matric_night = psy_matric_night.dropna(subset=['PSY_matric', 'Ψ_pd'])
        psy_matric_night['ΔΨ'] = psy_matric_night['Ψ_pd'] - psy_matric_night['PSY_matric']
        psy_matric_night['period'] = pd.cut(psy_matric_night.index, bins=period_def['bins'], labels=period_def['labels'], right=False)
        
        if psy_matric_night.empty:
            print(f"No valid data for {tree_name} ({year}).")
            continue
        
        # Compute daily stats
        daily_stats = psy_matric_night.groupby(psy_matric_night.index.date).agg({
            'PSY_matric': 'mean',
            'Ψ_pd': 'mean',
            'ΔΨ': 'mean',
            'period': 'first'
        }).reset_index()
        daily_stats['date'] = pd.to_datetime(daily_stats['index'])

        # Store and print total number of days with data
        total_days_with_data = len(daily_stats)
        if 'observation_metrics' not in metrics.get(tree_name, {}):
            metrics[tree_name] = {'observation_metrics': {}}
        metrics[tree_name]['observation_metrics']['total_days'] = total_days_with_data
        print(f"\n{tree_name} ({year}): Total days with data: {total_days_with_data}")

        # Create individual scatter plot without title
        fig = go.Figure()
        for period in labels:
            period_data = daily_stats[daily_stats['period'] == period]
            fig.add_trace(go.Scatter(
                x=period_data['PSY_matric'], y=period_data['Ψ_pd'], mode='markers',
                name=period, marker=dict(color={'Pre-Dry': 'blue', 'Dry': '#FFA500', 'Post-Dry': 'green'}[period])
            ))
        
        # Add 1:1 line
        lims = [-4, 0]  # Adjust based on your data range
        fig.add_trace(go.Scatter(x=lims, y=lims, mode='lines', line=dict(dash='dash', color='black'), name='1:1 Line'))
        
        # Add label (a), b), c), d) instead of title
        label = 'a)' if tree_name == 'DF27' and year == '2021' else \
                'b)' if tree_name == 'ES50' and year == '2021' else \
                'c)' if tree_name == 'DF49' and year == '2022' else \
                'd)' if tree_name == 'ES48' and year == '2022' else ''
        fig.update_layout(
            xaxis_title="Ψ matric (MPa)", yaxis_title="Ψ pd (MPa)",
            height=400, width=600,
            showlegend=True,
            legend=dict(orientation="h", x=0.5, y=-0.2, xanchor="center", yanchor="top"),
            # annotations=[dict(
            #     #text=label,
            #     xref="paper", yref="paper",
            #     x=0.05, y=0.95,
            #     showarrow=False
            # )]
        )
        fig.show()

    
        
        # Metrics: Average ΔΨ per period
        for period in labels:
            period_data = daily_stats[daily_stats['period'] == period]
            avg_delta_psi = period_data['ΔΨ'].mean() if not period_data.empty else np.nan
            if 'period_metrics' not in metrics.get(tree_name, {}):
                metrics[tree_name] = {'period_metrics': {}}
            metrics[tree_name]['period_metrics'][period] = avg_delta_psi

        # Kruskal-Wallis tests within tree for each period comparison
        delta_psi_values = {period: daily_stats[daily_stats['period'] == period]['ΔΨ'].dropna().tolist() for period in labels}
        kw_results = {}
        if all(len(delta_psi_values[p]) > 0 for p in labels):
            # Pre-Dry vs. Dry
            kw_pre_dry = kruskal(delta_psi_values['Pre-Dry'], delta_psi_values['Dry'])
            kw_results['Pre-Dry_vs_Dry'] = {'h_value': kw_pre_dry.statistic, 'p_value': kw_pre_dry.pvalue, 'df': 1}
            # Dry vs. Post-Dry
            kw_dry_post = kruskal(delta_psi_values['Dry'], delta_psi_values['Post-Dry'])
            kw_results['Dry_vs_Post-Dry'] = {'h_value': kw_dry_post.statistic, 'p_value': kw_dry_post.pvalue, 'df': 1}
            # Pre-Dry vs. Post-Dry
            kw_pre_post = kruskal(delta_psi_values['Pre-Dry'], delta_psi_values['Post-Dry'])
            kw_results['Pre-Dry_vs_Post-Dry'] = {'h_value': kw_pre_post.statistic, 'p_value': kw_pre_post.pvalue, 'df': 1}
            for test_name, result in kw_results.items():
                significance = "significant" if result['p_value'] < 0.05 else "not significant"
                if result['p_value'] <= 0.0001:
                    p_str = f"{result['p_value']:.2e}"  # Scientific notation for p ≤ 0.0001
                else:
                    p_str = f"{result['p_value']:.8f}"  # 8 decimals for p > 0.0001
                print(f"\nKruskal-Wallis Test for {tree_name} ({year}) - {test_name}: H = {result['h_value']:.3f}, df = {result['df']}, p = {p_str} ({significance})")
        else:
            print(f"\nInsufficient data for KW tests for {tree_name} ({year}).")

    # Print metrics
    print(f"\nMetrics for {year}:")
    for tree_name, data in metrics.items():
        tree_type = 'Soil' if tree_name in soil_trees else 'Cliff'
        print(f"\n{tree_name} ({tree_type}):")
        if 'period_metrics' in data:
            for period, delta_psi in data['period_metrics'].items():
                print(f"Average ΔΨ ({period}): {delta_psi:.3f} MPa")

    metrics['kruskal'] = kw_results
    return metrics

def compare_hydraulic_disconnection(trees_data, path_output=''):
    """
    Computes ΔΨ for trees with complete pre-dry, dry, and post-dry data across all years,
    performs Kruskal-Wallis tests to compare ΔΨ between cliff and soil trees across years for each period,
    and generates a 2x2 grid plot of all four trees.

    Parameters:
    trees_data (dict): Dictionary with 'PSY_matric', 'PSY_predawn', 'tree', and 'year' for each tree-year.

    Returns:
    dict: Metrics including ΔΨ per period and Kruskal-Wallis test results.
    """
    # Define dry periods based on rainfall data
    dry_periods = {
        '2021': [('2021-07-13', '2021-08-15', 5.6)],
        '2022': [('2022-07-30', '2022-08-20', 2.4)]  # Updated dry period for 2022
    }

    # Define trees with complete data across years
    complete_trees = {
        '2021': ['DF27', 'ES50'],  # Cliff trees
        '2022': ['DF49', 'ES48']   # Soil trees
    }

    # Combine all target trees
    target_trees = {tree for year in complete_trees for tree in complete_trees[year]}

    # Define soil and cliff trees
    soil_trees = {'DF49', 'ES48'}
    cliff_trees = {'DF27', 'ES50'}

    metrics = {}
    all_daily_stats = {}  # To store daily stats for grid plot
    all_delta_psi = {'cliff': {'Pre-Dry': [], 'Dry': [], 'Post-Dry': []}, 'soil': {'Pre-Dry': [], 'Dry': [], 'Post-Dry': []}}

    for tree_name in target_trees:
        # Find data for this tree across all years
        tree_data_list = [data for data in trees_data.values() if data['tree'] == tree_name]
        if not tree_data_list:
            print(f"No data for {tree_name}. Skipping.")
            continue

        for data in tree_data_list:
            year = data['year']
            psy_matric_df = data.get('PSY_matric')
            psy_predawn_series = data.get('PSY_predawn')

            if psy_matric_df is None or psy_matric_df.empty or psy_predawn_series is None or psy_predawn_series.empty:
                print(f"Skipping {tree_name} ({year}): Missing or empty data.")
                continue

            # Nighttime filter (10 PM to 7 AM)
            nighttime_filter = (psy_matric_df.index.hour >= 22) | (psy_matric_df.index.hour <= 7)
            psy_matric_night = psy_matric_df[nighttime_filter][['PSY_matric']].copy()

            # Align Ψ_pd to daily values
            psy_predawn_daily = psy_predawn_series.resample('D').mean()
            psy_matric_night['Ψ_pd'] = psy_matric_night.index.map(lambda x: psy_predawn_daily.get(pd.Timestamp(x.date()), np.nan))

            # Calculate ΔΨ and assign periods
            psy_matric_night = psy_matric_night.dropna(subset=['PSY_matric', 'Ψ_pd'])
            psy_matric_night['ΔΨ'] = psy_matric_night['Ψ_pd'] - psy_matric_night['PSY_matric']
            periods = dry_periods.get(year, [])
            if not periods:
                print(f"No dry periods defined for {year}. Skipping.")
                continue
            start_year = pd.Timestamp(f'{year}-01-01')
            end_year = pd.Timestamp(f'{year}-12-31')
            bins = [start_year]
            for start, end, _ in periods:
                bins.append(pd.to_datetime(start))
                bins.append(pd.to_datetime(end))
            bins.append(end_year + pd.Timedelta(days=1))
            psy_matric_night['period'] = pd.cut(psy_matric_night.index, bins=bins, labels=['Pre-Dry', 'Dry', 'Post-Dry'], right=False)

            if psy_matric_night.empty:
                print(f"No valid data for {tree_name} ({year}).")
                continue

            # Compute daily stats
            daily_stats = psy_matric_night.groupby(psy_matric_night.index.date).agg({
                'PSY_matric': 'mean',
                'Ψ_pd': 'mean',
                'ΔΨ': 'mean',
                'period': 'first'
            }).reset_index()
            daily_stats['date'] = pd.to_datetime(daily_stats['index'])
            all_daily_stats[(tree_name, year)] = daily_stats

            # Collect all daily ΔΨ values for each period (no averaging per tree)
            for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
                period_data = daily_stats[daily_stats['period'] == period]['ΔΨ'].dropna().tolist()
                if period_data:
                    if tree_name in cliff_trees:
                        all_delta_psi['cliff'][period].extend(period_data)
                    else:  # soil trees
                        all_delta_psi['soil'][period].extend(period_data)

    # Debug: Print collected ΔΨ values
    #print(f"Debug - Cliff ΔΨ: {all_delta_psi['cliff']}")
    #print(f"Debug - Soil ΔΨ: {all_delta_psi['soil']}")

    # Kruskal-Wallis tests across sites for each period (cliff 2021 vs. soil 2022)
    kw_results = {}
    for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
        cliff_data = all_delta_psi['cliff'][period]  # All daily ΔΨ for cliff trees (2021)
        soil_data = all_delta_psi['soil'][period]    # All daily ΔΨ for soil trees (2022)
        if cliff_data and soil_data and all(np.isfinite(cliff_data)) and all(np.isfinite(soil_data)):
            kruskal_result = kruskal(cliff_data, soil_data)
            h_value = kruskal_result.statistic
            p_value = kruskal_result.pvalue
            df = 1  # Degrees of freedom = number of groups - 1 (2 groups: cliff, soil)
            significance = "significant" if p_value < 0.05 else "not significant"
            if p_value <= 0.0001:
                p_str = f"{p_value:.2e}"  # Scientific notation for p ≤ 0.0001
            else:
                p_str = f"{p_value:.8f}"  # 8 decimals for p > 0.0001
            print(f"\nKruskal-Wallis Test Results for {period} (Cliff 2021 vs. Soil 2022): H = {h_value:.3f}, df = {df}, p = {p_str} ({significance})")
            kw_results[f'{period}_Cliff_vs_Soil'] = {'h_value': h_value, 'df': df, 'p_value': p_value}
        else:
            h_value = np.nan
            p_value = np.nan
            df = np.nan
            significance = "not significant (insufficient or invalid data)"
            print(f"\nKruskal-Wallis Test Results for {period} (Cliff 2021 vs. Soil 2022): H = {h_value}, df = {df}, p = {p_value} ({significance})")
            kw_results[f'{period}_Cliff_vs_Soil'] = {'h_value': h_value, 'df': df, 'p_value': p_value}

    # Create 2x2 grid plot for all four trees using make_subplots
    fig_grid = make_subplots(rows=2, cols=2, subplot_titles=('a) Cliff Douglas fir (DF27)', 'b) Cliff spruce (ES50)', 'c) Soil Douglas fir (DF49)', 'd) Soil spruce (ES48)'))
    trees_years = [('DF27', '2021'), ('ES50', '2021'), ('DF49', '2022'), ('ES48', '2022')]

    for i, (tree_name, year) in enumerate(trees_years):
        daily_stats = all_daily_stats.get((tree_name, year))
        if daily_stats is not None:
            row, col = (i // 2) + 1, (i % 2) + 1
            for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
                period_data = daily_stats[daily_stats['period'] == period]
                fig_grid.add_trace(go.Scatter(
                    x=period_data['PSY_matric'], y=period_data['Ψ_pd'], mode='markers',
                    name=f'{period}', marker=dict(color={'Pre-Dry': 'blue', 'Dry': '#FFA500', 'Post-Dry': 'green'}[period]),
                    legendgroup=period, showlegend=(i == 0 and col == 1)  # Show legend only in top-left subplot
                ), row=row, col=col)

            # Add 1:1 line to each subplot
            lims = [-4, 0]
            fig_grid.add_trace(go.Scatter(x=lims, y=lims, mode='lines', line=dict(dash='dash', color='black'), name='1:1 Line',
                                          showlegend=(i == 0 and col == 1)), row=row, col=col)

    fig_grid.update_layout(
        height=800, width=800,
        showlegend=True,
        legend=dict(orientation="h", x=0.5, y=-0.1, xanchor="center", yanchor="top")
    )
    fig_grid.update_xaxes(title_text="Ψ matric (MPa)", row=2, col=1)
    fig_grid.update_xaxes(title_text="Ψ matric (MPa)", row=2, col=2)
    fig_grid.update_yaxes(title_text="Ψ pd (MPa)", row=1, col=1)
    fig_grid.update_yaxes(title_text="Ψ pd (MPa)", row=2, col=1)
    fig_grid.show()

    # Save plots to folder s
    path_lags = path_output #+'IVC_plots/Hydraulic_disconnection/'
    fig_grid.write_image(path_lags + 'Psi_matricvsPsi_pd.png', scale=5)
    fig_grid.write_html(path_lags + 'Psi_matricvsPsi_pd.html', include_plotlyjs='cdn')

    # Print metrics
    #print(f"\nMetrics for all years:")

    for tree_name, data in metrics.items():
        tree_type = 'Soil' if tree_name in soil_trees else 'Cliff'
        print(f"\n{tree_name} ({tree_type}):")
        if 'period_metrics' in data:
            for period, delta_psi in data['period_metrics'].items():
                print(f"Average ΔΨ ({period}, {year}): {delta_psi:.3f} MPa")

    metrics['kruskal'] = kw_results
    return metrics


###############################################################################

###############################################################################

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_all_1to1(trees_data, path_output=''):
    """
    Visualize Ψ_pd vs. Ψ_matric scatter plots for all trees with data in trees_data, using a 1:1 line
    to highlight hydraulic disconnection. No statistical tests are performed.

    Parameters:
    trees_data (dict): Dictionary with 'PSY_matric', 'PSY_predawn', 'tree', and 'year' for each tree-year.
    path_output (str): Path to save output plots (default '').

    Returns:
    None
    """
    # Define dry periods based on rainfall data
    dry_periods = {
        '2021': [('2021-07-13', '2021-08-15', 5.6)],
        '2022': [('2022-07-30', '2022-08-20', 2.4)]  # Updated dry period for 2022
    }

    # Collect all unique tree-year pairs from trees_data with valid data
    valid_tree_years = []
    for data in trees_data.values():
        if all(k in data for k in ['tree', 'year', 'PSY_matric', 'PSY_predawn']):
            psy_matric_df = data.get('PSY_matric')
            psy_predawn_series = data.get('PSY_predawn')
            if psy_matric_df is not None and not psy_matric_df.empty and psy_predawn_series is not None and not psy_predawn_series.empty:
                tree_year_key = f"{data['tree']}-{data['year']}"
                if tree_year_key not in ['DF03-2022', 'DF49-2021', 'ES42-2022', 'ES01-2022', 'ES50-2022']:
                    valid_tree_years.append((data['tree'], data['year']))

    if not valid_tree_years:
        print("No valid tree data found in trees_data. Skipping.")
        return

    # Define order for sorting
    order_key = {
        ('DF27', '2021'): 1,
        ('ES50', '2021'): 2,
        ('DF49', '2022'): 3,
        ('ES48', '2022'): 4,
        ('DF27', '2022'): 5,
        ('ES51', '2021'): 6,
        ('DF21', '2022'): 7,
    }

    # Sort valid_tree_years
    valid_tree_years = sorted(valid_tree_years, key=lambda x: order_key.get(x, 100))

    n_plots = len(valid_tree_years)
    if n_plots == 0:
        print("No plots to generate.")
        return

    # Determine grid size (e.g., 2x2 for 4, 3x2 for 5-6, etc.)
    n_cols = min(2, int(np.ceil(np.sqrt(n_plots))))
    n_rows = int(np.ceil(n_plots / n_cols))

    # Create titles with labels
    subplot_titles = []
    for tree, year in valid_tree_years:
        label = 'a)' if tree == 'DF27' and year == '2021' else \
                'b)' if tree == 'ES50' and year == '2021' else \
                'c)' if tree == 'DF49' and year == '2022' else \
                'd)' if tree == 'ES48' and year == '2022' else \
                'e)' if tree == 'DF27' and year == '2022' else \
                'f)' if tree == 'ES51' and year == '2021' else \
                'g)' if tree == 'DF21' and year == '2022' else ''
        subplot_titles.append(f'{label} {tree} ({year})')

    # Create subplot grid with titles
    fig_grid = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=subplot_titles, horizontal_spacing=0.15, vertical_spacing=0.15)

    plot_idx = 0
    for tree, year in valid_tree_years:
        # Find data for this tree-year
        tree_data_list = [data for data in trees_data.values() if data['tree'] == tree and data['year'] == year]
        if not tree_data_list:
            print(f"No data for {tree} ({year}). Skipping this tree-year in plot.")
            continue
        tree_data = tree_data_list[0]  # Take first match

        psy_matric_df = tree_data.get('PSY_matric')
        psy_predawn_series = tree_data.get('PSY_predawn')

        if psy_matric_df is None or psy_matric_df.empty or psy_predawn_series is None or psy_predawn_series.empty:
            print(f"Skipping {tree} ({year}): Missing or empty PSY_matric or PSY_predawn.")
            continue

        # Nighttime filter (10 PM to 7 AM)
        nighttime_filter = (psy_matric_df.index.hour >= 22) | (psy_matric_df.index.hour <= 7)
        psy_matric_night = psy_matric_df[nighttime_filter][['PSY_matric']].copy()

        # Align Ψ_pd to daily values
        psy_predawn_daily = psy_predawn_series.resample('D').mean()
        psy_matric_night['Ψ_pd'] = psy_matric_night.index.map(lambda x: psy_predawn_daily.get(pd.Timestamp(x.date()), np.nan))

        # Calculate ΔΨ and assign periods
        psy_matric_night = psy_matric_night.dropna(subset=['PSY_matric', 'Ψ_pd'])
        psy_matric_night['ΔΨ'] = psy_matric_night['Ψ_pd'] - psy_matric_night['PSY_matric']
        periods = dry_periods.get(year, [])
        if not periods:
            print(f"No dry periods defined for {year}. Skipping period assignment for {tree} ({year}).")
            continue
        start_year = pd.Timestamp(f'{year}-01-01')
        end_year = pd.Timestamp(f'{year}-12-31')
        bins = [start_year]
        for start, end, _ in periods:
            bins.append(pd.to_datetime(start))
            bins.append(pd.to_datetime(end))
        bins.append(end_year + pd.Timedelta(days=1))
        psy_matric_night['period'] = pd.cut(psy_matric_night.index, bins=bins, labels=['Pre-Dry', 'Dry', 'Post-Dry'], right=False)

        # Compute daily stats and count unique days
        daily_stats = psy_matric_night.groupby(psy_matric_night.index.date).agg({
            'PSY_matric': 'mean',
            'Ψ_pd': 'mean',
            'period': 'first'
        }).reset_index()
        daily_stats['date'] = pd.to_datetime(daily_stats['index'])
        days_with_data = len(daily_stats['date'].unique())
        print(f"Total number of days with data for {tree} ({year}): {days_with_data}")

        # Determine subplot position
        row = (plot_idx // n_cols) + 1
        col = (plot_idx % n_cols) + 1

        # Add scatter plot for this tree-year
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = daily_stats[daily_stats['period'] == period]
            if not period_data.empty:
                fig_grid.add_trace(go.Scatter(
                    x=period_data['PSY_matric'], y=period_data['Ψ_pd'], mode='markers',
                    name=f'{period}', marker=dict(color={'Pre-Dry': 'blue', 'Dry': '#FFA500', 'Post-Dry': 'green'}[period]),
                    legendgroup=period, showlegend=(plot_idx == 0)  # Show legend only in first subplot
                ), row=row, col=col)

        # Add 1:1 line to subplot
        lims = [-4, 0]  # Adjust based on your data range
        fig_grid.add_trace(go.Scatter(x=lims, y=lims, mode='lines', line=dict(dash='dash', color='black'), name='1:1 Line',
                                      showlegend=(plot_idx == 0)), row=row, col=col)

        plot_idx += 1

    # Update layout
    fig_grid.update_layout(
        height=300 * n_rows, width=400 * n_cols,
        showlegend=True,
        legend=dict(orientation="h", x=0.5, y=-0.1, xanchor="center", yanchor="top")
    )
    for row in range(1, n_rows + 1):
        for col in range(1, n_cols + 1):
            fig_grid.update_xaxes(title_text="Ψ soil (MPa)", row=row, col=col, showline=True)
            fig_grid.update_yaxes(title_text="Ψ pd (MPa)", row=row, col=col, showline=True)

    # Display and save
    fig_grid.show()
    if path_output:
        fig_grid.write_image(path_output + 'all_1to1_plots.png', scale=5)
        fig_grid.write_html(path_output + 'all_1to1_plots.html', include_plotlyjs='cdn')
    return fig_grid