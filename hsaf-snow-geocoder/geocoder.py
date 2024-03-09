import csv
import datetime
import glob
import os
import sys
import tempfile

import h5py
import numpy as np
# import gdal
from osgeo import gdal, osr
import xarray as xr
from pathlib import Path

projection_dict = {
    'H10': 'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_unknown",SPHEROID["unknown",6378169,295.488065897014]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",0],PARAMETER["satellite_height",35785831],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
    'H34': 'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_unknown",SPHEROID["unknown",6378169,295.488065897014]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",0],PARAMETER["satellite_height",35785831],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
    'H35': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
    'H12': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
    'H13': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]'
}

transform_dict = {'H10': (3770007.5181810227, -3000.4031658172607, 0.0, 2635854.6990046464, 0.0, 3000.4031658172607),
                  # 'H10': (3776007.3841810226, -3000.4031658172607, 0.0, 2632853.7780046463, 0.0, 3000.4031658172607), #There is a known issue with the H10 projection we shift the image by half a pixel, will be fixed in product release
                  'H34': (5567248.074173927, -3000.4031658172607, 0.0, -5567248.074173927, 0.0, 3000.4031658172607),
                  'H13': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
                  'H12': (-25.005, 0.01, 0.0, 75.005, 0.0, -0.01),
                  'H35': (-179.995, 0.01, 0.0, 89.995, 0.0, -0.01),
                  }

data_key = {'H10': 'SC', 'H34': 'SC'}

product = 'H10'
in_folder = Path('/mnt/c/Users/cagri/Desktop/Projects/Github/hsaf-snow-geocoder/Data')
out_folder = in_folder
file = 'h10_20240222_day_merged.H5'
outfile = 'H10_projected.tif'

d = xr.open_dataset(in_folder.joinpath(file))
data = d[data_key.get(product)].values
# data = data.astype(np.int16)
data = np.flip(data)
rows, cols = data.shape

outfile = 'H10_projected.tif'
driver = gdal.GetDriverByName("GTiff")
outdata = driver.Create(str(out_folder.joinpath(outfile)), cols, rows, 1, gdal.GDT_Int16,
                        options=['COMPRESS=LZW'])

outdata.SetGeoTransform(transform_dict.get(product))  ##sets same geotransform as input
outdata.SetProjection(projection_dict.get(product))  ##sets same projection as input
outdata.GetRasterBand(1).WriteArray(data)

# outdata.GetRasterBand(1).SetNoDataValue(10000)  ##if you want these values transparent
outdata.FlushCache()  ##saves to disk!!
outdata = None
band = None
ds = None
d.close()
