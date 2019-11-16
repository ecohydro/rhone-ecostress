import pandas as pd
import numpy as np
import xarray as xa
from pathlib import Path
import src.data.ecostress_io as eio
import rioxarray
import sys
import geopandas as gpd
import json
import dask
from dask.distributed import Client

def filter_countries_for_france_aoi(root_path):
    with open(f"{root_path}/geo-countries/archive/countries.geojson", "rb") as f:
        all_countries_geojson = json.loads(f.read())


    for i in all_countries_geojson['features']:
        if i['properties']['ADMIN'] == "France":
            france_geo = i

    del all_countries_geojson

    france_gdf = gpd.GeoDataFrame.from_features([france_geo]).explode()

    france_gdf[france_gdf.area==max(france_gdf.area)].plot()

    aoi = france_gdf[france_gdf.area==max(france_gdf.area)]
    
    # xmin, ymin, xmax, ymax = aoi.total_bounds
    
    return aoi


def clip_scenes_if_not_clipped(source_paths, bounds_tuple, filter_nan, tempdir):
    """
    Looks in the clip dir for clipped scenes or resampled scenes. if neither exist, creates the clipped scenes.
    """
    clipped_scene_paths = [Path(p) for p in tempdir.glob("*clipped*")]
    resampled_scene_paths = [Path(p) for p in tempdir.glob("*resampled*")]

    if clipped_scene_paths == [] and resampled_scene_paths == []:
        print("starting clipping")
        client = Client()

        batches = eio.batches_from(source_paths, 8)

        batch_results = []

        for batch in batches:

            batch_result = dask.delayed(eio.clip_and_save)(batch, bounds_tuple, filter_nan, outDir=tempdir)
            batch_results.append(batch_result)

        result_futures = client.compute(batch_results, scheduler='processes')

        clipped_scene_batches = [i.result() for i in result_futures]# gets rid of None that denotes too little scene overlap
        clipped_scene_paths = []
        for batch in clipped_scene_batches:
            for path in batch:
                if path != None:
                    clipped_scene_paths.append(Path(path))
        client.restart()
        print("done clipping")
        return clipped_scene_paths
    else:
        return clipped_scene_paths

def rasterize_buffer_river_df(france_rivers_df, resolution, buffer=5000):
    """
    river lines must start out in 4326 projection. buffer units in meters
    """
    buffered_france_rivers_df = france_rivers_df.to_crs(epsg=2154)\
                                                .buffer(buffer)\
                                                .to_crs(epsg=4326) # buffers by 5000 meters
    france_rivers_df['geometry'] = buffered_france_rivers_df
    aoi_grid = eio.gdf_to_dataarray(france_rivers_df, france_rivers_df.crs, resolution)
    return aoi_grid

def resample_if_not_resampled(aoi_grid, tempdir, resampling_method):
    """
    resamples clipped scenes, assuming they exist and only if the resampled scenes don't exist. 
    """
    clipped_scene_paths = [Path(p) for p in tempdir.glob("*clipped*")]
    resampled_scene_paths = [Path(p) for p in tempdir.glob("*resampled*")]
    if resampled_scene_paths == []:
        print("start resampling")
        client = Client()
        batches = eio.batches_from(clipped_scene_paths, n_partitions)

        def wrapper(paths, aoi_grid, tempdir, path_id):
            return_paths = []
            for path in paths:
                with eio.read_mask_ecostress_scene(path) as x:
                    y = eio.resample_xarray_to_basis(x, aoi_grid, resampling_method)
                    return_paths.append(eio.write_tmp(y, tempdir, path_id))
            return return_paths

        all_results = []
        for batch in batches:
            sub_result = dask.delayed(wrapper)(batch, aoi_grid, tempdir, "resampled")
            all_results.append(sub_result)

        result_future = client.compute(all_results, scheduler="processes")

        resampled_scene_batches = [i.result() for i in result_future]
        resampled_scene_paths = []
        for batch in resampled_scene_batches:
            for path in batch:
                if path != None:
                    resampled_scene_paths.append(Path(path))
        print("done resampling")
        client.restart()
        return resampled_scene_paths
    else:
        return resampled_scene_paths
    
def clip_resample_ecostress_product(source_paths, bounds_tuple, filter_nan, tempdir, resampling_method):
    clipped_scene_paths = clip_scenes_if_not_clipped(source_paths, bounds_tuple, filter_nan, tempdir)
    resolution = eio.read_ecostress_scene(source_paths[0]).rio.resolution()
    aoi_grid = rasterize_buffer_river_df(france_rivers_df, resolution, 5000)
    resampled_scene_paths = resample_if_not_resampled(aoi_grid, tempdir, resampling_method)
    resampled_data_arrays = eio.read_scenes(resampled_scene_paths, chunks = {"band":1})
    ecostress_product_tseries = xa.concat(resampled_data_arrays, dim="date").sortby('date')
    return ecostress_product_tseries