from osgeo import gdal
import os
import numpy as np
import xarray as xr

os.chdir('/mnt/d/HSAF/H34/merged')

# Open the GeoTIFF file
# Total size of the GeoTIFF

total_size = 3712

# Rows and columns to subtract
start_row_subtract = 979
end_row_subtract = 64
start_col_subtract = 3115
end_col_subtract = 1214

# Calculate actual start and end rows and columns
start_row = total_size - start_row_subtract
end_row = total_size - end_row_subtract
start_col = total_size - start_col_subtract
end_col = total_size - end_col_subtract

start_row, end_row, start_col, end_col

# Original geotransformation parameters
OTLX, x_res, OTLY, y_res = (5567248.074173927, -3000.4031658172607, -5567248.074173927, 3000.4031658172607)

# Calculate new top left x and y for the subset
NTLX = OTLX + (start_col * x_res)
NTLY = OTLY + (start_row * y_res)

NTLX, NTLY

h10_transform = (NTLX, -3000.4031658172607, 0.0, NTLY, 0.0, 3000.4031658172607)
h10_projection = 'PROJCS["unknown",GEOGCS["GCS_unknown",DATUM["D_unknown",SPHEROID["unknown",6378169,295.488065897014]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Geostationary_Satellite"],PARAMETER["central_meridian",0],PARAMETER["satellite_height",35785831],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'


old_coords = (2854835.056, 3488128.133)
new_coords = (2848835.190, 3491129.054)

# Calculate the shift in easting and northing
shift_easting = new_coords[0] - old_coords[0]
shift_northing = new_coords[1] - old_coords[1]

# Apply the shift to the new top left x and y for the subset
adjusted_NTLX = NTLX + shift_easting
adjusted_NTLY = NTLY + shift_northing
h10_transform = (adjusted_NTLX, -3000.4031658172607, 0.0, adjusted_NTLY, 0.0, 3000.4031658172607)


file = 'h10_20231221_day_merged.H5'
d = xr.open_dataset(file)
data = d['SC'].values
data = data.astype(np.int16)
data = np.flip(data)

rows, cols = data.shape

# dataset = gdal.Open("h34_20231221_day_merged.tif")
# data = dataset.ReadAsArray()
# data = data[start_row:end_row+1, start_col:end_col+1]
# rows, cols = data.shape


outfile = 'H10_projected_from_h10.tif'
driver = gdal.GetDriverByName("GTiff")
outdata = driver.Create(outfile, cols, rows, 1, gdal.GDT_Int16,
                        options=['COMPRESS=LZW'])
outdata.SetGeoTransform(h10_transform)  ##sets same geotransform as input
outdata.SetProjection(h10_projection)  ##sets same projection as input
outdata.GetRasterBand(1).WriteArray(data)

# outdata.GetRasterBand(1).SetNoDataValue(10000)  ##if you want these values transparent
outdata.FlushCache()  ##saves to disk!!
outdata = None
band = None
ds = None

# 1) 2854835.056, 3488128.133
# 2) 2848835.190, 3491129.054
#
# 7516.904


H13 = (-25.125, 0.25, 0.0, 75.125, 0.0, -0.25)