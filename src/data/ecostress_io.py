from pathlib import Path
import xarray as xa
import pandas as pd

def separate_extensions(folder_path, tif_pattern="*.tif"):
    """
    Tif pattern is its own arg because dif layers need to be seperated
    """
    csv_paths = list(folder_path.glob("*.csv"))
    xml_paths = list(folder_path.glob("*.xml"))
    tif_paths = list(folder_path.glob(tif_pattern))
    return tif_paths, csv_paths, xml_paths

def path_date_to_coord(filename, da):
    """
    Takes a file path and data array and puts the time info in a new data array date coordinate as datetime
    """
    filetime = filename.split("_")[-2][3:] #different for each layer unfortunately.
    date_utc = pd.to_datetime(filetime, format="%Y%j%H%M%S")
    da['date'] = date_utc
    da.name = filename
    return da

def read_mask_ecostress_scene(tif_path):
    """
    Tested on ET_daily layer
    """
    filename = tif_path.name
    print("reading " + filename)
    et = xa.open_rasterio(tif_path, chunks={"band":1})
    et = path_date_to_coord(filename, et)
    et = et.where(~et.isin(-1e+13))
    return et
