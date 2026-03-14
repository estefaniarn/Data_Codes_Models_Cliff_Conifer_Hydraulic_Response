# import pandas as pd
# import numpy as np
# from scipy.optimize import curve_fit
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots

# # Initial R_max values for each period (order: ES51, ES50, ES42, ES01, ES48, DF27, DF03, DF21, DF49)
# R_max_pre = [0, 50000, 300000, 300000, 30000, 40000, 60000, 20000, 10500]  # 5000]
# R_max_dry = [600000, 60000, 300000, 300000, 0, 20000, 60000, 20000, 3000]  # 3000]
# R_max_post = [600000, 40000, 300000, 300000, 3000, 20000, 60000, 20000, 5000]  # 5000]

# R_min_all = [236.48, 8.56, 14.06, 183.76, 3.14, 89.61, 115.61, 13.83, 7.98]

# R_MIN_R_MAX_DATA = {
#     'ES51': {'R_min': R_min_all[0], 'R_max': R_max_pre[0]},
#     'ES50': {'R_min': R_min_all[1], 'R_max': R_max_pre[1]},
#     'ES42': {'R_min': R_min_all[2], 'R_max': R_max_pre[2]},
#     'ES01': {'R_min': R_min_all[3], 'R_max': R_max_pre[3]},
#     'ES48': {'R_min': R_min_all[4], 'R_max': R_max_pre[4]},
#     'DF27': {'R_min': R_min_all[5], 'R_max': R_max_pre[5]},
#     'DF03': {'R_min': R_min_all[6], 'R_max': R_max_pre[6]},
#     'DF21': {'R_min': R_min_all[7], 'R_max': R_max_pre[7]},
#     'DF49': {'R_min': R_min_all[8], 'R_max': R_max_pre[8]}
# }

# def weibull_func(x, d, b, R_min, R_max):
#     return R_min + (R_max - R_min) * (1 - np.exp(-((-x / d) ** b)))

# def weibull_function(psy, rmin, d, b):
#     return rmin * np.exp(((-psy / d) ** b))

# def weibull_cdf(psy, d, b):
#     return (1 - np.exp(-((-psy / d) ** b))) * 100

# def calculate_ivc_fits(trees_data, potential_type='matric', sf='incomplete', path_output=''):
#     sf_threshold = 0.1
#     results = []
#     figures = []
    
#     dry_periods = {
#         '2021': [('2021-07-20', '2021-08-16', 5.6)],
#         #'2021': [('2021-07-13', '2021-08-15', 5.6)],
#         '2022': [('2022-07-30', '2022-08-20', 0.4)],
#     }
    
#     period_colors = {
#         'Pre-Dry': 'rgb(51, 153, 255)',  # Blue
#         'Dry': 'rgb(255, 147, 0)',      # Orange
#         'Post-Dry': 'rgb(0, 153, 0)'     # Green
#     }
    
#     tree_order = ['ES51', 'ES50', 'ES42', 'ES01', 'ES48', 'DF27', 'DF03', 'DF21', 'DF49']
    
#     for tree_id, data in trees_data.items():
#         tree = data['tree']
#         year = data['year']
        
#         print(f"\nProcessing tree: {tree}, Year: {year}, Potential Type: {potential_type}, SF Type: {sf}")
        
#         if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
#             print(f"No PSY_cleaned data for {tree} in year {year}. Skipping...")
#             continue
        
#         if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
#             print(f"No SF_W_SM_PSY data for {tree} in year {year}. Skipping...")
#             continue
        
#         if potential_type == 'matric':
#             if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
#                 print(f"No PSY_matric data for {tree} in year {year}. Skipping...")
#                 continue
#             psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
#         elif potential_type == 'predawn':
#             if not ('PSY_predawn' in data and not pd.isna(data['PSY_predawn']).all()):
#                 print(f"No PSY_predawn data for {tree} in year {year}. Skipping...")
#                 continue
#             if isinstance(data['PSY_predawn'], pd.Series):
#                 psy_s_df = pd.DataFrame(data['PSY_predawn'], columns=['PSYs'])
#             else:
#                 psy_s_df = data['PSY_predawn'].rename(columns={'PSY_predawn': 'PSYs'})
#         else:
#             print(f"Invalid potential_type for {tree} in year {year}. Skipping...")
#             continue
        
#         sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
#         psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
#         sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
#         sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
#         if 'SF' not in sf_w_sm_psy_df.columns:
#             if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
#                 if sf == 'complete':
#                     sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_complete']
#                 elif sf == 'incomplete':
#                     sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
#                 else:
#                     print(f"Invalid SF type for {tree} in year {year}. Skipping...")
#                     continue
#             else:
#                 print(f"No SF data for {tree} in year {year}. Skipping...")
#                 continue
        
