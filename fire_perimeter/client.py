import numpy
import requests
from typing import Tuple
from datetime import date, timedelta
import struct
import json
from google.oauth2.credentials import Credentials
import ee
from numpy import ndarray
from osgeo import gdal, ogr, osr
from pyproj import Geod
from shapely.geometry import shape
from fire_perimeter.active_fire import apply_classification_rule, apply_cloud_cover_threshold
from fire_perimeter.auth import jwt_token


def write_geotiff(data, bbox, filename, params={}):
    # https://developers.google.com/earth-engine/apidocs/ee-image-getthumburl
    base_params = {'min': 0, 'max': 1, 'dimensions': 1024, 'region': bbox, 'format': 'GEO_TIFF'}

    url = data.getDownloadUrl(dict(base_params, **params))
    response = requests.get(url, timeout=60)

    print(response.status_code)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f'{filename} written')


def create_in_memory_band(data: ndarray, cols, rows, projection, geotransform):
    """ Create an in memory data band to represent a single raster layer.
    See https://gdal.org/user/raster_data_model.html#raster-band for a complete
    description of what a raster band is.
    """
    mem_driver = gdal.GetDriverByName('MEM')

    dataset = mem_driver.Create('memory', cols, rows, 1, gdal.GDT_Byte)
    dataset.SetProjection(projection)
    dataset.SetGeoTransform(geotransform)
    band = dataset.GetRasterBand(1)
    band.WriteArray(data)

    return dataset, band


def read_scanline(band, yoff):
    """ Read a band scanline (up to the y-offset), returning an array of values.

    A raster (image) may consist of multiple bands (e.g. for a colour image, one may have a band for
    red, green, blue, and alpha).
    A scanline, is a single row of a band.

    band, definition: https://gdal.org/user/raster_data_model.html#raster-band
    fetching a raster band: https://gdal.org/tutorials/raster_api_tut.html#fetching-a-raster-band
    """
    scanline = band.ReadRaster(xoff=0, yoff=yoff,
                               xsize=band.XSize, ysize=1,
                               buf_xsize=band.XSize, buf_ysize=1,
                               buf_type=gdal.GDT_Float32)
    return struct.unpack('f' * band.XSize, scanline)


def polygonize(geotiff_filename, geojson_filename):
    classification = gdal.Open(geotiff_filename, gdal.GA_ReadOnly)
    band = classification.GetRasterBand(1)

    projection = classification.GetProjection()
    geotransform = classification.GetGeoTransform()
    rows = band.YSize
    cols = band.XSize

    # generate mask data
    mask_data = numpy.empty([rows, cols], bool)
    for y_row_index in range(rows):
        row = read_scanline(band, y_row_index)
        for index, cell in enumerate(row):
            mask_data[y_row_index, index] = cell ==1
    mask_ds, mask_band = create_in_memory_band(mask_data, cols, rows, projection, geotransform)

    # Create a GeoJSON layer.
    geojson_driver = ogr.GetDriverByName('GeoJSON')
    dst_ds = geojson_driver.CreateDataSource(geojson_filename)
    dst_layer = dst_ds.CreateLayer('fire')
    field_name = ogr.FieldDefn("fire", ogr.OFTInteger)
    field_name.SetWidth(24)
    dst_layer.CreateField(field_name)

    # Turn the rasters into polygons.
    gdal.Polygonize(band, mask_band, dst_layer, 0, [], callback=None)

    # Ensure that all data in the target dataset is written to disk.
    dst_ds.FlushCache()
    # Explicitly clean up (is this needed?)

    del dst_ds, classification, mask_ds
    print(f'{geojson_filename} written')


def generate_raster(date_of_interest: date, point_of_interest: Tuple, classification_geotiff_filename: str, rgb_geotiff_filename: str):
    """
    Step back 14 days from the the of interest, and classify an area around the point of interest.
    """
    # construct jwt token
    token = jwt_token()

    # from google.oauth2.credentials import Credentials - only works with python 3.8.* or earlier.
    credentials = Credentials(token=token)
    ee.Initialize(credentials)

    # https://developers.google.com/earth-engine/guides/python_install#syntax

    # very unlikely to have a good image for any given date, so we'll go back 14 days...
    date_range = 14
    start_date = date_of_interest - timedelta(days=date_range)

    print(f'start date: {start_date}')

    data = apply_cloud_cover_threshold(
        ee.Date(f'{start_date.isoformat()}T00:00', 'Etc/GMT-8'),
        date_range, # date range: [t1, t1 + N_DAYS]
        22.2 # cloud cover max %
        )

    fires = apply_classification_rule(data)

    # ee.Geometry.BBox(west, south, east, north)
    lat = point_of_interest[0]
    lon = point_of_interest[1]
    west = lon-0.3
    south = lat-0.2
    east = lon+0.3
    north = lat+0.2
    
    bbox = ee.Geometry.BBox(west, south, east, north)
    # print(bbox)

    write_geotiff(fires, bbox, classification_geotiff_filename)
    write_geotiff(data, bbox, rgb_geotiff_filename, {'bands': ['B12', 'B11', 'B9']})
    

def calculate_area(filename):
    # TODO: you have to do some magic here, to re-project to something that uses meters
    print(filename)
    driver = ogr.GetDriverByName('GeoJSON')
    ds = driver.Open(filename, gdal.GA_ReadOnly)
    layer = ds.GetLayer()
    source_projection = layer.GetSpatialRef()
    target_projection = osr.SpatialReference()
    # target_projection.SetWellKnownGeogCS('NAD83')
    # TODO: use a better target projection!! I just thumb sucked this one!
    target_projection.ImportFromEPSG(3857)
    transform = osr.CoordinateTransformation(source_projection, target_projection)
    area_total = 0
    for feature in layer:
        transformed = feature.GetGeometryRef()
        transformed.Transform(transform)
        area_total += transformed.GetArea()
    print(f'Total area: {area_total} m^2, {area_total/10000} hectares')

    del ds


def calculate_area_fail(filename):
    print(filename)
    with open(filename) as f:
        js = json.load(f)
    total_area = 0
    for feature in js['features']:
        polygon = shape(feature['geometry'])
        geod = Geod(ellps="WGS84")
        area, perim = geod.geometry_area_perimeter(polygon)
        total_area += area
        # print(f'area: {area}')
        # print(f'perim: {perim}')
    print(f'total_area {total_area}')


def generate_data(date_of_interest: date, point_of_interest: Tuple):
    """
    Generate a geojson file for the fire classification, and a geotiff file for the RGB image.
    """
    classification_geotiff_filename = f'output/binary_classification_{date_of_interest.isoformat()}.tif'
    geojson_filename=f'output/binary_classification_{date_of_interest.isoformat()}.json'

    generate_raster(
        date_of_interest=date_of_interest,
        point_of_interest=point_of_interest,
        classification_geotiff_filename=classification_geotiff_filename,
        rgb_geotiff_filename=f'output/rgb_{date_of_interest.isoformat()}.tif')

    polygonize(classification_geotiff_filename, geojson_filename)

    calculate_area(geojson_filename)
    


if __name__ == '__main__':
    # date_of_interest = date(2021, 8, 23)
    date_of_interest = date(2021, 8, 9)
    point_of_interest = (51.5, -121.6) # lat, lon

    for _ in range(1):
        generate_data(date_of_interest, point_of_interest)
        date_of_interest += timedelta(days=1)

    # once you have a polygon, you can calculate the area: https://pyproj4.github.io/pyproj/stable/examples.html#geodesic-area