# hsaf-snow-geocoder

This repository contains the code for the conversion and projection of [HSAF](http://hsaf.meteoam.it/) Snow Products.
The Geocoder is a Python tool designed for projecting HSAF snow product data into WGS84 or GEOS coordinate systems.
The tool is a command-line application that takes an input file in HDF, GRIB2, or NetCDF format and converts it to a GeoTIFF file with the desired projection.

## Features

- **Projection Support**: Converts HSAF snow product data to widely used coordinate systems: WGS84, GEOS, GEOS_MTG, GEOS_IND, and EASE.
- **Data Compatibility**: Handles various HSAF snow product formats (HDF, GRIB2, NetCDF).
- **Variant Support**: Supports `merged`, `flat`, and `mountain` data variants for applicable products.
- **CLI Interface**: Easy-to-use command-line interface for quick geocoding of HSAF snow product data.

## Supported Products

| Product  | Description              | Format | Native Projection | Variants                    |
|----------|--------------------------|--------|--------------------|-----------------------------|
| H10      | Snow Cover - Europe      | HDF    | GEOS               | merged, flat, mountain      |
| H11      | Snow Cover - Europe      | GRIB2  | WGS84              | -                           |
| H12      | Snow Cover - Europe      | GRIB2  | WGS84              | -                           |
| H13      | Snow Cover - Europe      | GRIB2  | WGS84              | -                           |
| H34      | Snow Cover - Full Disk      | HDF    | GEOS               | merged, flat, mountain      |
| H34_IND  | Snow Cover - Full Disk - Indian Ocean        | HDF    | GEOS_IND            | -                           |
| H35      | Snow Cover - Global      | GRIB2  | WGS84              | merged, flat, mountain      |
| H43      | Snow Cover - Full Disk      | NetCDF | GEOS_MTG            | merged, flat, mountain      |
| H43_MNT  | Snow Cover - Full Disk - Mountains   | NetCDF | GEOS_MTG            | -                           |
| H65      | Snow Water Equivalent - Global   | NetCDF | EASE               | merged, flat, mountain      |

## Installation

1. Clone the repository or download the source code.
2. Install the required dependencies using pip:

```bash
pip install -e .
```

### Dependencies

- typer
- h5py
- cfgrib / eccodes
- xarray
- gdal
- numpy
- pyyaml

## Usage

The CLI tool is designed with simplicity in mind. Use the following command structure to geocode your HSAF snow product data:

```bash
geocoder geocode -i <input_file> -o <output_file> -p <product> --crs <crs> --variant <variant>
```

### Options

| Option           | Short | Description                                                           | Default   |
|------------------|-------|-----------------------------------------------------------------------|-----------|
| `--input-file`   | `-i`  | Path to the input file                                                | Required  |
| `--output-file`  | `-o`  | Path where the output GeoTIFF will be saved                          | Required  |
| `--product`      | `-p`  | Product code (see Supported Products table)                          | Required  |
| `--crs`          |       | Target CRS: `4326` (WGS84), `GEOS`, or `EASE`                       | `4326`    |
| `--variant`      |       | Data variant: `merged`, `flat`, or `mountain`                        | `merged`  |
| `--extension`    |       | Override file extension detection: `hdf`, `grib2`, or `nc`          | Auto      |

### Examples

Geocode an H10 product file to WGS84:

```bash
geocoder geocode -i /path/to/h10_file.H5 -o /path/to/output.tif -p H10 --crs 4326
```

Geocode an H43 product with the mountain variant:

```bash
geocoder geocode -i /path/to/h43_file.nc -o /path/to/output.tif -p H43 --variant mountain
```

### Batch Conversion

Convert all matching files in a directory at once:

```bash
geocoder batch -i /path/to/input_dir -o /path/to/output_dir -p H43 --crs 4326 --variant merged
```

The batch command scans the input directory for files whose extension matches the given product, converts each one, and writes the output GeoTIFFs to the output directory. A summary of successes and failures is printed at the end.

If your input files are gzip-compressed (`.gz`), use `--decompress` to automatically extract them before processing:

```bash
geocoder batch -i /path/to/gz_files -o /path/to/output_dir -p H10 --decompress
```

The `.gz` files are decompressed in-place and removed after extraction.

### Other Commands

List all supported products:

```bash
geocoder list-products
```

## Configuration

Product definitions (projections, transforms, data shapes, expected extensions) are stored in `geocoder/config.yaml`. To add or modify a product, edit this file rather than the source code.

## Running Tests

```bash
pytest tests.py -v
```

## Troubleshooting

- Ensure your input file matches the expected format for the specified product.
- Verify the path to your input and output files is correct and accessible.
- Check that the product code, CRS, and variant are among the supported options.
- If extension auto-detection fails, specify it explicitly with `--extension`.
