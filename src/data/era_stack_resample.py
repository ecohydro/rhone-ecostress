from rasterio.enums import Resampling
import os
import xarray as xa
import rioxarray
import numpy as np
import src.data.ecostress_io as eio
import pandas as pd

def read_resampled_era(root_path, dataset_filename = "Daily_VPD_10am-3pm_Paris_Time_Resampled.nc"):
    dataset_name = dataset_filename.split(".")[0]
    resampled_vpd_path = os.path.join(root_path, dataset_filename)
    if os.path.isfile(resampled_vpd_path):
        resampled_vpd_ds = xa.open_dataset(resampled_vpd_path, chunks = {"time": 1, "y": 6101, "x": 6558})
        print(dataset_name, " done reading")
        return resampled_vpd_ds
    
def resample_era_daily(reanalysis_path, root_path, project_source):
    
    dataset_name = os.path.basename(reanalysis_path).split(".")[0]
    resampled_vpd_path = os.path.join(root_path, dataset_filename)
    
    print("starting calculation of vpd and resampling...")

    vpd = read_era_land_and_vpd(reanalysis_path)

    daytime_mask = np.isin(vpd.time.dt.hour, [9, 10, 11, 12, 13, 14])

    daytime_vpd = vpd.isel(time=daytime_mask)

    daytime_vpd_daily = daytime_vpd.resample(time="1D").mean()

    daytime_vpd_daily = daytime_vpd_daily.rio.set_crs(4326)

    print("I need this much RAM to reproject...", str(np.float32(1).itemsize * np.prod([395, 6101, 6558]) / 1e9))

    resampled_vpd_da = daytime_vpd_daily.rio.reproject_match(project_source, resampling = Resampling.bilinear)

    resampled_vpd.name = dataset_name

    eio.write_netcdf(resampled_vpd_da, resampled_vpd_path)

    del resampled_vpd_da

    resampled_vpd_ds = xa.open_dataset(resampled_vpd_path, chunks = {"time": 1, "y": 6101, "x": 6558})
    print(dataset_name, " done processing")

    return resampled_vpd_ds

def reproject_era_hourly_rhone(reanalysis_path, dest_path, project_source, hours_to_keep=[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]):
    
    dataset_name = "Hourly_VPD_6am-8pm_utc_Resampled.nc"
    
    print("starting calculation of vpd and resampling...")

    vpd = read_era_land_and_vpd(reanalysis_path)

    daytime_mask = np.isin(vpd.time.dt.hour, hours_to_keep)

    daytime_vpd = vpd.isel(time=daytime_mask)

    daytime_vpd = daytime_vpd.rio.set_crs(4326)

    print("I need this much RAM to reproject...", str(np.float32(1).itemsize * np.prod(daytime_vpd.shape) / 1e9))

    resampled_vpd_da = daytime_vpd.rio.reproject_match(project_source, resampling = Resampling.bilinear)

    resampled_vpd.name = dataset_name

    eio.write_netcdf(resampled_vpd_da, dest_path)

    del resampled_vpd_da

    resampled_vpd_ds = xa.open_dataset(dest_path, chunks = {"time": 1, "y": 6101, "x": 6558})
    print(dataset_name, " done processing")

    return resampled_vpd_ds


def reproject_era_hourly_san_pedro(reanalysis_path, dest_path, aoi_grid):
    
    dataset_name = "Hourly_VPD_6am-8pm_utc_Resampled.nc"
    
    print("starting calculation of vpd and resampling...")

    vpd = read_era_land_and_vpd(reanalysis_path)
    
    vpd = vpd.rio.set_crs(4326)

    print("I need this much RAM to reproject...", str(np.float32(1).itemsize * np.prod(vpd.shape) / 1e9))

    resampled_vpd_da = vpd.rio.reproject_match(aoi_grid, resampling = Resampling.bilinear)

    resampled_vpd_da.name = dataset_name

    return resampled_vpd_da
    
