import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from scipy.stats import kruskal
import pingouin as pg
import numpy as np
from itertools import combinations

### USE PER DAY 
def define_periods(year):
    dry_periods = {
        '2021': [('2021-07-13', '2021-08-15', 5.6)],
        '2022': [('2022-07-30', '2022-08-20', 0.4)],
    }
    return dry_periods.get(year, [])

def add_period_column(df, year):
    df = df.copy()
    df.index = pd.to_datetime(df.index)  # Ensure index is datetime
    df['Period'] = 'Early'
    periods = define_periods(year)
    if periods:
        dry_start, dry_end, _ = periods[0]  # Ignore third value for now
        dry_mask = (df.index >= pd.to_datetime(dry_start)) & (df.index < pd.to_datetime(dry_end))
        df.loc[dry_mask, 'Period'] = 'Dry'
        df.loc[df.index >= pd.to_datetime(dry_end), 'Period'] = 'Late'
    return df

def process_water_use(trees_data, year):
    processed = {}
    for key, data in trees_data.items():
        if data['year'] == year and 'SF' in data and isinstance(data['SF'], pd.DataFrame):
            sf_df = data['SF'].copy()
            sf_df['SF_L_h'] = sf_df['SF_complete'] / 1000  # Convert cm3/h to L/h
            sf_df = add_period_column(sf_df, year)
            # Resample to daily total water use (L/day) by summing hourly values
            sf_df_daily = sf_df.resample('D')['SF_L_h'].sum()  # Sum all hourly values per day
            sf_df_daily = sf_df_daily.to_frame(name='SF_L_day')
            sf_df_daily['Period'] = sf_df['Period'].reindex(sf_df_daily.index, method='ffill')
            processed[key] = sf_df_daily
    return processed

