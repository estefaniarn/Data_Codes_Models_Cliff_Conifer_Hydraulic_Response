import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def weibull_func(x, r_min, d, b):
    # Weibull function for Rp: Rp = R_min * exp(((-x)/d)^b)
    return r_min * np.exp(((-x / d) ** b))

def weibull_hcl(x, r_min, d, b):
    # HCL function: HCL(%) = 100 * (1 - R_min / Rp), where Rp = R_min * exp(((-x)/d)^b)
    rp = weibull_func(x, r_min, d, b)
    return 100 * (1 - r_min / rp)

def calculate_resistance_dry_rain(trees_data, potential_type='matric', sf='incomplete', dry_periods=None):
    sf_threshold = 0.5
    lumped_results = []
    period_results = []
    figures = []
    
    # Define colors for plotting periods
    period_colors = {
        'Pre-Dry': 'blue',
        'Dry': 'rgb(255, 147, 0)',  # Medium orange
        'Post-Dry': 'green'
    }
    
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
        else:
            continue
        
        # Use PSY_cleaned for PSYx and replace PSY in SF_W_SM_PSY
        sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
        psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
        sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
        sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
        # Compute SF
        if 'SF' not in sf_w_sm_psy_df.columns:
            if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
                sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
            else:
                continue
        
        # Align data
        sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
        aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
        # Adjust PSYs
        aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
        aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
        # Calculate resistance (Rp)
        aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
        # Filter for daytime (12 PM to 5 PM)
        daytime_filter = (aligned_df.index.hour >= 11) & (aligned_df.index.hour <= 18)
        aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
        daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
        valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
        if valid_data.empty:
            continue
        
        # Calculate average points per day
        valid_data['Day'] = valid_data.index.date
        points_per_day = valid_data.groupby('Day').size()
        avg_points_per_day = points_per_day.mean() if not points_per_day.empty else 0
        
        # Identify periods
        periods = dry_periods.get(str(year), [])
        period_dict = {}
        for start, end, _, label in periods:
            period_dict[label] = (pd.to_datetime(start), pd.to_datetime(end))
        
        dry_period = period_dict.get(f'D1_{year[-2:]}')
        
        is_period = []
        for idx in valid_data.index:
            date = idx
            if dry_period and dry_period[0] <= date <= dry_period[1]:
                is_period.append('Dry')
            elif date < (dry_period[0] if dry_period else pd.Timestamp.min):
                is_period.append('Pre-Dry')
            elif dry_period and date > dry_period[1]:
                is_period.append('Post-Dry')
            else:
                is_period.append('Other')
        
        valid_data['Period'] = is_period
        
        # Prepare data for overall fit
        x_data = valid_data['PSYx'].values
        y_data = valid_data['Rp'].values
        
        if len(x_data) < 3:
            print(f"Insufficient data points ({len(x_data)}) for tree {tree} in year {year}. Skipping...")
            continue
        
        # Scale Rp data
        scale_factor = 1000.0
        y_data_scaled = y_data / scale_factor
        
        print(f"Tree {tree} (Year {year}): PSYx range: {min(x_data):.2f} to {max(x_data):.2f}, Rp range: {min(y_data):.2f} to {max(y_data):.2f}")
        
        # Define bounds and initial guesses
        observed_min_rp = max(min(y_data), 10)
        rmin_lower_bound = 50 / scale_factor #127
        rmin_upper_bound = 10000 / scale_factor #10000
        d_lower_bound = 1.5
        d_upper_bound = 6.1
        b_lower_bound = 1 #2.051
        b_upper_bound = 10.1
        rmin_initial = max(observed_min_rp / scale_factor, rmin_lower_bound * 1.1)
        rmin_initial = min(rmin_initial, rmin_upper_bound * 0.9)
        d_initial = 3.5
        b_initial = 4.0
        bounds = ([rmin_lower_bound, d_lower_bound, b_lower_bound], [rmin_upper_bound, d_upper_bound, b_upper_bound])
        p0 = [rmin_initial, d_initial, b_initial]
        
        # Overall Weibull fit
        try:
            popt, _ = curve_fit(weibull_func, x_data, y_data_scaled, p0=p0, bounds=bounds, maxfev=10000)
            r_min_fit_scaled, d_fit, b_fit = popt
            r_min_fit = r_min_fit_scaled * scale_factor
            x_fit = np.linspace(min(x_data), max(x_data), 100)
            y_fit = weibull_func(x_fit, r_min_fit_scaled, d_fit, b_fit) * scale_factor
            y_pred = weibull_func(x_data, r_min_fit_scaled, d_fit, b_fit) * scale_factor
            ss_tot = np.sum((y_data - np.mean(y_data))**2)
            ss_res = np.sum((y_data - y_pred)**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
        except RuntimeError as e:
            print(f"Could not fit Weibull curve for tree {tree} in year {year}. Error: {str(e)}")
            r_min_fit, d_fit, b_fit = np.nan, np.nan, np.nan
            x_fit, y_fit = [], []
            r_squared = np.nan
            continue
        
        # Compute P50 and P88 for overall fit
        p50_fit = -d_fit * (np.log(2) ** (1 / b_fit)) if not np.isnan(d_fit) and not np.isnan(b_fit) else np.nan
        p88_fit = -d_fit * ((np.log(1 / (1 - 0.88))) ** (1 / b_fit)) if not np.isnan(d_fit) and not np.isnan(b_fit) else np.nan
        
        # Create Resistance figure
        fig_resistance = go.Figure()
        
        # Rp Plot
        for period, color in period_colors.items():
            period_data = valid_data[valid_data['Period'] == period]
            if not period_data.empty:
                fig_resistance.add_trace(go.Scatter(
                    x=period_data['PSYx'],
                    y=period_data['Rp'],
                    mode='markers',
                    name=f'{period}',
                    marker=dict(size=8, color=color),
                    legendgroup=period,
                    showlegend=True
                ))
        
        if len(x_fit) > 0:
            fig_resistance.add_trace(go.Scatter(
                x=x_fit,
                y=y_fit,
                mode='lines',
                name='Weibull Fit',
                line=dict(color='black', dash='dash'),
                legendgroup='Fit',
                showlegend=True
            ))
        
        # Update layout for Resistance plot
        fig_resistance.update_layout(
            height=400,
            width=600,
            showlegend=True,
            legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
            margin=dict(r=50, t=50, b=50, l=50),
            xaxis_title="Tree Water Potential (MPa)",
            yaxis_title="Plant Resistance (MPa s kg^-1)",
            xaxis_range=[-5, 0],
            #yaxis_range=[0, 40000] #60000
        )
        
        fig_resistance.show()
        
        """
        # Commented out: HCL figure
        fig_hcl = go.Figure()
        
        # Compute HCL
        if not np.isnan(r_min_fit):
            valid_data['HCL_data(%)'] = [100 * (1 - r_min_fit/rp) if rp > 0 else np.nan for rp in valid_data['Rp']]
            valid_data['HCL_data(%)'] = np.clip(valid_data['HCL_data(%)'], 0, 100)
            print(f"Debug: HCL_data(%) for {tree} - Min: {valid_data['HCL_data(%)'].min()}, Max: {valid_data['HCL_data(%)'].max()}")
        else:
            print(f"Skipping HCL calculation for {tree} in year {year} due to fitting failure.")
            valid_data['HCL_data(%)'] = np.nan
        
        # HCL Plot
        for period, color in period_colors.items():
            period_data = valid_data[valid_data['Period'] == period]
            if not period_data.empty and 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all():
                fig_hcl.add_trace(go.Scatter(
                    x=period_data['PSYx'],
                    y=period_data['HCL_data(%)'],
                    mode='markers',
                    name=f'{period} HCL',
                    marker=dict(size=8, color=color),
                    legendgroup=period,
                    showlegend=True
                ))
        
        if not np.isnan(r_min_fit) and not np.isnan(d_fit) and not np.isnan(b_fit):
            predefined_x = np.linspace(0, -10, 100)
            hcl_fit = weibull_hcl(predefined_x, r_min_fit, d_fit, b_fit)
            fig_hcl.add_trace(go.Scatter(
                x=predefined_x,
                y=hcl_fit,
                mode='lines',
                name='HCL Fit',
                line=dict(color='black', dash='dash'),
                legendgroup='Fit',
                showlegend=True
            ))
        
        if not np.isnan(p50_fit):
            fig_hcl.add_shape(
                type="line",
                x0=p50_fit,
                x1=p50_fit,
                y0=0,
                y1=100,
                line=dict(color="red", width=2, dash="dash"),
                name="P50"
            )
        
        if not np.isnan(p88_fit):
            fig_hcl.add_shape(
                type="line",
                x0=p88_fit,
                x1=p88_fit,
                y0=0,
                y1=100,
                line=dict(color="purple", width=2, dash="dash"),
                name="P88"
            )
        
        # Update layout for HCL plot
        fig_hcl.update_layout(
            height=400,
            width=600,
            showlegend=True,
            legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
            margin=dict(r=50, t=50, b=50, l=50),
            xaxis_title="PSYx (MPa)",
            xaxis_range=[-10, 0],
            yaxis_title="HCL (%)",
            yaxis_range=[0, 100]
        )
        
        # fig_hcl.show()
        """
        
        figures.append((fig_resistance, tree, year)) # Only append Resistance figure
        
        # Store lumped results
        lumped_result = {
            'Tree': tree,
            'Year': year,
            'Mean_Rp': valid_data['Rp'].mean(),
            'Min_Rp': valid_data['Rp'].min(),
            'Max_Rp': valid_data['Rp'].max(),
            'Max_Rp_Day': valid_data['Rp'].idxmax().date() if not valid_data['Rp'].empty else np.nan,
            'Mean_HCL': valid_data['HCL_data(%)'].mean() if 'HCL_data(%)' in valid_data.columns and not valid_data['HCL_data(%)'].isna().all() else np.nan,
            'Potential_Type': potential_type,
            'SF_Type': sf,
            'Avg_Points_Per_Day': avg_points_per_day,
            'Weibull_Rmin': r_min_fit,
            'Weibull_d': d_fit,
            'Weibull_b': b_fit,
            'P50': p50_fit,
            'P88': p88_fit,
            'R_squared': r_squared
        }
        lumped_results.append(lumped_result)
        
        # Per-period Weibull fits and results
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = valid_data[valid_data['Period'] == period]
            if period_data.empty:
                continue
            
            # Compute period-specific Weibull fit
            x_period = period_data['PSYx'].values
            y_period = period_data['Rp'].values
            r_min_period, d_period, b_period, p50_period, p88_period, r_squared_period = np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            
            if len(x_period) >= 3:
                y_period_scaled = y_period / scale_factor
                try:
                    popt_period, _ = curve_fit(weibull_func, x_period, y_period_scaled, p0=p0, bounds=bounds, maxfev=10000)
                    r_min_period_scaled, d_period, b_period = popt_period
                    r_min_period = r_min_period_scaled * scale_factor
                    y_pred_period = weibull_func(x_period, r_min_period_scaled, d_period, b_period) * scale_factor
                    ss_tot_period = np.sum((y_period - np.mean(y_period))**2)
                    ss_res_period = np.sum((y_period - y_pred_period)**2)
                    r_squared_period = 1 - (ss_res_period / ss_tot_period) if ss_tot_period != 0 else np.nan
                    p50_period = -d_period * (np.log(2) ** (1 / b_period)) if not np.isnan(d_period) and not np.isnan(b_period) else np.nan
                    p88_period = -d_period * ((np.log(1 / (1 - 0.88))) ** (1 / b_period)) if not np.isnan(d_period) and not np.isnan(b_period) else np.nan
                except RuntimeError as e:
                    print(f"Could not fit Weibull curve for tree {tree} in year {year}, period {period}. Error: {str(e)}")
            
            mean_hcl = period_data['HCL_data(%)'].mean() if 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all() else np.nan
            
            result = {
                'Tree': tree,
                'Year': year,
                'Period': period,
                'Mean_Rp': period_data['Rp'].mean(),
                'Min_Rp': period_data['Rp'].min(),
                'Max_Rp': period_data['Rp'].max(),
                'Max_Rp_Day': period_data['Rp'].idxmax().date() if not period_data['Rp'].empty else np.nan,
                'Mean_HCL': mean_hcl,
                'Potential_Type': potential_type,
                'SF_Type': sf,
                'Avg_Points_Per_Day': period_data.groupby('Day').size().mean() if not period_data.empty else np.nan,
                'Weibull_Rmin': r_min_period,
                'Weibull_d': d_period,
                'Weibull_b': b_period,
                'P50': p50_period,
                'P88': p88_period,
                'R_squared': r_squared_period
            }
            period_results.append(result)
    
    lumped_results_df = pd.DataFrame(lumped_results)
    period_results_df = pd.DataFrame(period_results)
    
    print(f"\nLumped Results for {potential_type} potential and {sf} sap flow:")
    print(lumped_results_df)
    print(f"\nPeriod Results for {potential_type} potential and {sf} sap flow:")
    print(period_results_df)
    
    # Export lumped results for later plotting
    lumped_results_df.to_csv('lumped_weibull_fits.csv', index=False)
    
    return lumped_results_df, period_results_df, figures

# import pandas as pd
# import numpy as np
# from scipy.optimize import curve_fit
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots


# def weibull_func(x, r_min, d, b):
#     # Weibull function for Rp: Rp = R_min * exp(((-x)/d)^b)
#     return r_min * np.exp(((-x / d) ** b))

# def weibull_hcl(x, r_min, d, b):
#     # HCL function: HCL(%) = 100 * (1 - R_min / Rp), where Rp = R_min * exp(((-x)/d)^b)
#     rp = weibull_func(x, r_min, d, b)
#     return 100 * (1 - r_min / rp)

# def calculate_resistance_dry_rain(trees_data, potential_type='matric', sf='incomplete', dry_periods=None):
#     sf_threshold = 0.5
#     results = []
#     figures = []
    
#     # Define colors for plotting periods
#     period_colors = {
#         'Pre-Dry': 'blue',
#         'Dry': 'rgb(255, 147, 0)',  # Medium orange
#         'Post-Dry': 'green'
#     }
    
#     for tree_id, data in trees_data.items():
#         tree = data['tree']
#         year = data['year']
        
#         print(f"Processing tree: {tree}, Year: {year}, Potential Type: {potential_type}, SF Type: {sf}")
        
#         # Check required data
#         if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
#             continue
        
#         if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
#             continue
        
#         # Select PSYs based on potential_type
#         if potential_type == 'matric':
#             if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
#                 continue
#             psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
#         else:
#             continue
        
#         # Use PSY_cleaned for PSYx and replace PSY in SF_W_SM_PSY
#         sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
#         psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
#         sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
#         sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
#         # Compute SF
#         if 'SF' not in sf_w_sm_psy_df.columns:
#             if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
#                 sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
#             else:
#                 continue
        
#         # Align data
#         sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
#         aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
#         # Adjust PSYs
#         aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
#         aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
#         # Calculate resistance (Rp)
#         aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
#         # Filter for daytime (12 PM to 5 PM)
#         daytime_filter = (aligned_df.index.hour >= 11) & (aligned_df.index.hour <= 18) #12-17
#         aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
#         daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
#         valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
#         if valid_data.empty:
#             continue
        
#         # Calculate average points per day
#         valid_data['Day'] = valid_data.index.date
#         points_per_day = valid_data.groupby('Day').size()
#         avg_points_per_day = points_per_day.mean() if not points_per_day.empty else 0
        
#         # Identify periods
#         periods = dry_periods.get(str(year), [])
#         period_dict = {}
#         for start, end, _, label in periods:
#             period_dict[label] = (pd.to_datetime(start), pd.to_datetime(end))
        
#         dry_period = period_dict.get(f'D1_{year[-2:]}')
        
#         is_period = []
#         for idx in valid_data.index:
#             date = idx
#             if dry_period and dry_period[0] <= date <= dry_period[1]:
#                 is_period.append('Dry')
#             elif date < (dry_period[0] if dry_period else pd.Timestamp.min):
#                 is_period.append('Pre-Dry')
#             elif dry_period and date > dry_period[1]:
#                 is_period.append('Post-Dry')
#             else:
#                 is_period.append('Other')
        
#         valid_data['Period'] = is_period
        
#         # Prepare data for fitting
#         x_data = valid_data['PSYx'].values
#         y_data = valid_data['Rp'].values
        
#         if len(x_data) < 3:
#             print(f"Insufficient data points ({len(x_data)}) for tree {tree} in year {year}. Skipping...")
#             continue
        
#         # Scale Rp data
#         scale_factor = 1000.0
#         y_data_scaled = y_data / scale_factor
        
#         print(f"Tree {tree} (Year {year}): PSYx range: {min(x_data):.2f} to {max(x_data):.2f}, Rp range: {min(y_data):.2f} to {max(y_data):.2f}")
        
#         # Define bounds and initial guesses
#         observed_min_rp = max(min(y_data), 10)
#         rmin_lower_bound = 127 / scale_factor
#         rmin_upper_bound = 10000 / scale_factor
#         d_lower_bound = 1.5
#         d_upper_bound = 6.1
#         b_lower_bound = 2.051
#         b_upper_bound = 10.1
#         rmin_initial = max(observed_min_rp / scale_factor, rmin_lower_bound * 1.1)
#         rmin_initial = min(rmin_initial, rmin_upper_bound * 0.9)
#         d_initial = 3.5
#         b_initial = 4.0
#         bounds = ([rmin_lower_bound, d_lower_bound, b_lower_bound], [rmin_upper_bound, d_upper_bound, b_upper_bound])
#         p0 = [rmin_initial, d_initial, b_initial]
        
#         # Fit Weibull function
#         try:
#             popt, _ = curve_fit(weibull_func, x_data, y_data_scaled, p0=p0, bounds=bounds, maxfev=10000)
#             r_min_fit_scaled, d_fit, b_fit = popt
#             r_min_fit = r_min_fit_scaled * scale_factor
#             x_fit = np.linspace(min(x_data), max(x_data), 100)
#             y_fit = weibull_func(x_fit, r_min_fit_scaled, d_fit, b_fit) * scale_factor
#             y_pred = weibull_func(x_data, r_min_fit_scaled, d_fit, b_fit) * scale_factor
#             ss_tot = np.sum((y_data - np.mean(y_data))**2)
#             ss_res = np.sum((y_data - y_pred)**2)
#             r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
#         except RuntimeError as e:
#             print(f"Could not fit Weibull curve for tree {tree} in year {year}. Error: {str(e)}")
#             r_min_fit, d_fit, b_fit = np.nan, np.nan, np.nan
#             x_fit, y_fit = [], []
#             r_squared = np.nan
#             continue
        
#         # Compute P50 and P88
#         p50_fit = -d_fit * (np.log(2) ** (1 / b_fit)) if not np.isnan(d_fit) and not np.isnan(b_fit) else np.nan
#         p88_fit = -d_fit * ((np.log(1 / (1 - 0.88))) ** (1 / b_fit)) if not np.isnan(d_fit) and not np.isnan(b_fit) else np.nan
        
#         # Create combined figure
#         fig_combined = make_subplots(
#             rows=2, cols=1,
#             subplot_titles=("Rp vs. PSYx", "HCL vs. PSYx"),
#             vertical_spacing=0.15
#         )
        
#         # Rp Plot
#         for period, color in period_colors.items():
#             period_data = valid_data[valid_data['Period'] == period]
#             if not period_data.empty:
#                 fig_combined.add_trace(go.Scatter(
#                     x=period_data['PSYx'],
#                     y=period_data['Rp'],
#                     mode='markers',
#                     name=f'{period}',
#                     marker=dict(size=8, color=color),
#                     legendgroup=period,
#                     showlegend=True
#                 ), row=1, col=1)
        
#         if len(x_fit) > 0:
#             fig_combined.add_trace(go.Scatter(
#                 x=x_fit,
#                 y=y_fit,
#                 mode='lines',
#                 name='Weibull Fit',
#                 line=dict(color='black', dash='dash'),
#                 legendgroup='Fit',
#                 showlegend=True
#             ), row=1, col=1)
        
#         # Compute HCL
#         if not np.isnan(r_min_fit):
#             valid_data['HCL_data(%)'] = [100 * (1 - r_min_fit/rp) if rp > 0 else np.nan for rp in valid_data['Rp']]
#             valid_data['HCL_data(%)'] = np.clip(valid_data['HCL_data(%)'], 0, 100)
#             print(f"Debug: HCL_data(%) for {tree} - Min: {valid_data['HCL_data(%)'].min()}, Max: {valid_data['HCL_data(%)'].max()}")
#         else:
#             print(f"Skipping HCL calculation for {tree} in year {year} due to fitting failure.")
#             valid_data['HCL_data(%)'] = np.nan
        
#         # Compute HCL fit
#         predefined_x = np.linspace(0, -10, 100)
#         if not np.isnan(r_min_fit) and not np.isnan(d_fit) and not np.isnan(b_fit):
#             hcl_fit = weibull_hcl(predefined_x, r_min_fit, d_fit, b_fit)
#         else:
#             hcl_fit = np.full_like(predefined_x, np.nan)
        
#         # HCL Plot
#         for period, color in period_colors.items():
#             period_data = valid_data[valid_data['Period'] == period]
#             if not period_data.empty and 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all():
#                 fig_combined.add_trace(go.Scatter(
#                     x=period_data['PSYx'],
#                     y=period_data['HCL_data(%)'],
#                     mode='markers',
#                     name=f'{period} HCL',
#                     marker=dict(size=8, color=color),
#                     legendgroup=period,
#                     showlegend=True
#                 ), row=2, col=1)
        
#         if len(predefined_x) > 0 and not np.isnan(r_min_fit):
#             fig_combined.add_trace(go.Scatter(
#                 x=predefined_x,
#                 y=hcl_fit,
#                 mode='lines',
#                 name='HCL Fit',
#                 line=dict(color='black', dash='dash'),
#                 legendgroup='Fit',
#                 showlegend=True
#             ), row=2, col=1)
        
#         if not np.isnan(p50_fit):
#             fig_combined.add_shape(
#                 type="line",
#                 x0=p50_fit,
#                 x1=p50_fit,
#                 y0=0,
#                 y1=100,
#                 line=dict(color="red", width=2, dash="dash"),
#                 name="P50",
#                 row=2, col=1
#             )
        
#         if not np.isnan(p88_fit):
#             fig_combined.add_shape(
#                 type="line",
#                 x0=p88_fit,
#                 x1=p88_fit,
#                 y0=0,
#                 y1=100,
#                 line=dict(color="purple", width=2, dash="dash"),
#                 name="P88",
#                 row=2, col=1
#             )
        
#         # Update layout
#         fig_combined.update_layout(
#             height=800,
#             width=600,
#             showlegend=True,
#             legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
#             margin=dict(r=50, t=100, b=50, l=50)
#         )
        
#         fig_combined.update_xaxes(title_text="Tree Water Potential (MPa)", row=1, col=1)
#         fig_combined.update_yaxes(title_text="Plant Resistance (MPa s kg^-1)", row=1, col=1)
#         fig_combined.update_xaxes(title_text="PSYx (MPa)", range=[-10, 0], row=2, col=1)
#         fig_combined.update_yaxes(title_text="HCL (%)", range=[0, 100], row=2, col=1)
        
#         fig_combined.show()
        
#         figures.append((fig_combined, tree, year))
        
#         # Store results
#         for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
#             period_data = valid_data[valid_data['Period'] == period]
#             if period_data.empty:
#                 continue
            
#             mean_hcl = period_data['HCL_data(%)'].mean() if 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all() else np.nan
            
#             if not period_data['Rp'].empty:
#                 max_rp_date = period_data['Rp'].idxmax()
#                 max_rp_day = max_rp_date.date() if pd.notna(max_rp_date) else np.nan
#             else:
#                 max_rp_day = np.nan
            
#             result = {
#                 'Tree': tree,
#                 'Year': year,
#                 'Period': period,
#                 'Mean_Rp': period_data['Rp'].mean(),
#                 'Min_Rp': period_data['Rp'].min(),
#                 'Max_Rp': period_data['Rp'].max(),
#                 'Max_Rp_Day': max_rp_day,
#                 'Mean_HCL': mean_hcl,
#                 'Potential_Type': potential_type,
#                 'SF_Type': sf,
#                 'Avg_Points_Per_Day': period_data.groupby('Day').size().mean(),
#                 'Weibull_Rmin': r_min_fit,
#                 'Weibull_d': d_fit,
#                 'Weibull_b': b_fit,
#                 'P50': p50_fit,
#                 'P88': p88_fit,
#                 'R_squared': r_squared
#             }
#             results.append(result)
    
#     results_df = pd.DataFrame(results)
#     print(f"\nResults for {potential_type} potential and {sf} sap flow (Pre-Dry, Dry, Post-Dry Periods):")
#     print(results_df)
#     return results_df, figures




###############################################################################
from scipy.ndimage import gaussian_filter
def plot_resistance_timeseries(trees_data, dry_periods, potential_type='matric', sf_threshold=0.1):
    fig = go.Figure()

    for tree_id, data in trees_data.items():
        tree = data['tree']
        year = data['year']

        # Check required data
        if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
            continue
        if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
            continue
        if potential_type == 'matric':
            if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
                continue
            psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
        else:
            continue

        # Prepare data
        sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
        psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
        sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
        sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        if 'SF_incomplete' in sf_w_sm_psy_df.columns:
            sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
        else:
            continue

        # Align and filter data
        sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
        aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
        aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)

        # Exclude low VPD or rainy days
        aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
        daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
        valid_data = aligned_df[daily_flags == False].dropna(subset=['Rp'])

        if valid_data.empty:
            continue

        # Assign periods
        periods = dry_periods.get(str(year), [])
        period_dict = {label: (pd.to_datetime(start), pd.to_datetime(end)) for start, end, _, label in periods}
        dry_period = period_dict.get(f'D1_{year[-2:]}')

        is_period = []
        for idx in valid_data.index:
            date = idx
            if dry_period and dry_period[0] <= date <= dry_period[1]:
                is_period.append('Dry')
            elif date < (dry_period[0] if dry_period else pd.Timestamp.min):
                is_period.append('Pre-Dry')
            elif dry_period and date > dry_period[1]:
                is_period.append('Post-Dry')
            else:
                is_period.append('Other')
        valid_data['Period'] = is_period

        # Smooth SF
        sf_array = valid_data['SF'].to_numpy()
        sf_smoothed = gaussian_filter(sf_array, sigma=0.5)
        valid_data['SF_smoothed'] = pd.Series(sf_smoothed, index=valid_data.index)
        valid_data['Rp_smoothed'] = ((valid_data['PSYs'] - valid_data['PSYx']) / valid_data['SF_smoothed']) * (3.6 * 1e6)

        # Determine peak sap flow time per day (±1h window)
        valid_data['DateOnly'] = valid_data.index.date
        peak_times = valid_data.loc[valid_data.groupby('DateOnly')['SF_smoothed'].idxmax()]
        peak_windows = {}
        for idx, row in peak_times.iterrows():
            peak_time = idx
            start_time = peak_time - pd.Timedelta(hours=1)
            end_time = peak_time + pd.Timedelta(hours=1)
            peak_windows[row['DateOnly']] = (start_time, end_time)

        # Filter data for ±1h windows
        windowed_data = pd.DataFrame()
        for date, (start, end) in peak_windows.items():
            day_data = valid_data[valid_data['DateOnly'] == date]
            window_data = day_data[(day_data.index >= start) & (day_data.index <= end)]
            windowed_data = pd.concat([windowed_data, window_data])

        if windowed_data.empty:
            continue

        # Plot resistance time series
        for period, color in {'Pre-Dry': 'blue', 'Dry': 'orange', 'Post-Dry': 'green'}.items():
            period_data = windowed_data[windowed_data['Period'] == period]
            if not period_data.empty:
                fig.add_trace(go.Scatter(
                    x=period_data.index, y=period_data['Rp_smoothed'],
                    mode='markers', name=f'{tree} {period}',
                    line=dict(color=color), marker=dict(size=6)
                ))

    # Update layout
    fig.update_layout(
        title='Smoothed Resistance (Rp) Time Series by Peak Sap Flow Window (±1h)',
        xaxis_title='Date',
        yaxis_title='Resistance (MPa s kg⁻¹)',
        height=600, width=1000,
        showlegend=True,
        legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top')
    )
    fig.show()