#         sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
#         aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
#         aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
#         aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
#         aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
#         daytime_filter = (aligned_df.index.hour >= 9) & (aligned_df.index.hour <= 21)
#         aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
#         daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
#         valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
#         if valid_data.empty:
#             print(f"No valid data after filtering for {tree} in year {year}. Skipping...")
#             continue
        
#         valid_data['Day'] = valid_data.index.date
#         periods = dry_periods.get(year, [])
#         period_labels = []
#         for idx in valid_data.index:
#             date = idx
#             in_dry_period = False
#             for start, end, _ in periods:
#                 start_date = pd.to_datetime(start)
#                 end_date = pd.to_datetime(end)
#                 if start_date <= date <= end_date:
#                     in_dry_period = True
#                     break
#             if in_dry_period:
#                 period_labels.append('Dry')
#             elif date < start_date if periods else True:
#                 period_labels.append('Pre-Dry')
#             else:
#                 period_labels.append('Post-Dry')
        
#         valid_data['Period'] = period_labels
        
#         # Initialize dictionaries for period-specific fits and R_max/R_min
#         period_fits = {}
#         period_rmax_rmin = {period: {'R_min': np.nan, 'R_max': np.nan, 'sw_area': np.nan} for period in ['Pre-Dry', 'Dry', 'Post-Dry']}
        
#         # Sensitivity analysis for R_max and R_min per period
#         tree_key = tree_id.split('-')[0]
#         tree_idx = tree_order.index(tree_key)
        
#         for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
#             period_data = valid_data[valid_data['Period'] == period]
#             if period_data.empty:
#                 continue
            
#             # Set initial R_max and R_min based on period
#             if period == 'Pre-Dry':
#                 initial_rmax = R_max_pre[tree_idx]
#                 initial_rmin = R_min_all[tree_idx]  # Base R_min from data
#             elif period == 'Dry':
#                 initial_rmax = R_max_dry[tree_idx]
#                 initial_rmin = R_min_all[tree_idx]
#             else:  # Post-Dry
#                 initial_rmax = R_max_post[tree_idx]
#                 initial_rmin = R_min_all[tree_idx]
            
#             best_rmax = initial_rmax
#             best_rmin = initial_rmin
#             best_r_squared = -np.inf
#             current_fits = {}
            
#             # Define ranges for sensitivity analysis
#             r_max_range = np.linspace(initial_rmax * 0.25, initial_rmax * 1.75, 5)  # ±50% of initial R_max
#             r_min_range = np.linspace(initial_rmin * 0.5, initial_rmin * 1.5, 5)    # ±50% of initial R_min
            
#             for r_max in r_max_range:
#                 for r_min in r_min_range:
#                     if r_max <= r_min:  # Ensure R_max > R_min
#                         continue
#                     period_rmax_rmin[period] = {'R_min': r_min, 'R_max': r_max, 'sw_area': np.nan}
                    
#                     x_data = period_data['PSYx'].values
#                     y_data = period_data['Rp'].values
                    
#                     if len(x_data) < 3:
#                         continue
                    
#                     d_initial = 4.0
#                     b_initial = 2.0
#                     bounds = ([1.0, 1.0], [4.0, 6.0])  # d (1 to 4), b (1 to 6)
#                     p0 = [d_initial, b_initial]
                    
#                     try:
#                         popt, _ = curve_fit(
#                             lambda x, d, b: weibull_func(x, d, b, r_min, r_max),
#                             x_data,
#                             y_data,
#                             p0=p0,
#                             bounds=bounds,
#                             maxfev=10000
#                         )
#                         d_fit, b_fit = popt
                        
#                         y_pred = weibull_func(x_data, d_fit, b_fit, r_min, r_max)
#                         ss_tot = np.sum((y_data - np.mean(y_data))**2)
#                         ss_res = np.sum((y_data - y_pred)**2)
#                         r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
                        
#                         current_fits[(r_min, r_max)] = {
#                             'd': d_fit,
#                             'b': b_fit,
#                             'r_squared': r_squared,
#                             'x_data': x_data,
#                             'y_data': y_data
#                         }
#                         if r_squared > best_r_squared:
#                             best_r_squared = r_squared
#                             best_rmax = r_max
#                             best_rmin = r_min
#                     except RuntimeError:
#                         continue
            