def perform_stats(df, dv, group_col, year=None, period=None, comparison_type='group'):
    result_dict = {
        'Year': year,
        'Period': period,
        'Comparison': group_col,
        'Test': 'Kruskal-Wallis' if len(df[group_col].unique()) > 2 else 'Mann-Whitney U',
        'P_Value': None,
        'Details': []
    }
    
    df_clean = df[[dv, group_col]].dropna()
    df_clean = df_clean[df_clean[dv] > 0]
    
    if df_clean.empty or len(df_clean[group_col].unique()) < 2:
        print(f"No valid data or insufficient groups for {dv} in {group_col} after cleaning.")
        result_dict['Test'] = 'None'
        result_dict['Details'] = ['No valid data or insufficient groups after cleaning']
        return result_dict
    
    groups = [df_clean[df_clean[group_col] == g][dv] for g in df_clean[group_col].unique()]
    if len(groups) >= 2:
        if len(groups) > 2:
            stat, pval = kruskal(*groups)
            print(f"\nKruskal-Wallis Test: stat={stat:.4f}, p={pval:.4e}")
            result_dict['P_Value'] = pval
            result_dict['Details'].append(f"Kruskal-Wallis: stat={stat:.4f}, p={pval:.4e}")
            
            if pval < 0.05:
                posthoc_np = []
                pairs = list(combinations(df_clean[group_col].unique(), 2))
                for g1, g2 in pairs:
                    mwu_result = pg.mwu(df_clean[df_clean[group_col] == g1][dv],
                                        df_clean[df_clean[group_col] == g2][dv])
                    posthoc_np.append({
                        'Group1': g1,
                        'Group2': g2,
                        'U_stat': mwu_result['U-val'].iloc[0],
                        'P_val': mwu_result['p-val'].iloc[0] * len(pairs),  # Bonferroni correction
                        'Significant': mwu_result['p-val'].iloc[0] * len(pairs) < 0.05
                    })
                posthoc_df = pd.DataFrame(posthoc_np)
                print("\nPairwise Mann-Whitney U Tests (Bonferroni corrected):")
                print(posthoc_df[['Group1', 'Group2', 'U_stat', 'P_val', 'Significant']])
                result_dict['Details'].append(f"Non-parametric Post-hoc: {posthoc_df.to_string()}")
                if comparison_type == 'tree_periods':
                    result_dict['Post_Hoc'] = {
                        'E-D': posthoc_df[(posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Dry')]['Significant'].iloc[0] if any((posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Dry')) else False,
                        'D-L': posthoc_df[(posthoc_df['Group1'] == 'Dry') & (posthoc_df['Group2'] == 'Late')]['Significant'].iloc[0] if any((posthoc_df['Group1'] == 'Dry') & (posthoc_df['Group2'] == 'Late')) else False,
                        'E-L': posthoc_df[(posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Late')]['Significant'].iloc[0] if any((posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Late')) else False,
                        'p_E-D': posthoc_df[(posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Dry')]['P_val'].iloc[0] if any((posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Dry')) else np.nan,
                        'p_D-L': posthoc_df[(posthoc_df['Group1'] == 'Dry') & (posthoc_df['Group2'] == 'Late')]['P_val'].iloc[0] if any((posthoc_df['Group1'] == 'Dry') & (posthoc_df['Group2'] == 'Late')) else np.nan,
                        'p_E-L': posthoc_df[(posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Late')]['P_val'].iloc[0] if any((posthoc_df['Group1'] == 'Early') & (posthoc_df['Group2'] == 'Late')) else np.nan
                    }
                elif comparison_type == 'fractures':
                    result_dict['Post_Hoc'] = {f"{g1}-{g2}": posthoc_df[(posthoc_df['Group1'] == g1) & (posthoc_df['Group2'] == g2)]['Significant'].iloc[0] if any((posthoc_df['Group1'] == g1) & (posthoc_df['Group2'] == g2)) else False
                                               for g1, g2 in pairs}
                    result_dict['Post_Hoc_P'] = {f"{g1}-{g2}": posthoc_df[(posthoc_df['Group1'] == g1) & (posthoc_df['Group2'] == g2)]['P_val'].iloc[0] if any((posthoc_df['Group1'] == g1) & (posthoc_df['Group2'] == g2)) else np.nan
                                                 for g1, g2 in pairs}
        else:
            mwu_result = pg.mwu(groups[0], groups[1])
            pval = mwu_result['p-val'].iloc[0]
            print(f"\nMann-Whitney U Test: U={mwu_result['U-val'].iloc[0]:.4f}, p={pval:.4e}")
            result_dict['P_Value'] = pval
            result_dict['Details'].append(f"Mann-Whitney U: U={mwu_result['U-val'].iloc[0]:.4f}, p={pval:.4e}")
    
    return result_dict

def plot_water_use_daily_boxplots(trees_data, year):
    processed = process_water_use(trees_data, year)
    if not processed:
        print(f"No data for year {year}")
        return None
    
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
                        subplot_titles=('Early Season', 'Dry Season', 'Late Season'))
    
    periods = ['Early', 'Dry', 'Late']
    all_data_per_period = {period: pd.DataFrame() for period in periods}
    results_table = []
    
    for col, period in enumerate(periods, 1):
        all_data = []
        unique_trees = set(key.split('-')[0] for key in processed.keys())  # Unique tree IDs
        for key, df in processed.items():
            tree_id = key.split('-')[0]  # e.g., 'DF49'
            period_df = df[df['Period'] == period].copy()
            if not period_df.empty:
                site = 'Soil' if tree_id in ['DF49', 'ES48'] else 'Cliff'
                species = 'DF' if tree_id in ['DF21', 'DF27', 'DF03', 'DF49'] else 'ES' if tree_id in ['ES01', 'ES51', 'ES50', 'ES42', 'ES48'] else trees_data[key]['species']
                for val in period_df['SF_L_day']:
                    all_data.append({
                        'Tree': tree_id,
                        'Species': species,
                        'Site': site,
                        'SF_L_day': val
                    })
        if all_data:
            plot_df = pd.DataFrame(all_data)
            box = px.box(plot_df, x='Tree', y='SF_L_day', color='Species',
                         color_discrete_map={'DF': 'blue', 'ES': 'red'})
            for trace in box.data:
                fig.add_trace(trace, row=1, col=col)
            all_data_per_period[period] = plot_df
    
    fig.update_layout(height=600, width=1200, showlegend=False)
    fig.update_yaxes(title_text='Water Use (L/day)', row=1, col=1)
    fig.show()
    
    # Statistical comparisons per period
    for period, plot_df in all_data_per_period.items():
        if not plot_df.empty:
            print(f"\n=== Statistical Comparisons for {period} Period ({year}) ===")
            
            # 1. Averaged Soil vs. Averaged Cliff
            site_df = plot_df.copy()
            site_df['Group'] = site_df['Site']
            site_means = site_df.groupby(['Group', 'Tree'])['SF_L_day'].mean().reset_index()
            site_avg = site_means.groupby('Group')['SF_L_day'].mean().reset_index()
            print("\nAveraged Soil vs. Averaged Cliff Comparison (Mann-Whitney U):")
            result_dict = perform_stats(site_df, dv='SF_L_day', group_col='Group', year=year, period=period, comparison_type='site_avg')
            result_dict['Mean_Soil'] = site_avg[site_avg['Group'] == 'Soil']['SF_L_day'].iloc[0] if 'Soil' in site_avg['Group'].values else np.nan
            result_dict['Mean_Cliff'] = site_avg[site_avg['Group'] == 'Cliff']['SF_L_day'].iloc[0] if 'Cliff' in site_avg['Group'].values else np.nan
            result_dict['Significant'] = result_dict['P_Value'] < 0.05
            results_table.append(result_dict)
    
    # 2. Individual Tree Across Periods
    for tree_id in unique_trees:
        tree_data = []
        for period in periods:
            for key, df in processed.items():
                if key.split('-')[0] == tree_id and not df[df['Period'] == period].empty:
                    period_df = df[df['Period'] == period].copy()
                    for val in period_df['SF_L_day']:
                        tree_data.append({
                            'Tree': tree_id,
                            'Period': period,
                            'SF_L_day': val
                        })
        if tree_data:
            tree_df = pd.DataFrame(tree_data)
            print(f"\n=== Period Comparison for Tree {tree_id} ({year}) ===")
            result_dict = perform_stats(tree_df, dv='SF_L_day', group_col='Period', year=year, period=tree_id, comparison_type='tree_periods')
            tree_means = tree_df.groupby('Period')['SF_L_day'].mean().reset_index()
            for period in periods:
                result_dict[f'Mean_{period}'] = tree_means[tree_means['Period'] == period]['SF_L_day'].iloc[0] if period in tree_means['Period'].values else np.nan
            result_dict['Pct_Change_Early_to_Dry'] = ((result_dict.get('Mean_Dry', np.nan) - result_dict.get('Mean_Early', np.nan)) / result_dict.get('Mean_Early', np.nan) * 100) if result_dict.get('Mean_Early', np.nan) and not np.isnan(result_dict.get('Mean_Dry', np.nan)) else np.nan
            result_dict['Pct_Change_Dry_to_Late'] = ((result_dict.get('Mean_Late', np.nan) - result_dict.get('Mean_Dry', np.nan)) / result_dict.get('Mean_Dry', np.nan) * 100) if result_dict.get('Mean_Dry', np.nan) and not np.isnan(result_dict.get('Mean_Late', np.nan)) else np.nan
            result_dict['Pct_Change_Early_to_Late'] = ((result_dict.get('Mean_Late', np.nan) - result_dict.get('Mean_Early', np.nan)) / result_dict.get('Mean_Early', np.nan) * 100) if result_dict.get('Mean_Early', np.nan) and not np.isnan(result_dict.get('Mean_Late', np.nan)) else np.nan
            result_dict['Significant_E-D'] = result_dict.get('Post_Hoc', {}).get('E-D', False)
            result_dict['Significant_D-L'] = result_dict.get('Post_Hoc', {}).get('D-L', False)
            result_dict['Significant_E-L'] = result_dict.get('Post_Hoc', {}).get('E-L', False)
            results_table.append(result_dict)
    
    # Print results tables
    if results_table:
        # Individual Tree Across Periods
        tree_results = [r for r in results_table if r['Comparison'] == 'Period']
        if tree_results:
            print("\n=== Results for Individual Tree Across Periods (Water Use, L/day) ===")
            tree_df = pd.DataFrame(tree_results)
            print(tree_df[['Period', 'Significant_E-D', 'Significant_D-L', 'Significant_E-L', 'Post_Hoc.p_E-D', 'Post_Hoc.p_D-L', 'Post_Hoc.p_E-L', 'Mean_Early', 'Mean_Dry', 'Mean_Late', 'Pct_Change_Early_to_Dry', 'Pct_Change_Dry_to_Late', 'Pct_Change_Early_to_Late']].rename(columns={
                'Period': 'Tree', 'Significant_E-D': 'E-D', 'Significant_D-L': 'D-L', 'Significant_E-L': 'E-L',
                'Post_Hoc.p_E-D': 'p_E-D', 'Post_Hoc.p_D-L': 'p_D-L', 'Post_Hoc.p_E-L': 'p_E-L'
            }).to_string(index=False))
        
        # Averaged Soil vs. Cliff
        site_results = [r for r in results_table if r['Comparison'] == 'Group']
        if site_results:
            print("\n=== Results for Averaged Soil vs. Averaged Cliff (Water Use, L/day) ===")
            site_df = pd.DataFrame(site_results)
            print(site_df[['Period', 'Significant', 'P_Value', 'Mean_Soil', 'Mean_Cliff']].rename(columns={
                'Significant': 'Soil-Cliff', 'P_Value': 'p_Soil-Cliff'
            }).to_string(index=False))
    
    return fig

def water_use_cliff_boxplots(trees_data, year):
    processed = process_water_use(trees_data, year)
    if not processed:
        print(f"No data for year {year}")
        return None
    
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
                        subplot_titles=('Early Season', 'Dry Season', 'Late Season'))
    
    periods = ['Early', 'Dry', 'Late']
    cliff_tree_stats = {}  # To store statistics for each cliff tree per period
    all_data_per_period = {period: pd.DataFrame() for period in periods}
    results_table = []
    
    for col, period in enumerate(periods, 1):
        all_data = []
        for key, df in processed.items():
            tree_id = key.split('-')[0]  # e.g., 'DF49'
            if tree_id not in ['DF49', 'ES48']:  # Exclude soil trees
                period_df = df[df['Period'] == period].copy()
                if not period_df.empty:
                    species = 'DF' if tree_id in ['DF21', 'DF27', 'DF03'] else 'ES' if tree_id in ['ES01', 'ES51', 'ES50', 'ES42'] else trees_data[key]['species']
                    for val in period_df['SF_L_day']:
                        all_data.append({
                            'Tree': tree_id,
                            'Species': species,
                            'Site': trees_data[key]['site'],
                            'SF_L_day': val
                        })
                    # Calculate statistics for this tree and period
                    tree_data = period_df['SF_L_day'].dropna()
                    if tree_id not in cliff_tree_stats:
                        cliff_tree_stats[tree_id] = {}
                    cliff_tree_stats[tree_id][period] = {
                        'mean': tree_data.mean(),
                        'sd': tree_data.std(),
                        'n': len(tree_data)
                    }
        
        if all_data:
            plot_df = pd.DataFrame(all_data)
            box = px.box(plot_df, x='Tree', y='SF_L_day', color='Species',
                         color_discrete_map={'DF': 'blue', 'ES': 'red'})
            for trace in box.data:
                fig.add_trace(trace, row=1, col=col)
            all_data_per_period[period] = plot_df
        
        # Print statistics for the current period
        print(f"\nStatistics for Period {period} ({year}):")
        for tree_id, periods_data in cliff_tree_stats.items():
            if period in periods_data:
                stats = periods_data[period]
                print(f"Tree {tree_id}: Mean = {stats['mean']:.1f} ± {stats['sd']:.1f} L/day, n = {stats['n']}")
    
    fig.update_layout(height=600, width=1200, showlegend=False)
    fig.update_yaxes(title_text='Water Use (L/day)', row=1, col=1)
    fig.show()
    
    # Statistical comparisons per period (Cliff only)
    for period, plot_df in all_data_per_period.items():
        if not plot_df.empty:
            print(f"\n=== Statistical Comparisons for {period} Period ({year}) - Cliff Only ===")
            
            # 1. Firs vs. Spruces
            cliff_df = plot_df.copy()
            cliff_df['Group'] = cliff_df['Species']
            cliff_means = cliff_df.groupby(['Group', 'Tree'])['SF_L_day'].mean().reset_index()
            cliff_avg = cliff_means.groupby('Group')['SF_L_day'].mean().reset_index()
            print("\nFirs vs. Spruces (Mann-Whitney U):")
            result_dict = perform_stats(cliff_df, dv='SF_L_day', group_col='Group', year=year, period=period, comparison_type='species')
            result_dict['Mean_Fir'] = cliff_avg[cliff_avg['Group'] == 'DF']['SF_L_day'].iloc[0] if 'DF' in cliff_avg['Group'].values else np.nan
            result_dict['Mean_Spruce'] = cliff_avg[cliff_avg['Group'] == 'ES']['SF_L_day'].iloc[0] if 'ES' in cliff_avg['Group'].values else np.nan
            result_dict['Significant'] = result_dict['P_Value'] < 0.05
            result_dict['Pct_Change_Fir'] = np.nan
            result_dict['Pct_Change_Spruce'] = np.nan
            results_table.append(result_dict)
            
            # 2. Among all Cliff Trees/Fractures
            cliff_df['Group'] = cliff_df['Tree']
            cliff_tree_means = cliff_df.groupby('Group')['SF_L_day'].mean().reset_index()
            print("\nDifferences among Cliff Trees/Fractures (Kruskal-Wallis):")
            result_dict = perform_stats(cliff_df, dv='SF_L_day', group_col='Group', year=year, period=period, comparison_type='fractures')
            for tree_id in cliff_tree_means['Group']:
                result_dict[f'Mean_{tree_id}'] = cliff_tree_means[cliff_tree_means['Group'] == tree_id]['SF_L_day'].iloc[0]
            results_table.append(result_dict)
    
    # Calculate percentage changes for Firs vs. Spruces across periods
    species_results = [r for r in results_table if r['Comparison'] == 'Species']
    for species_result in species_results:
        period = species_result['Period']
        early_result = next((r for r in species_results if r['Period'] == 'Early'), {})
        dry_result = next((r for r in species_results if r['Period'] == 'Dry'), {})
        late_result = next((r for r in species_results if r['Period'] == 'Late'), {})
        if period == 'Dry':
            species_result['Pct_Change_Fir'] = ((dry_result.get('Mean_Fir', np.nan) - early_result.get('Mean_Fir', np.nan)) / early_result.get('Mean_Fir', np.nan) * 100) if early_result.get('Mean_Fir', np.nan) and not np.isnan(dry_result.get('Mean_Fir', np.nan)) else np.nan
            species_result['Pct_Change_Spruce'] = ((dry_result.get('Mean_Spruce', np.nan) - early_result.get('Mean_Spruce', np.nan)) / early_result.get('Mean_Spruce', np.nan) * 100) if early_result.get('Mean_Spruce', np.nan) and not np.isnan(dry_result.get('Mean_Spruce', np.nan)) else np.nan
        elif period == 'Late':
            species_result['Pct_Change_Fir'] = ((late_result.get('Mean_Fir', np.nan) - early_result.get('Mean_Fir', np.nan)) / early_result.get('Mean_Fir', np.nan) * 100) if early_result.get('Mean_Fir', np.nan) and not np.isnan(late_result.get('Mean_Fir', np.nan)) else np.nan
            species_result['Pct_Change_Spruce'] = ((late_result.get('Mean_Spruce', np.nan) - early_result.get('Mean_Spruce', np.nan)) / early_result.get('Mean_Spruce', np.nan) * 100) if early_result.get('Mean_Spruce', np.nan) and not np.isnan(late_result.get('Mean_Spruce', np.nan)) else np.nan
    
    # Print results tables
    if results_table:
        # Firs vs. Spruces
        species_results = [r for r in results_table if r['Comparison'] == 'Species']
        if species_results:
            print("\n=== Results for Cliff Firs vs. Cliff Spruces (Water Use, L/day) ===")
            species_df = pd.DataFrame(species_results)
            print(species_df[['Period', 'Significant', 'P_Value', 'Mean_Fir', 'Mean_Spruce', 'Pct_Change_Fir', 'Pct_Change_Spruce']].rename(columns={
                'Significant': 'Fir-Spruce', 'P_Value': 'p_Fir-Spruce'
            }).to_string(index=False))
        
        # Among Cliff Trees/Fractures
        fracture_results = [r for r in results_table if r['Comparison'] == 'Tree']
        if fracture_results:
            print("\n=== Results for Cliff Trees/Fractures (Water Use, L/day) ===")
            fracture_df = pd.DataFrame(fracture_results)
            columns = ['Period', 'P_Value']
            tree_columns = [col for col in fracture_df.columns if col.startswith('Mean_')]
            columns.extend(tree_columns)
            pairs = [k for k in fracture_df.iloc[0].get('Post_Hoc', {}).keys()]
            for pair in pairs:
                columns.append(f'Sig_{pair}')
                columns.append(f'p_{pair}')
            print(fracture_df[columns].to_string(index=False))
    
    return fig

