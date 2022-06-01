import os
import math
import shutil
import tempfile
import asyncio
from datetime import date, timedelta
import struct
import json
import numpy
import requests
from google.oauth2.credentials import Credentials
import ee
from numpy import ndarray
from osgeo import gdal, ogr, osr
from pyproj import Geod
from decouple import config
from shapely.geometry import shape, Point
from fire_perimeter.active_fire import apply_classification_rule, apply_cloud_cover_threshold
from fire_perimeter.auth import jwt_token
from fire_perimeter.persistence import persist_polygon
from fire_perimeter.store import get_client


def write_geotiff(data, bbox, filename, params={}, pixels=(1024, 1024)):
    # https://developers.google.com/earth-engine/apidocs/ee-image-getthumburl
    # the largest dimension we're allowed to use is 10000 - that's all good and well that you want 10000x10000, pixels
    # but according to docmentation the maximum size is 32 MB
    # Assuming out TIFF has 3 bands, and 4 bytes per band, that's 12 bytes per pixel
    bytes_per_pixel = 12
    max_bytes = 32 * 1024 * 1024
    max_pixels = max_bytes / bytes_per_pixel
    requested_pixels = pixels[0] * pixels[1]
    ratio = math.sqrt(max_pixels) / math.sqrt(requested_pixels)

    if ratio < 1.0:
        # we're exceeding the max size, scale it down.
        dimensions = (int(pixels[0]*ratio),
                      int(pixels[1]*ratio))
    else:
        # we're not exceeding the max size, all good.
        dimensions = pixels

    base_params = {'min': 0, 'max': 1, 'dimensions': dimensions,
                   'region': bbox, 'format': 'GEO_TIFF'}

    url = data.getDownloadUrl(dict(base_params, **params))
    response = requests.get(url, timeout=60)

    # print(response.status_code)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
    else:
        print(f'failed to write {filename}')
        # print(f'{filename} written')


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
            mask_data[y_row_index, index] = cell == 1
    mask_ds, mask_band = create_in_memory_band(
        mask_data, cols, rows, projection, geotransform)

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


def calculate_bounding_box(point_of_intereset: Point, current_size: float):
    """
    Somewhat verbose function, but easy to read
    """
    # current size is in hectares, and let's assume it's grown some:
    adjusted_hectares = current_size * \
        float(config('bounding_box_multiple', 3))
    # width in meters
    width_in_m = adjusted_hectares * 100
    # but we're measuring from the starting point, so we only need half of that
    distance = width_in_m / 2

    lon = point_of_intereset.x
    lat = point_of_intereset.y
    g = Geod(ellps='WGS84')

    # north
    n = g.fwd(lon, lat, 0, distance)
    # south
    s = g.fwd(lon, lat, 180, distance)
    # east
    e = g.fwd(lon, lat, 90, distance)
    # west
    w = g.fwd(lon, lat, 270, distance)

    west = w[0]
    south = s[1]
    east = e[0]
    north = n[1]

    return (west, south, east, north)


def generate_raster(date_of_interest: date,
                    point_of_interest: Point,
                    classification_geotiff_filename: str,
                    rgb_geotiff_filename: str,
                    current_size: float,
                    date_range: int,
                    cloud_cover: float):
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
    start_date = date_of_interest - timedelta(days=date_range)

    print(f'start date: {start_date}')

    data = apply_cloud_cover_threshold(
        ee.Date(f'{start_date.isoformat()}T00:00', 'Etc/GMT-8'),
        date_range,  # date range: [t1, t1 + N_DAYS]
        cloud_cover  # cloud cover max %
    )

    fires = apply_classification_rule(data)

    # ee.Geometry.BBox(west, south, east, north)
    # Latitude is denoted by Y (northing) and Longitude by X (Easting)
    lon = point_of_interest.x
    lat = point_of_interest.y
    # # for a super big fire - longitude +/- 0.3, latitude +/- 0.2
    # # TODO: figure this out using hectare estimate. (current_size)
    # west = lon-0.3
    # south = lat-0.2
    # east = lon+0.3
    # north = lat+0.2
    west, south, east, north = calculate_bounding_box(
        point_of_interest, current_size)

    bbox = ee.Geometry.BBox(west, south, east, north)

    # attempt to figure out how many pixels we need to ask for to get 20m resolution:
    g = Geod(ellps='WGS84')
    _, _, width = g.inv(west, lat, east, lat)
    _, _, height = g.inv(lon, south, lon, north)
    width = int(width / 20)
    height = int(height / 20)

    write_geotiff(fires, bbox, classification_geotiff_filename,
                  pixels=(width, height))
    write_geotiff(data, bbox, rgb_geotiff_filename,
                  {'bands': ['B12', 'B11', 'B9']}, (width, height))


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
    # https://spatialreference.org/ref/epsg/nad83-utm-zone-10n/
    target_projection.ImportFromEPSG(26910)
    transform = osr.CoordinateTransformation(
        source_projection, target_projection)
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


def copy_file_local(source, target):
    print(f'saving {target}')
    if os.path.exists(target):
        os.remove(target)
    shutil.copy(source, target)