#             if current_fits:  # Only update if a fit was successful
#                 period_fits[period] = current_fits.get((best_rmin, best_rmax), {})
#                 period_rmax_rmin[period]['R_min'] = best_rmin
#                 period_rmax_rmin[period]['R_max'] = best_rmax
#                 print(f"Best R_max for {tree} ({period}): {best_rmax:.2f} MPa s kg^-1 (Initial R_max: {initial_rmax:.2f}), Best R_min: {best_rmin:.2f} MPa s kg^-1 (Initial R_min: {initial_rmin:.2f}, R-squared: {best_r_squared:.2f}, d: {period_fits[period].get('d', np.nan):.2f}, b: {period_fits[period].get('b', np.nan):.2f})")
#             else:
#                 print(f"No valid fit found for {tree} ({period}). Using initial values: R_min = {initial_rmin}, R_max = {initial_rmax}")
#                 period_rmax_rmin[period]['R_min'] = initial_rmin
#                 period_rmax_rmin[period]['R_max'] = initial_rmax
        
#         # Recalculate HCL for plotting
#         for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
#             period_data = valid_data[valid_data['Period'] == period]
#             if period_data.empty:
#                 continue
#             R_min = period_rmax_rmin[period]['R_min']
#             R_max = period_rmax_rmin[period]['R_max']
#             if not np.isnan(R_min) and not np.isnan(R_max) and R_max > R_min and np.isfinite(R_max):
#                 valid_data.loc[valid_data['Period'] == period, 'HCL_data(%)'] = ((period_data['Rp'] - R_min) / (R_max - R_min)) * 100
#                 valid_data['HCL_data(%)'] = np.clip(valid_data['HCL_data(%)'], 0, 100)
#                 print(f"Debug: Adjusted HCL_data(%) for {tree} ({period}) - Min: {valid_data[valid_data['Period'] == period]['HCL_data(%)'].min():.2f}, Max: {valid_data[valid_data['Period'] == period]['HCL_data(%)'].max():.2f}")
#             else:
#                 print(f"Skipping adjusted HCL calculation for {tree} ({period}) due to invalid R_min ({R_min}) or R_max ({R_max}).")
#                 valid_data.loc[valid_data['Period'] == period, 'HCL_data(%)'] = np.nan
        
#         # Create and save resistance plot
#         fig_resistance = go.Figure()
        
#         for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
#             period_data = valid_data[valid_data['Period'] == period]
#             if not period_data.empty:
#                 fig_resistance.add_trace(go.Scatter(
#                     x=period_data['PSYx'],
#                     y=period_data['Rp'],
#                     mode='markers',
#                     name=f'{tree} - {period} Data',
#                     marker=dict(size=8, color=period_colors[period]),
#                     legendgroup=period,
#                     showlegend=True
#                 ))
        
#         for period, fit in period_fits.items():
#             if fit:
#                 R_min = period_rmax_rmin[period]['R_min']
#                 R_max = period_rmax_rmin[period]['R_max']
#                 x_fit = np.linspace(min(fit['x_data']), max(fit['x_data']), 100) if len(fit['x_data']) > 0 else np.linspace(-10, 0, 100)
#                 y_fit = weibull_func(x_fit, fit['d'], fit['b'], R_min, R_max)
#                 fig_resistance.add_trace(go.Scatter(
#                     x=x_fit,
#                     y=y_fit,
#                     mode='lines',
#                     name=f'{tree} - Weibull Fit ({period})',
#                     line=dict(color=period_colors[period], dash='dash'),
#                     legendgroup=period,
#                     showlegend=True
#                 ))
        
#         fig_resistance.update_layout(
#             height=600,
#             width=800,
#             #title=f'Resistance vs. Water Potential for {tree} ({year})',
#             xaxis_title='Xylem Water Potential (MPa)',
#             yaxis_title='Plant Resistance (MPa s kg^-1)',
#             showlegend=True,
#             legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
#             margin=dict(r=50, t=100, b=50, l=50)
#         )
        
#         fig_resistance.show()
#         fig_resistance.write_image(f'{path_output}IVC_plots/resistance_{tree}_{year}.png', scale=5)
#         figures.append((fig_resistance, tree, year))
        
#         # Create and save HCL plot
#         fig_hcl = go.Figure()
        
#         for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
#             period_data = valid_data[valid_data['Period'] == period]
#             if not period_data.empty and 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all():
#                 fig_hcl.add_trace(go.Scatter(
#                     x=period_data['PSYx'],
#                     y=period_data['HCL_data(%)'],
#                     mode='markers',
#                     name=f'{tree} - HCL ({period}) Data',
#                     marker=dict(size=8, color=period_colors[period]),
#                     legendgroup=period,
#                     showlegend=True
#                 ))
        