def plot_water_use_leaf_area_boxplots(trees_data, year):
    processed = process_water_use(trees_data, year)
    if not processed:
        print(f"No data for year {year}")
        return None
    
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
                        subplot_titles=('Early Season', 'Dry Season', 'Late Season'))
    
    periods = ['Early', 'Dry', 'Late']
    tree_stats = {}  # To store statistics for each tree per period
    all_data_per_period = {period: pd.DataFrame() for period in periods}
    results_table = []
    
    for col, period in enumerate(periods, 1):
        all_data = []
        unique_trees = set(key.split('-')[0] for key in processed.keys())  # Unique tree IDs
        for key, df in processed.items():
            tree_id = key.split('-')[0]  # e.g., 'DF49'
            period_df = df[df['Period'] == period].copy()
            if not period_df.empty:
                # Convert sap flow from cm³/h to dm³/h and sum to L/day
                sf_df = trees_data[key]['SF'].copy()
                sf_df['SF_dm3_h'] = sf_df['SF_complete'] / 1000.0  # cm³/h to dm³/h
                sf_df_daily = sf_df.resample('D')['SF_dm3_h'].sum()  # Sum to dm³/day = L/day
                period_sf_daily = sf_df_daily[period_df.index].dropna()  # Align with period
                # Convert leaf area from cm² to m²
                leaf_area_cm2 = trees_data[key].get('leaf_area')  # No default, raise KeyError if missing
                if leaf_area_cm2 is None:
                    print(f"Warning: No leaf_area found for {key}, using 10000 cm² (1 m²) as default.")
                    leaf_area_cm2 = 10000.0
                leaf_area_m2 = float(leaf_area_cm2) / 10000.0  # Convert cm² to m²
                if leaf_area_m2 <= 0:
                    print(f"Warning: Invalid leaf_area for {key}, using 1 m² instead.")
                    leaf_area_m2 = 1.0  # Avoid division by zero
                site = 'Soil' if tree_id in ['DF49', 'ES48'] else 'Cliff'
                species = 'DF' if tree_id in ['DF21', 'DF27', 'DF03', 'DF49'] else 'ES' if tree_id in ['ES01', 'ES51', 'ES50', 'ES48', 'ES42'] else trees_data[key]['species']
                for val in period_sf_daily:  # val in L/day
                    water_use_per_leaf = val / leaf_area_m2  # L/day/m²
                    all_data.append({
                        'Tree': tree_id,
                        'Species': species,
                        'Site': site,
                        'Water_Use_per_Leaf': water_use_per_leaf
                    })
                # Calculate statistics for this tree and period
                tree_data = period_sf_daily.dropna()
                if tree_id not in tree_stats:
                    tree_stats[tree_id] = {}
                tree_stats[tree_id][period] = {
                    'mean': tree_data.mean() / leaf_area_m2,  # Mean in L/day/m²
                    'sd': tree_data.std() / leaf_area_m2,    # SD in L/day/m²
                    'n': len(tree_data)
                }
        
        if all_data:
            plot_df = pd.DataFrame(all_data)
            box = px.box(plot_df, x='Tree', y='Water_Use_per_Leaf', color='Species',
                         color_discrete_map={'DF': 'blue', 'ES': 'red'})
            for trace in box.data:
                fig.add_trace(trace, row=1, col=col)
            all_data_per_period[period] = plot_df
        
        # Print statistics for the current period
        print(f"\nStatistics for Period {period} ({year}) - Water Use per Leaf Area (L/day/m²):")
        for tree_id, periods_data in tree_stats.items():
            if period in periods_data:
                stats = periods_data[period]
                print(f"Tree {tree_id}: Mean = {stats['mean']:.2f} ± {stats['sd']:.2f} L/day/m², n = {stats['n']}")
    
    fig.update_layout(height=600, width=1200, showlegend=False)
    fig.update_yaxes(title_text='Water Use per Leaf Area (L/day/m²)', row=1, col=1)
    fig.show()
    
    # Statistical comparisons per period for water use per leaf area
    for period, plot_df in all_data_per_period.items():
        if not plot_df.empty:
            print(f"\n=== Statistical Comparisons for {period} Period ({year}) - Water Use per Leaf Area ===")
            
            # 1. Averaged Soil vs. Averaged Cliff
            all_df = plot_df.copy()
            all_df['Group'] = all_df['Site']
            site_means = all_df.groupby(['Group', 'Tree'])['Water_Use_per_Leaf'].mean().reset_index()
            site_avg = site_means.groupby('Group')['Water_Use_per_Leaf'].mean().reset_index()
            print("\nAveraged Soil vs. Averaged Cliff Comparison (Mann-Whitney U):")
            result_dict = perform_stats(all_df, dv='Water_Use_per_Leaf', group_col='Group', year=year, period=period, comparison_type='site_avg')
            result_dict['Mean_Soil'] = site_avg[site_avg['Group'] == 'Soil']['Water_Use_per_Leaf'].iloc[0] if 'Soil' in site_avg['Group'].values else np.nan
            result_dict['Mean_Cliff'] = site_avg[site_avg['Group'] == 'Cliff']['Water_Use_per_Leaf'].iloc[0] if 'Cliff' in site_avg['Group'].values else np.nan
            result_dict['Significant'] = result_dict['P_Value'] < 0.05
            results_table.append(result_dict)
            
            # 2. Firs vs. Spruces Overall
            all_df['Group'] = all_df['Species']
            all_means = all_df.groupby(['Group', 'Tree'])['Water_Use_per_Leaf'].mean().reset_index()
            all_avg = all_means.groupby('Group')['Water_Use_per_Leaf'].mean().reset_index()
            print("\nFirs vs. Spruces Overall (Mann-Whitney U):")
            result_dict = perform_stats(all_df, dv='Water_Use_per_Leaf', group_col='Group', year=year, period=period, comparison_type='species')
            result_dict['Mean_Fir'] = all_avg[all_avg['Group'] == 'DF']['Water_Use_per_Leaf'].iloc[0] if 'DF' in all_avg['Group'].values else np.nan
            result_dict['Mean_Spruce'] = all_avg[all_avg['Group'] == 'ES']['Water_Use_per_Leaf'].iloc[0] if 'ES' in all_avg['Group'].values else np.nan
            result_dict['Significant'] = result_dict['P_Value'] < 0.05
            result_dict['Pct_Change_Fir'] = np.nan
            result_dict['Pct_Change_Spruce'] = np.nan
            results_table.append(result_dict)
    
    # Calculate percentage changes for Firs vs. Spruces across periods
    species_results = [r for r in results_table if r['Comparison'] == 'Species']
    for species_result in species_results:
        period = species_result['Period']
        early_result = next((r for r in species_results if r['Period'] == 'Early'), {})
        dry_result = next((r for r in species_results if r['Period'] == 'Dry'), {})
        late_result = next((r for r in species_results if r['Period'] == 'Late'), {})
        if period == 'Dry':
            species_result['Pct_Change_Fir'] = ((dry_result.get('Mean_Fir', np.nan) - early_result.get('Mean_Fir', np.nan)) / early_result.get('Mean_Fir', np.nan) * 100) if early_result.get('Mean_Fir', np.nan) and not np.isnan(dry_result.get('Mean_Fir', np.nan)) else np.nan
            species_result['Pct_Change_Spruce'] = ((dry_result.get('Mean_Spruce', np.nan) - early_result.get('Mean_Spruce', np.nan)) / early_result.get('Mean_Spruce', np.nan) * 100) if early_result.get('Mean_Spruce', np.nan) and not np.isnan(dry_result.get('Mean_Spruce', np.nan)) else np.nan
        elif period == 'Late':
            species_result['Pct_Change_Fir'] = ((late_result.get('Mean_Fir', np.nan) - early_result.get('Mean_Fir', np.nan)) / early_result.get('Mean_Fir', np.nan) * 100) if early_result.get('Mean_Fir', np.nan) and not np.isnan(late_result.get('Mean_Fir', np.nan)) else np.nan
            species_result['Pct_Change_Spruce'] = ((late_result.get('Mean_Spruce', np.nan) - early_result.get('Mean_Spruce', np.nan)) / early_result.get('Mean_Spruce', np.nan) * 100) if early_result.get('Mean_Spruce', np.nan) and not np.isnan(late_result.get('Mean_Spruce', np.nan)) else np.nan
    
    # Print results tables
    if results_table:
        # Soil vs. Cliff
        site_results = [r for r in results_table if r['Comparison'] == 'Group']
        if site_results:
            print("\n=== Results for Averaged Soil vs. Averaged Cliff (Water Use per Leaf Area, L/day/m²) ===")
            site_df = pd.DataFrame(site_results)
            print(site_df[['Period', 'Significant', 'P_Value', 'Mean_Soil', 'Mean_Cliff']].rename(columns={
                'Significant': 'Soil-Cliff', 'P_Value': 'p_Soil-Cliff'
            }).to_string(index=False))
        
        # Firs vs. Spruces
        species_results = [r for r in results_table if r['Comparison'] == 'Species']
        if species_results:
            print("\n=== Results for Firs vs. Spruces Overall (Water Use per Leaf Area, L/day/m²) ===")
            species_df = pd.DataFrame(species_results)
            print(species_df[['Period', 'Significant', 'P_Value', 'Mean_Fir', 'Mean_Spruce', 'Pct_Change_Fir', 'Pct_Change_Spruce']].rename(columns={
                'Significant': 'Fir-Spruce', 'P_Value': 'p_Fir-Spruce'
            }).to_string(index=False))
    
    return fig

