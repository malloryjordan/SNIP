from shiny import App, render, ui, reactive
from shinywidgets import render_widget, output_widget
import folium
import os
import subprocess
import requests
import tempfile
import pandas as pd
import SNIP_open

###### Get SNIP code from Github ######
Github_SNIP_open = "https://github.com/malloryjordan/SNIP/blob/master/Python_Files_open/SNIP_open.py"

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
                    {"test": "Use Test Data", "upload": "Upload My Own"},
                    selected="test"
                ),
                ui.panel_conditional("input.data_mode == 'upload'",
                                     ui.input_file("street_file", "Street Shapefile (.zip)"),
                                     ui.input_file("building_file", "Building Shapefile (.zip)"),
                                     ui.input_file("dem_file", "DEM (.zip)"),
                                     ),
                ui.panel_conditional("input.data_mode == 'test'",
                                     ui.p("Running with built-in test data.")
                                     ),
                ui.input_action_button("run_preprocess", "Run Preprocessing"),
                ui.output_ui("map_preview"),
                style="padding: 5px"
            ),
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
                ui.download_button("download_outputs", "Download Outputs"),
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

    # Temporary folder for outputs
    temp_dir = tempfile.mkdtemp(prefix="snip_outputs_")

    # Load either test data or uploaded data
    @reactive.Calc
    def load_data():
        data = {}
        if input.data_mode() == "test":
            # Test data (make sure these paths exist in your repo)
            street_file = "test_data/street_simplified_WhiteHall.shp"
            building_file = "test_data/CorelogicParcel_point_Lowndes_WhiteHall.shp"
            dem_file = "test_data/lowndes_dem_90_utm_WhiteHall.shp"
        else:
            # Uploaded data
            street_file = input.street_file()
            building_file = input.building_file()
            dem_file = input.dem_file()

            street_file = street_file[0]["datapath"] if street_file else None
            building_file = building_file[0]["datapath"] if building_file else None
            dem_file = dem_file[0]["datapath"] if dem_file else None

        data["streets"] = gpd.read_file(street_file) if street_file else None
        data["buildings"] = gpd.read_file(building_file) if building_file else None
        data["dem"] = gpd.read_file(dem_file) if dem_file else None

        return data

    # Run full SNIP when button clicked
    @reactive.effect
    @reactive.event(input.run_full)
    def run_snip():
        data = load_data()
        streets = data["streets"]
        buildings = data["buildings"]
        dem = data["dem"]

        try:
            # Import and run SNIP (your SNIP_open.py must define run_snip_model)
            from SNIP_open import run_snip_model
            stats = run_snip_model(streets, buildings, dem)

            # Update outputs
            output.log_output.set_text("Model ran successfully!")
            if isinstance(stats, pd.DataFrame):
                output.stats_table.set_table(stats)
            else:
                df = pd.DataFrame([stats])
                output.stats_table.set_table(df)

        except Exception as e:
            output.log_output.set_text(f"Error running model: {e}")

    # Map of input data
    @output
    @render.widget
    def map_preview():
        data = load_data()  # Your reactive function returning streets, buildings, dem
        streets_gdf = data["streets"]
        buildings_gdf = data["buildings"]
        dem_gdf = data["dem"]

        # Create folium map
        m = folium.Map(location=[32.5, -85.0], zoom_start=12, tiles="OpenStreetMap")

        # Add streets
        if streets_gdf is not None and not streets_gdf.empty:
            folium.GeoJson(
                streets_gdf,
                name="Streets",
                style_function=lambda x: {"color": "black", "weight": 2}
            ).add_to(m)

        # Add buildings with marker cluster
        if buildings_gdf is not None and not buildings_gdf.empty:
            cluster = MarkerCluster(name="Buildings").add_to(m)
            for _, row in buildings_gdf.iterrows():
                if row.geometry and row.geometry.geom_type == "Point":
                    folium.Marker([row.geometry.y, row.geometry.x]).add_to(cluster)

        # Add DEM points if available
        if dem_gdf is not None and not dem_gdf.empty:
            for _, row in dem_gdf.iterrows():
                if row.geometry and row.geometry.geom_type == "Point":
                    folium.CircleMarker(
                        [row.geometry.y, row.geometry.x],
                        radius=3,
                        color="red",
                        fill=True,
                        fill_opacity=0.6
                    ).add_to(m)

        folium.LayerControl().add_to(m)

        return m

    # Map of output data
    @output
    @render.ui
    def create_map():
        data = load_data()
        m = folium.Map(location=[32.5, -85.0], zoom_start=10)
        folium.TileLayer("OpenStreetMap").add_to(m)

        if data["streets"] is not None:
            folium.GeoJson(data["streets"], name="Streets", style_function=lambda x: {"color": "black"}).add_to(m)
        if data["buildings"] is not None:
            folium.GeoJson(data["buildings"], name="Buildings", style_function=lambda x: {"color": "blue"}).add_to(m)
        if data["dem"] is not None:
            folium.GeoJson(
                data["dem"],
                name="DEM Points",
                marker=folium.CircleMarker(radius=2, color="green", fill=True, fill_opacity=0.7),
            ).add_to(m)

        folium.LayerControl().add_to(m)
        return m._repr_html_()

    # Stats table
    @output
    @render.table
    def stats_table():
        return [
            {"Metric": "Degree of Centralization", "Value": "NA"},
            {"Metric": "Total Cost", "Value": "NA"},
        ]

    # Download button for outputs
    @output
    @render.download(filename=lambda: "snip_outputs.zip")
    def download_outputs():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zf.write(file_path, arcname=file)
        buf.seek(0)
        return buf

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