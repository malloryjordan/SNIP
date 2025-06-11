# ======================================================================================
# Copyright 2014  Swiss Federal Institute of Aquatic Science and Technology
#
# This file is part of SNIP (Sustainable Network Infrastructure Planning)
# SNIP is used for determining the optimal degree of centralization for waste
# water infrastructures. You find detailed information about SNIP in Eggimann et al. (2014).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
# The Djikstra and a* algorithm are adapted from Hetland (2010).
# The algorithm is developed for Python 2.7 and ArcGIS 10.2
#
# Literature
# ----------
# Eggimann Sven, Truffer Bernhard, Maurer Max (2015): To connect or not to connect?
# Modelling the optimal degree of centralisation for wastewater infrastructures.
# Water Research, XY, .....
#
# Hetland M.L. (2010): Python Algorithms. Mastering Basic Algorithms in the Python Language. apress.
#
# Contact:   maj0062@auburn.edu
# Version    1.0
# Date:      3.30.2015
# Author:    Mallory Jordan
# ======================================================================================

# Imports
import os
import subprocess

def experiment(outListFolder, fc_SewerCost, fc_wwtpOpex, fc_wwtpCapex, EW_Q):
    '''
    This function runs the SNIP model with a given list of parameters and saves results in a unique folder.

    Input Arguments
    outListFolder       --    Output folder
    fc_SewerCost        --    Used for Sensitivity Analysis to shift cost curve of seweres (e.g. 10 % = 0.1)
    fc_wwtpOpex         --    Used for Sensitivity Analysis to shift cost curve of WWTP operation (e.g. 10 % = 0.1)
    fc_wwtpCapex        --    Used for Sensitivity Analysis to shift cost curve of WWTP replacement (e.g. 10 % = 0.1)
    EW_Q = 0.3785       --    Per capita wastewater production. This factor must be the same as for the GIS-Files. [m3 / day]
    '''

    # Base script path
    script_path = "C:\Users\maj0062\Documents\GitHub\SNIP\Python_Files\SNIP_arcgis.py"

    # Define ranges of values for parameters
    output_folders = [f"C:/Users/maj0062/Documents/TEMP/LowndesCounty/SNIP_output{i}" for i in range(1, 6)]
    fc_SewerCost_values = [-0.2, -0.1, 0.0, 0.1, 0.2]
    fc_wwtpOpex_values = [-0.2, -0.1, 0.0, 0.1, 0.2]
    fc_wwtpCapex_values = [-0.2, -0.1, 0.0, 0.1, 0.2]
    EW_Q_values = [0.3, 0.35, 0.3785, 0.4, 0.45]

    # Iterate over combinations of parameters
    for i in range(len(output_folders)):
        output_folder = output_folders[i]
        fc_SewerCost = fc_SewerCost_values[i]
        fc_wwtpOpex = fc_wwtpOpex_values[i]
        fc_wwtpCapex = fc_wwtpCapex_values[i]
        EW_Q = EW_Q_values[i]

        # Ensure the output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Construct the command to run the script with arguments
        command = [
            "python", script_path,
            output_folder, str(fc_SewerCost), str(fc_wwtpOpex), str(fc_wwtpCapex), str(EW_Q)
        ]

        print(f"Running script with output folder: {output_folder}, fc_SewerCost: {fc_SewerCost}, "
              f"fc_wwtpOpex: {fc_wwtpOpex}, fc_wwtpCapex: {fc_wwtpCapex}, EW_Q: {EW_Q}")

        # Run the script
        subprocess.run(command)
