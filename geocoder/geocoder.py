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
from pyproj import CRS

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
        'GEOS_MTG': 'PROJCS["unknown",GEOGCS["unknown",DATUM["D_Unknown_based_on_WGS_84_ellipsoid",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",0],PARAMETER["satellite_height",35786400],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
        'EASE': 'PROJCS["WGS 84 / NSIDC EASE-Grid 2.0 North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Lambert_Azimuthal_Equal_Area"],PARAMETER["latitude_of_center",90],PARAMETER["longitude_of_center",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",SOUTH],AXIS["Northing",SOUTH],AUTHORITY["EPSG","6931"]]'
    }

    # PROJECTION_DICT = {
    #     'GEOS': CRS.from_proj4(
    #         "+proj=geos +lon_0=0 +h=35785831 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    #     ),
    #     'WGS_84': CRS.from_epsg(4326),  # EPSG code for WGS 84
    #     'GEOS_MTG': CRS.from_proj4(
    #         "+proj=geos +lon_0=0 +h=35786400 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    #     ),
    #     'EASE': CRS.from_proj4(
    #         "+proj=laea +lat_0=90 +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    #     ),
    # }

    PROJECTION_MAP = {
        'H10': 'GEOS',
        'H34': 'GEOS',
        'H43': 'GEOS_MTG',
        'H65': 'EASE'
    }

    TRANSFORM_DICT = {
        'H10': (3770007.5181810227, -3000.4031658172607, 0.0, 2635854.6990046464, 0.0, 3000.4031658172607),
        'H11': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
        'H34': (5567248.074173927, -3000.4031658172607, 0.0, -5567248.074173927, 0.0, 3000.4031658172607),
        'H13': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
        'H12': (-25.005, 0.01, 0.0, 75.005, 0.0, -0.01),
        'H35': (-180.0, 0.01, 0.0, 90.0, 0.0, -0.01),
        'H43': (-5567999.994203018, 1999.9999979177508, 0.0, 5567999.994203017, 0.0, -1999.9999979177508),
        'H65': (-9000000.0, 25000.0, 0.0, 9000000.0, 0.0, -25000.0)
    }

    DATA_KEY = {'H10': 'SC', 'H11': 'rssc', 'H34': 'SC', 'H35': 'rssc', 'H12': 'rssc', 'H13': 'rssc', 'H43': 'SC',
                'H65': 'swe'}

    DATA_SHAPE = {'H10': (916, 1902), 'H11': (201, 281), 'H34': (3712, 3712), 'H35': (8999, 35999), 'H12': (5001, 7001),
                  'H13': (201, 281), 'H43': (5568, 5568), 'H65': (720, 720)}

    def __init__(self, product, file, outfile, crs='4326'):
        self.product = product.upper()
        self.file = file
        self.outfile = outfile
        self.engine = 'cfgrib' if self.product not in ['H10', 'H34', 'H43', 'H65'] else 'netcdf4'
        self.projection_key = self.PROJECTION_MAP.get(self.product, 'WGS_84')

        self.crs = crs
        self.rotation = self.product in ['H10', 'H34']

    def read_data(self):
        d = xr.open_dataset(self.file, engine=self.engine)
        data = d[self.DATA_KEY[self.product]].values

        if data.shape != self.DATA_SHAPE[self.product]:
            raise ValueError(f"Invalid data shape. Expected {self.DATA_SHAPE[self.product]}, got {data.shape}")

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

    def project_to_wgs84(self, temp_filename):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.vrt') as tmp_vrt:
            warp_options = gdal.WarpOptions(format='VRT', dstSRS='EPSG:4326')
            gdal.Warp(destNameOrDestDS=tmp_vrt.name, srcDSOrSrcDSTab=temp_filename, options=warp_options)

            translate_options = gdal.TranslateOptions(format='GTiff', creationOptions=['COMPRESS=LZW'])
            gdal.Translate(destName=self.outfile, srcDS=tmp_vrt.name, options=translate_options)

    def project(self):
        with tqdm(total=2, desc="Projecting", ncols=80) as pbar:
            # data = self.read_data()
            data = xr.open_dataset(self.file)
            data = data.data.values
            pbar.update()
            temp_filename = self.write_data(data)
            pbar.update()
            if self.projection_key in ['GEOS', 'EASE'] and self.crs == '4326':
                self.project_to_wgs84(temp_filename)

            print(f'{self.outfile} is created')
            pbar.update()


if __name__ == '__main__':
    product = 'H35'
    folder = '/Volumes/external/Projects/HSAF/H35/input'
    import glob
    files = glob.glob1(folder, '*ndsi*.hdf')
    for file in files:
        file = folder + '/' + file
        outfile =  file.split('.')[0] + '.tif'
        try:
            geocoder = Geocoder(product, file, outfile).project()
        except Exception as e:
            print(e)

    # file = folder + '/eps_M01_20200817_2240_0022_ndsi.hdf'
    # outfile = folder + '/eps_M01_20200817_2240_0022_ndsi.tif'
    # # crs = '6931'  # EASEGrid
    # geocoder = Geocoder(product, file, outfile).project()

# !TODO check H43 GO ES implementation