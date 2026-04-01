import pytest
from unittest import mock
from geocoder.geocoder import Geocoder
import numpy as np
from unittest.mock import patch, ANY
import xarray as xr
import os
import h5py
import uuid

# Use paths relative to this test file for portability
DATA_DIR = os.path.join(os.path.dirname(__file__), 'Data')
file = os.path.join(DATA_DIR, 'h10_20240107_day_merged.H5')
outfile = os.path.join(DATA_DIR, 'h10_projected.tif')
tempfile_vrt = os.path.join(DATA_DIR, 'temp.vrt')
tempfile_tif = os.path.join(DATA_DIR, 'temp.tif')


def test_geocoder_initialization():
    geocoder = Geocoder('H10', file, outfile, '4326')
    assert geocoder.product == 'H10'
    assert geocoder.file == file
    assert geocoder.outfile == outfile
    assert geocoder.crs == '4326'
    assert geocoder.engine == 'netcdf4'
    assert geocoder.projection_key == 'GEOS'
    assert geocoder.rotation is True


def test_geocoder_invalid_product():
    with pytest.raises(ValueError, match="Unknown product"):
        Geocoder('INVALID', file, outfile, '4326')


def test_geocoder_invalid_variant():
    with pytest.raises(ValueError, match="Invalid variant"):
        Geocoder('H10', file, outfile, '4326', variant='nonexistent')


def test_geocoder_invalid_extension():
    with pytest.raises(ValueError, match="Invalid extension"):
        Geocoder('H10', file, outfile, '4326', extension='xyz')


@patch('xarray.open_dataset')
def test_read_data(mock_open_dataset):
    mock_data_array = xr.DataArray(np.random.randint(0, 100, size=(916, 1902)))
    mock_open_dataset.return_value = {'SC': mock_data_array}

    geocoder = Geocoder('H10', file, outfile, '4326')
    data = geocoder.read_data()

    mock_open_dataset.assert_called_once_with(file, engine='netcdf4')
    assert np.array_equal(data, np.flip(mock_data_array))


def _workspace_temp_file(name):
    return os.path.join(DATA_DIR, f"{name}_{uuid.uuid4().hex}.h5")


@patch('xarray.open_dataset')
def test_read_data_missing_variable(mock_open_dataset):
    missing_file = _workspace_temp_file('missing_variable')
    with h5py.File(missing_file, 'w') as dataset:
        dataset.create_dataset('wrong_key', data=np.zeros((916, 1902), dtype=np.uint8))

    try:
        mock_open_dataset.return_value = xr.Dataset({'wrong_key': xr.DataArray(np.zeros((916, 1902)))})

        geocoder = Geocoder('H10', missing_file, outfile, '4326')
        with pytest.raises(IOError, match="Variable 'SC' not found"):
            geocoder.read_data()
    finally:
        if os.path.exists(missing_file):
            os.remove(missing_file)


@patch('xarray.open_dataset')
def test_read_data_wrong_shape(mock_open_dataset):
    mock_data_array = xr.DataArray(np.random.randint(0, 100, size=(100, 100)))
    mock_open_dataset.return_value = {'SC': mock_data_array}

    geocoder = Geocoder('H10', file, outfile, '4326')
    with pytest.raises(ValueError, match="Invalid data shape"):
        geocoder.read_data()


@patch('xarray.open_dataset')
def test_read_data_falls_back_to_h5py_when_xarray_open_fails(mock_open_dataset):
    fallback_file = _workspace_temp_file('fallback')
    source_data = np.arange(916 * 1902, dtype=np.int32).reshape((916, 1902))

    with h5py.File(fallback_file, 'w') as dataset:
        dataset.create_dataset('SC', data=source_data)

    try:
        mock_open_dataset.side_effect = ImportError(
            "DLL load failed while importing _netCDF4: The specified procedure could not be found."
        )

        geocoder = Geocoder('H10', fallback_file, outfile, '4326', extension='hdf')
        data = geocoder.read_data()

        mock_open_dataset.assert_called_once_with(fallback_file, engine='netcdf4')
        assert np.array_equal(data, np.flip(source_data))
    finally:
        if os.path.exists(fallback_file):
            os.remove(fallback_file)


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
    mock_outdata.SetGeoTransform.assert_called_once_with(geocoder._transform)
    mock_outdata.SetProjection.assert_called_once_with(geocoder._projection_dict['GEOS'])
    mock_outdata.GetRasterBand(1).WriteArray.assert_called_once_with(data)


@mock.patch('osgeo.gdal.Translate')
@mock.patch('osgeo.gdal.Warp')
@mock.patch('tempfile.NamedTemporaryFile')
def test_project_to_wgs84(mock_tempfile, mock_warp, mock_translate):
    mock_tempfile.return_value.name = tempfile_vrt
    mock_tempfile.return_value.close = mock.Mock()
    mock_warp.return_value = mock.Mock()  # Non-None means success
    mock_translate.return_value = mock.Mock()

    geocoder = Geocoder('H10', file, outfile, '4326')

    with mock.patch('pathlib.Path.exists', return_value=True), \
         mock.patch('pathlib.Path.unlink'):
        geocoder.project_to_wgs84(tempfile_tif)

    mock_warp.assert_called_once()
    mock_translate.assert_called_once_with(
        destName=outfile, srcDS=tempfile_vrt, options=mock.ANY
    )


@mock.patch('geocoder.geocoder.Geocoder.project_to_wgs84')
@mock.patch('geocoder.geocoder.Geocoder.write_data')
@mock.patch('geocoder.geocoder.Geocoder.read_data')
def test_project(mock_read_data, mock_write_data, mock_project_to_wgs84):
    mock_read_data.return_value = xr.DataArray(np.random.randint(0, 100, size=(916, 1902)))
    mock_write_data.return_value = tempfile_tif

    geocoder = Geocoder('H10', file, outfile, '4326')
    geocoder.project()

    mock_read_data.assert_called_once()
    mock_write_data.assert_called_once_with(ANY)

    # For 'GEOS' products with '4326' CRS, project_to_wgs84 should be called
    if geocoder.projection_key == 'GEOS' and geocoder.crs == '4326':
        mock_project_to_wgs84.assert_called_once_with(tempfile_tif)
    else:
        mock_project_to_wgs84.assert_not_called()


def test_h34_ind_no_rotation():
    geocoder = Geocoder('H34_IND', file, outfile, '4326', extension='hdf')
    assert geocoder.rotation is False


def test_h43_mnt_initialization():
    geocoder = Geocoder('H43_MNT', file, outfile, '4326', extension='nc')
    assert geocoder.product == 'H43_MNT'
    assert geocoder.projection_key == 'GEOS_MTG'
    assert geocoder.rotation is False
