import typer
from geocoder.geocoder import Geocoder
import os
from pathlib import Path

app = typer.Typer()

# File format validation based on product - updated to match EXTENSION_DICT from geocoder.py
file_format_dict = {
    'H10': ['hdf', 'h5', 'H5'],
    'H11': ['grib2'],
    'H12': ['grib2'],
    'H13': ['grib2'],
    'H34': ['hdf', 'h5', 'H5'],
    'H35': ['grib2'],
    'H43': ['nc', 'nc4', 'netcdf'],
    'H65': ['nc', 'nc4', 'netcdf'],
    'H34_IND': ['hdf', 'h5', 'H5'],
    'H43_MNT': ['nc', 'nc4', 'netcdf']
}

# Valid variants for products that support them
variant_dict = {
    'H10': ['merged', 'flat', 'mountain'],
    'H34': ['merged', 'flat', 'mountain'],
    'H35': ['merged', 'flat', 'mountain'],
    'H43': ['merged', 'flat', 'mountain'],
    'H65': ['merged', 'flat', 'mountain']
}


def validate_file(file_path: str, product: str) -> bool:
    """Validate file existence and extension"""
    valid_extensions = file_format_dict.get(product.upper(), [])
    file_path_obj = Path(file_path)
    return file_path_obj.is_file() and any(file_path.endswith(ext) for ext in valid_extensions)


def validate_product(product: str) -> bool:
    """Validate product code"""
    valid_products = ['H10', 'H11', 'H12', 'H13', 'H34', 'H34_IND', 'H35', 'H43', 'H43_MNT', 'H65']
    return product.upper() in valid_products


def validate_crs(crs: str) -> bool:
    """Validate coordinate reference system"""
    valid_crs = ['4326', 'GEOS', 'EASE']
    return crs in valid_crs


def validate_variant(product: str, variant: str) -> bool:
    """Validate variant for products that support variants"""
    if product.upper() not in variant_dict:
        return True  # Products without variants are always valid
    return variant in variant_dict[product.upper()]


@app.command()
def geocode(
    input_file: str = typer.Option(..., "-i", "--input-file",
                                   help="Input file path. Extension should match product requirements."),
    output_file: str = typer.Option(..., "-o", "--output-file", 
                                    help="Output GeoTIFF file path."),
    product: str = typer.Option(..., "-p", "--product",
                                help="Product code. Valid products: H10, H11, H12, H13, H34, H34_IND, H35, H43, H43_MNT, H65"),
    crs: str = typer.Option('4326', "--crs",
                           help="Coordinate Reference System. Options: '4326' (WGS84), 'GEOS', 'EASE'. Default: '4326'"),
    variant: str = typer.Option('merged', "--variant",
                               help="Data variant for products that support it. Options: 'merged', 'flat', 'mountain'. Default: 'merged'"),
    extension: str = typer.Option(None, "--extension",
                                 help="Override file extension detection. Options: 'hdf', 'grib2', 'nc'. Usually auto-detected.")
):
    """
    Geocode HSAF snow products to WGS84 or other coordinate systems.
    
    This tool projects HSAF snow products from their native projections to standard
    coordinate reference systems like WGS84, GEOS, or EASE.
    """
    
    # Validate product first
    if not validate_product(product):
        valid_products = ['H10', 'H11', 'H12', 'H13', 'H34', 'H34_IND', 'H35', 'H43', 'H43_MNT', 'H65']
        typer.echo(f"Invalid product code '{product}'. Valid options: {valid_products}")
        raise typer.Exit(code=1)

    # Validate CRS
    if not validate_crs(crs):
        typer.echo(f"Invalid CRS '{crs}'. Valid options: ['4326', 'GEOS', 'EASE']")
        raise typer.Exit(code=1)

    # Validate variant
    if not validate_variant(product, variant):
        valid_variants = variant_dict.get(product.upper(), ['merged'])
        typer.echo(f"Invalid variant '{variant}' for product {product}. Valid options: {valid_variants}")
        raise typer.Exit(code=1)

    # Validate input file
    if not validate_file(input_file, product):
        expected_formats = file_format_dict.get(product.upper(), ['unknown'])
        typer.echo(f"Invalid input file '{input_file}'. Expected formats for {product}: {expected_formats}")
        typer.echo(f"Please ensure the file exists and has the correct extension.")
        raise typer.Exit(code=1)

    # Auto-detect extension if not provided
    if extension is None:
        file_path = Path(input_file)
        file_suffix = file_path.suffix.lower()
        if file_suffix in ['.h5', '.hdf']:
            extension = 'hdf'
        elif file_suffix == '.grib2':
            extension = 'grib2'
        elif file_suffix in ['.nc', '.nc4', '.netcdf']:
            extension = 'nc'
        else:
            typer.echo(f"Could not auto-detect extension for file '{input_file}'. Please specify --extension")
            raise typer.Exit(code=1)

    # Validate extension if provided
    valid_extensions = ['hdf', 'grib2', 'nc']
    if extension and extension not in valid_extensions:
        typer.echo(f"Invalid extension '{extension}'. Valid options: {valid_extensions}")
        raise typer.Exit(code=1)

    # Create output directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Display processing information
    typer.echo(f"Processing {product} product...")
    typer.echo(f"Input file: {input_file}")
    typer.echo(f"Output file: {output_file}")
    typer.echo(f"Target CRS: {crs}")
    typer.echo(f"Variant: {variant}")
    typer.echo(f"Extension: {extension}")

    # Instantiate and execute Geocoder
    try:
        geocoder = Geocoder(
            product=product,
            file=input_file,
            outfile=output_file,
            crs=crs,
            extension=extension,
            variant=variant
        )
        geocoder.project()
        typer.echo("✅ Geocoding completed successfully!")
        
    except ValueError as ve:
        typer.echo(f"❌ Validation error: {ve}")
        raise typer.Exit(code=1)
    except FileNotFoundError as fe:
        typer.echo(f"❌ File not found: {fe}")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ An error occurred during geocoding: {e}")
        raise typer.Exit(code=1)


@app.command()
def list_products():
    """List all supported HSAF products and their details."""
    products_info = [
        ("H10", "Snow Cover - Europe", "HDF", "GEOS"),
        ("H11", "Snow Cover - Global", "GRIB2", "WGS84"),
        ("H12", "Snow Cover - Global", "GRIB2", "WGS84"),
        ("H13", "Snow Cover - Global", "GRIB2", "WGS84"),
        ("H34", "Snow Cover - Europe", "HDF", "GEOS"),
        ("H34_IND", "Snow Cover - India", "HDF", "GEOS_IND"),
        ("H35", "Snow Cover - Global", "GRIB2", "WGS84"),
        ("H43", "Snow Cover - Europe", "NetCDF", "GEOS_MTG"),
        ("H43_MNT", "Snow Cover - Mountains", "NetCDF", "GEOS_MTG"),
        ("H65", "Snow Water Equivalent", "NetCDF", "EASE")
    ]
    
    typer.echo("Supported HSAF Snow Products:")
    typer.echo("-" * 60)
    typer.echo(f"{'Product':<8} {'Description':<20} {'Format':<8} {'Projection':<12}")
    typer.echo("-" * 60)
    
    for product, desc, format_type, proj in products_info:
        typer.echo(f"{product:<8} {desc:<20} {format_type:<8} {proj:<12}")


if __name__ == "__main__":
    app()