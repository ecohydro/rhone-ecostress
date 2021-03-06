from pathlib import Path
import xarray as xa
import pandas as pd
import rioxarray
import numpy as np
from geocube.api.core import make_geocube
import geopandas as gpd
from rasterio.enums import Resampling
import dask
import os

def separate_by_pattern(folder_path, tif_pattern="*.tif"):
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

def read_ecostress_scene(tif_path):
    """
    Tested on ET_daily layer
    """
    filename = tif_path.name
    x = xa.open_rasterio(tif_path)
    x = path_date_to_coord(filename, x)
    return x

def read_mask_ecostress_scene(tif_path):
    """
    Tested on ET_daily layer
    """
    x = read_ecostress_scene(tif_path)
    x.where((~x.isin(-1e+13))&(~x.isin(-999.))&(~x.isin(-99999.))) # no data values for quality and et product layers
    return x

def read_scenes(tif_paths, chunks={"band":1}):
    scenes = []
    for path in tif_paths:
        da = xa.open_rasterio(path, chunks=chunks)
        da = path_date_to_coord(path.name, da)
        scenes.append(da)
    return scenes

def clip_and_save(paths, bounds_tuple, filter_nan, outDir):
    scene_paths = []
    for path in paths:
        da = read_mask_ecostress_scene(path)
        scene_da = clip_box_scene(da, bounds_tuple, filter_nan=filter_nan)
        if scene_da is not None:
            path = write_tmp(scene_da, outDir, "clipped")
            da.close()
            del da
            scene_da.close()
            del scene_da
            scene_paths.append(path)
    return scene_paths 

def compute_nan_check(da):
    nanbool = np.isnan(da.sel(band=1))
    nanper = np.sum(nanbool) / da.size
    if nanper > .9:
        da.close()
        return None
    else:
        return da
       
def clip_box_scene(da, bounds_tuple, filter_nan=False):
    """
    Will clip if bounds intersect, if not returns None.
    """
    xmin, ymin, xmax, ymax = bounds_tuple # overide gdf bounds
    try:
        da_clipped = da.rio.clip_box(
            minx=xmin,
            miny=ymin,
            maxx=xmax,
            maxy=ymax
        )
        if filter_nan == True:
            return compute_nan_check(da_clipped)
        else:
            return da_clipped
    
    except rioxarray.exceptions.NoDataInBounds:
        print("The whole scene falls outside the aoi bounds, skipping and returning None")
        return None
    except rioxarray.exceptions.OneDimensionalRaster:
        print("The data array below is one dimensional for some reason, returning None")
        return None

def resample_and_save(da_list, aoi_grid, outDir="/scratch/rave/tmp"):
    resampled_paths = []
    for da in da_list:
        x = resample_xarray_to_basis(da, aoi_grid, outDir)
        da.close()
        del da
        y = write_tmp(x, "resampled")
        resampled_paths.append(y)
    return resampled_paths
    
def check_all_nan(da_clipped):
    """
    After clipping, som ecostress scenes will have no valid data in the clip area but will have NaN values in 
    the clipped area (either they were clouds or completed the rectangular array). This returns None if all nan.
    """
    # this runs super slow in a for loop since it has to read everything in at once 
    # and hold ~ 20 gigs in mem just for the Rhone.
    prop_nan = np.sum(np.isnan(da_clipped)) / da_clipped.size
    if prop_nan > .1: # keep data array if it has a good amount of good data in it.
        return da_clipped
    else:
        return None
    
def match_da_lists(da_list1, da_list2):
    """
    Gets the dataarrays that have a corresponding datarray with the same date in another list.
    Returns both as new lists. the basis list should go first (ETinst)
    """
    new_da_list1 = []
    new_da_list2 = []
    for da1 in da_list1:
        date = da1.date.values
        for da2 in da_list2:
            if da2.date.values == date:
                new_da_list1.append(da1)
                new_da_list2.append(da2)
    return new_da_list1, new_da_list2

def get_date_df(da_list):
    """
    Gets list of dates from list of DataArrays as pandas df
    """
    
    dates = []
    for i in da_list:
        dates.append(i.date.values)

    date_df = pd.DataFrame(dates)
    date_df['date'] = date_df[0:]
    return date_df.drop(date_df.columns[0], axis=1)

def gdf_to_dataarray(gdf, crs, resolution):
    """
    df should be a geodataframe with a geometry column
    crs in format {'init': 'epsg:4326'}
    resolution in format (0.000629777416967, -0.000629777416967)
    """
    envelope = gdf.unary_union.envelope
    rasterizeable_aoi = gpd.GeoDataFrame(crs = crs, geometry=[envelope])
    rasterizeable_aoi['value'] = 1 # allows us to make non empty dataset, required for resampling
    return make_geocube(vector_data=rasterizeable_aoi, resolution=resolution)['value']

def resample_xarray_to_basis(da, basis, resampling_method):
    """
    Resamples xarray dataarray to snap it to the aoi grid created from
    gdf_todataset. Can be run on multiple ecostress rasters acquired from different orbits.
    returns the result with an updated path attribute.
    """
    reprojected_da = da.rio.reproject_match(basis, resampling=resampling_method)
    return reprojected_da

def write_tmp(da, outDir, path_id):
    if da is None:
        return None
    else:
        out_path = os.path.join(outDir, "".join(da.name.split(".")[:-1]) + f"-{path_id}.tif")
        da.attrs['path'] = out_path
        da.rio.to_raster(out_path)
        da.close()
        del da
        return out_path
    
def write_netcdf(da, outPath):
    da.attrs['path'] = outPath
    da.to_netcdf(outPath)
    return outPath
    
def batches_from(items, maxbaskets=25):
    baskets = [[] for _ in range(maxbaskets)] # in Python 3 use range
    for i, item in enumerate(items):
        baskets[i % maxbaskets].append(item)
    return list(filter(None, baskets))

def saturation_vapor_pressure(temperature):
    """
    Empirical equation from campbell and Norman p.41
    """
    a = .611 # kPa
    b = 17.052
    c = 240.97 # Celsius
    return a*np.e**((b * temperature) / (temperature + c))

def vapor_deficit(temperature, dew_point):
    """
    Temperatures must be in celsius
    """
    svp = saturation_vapor_pressure(temperature)
    ambient_vapor_pressure = saturation_vapor_pressure(dew_point)
    return svp-ambient_vapor_pressure