# def plot_resistance_timeseries(trees_data, dry_periods, potential_type='matric', sf_threshold=0.1):
#     # Initialize figure
#     fig = go.Figure()

#     for tree_id, data in trees_data.items():
#         tree = data['tree']
#         year = data['year']

#         # Check required data
#         if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
#             continue
#         if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
#             continue
#         if potential_type == 'matric':
#             if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
#                 continue
#             psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
#         else:
#             continue

#         # Prepare data
#         sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
#         psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
#         sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
#         sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
#         if 'SF_incomplete' in sf_w_sm_psy_df.columns:
#             sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
#         else:
#             continue

#         # Align and filter initial data
#         sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
#         aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
#         aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
#         aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
#         aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)

#         # Exclude low VPD or rainy days
#         aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
#         daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
#         valid_data = aligned_df[daily_flags == False].dropna(subset=['Rp'])

#         if valid_data.empty:
#             continue

#         # Assign periods
#         periods = dry_periods.get(str(year), [])
#         period_dict = {label: (pd.to_datetime(start), pd.to_datetime(end)) for start, end, _, label in periods}
#         d2_period = period_dict.get(f'D2_{year[-2:]}')
#         d3_period = period_dict.get(f'D3_{year[-2:]}')

#         is_period = []
#         for idx in valid_data.index:
#             date = idx
#             if d2_period and d2_period[0] <= date <= d2_period[1]:
#                 is_period.append('D2')
#             elif d3_period and d3_period[0] <= date <= d3_period[1]:
#                 is_period.append('D3')
#             elif date < (d2_period[0] if d2_period else pd.Timestamp.min):
#                 is_period.append('Pre-D2')
#             elif d2_period and d3_period and d2_period[1] < date < d3_period[0]:
#                 is_period.append('Post-D2')
#             else:
#                 is_period.append('Other')
#         valid_data['Period'] = is_period

