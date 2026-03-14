#kernel rw_data
#Libraries 
from pathlib import Path
from csv import DictReader, reader

#Paths 
path_cwd = Path.cwd()
path_output_graphs = str(path_cwd) + '/Output_graphs/'
path_graphs=path_output_graphs+'Graphs/'
path_latex = str(path_cwd.parents[0]) + '/TEX_file/Figures/'
path_predawn_regression = path_graphs + 'Predawn_Soil_Regression/'

# Import the utility functions
from utils.read_and_create_dict import read_and_create_dict
from utils.clean_psy import clean_psy_in_dict
from utils.rainfall import plot_cumulative_rainfall_with_periods
from utils.van_genuchten import calculate_and_store_matric_potential, plot_soil_moisture_and_matric_potential
from utils.predawn import calculate_predawn_water_potential, plot_predawn_scatter
from utils.predawn import plot_hydraulic_disconnection, compare_hydraulic_disconnection

# Read files, create/update the dictionary, and clean PSY data
trees_data, paths = read_and_create_dict()
trees_data = clean_psy_in_dict(trees_data)

# Calculate dry periods and generate cumulative rainfall plots
figures_rainfall, dry_periods = plot_cumulative_rainfall_with_periods(trees_data) 

# Calculate matric potentials (Ψ_matric)and store in trees_data
trees_data = calculate_and_store_matric_potential(trees_data) 

# Calculate predawn water potentials (Ψ_pd) and store in trees_data
trees_data = calculate_predawn_water_potential(trees_data)

# Plot Soil and PD water potential as a regression and do a Kruskal-Wallis test on the nightime differences
# This step will print the Kruskal-Wallis test results and a 2x2 grid plot of all four trees (DF27,ES50,DF49,ES48)
# These analysis is split into pre-dry, dry, and post-dry periods but we might need to re-define (maybe 2 or 3 dry periods)
plot_metrics_2021 = plot_hydraulic_disconnection(trees_data, '2021')
plot_metrics_2022 = plot_hydraulic_disconnection(trees_data, '2022')
comp_metrics = compare_hydraulic_disconnection(trees_data,path_output=path_predawn_regression)

# # Access dry periods
# print(dry_periods['2021'])  # List of tuples for 2021
# print(dry_periods['2022'])  # List of tuples for 2022