#         predefined_x = np.linspace(0, -10, 100)
#         for period, fit in period_fits.items():
#             if fit:
#                 hcl_simulated = weibull_cdf(predefined_x, fit['d'], fit['b'])
#                 fig_hcl.add_trace(go.Scatter(
#                     x=predefined_x,
#                     y=hcl_simulated,
#                     mode='lines',
#                     name=f'{tree} - Simulated HCL ({period})',
#                     line=dict(color=period_colors[period], dash='dash'),
#                     legendgroup=period,
#                     showlegend=True
#                 ))
        
#         for period, fit in period_fits.items():
#             if fit and not np.isnan(fit['d']) and not np.isnan(fit['b']):
#                 p50_fit = -fit['d'] * (np.log(2) ** (1 / fit['b']))
#                 p88_fit = -fit['d'] * ((np.log(1 / (1 - 0.88))) ** (1 / fit['b']))
#                 if not np.isnan(p50_fit):
#                     fig_hcl.add_shape(
#                         type="line",
#                         x0=p50_fit,
#                         x1=p50_fit,
#                         y0=0,
#                         y1=100,
#                         line=dict(color=period_colors[period], width=2, dash='dot'),
#                         name=f"P50 ({period})",
#                     )
#                 if not np.isnan(p88_fit):
#                     fig_hcl.add_shape(
#                         type="line",
#                         x0=p88_fit,
#                         x1=p88_fit,
#                         y0=0,
#                         y1=100,
#                         line=dict(color=period_colors[period], width=1, dash='dashdot'),
#                         name=f"P88 ({period})",
#                     )
        
#         fig_hcl.update_layout(
#             height=600,
#             width=800,
#             #title=f'HCL vs. Water Potential for {tree} ({year})',
#             xaxis_title='Xylem Water Potential (MPa)',
#             yaxis_title='HCL (%)',
#             showlegend=True,
#             legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
#             margin=dict(r=50, t=100, b=50, l=50)
#         )
        
#         fig_hcl.show()
#         fig_hcl.write_image(f'{path_output}IVC_plots/hcl_{tree}_{year}.png', scale=5)
#         figures.append((fig_hcl, tree, year))
        
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
            
#             fit = period_fits.get(period, {'d': np.nan, 'b': np.nan, 'r_squared': np.nan})
#             p50_fit = -fit['d'] * (np.log(2) ** (1 / fit['b'])) if not np.isnan(fit['d']) and not np.isnan(fit['b']) else np.nan
#             p88_fit = -fit['d'] * ((np.log(1 / (1 - 0.88))) ** (1 / fit['b'])) if not np.isnan(fit['d']) and not np.isnan(fit['b']) else np.nan
#             R_min = period_rmax_rmin[period]['R_min']
#             R_max = period_rmax_rmin[period]['R_max']
#             R_50 = R_min + 0.5 * (R_max - R_min) if not np.isnan(R_min) and not np.isnan(R_max) and R_max > R_min else np.nan
#             R_88 = R_min + 0.88 * (R_max - R_min) if not np.isnan(R_min) and not np.isnan(R_max) and R_max > R_min else np.nan
            
#             if period == 'Pre-Dry':
#                 initial_rmax_used = R_max_pre[tree_idx]
#             elif period == 'Dry':
#                 initial_rmax_used = R_max_dry[tree_idx]
#             else:  # Post-Dry
#                 initial_rmax_used = R_max_post[tree_idx]
            
#             result = {
#                 'Tree': tree,
#                 'Year': year,
#                 'Period': period,
#                 'Mean_Rp': period_data['Rp'].mean() if not period_data['Rp'].empty else np.nan,
#                 'Max_Rp': period_data['Rp'].max() if not period_data['Rp'].empty else np.nan,
#                 'Max_Rp_Day': max_rp_day,
#                 'Mean_HCL': mean_hcl,
#                 'Potential_Type': potential_type,
#                 'SF_Type': sf,
#                 'R_max': R_max,
#                 'Initial_R_max': initial_rmax_used,
#                 'Weibull_d': fit['d'],
#                 'Weibull_b': fit['b'],
#                 'Weibull_Rmin': R_min,
#                 'Initial_R_min': initial_rmin,
#                 'P50': p50_fit,
#                 'P88': p88_fit,
#                 'R_50': R_50,
#                 'R_88': R_88,
#                 'R_squared': fit['r_squared']
#             }
#             results.append(result)
    
#     results_df = pd.DataFrame(results)
#     print(f"\nResults for {potential_type} potential and {sf} sap flow:")
#     print(results_df[['Tree', 'Period', 'Initial_R_max', 'R_max', 'Initial_R_min', 'Weibull_Rmin', 'Weibull_d', 'Weibull_b', 'P50', 'P88', 'R_squared']])
#     return results_df, figures