def plot_cumulative_bar(trees_data):
    total_flow_2021 = []
    total_flow_2022 = []
    names_2021 = []
    names_2022 = []
    
    # Collect data for 2021 and 2022
    for key, data in trees_data.items():
        if 'SF' in data and isinstance(data['SF'], pd.DataFrame):
            season_sf = data['SF']['SF_complete'].sum() / 1000  # Convert to litres
            name = key.split('-')[0]  # e.g., 'DF49' from 'DF49-2021'
            if data['year'] == '2021':
                total_flow_2021.append(season_sf)
                names_2021.append(name)
            elif data['year'] == '2022':
                total_flow_2022.append(season_sf)
                names_2022.append(name)
    
    # Create the bar plot
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names_2021,
        y=total_flow_2021,
        name='2021',
        marker_color='yellow'
    ))
    fig.add_trace(go.Bar(
        x=names_2022,
        y=total_flow_2022,
        name='2022',
        marker_color='lightgreen'
    ))

    # Add dotted lines at 2000 L
    fig.add_hline(y=2000, line_dash="dot", line_width=0.5, line_color="black")

    fig.update_layout(barmode='group', xaxis_tickangle=-45, xaxis=dict(title='Tree Species-ID'),
                      yaxis=dict(title='Seasonal Water Use (L)'))
    fig.show()

    # Generate table with seasonal differences
    table_data = []
    tree_ids = set(names_2021 + names_2022)
    for tree_id in tree_ids:
        flow_2021 = next((flow for name, flow in zip(names_2021, total_flow_2021) if name == tree_id), None)
        flow_2022 = next((flow for name, flow in zip(names_2022, total_flow_2022) if name == tree_id), None)
        fold_change = (flow_2022 / flow_2021) if flow_2021 and flow_2022 else None
        table_data.append({
            'Tree': tree_id,
            '2021_Total_L': flow_2021 if flow_2021 is not None else 'N/A',
            '2022_Total_L': flow_2022 if flow_2022 is not None else 'N/A',
            'Fold_Change': f'{fold_change:.1f}x' if fold_change else 'N/A'
        })
    
    table_df = pd.DataFrame(table_data)
    print("\n=== Cumulative Water Use Table ===")
    print(table_df.to_string(index=False))
    return fig