#         # Determine peak sap flow time per day and create ±2h window
#         valid_data['DateOnly'] = valid_data.index.date
#         peak_times = valid_data.loc[valid_data.groupby('DateOnly')['SF'].idxmax()]
#         peak_windows = {}
#         for idx, row in peak_times.iterrows():
#             peak_time = idx
#             start_time = peak_time - pd.Timedelta(hours=2)
#             end_time = peak_time + pd.Timedelta(hours=2)
#             peak_windows[row['DateOnly']] = (start_time, end_time)

#         # Filter data for ±2h windows and calculate Rp
#         windowed_data = pd.DataFrame()
#         for date, (start, end) in peak_windows.items():
#             day_data = valid_data[valid_data['DateOnly'] == date]
#             window_data = day_data[(day_data.index >= start) & (day_data.index <= end)]
#             windowed_data = pd.concat([windowed_data, window_data])

#         if windowed_data.empty:
#             continue

#         # Plot resistance time series
#         for period, color in {'Pre-D2': 'blue', 'D2': 'orange', 'Post-D2': 'green', 'D3': 'yellow'}.items():
#             period_data = windowed_data[windowed_data['Period'] == period]
#             if not period_data.empty:
#                 fig.add_trace(go.Scatter(
#                     x=period_data.index, y=period_data['Rp'],
#                     mode='markers', name=f'{tree} {period}',
#                     line=dict(color=color), marker=dict(size=6)
#                 ))

