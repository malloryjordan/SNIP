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

## You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#    
# The Djikstra and a* algorithm are adapted from Hetland (2010).
# The algorithm is developed for Python 2.7 and ArcGIS 10.2
#
# Literature
# ==========
# Eggimann Sven, Truffer Bernhard, Maurer Max (2015): To connect or not to connect? 
# Modelling the optimal degree of centralisation for wastewater infrastructures.   
# Water Research, 84, 218-231. Link: http://www.sciencedirect.com/science/article/pii/S004313541530107X
#
# Hetland M.L. (2010): Python Algorithms. Mastering Basic Algorithms in the Python Language. apress.
#
# Contact:   sven.eggimann@eawag.ch
# Version    1.0
# Date:      1.07.2015
# Author:    Eggimann Sven
# ======================================================================================
# The SNIP model was updated and modified for use in rural Alabama in 2025.
# For detailed information see Jordan et al. (in prep).

# The model was modified for Python 3.11 and ArcGIS Pro 3.4

# Author:   Mallory Jordan
# Date:     June 11, 2025
# Contact:  maj0082@auburn.edu
# ======================================================================================
import os, sys, time               # General Imports
import gc; gc.disable()            # Don't allow garbage collection

start = time.perf_counter()   # Start script timer

# SNIP Imports    
from SNIP_functions_open import *                           # Import open source functions
from SNIP_astar_open import *                                    # Import a* functions
from SNIP_costs_open import *                                    # Import cost functions

# Prompt user for input paths
in_street = input("Enter the path to the street shapefile: ").strip('"').strip("'")
buildings = input("Enter the path to the building shapefile: ").strip('"').strip("'")
inDHM = input("Enter the path to the DEM point shapefile: ").strip('"').strip("'")
outListFolder = input("Enter the path to the output folder: ").strip('"').strip("'")

# Ensure output folder exists
outListFolder = outListFolder.replace("\\", "/") + "/"
os.makedirs(outListFolder, exist_ok=True)

demAlreadyReadOut = 1 if inDHM else 0

# Read shapefiles
streets_gdf = gpd.read_file(in_street)
buildings_gdf = gpd.read_file(buildings)
dem_gdf = None
if demAlreadyReadOut:
    dem_gdf = gpd.read_file(inDHM)

# Get CRS from streets as the reference
crs = streets_gdf.crs

# Make sure all GeoDataFrames have a CRS
if streets_gdf.crs is None:
    streets_gdf = streets_gdf.set_crs(crs)
if buildings_gdf.crs is None:
    buildings_gdf = buildings_gdf.set_crs(crs)
elif buildings_gdf.crs != crs:
    buildings_gdf = buildings_gdf.to_crs(crs)
if dem_gdf is not None:
    if dem_gdf.crs is None:
        dem_gdf = dem_gdf.set_crs(crs)
    elif dem_gdf.crs != crs:
        dem_gdf = dem_gdf.to_crs(crs)

# Model parameters (based parameters as in Eggimann et al. 2015 and Jordan et al. in prep)
# ========================================================================
  
# Sewer related
maxTD = 4                                   # [m] Maximum trench depth
minTD = 0.9                                 # [m] Min trench depth
minSlope = 1                                # [%] Criteria of minimum slope without pumps needed
stricklerC = 85                             # [m^1/3 s^-1] Stricker Coefficient
EW_Q = 0.3785                               # [m3 / day] 1 EW is equal to 378.5 liter (~ 100 gallons). This factor must be the same as for the GIS-Files and in unts of [m3 / day].
    
#Cost related
resonableCostsPerEW = 4220                  # [currency] Reasonable Costs
pricekWh = 0.12                             # [currency / kWh] price per kWh of electricity
pumpingYears = 30                           # [years] Pump lifespan
discountYearsSewers = 50                    # [years] Pipe lifespan
wwtpLifespan = 25                           # [years] WWTP lifespan
interestRate = 2.75                         # [%] Real interest rate
operationCosts = 5                          # [currency / meter] operation costs per meter pipe per year, denoted as operationCostsPerYear in the cost script
pumpInvestmentCosts = 500                   # [currency] Fix costs of pumps
fc_SewerCost = 0.0                          # [-20% - 20%] Used for Sensitivity Analysis to shift cost curve  (e.g. 10 % = 0.1)
fc_wwtpOpex = 0.0                           # [-20% - 20%] Used for Sensitivity Analysis to shift cost curve  (e.g. 10 % = 0.1)
fc_wwtpCapex = 0.0                          # [-20% - 20%] Used for Sensitivity Analysis to shift cost curve
        
# Algorithm related
f_street = 5.0                              # [-] Factor to set How close the sewer follow the road network
f_merge = 2.4                               # [-] Factor do determine how the WWTPS are merged.
f_topo = 1.2                                # [-] Factor weighting the dem graph creation for the a* algorithm
    