# import pandas as pd
# import plotly.express as px
# from plotly.subplots import make_subplots
# import plotly.graph_objects as go
# from scipy.stats import shapiro
# import pingouin as pg

# ### USE PER DAY 
# def define_periods(year):
#     dry_periods = {
#         '2021': [('2021-07-13', '2021-08-15', 5.6)],
#         '2022': [('2022-07-30', '2022-08-20', 0.4)],
#     }
#     return dry_periods.get(year, [])

# def add_period_column(df, year):
#     df = df.copy()
#     df.index = pd.to_datetime(df.index)  # Ensure index is datetime
#     df['Period'] = 'Early'
#     periods = define_periods(year)
#     if periods:
#         dry_start, dry_end, _ = periods[0]  # Ignore third value for now
#         dry_mask = (df.index >= pd.to_datetime(dry_start)) & (df.index < pd.to_datetime(dry_end))
#         df.loc[dry_mask, 'Period'] = 'Dry'
#         df.loc[df.index >= pd.to_datetime(dry_end), 'Period'] = 'Late'
#     return df

# def process_water_use(trees_data, year):
#     processed = {}
#     for key, data in trees_data.items():
#         if data['year'] == year and 'SF' in data and isinstance(data['SF'], pd.DataFrame):
#             sf_df = data['SF'].copy()
#             sf_df['SF_L_h'] = sf_df['SF_complete'] / 1000  # Convert cm3/h to L/h
#             sf_df = add_period_column(sf_df, year)
#             # Resample to daily total water use (L/day) by summing hourly values
#             sf_df_daily = sf_df.resample('D')['SF_L_h'].sum()  # Sum all hourly values per day
#             sf_df_daily = sf_df_daily.to_frame(name='SF_L_day')
#             sf_df_daily['Period'] = sf_df['Period']
#             processed[key] = sf_df_daily
#     return processed

