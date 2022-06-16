import os
import ee
import sys
import fire
import json
import shutil
import asyncio
import zipfile
import datetime
import urllib.request
from datetime import date
from shapely.geometry import Point

from osgeo import ogr
from osgeo import gdal
from osgeo import gdalconst

from fire_perimeter.client import generate_raster, polygonize


async def _fire_perimeter(
        latitude: float,
        longitude: float,
        date_of_interest: date,
        date_range: int,
        cloud_cover: float,
        classification_filename: str,
        rgb_filename: str,
        current_size: float,
        geojson_filename: str):

    # gcloud authentication
    try:
        ee.Initialize()  # don't re-authenticate if already signed in
    except Exception:
        ee.Authenticate(auth_mode="gcloud")
        ee.Initialize()

    # clean up existing files
    for file in [classification_filename, rgb_filename, geojson_filename]:
        if os.path.exists(file):
            os.remove(file)

    point_of_interest = Point(longitude, latitude)

    generate_raster(
        date_of_interest=date_of_interest,
        point_of_interest=point_of_interest,
        classification_geotiff_filename=classification_filename,
        rgb_geotiff_filename=rgb_filename,
        current_size=current_size,
        date_range=date_range,
        cloud_cover=cloud_cover)

    polygonize(classification_filename, geojson_filename)


def fire_perimeter(
        latitude: float = 51.5,
        longitude: float = -121.6,
        date_of_interest: str = '2021-08-23',
        date_range: int = 14,
        cloud_cover: float = 22.2,
        classification_filename: str = 'classification.tif',
        rgb_filename: str = 'rgb.tif',
        current_size: float = 90,
        geojson_filename: str = 'classification.json'):

    # TODO: ran out of time, but the "current_size" variable is a mess - since it's going to multiply it by 3 - would be better
    # to just define the bounding box here.

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_fire_perimeter(
        latitude,
        longitude,
        date.fromisoformat(date_of_interest),
        date_range,
        cloud_cover,
        classification_filename,
        rgb_filename,
        current_size,
        geojson_filename))
    loop.close()


if __name__ == '__main__':
    fn = 'prot_current_fire_points.zip'  # download fire data
    dl_path = 'https://pub.data.gov.bc.ca/datasets/2790e3f7-6395-4230-8545-04efb5a18800/' + fn
    urllib.request.urlretrieve(dl_path, fn)
    
    t = datetime.datetime.now().strftime("%Y%m%d%H%M%S")  # timestamped backup
    shutil.copyfile(fn, 'prot_current_fire_points_' + t + '.zip')
    zipfile.ZipFile(fn).extractall()   

    # Open Shapefile
    Shapefile = ogr.Open('prot_current_fire_points.shp')
    print(Shapefile)
    layer = Shapefile.GetLayer()
    layerDefinition = layer.GetLayerDefn()
    feature_count = layer.GetFeatureCount()
    spatialRef = layer.GetSpatialRef()

    def records(layer):
        for i in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(i)
            yield json.loads(feature.ExportToJson())

    features = records(layer)
    feature_names, feature_ids = [], []
    biggest_size, biggest_ID, biggest_lat, biggest_lon = 0, None, None, None
    for f in features: # print(f.keys())
        for key in f.keys():
            if key == 'properties':
                fk = f[key]
                fire_size = float(fk['CURRENT_SI'])
                if(fire_size > biggest_size):
                    biggest_size = fire_size
                    biggest_ID = fk # ['FIRE_NUMBE']
                    biggest_lat = fk['LATITUDE']
                    biggest_lon = fk['LONGITUDE']
    print("biggest fire:", biggest_ID['FIRE_NUMBE'], biggest_ID)
    print("size:", biggest_size)
    print("lat:", biggest_lat)
    print("lon:", biggest_lon)

    if len(sys.argv) > 1:
        fire.Fire(fire_perimeter)
    else:
        # call with different parameters
        fire_perimeter(latitude=biggest_lat,
                       longitude=biggest_lon, 
                       date_of_interest=datetime.datetime.now().strftime("%Y-%m-%d"),
                       current_size=biggest_size)