neighborhood = 180                          # [m] Defines how large the neighbourhood for the a-Star Algorithm (Needs to be at least twice the raster size)
AggregateKritStreet = 50                    # [m] How long the distances on the roads can be in maximum be before they get aggregated on the street network (must not be 0)
border = 3000                               # [m] How large the virtual dem borders are around topleft and bottom
tileSize = 50                               # [m] for selection of density based starting node
    
pipeDiameterPrivateSewer = 0.1             # [m] Cost Assumptions private sewers: Pipe Diameter
avgTDprivateSewer = 0.9                    # [m] Cost Assumptions private sewers: Average Trench Depth
    
# ArcGIS Representation related
drawHouseConnections = 1                    # 1: House connections are drawn in ArcGIS, 0: House Connections are not drawn in ArcGIS
interestRate = float(interestRate) / 100.0  # Reformulate real interest rate

# Add parameters into List for SNIP Algorithm
InputParameter = [minTD, maxTD, minSlope, f_merge, resonableCostsPerEW, neighborhood, f_street, pricekWh, pumpingYears, discountYearsSewers, interestRate, stricklerC, EW_Q,  wwtpLifespan, operationCosts, pumpInvestmentCosts,  f_topo, fc_SewerCost, fc_wwtpOpex, fc_wwtpCapex]

outListStep_point = outListFolder + "aggregated_nodes.shp"
outPathPipes = outListFolder + "sewers.shp"
outList_nodes = outListFolder + "nodes.shp"
outList_pumpes = outListFolder + "pumpes.shp"
outList_WWTPs = outListFolder + "WWTPs.shp"
aggregatetStreetFile = outListFolder  + "streetGraph.shp"
allNodesPath = outListFolder + "allNodes.shp"
outPath_StartNode = outListFolder + "startnode.shp"

# Create .txt files for SNIP Calculation and data preparation
buildPoints = readBuildingPoints(buildings, crs)                                                                 # Read out buildings. read ID from Field

anzNumberOfConnections = len(buildPoints)                                                                   # used for setting new IDs
rasterPoints, rasterSize = readRasterPoints(inDHM, anzNumberOfConnections, crs)                                  # Read out DEM
rasterSizeList = [rasterSize]                                                                               # Store raster size

nearPoints = readClosestPointsAggregate(buildings, crs)                                                          # Read the near_X, near_Y -points of the buildings into a list
aggregatetPoints, buildings = aggregate(nearPoints, AggregateKritStreet, outListStep_point, minTD, crs)          # Aggregate houses on the street and create point file (sewer inlets).
updateFieldStreetInlets(outListStep_point, crs)                                                                  # Update field for the sewer inlets
writefieldsStreetInlets(outListStep_point, aggregatetPoints, crs)                                                # Write to shapefile
splitStreetwithInlets(in_street, outListStep_point, aggregatetStreetFile, crs)                                   # Split street network with the sewer inlets
updatefieldsPoints(aggregatetStreetFile, crs)                                                                    # Update fields in splitted street and add StreetID, the height to each points is assigned from closest DEM-Point
streetVertices = readOutAllStreetVerticesAfterAggregation(aggregatetStreetFile, rasterPoints, rasterSize, crs)
aggregatetPoints = correctCoordinatesAfterClip(aggregatetPoints, streetVertices)                           # Because after ArcGIS Clipping slightly different coordinate endings, change them in aggregatetPoints (different near-analysis)
forSNIP, aggregatetPoints = assignStreetVertAggregationMode(aggregatetPoints, streetVertices, minTD)        # Build dictionary with vertexes and save which buildings are connected to which streetInlet   
drawAllNodes(streetVertices, allNodesPath, crs)                                                                  # Write out all relevant nodes
updateFieldNode(allNodesPath, crs)
writefieldsAllNodes(allNodesPath, streetVertices, crs)
edges = createStreetGraph(aggregatetStreetFile, crs)                                                             # Create list with edges from street network
edgeList = addedgesID(edges, streetVertices)                                                                # Assign id and distance to edges
streetGraph = appendStreetIDandCreateGraph(edgeList)                                                        # Create graph
aggregatetPoints = assignHighAggregatedNodes(aggregatetPoints, rasterPoints, rasterSize, minTD)             # Assign High to Aggregated Nodes
forSNIP = addBuildingsFarFromRoadTo(aggregatetPoints, forSNIP)                                              # Add all buildings far from the road network 
_, startnode, startX, startY = densityBasedSelection(aggregatetPoints, tileSize)                            # Select start node with highest density  

writeTotxt(outListFolder, "inputParameters", InputParameter)                                                # Write to .txt files
writeTotxt(outListFolder, "rasterPoints", rasterPoints)                                                     # Write to .txt files
writeTotxt(outListFolder, "rastersize", rasterSizeList)                                                     # Write to .txt files
writeTotxt(outListFolder, "buildPoints", buildPoints)                                                       # Write to .txt files
writeTotxt(outListFolder, "forSNIP", forSNIP)                                                               # Write to .txt files
writeTotxt(outListFolder, "aggregatetPoints", aggregatetPoints)                                             # Write to .txt files
writeTotxt(outListFolder, "forSNIP", forSNIP)                                                               # Write to .txt files
writeTotxt(outListFolder, "streetVertices", streetVertices)                                                 # Write to .txt files
writeTotxt(outListFolder, "edgeList", edgeList)                                                             # Write to .txt files
writeToDoc(outListFolder, "streetGraph", streetGraph)                                                       # Write to .txt files
writeTotxt(outListFolder, "buildings", buildings)                                                           # Write to .txt files

