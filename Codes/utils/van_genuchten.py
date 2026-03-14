import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Suppress all NumPy warnings globally
np.seterr(all='ignore')

# Constants
rho_w = 1000  # kg/m3
g = 9.81  # m/s2
n= 2.085 #1.89-2.28 for Sandy loams mid value 2.085   //2.68chen et al 2021
α= 0.0085 #0.007-0.01 MPa^-1 for Sandy loams mid value 0.0085 

def invθ(θ, θs, θr, α, n, m):
    """
    Calculate matric potential (Ψ) in MPa using the Van Genuchten equation.
    
    Parameters:
    θ (float): Soil moisture content (m3/m3)
    θs (float): Saturated soil moisture content (m3/m3)
    θr (float): Residual soil moisture content (m3/m3)
    α (float): Van Genuchten parameter (MPa^-1)
    n (float): Van Genuchten parameter
    m (float): Van Genuchten parameter (typically 1 - 1/n)
    
    Returns:
    float: Matric potential (Ψ) in MPa, or NaN if calculation fails
    """
    if θ <= θr or np.isnan(θ):
        return np.nan
    try:
        return (((1/α) * (((θs - θr) / (θ - θr))**(1/m) - 1)**(1/n)) * rho_w * 1e-6 * -1).real  # J/kg -> MPa
    except (ValueError, RuntimeWarning):
        return np.nan

def calculate_and_store_matric_potential(trees_data, n=n, α=α):
    """
    Calculate matric potential for each tree using the Van Genuchten equation and store in trees_data.

    Parameters:
    trees_data (dict): Dictionary containing tree data with 'SM' (soil moisture) data
    n (float): Van Genuchten parameter (curve steepness)
    α (float): Van Genuchten parameter (air entry suction)

    Returns:
    dict: Updated trees_data with 'PSY_matric' key containing matric potential Series
    """
    m = 1 - 1/n

    for tree_year, data in trees_data.items():
        psy_matric = pd.DataFrame(columns=['PSY_matric'])

        sm_data = data.get('SM')
        if (sm_data is None or 
            not isinstance(sm_data, pd.DataFrame) or 
            sm_data.empty or 
            'Soil_moisture' not in sm_data.columns or 
            sm_data['Soil_moisture'].isna().all()):
            data['PSY_matric'] = psy_matric
            continue

        # Extract soil moisture data
        tree_name = data['tree']
        year = data['year']

        if tree_name == 'ES42' and year == '2022':
            θ = sm_data['Soil_moisture'].values + 0.025
        else:
            θ = sm_data['Soil_moisture'].values  # m3/m3
        
        # Set Van Genuchten parameters
        if year == '2021':
            θs = 0.36 #0.36  # m3/m3 (saturated moisture content)
        else:
            θs = 0.47 # m3/m3 (saturated moisture content)

       

        # if np.nanmin(θ) >0.03:
        #     θr = np.nanmin(θ) - 0.021  # Residual moisture content
        # else:
        #     θr = 0.0000001
        θr = np.nanmin(θ) - 0.021  #0.021 Residual moisture content
        #print(tree_name,θr,np.nanmin(θ))

        # Calculate matric potential
        psy_soil = [invθ(j, θs, θr, α=α, n=n, m=m) for j in θ]
        psy_matric = pd.DataFrame({'PSY_matric': psy_soil}, index=sm_data.index)

        # Store in trees_data
        data['PSY_matric'] = psy_matric
    
    return trees_data

def plot_soil_moisture_and_matric_potential(trees_data, year):
    """
    Plot soil moisture (θ) and matric potential (Ψ) for trees in a given year.
    
    Parameters:
    trees_data (dict): Dictionary containing tree data with 'SM' and 'PSY_matric'
    year (str): Year to filter data ('2021' or '2022')
    """
    fig = go.Figure()

    # Define the same color palette as in plot_psy_matric_daily
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
        # Light Pink
        ('hsl(340, 70%, 85%)', 'hsl(340, 70%, 60%)'),    # Bright: #F7C9D6, Dark: #EB91AB
        # Grey
        ('hsl(0, 0%, 70%)', 'hsl(0, 0%, 45%)'),          # Bright: #B3B3B3, Dark: #737373
    ]

    # Create a mapping of tree names to color pairs for consistency across years and plots
    all_tree_names = sorted(set(data['tree'] for data in trees_data.values()))
    num_trees_total = len(all_tree_names)
    color_pairs = base_colors * (num_trees_total // len(base_colors) + 1)  # Repeat palette if needed
    color_pairs = color_pairs[:num_trees_total]  # Trim to the number of unique trees
    tree_color_map = {tree_name: color_pair for tree_name, color_pair in zip(all_tree_names, color_pairs)}

    for tree_year, data in trees_data.items():
        if data['year'] != year:
            continue
        
        tree_name = data['tree']
        sm_data = data.get('SM')
        psy_matric = data.get('PSY_matric', pd.DataFrame())
        
        # Skip if no valid soil moisture or matric potential data
        if (sm_data is None or 
            not isinstance(sm_data, pd.DataFrame) or 
            sm_data.empty or 
            'Soil_moisture' not in sm_data.columns or 
            sm_data['Soil_moisture'].isna().all() or 
            psy_matric.empty):
            continue
        
        # Filter soil moisture data for the given year
        sm_data = sm_data[sm_data.index.year == int(year)]
        if tree_name == 'ES42' and year == '2022':
            θ = sm_data['Soil_moisture'].values + 0.025
        else:
            θ = sm_data['Soil_moisture'].values  # m3/m3
        #θ = sm_data['Soil_moisture'].values
        
        # Ensure matric potential aligns with soil moisture dates
        psy_matric = psy_matric[psy_matric.index.isin(sm_data.index)]
        
        # Get the colors for this tree from the color map
        color_θ, color_ψ = tree_color_map[tree_name]

        # Plot soil moisture (θ) with the brighter shade
        fig.add_trace(go.Scatter(
            x=sm_data.index,
            y=θ,
            name=f'{tree_name}-θ',
            mode='lines',
            line=dict(color=color_θ)
        ))
        
        # Plot matric potential (Ψ) with the darker shade
        fig.add_trace(go.Scatter(
            x=psy_matric.index,
            y=psy_matric['PSY_matric'],
            name=f'{tree_name}-Ψ',
            mode='lines',
            line=dict(color=color_ψ)
        ))
    
    # Update layout
    fig.update_layout(
        #title='a) ' f'{year}',
        xaxis_title='Date',
        yaxis=dict(
            title='Matric Potential Ψ matric  (MPa) (values<0) | Soil Moisture θ (m3/m3) (values>0)',
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.1,
            xanchor="center",
            yanchor="top",
            itemsizing='constant'
        ),
        height=800
    )
    
    #fig.show()
    return fig