# def plot_water_use_daily_boxplots(trees_data, year):
#     processed = process_water_use(trees_data, year)
#     if not processed:
#         print(f"No data for year {year}")
#         return None
    
#     fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
#                         subplot_titles=('Early Season', 'Dry Season', 'Late Season'))
    
#     periods = ['Early', 'Dry', 'Late']
#     for col, period in enumerate(periods, 1):
#         all_data = []
#         unique_trees = set(key.split('-')[0] for key in processed.keys())  # Unique tree IDs
#         for key, df in processed.items():
#             tree_id = key.split('-')[0]  # e.g., 'DF49'
#             period_df = df[df['Period'] == period]
#             if not period_df.empty:
#                 for val in period_df['SF_L_day']:
#                     all_data.append({
#                         'Tree': tree_id,
#                         'Species': trees_data[key]['species'],
#                         'Site': trees_data[key]['site'],
#                         'SF_L_day': val
#                     })
        
#         if all_data:
#             plot_df = pd.DataFrame(all_data)
#             box = px.box(plot_df, x='Tree', y='SF_L_day', color='Species')
#             for trace in box.data:
#                 fig.add_trace(trace, row=1, col=col)
    
#     fig.update_layout(height=600, width=1200, #title_text=f'Water Use Distributions (L/day) by Tree and Period - {year}',
#                       showlegend=False)
#     fig.update_yaxes(title_text='Water Use (L/day)', row=1, col=1)
#     fig.show()
#     return fig