#     # Update layout
#     fig.update_layout(
#         title='Resistance (Rp) Time Series by Peak Sap Flow Window (±2h)',
#         xaxis_title='Date',
#         yaxis_title='Resistance (MPa s kg⁻¹)',
#         height=600, width=1000,
#         showlegend=True,
#         legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top')
#     )
#     fig.show()

# import pandas as pd
# import numpy as np
# from scipy.optimize import curve_fit
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots

# def weibull_func(x, r_min, d, b):
#     # Weibull function for Rp: Rp = R_min * exp(((-x)/d)^b)
#     return r_min * np.exp(((-x / d) ** b))

# def weibull_cdf(x, d, b):
#     # Weibull CDF for HCL: HCL(%) = (1 - exp(-((-x)/d)^b)) * 100
#     return (1 - np.exp(-((-x / d) ** b))) * 100

# def calculate_resistance_dry_rain(trees_data, potential_type='matric', sf='incomplete'):
#     sf_threshold = 0.1
#     results = []
#     figures = []  # List to store (fig, tree, year) tuples for saving
    
#     dry_periods = {
#         '2021': [
#             ('2021-07-13', '2021-08-15', 5.6),
#             #('2021-09-19', '2021-10-21', 5.6),
#         ],
#         '2022': [
#             ('2022-07-30', '2022-08-20', 0.4), #2022-07-21
#             #('2022-07-30', '2022-08-20', 0.4),
#             #('2022-09-30', '2022-10-19', 0.2),
#         ]
#     }
    
