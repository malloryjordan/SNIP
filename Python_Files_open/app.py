from shiny import App, render, ui, reactive
from shinywidgets import render_widget, output_widget
import folium
import os
import subprocess
import requests
import tempfile
import pandas as pd

###### Get SNIP code from Github ######


###### UI ######
app_ui = ui.page_fluid(
    # Fixed header
    ui.tags.header(
        ui.h1("Wastewater Treatment Infrastructure Optimization", style="margin-top: 5px; margin-bottom: 10px; color: white; background-color: #2c3e50; padding: 15px;"),
    ),

    # Navigation panels
    ui.navset_tab(
        ui.nav_panel("Info / About",
            ui.div(
                ui.h2("Welcome to SNIP"),
                ui.p("SNIP (Sustainable Network Infrastructure Planning) model..."),
                ui.p("Data inputs, preprocessing, model parameters, outputs..."),
                style="padding: 5px"
            )
        ),
        ui.nav_panel("Data Upload & Preprocessing",
            ui.div(
                ui.input_radio_buttons(
                    "data_mode", "Choose data source:",
                    {"test": "Use Test Data", "upload": "Upload My Own"}
                ),
                ui.input_file("street_file", "Street Shapefile (.zip)"),
                ui.input_file("building_file", "Building Shapefile (.zip)"),
                ui.input_file("dem_file", "DEM (.tif)"),
                ui.input_action_button("SNIP_prep", "Run Preprocessing"),
                ui.output_ui("map_preview"),
                style="padding: 5px"
            )
        ),
        ui.nav_panel("Model Parameters & Run SNIP",
            ui.div(
                ui.input_slider("f_street", "Factor to set How close the sewer follow the road network", 0, 5, 2.4, step=0.1),
                ui.input_slider("f_merge", "Factor do determine how the WWTPS are merged", 0, 5, 2.4, step=0.1),
                ui.input_slider("f_topo", "Factor weighting the topography in distance calculations", 0, 5, 1.2, step=0.1),
                ui.input_action_button("SNIP_open", "Run SNIP"),
                ui.output_text("log_output"),
                style="padding: 5px"
            )
        ),
        ui.nav_panel("Explore Outputs",
            ui.div(
                ui.output_ui("map_outputs"),
                ui.output_table("stats_table"),
                ui.output_text("downloads_text"),
                style="padding: 5px"
            )
        )
    ),
    # Include Google Fonts
    ui.tags.head(
        ui.tags.link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap"
        ),
        ui.tags.style("""
            body {
                font-family: 'Montserrat', sans-serif;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: 'Montserrat', sans-serif;
            }
        """)
    ),
)

###### SERVER ######
def server(input, output, session):

    # Load either test data or uploaded data
    @reactive.Calc
    def load_data():
        data = {}
        if input.data_mode() == "test":
            street_file = r"/TEMP/SNIP_test/input_data/street_simplified_WhiteHall.shp"
            building_file = r"/TEMP/SNIP_test/input_data/CorelogicParcel_point_Lowndes_WhiteHall.shp"
            dem_file = r"/TEMP/SNIP_test/input_data/lowndes_dem_90_utm_WhiteHall.shp"
        else:
            street_file = input.street_file()
            building_file = input.building_file()
            dem_file = input.dem_file()

            street_file = street_file[0]["datapath"] if street_file else None
            building_file = building_file[0]["datapath"] if building_file else None
            dem_file = dem_file[0]["datapath"] if dem_file else None

        data["streets"] = gpd.read_file(street_file) if street_file else None
        data["buildings"] = gpd.read_file(building_file) if building_file else None
        data["dem"] = dem_file  # keep tif path for rasterio/leafmap

        return data

    # Run full SNIP when button clicked
    @reactive.Effect
    def run_snip():
        if not input.run_full():
            return

        data = load_data()
        streets = data["streets"]
        buildings = data["buildings"]
        dem = data["dem"]

        try:
            # Call SNIP functions

            # Update outputs
            log_output.set(f"SNIP ran successfully! Degree of centralization: {degCen}")
            stats_table.set([{"Metric": "Degree of Centralization", "Value": degCen}])

            # Save outputs for download
            streets.to_file("output_streets.shp")
            gpd.GeoDataFrame(buildings).to_file("output_buildings.shp")

        except Exception as e:
            log_output.set(f"Error running SNIP: {e}")

    # Create output map
    @output
    @render_widget
    def create_map():
        m = folium.Map(location=[32.5, -85.0], zoom_start=10)
        folium.TileLayer("OpenStreetMap").add_to(m)

        if data["streets"] is not None:
            m.add_gdf(data["streets"], layer_name="Streets", style={"color": "black"})
        if data["buildings"] is not None:
            m.add_gdf(data["buildings"], layer_name="Buildings", style={"color": "blue"})
        if data["dem"] is not None:
            try:
                m.add_raster(data["dem"], layer_name="DEM", colormap="terrain")
            except Exception as e:
                print(f"DEM load error: {e}")

        # Return as HTML widget
        return m.to_streamlit()  # folium backend doesn't require ipywidgets

    # Stats table
    @output
    @render.table
    def stats_table():
        return [
            {"Metric": "Degree of Centralization", "Value": "NA"},
            {"Metric": "Total Cost", "Value": "NA"},
        ]

    # Download output data
    @output
    @render.text
    def downloads_text():
        return "Download links will appear here after running SNIP."

    # Logs output
    @output
    @render.text
    def log_output():
        return "Logs and errors will be shown here."

###### RUN APP ######
app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app("app.py", host="127.0.0.1", port=8000, reload=True)