# ###########################################################################################################
# #ONLY CLIFF TREES 
# def water_use_cliff_boxplots(trees_data, year):
#     processed = process_water_use(trees_data, year)
#     if not processed:
#         print(f"No data for year {year}")
#         return None
    
#     fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
#                         subplot_titles=('Early Season', 'Dry Season', 'Late Season'))
    
#     periods = ['Early', 'Dry', 'Late']
#     cliff_tree_stats = {}  # To store statistics for each cliff tree per period
    
#     for col, period in enumerate(periods, 1):
#         all_data = []
#         for key, df in processed.items():
#             tree_id = key.split('-')[0]  # e.g., 'DF49'
#             if tree_id not in ['DF49', 'ES48']:  # Exclude soil trees
#                 period_df = df[df['Period'] == period]
#                 if not period_df.empty:
#                     for val in period_df['SF_L_day']:
#                         all_data.append({
#                             'Tree': tree_id,
#                             'Species': trees_data[key]['species'],
#                             'Site': trees_data[key]['site'],
#                             'SF_L_day': val
#                         })
#                     # Calculate statistics for this tree and period
#                     tree_data = period_df['SF_L_day'].dropna()
#                     if tree_id not in cliff_tree_stats:
#                         cliff_tree_stats[tree_id] = {}
#                     cliff_tree_stats[tree_id][period] = {
#                         'mean': tree_data.mean(),
#                         'sd': tree_data.std(),
#                         'n': len(tree_data)
#                     }
        
#         if all_data:
#             plot_df = pd.DataFrame(all_data)
#             box = px.box(plot_df, x='Tree', y='SF_L_day', color='Species')
#             for trace in box.data:
#                 fig.add_trace(trace, row=1, col=col)
        
#         # Print statistics for the current period
#         print(f"\nStatistics for Period {period} ({year}):")
#         for tree_id, periods_data in cliff_tree_stats.items():
#             if period in periods_data:
#                 stats = periods_data[period]
#                 print(f"Tree {tree_id}: Mean = {stats['mean']:.1f} ± {stats['sd']:.1f} L/day, n = {stats['n']}")
    
#     fig.update_layout(height=600, width=1200, #title_text=f'Water Use Distributions (L/day) by Cliff Tree and Period - {year}',
#                       showlegend=False)
#     fig.update_yaxes(title_text='Water Use (L/day)', row=1, col=1)
#     fig.show()
#     return fig


# ##################################################################
# ###WATER USE PER LEAF AREA
# def plot_water_use_leaf_area_boxplots(trees_data, year):
#     processed = process_water_use(trees_data, year)
#     if not processed:
#         print(f"No data for year {year}")
#         return None
    
#     fig = make_subplots(rows=1, cols=3, shared_yaxes=True,
#                         subplot_titles=('Early Season', 'Dry Season', 'Late Season'))
    
#     periods = ['Early', 'Dry', 'Late']
#     tree_stats = {}  # To store statistics for each tree per period
    
