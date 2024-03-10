import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from pathlib import Path
from geocoder import Geocoder

class TestGeocoder(unittest.TestCase):
    def setUp(self):
        self.product = 'H34'
        self.file = '/Users/cak/Desktop/Projects/hsaf-snow-geocoder/Data/h34_20240101_day_merged.H5'
        self.outfile = '/Users/cak/Desktop/Projects/hsaf-snow-geocoder/Data/geotiff/h34_projected.tif'
        self.geocoder = Geocoder(self.product, self.file, self.outfile)

    @patch('xarray.open_dataset')
    def reads_data_correctly(self, mock_open_dataset):
        mock_dataset = MagicMock()
        mock_dataset.__getitem__.return_value.values.return_value = np.array([[1, 2], [3, 4]])
        mock_open_dataset.return_value = mock_dataset

        data = self.geocoder.read_data()

        np.testing.assert_array_equal(data, np.array([[3, 4], [1, 2]]))
        mock_open_dataset.assert_called_once_with(str(self.file), engine='netcdf4')

    @patch('osgeo.gdal.GetDriverByName')
    def writes_data_correctly(self, mock_get_driver):
        mock_driver = MagicMock()
        mock_outdata = MagicMock()
        mock_driver.Create.return_value = mock_outdata
        mock_get_driver.return_value = mock_driver

        data = np.array([[1, 2], [3, 4]])

        self.geocoder.write_data(data)

        mock_get_driver.assert_called_once_with("GTiff")
        mock_driver.Create.assert_called_once_with(str(self.outfile), 2, 2, 1, gdal.GDT_Int16, options=['COMPRESS=LZW'])
        mock_outdata.GetRasterBand(1).WriteArray.assert_called_once_with(data)
        mock_outdata.FlushCache.assert_called_once()

    def projects_data_correctly(self):
        with patch.object(self.geocoder, 'read_data', return_value=np.array([[1, 2], [3, 4]])) as mock_read_data, \
             patch.object(self.geocoder, 'write_data') as mock_write_data:

            self.geocoder.project()

            mock_read_data.assert_called_once()
            mock_write_data.assert_called_once_with(np.array([[1, 2], [3, 4]]))

if __name__ == '__main__':
    unittest.main()