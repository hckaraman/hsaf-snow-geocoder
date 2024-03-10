import typer
from geocoder.geocoder import Geocoder
import os
from pathlib import Path

app = typer.Typer()

# File format validation based on product
file_format_dict = {
    'H10': ['hdf', 'h5', 'H5'],
    'H34': ['hdf', 'h5', 'H5'],
    'H13': ['grib2'],
    'H11': ['grib2'],
    'H12': ['grib2'],
    'H35': ['grib2']
}


# Function to validate file existence and type
def validate_file(file_path: str, product: str) -> bool:
    valid_extensions = file_format_dict.get(product.upper(), '')
    return Path(file_path).is_file() and any(file_path.endswith(ext) for ext in valid_extensions)


# Function to validate product
def validate_product(product: str) -> bool:
    valid_products = ['H10', 'H11', 'H34', 'H13', 'H12', 'H35']
    return product.upper() in valid_products


def validate_crs(crs: str) -> bool:
    valid_crs = ['4326', 'GEOS']
    return crs in valid_crs


@app.command()
def geocode(input_file: str = typer.Option(..., "-i", "--input-file",
                                           help="'H10' and 'H34' expect HDF files, others expect GRIB2."),
            output_file: str = typer.Option(..., "-o", "--output-file", help="Geotiff file to be created."),
            product: str = typer.Option(..., "-p", "--product",
                                        help="Product code. Valid products are ['H10', 'H34', 'H13', 'H12', 'H35']. "),
            crs: str = typer.Option('4326', "--crs",
                                    help="Coordinate Reference System, default to 4326, H10 and H34 can also be projected to default GEOS projection.")):
    # Validate product first to ensure we check the file with the correct expected format
    if not validate_product(product):
        typer.echo(f"Invalid product code. Valid options are: ['H10', 'H34', 'H13', 'H12', 'H35'].")
        raise typer.Exit(code=1)

    if not validate_crs(crs):
        typer.echo(f"Invalid crs code. Valid options are: ['4326' , 'GEOS'].")
        raise typer.Exit(code=1)

    # Validate input file
    if not validate_file(input_file, product):
        expected_format = file_format_dict.get(product.upper(), 'unknown format')
        typer.echo(f"Invalid input file. Please ensure it is a {expected_format} file and try again.")
        raise typer.Exit(code=1)

    # Instantiate and execute Geocoder
    try:
        geocoder = Geocoder(product, input_file, output_file, crs)
        geocoder.project()
        typer.echo("Geocoding complete.")
    except Exception as e:
        typer.echo(f"An error occurred during geocoding: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