#     for col, period in enumerate(periods, 1):
#         all_data = []
#         unique_trees = set(key.split('-')[0] for key in processed.keys())  # Unique tree IDs
#         for key, df in processed.items():
#             tree_id = key.split('-')[0]  # e.g., 'DF49'
#             period_df = df[df['Period'] == period]
#             if not period_df.empty:
#                 # Convert sap flow from cm³/h to dm³/h and sum to L/day
#                 sf_df = trees_data[key]['SF'].copy()
#                 sf_df['SF_dm3_h'] = sf_df['SF_complete'] / 1000.0  # cm³/h to dm³/h
#                 sf_df_daily = sf_df.resample('D')['SF_dm3_h'].sum()  # Sum to dm³/day = L/day
#                 period_sf_daily = sf_df_daily[period_df.index].dropna()  # Align with period
#                 # Convert leaf area from cm² to m²
#                 leaf_area_cm2 = trees_data[key].get('leaf_area')  # No default, raise KeyError if missing
#                 if leaf_area_cm2 is None:
#                     print(f"Warning: No leaf_area found for {key}, using 10000 cm² (1 m²) as default.")
#                     leaf_area_cm2 = 10000.0
#                 leaf_area_m2 = float(leaf_area_cm2) / 10000.0  # Convert cm² to m²
#                 if leaf_area_m2 <= 0:
#                     print(f"Warning: Invalid leaf_area for {key}, using 1 m² instead.")
#                     leaf_area_m2 = 1.0  # Avoid division by zero
#                 for val in period_sf_daily:  # val in L/day
#                     water_use_per_leaf = val / leaf_area_m2  # L/day/m²
#                     all_data.append({
#                         'Tree': tree_id,
#                         'Species': trees_data[key]['species'],
#                         'Site': trees_data[key]['site'],
#                         'Water_Use_per_Leaf': water_use_per_leaf
#                     })
#                 # Calculate statistics for this tree and period
#                 tree_data = period_sf_daily.dropna()
#                 if tree_id not in tree_stats:
#                     tree_stats[tree_id] = {}
#                 tree_stats[tree_id][period] = {
#                     'mean': tree_data.mean() / leaf_area_m2,  # Mean in L/day/m²
#                     'sd': tree_data.std() / leaf_area_m2,    # SD in L/day/m²
#                     'n': len(tree_data)
#                 }
        
#         if all_data:
#             plot_df = pd.DataFrame(all_data)
#             box = px.box(plot_df, x='Tree', y='Water_Use_per_Leaf', color='Species')
#             for trace in box.data:
#                 fig.add_trace(trace, row=1, col=col)
        
#         # Print statistics for the current period
#         print(f"\nStatistics for Period {period} ({year}) - Water Use per Leaf Area (L/day/m²):")
#         for tree_id, periods_data in tree_stats.items():
#             if period in periods_data:
#                 stats = periods_data[period]
#                 print(f"Tree {tree_id}: Mean = {stats['mean']:.2f} ± {stats['sd']:.2f} L/day/m², n = {stats['n']}")
    
#     fig.update_layout(height=600, width=1200, #title_text=f'Water Use per Leaf Area Distributions (L/day/m²) by Tree and Period - {year}',
#                       showlegend=False)
#     fig.update_yaxes(title_text='Water Use per Leaf Area (L/day/m²)', row=1, col=1)
#     fig.show()
#     return fig
# ###########################################################################################################

# ##CUMULATIVE 
# def plot_cumulative_bar(trees_data):
#     total_flow_2021 = []
#     total_flow_2022 = []
#     names_2021 = []
#     names_2022 = []
    
#     # Collect data for 2021 and 2022
#     for key, data in trees_data.items():
#         if 'SF' in data and isinstance(data['SF'], pd.DataFrame):
#             season_sf = data['SF']['SF_complete'].sum() / 1000  # convert to litres
#             name = key.split('-')[0]  # e.g., 'DF49' from 'DF49-2021'
#             if data['year'] == '2021':
#                 total_flow_2021.append(season_sf)
#                 names_2021.append(name)
#             elif data['year'] == '2022':
#                 total_flow_2022.append(season_sf)
#                 names_2022.append(name)
    
#     # Create the bar plot
#     fig = go.Figure()
#     fig.add_trace(go.Bar(
#         x=names_2021,
#         y=total_flow_2021,
#         name='2021',
#         marker_color='yellow',
#     ))
#     fig.add_trace(go.Bar(
#         x=names_2022,
#         y=total_flow_2022,
#         name='2022',
#         marker_color='lightgreen'
#     ))

#     # Add dotted lines at 2000 L
#     fig.add_hline(y=2000, line_dash="dot", line_width=0.5, line_color="black")
#     #fig.add_hline(y=8500, line_dash="dot", line_color="black")

#     fig.update_layout(barmode='group', xaxis_tickangle=-45, xaxis=dict(title='Tree Species-ID'),
#                       yaxis=dict(title='Seasonal Water Use (L)'))
#     fig.show()

#     # Generate table with seasonal differences
#     table_data = []
#     tree_ids = set(names_2021 + names_2022)
#     for tree_id in tree_ids:
#         flow_2021 = next((flow for name, flow in zip(names_2021, total_flow_2021) if name == tree_id), None)
#         flow_2022 = next((flow for name, flow in zip(names_2022, total_flow_2022) if name == tree_id), None)
#         fold_change = (flow_2022 / flow_2021) if flow_2021 and flow_2022 else None
#         table_data.append({
#             'Tree': tree_id,
#             '2021_Total_L': flow_2021 if flow_2021 is not None else 'N/A',
#             '2022_Total_L': flow_2022 if flow_2022 is not None else 'N/A',
#             'Fold_Change': f'{fold_change:.1f}x' if fold_change else 'N/A'
#         })
    
#     table_df = pd.DataFrame(table_data)
#     print(table_df.to_string(index=False))
#     return fig, table_df

