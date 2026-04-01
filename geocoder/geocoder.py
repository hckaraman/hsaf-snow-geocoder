"""
This script is used to project the HSAF snow products to WGS84 or GEOS coordinate system.
Author: Cagri Karaman
Date: 2025-04-11
Version: 0.2
"""
import tempfile
import numpy as np
import osgeo
import h5py
from osgeo import gdal
import xarray as xr
from pathlib import Path
import yaml
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)


def _load_config():
    """Load product configuration from config.yaml."""
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


class Geocoder:
    """
    A class used to project the HSAF snow products to WGS84 or GEOS coordinate system.

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
    project_to_wgs84(temp_filename):
        Converts the data in the temporary file from the native coordinate system to WGS84.
    project():
        Projects the data from the input file to the output file using the specified coordinate reference system.
    """

    _config = None

    @classmethod
    def _get_config(cls):
        if cls._config is None:
            cls._config = _load_config()
        return cls._config

    def __init__(self, product, file, outfile, crs='4326', extension='hdf', variant='merged'):
        config = self._get_config()
        self.product = product.upper()

        if self.product not in config['products']:
            valid = list(config['products'].keys())
            raise ValueError(f"Unknown product '{self.product}'. Valid products: {valid}")

        product_cfg = config['products'][self.product]

        self.file = file
        self.outfile = outfile
        self.extension = extension
        self.engine = 'cfgrib' if self.extension == 'grib2' else 'netcdf4'
        self.projection_key = product_cfg['projection']
        self.crs = crs
        self.rotation = product_cfg.get('rotation', False)
        self.variant = variant

        self._projection_dict = config['projections']
        self._transform = tuple(product_cfg['transform'])
        self._data_shape = tuple(product_cfg['data_shape'])
        self._data_key = product_cfg['data_key']
        self._expected_extension = product_cfg.get('extension')

        # Validate the variant
        if isinstance(self._data_key, dict):
            if not self.variant:
                self.variant = 'merged'
            if self.variant not in self._data_key:
                valid_variants = list(self._data_key.keys())
                raise ValueError(
                    f"Invalid variant for {self.product}. Expected one of {valid_variants}, got '{self.variant}'")

        # Validate the extension
        if self.extension:
            valid_extensions = {'grib2', 'nc', 'hdf'}
            if self.extension not in valid_extensions:
                raise ValueError(f"Invalid extension '{self.extension}'. Expected one of {sorted(valid_extensions)}")

            if self._expected_extension and self.extension != self._expected_extension:
                warnings.warn(
                    f"Unexpected extension for {self.product}. Expected '{self._expected_extension}', got '{self.extension}'",
                    UserWarning
                )

    def read_data(self):
        if not Path(self.file).exists():
            raise FileNotFoundError(f"Input file not found: {self.file}")

        try:
            data = self._read_data_with_fallback()
        except Exception as e:
            raise IOError(f"Failed to read data from '{self.file}': {e}") from e

        if data.shape != self._data_shape:
            raise ValueError(f"Invalid data shape for {self.product}. Expected {self._data_shape}, got {data.shape}")

        return np.flip(data) if self.rotation else data

    def _get_data_key(self):
        if isinstance(self._data_key, dict) and self.variant:
            return self._data_key[self.variant]
        return self._data_key

    def _read_data_with_fallback(self):
        data_key = self._get_data_key()
        errors = []

        try:
            return self._read_data_with_xarray(data_key)
        except Exception as exc:
            errors.append(f"xarray/{self.engine}: {exc}")

        if self.extension != 'grib2':
            try:
                return self._read_data_with_h5py(data_key)
            except Exception as exc:
                errors.append(f"h5py: {exc}")

        raise IOError("; ".join(errors))

    def _read_data_with_xarray(self, data_key):
        dataset = xr.open_dataset(self.file, engine=self.engine)
        try:
            if data_key not in dataset:
                available = list(getattr(dataset, 'data_vars', {}).keys())
                raise KeyError(f"Variable '{data_key}' not found in dataset. Available variables: {available}")
            return dataset[data_key].values
        finally:
            close = getattr(dataset, 'close', None)
            if callable(close):
                close()

    def _read_data_with_h5py(self, data_key):
        with h5py.File(self.file, 'r') as dataset:
            dataset_path = self._find_h5py_dataset_path(dataset, data_key)
            return np.asarray(dataset[dataset_path][()])

    @staticmethod
    def _find_h5py_dataset_path(dataset, data_key):
        if data_key in dataset and isinstance(dataset[data_key], h5py.Dataset):
            return data_key

        matches = []

        def _visit(name, obj):
            if isinstance(obj, h5py.Dataset) and (name == data_key or name.endswith(f'/{data_key}')):
                matches.append(name)

        dataset.visititems(_visit)

        if matches:
            return sorted(matches, key=lambda item: (item.count('/'), item))[0]

        available = []
        dataset.visititems(
            lambda name, obj: available.append(name)
            if isinstance(obj, h5py.Dataset) else None
        )
        raise KeyError(f"Variable '{data_key}' not found in HDF5 dataset. Available datasets: {available}")

    def write_data(self, data):
        driver = gdal.GetDriverByName("GTiff")
        options = ['COMPRESS=LZW']

        needs_reprojection = self.projection_key in ['GEOS', 'GEOS_MTG', 'EASE', 'GEOS_IND'] and self.crs == '4326'

        if needs_reprojection:
            tmp = tempfile.NamedTemporaryFile(suffix='.tif', delete=False)
            temp_filename = tmp.name
            tmp.close()
        else:
            temp_filename = self.outfile

        outdata = driver.Create(temp_filename, data.shape[1], data.shape[0], 1, gdal.GDT_Int16, options=options)
        if outdata is None:
            raise IOError(f"Failed to create output file: {temp_filename}")

        outdata.SetGeoTransform(self._transform)
        outdata.SetProjection(self._projection_dict[self.projection_key])
        outdata.GetRasterBand(1).WriteArray(data)
        outdata.FlushCache()
        outdata = None  # Close the dataset

        return temp_filename

    def project_to_wgs84(self, temp_filename):
        # Check if cropping is needed
        if self.product == 'H10':
            crop_bounds = [-25, 25, 45, 75]  # [min_lon, min_lat, max_lon, max_lat]
            warp_options = gdal.WarpOptions(format='VRT',
                                            dstSRS='EPSG:4326',
                                            outputBounds=crop_bounds,
                                            dstNodata=255)  # H10 extent does not cover the whole paneuropean region
        elif self.product == 'H65':
            # Northern Hemisphere at 0.25° resolution: extent -180.125,-0.125 : 180.125,90.125 → 1441×361
            warp_options = gdal.WarpOptions(format='VRT',
                                            dstSRS='EPSG:4326',
                                            outputBounds=[-180.125, -0.125, 180.125, 90.125],
                                            xRes=0.25, yRes=0.25)
        else:
            warp_options = gdal.WarpOptions(format='VRT', dstSRS='EPSG:4326')

        vrt_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.vrt')
        vrt_path = vrt_tmp.name
        vrt_tmp.close()

        try:
            result = gdal.Warp(destNameOrDestDS=vrt_path,
                               srcDSOrSrcDSTab=temp_filename,
                               options=warp_options)
            if result is None:
                raise IOError(f"GDAL Warp failed for '{temp_filename}'")

            translate_options = gdal.TranslateOptions(format='GTiff',
                                                      creationOptions=['COMPRESS=LZW'])
            result = gdal.Translate(destName=self.outfile,
                                    srcDS=vrt_path,
                                    options=translate_options)
            if result is None:
                raise IOError(f"GDAL Translate failed for '{vrt_path}'")
        finally:
            # Clean up temp files
            temp_path = Path(temp_filename)
            vrt_file = Path(vrt_path)
            if temp_path.exists():
                temp_path.unlink()
            if vrt_file.exists():
                vrt_file.unlink()

    def project(self):
        data = self.read_data()
        temp_filename = self.write_data(data)

        if self.projection_key in ['GEOS', 'GEOS_IND', 'EASE', 'GEOS_MTG'] and self.crs == '4326':
            self.project_to_wgs84(temp_filename)


if __name__ == '__main__':

    folder = r'S:\Projects\H43_HR\output'
    folder = Path(folder)

    file = 'h43_hr_20260316_day_TSMS.H5'
    fname = folder / file
    oname = fname.with_suffix('.tif')

    h43_coder = Geocoder(product='H43_HR', file=fname, outfile=oname,
                         crs='GEOS', variant='merged', extension='hdf')
    h43_coder.project()
