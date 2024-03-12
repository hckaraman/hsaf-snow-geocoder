"""
This script is used to project the HSAF snow products to WGS84 or GEOS coordinate system.
Author: Cagri Karaman
Date: 2024-03-10
Version: 0.1
"""

import tempfile
import numpy as np
from osgeo import gdal, osr
import xarray as xr
from pathlib import Path
from tqdm import tqdm
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)


class Geocoder:
    """
        A class used to project the HSAF snow products to WGS84 or GEOS coordinate system.

        ...

        Attributes
        ----------
        product : str
            a string representing the product type
        file : str
            a string representing the file path of the input data
        outfile : str
            a string representing the file path of the output data
        engine : str
            a string representing the engine used to open the dataset
        projection_key : str
            a string representing the key to access the projection dictionary
        crs : str
            a string representing the coordinate reference system
        rotation : bool
            a boolean representing whether the data needs to be flipped vertically

        Methods
        -------
        read_data():
            Reads the data from the file specified during the initialization of the Geocoder object.
        write_data(data):
            Writes the data to a temporary file or directly to the output file depending on the projection key and crs.
        msg_to_wgs84(temp_filename):
            Converts the data in the temporary file from the GEOS coordinate system to the WGS84 coordinate system.
        project():
            Projects the data from the input file to the output file using the specified coordinate reference system.
        """

    PROJECTION_DICT = {
        'GEOS': 'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_unknown",SPHEROID["unknown",6378169,295.488065897014]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",0],PARAMETER["satellite_height",35785831],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
        'WGS_84': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
    }

    TRANSFORM_DICT = {
        'H10': (3770007.5181810227, -3000.4031658172607, 0.0, 2635854.6990046464, 0.0, 3000.4031658172607),
        'H11': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
        'H34': (5567248.074173927, -3000.4031658172607, 0.0, -5567248.074173927, 0.0, 3000.4031658172607),
        'H13': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
        'H12': (-25.005, 0.01, 0.0, 75.005, 0.0, -0.01),
        'H35': (-179.995, 0.01, 0.0, 89.995, 0.0, -0.01),
    }

    DATA_KEY = {'H10': 'SC', 'H11': 'rssc', 'H34': 'SC', 'H35': 'rssc', 'H12': 'rssc', 'H13': 'rssc'}

    def __init__(self, product, file, outfile, crs='4326'):
        self.product = product.upper()
        self.file = file
        self.outfile = outfile
        self.engine = 'cfgrib' if self.product not in ['H10', 'H34'] else 'netcdf4'
        self.projection_key = 'GEOS' if self.product in ['H10', 'H34'] else 'WGS_84'
        self.crs = crs
        self.rotation = self.product in ['H10', 'H34']

    def read_data(self):
        d = xr.open_dataset(self.file, engine=self.engine)
        data = d[self.DATA_KEY[self.product]].values
        return np.flip(data) if self.rotation else data

    def write_data(self, data):
        driver = gdal.GetDriverByName("GTiff")
        options = ['COMPRESS=LZW']

        temp_filename = tempfile.mktemp(
            suffix='.tif') if self.projection_key == 'GEOS' and self.crs == '4326' else self.outfile

        outdata = driver.Create(temp_filename, data.shape[1], data.shape[0], 1, gdal.GDT_Int16, options=options)
        outdata.SetGeoTransform(self.TRANSFORM_DICT[self.product])
        outdata.SetProjection(self.PROJECTION_DICT[self.projection_key])
        outdata.GetRasterBand(1).WriteArray(data)
        outdata.FlushCache()
        return temp_filename

    def msg_to_wgs84(self, temp_filename):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.vrt') as tmp_vrt:
            warp_options = gdal.WarpOptions(format='VRT', dstSRS='EPSG:4326')
            gdal.Warp(destNameOrDestDS=tmp_vrt.name, srcDSOrSrcDSTab=temp_filename, options=warp_options)

            translate_options = gdal.TranslateOptions(format='GTiff', creationOptions=['COMPRESS=LZW'])
            gdal.Translate(destName=self.outfile, srcDS=tmp_vrt.name, options=translate_options)

    def project(self):
        with tqdm(total=2, desc="Projecting", ncols=80) as pbar:
            data = self.read_data()
            pbar.update()
            temp_filename = self.write_data(data)
            pbar.update()
            if self.projection_key == 'GEOS' and self.crs == '4326':
                self.msg_to_wgs84(temp_filename)
            print(f'{self.outfile} is created')
            pbar.update()


if __name__ == '__main__':
    product = 'H35'
    folder = '/Users/cak/Desktop/Projects/hsaf-snow-geocoder/Data'
    file = folder + '/h35_20240106_day_merged.grib2'
    outfile = folder + '/geotiff/h35_projected.tif'
    geocoder = Geocoder(product, file, outfile).project()
