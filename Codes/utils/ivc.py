import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import plotly.graph_objects as go

def weibull_func(x, r_min, d, b):
    # Weibull function from literature: Rp = R_min * exp(((-x)/d)^b)
    return r_min * np.exp(((-x / d) ** b))

def weibull_cdf(x, d, b):
    # Weibull CDF for HCL: HCL(%) = (1 - exp(-((-x)/d)^b)) * 100
    return (1 - np.exp(-((-x / d) ** b))) * 100

def calculate_resistance_and_plot(trees_data, potential_type='matric', sf='incomplete'):
    sf_threshold = 0.1
    results = []
    
    # Define dry periods with precipitation amounts (precipitation not used for coloring)
    dry_periods = {
        '2021': [
            ('2021-07-13', '2021-08-15', 5.6),  # Dry: 33 days, 5.6 mm
            ('2021-09-19', '2021-10-21', 5.6),  # Dry: 32 days, 5.6 mm
        ],
        '2022': [
            ('2022-07-05', '2022-07-21', 2.4),  # Dry: 16 days, 2.4 mm
            ('2022-07-30', '2022-08-20', 0.4),  # Dry: 21 days, 0.4 mm
            ('2022-09-30', '2022-10-19', 0.2),  # Dry: 19 days, 0.2 mm
        ]
    }
    
    # Define colors
    dry_color = 'rgb(255, 147, 0)'  # Medium orange for dry periods
    rain_color = 'rgb(51, 153, 255)'  # Medium blue for rain periods
    
    for tree_id, data in trees_data.items():
        tree = data['tree']
        year = data['year']
        
        # Print the potential_type, sf data type, and tree name
        print(f"Processing tree: {tree}, Year: {year}, Potential Type: {potential_type}, SF Type: {sf}")
        
        # Check required data
        if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
            continue
        
        if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
            continue
        
        # Select PSYs based on potential_type
        if potential_type == 'matric':
            if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
                continue
            psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
        elif potential_type == 'predawn':
            if not ('PSY_predawn' in data and not pd.isna(data['PSY_predawn']).all()):
                continue
            if isinstance(data['PSY_predawn'], pd.Series):
                psy_s_df = pd.DataFrame(data['PSY_predawn'], columns=['PSYs'])
            else:
                psy_s_df = data['PSY_predawn'].rename(columns={'PSY_predawn': 'PSYs'})
        else:
            continue
        
        # Use PSY_cleaned for PSYx and replace PSY in SF_W_SM_PSY
        sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
        
        # Replace PSY column with PSY_cleaned
        psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
        sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
        sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
        # Compute SF based on the sf argument
        if 'SF' not in sf_w_sm_psy_df.columns:
            if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
                if sf == 'complete':
                    sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_complete']
                elif sf == 'incomplete':
                    sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
                else:
                    continue
            else:
                continue
        
        # Align data
        sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
        aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
        # Adjust PSYs to ensure it's never positive and greater than PSYx
        aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
        aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
        # Calculate resistance (Rp), adjusting units: MPa s kg^-1
        aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
        # Filter for daytime (9 AM to 9 PM) and exclude low VPD or rainy days
        daytime_filter = (aligned_df.index.hour >= 9) & (aligned_df.index.hour <= 21)
        aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
        daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
        valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
        if valid_data.empty:
            continue
        
        # Calculate the average number of valid data points per day
        valid_data['Day'] = valid_data.index.date
        points_per_day = valid_data.groupby('Day').size()
        avg_points_per_day = points_per_day.mean() if not points_per_day.empty else 0
        
        # Identify dry periods for the current year
        periods = dry_periods.get(year, [])
        
        # Initialize array to store whether each point is in a dry period
        is_dry = []
        for idx in valid_data.index:
            date = idx
            in_dry_period = False
            for start, end, _ in periods:
                start_date = pd.to_datetime(start)
                end_date = pd.to_datetime(end)
                if start_date <= date <= end_date:
                    in_dry_period = True
                    break
            is_dry.append('Dry' if in_dry_period else 'Rain')
        
        # Fit Weibull curve to the data using the literature form
        try:
            # Prepare data for fitting
            x_data = valid_data['PSYx'].values
            y_data = valid_data['Rp'].values
            
            # Scale Rp data to improve fitting (divide by 1000)
            scale_factor = 1000.0
            y_data_scaled = y_data / scale_factor
            
            # Print data ranges for diagnostics
            print(f"Tree {tree} (Year {year}): PSYx range: {min(x_data):.2f} to {max(x_data):.2f}, Rp range: {min(y_data):.2f} to {max(y_data):.2f}")
            
            # Define bounds and initial guesses
            observed_min_rp = max(min(y_data), 10)  # Ensure it's at least 10 in original units
            rmin_lower_bound = 10 / scale_factor  # 0.01
            rmin_upper_bound = 1000 / scale_factor  # 1.0
            rmin_initial = max(observed_min_rp / scale_factor, rmin_lower_bound * 1.1)  # Add a 10% buffer
            rmin_initial = min(rmin_initial, rmin_upper_bound * 0.9)  # Ensure below upper bound
            initial_guess = [rmin_initial, 0.5, 0.6]  # [Rmin, d, b]
            bounds = ([10 / scale_factor, 0.1, 0.5], [1000 / scale_factor, 10, 10])  # [Rmin, d, b]
            
            # Print initial guess for debugging
            print(f"Initial guess for {tree} (Year {year}): Rmin={initial_guess[0]:.4f}, d={initial_guess[1]:.4f}, b={initial_guess[2]:.4f}")
            
            # Fit the Weibull function on scaled data
            popt, _ = curve_fit(weibull_func, x_data, y_data_scaled, p0=initial_guess, bounds=bounds, maxfev=5000)
            r_min_fit_scaled, d_fit, b_fit = popt
            
            # Rescale Rmin back to original units
            r_min_fit = r_min_fit_scaled * scale_factor
            
            # Generate points for the fitted curve (in original units)
            x_fit = np.linspace(min(x_data), max(x_data), 100)
            y_fit = weibull_func(x_fit, r_min_fit_scaled, d_fit, b_fit) * scale_factor
            
            # Compute predicted Rp values for the original data points (in original units)
            y_pred = weibull_func(x_data, r_min_fit_scaled, d_fit, b_fit) * scale_factor
            
            # Calculate R-squared
            ss_tot = np.sum((y_data - np.mean(y_data))**2)
            ss_res = np.sum((y_data - y_pred)**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
            
            # Calculate MAPE
            epsilon = 1e-6  # Small constant to avoid division by zero
            mape = np.mean(np.abs((y_data - y_pred) / np.maximum(y_data, epsilon))) * 100
        except RuntimeError as e:
            print(f"Could not fit Weibull curve for tree {tree} in year {year}. Error: {str(e)}")
            print(f"PSYx range: {min(x_data):.2f} to {max(x_data):.2f}, Rp range: {min(y_data):.2f} to {max(y_data):.2f}")
            r_min_fit, d_fit, b_fit = np.nan, np.nan, np.nan
            x_fit, y_fit = [], []
            r_squared, mape = np.nan, np.nan
            continue
        
        # Create the Rp plot
        fig_rp = go.Figure()
        
        # Dry periods (orange)
        dry_mask = np.array(is_dry) == 'Dry'
        if dry_mask.any():
            fig_rp.add_trace(go.Scatter(
                x=valid_data['PSYx'][dry_mask],
                y=valid_data['Rp'][dry_mask],
                mode='markers',
                name='Dry',
                marker=dict(
                    size=8,
                    color=dry_color
                )
            ))
        
        # Rain periods (blue)
        rain_mask = np.array(is_dry) == 'Rain'
        if rain_mask.any():
            fig_rp.add_trace(go.Scatter(
                x=valid_data['PSYx'][rain_mask],
                y=valid_data['Rp'][rain_mask],
                mode='markers',
                name='Rain',
                marker=dict(
                    size=8,
                    color=rain_color
                )
            ))
        
        # Add Weibull fit trace
        if len(x_fit) > 0:
            fig_rp.add_trace(go.Scatter(
                x=x_fit,
                y=y_fit,
                mode='lines',
                name='Weibull Fit',
                line=dict(color='black', dash='dash')
            ))
        
        # Update layout for Rp plot
        fig_rp.update_layout(
            xaxis_title='Tree Water Potential (MPa)',
            yaxis_title='Plant Resistance (MPa s kg^-1)',
            legend=dict(
                x=1.02,
                y=1.0,
                xanchor='left',
                yanchor='top'
            ),
            margin=dict(r=50),
            title=f"Rp vs. PSYx for {tree} (Year {year})"
        )
        fig_rp.show()
        
        # Compute HCL for the actual Rp data
        valid_data['HCL_data(%)'] = [(1 - (r_min_fit / rp)) * 100 if rp > r_min_fit else np.nan for rp in valid_data['Rp']]
        
        # Compute HCL for the simulated curve at predefined PSYx points
        predefined_x = [-0.01, -1, -2, -3, -4, -5, -6, -7]
        rp_simulated = weibull_func(np.array(predefined_x), r_min_fit, d_fit, b_fit)
        hcl_simulated = [(1 - (r_min_fit / rp)) * 100 if rp > r_min_fit else np.nan for rp in rp_simulated]
        
        # Create the HCL plot
        fig_hcl = go.Figure()
        
        # Add scatter plot of HCL for actual data
        fig_hcl.add_trace(go.Scatter(
            x=valid_data['PSYx'],
            y=valid_data['HCL_data(%)'],
            mode='markers',
            name='HCL(%)',
            marker=dict(
                size=8,
                color='blue'
            )
        ))
        
        # Add simulated HCL line
        fig_hcl.add_trace(go.Scatter(
            x=predefined_x,
            y=hcl_simulated,
            mode='lines',
            name='Simulated HCL',
            line=dict(color='black', dash='dash')
        ))
        
        # Update layout for HCL plot
        fig_hcl.update_layout(
            xaxis_title='PSYx (MPa)',
            yaxis_title='HCL (%)',
            yaxis_range=[0, 100],  # Set y-axis range to 0-100%
            legend=dict(
                x=1.02,
                y=1.0,
                xanchor='left',
                yanchor='top'
            ),
            margin=dict(r=50),
            title=f"HCL for {tree}-{year}"
        )
        fig_hcl.show()
        
        # Store some basic results for verification
        result = {
            'Tree': tree,
            'Year': year,
            'Mean_Rp': valid_data['Rp'].mean(),
            'Min_Rp': valid_data['Rp'].min(),
            'Max_Rp': valid_data['Rp'].max(),
            'Potential_Type': potential_type,
            'SF_Type': sf,
            'Avg_Points_Per_Day': avg_points_per_day,
            'Weibull_Rmin': r_min_fit,
            'Weibull_d': d_fit,
            'Weibull_b': b_fit,
            'R_squared': r_squared,
            'MAPE': mape
        }
        results.append(result)
    
    results_df = pd.DataFrame(results)
    print(f"Results using {potential_type} potential and {sf} sap flow:")
    print(results_df)
    return results_df

def compare_potential_types(trees_data, sf='complete'):
    # Run analysis for matric potential
    print("Running analysis for matric potential...")
    matric_results = calculate_resistance_and_plot(trees_data, potential_type='matric', sf=sf)
    print("\nMatric Potential Fit Results:")
    print(matric_results)
    
    # Run analysis for predawn potential
    print("\nRunning analysis for predawn potential...")
    predawn_results = calculate_resistance_and_plot(trees_data, potential_type='predawn', sf=sf)
    print("\nPredawn Potential Fit Results:")
    print(predawn_results)
    
    # Print averages for comparison
    print("\nSummary of Fit Metrics:")
    print(f"Matric Potential - Average R-squared: {matric_results['R_squared'].mean():.4f}, Average MAPE: {matric_results['MAPE'].mean():.4f}%")
    print(f"Predawn Potential - Average R-squared: {predawn_results['R_squared'].mean():.4f}, Average MAPE: {predawn_results['MAPE'].mean():.4f}%")
    
    return matric_results, predawn_results

# Example usage:
# matric_results, predawn_results = compare_potential_types(trees_data, sf='complete')


# separate dry wet periods

def weibull_func(x, r_min, d, b):
    # Weibull function from literature: Rp = R_min * exp(((-x)/d)^b)
    return r_min * np.exp(((-x / d) ** b))

def calculate_resistance_dry_rain(trees_data, potential_type='matric', sf='incomplete'):
    sf_threshold = 0.1
    results = []
    
    # Define dry periods with precipitation amounts
    dry_periods = {
        '2021': [
            ('2021-07-13', '2021-08-15', 5.6),  # Dry: 33 days, 5.6 mm
            ('2021-09-19', '2021-10-21', 5.6),  # Dry: 32 days, 5.6 mm
        ],
        '2022': [
            ('2022-07-05', '2022-07-21', 2.4),  # Dry: 16 days, 2.4 mm
            ('2022-07-30', '2022-08-20', 0.4),  # Dry: 21 days, 0.4 mm
            ('2022-09-30', '2022-10-19', 0.2),  # Dry: 19 days, 0.2 mm
        ]
    }
    
    # Define colors for plotting
    dry_color = 'rgb(255, 147, 0)'  # Medium orange for dry periods
    rain_color = 'rgb(51, 153, 255)'  # Medium blue for rain periods
    
    for tree_id, data in trees_data.items():
        tree = data['tree']
        year = data['year']
        
        print(f"Processing tree: {tree}, Year: {year}, Potential Type: {potential_type}, SF Type: {sf}")
        
        # Check required data
        if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
            continue
        
        if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
            continue
        
        # Select PSYs based on potential_type
        if potential_type == 'matric':
            if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
                continue
            psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
        elif potential_type == 'predawn':
            if not ('PSY_predawn' in data and not pd.isna(data['PSY_predawn']).all()):
                continue
            if isinstance(data['PSY_predawn'], pd.Series):
                psy_s_df = pd.DataFrame(data['PSY_predawn'], columns=['PSYs'])
            else:
                psy_s_df = data['PSY_predawn'].rename(columns={'PSY_predawn': 'PSYs'})
        else:
            continue
        
        # Use PSY_cleaned for PSYx and replace PSY in SF_W_SM_PSY
        sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
        psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
        sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
        sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
        # Compute SF based on the sf argument
        if 'SF' not in sf_w_sm_psy_df.columns:
            if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
                if sf == 'complete':
                    sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_complete']
                elif sf == 'incomplete':
                    sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
                else:
                    continue
            else:
                continue
        
        # Align data
        sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
        aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
        # Adjust PSYs to ensure it's never positive and greater than PSYx
        aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
        aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
        # Calculate resistance (Rp), adjusting units: MPa s kg^-1
        aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
        # Filter for daytime (9 AM to 9 PM) and exclude low VPD or rainy days
        daytime_filter = (aligned_df.index.hour >= 9) & (aligned_df.index.hour <= 21)
        aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
        daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
        valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
        if valid_data.empty:
            continue
        
        # Calculate the average number of valid data points per day
        valid_data['Day'] = valid_data.index.date
        points_per_day = valid_data.groupby('Day').size()
        avg_points_per_day = points_per_day.mean() if not points_per_day.empty else 0
        
        # Identify dry periods for the current year
        periods = dry_periods.get(year, [])
        
        # Initialize array to store whether each point is in a dry period
        is_dry = []
        for idx in valid_data.index:
            date = idx
            in_dry_period = False
            for start, end, _ in periods:
                start_date = pd.to_datetime(start)
                end_date = pd.to_datetime(end)
                if start_date <= date <= end_date:
                    in_dry_period = True
                    break
            is_dry.append('Dry' if in_dry_period else 'Rain')
        
        # Split data into dry and rain periods
        valid_data['Period'] = is_dry
        dry_data = valid_data[valid_data['Period'] == 'Dry']
        rain_data = valid_data[valid_data['Period'] == 'Rain']
        
        # Process each period (Dry and Rain)
        for period, period_data in [('Dry', dry_data), ('Rain', rain_data)]:
            if period_data.empty:
                print(f"No data for {period} period for tree {tree} in year {year}. Skipping...")
                continue
            
            # Prepare data for fitting
            x_data = period_data['PSYx'].values
            y_data = period_data['Rp'].values
            
            # Skip if there are too few data points to fit
            if len(x_data) < 4:  # Need at least 4 points to fit 3 parameters
                print(f"Insufficient data points ({len(x_data)}) for {period} period for tree {tree} in year {year}. Skipping...")
                continue
            
            # Scale Rp data to improve fitting (divide by 1000)
            scale_factor = 1000.0
            y_data_scaled = y_data / scale_factor
            
            # Print data ranges for diagnostics
            print(f"Tree {tree} (Year {year}, {period} Period): PSYx range: {min(x_data):.2f} to {max(x_data):.2f}, Rp range: {min(y_data):.2f} to {max(y_data):.2f}")
            
            # Define bounds and initial guesses
            observed_min_rp = max(min(y_data), 10)  # Ensure it's at least 10 in original units
            rmin_lower_bound = 10 / scale_factor  # 0.01
            rmin_upper_bound = 1000 / scale_factor  # 1.0
            rmin_initial = max(observed_min_rp / scale_factor, rmin_lower_bound * 1.1)  # Add a 10% buffer
            rmin_initial = min(rmin_initial, rmin_upper_bound * 0.9)  # Ensure below upper bound
            initial_guess = [rmin_initial, 0.5, 0.6]  # [Rmin, d, b]
            bounds = ([10 / scale_factor, 0.1, 0.5], [1000 / scale_factor, 10, 10])  # [Rmin, d, b]
            
            # Print initial guess for debugging
            print(f"Initial guess for {tree} (Year {year}, {period} Period): Rmin={initial_guess[0]:.4f}, d={initial_guess[1]:.4f}, b={initial_guess[2]:.4f}")
            
            # Fit the Weibull function on scaled data
            try:
                popt, _ = curve_fit(weibull_func, x_data, y_data_scaled, p0=initial_guess, bounds=bounds, maxfev=5000)
                r_min_fit_scaled, d_fit, b_fit = popt
                
                # Rescale Rmin back to original units
                r_min_fit = r_min_fit_scaled * scale_factor
                
                # Generate points for the fitted curve (in original units)
                x_fit = np.linspace(min(x_data), max(x_data), 100)
                y_fit = weibull_func(x_fit, r_min_fit_scaled, d_fit, b_fit) * scale_factor
                
                # Compute predicted Rp values for the original data points (in original units)
                y_pred = weibull_func(x_data, r_min_fit_scaled, d_fit, b_fit) * scale_factor
                
                # Calculate R-squared
                ss_tot = np.sum((y_data - np.mean(y_data))**2)
                ss_res = np.sum((y_data - y_pred)**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
                
                # Calculate MAPE
                epsilon = 1e-6  # Small constant to avoid division by zero
                mape = np.mean(np.abs((y_data - y_pred) / np.maximum(y_data, epsilon))) * 100
            except RuntimeError as e:
                print(f"Could not fit Weibull curve for tree {tree} in year {year} ({period} Period). Error: {str(e)}")
                r_min_fit, d_fit, b_fit = np.nan, np.nan, np.nan
                x_fit, y_fit = [], []
                r_squared, mape = np.nan, np.nan
                continue
            
            # Create the Rp plot for this period
            fig_rp = go.Figure()
            
            # Plot the data points for this period
            if period == 'Dry':
                color = dry_color
            else:
                color = rain_color
                
            fig_rp.add_trace(go.Scatter(
                x=period_data['PSYx'],
                y=period_data['Rp'],
                mode='markers',
                name=period,
                marker=dict(
                    size=8,
                    color=color
                )
            ))
            
            # Add Weibull fit trace
            if len(x_fit) > 0:
                fig_rp.add_trace(go.Scatter(
                    x=x_fit,
                    y=y_fit,
                    mode='lines',
                    name='Weibull Fit',
                    line=dict(color='black', dash='dash')
                ))
            
            # Update layout for Rp plot
            fig_rp.update_layout(
                xaxis_title='Tree Water Potential (MPa)',
                yaxis_title='Plant Resistance (MPa s kg^-1)',
                legend=dict(
                    x=1.02,
                    y=1.0,
                    xanchor='left',
                    yanchor='top'
                ),
                margin=dict(r=50),
                title=f"Rp vs. PSYx for {tree} (Year {year}, {period} Period)"
            )
            fig_rp.show()
            
            # Compute HCL for the actual Rp data (for scatter points)
            period_data['HCL_data(%)'] = [(1 - (r_min_fit / rp)) * 100 if rp > r_min_fit else np.nan for rp in period_data['Rp']]
            
            # Compute HCL using the Weibull CDF for the simulated curve over a wider range
            predefined_x = np.linspace(0, -10, 100)  # Extended range to capture full S-shape
            hcl_simulated = weibull_cdf(predefined_x, d_fit, b_fit)
            
            # Create the HCL plot for this period
            fig_hcl = go.Figure()
            
            # Add scatter plot of HCL for actual data
            fig_hcl.add_trace(go.Scatter(
                x=period_data['PSYx'],
                y=period_data['HCL_data(%)'],
                mode='markers',
                name='HCL(%)',
                marker=dict(
                    size=8,
                    color=color
                )
            ))
            
            # Add simulated HCL line using the Weibull CDF
            fig_hcl.add_trace(go.Scatter(
                x=predefined_x,
                y=hcl_simulated,
                mode='lines',
                name='Simulated HCL (CDF)',
                line=dict(color='black', dash='dash')
            ))
            
            # Update layout for HCL plot
            fig_hcl.update_layout(
                xaxis_title='PSYx (MPa)',
                yaxis_title='HCL (%)',
                yaxis_range=[0, 100],  # Set y-axis range to 0-100%
                xaxis_range=[0, -10],  # Set x-axis range to match predefined_x
                legend=dict(
                    x=1.02,
                    y=1.0,
                    xanchor='left',
                    yanchor='top'
                ),
                margin=dict(r=50),
                title=f"HCL for {tree}-{year} ({period} Period)"
            )
            fig_hcl.show()
            
            # Store results for this period
            result = {
                'Tree': tree,
                'Year': year,
                'Period': period,
                'Mean_Rp': period_data['Rp'].mean(),
                'Min_Rp': period_data['Rp'].min(),
                'Max_Rp': period_data['Rp'].max(),
                'Potential_Type': potential_type,
                'SF_Type': sf,
                'Avg_Points_Per_Day': period_data.groupby('Day').size().mean(),
                'Weibull_Rmin': r_min_fit,
                'Weibull_d': d_fit,
                'Weibull_b': b_fit,
                'R_squared': r_squared,
                'MAPE': mape
            }
            results.append(result)
    
    results_df = pd.DataFrame(results)
    print(f"\nResults for {potential_type} potential and {sf} sap flow (Dry and Rain Periods):")
    print(results_df)
    return results_df

def compare_potential_types_dry_rain(trees_data, sf='complete'):
    # Run analysis for matric potential
    print("Running analysis for matric potential (Dry and Rain Periods)...")
    matric_results = calculate_resistance_dry_rain(trees_data, potential_type='matric', sf=sf)
    print("\nMatric Potential Fit Results (Dry and Rain Periods):")
    print(matric_results)
    
    # Run analysis for predawn potential
    print("\nRunning analysis for predawn potential (Dry and Rain Periods)...")
    predawn_results = calculate_resistance_dry_rain(trees_data, potential_type='predawn', sf=sf)
    print("\nPredawn Potential Fit Results (Dry and Rain Periods):")
    print(predawn_results)
    
    # Print averages for comparison
    print("\nSummary of Fit Metrics (Dry Periods):")
    matric_dry = matric_results[matric_results['Period'] == 'Dry']
    predawn_dry = predawn_results[predawn_results['Period'] == 'Dry']
    print(f"Matric Potential (Dry) - Average R-squared: {matric_dry['R_squared'].mean():.4f}, Average MAPE: {matric_dry['MAPE'].mean():.4f}%")
    print(f"Predawn Potential (Dry) - Average R-squared: {predawn_dry['R_squared'].mean():.4f}, Average MAPE: {predawn_dry['MAPE'].mean():.4f}%")
    
    print("\nSummary of Fit Metrics (Rain Periods):")
    matric_rain = matric_results[matric_results['Period'] == 'Rain']
    predawn_rain = predawn_results[predawn_results['Period'] == 'Rain']
    print(f"Matric Potential (Rain) - Average R-squared: {matric_rain['R_squared'].mean():.4f}, Average MAPE: {matric_rain['MAPE'].mean():.4f}%")
    print(f"Predawn Potential (Rain) - Average R-squared: {predawn_rain['R_squared'].mean():.4f}, Average MAPE: {predawn_rain['MAPE'].mean():.4f}%")
    
    return matric_results, predawn_results

# Example usage:
# matric_results, predawn_results = compare_potential_types_dry_rain(trees_data, sf='complete')
