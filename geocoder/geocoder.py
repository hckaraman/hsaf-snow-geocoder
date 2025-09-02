"""
This script is used to project the HSAF snow products to WGS84 or GEOS coordinate system.
Author: Cagri Karaman
Date: 2025-04-11
Version: 0.2
"""
import os
import tempfile
import numpy as np
from osgeo import gdal, osr
import xarray as xr
from pathlib import Path
from tqdm import tqdm
import warnings

# from pyproj import CRS

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
        'GEOS': "+proj=geos +lon_0=0 +h=35785831 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
        'GEOS_IND': "+proj=geos +lon_0=45.5 +h=35785831 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
        'WGS_84': "+proj=longlat +datum=WGS84 +no_defs",
        'GEOS_MTG': "+proj=geos +lon_0=0 +h=35786400 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
        'EASE': "+proj=laea +lat_0=90 +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    }

    PROJECTION_MAP = {
        'H10': 'GEOS',
        'H34': 'GEOS',
        'H34_IND': 'GEOS_IND',
        'H43': 'GEOS_MTG',
        'H43_MNT': 'GEOS_MTG',
        'H65': 'EASE'
    }

    TRANSFORM_DICT = {
        'H10': (3770007.5181810227, -3000.4031658172607, 0.0, 2635854.6990046464, 0.0, 3000.4031658172607),
        'H11': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
        'H34': (5567248.074173927, -3000.4031658172607, 0.0, -5567248.074173927, 0.0, 3000.4031658172607),
        'H34_IND': (-5570248.5, 3000.403076171875, 0.0, 5570248.5, 0.0, -3000.403076171875),
        'H13': (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25),
        'H12': (-25.005, 0.01, 0.0, 75.005, 0.0, -0.01),
        'H35': (-180.0, 0.01, 0.0, 90.0, 0.0, -0.01),
        'H43': (-5567999.994203018, 1999.9999979177508, 0.0, 5567999.994203017, 0.0, -1999.9999979177508),
        'H43_MNT': (-5567999.994203018, 1999.9999979177508, 0.0, 5567999.994203017, 0.0, -1999.9999979177508),
        'H65': (-9000000.0, 25000.0, 0.0, 9000000.0, 0.0, -25000.0)
    }

    DATA_KEY = {
        'H10': {
            'merged': 'SC',
            'flat': 'SC',
            'mountain': 'CSC'
        },
        'H11': 'snow_status',
        'H34': {
            'merged': 'SC',
            'flat': 'SC_flat',
            'mountain': 'SC_mountainous'
        },
        'H35': {
            'merged': 'rssc',
            'flat': 'SC',
            'mountain': 'fsc'
        },
        'H12': 'rssc',
        'H13': 'rssc',
        'H43': {
            'merged': 'merged_sc',
            'flat': 'flat_sc',
            'mountain': 'mountain_sc'
        },
        'H65': {
            'merged': 'swe',
            'flat': 'swe_flat',
            'mountain': 'swe_mountain'
        },
        'H34_IND': 'SC',
        'H43_MNT': 'SC'
    }

    DATA_SHAPE = {'H10': (916, 1902), 'H11': (201, 281), 'H34': (3712, 3712), 'H35': (8999, 35999), 'H12': (5001, 7001),
                  'H13': (201, 281), 'H43': (5568, 5568), 'H65': (720, 720), 'H34_IND': (3712, 3712),
                  'H43_MNT': (5568, 5568)}

    EXTENSION_DICT = {
        'H10': 'hdf',
        'H11': 'grib2',
        'H12': 'grib2',
        'H13': 'grib2',
        'H34': 'hdf',
        'H35': 'grib2',
        'H43': 'nc',
        'H65': 'nc',
    }

    def __init__(self, product, file, outfile, crs='4326', extension='hdf', variant='merged'):
        self.product = product.upper()
        self.file = file
        self.outfile = outfile
        self.extension = extension
        self.engine = 'cfgrib' if self.extension == 'grib2' else 'netcdf4'
        self.projection_key = self.PROJECTION_MAP.get(self.product, 'WGS_84')

        self.crs = crs
        self.rotation = self.product in ['H10', 'H34']
        self.variant = variant

        # Validate the variant
        if isinstance(self.DATA_KEY[self.product], dict):
            if not self.variant:
                self.variant = 'merged'  # Use 'merge' variant if none provided
            if self.variant not in self.DATA_KEY[self.product]:
                valid_variants = list(self.DATA_KEY[self.product].keys())
                raise ValueError(
                    f"Invalid variant for {self.product}. Expected one of {valid_variants}, got {self.variant}")

        # Validate the extension
        if self.extension:
            valid_extensions = {'grib2', 'nc', 'hdf'}

            if self.extension not in valid_extensions:
                raise ValueError(f"Invalid extension. Expected one of {valid_extensions}, got '{self.extension}'")

            expected_extension = self.EXTENSION_DICT.get(self.product)

            if expected_extension and self.extension != expected_extension:
                warnings.warn(
                    f"Invalid extension for {self.product}. Expected '{expected_extension}', got '{self.extension}'",
                    UserWarning
                )

    def read_data(self):

        d = xr.open_dataset(self.file, engine=self.engine)

        # Get the appropriate data key
        if isinstance(self.DATA_KEY[self.product], dict) and self.variant:
            data_key = self.DATA_KEY[self.product][self.variant]
        else:
            data_key = self.DATA_KEY[self.product]

        data = d[data_key].values

        if data.shape != self.DATA_SHAPE[self.product]:
            raise ValueError(f"Invalid data shape. Expected {self.DATA_SHAPE[self.product]}, got {data.shape}")

        return np.flip(data) if self.rotation else data

    def write_data(self, data):
        driver = gdal.GetDriverByName("GTiff")
        options = ['COMPRESS=LZW']

        temp_filename = tempfile.mktemp(
            suffix='.tif') if self.projection_key in ['GEOS', 'GEOS_MTG', 'EASE',
                                                      'GEOS_IND'] and self.crs == '4326' else self.outfile

        outdata = driver.Create(temp_filename, data.shape[1], data.shape[0], 1, gdal.GDT_Int16, options=options)
        outdata.SetGeoTransform(self.TRANSFORM_DICT[self.product])
        outdata.SetProjection(self.PROJECTION_DICT[self.projection_key])
        outdata.GetRasterBand(1).WriteArray(data)
        outdata.FlushCache()
        return temp_filename

    def project_to_wgs84(self, temp_filename):
        # Check if cropping is needed
        if self.product == 'H10':
            crop_bounds = [-25, 25, 45, 75]  # [min_lon, min_lat, max_lon, max_lat]
            warp_options = gdal.WarpOptions(format='VRT',
                                            dstSRS='EPSG:4326',
                                            outputBounds=crop_bounds,
                                            dstNodata=255) # H10 extent does not cover the whole paneuropean region with GEOS proj.
        else:
            warp_options = gdal.WarpOptions(format='VRT', dstSRS='EPSG:4326')

        # Temporary VRT file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.vrt') as tmp_vrt:
            # Project to WGS84 with or without cropping
            gdal.Warp(destNameOrDestDS=tmp_vrt.name,
                      srcDSOrSrcDSTab=temp_filename,
                      options=warp_options)

            # Translate to GeoTIFF with compression
            translate_options = gdal.TranslateOptions(format='GTiff',
                                                      creationOptions=['COMPRESS=LZW'])
            gdal.Translate(destName=self.outfile,
                           srcDS=tmp_vrt.name,
                           options=translate_options)

    def project(self):
        with tqdm(total=2, desc="Projecting", ncols=80) as pbar:
            data = self.read_data()
            pbar.update()
            temp_filename = self.write_data(data)
            pbar.update()
            if self.projection_key in ['GEOS', 'GEOS_IND', 'EASE', 'GEOS_MTG'] and self.crs == '4326':
                self.project_to_wgs84(temp_filename)

            print(f'{self.outfile} is created')
            pbar.update()


if __name__ == '__main__':

    folder = '/Users/cak/Desktop/Projects/HSAF_Snow_Quicklook/data'
    folder = Path(folder)

    file = 'h43_20250120_day_merged.nc'
    fname = folder / file
    oname = fname.with_suffix('.tif')


    h43_coder = Geocoder(product='H43', file=fname, outfile=oname,
                         crs='4326', variant='merged', extension='nc')
    h43_coder.project()