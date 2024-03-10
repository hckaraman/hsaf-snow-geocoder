import pytest
from unittest import mock
from geocoder.geocoder import Geocoder
import numpy as np
from unittest.mock import patch
import xarray as xr
from tqdm import tqdm
from unittest.mock import ANY

folder = '/mnt/c/Users/cagri/Desktop/Projects/Github/hsaf-snow-geocoder/Data'
file = folder + '/merged/h10_20240106_day_merged.H5'
outfile = folder + '/geotiff/h10_projected.tif'
tempfile_vrt = folder + '/geotiff/temp.vrt'
tempfile_tif = folder + '/geotiff/temp.tif'


def test_geocoder_initialization():
    geocoder = Geocoder('H10', file, outfile, '4326')
    assert geocoder.product == 'H10'
    assert geocoder.file == file
    assert geocoder.outfile == outfile
    assert geocoder.crs == '4326'
    assert geocoder.engine == 'netcdf4'  # Assuming 'H10' uses 'netcdf4'
    assert geocoder.projection_key == 'GEOS'  # Assuming 'H10' is associated with 'GEOS'
    assert geocoder.rotation is True  # Assuming 'H10' requires rotation


@patch('xarray.open_dataset')
def test_read_data(mock_open_dataset):
    mock_data_array = xr.DataArray(np.random.randint(0, 100, size=(916, 1902)))

    mock_open_dataset.return_value = {'SC': mock_data_array}

    geocoder = Geocoder('H10', file, outfile, '4326')
    data = geocoder.read_data()

    mock_open_dataset.assert_called_once_with(file, engine='netcdf4')
    assert np.array_equal(data, np.flip(mock_data_array))


@patch('osgeo.gdal.GetDriverByName')
def test_write_data(mock_get_driver_by_name):
    mock_driver = mock.Mock()
    mock_outdata = mock.Mock()
    mock_get_driver_by_name.return_value = mock_driver
    mock_driver.Create.return_value = mock_outdata

    geocoder = Geocoder('H10', file, outfile, '4326')
    data = np.array([[1, 2], [3, 4]])

    temp_filename = geocoder.write_data(data)

    mock_get_driver_by_name.assert_called_once_with("GTiff")
    mock_driver.Create.assert_called_once()
    mock_outdata.SetGeoTransform.assert_called_once_with(geocoder.TRANSFORM_DICT['H10'])
    mock_outdata.SetProjection.assert_called_once_with(geocoder.PROJECTION_DICT['GEOS'])
    mock_outdata.GetRasterBand(1).WriteArray.assert_called_once_with(data)


@mock.patch('osgeo.gdal.Translate')
@mock.patch('osgeo.gdal.Warp')
@mock.patch('tempfile.NamedTemporaryFile')
def test_msg_to_wgs84(mock_tempfile, mock_warp, mock_translate):
    # Setup the mock for tempfile to simulate a temporary file
    mock_tempfile.return_value.__enter__.return_value.name = tempfile_vrt

    # Initialize Geocoder
    geocoder = Geocoder('H10', file, outfile, '4326')

    # Call msg_to_wgs84 with a dummy temp_filename
    geocoder.msg_to_wgs84(tempfile_tif)

    # Check that gdal.Warp and gdal.Translate are called with the correct parameters
    mock_warp.assert_called_once()
    mock_translate.assert_called_once_with(
        destName=outfile, srcDS=tempfile_vrt, options=mock.ANY
    )
    # You can add more detailed checks for the options passed to gdal.Warp and gdal.Translate


@mock.patch('geocoder.geocoder.Geocoder.msg_to_wgs84')
@mock.patch('geocoder.geocoder.Geocoder.write_data')
@mock.patch('geocoder.geocoder.Geocoder.read_data')
@mock.patch('geocoder.geocoder.tqdm')
def test_project(mock_tqdm, mock_read_data, mock_write_data, mock_msg_to_wgs84):
    # Setup mock responses
    mock_read_data.return_value = xr.DataArray(np.random.randint(0, 100, size=(916, 1902)))
    mock_write_data.return_value = tempfile_tif

    # Initialize Geocoder
    geocoder = Geocoder('H10', file, outfile, '4326')

    # Call project method
    geocoder.project()

    # Verify that the read_data, write_data, and potentially msg_to_wgs84 methods are called
    mock_read_data.assert_called_once()
    mock_write_data.assert_called_once_with(ANY)


    # For 'GEOS' products with '4326' CRS, msg_to_wgs84 should be called
    if geocoder.projection_key == 'GEOS' and geocoder.crs == '4326':
        mock_msg_to_wgs84.assert_called_once_with(tempfile_tif)
    else:
        mock_msg_to_wgs84.assert_not_called()

    # Assert the progress bar is updated the expected number of times
    # assert mock_tqdm.return_value.update.call_count == 3