#     # Define colors for plotting
#     dry_color = 'rgb(255, 147, 0)'  # Medium orange for dry periods
#     rain_color = 'rgb(51, 153, 255)'  # Medium blue for rain periods
    
#     for tree_id, data in trees_data.items():
#         tree = data['tree']
#         year = data['year']
        
#         print(f"Processing tree: {tree}, Year: {year}, Potential Type: {potential_type}, SF Type: {sf}")
        
#         # Check required data
#         if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
#             continue
        
#         if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
#             continue
        
#         # Select PSYs based on potential_type
#         if potential_type == 'matric':
#             if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
#                 continue
#             psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
#         elif potential_type == 'predawn':
#             if not ('PSY_predawn' in data and not pd.isna(data['PSY_predawn']).all()):
#                 continue
#             if isinstance(data['PSY_predawn'], pd.Series):
#                 psy_s_df = pd.DataFrame(data['PSY_predawn'], columns=['PSYs'])
#             else:
#                 psy_s_df = data['PSY_predawn'].rename(columns={'PSY_predawn': 'PSYs'})
#         else:
#             continue
        
#         # Use PSY_cleaned for PSYx and replace PSY in SF_W_SM_PSY
#         sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
#         psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
#         sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
#         sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
#         # Compute SF based on the sf argument
#         if 'SF' not in sf_w_sm_psy_df.columns:
#             if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
#                 if sf == 'complete':
#                     sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_complete']
#                 elif sf == 'incomplete':
#                     sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
#                 else:
#                     continue
#             else:
#                 continue
        