import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Initial R_max values for each period (order: ES51, ES50, ES42, ES01, ES48, DF27, DF03, DF21, DF49)
R_max_pre = [0, 50000, 300000, 300000, 30000, 40000, 60000, 20000, 10500]#5000]
R_max_dry = [600000, 60000, 300000, 300000, 0, 20000, 60000, 20000, 10500]#3000]
R_max_post = [600000, 40000, 300000, 300000, 3000, 20000, 60000, 20000, 10500]#5000]

R_min_all = [10000, 8.56, 14.06, 183.76, 3.14, 89.61, 115.61, 13.83, 7.98] #from Hagen-Poiseuille 236.48

R_MIN_R_MAX_DATA = {
    'ES51': {'R_min': R_min_all[0], 'R_max': R_max_pre[0]},
    'ES50': {'R_min': R_min_all[1], 'R_max': R_max_pre[1]},
    'ES42': {'R_min': R_min_all[2], 'R_max': R_max_pre[2]},
    'ES01': {'R_min': R_min_all[3], 'R_max': R_max_pre[3]},
    'ES48': {'R_min': R_min_all[4], 'R_max': R_max_pre[4]},
    'DF27': {'R_min': R_min_all[5], 'R_max': R_max_pre[5]},
    'DF03': {'R_min': R_min_all[6], 'R_max': R_max_pre[6]},
    'DF21': {'R_min': R_min_all[7], 'R_max': R_max_pre[7]},
    'DF49': {'R_min': R_min_all[8], 'R_max': R_max_pre[8]}
}

def weibull_func(x, d, b, R_min, R_max):
    return R_min + (R_max - R_min) * (1-np.exp(-((-x / d) ** b))) # 1- exp (-((-x/d)^b))

# def weibull_function(psy, rmin, d, b):
#     return rmin * np.exp(((-psy / d) ** b))

def weibull_cdf(psy, d, b):
    return (1 - np.exp(-((-psy / d) ** b))) * 100

