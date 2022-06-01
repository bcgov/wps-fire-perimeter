"""
Based on code by https://github.com/ashlinrichardson available at:
https://github.com/bcgov/wps-research/blob/master/py/gee/active_fire.js
"""
import ee


def maskS2clouds(image):
    """ function from online example """
    qa = image.select('QA60')  # Bits 10, 11: clouds, cirrus, resp.
    cloudBitMask = 1 << 10  # set both 0 == clear conditions
    cirrusBitMask = 1 << 11
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(
        qa.bitwiseAnd(cirrusBitMask).eq(0))
    return image.updateMask(mask).divide(10000)


def apply_cloud_cover_threshold(start_date, n_days, cloud_threshold):
    # https://developers.google.com/earth-engine/apidocs/ee-imagecollection-filterdate
    data = ee.ImageCollection('COPERNICUS/S2_SR').filterDate(
        start_date,
        start_date.advance(n_days, 'day'))

    # apply cloud threshold and mask
    data = data.filter(ee.Filter.lt(
        'CLOUDY_PIXEL_PERCENTAGE',
        cloud_threshold)).map(maskS2clouds).mean()

    return data


def apply_classification_rule(data):
    # get DEM, LandCover, Sentinel-2 "L2A" (level two atmospherically-
    # corrected "bottom of atmosphere (BOA) reflectance) data """
    nasa_dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation')
    land_cover = ee.ImageCollection("ESA/WorldCover/v100").first()

    # apply classification rule
    rule = 'x = R > G && R > B && (LC != 80) && (LC != 50) && (LC != 70) && (DEM < 1500)'
    r = data.expression(rule, {'R': data.select('B12'),
                               'G': data.select('B11'),
                               'B': data.select('B9'),
                               'LC': land_cover.select('Map'),
                               'DEM': nasa_dem})

    return r
