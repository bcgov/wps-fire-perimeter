from datetime import date
import os
import ee
import asyncio
import fire
from shapely.geometry import Point
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
    fire.Fire(fire_perimeter)