#         # Align data
#         sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
#         aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
#         # Adjust PSYs to ensure it's never positive and greater than PSYx
#         aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
#         aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
#         # Calculate resistance (Rp), adjusting units: MPa s kg^-1
#         aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
#         # Filter for daytime (9 AM to 9 PM) and exclude low VPD or rainy days
#         daytime_filter = (aligned_df.index.hour >= 9) & (aligned_df.index.hour <= 21)
#         aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
#         daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
#         valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
#         if valid_data.empty:
#             continue
        
#         # Calculate the average number of valid data points per day
#         valid_data['Day'] = valid_data.index.date
#         points_per_day = valid_data.groupby('Day').size()
#         avg_points_per_day = points_per_day.mean() if not points_per_day.empty else 0
        
#         # Identify dry periods for the current year
#         periods = dry_periods.get(year, [])
        
#         # Initialize array to store whether each point is in a dry period
#         is_dry = []
#         for idx in valid_data.index:
#             date = idx
#             in_dry_period = False
#             for start, end, _ in periods:
#                 start_date = pd.to_datetime(start)
#                 end_date = pd.to_datetime(end)
#                 if start_date <= date <= end_date:
#                     in_dry_period = True
#                     break
#             is_dry.append('Dry' if in_dry_period else 'Rain')
        
#         # Add period labels to the data
#         valid_data['Period'] = is_dry
        
#         # Prepare data for fitting (combine dry and rain periods)
#         x_data = valid_data['PSYx'].values
#         y_data = valid_data['Rp'].values
        