async def generate_data(date_of_interest: date, point_of_interest: Point, identifier: str, current_size: float):
    """
    Generate a geojson file for the fire classification, and a geotiff file for the RGB image.
    """

    with tempfile.TemporaryDirectory() as temporary_path:
        # We use a temporary file to generate raster files and polygons. When we're done, we're throwing away
        # all the files, since we're only persisting the resultant polygons.

        classification_geotiff_filename = os.path.join(
            temporary_path, f'{identifier}_{date_of_interest.isoformat()}_binary_classification.tif')
        geojson_filename = os.path.join(
            temporary_path, f'{identifier}_{date_of_interest.isoformat()}_binary_classification.json')
        rgb_geotiff_filename = os.path.join(
            temporary_path, f'{identifier}_{date_of_interest.isoformat()}_rgb.tif')

        date_range = int(config('date_range', 14))
        cloud_cover = float(config('cloud_cover', 22.2))
        generate_raster(
            date_of_interest=date_of_interest,
            point_of_interest=point_of_interest,
            classification_geotiff_filename=classification_geotiff_filename,
            rgb_geotiff_filename=rgb_geotiff_filename,
            current_size=current_size,
            date_range=date_range,
            cloud_cover=cloud_cover)

        polygonize(classification_geotiff_filename, geojson_filename)

        calculate_area(geojson_filename)

        try:
            object_store_filename = f'{identifier}/{identifier}_{date_of_interest.isoformat()}_rgb.tif'
            object_store_path = f'fire_perimeter/{object_store_filename}'
            async with get_client() as (client, bucket):
                with open(rgb_geotiff_filename, 'rb') as f:
                    print(f'Uploading to S3... {object_store_path}')
                    await client.put_object(Bucket=bucket, Key=object_store_path, Body=f)
        except Exception as e:
            print(f'Could not store RGB image: {e}')

        try:
            persist_polygon(geojson_filename, identifier,
                            date_of_interest, point_of_interest,
                            date_range, cloud_cover, object_store_filename)
        except Exception as e:
            print(f'Could not persist polygon: {e}')

        if config('save_local', 'false') == 'true':
            if not os.path.exists('output'):
                os.mkdir('output')
            copy_file_local(rgb_geotiff_filename,
                            os.path.join(os.getcwd(),
                                         'output', f'{identifier}_{date_of_interest.isoformat()}_rgb.tif'))
            copy_file_local(classification_geotiff_filename,
                            os.path.join(os.getcwd(),
                                         'output', f'{identifier}_{date_of_interest.isoformat()}_binary_classification.tif'))

        # cleanup (do I need this? or will using temp directory be enough?)
        for filename in [classification_geotiff_filename, geojson_filename, rgb_geotiff_filename]:
            if os.path.exists(filename):
                os.remove(filename)


def get_active_fires():
    url = 'https://openmaps.gov.bc.ca/geo/pub/ows'
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typeName': 'pub:WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_PNTS_SP',
        'outputFormat': 'json',
        'srsName': 'EPSG:4326'
    }

    response = requests.get(url, params=params, timeout=60)
    current_size_threshold = int(config('current_size_threshold', 90))

    if response.status_code == 200:
        js = response.json()

        for feature in js['features']:
            try:
                properties = feature.get('properties', {})
                fire_status = properties.get('FIRE_STATUS')
                if fire_status != 'Out':
                    current_size = int(properties.get('CURRENT_SIZE'))
                    if current_size >= current_size_threshold:
                        yield feature
                    else:
                        print(
                            f'Skipping {fire_status} fire {properties.get("FIRE_NUMBER")} with size {current_size}')
                else:
                    pass
                    # print(
                    #     f'Skipping fire {properties.get("FIRE_NUMBER")} because it is out')
            except:
                print('trouble with feature')
    else:
        print(response.status_code)
        print(response.text)


async def main():
    for feature in get_active_fires():
        properties = feature.get('properties', {})
        fire_status = properties.get('FIRE_STATUS')
        current_size = float(properties.get('CURRENT_SIZE'))
        ignition_date = properties.get('IGNITION_DATE')
        fire_number = properties.get('FIRE_NUMBER')

        print(
            f'{fire_number} {fire_status} current size: {current_size}, ignition date: {ignition_date}')

        point = shape(feature['geometry'])

        yesterday = date.today() - timedelta(days=1)

        await generate_data(yesterday, point, fire_number, current_size)

    # for a particular date:
    # date_of_interest = date(2021, 8, 23)
    # point_of_interest = Point(-121.6, 51.5)
    # await generate_data(date_of_interest, point_of_interest, 'sybrand', 320.0)

    # for a bunch of dates:
    # date_of_interest = date(2021, 8, 9)
    # point_of_interest = (51.5, -121.6) # lat, lon
    # for _ in range(1):
    #     generate_data(date_of_interest, point_of_interest)
    #     date_of_interest += timedelta(days=1)

    # once you have a polygon, you can calculate the area: https://pyproj4.github.io/pyproj/stable/examples.html#geodesic-area

    # https://openmaps.gov.bc.ca/geo/pub/WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_PNTS_SP/ows?service=WMS&request=GetCapabilities


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
