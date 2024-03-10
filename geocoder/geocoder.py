# Description: This file contains the Geocoder class which is used to geocode the HSAF snow products.
import csv
import datetime
import glob
import os
import sys
import tempfile
import h5py
import numpy as np
from osgeo import gdal, osr
import xarray as xr
from pathlib import Path
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class Geocoder:
    def __init__(self, product, file, outfile,crs=4326):
        self.projection_dict = {
            'MSG': 'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_unknown",SPHEROID["unknown",6378169,295.488065897014]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",0],PARAMETER["satellite_height",35785831],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
            'WGS_84': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
        }

        self.transform_dict = {
            'H10': (3770007.5181810227, -3000.4031658172607, 0.0, 2635854.6990046464, 0.0, 3000.4031658172607),
            'H34': (5567248.074173927, -3000.4031658172607, 0.0, -5567248.074173927, 0.0, 3000.4031658172607),
            'H13': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
            'H12': (-25.005, 0.01, 0.0, 75.005, 0.0, -0.01),
            'H35': (-179.995, 0.01, 0.0, 89.995, 0.0, -0.01),
            }

        self.data_key = {'H10': 'SC', 'H34': 'SC', 'H35': 'rssc', 'H12': 'rssc', 'H13': 'rssc'}
        self.product = product.upper()
        self.file = file
        self.outfile = outfile
        self.engine = 'cfgrib' if self.product not in ['H10', 'H34'] else 'netcdf4'
        self.projection_key = 'MSG' if self.product in ['H10', 'H34'] else 'WGS_84'
        self.crs = crs
        self.rotation = self.product in ['H10', 'H34']
        self.tempfile = None

    def read_data(self):

        d = xr.open_dataset(str(self.file), engine=self.engine)
        data = d[self.data_key.get(self.product)].values
        if self.rotation:
            data = np.flip(data)
        return data

    def write_data(self, data):
        driver = gdal.GetDriverByName("GTiff")
        options = ['COMPRESS=LZW']

        if self.projection_key == 'MSG' and self.crs == 4326:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp:
                self.temp_filename = tmp.name
        else:
            self.temp_filename = self.outfile

        outdata = driver.Create(self.temp_filename, data.shape[1], data.shape[0], 1, gdal.GDT_Int16, options=options)
        outdata.SetGeoTransform(self.transform_dict[self.product])
        outdata.SetProjection(self.projection_dict[self.projection_key])
        outdata.GetRasterBand(1).WriteArray(data)
        outdata.FlushCache()
        return

    def msg_to_wgs84(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.vrt') as tmp_vrt:
            warp_options = gdal.WarpOptions(format='VRT', dstSRS='EPSG:4326')
            gdal.Warp(destNameOrDestDS=tmp_vrt.name, srcDSOrSrcDSTab=self.temp_filename, options=warp_options)

            translate_options = gdal.TranslateOptions(format='GTiff', creationOptions=['COMPRESS=LZW'])
            gdal.Translate(destName=self.outfile, srcDS=tmp_vrt.name, options=translate_options)

    def project(self):
        with tqdm(total=2, desc="Projecting", ncols=80) as pbar:
            data = self.read_data()
            pbar.update()
            self.write_data(data)
            pbar.update()
            if self.projection_key == 'MSG' and self.crs == 4326:
                self.msg_to_wgs84()
                os.remove(self.temp_filename)
            print(f'{self.outfile} is created')
            pbar.update()
    

# product = 'H10

if __name__ == '__main__':
    product = 'H35'
    folder = '/Users/cak/Desktop/Projects/hsaf-snow-geocoder/Data'
    file = folder + '/h35_20240106_day_merged.grib2'
    outfile = folder + '/geotiff/h35_projected.tif'
    geocoder = Geocoder(product, file, outfile).project()
