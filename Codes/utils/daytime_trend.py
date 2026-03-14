import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

def plot_max_daily_delta_vs_sapflow(trees_data, year):
    """
    Plot maximum daily difference between matric and xylem water potential (ΔΨ = Ψ_matric - PSY)
    against sap flow (SF_incomplete) for each tree, focusing on low sap flow to estimate R_max.
    
    Parameters:
    trees_data (dict): Dictionary containing tree data with 'SF_W_SM_PSY', 'PSY_cleaned', and 'PSY_matric'
    year (str): Year to filter data ('2021' or '2022')
    
    Returns:
    list: List of tuples, each containing a plotly figure and the corresponding tree name
    """
    results = []
    
    for tree_year, data in trees_data.items():
        if data['year'] != year:
            continue
        
        tree_name = data['tree']
        sf_data = data.get('SF_W_SM_PSY')
        psy_data = data.get('PSY_cleaned')
        psy_matric_data = data.get('PSY_matric')
        
        if (sf_data is None or 
            not isinstance(sf_data, pd.DataFrame) or 
            sf_data.empty or 
            'SF_incomplete' not in sf_data.columns or 
            sf_data['SF_incomplete'].isna().all() or
            psy_data is None or 
            not isinstance(psy_data, pd.DataFrame) or 
            psy_data.empty or 
            'PSY' not in psy_data.columns or 
            psy_data['PSY'].isna().all() or
            psy_matric_data is None or 
            not isinstance(psy_matric_data, pd.DataFrame) or 
            psy_matric_data.empty or 
            'PSY_matric' not in psy_matric_data.columns or 
            psy_matric_data['PSY_matric'].isna().all()):
            print(f"Skipping {tree_name} ({tree_year}) for {year} due to no data.")
            continue
        
        # Align SF, PSY, and PSY_matric data
        sf_df = sf_data[['SF_incomplete']].copy()
        sf_df = sf_df[sf_df['SF_incomplete'] >= 0]  # Ensure non-negative sap flow
        psy_df = psy_data[['PSY']].copy()
        psy_matric_df = psy_matric_data[['PSY_matric']].copy()
        
        aligned_df = sf_df.join(psy_df, how='inner').join(psy_matric_df, how='inner')
        if aligned_df.empty:
            continue
        
        # Filter for daytime (7 AM to 10 PM) as per your earlier focus
        daytime_data = aligned_df[(aligned_df.index.hour >= 7) & (aligned_df.index.hour <= 22)].copy()
        if daytime_data.empty:
            continue
        
        daytime_data['day'] = daytime_data.index.date
        daytime_data['delta_psi'] = daytime_data['PSY_matric'] - daytime_data['PSY']  # ΔΨ = Ψ_matric - PSY
        
        # Calculate maximum daily ΔΨ and corresponding SF
        daily_max = daytime_data.groupby('day').apply(
            lambda x: pd.Series({
                'max_delta_psi': x['delta_psi'].max(),
                'sf_at_max_delta': x.loc[x['delta_psi'].idxmax(), 'SF_incomplete']
            })
        ).reset_index()
        
        # Focus on low sap flow (e.g., SF < 0.1 cm³/h) for R_max estimation
        low_sf_threshold = 0.1
        low_sf_data = daily_max[daily_max['sf_at_max_delta'] <= low_sf_threshold]
        
        # Plotting
        fig = go.Figure()
        
        # Generate colors for each day
        unique_days = sorted(daily_max['day'].unique())
        colors = ['hsl('+str(h)+',50%,50%)' for h in np.linspace(0, 360, len(unique_days))]
        day_color_map = {day: color for day, color in zip(unique_days, colors)}
        
        # Scatter plot of max daily ΔΨ vs. SF
        for day in unique_days:
            day_data = daily_max[daily_max['day'] == day]
            color = day_color_map[day]
            fig.add_trace(go.Scatter(
                x=day_data['sf_at_max_delta'],
                y=day_data['max_delta_psi'],
                mode='markers',
                name=f'Day {day}',
                marker=dict(color=color, size=5),
                text=[f'Day: {day}'] * len(day_data),
                hoverinfo='x+y+text'
            ))
        
        # Optional: Linear fit for low SF data to estimate R_max
        if not low_sf_data.empty:
            X = low_sf_data['sf_at_max_delta'].values.reshape(-1, 1)
            y = low_sf_data['max_delta_psi'].values
            if len(X) >= 2 and not np.all(np.isnan(y)):
                model = LinearRegression().fit(X, y)
                slope = model.coef_[0]
                intercept = model.intercept_
                # R_max ≈ ΔΨ / SF when SF → 0, so R_max ≈ intercept / small SF
                r_max_estimate = intercept / low_sf_threshold if low_sf_threshold > 0 else np.nan
                
                x_range = [0, low_sf_data['sf_at_max_delta'].max()]
                y_fit = [slope * x + intercept for x in x_range]
                fig.add_trace(go.Scatter(
                    x=x_range,
                    y=y_fit,
                    mode='lines',
                    line=dict(color='gray', width=1, dash='dash'),
                    name=f'Fit (R_max est: {r_max_estimate:.2f} MPa s cm⁻³)',
                    showlegend=True,
                    hovertemplate=f'R_max Estimate: {r_max_estimate:.2f} MPa s cm⁻³<br>Slope: {slope:.2f}'
                ))
                print(f"Tree {tree_name}, R_max estimate: {r_max_estimate:.2f} MPa s cm⁻³ (SF < {low_sf_threshold} cm³/h)")

        if not fig.data:
            continue
        
        # Update layout
        fig.update_layout(
            xaxis_title='Sap Flow at Max ΔΨ (cm³/h)',
            yaxis_title='Max Daily ΔΨ (Ψ_matric - Ψ_xylem, MPa)',
            legend=dict(
                orientation="v",
                x=1.05,
                y=1,
                xanchor="left",
                yanchor="top",
                itemsizing='constant'
            ),
            margin=dict(r=200),
            title=f'Max Daily ΔΨ vs. Sap Flow for {tree_name} ({year})'
        )
        
        fig.show()
        results.append((fig, tree_name))
        print(f"Processed: {tree_name}")
    
    return results

# Example usage (uncomment to test with your data)
# results = plot_max_daily_delta_vs_sapflow(trees_data, '2021')