def calculate_ivc_fits(trees_data, potential_type='matric', sf='incomplete', path_output=''):
    sf_threshold = 0.1
    results = []
    figures = []
    
    dry_periods = {
        #'2021': [('2021-07-20', '2021-08-16', 5.6)],
        '2021': [('2021-07-13', '2021-08-15', 5.6)],
        '2022': [('2022-07-30', '2022-08-20', 0.4)],
    }
    
    period_colors = {
        'Pre-Dry': 'rgb(51, 153, 255)',  # Blue
        'Dry': 'rgb(255, 147, 0)',      # Orange
        'Post-Dry': 'rgb(0, 153, 0)'     # Green
    }
    
    tree_order = ['ES51', 'ES50', 'ES42', 'ES01', 'ES48', 'DF27', 'DF03', 'DF21', 'DF49']
    
    for tree_id, data in trees_data.items():
        tree = data['tree']
        year = data['year']
        
        print(f"\nProcessing tree: {tree}, Year: {year}, Potential Type: {potential_type}, SF Type: {sf}")
        
        if not ('PSY_cleaned' in data and isinstance(data['PSY_cleaned'], pd.DataFrame) and not data['PSY_cleaned'].empty):
            print(f"No PSY_cleaned data for {tree} in year {year}. Skipping...")
            continue
        
        if not ('SF_W_SM_PSY' in data and isinstance(data['SF_W_SM_PSY'], pd.DataFrame) and not data['SF_W_SM_PSY'].empty):
            print(f"No SF_W_SM_PSY data for {tree} in year {year}. Skipping...")
            continue
        
        if potential_type == 'matric':
            if not ('PSY_matric' in data and isinstance(data['PSY_matric'], pd.DataFrame) and not data['PSY_matric'].empty):
                print(f"No PSY_matric data for {tree} in year {year}. Skipping...")
                continue
            psy_s_df = data['PSY_matric'].rename(columns={'PSY_matric': 'PSYs'})
        elif potential_type == 'predawn':
            if not ('PSY_predawn' in data and not pd.isna(data['PSY_predawn']).all()):
                print(f"No PSY_predawn data for {tree} in year {year}. Skipping...")
                continue
            if isinstance(data['PSY_predawn'], pd.Series):
                psy_s_df = pd.DataFrame(data['PSY_predawn'], columns=['PSYs'])
            else:
                psy_s_df = data['PSY_predawn'].rename(columns={'PSY_predawn': 'PSYs'})
        else:
            print(f"Invalid potential_type for {tree} in year {year}. Skipping...")
            continue
        
        sf_w_sm_psy_df = data['SF_W_SM_PSY'].copy()
        psy_cleaned_df = data['PSY_cleaned'].rename(columns={'PSY': 'PSYx'})
        sf_w_sm_psy_df = sf_w_sm_psy_df.drop(columns=['PSY'], errors='ignore')
        sf_w_sm_psy_df = sf_w_sm_psy_df.join(psy_cleaned_df, how='left')
        
        if 'SF' not in sf_w_sm_psy_df.columns:
            if 'SF_complete' in sf_w_sm_psy_df.columns and 'SF_incomplete' in sf_w_sm_psy_df.columns:
                if sf == 'complete':
                    sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_complete']
                elif sf == 'incomplete':
                    sf_w_sm_psy_df['SF'] = sf_w_sm_psy_df['SF_incomplete']
                else:
                    print(f"Invalid SF type for {tree} in year {year}. Skipping...")
                    continue
            else:
                print(f"No SF data for {tree} in year {year}. Skipping...")
                continue
        
        sf_df = sf_w_sm_psy_df[['SF', 'Rain', 'VPD', 'PSYx']].query(f'SF >= {sf_threshold}')
        aligned_df = sf_df.join(psy_s_df, how='inner').dropna()
        
        aligned_df['PSYs'] = aligned_df.apply(lambda row: row['PSYx'] + 0.001 if row['PSYs'] <= row['PSYx'] else row['PSYs'], axis=1)
        aligned_df['PSYs'] = aligned_df['PSYs'].apply(lambda x: x if x < 0 else -0.001)
        
        aligned_df['Rp'] = ((aligned_df['PSYs'] - aligned_df['PSYx']) / aligned_df['SF']) * (3.6 * 1e6)
        
        daytime_filter = (aligned_df.index.hour >= 9) & (aligned_df.index.hour <= 21)
        aligned_df['exclude_flag'] = (aligned_df['VPD'] < 0.3) | (aligned_df['Rain'] > 0)
        daily_flags = aligned_df.groupby(aligned_df.index.date)['exclude_flag'].transform('max')
        valid_data = aligned_df[(daily_flags == False) & daytime_filter].dropna(subset=['Rp'])
        
        if valid_data.empty:
            print(f"No valid data after filtering for {tree} in year {year}. Skipping...")
            continue
        
        valid_data['Day'] = valid_data.index.date
        periods = dry_periods.get(year, [])
        period_labels = []
        for idx in valid_data.index:
            date = idx
            in_dry_period = False
            for start, end, _ in periods:
                start_date = pd.to_datetime(start)
                end_date = pd.to_datetime(end)
                if start_date <= date <= end_date:
                    in_dry_period = True
                    break
            if in_dry_period:
                period_labels.append('Dry')
            elif date < start_date if periods else True:
                period_labels.append('Pre-Dry')
            else:
                period_labels.append('Post-Dry')
        
        valid_data['Period'] = period_labels
        
        # Initialize dictionaries for period-specific fits and R_max
        period_fits = {}
        period_rmax = {}
        
        # Sensitivity analysis for R_max per period
        tree_key = tree_id.split('-')[0]
        tree_idx = tree_order.index(tree_key)
        
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = valid_data[valid_data['Period'] == period]
            if period_data.empty:
                continue
            
            # Set initial R_max based on period
            if period == 'Pre-Dry':
                initial_rmax = R_max_pre[tree_idx] #### 
            elif period == 'Dry':
                initial_rmax = R_max_dry[tree_idx]
            else:  # Post-Dry
                initial_rmax = R_max_post[tree_idx]
            
            best_rmax = initial_rmax
            best_r_squared = -np.inf
            current_fits = {}
            
            R_min = R_MIN_R_MAX_DATA[tree_key]['R_min']
            r_max_range = np.linspace(initial_rmax * 0.25, initial_rmax * 1.75, 5)  # ±70% of initial guess
            
            for r_max in r_max_range:
                period_rmax[period] = {'R_min': R_min, 'R_max': r_max, 'sw_area': np.nan}
                
                x_data = period_data['PSYx'].values
                y_data = period_data['Rp'].values
                
                if len(x_data) < 3:
                    continue
                
                d_initial = 4.0
                b_initial = 2.0
                bounds = ([1.0, 1.0], [4.0, 6.0])  # d (1 to 4), b (1 to 6)
                p0 = [d_initial, b_initial]
                
                try:
                    popt, _ = curve_fit(
                        lambda x, d, b: weibull_func(x, d, b, R_min, r_max),
                        x_data,
                        y_data,
                        p0=p0,
                        bounds=bounds,
                        maxfev=10000
                    )
                    d_fit, b_fit = popt
                    
                    y_pred = weibull_func(x_data, d_fit, b_fit, R_min, r_max)
                    ss_tot = np.sum((y_data - np.mean(y_data))**2)
                    ss_res = np.sum((y_data - y_pred)**2)
                    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else np.nan
                    
                    current_fits[r_max] = {
                        'd': d_fit,
                        'b': b_fit,
                        'r_squared': r_squared,
                        'x_data': x_data,
                        'y_data': y_data
                    }
                    if r_squared > best_r_squared:
                        best_r_squared = r_squared
                        best_rmax = r_max
                except RuntimeError:
                    continue
            
            if current_fits:  # Only update if a fit was successful
                period_fits[period] = current_fits.get(best_rmax, {})
                period_rmax[period]['R_max'] = best_rmax
                print(f"Best R_max for {tree} ({period}): {best_rmax:.2f} MPa s kg^-1 (Initial R_max: {initial_rmax:.2f}, R-squared: {best_r_squared:.2f}, d: {period_fits[period].get('d', np.nan):.2f}, b: {period_fits[period].get('b', np.nan):.2f})")
        
        # Recalculate HCL for plotting
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = valid_data[valid_data['Period'] == period]
            if period_data.empty:
                continue
            R_min = period_rmax[period]['R_min']
            R_max = period_rmax[period]['R_max']
            if not np.isnan(R_min) and not np.isnan(R_max) and R_max > R_min and np.isfinite(R_max):
                valid_data.loc[valid_data['Period'] == period, 'HCL_data(%)'] = ((period_data['Rp'] - R_min) / (R_max - R_min)) * 100
                valid_data['HCL_data(%)'] = np.clip(valid_data['HCL_data(%)'], 0, 100)
                print(f"Debug: Adjusted HCL_data(%) for {tree} ({period}) - Min: {valid_data[valid_data['Period'] == period]['HCL_data(%)'].min():.2f}, Max: {valid_data[valid_data['Period'] == period]['HCL_data(%)'].max():.2f}")
            else:
                print(f"Skipping adjusted HCL calculation for {tree} ({period}) due to invalid R_min ({R_min}) or R_max ({R_max}).")
                valid_data.loc[valid_data['Period'] == period, 'HCL_data(%)'] = np.nan
        
        # Create and save resistance plot
        fig_resistance = go.Figure()
        
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = valid_data[valid_data['Period'] == period]
            if not period_data.empty:
                fig_resistance.add_trace(go.Scatter(
                    x=period_data['PSYx'],
                    y=period_data['Rp'],
                    mode='markers',
                    name=f'{tree} - {period} Data',
                    marker=dict(size=8, color=period_colors[period]),
                    legendgroup=period,
                    showlegend=True
                ))
        
        for period, fit in period_fits.items():
            if fit:
                R_min = period_rmax[period]['R_min']
                R_max = period_rmax[period]['R_max']
                x_fit = np.linspace(min(fit['x_data']), max(fit['x_data']), 100) if len(fit['x_data']) > 0 else np.linspace(-10, 0, 100)
                y_fit = weibull_func(x_fit, fit['d'], fit['b'], R_min, R_max)
                fig_resistance.add_trace(go.Scatter(
                    x=x_fit,
                    y=y_fit,
                    mode='lines',
                    name=f'{tree} - Weibull Fit ({period})',
                    line=dict(color=period_colors[period], dash='dash'),
                    legendgroup=period,
                    showlegend=True
                ))
        
        fig_resistance.update_layout(
            height=600,
            width=800,
            #title=f'Resistance vs. Water Potential for {tree} ({year})',
            xaxis_title='Xylem Water Potential (MPa)',
            yaxis_title='Plant Resistance (MPa s kg^-1)',
            showlegend=True,
            legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
            margin=dict(r=50, t=100, b=50, l=50)
        )
        
        fig_resistance.show()
        fig_resistance.write_image(f'{path_output}IVC_plots/resistance_{tree}_{year}.png', scale=5)
        figures.append((fig_resistance, tree, year))
        
        # Create and save HCL plot
        fig_hcl = go.Figure()
        
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = valid_data[valid_data['Period'] == period]
            if not period_data.empty and 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all():
                fig_hcl.add_trace(go.Scatter(
                    x=period_data['PSYx'],
                    y=period_data['HCL_data(%)'],
                    mode='markers',
                    name=f'{tree} - HCL ({period}) Data',
                    marker=dict(size=8, color=period_colors[period]),
                    legendgroup=period,
                    showlegend=True
                ))
        
        predefined_x = np.linspace(0, -10, 100)
        for period, fit in period_fits.items():
            if fit:
                hcl_simulated = weibull_cdf(predefined_x, fit['d'], fit['b'])
                fig_hcl.add_trace(go.Scatter(
                    x=predefined_x,
                    y=hcl_simulated,
                    mode='lines',
                    name=f'{tree} - Simulated HCL ({period})',
                    line=dict(color=period_colors[period], dash='dash'),
                    legendgroup=period,
                    showlegend=True
                ))
        
        for period, fit in period_fits.items():
            if fit and not np.isnan(fit['d']) and not np.isnan(fit['b']):
                p50_fit = -fit['d'] * (np.log(2) ** (1 / fit['b']))
                p88_fit = -fit['d'] * ((np.log(1 / (1 - 0.88))) ** (1 / fit['b']))
                if not np.isnan(p50_fit):
                    fig_hcl.add_shape(
                        type="line",
                        x0=p50_fit,
                        x1=p50_fit,
                        y0=0,
                        y1=100,
                        line=dict(color=period_colors[period], width=2, dash='dot'),
                        name=f"P50 ({period})",
                    )
                if not np.isnan(p88_fit):
                    fig_hcl.add_shape(
                        type="line",
                        x0=p88_fit,
                        x1=p88_fit,
                        y0=0,
                        y1=100,
                        line=dict(color=period_colors[period], width=1, dash='dashdot'),
                        name=f"P88 ({period})",
                    )
        
        fig_hcl.update_layout(
            height=600,
            width=800,
            #title=f'HCL vs. Water Potential for {tree} ({year})',
            xaxis_title='Xylem Water Potential (MPa)',
            yaxis_title='HCL (%)',
            showlegend=True,
            legend=dict(x=1.02, y=1.0, xanchor='left', yanchor='top'),
            margin=dict(r=50, t=100, b=50, l=50)
        )
        
        fig_hcl.show()
        fig_hcl.write_image(f'{path_output}IVC_plots/hcl_{tree}_{year}.png', scale=5)
        figures.append((fig_hcl, tree, year))
        
        # Store results
        for period in ['Pre-Dry', 'Dry', 'Post-Dry']:
            period_data = valid_data[valid_data['Period'] == period]
            if period_data.empty:
                continue
            
            mean_hcl = period_data['HCL_data(%)'].mean() if 'HCL_data(%)' in period_data.columns and not period_data['HCL_data(%)'].isna().all() else np.nan
            
            if not period_data['Rp'].empty:
                max_rp_date = period_data['Rp'].idxmax()
                max_rp_day = max_rp_date.date() if pd.notna(max_rp_date) else np.nan
            else:
                max_rp_day = np.nan
            
            fit = period_fits.get(period, {'d': np.nan, 'b': np.nan, 'r_squared': np.nan})
            p50_fit = -fit['d'] * (np.log(2) ** (1 / fit['b'])) if not np.isnan(fit['d']) and not np.isnan(fit['b']) else np.nan
            p88_fit = -fit['d'] * ((np.log(1 / (1 - 0.88))) ** (1 / fit['b'])) if not np.isnan(fit['d']) and not np.isnan(fit['b']) else np.nan
            R_min = period_rmax[period]['R_min']
            R_max = period_rmax[period]['R_max']
            R_50 = R_min + 0.5 * (R_max - R_min) if not np.isnan(R_min) and not np.isnan(R_max) and R_max > R_min else np.nan
            R_88 = R_min + 0.88 * (R_max - R_min) if not np.isnan(R_min) and not np.isnan(R_max) and R_max > R_min else np.nan
            
            if period == 'Pre-Dry':
                initial_rmax_used = R_max_pre[tree_idx]
            elif period == 'Dry':
                initial_rmax_used = R_max_dry[tree_idx]
            else:  # Post-Dry
                initial_rmax_used = R_max_post[tree_idx]
            
            result = {
                'Tree': tree,
                'Year': year,
                'Period': period,
                'Mean_Rp': period_data['Rp'].mean() if not period_data['Rp'].empty else np.nan,
                'Max_Rp': period_data['Rp'].max() if not period_data['Rp'].empty else np.nan,
                'Max_Rp_Day': max_rp_day,
                'Mean_HCL': mean_hcl,
                'Potential_Type': potential_type,
                'SF_Type': sf,
                'R_max': R_max,
                'Initial_R_max': initial_rmax_used,
                'Weibull_d': fit['d'],
                'Weibull_b': fit['b'],
                'Weibull_Rmin': R_min,  # Added for consistency with your approach
                'P50': p50_fit,
                'P88': p88_fit,
                'R_50': R_50,
                'R_88': R_88,
                'R_squared': fit['r_squared']
            }
            results.append(result)
    
    results_df = pd.DataFrame(results)
    print(f"\nResults for {potential_type} potential and {sf} sap flow:")
    print(results_df[['Tree', 'Period', 'Initial_R_max', 'R_max', 'Weibull_d', 'Weibull_b', 'Weibull_Rmin', 'P50', 'P88', 'R_squared']])
    return results_df, figures