def read_era_land_and_vpd(reanalysis_path):
    
    met_dataset = xa.open_dataset(reanalysis_path, chunks = {"time": 1})

    met_dataset['vpd'] = eio.vapor_deficit(met_dataset['t2m']-273.15,met_dataset['d2m']-273.15)\
            .sel(time=slice("2019-03-01", "2019-06-30"))

    met_dataset = met_dataset.rio.set_crs(4326)

    return met_dataset['vpd']
    
def resample_if_not_resampled():
    """
    Untested, this was used in nb to make huge un subsetted vpd files but should be adapted so that ecostress time subsetting and clipping to rhone occurs first. Now we work from the clipped and subsetted vpd files.
    """
    raise NotImplemented
    dest_path = root_path/"Hourly_VPD_10am-3pm_Paris_Time_Resampled.nc"
    if dest_path.exists() is not True:
        resampled_vpd_ds = esr.reproject_era_hourly(reanalysis_path, dest_path, etinst_tseries[0], hours_to_keep=[9, 10, 11, 12, 13, 14])
        resampled_vpd_da = resampled_vpd_ds["Hourly_VPD_10am-3pm_Paris_Time_Resampled"]
    else:
        esr.read_era_land_and_vpd(dest_path)

    resampled_vpd_da = resampled_vpd_da.transpose(...,"y") # puts y last
    resampled_vpd_ds.time.values
    
def intersect_et_vpd_times(et, vpd):
    """
    Tested after removing/merging duplicates in et array
    """
    et_times = pd.to_datetime(np.array(et['date']))
    et_time_mask = np.isin(vpd.time.values, et_times)
    vpd_da_et_times = vpd.sel(time=et_time_mask)
    return vpd_da_et_times
    
def clip_subset_save_vpd():
    """
    needs args sorted out to be made modular
    """
    raise NotImplemented

    july_clipped_et_t_path = root_path/"July-Hourly_VPD_clipped_et_times.nc"
    august_clipped_et_t_path = root_path/"August-Hourly_VPD_clipped_et_times.nc"
    sept_clipped_et_t_path = root_path/"September-Hourly_VPD_clipped_et_times.nc"

    if july_clipped_et_t_path.exists() and august_clipped_et_t_path.exists() and sept_clipped_et_t_path.exists():
        print("all vpd files clipped to rhone river bounding box and subsetted to ecostress overpass times")

    else:

        #aggregating inst to hourly to compare with era vpd?

        def wm2_to_mm_per_hour(wm2):
            lh_vap = 1/2454000 # at 20 C, we can adjust this based on era temp?
            sec_hour = 60*60
            return wm2*lh_vap*sec_hour # units of mm per hour

        # june = root_path/"June-Hourly_VPD_10am-3pm_Paris_Time_Resampled.nc" #no june data for ecostress
        july = root_path/"July-Hourly_VPD_10am-3pm_Paris_Time_Resampled.nc"
        august = root_path/"August-Hourly_VPD_10am-3pm_Paris_Time_Resampled.nc"
        sept = root_path/"September-Hourly_VPD_10am-3pm_Paris_Time_Resampled.nc"


        july_da = xa.open_dataset(july)
        august_da = xa.open_dataset(august)
        sept_da = xa.open_dataset(sept)


        july_vpd_et_times = intersect_et_vpd_times(et_concat_ds,july_da)

        august_vpd_et_times = intersect_et_vpd_times(et_concat_ds,august_da)

        september_vpd_et_times = intersect_et_vpd_times(et_concat_ds,sept_da)

        july_vpd_clipped_et_times = july_vpd_et_times.rio.clip(geodf.geometry.apply(mapping), geodf.crs, drop=True, invert=False)

        august_vpd_clipped_et_times = august_vpd_et_times.rio.clip(geodf.geometry.apply(mapping), geodf.crs, drop=True, invert=False)

        sept_vpd_clipped_et_times = september_vpd_et_times.rio.clip(geodf.geometry.apply(mapping), geodf.crs, drop=True, invert=False)

        july_vpd_clipped_et_times.to_netcdf(july_clipped_et_t_path)
        august_vpd_clipped_et_times.to_netcdf(august_clipped_et_t_path)
        sept_vpd_clipped_et_times.to_netcdf(sept_clipped_et_t_path)