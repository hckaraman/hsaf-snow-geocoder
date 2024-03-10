# hsaf-snow-geocoder

This repository contains the code for the conversion and projection of [HSAF](http://hsaf.meteoam.it/) Snow Products. 
The Geocoder is a Python tool designed for projecting HSAF snow product data into WGS84 or GEOS coordinate systems. 
The tool is a command-line application that takes an input file in hdf or grib2 and converts it to geotiff file with the desired projection.


## Features

- **Projection Support**: Converts HSAF snow product data to widely used coordinate systems: WGS84 and GEOS.
- **Data Compatibility**: Handles various HSAF snow product formats, ensuring broad usability across different datasets.
- **CLI Interface**: Easy-to-use command-line interface for quick geocoding of HSAF snow product data.

## Installation

1. Clone the repository or download the source code.
2. Install the required dependencies using pip:
```bash
pip install -e .
```

## Usage
The CLI tool is designed with simplicity in mind. Use the following command structure to geocode your HSAF snow product data:
```bash
geocoder --input-file <path_to_input_file> --output-file <path_to_output_file> --product <product_code> --crs <coordinate_reference_system>
```

### Options:
- --input-file, -i: Path to the input file. HDF files are expected for 'H10' and 'H34', while GRIB2 is expected for 'H13', 'H11', 'H12', and 'H35'.
- --output-file, -o: Path where the geocoded Geotiff file will be saved.
- --product, -p: Product code. Valid options are 'H10', 'H34', 'H13', 'H12', and 'H35'.
- --crs: Coordinate Reference System for the output file. Defaults to '4326'. 'H10' and 'H34' can also be projected to the GEOS projection.

## Options:
Geocode an 'H10' product file to WGS84:

```bash
geocoder -i /path/to/h10_file.hdf -o /path/to/output.tif -p H10 -crs 4326
```

## Troubleshooting
Ensure your input file matches the expected format for the specified product.
Verify the path to your input and output files is correct and accessible.
Check the product code and CRS are among the supported options.