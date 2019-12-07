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
import dask
from dask.distributed import Client
import matplotlib.pyplot as plt
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

l3qa_path = Path(root_path, "ECO3ANCQA")
et_path = Path(root_path, "ECO3ETPTJPL")
esi_path = Path(root_path, "ECO4ESIPTJPL")
l2_path = Path(root_path, "ECO2")

tempdir_daily = root_path/"tmp-daily-nearest"
whole_tif_etdaily_paths, csv_et_paths, xml_et_paths = eio.separate_by_pattern(et_path, "*ETdaily*.tif")

tempdir_inst = root_path/"tmp-inst-nearest"
whole_tif_etinst_paths, csv_etinst_paths, xml_etinst_paths = eio.separate_by_pattern(et_path, "*ETinst_*.tif")

tempdir_inst_uncertainty = root_path/"tmp-inst_uncertainty-nearest"
whole_tif_etinst_uncertainty_paths, csv_etinst_uncertainty_paths, xml_etinst_uncertainty_paths = eio.separate_by_pattern(et_path, "*ETinstUncertainty*.tif")

tempdir_l3qa = root_path/"tmp-l3qa"
whole_tif_l3qa_paths, csv_qa_paths, xml_qa_paths = eio.separate_by_pattern(l3qa_path)

tempdir_l2qa = root_path/"tmp-l2qa"
whole_tif_l2qa_paths, csv_l2qa_paths, xml_l2qa_paths = eio.separate_by_pattern(l2_path, "*SDS_QC*.tif")

tempdir_l2cloud = root_path/"tmp-l2cloud"
whole_tif_l2cloud_paths, csv_l2cloud_paths, xml_l2cloud_paths = eio.separate_by_pattern(l2_path, "*SDS_CloudMask*.tif")

x = eio.read_ecostress_scene(whole_tif_etinst_uncertainty_paths[0])
resolution = x.rio.resolution()
x.close()
aoi_grid = es.rasterize_buffer_river_df(france_rivers_df, resolution, buffer=5000)

from rasterio.enums import Resampling
# etdaily_tseries_paths = es.clip_resample_ecostress(whole_tif_etdaily_paths, bounds_tuple, aoi_grid, filter_nan=True, tempdir=tempdir_daily, resampling_method=Resampling.nearest)
etinst_tseries_paths = es.clip_resample_ecostress(whole_tif_etinst_paths, bounds_tuple, aoi_grid, filter_nan=True, tempdir=tempdir_inst, resampling_method=Resampling.nearest)
# etinst_uncertainty_tseries_paths = es.clip_resample_ecostress(whole_tif_etinst_uncertainty_paths, bounds_tuple, aoi_grid, filter_nan=True, tempdir=tempdir_inst_uncertainty , resampling_method=Resampling.nearest)
# l3qa_tseries_paths = es.clip_resample_ecostress_no_dask(whole_tif_l3qa_paths, bounds_tuple, aoi_grid, filter_nan=True, tempdir=tempdir_l3qa, resampling_method=Resampling.nearest)
# l2qa_tseries_paths = es.clip_resample_ecostress_no_dask(whole_tif_l2qa_paths, bounds_tuple, aoi_grid, filter_nan=True, tempdir=tempdir_l2qa, resampling_method=Resampling.nearest)
# l2cloud_tseries_paths = es.clip_resample_ecostress_no_dask(whole_tif_l2cloud_paths, bounds_tuple, aoi_grid, filter_nan=True, tempdir=tempdir_l2cloud, resampling_method=Resampling.nearest)

etinst_da_list = eio.read_scenes(etinst_tseries_paths, chunks = {"band":1})
# l3qa_tseries, etinst_da_list = es.read_and_concat(l3qa_tseries_paths, etinst_da_list)
# l2qa_tseries, etinst_da_list = es.read_and_concat(l2qa_tseries_paths, etinst_da_list)
# l2cloud_tseries, etinst_da_list = es.read_and_concat(l2cloud_tseries_paths, etinst_da_list)
# etinst_uncertainty_tseries, etinst_da_list = es.read_and_concat(etinst_uncertainty_tseries_paths, etinst_da_list)
etinst_tseries = xa.concat(etinst_da_list, dim="date").sortby('date')

dataset_name = "Hourly_VPD_6am-8pm_utc_Resampled.nc"

print("starting calculation of vpd and resampling...")

vpd = esr.read_era_land_and_vpd(reanalysis_path)
hours_to_keep = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
daytime_mask = np.isin(vpd.time.dt.hour, hours_to_keep)

daytime_vpd = vpd.isel(time=daytime_mask)
daytime_vpd = daytime_vpd.sel(time=slice("2018-06-01", "2018-06-30"))
daytime_vpd = daytime_vpd.rio.set_crs(4326)

daytime_vpd = daytime_vpd.rename({"latitude":"y", "longitude":"x"})
source_da = etinst_tseries[0]
print("starting resampling")
def wrapper(da, source_da, resampling= Resampling.bilinear):
    da = da.rio.set_crs(4326)
    return da.rio.reproject_match(source_da, resampling = resampling)
resampled_vpd = wrapper(daytime_vpd, source_da)
resampled_vpd.name = dataset_name
dest_path = root_path/"June-Hourly_VPD_10am-3pm_Paris_Time_Resampled.nc"
print("saving")
del resampled_vpd.attrs # can't serialize rio crs and can't delete
eio.write_netcdf(resampled_vpd, dest_path)

del resampled_vpd

print("done")
