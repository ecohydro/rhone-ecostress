import pandas as pd
import numpy as np
import xarray as xa
from pathlib import Path
import src.data.ecostress_io as eio
import src.data.ecostress_stack as es
import src.data.era_stack_resample as esr
import rioxarray
import sys
import geopandas as gpd
import json

def get_aoi_grid_from_rivers():
    xa.set_options(display_style='html')
    n_partitions = 8 # set in the files
    root_path = Path("/raid/scratch/rave/rhone-ecostress/rhone-ecostress-data")
    reanalysis_path = Path(root_path, "era5-download.nc")
    bounds_tuple = (4, 42, 7, 47)
    xmin, ymin, xmax, ymax = bounds_tuple  # hardcoding since concattenating 1000s of ecostress files with different overlaps hangs

    rivers_df = gpd.read_file(Path(root_path, "europe_rivers/eu_river.shp"))

    rivers_df['R_ID'] = rivers_df['R_ID'].apply(int).apply(str)

    france_rivers_df = rivers_df.cx[xmin:xmax, ymin:ymax]

    aoi = es.filter_countries_for_france_aoi(root_path)

    aoi.crs = france_rivers_df.crs # setting crs for aoi

    et_path = Path(root_path, "ECO3ETPTJPL")

    tempdir_inst_uncertainty = root_path/"tmp-inst_uncertainty-nearest"
    whole_tif_etinst_uncertainty_paths, csv_etinst_uncertainty_paths, xml_etinst_uncertainty_paths = eio.separate_by_pattern(et_path, "*ETinstUncertainty*.tif")

    x = eio.read_ecostress_scene(whole_tif_etinst_uncertainty_paths[0])
    resolution = x.rio.resolution()
    x.close()
    aoi_grid = es.rasterize_buffer_river_df(france_rivers_df, resolution, buffer=5000)
    return aoi_grid


# france_rivers_df.to_file(root_path/"france_rivers.geojson", driver="GeoJSON")