#         # Skip if there are too few data points to fit
#         if len(x_data) < 3:  # Need at least 3 points to fit Rmin, d, and b
#             print(f"Insufficient data points ({len(x_data)}) for tree {tree} in year {year}. Skipping...")
#             continue
        
#         # Scale Rp data to improve fitting (divide by 1000)
#         scale_factor = 1000.0
#         y_data_scaled = y_data / scale_factor
        
#         # Print data ranges for diagnostics
#         print(f"Tree {tree} (Year {year}): PSYx range: {min(x_data):.2f} to {max(x_data):.2f}, Rp range: {min(y_data):.2f} to {max(y_data):.2f}")
        
#         # Define bounds and initial guesses for Rmin, d, b
#         observed_min_rp = max(min(y_data), 10)  # Ensure it's at least 10 in original units
#         rmin_lower_bound = 10 / scale_factor
#         rmin_upper_bound = 5000 / scale_factor  # Allow high Rmin to capture high Rp values
#         d_lower_bound = 1  # d should be positive and reasonable
#         d_upper_bound = 10
#         b_lower_bound = 0.1  #0.1 b should be positive and reasonable
#         b_upper_bound = 5
#         rmin_initial = max(observed_min_rp / scale_factor, rmin_lower_bound * 1.1)
#         rmin_initial = min(rmin_initial, rmin_upper_bound * 0.9)
#         d_initial = 5.0  # 5Initial guess based on typical P50 around -4 to -5 MPa
#         b_initial = 3.5  # 2.5Initial guess based on typical Weibull shape
#         bounds = ([rmin_lower_bound, d_lower_bound, b_lower_bound], [rmin_upper_bound, d_upper_bound, b_upper_bound])
#         p0 = [rmin_initial, d_initial, b_initial]
        
#         # Fit the Weibull function, fitting Rmin, d, and b
#         try:
#             popt, _ = curve_fit(weibull_func, x_data, y_data_scaled, p0=p0, bounds=bounds, maxfev=10000)
#             r_min_fit_scaled, d_fit, b_fit = popt
            
#             # Rescale Rmin back to original units
#             r_min_fit = r_min_fit_scaled * scale_factor
            
#             # Generate points for the fitted curve (in original units)
#             x_fit = np.linspace(min(x_data), max(x_data), 100)
#             y_fit = weibull_func(x_fit, r_min_fit_scaled, d_fit, b_fit) * scale_factor
            
#             # Compute predicted Rp values for the original data points (in original units)
#             y_pred = weibull_func(x_data, r_min_fit_scaled, d_fit, b_fit) * scale_factor
            
#             # Calculate R-squared
#             ss_tot = np.sum((y_data - np.mean(y_data))**2)
#             ss_res = np.sum((y_data - y_pred)**2)
#             r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
#         except RuntimeError as e:
#             print(f"Could not fit Weibull curve for tree {tree} in year {year}. Error: {str(e)}")
#             r_min_fit, d_fit, b_fit = np.nan, np.nan, np.nan
#             x_fit, y_fit = [], []
#             r_squared = np.nan
#             continue
        
#         # Compute P50 and P88 for the fitted model
#         p50_fit = -d_fit * (np.log(2) ** (1 / b_fit))
#         p88_fit = -d_fit * ((np.log(1 / (1 - 0.88))) ** (1 / b_fit))
        
#         # Create a combined figure with subplots
#         fig_combined = make_subplots(
#             rows=2, cols=1,
#             #subplot_titles=("Rp vs. PSYx", "HCL vs. PSYx"),
#             vertical_spacing=0.15
#         )
        
#         # --- Rp Plot (Upper Panel) ---
#         dry_data = valid_data[valid_data['Period'] == 'Dry']
#         rain_data = valid_data[valid_data['Period'] == 'Rain']
        
#         if not dry_data.empty:
#             fig_combined.add_trace(go.Scatter(
#                 x=dry_data['PSYx'],
#                 y=dry_data['Rp'],
#                 mode='markers',
#                 name='Dry',
#                 marker=dict(size=8, color=dry_color),
#                 legendgroup='Dry',
#                 showlegend=True
#             ), row=1, col=1)
        
#         if not rain_data.empty:
#             fig_combined.add_trace(go.Scatter(
#                 x=rain_data['PSYx'],
#                 y=rain_data['Rp'],
#                 mode='markers',
#                 name='Rain',
#                 marker=dict(size=8, color=rain_color),
#                 legendgroup='Rain',
#                 showlegend=True
#             ), row=1, col=1)
        
#         if len(x_fit) > 0:
#             fig_combined.add_trace(go.Scatter(
#                 x=x_fit,
#                 y=y_fit,
#                 mode='lines',
#                 name='Weibull Fit',
#                 line=dict(color='black', dash='dash'),
#                 legendgroup='Fit',
#                 showlegend=True
#             ), row=1, col=1)
        
#         # Compute HCL as percentage resistance loss: (1 - Rmin / Rp) * 100
#         if not np.isnan(r_min_fit):
#             valid_data['HCL_data(%)'] = [(1 - (r_min_fit/rp)) * 100 if rp > 0 else np.nan for rp in valid_data['Rp']]
#             valid_data['HCL_data(%)'] = np.clip(valid_data['HCL_data(%)'], 0, 100)
#             print(f"Debug: HCL_data(%) for {tree} - Min: {valid_data['HCL_data(%)'].min()}, Max: {valid_data['HCL_data(%)'].max()}")
#         else:
#             print(f"Skipping HCL calculation for {tree} in year {year} due to fitting failure.")
#             valid_data['HCL_data(%)'] = np.nan
        
#         # Compute HCL using the Weibull CDF over a wider range
#         predefined_x = np.linspace(0, -10, 100)
#         if not np.isnan(d_fit) and not np.isnan(b_fit):
#             hcl_simulated = weibull_cdf(predefined_x, d_fit, b_fit)
#         else:
#             hcl_simulated = np.full_like(predefined_x, np.nan)
        
#         # --- HCL Plot (Lower Panel) ---
#         if not dry_data.empty and 'HCL_data(%)' in dry_data.columns and not dry_data['HCL_data(%)'].isna().all():
#             fig_combined.add_trace(go.Scatter(
#                 x=dry_data['PSYx'],
#                 y=dry_data['HCL_data(%)'],
#                 mode='markers',
#                 name='HCL (%) - Dry',
#                 marker=dict(size=8, color=dry_color),
#                 legendgroup='Dry',
#                 showlegend=False
#             ), row=2, col=1)
        
