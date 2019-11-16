from rasterio.enums import Resampling
import os
import xarray as xa
import rioxarray
import numpy as np

def read_or_process(root_path, dataset_filename = "Daily_VPD_10am-3pm_Paris_Time_Resampled.nc"):
    dataset_name = dataset_filename.split(".")[0]
    resampled_vpd_path = os.path.join(root_path, dataset_filename)
    if os.path.isfile(resampled_vpd_path):
        resampled_vpd_ds = xa.open_dataset(resampled_vpd_path, chunks = {"time": 1, "y": 6101, "x": 6558})
        print(dataset_name, " done reading")
        return resampled_vpd_ds
    
    else:
        print("starting calculation of vpd and resampling...")

        reanalysis_path = Path(root_path, "era5-download.nc")

        met_dataset = xa.open_dataset(reanalysis_path, chunks = {"time": 1, "latitude": 39, "longitude": 41})

        met_dataset['vpd'] = eio.vapor_deficit(met_dataset['t2m']-273.15,met_dataset['d2m']-273.15)

        met_dataset = met_dataset.rio.set_crs(4326)

        vpd = met_dataset['vpd']

        daytime_mask = np.isin(vpd.time.dt.hour, [9, 10, 11, 12, 13, 14])

        daytime_vpd = vpd.isel(time=daytime_mask)

        daytime_vpd_daily = daytime_vpd.resample(time="1D").mean()

        daytime_vpd_daily = daytime_vpd_daily.rio.set_crs(4326)

        print("I need this much RAM to reproject...", str(np.float32(1).itemsize * np.prod([395, 6101, 6558]) / 1e9))

        resampled_vpd_da = daytime_vpd_daily.rio.reproject_match(et_tseries[0], resampling = Resampling.bilinear)

        resampled_vpd.name = dataset_name

        eio.write_netcdf(resampled_vpd_da, resampled_vpd_path)

        del resampled_vpd_da

        resampled_vpd_ds = xa.open_dataset(resampled_vpd_path, chunks = {"time": 1, "y": 6101, "x": 6558})
        print(dataset_name, " done processing")
        
        return resampled_vpd_ds