print("...ready for SNIP Calculation")
     
# Run SNIP
ExpansionTime, MergeTime, sewers, pointsPrim, WWTPs, wtpstodraw, pumpList, edgeList, completePumpCosts, completeWWTPCosts, completePublicPipeCosts, totalSystemCosts, buildings, buildPoints, aggregatetPoints = SNIP(0, outListFolder, 1, forSNIP, 1, streetGraph, startnode, edgeList, streetVertices, rasterSize, buildPoints, buildings, rasterPoints, InputParameter, aggregatetPoints)

# Calculate cost of private sewers
totCostPrivateSewer = costsPrivateSewers(buildings, buildPoints, pipeDiameterPrivateSewer, avgTDprivateSewer, discountYearsSewers, interestRate, operationCosts, fc_SewerCost) # Calculate costs of Private Sewers
        
inputStartNod = [[startnode, startX, startY]]           
startNodeToDraw = createPolyPoint(inputStartNod, outPath_StartNode, crs)     # Draw the wtps in ArcGIS
writeStartnode(outPath_StartNode, startNodeToDraw, crs)                      # Write out startnode
            
# Draw the graphs in ArcGIS, DrawHouse Connections
list_GIS = primResultGISList(drawHouseConnections, sewers, pointsPrim, streetVertices, buildings, buildPoints, rasterPoints, edgeList)
writeOutPipes(outListFolder, "info_pipes", list_GIS)
    
createPolyLine(list_GIS, outPathPipes, crs)                              # Draw Pipes in ArcGIS
wwtoArDrawn = createPolyPointWWTP(wtpstodraw, outList_WWTPs, crs)        # Draw the wtps in ArcGIS
            
if wwtoArDrawn == 1:
    writeWWTPs(outList_WWTPs, wtpstodraw, crs)

#Draw the nodes in ArcGIS
createPolyPoint(pointsPrim, outList_nodes, crs)
writefieldsNodes(outList_nodes, pointsPrim, crs)
            
#Draw Pumps
draw = createPolyPointPump(pumpList, outList_pumpes, crs)
if draw == True:
    writeFieldNodesPUMPS(outList_pumpes, pumpList, crs)
    
# Statistics
totCostPrivateSewer = costsPrivateSewers(buildings, buildPoints, pipeDiameterPrivateSewer, avgTDprivateSewer, discountYearsSewers, interestRate, operationCosts, fc_SewerCost) # Calculate costs of Private Sewers
        
# Sum whole System Costs
totSystemCostsNoPrivate = completePumpCosts  + completeWWTPCosts + completePublicPipeCosts
totSystemCostsWithPrivate = completePumpCosts  + completeWWTPCosts + completePublicPipeCosts + totCostPrivateSewer
        
# Calculate number of neighbours (density)
densityRaster, startnode, startX, startY = densityBasedSelection(aggregatetPoints, tileSize)        # Select startnode with highest density
for entry in densityRaster:
    if startX >= densityRaster[entry][0] and startX < (densityRaster[entry][0] + tileSize) and startY > (densityRaster[entry][1] - tileSize) and startY <= densityRaster[entry][1]:
        nrOfNeighboursDensity = densityRaster[entry][2]
        break

# Write out statistics
statistics = getStatistics(startnode, sewers, pointsPrim, aggregatetPoints, WWTPs, edgeList, nrOfNeighboursDensity, EW_Q, buildings, buildPoints)     

statistics.append(f"completePumpCosts: {completePumpCosts}")                    # Append costs to statistics.
statistics.append(f"completeWWTPCosts: {completeWWTPCosts}")                    # Append costs to statistics.
statistics.append(f"completePublicPipeCosts: {completePublicPipeCosts}")              # Append costs to statistics.
statistics.append(f"totCostPrivateSewer: {totCostPrivateSewer}")                  # Append costs to statistics.
statistics.append(f"totSystemCostsNoPrivate: {totSystemCostsNoPrivate}")              # Append costs to statistics.
statistics.append(f"totSystemCostsWithPrivate: {totSystemCostsWithPrivate}")            # Append costs to statistics.
writeTotxt(outListFolder, "statistics", statistics)     # Append costs to statistics.

# Calculate and print time required to complete script
end = time.perf_counter()
runtime = end - start

if runtime < 60:
    print(f'Runtime: {runtime:.2f} seconds')
elif runtime < 3600:  # Less than one hour
    minutes = runtime / 60
    print(f'Runtime: {minutes:.2f} minutes')
else:
    hours = runtime / 3600
    print(f'Runtime: {hours:.2f} hours')