#         if not rain_data.empty and 'HCL_data(%)' in rain_data.columns and not rain_data['HCL_data(%)'].isna().all():
#             fig_combined.add_trace(go.Scatter(
#                 x=rain_data['PSYx'],
#                 y=rain_data['HCL_data(%)'],
#                 mode='markers',
#                 name='HCL (%) - Rain',
#                 marker=dict(size=8, color=rain_color),
#                 legendgroup='Rain',
#                 showlegend=False
#             ), row=2, col=1)
        
#         if not np.isnan(d_fit) and not np.isnan(b_fit):
#             fig_combined.add_trace(go.Scatter(
#                 x=predefined_x,
#                 y=hcl_simulated,
#                 mode='lines',
#                 name='Simulated HCL (CDF)',
#                 line=dict(color='black', dash='dash'),
#                 legendgroup='Fit',
#                 showlegend=False
#             ), row=2, col=1)
        
#         if not np.isnan(p50_fit):
#             fig_combined.add_shape(
#                 type="line",
#                 x0=p50_fit,
#                 x1=p50_fit,
#                 y0=0,
#                 y1=100,
#                 line=dict(color="red", width=2, dash="dash"),
#                 name="P50",
#                 row=2, col=1
#             )
        
#         if not np.isnan(p88_fit):
#             fig_combined.add_shape(
#                 type="line",
#                 x0=p88_fit,
#                 x1=p88_fit,
#                 y0=0,
#                 y1=100,
#                 line=dict(color="purple", width=2, dash="dash"),
#                 name="P88",
#                 row=2, col=1
#             )
        
#         # Update layout for the combined figure
#         fig_combined.update_layout(
#             height=800,
#             width=600,
#             showlegend=True,
#             legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
#             margin=dict(r=50, t=100, b=50, l=50)
#         )
        
#         # Update axes for each subplot
#         fig_combined.update_xaxes(title_text="Tree Water Potential (MPa)", row=1, col=1)
#         fig_combined.update_yaxes(title_text="Plant Resistance (MPa s kg^-1)", row=1, col=1)
#         fig_combined.update_xaxes(title_text="PSYx (MPa)", range=[0, -10], row=2, col=1)
#         fig_combined.update_yaxes(title_text="HCL (%)", range=[0, 100], row=2, col=1)
        
#         # Show the combined figure
#         fig_combined.show()
        
#         # Store the combined figure for saving
#         figures.append((fig_combined, tree, year))
        
#         # Store results (separate for dry and rain periods for reporting, but single fit)
#         for period in ['Dry', 'Rain']:
#             period_data = valid_data[valid_data['Period'] == period]
#             if period_data.empty:
#                 continue
            
#             mean_hcl = period_data['HCL_data(%)'].mean() if 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all() else np.nan
            
#             # Find the date of Max_Rp
#             if not period_data['Rp'].empty:
#                 max_rp_date = period_data['Rp'].idxmax()
#                 max_rp_day = max_rp_date.date() if pd.notna(max_rp_date) else np.nan
#             else:
#                 max_rp_day = np.nan
            
#             result = {
#                 'Tree': tree,
#                 'Year': year,
#                 'Period': period,
#                 'Mean_Rp': period_data['Rp'].mean(),
#                 'Min_Rp': period_data['Rp'].min(),
#                 'Max_Rp': period_data['Rp'].max(),
#                 'Max_Rp_Day': max_rp_day,
#                 'Mean_HCL': mean_hcl,
#                 'Potential_Type': potential_type,
#                 'SF_Type': sf,
#                 'Avg_Points_Per_Day': period_data.groupby('Day').size().mean(),
#                 'Weibull_Rmin': r_min_fit,
#                 'Weibull_d': d_fit,
#                 'Weibull_b': b_fit,
#                 'P50': p50_fit,
#                 'P88': p88_fit,
#                 'R_squared': r_squared
#             }
#             results.append(result)
    
#     results_df = pd.DataFrame(results)
#     print(f"\nResults for {potential_type} potential and {sf} sap flow (Dry and Rain Periods):")
#     #print(results_df)
#     return results_df, figures
# import pandas as pd


# def compare_potential_types_dry_rain(trees_data, sf='complete'):
#     # Run analysis for matric potential
#     print("Running analysis for matric potential (Dry and Rain Periods)...")
#     matric_results = calculate_resistance_dry_rain(trees_data, potential_type='matric', sf=sf)
#     print("\nMatric Potential Fit Results (Dry and Rain Periods):")
#     print(matric_results)
    
#     # Run analysis for predawn potential
#     print("\nRunning analysis for predawn potential (Dry and Rain Periods)...")
#     predawn_results = calculate_resistance_dry_rain(trees_data, potential_type='predawn', sf=sf)
#     print("\nPredawn Potential Fit Results (Dry and Rain Periods):")
#     print(predawn_results)
    
#     # Print averages for comparison
#     print("\nSummary of Fit Metrics (Dry Periods):")
#     matric_dry = matric_results[matric_results['Period'] == 'Dry']
#     predawn_dry = predawn_results[predawn_results['Period'] == 'Dry']
#     print(f"Matric Potential (Dry) - Average R-squared: {matric_dry['R_squared'].mean():.4f}")
#     print(f"Predawn Potential (Dry) - Average R-squared: {predawn_dry['R_squared'].mean():.4f}")
    
#     print("\nSummary of Fit Metrics (Rain Periods):")
#     matric_rain = matric_results[matric_results['Period'] == 'Rain']
#     predawn_rain = predawn_results[predawn_results['Period'] == 'Rain']
#     print(f"Matric Potential (Rain) - Average R-squared: {matric_rain['R_squared'].mean():.4f}")
#     print(f"Predawn Potential (Rain) - Average R-squared: {predawn_rain['R_squared'].mean():.4f}")
    
#     return matric_results, predawn_results

# # Example usage:
# # matric_results, predawn_results = compare_potential_types_dry_rain(trees_data, sf='complete')