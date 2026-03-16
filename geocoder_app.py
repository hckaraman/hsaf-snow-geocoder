import gzip
import shutil
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
    'H43_MNT': ['nc', 'nc4', 'netcdf'],
    'H43_HR': ['hdf', 'h5', 'H5']
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
    valid_products = ['H10', 'H11', 'H12', 'H13', 'H34', 'H34_IND', 'H35', 'H43', 'H43_HR', 'H43_MNT', 'H65']
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


def detect_extension(file_path: str) -> str:
    """Auto-detect the geocoder extension string from a file's suffix."""
    suffix = Path(file_path).suffix.lower()
    if suffix in ['.h5', '.hdf']:
        return 'hdf'
    elif suffix == '.grib2':
        return 'grib2'
    elif suffix in ['.nc', '.nc4', '.netcdf']:
        return 'nc'
    return None


def _decompress_gz_files(directory: Path) -> int:
    """Decompress all .gz files in a directory in-place. Returns count of files decompressed."""
    count = 0
    for gz_file in sorted(directory.glob('*.gz')):
        out_file = gz_file.with_suffix('')  # strip .gz
        with gzip.open(gz_file, 'rb') as f_in, open(out_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        gz_file.unlink()
        typer.echo(f"  UNZIP {gz_file.name}")
        count += 1
    return count


def _validate_common(product, crs, variant):
    """Validate product, CRS, and variant. Returns error message or None."""
    if not validate_product(product):
        valid_products = ['H10', 'H11', 'H12', 'H13', 'H34', 'H34_IND', 'H35', 'H43', 'H43_HR', 'H43_MNT', 'H65']
        return f"Invalid product code '{product}'. Valid options: {valid_products}"

    if not validate_crs(crs):
        return f"Invalid CRS '{crs}'. Valid options: ['4326', 'GEOS', 'EASE']"

    if not validate_variant(product, variant):
        valid_variants = variant_dict.get(product.upper(), ['merged'])
        return f"Invalid variant '{variant}' for product {product}. Valid options: {valid_variants}"

    return None


@app.command()
def geocode(
    input_file: str = typer.Option(..., "-i", "--input-file",
                                   help="Input file path. Extension should match product requirements."),
    output_file: str = typer.Option(..., "-o", "--output-file",
                                    help="Output GeoTIFF file path."),
    product: str = typer.Option(..., "-p", "--product",
                                help="Product code. Valid products: H10, H11, H12, H13, H34, H34_IND, H35, H43, H43_HR, H43_MNT, H65"),
    crs: str = typer.Option('4326', "--crs",
                           help="Coordinate Reference System. Options: '4326' (WGS84), 'GEOS', 'EASE'. Default: '4326'"),
    variant: str = typer.Option('merged', "--variant",
                               help="Data variant for products that support it. Options: 'merged', 'flat', 'mountain'. Default: 'merged'"),
    extension: str = typer.Option(None, "--extension",
                                 help="Override file extension detection. Options: 'hdf', 'grib2', 'nc'. Usually auto-detected.")
):
    """
    Geocode a single HSAF snow product file to WGS84 or other coordinate systems.
    """

    # Validate common parameters
    error = _validate_common(product, crs, variant)
    if error:
        typer.echo(error)
        raise typer.Exit(code=1)

    # Validate input file
    if not validate_file(input_file, product):
        expected_formats = file_format_dict.get(product.upper(), ['unknown'])
        typer.echo(f"Invalid input file '{input_file}'. Expected formats for {product}: {expected_formats}")
        typer.echo(f"Please ensure the file exists and has the correct extension.")
        raise typer.Exit(code=1)

    # Auto-detect extension if not provided
    if extension is None:
        extension = detect_extension(input_file)
        if extension is None:
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
        typer.echo("Geocoding completed successfully!")

    except ValueError as ve:
        typer.echo(f"Validation error: {ve}")
        raise typer.Exit(code=1)
    except FileNotFoundError as fe:
        typer.echo(f"File not found: {fe}")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An error occurred during geocoding: {e}")
        raise typer.Exit(code=1)


@app.command()
def batch(
    input_dir: str = typer.Option(..., "-i", "--input-dir",
                                  help="Directory containing input files to process."),
    output_dir: str = typer.Option(..., "-o", "--output-dir",
                                   help="Directory where output GeoTIFF files will be saved."),
    product: str = typer.Option(..., "-p", "--product",
                                help="Product code applied to all files. Valid products: H10, H11, H12, H13, H34, H34_IND, H35, H43, H43_MNT, H65"),
    crs: str = typer.Option('4326', "--crs",
                           help="Coordinate Reference System. Options: '4326' (WGS84), 'GEOS', 'EASE'. Default: '4326'"),
    variant: str = typer.Option('merged', "--variant",
                               help="Data variant. Options: 'merged', 'flat', 'mountain'. Default: 'merged'"),
    extension: str = typer.Option(None, "--extension",
                                 help="Override file extension detection. Options: 'hdf', 'grib2', 'nc'. Usually auto-detected."),
    decompress: bool = typer.Option(False, "--decompress",
                                    help="Decompress .gz files in the input directory before processing.")
):
    """
    Batch geocode all matching files in a directory.

    Scans the input directory for files whose extension matches the given product
    and converts each one to a GeoTIFF in the output directory.
    Use --decompress to automatically gunzip .gz files first.
    """

    # Validate common parameters
    error = _validate_common(product, crs, variant)
    if error:
        typer.echo(error)
        raise typer.Exit(code=1)

    input_path = Path(input_dir)
    if not input_path.is_dir():
        typer.echo(f"Input directory not found: {input_dir}")
        raise typer.Exit(code=1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Decompress .gz files if requested
    if decompress:
        count = _decompress_gz_files(input_path)
        if count:
            typer.echo(f"Decompressed {count} file(s)")

    # Collect matching files
    valid_suffixes = file_format_dict.get(product.upper(), [])
    files = sorted([
        f for f in input_path.iterdir()
        if f.is_file() and any(f.name.endswith(ext) for ext in valid_suffixes)
    ])

    if not files:
        typer.echo(f"No matching files found in '{input_dir}' for product {product} (expected extensions: {valid_suffixes})")
        raise typer.Exit(code=1)

    typer.echo(f"Found {len(files)} file(s) for product {product} in '{input_dir}'")
    typer.echo(f"Target CRS: {crs} | Variant: {variant}")
    typer.echo("-" * 60)

    succeeded = 0
    failed = 0

    for filepath in files:
        outfile = output_path / filepath.with_suffix('.tif').name

        # Detect extension per file if not overridden
        ext = extension
        if ext is None:
            ext = detect_extension(str(filepath))
            if ext is None:
                typer.echo(f"  SKIP {filepath.name} (unknown extension)")
                failed += 1
                continue

        try:
            geocoder = Geocoder(
                product=product,
                file=str(filepath),
                outfile=str(outfile),
                crs=crs,
                extension=ext,
                variant=variant
            )
            geocoder.project()
            typer.echo(f"  OK   {filepath.name} -> {outfile.name}")
            succeeded += 1
        except Exception as e:
            typer.echo(f"  FAIL {filepath.name}: {e}")
            failed += 1

    typer.echo("-" * 60)
    typer.echo(f"Done. {succeeded} succeeded, {failed} failed out of {len(files)} file(s).")

    if failed > 0:
        raise typer.Exit(code=1)


@app.command()
def list_products():
    """List all supported HSAF products and their details."""
    products_info = [
        ("H10", "Snow Cover - Europe", "HDF", "GEOS"),
        ("H11", "Snow Cover - Europe", "GRIB2", "WGS84"),
        ("H12", "Snow Cover - Europe", "GRIB2", "WGS84"),
        ("H13", "Snow Cover - Europe", "GRIB2", "WGS84"),
        ("H34", "Snow Cover - Full Disk", "HDF", "GEOS"),
        ("H34_IND", "Snow Cover - Full Disk Indian Ocean", "HDF", "GEOS_IND"),
        ("H35", "Snow Cover - Global", "GRIB2", "WGS84"),
        ("H43", "Snow Cover - Full Disk", "NetCDF", "GEOS_MTG"),
        ("H43_HR", "Snow Cover - Full Disk 1km", "HDF", "GEOS_MTG"),
        ("H43_MNT", "Snow Cover - Full Disk - Mountains", "NetCDF", "GEOS_MTG"),
        ("H65", "Snow Water Equivalent - Global", "NetCDF", "EASE")
    ]

    typer.echo("Supported HSAF Snow Products:")
    typer.echo("-" * 60)
    typer.echo(f"{'Product':<8} {'Description':<20} {'Format':<8} {'Projection':<12}")
    typer.echo("-" * 60)

    for product, desc, format_type, proj in products_info:
        typer.echo(f"{product:<8} {desc:<20} {format_type:<8} {proj:<12}")


if __name__ == "__main__":
    app()
