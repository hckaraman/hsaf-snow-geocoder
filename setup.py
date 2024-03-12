from setuptools import setup, find_packages

setup(
    name='geocoder-cli',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'typer',
        'h5py',
        'pygrib',
        'xarray',
        'gdal',
        'numpy',
        'tqdm',
        'pytest',
        'pytest-mock'
    ],
    entry_points={
        'console_scripts': [
            'geocoder=geocoder_app:app',
        ],
    },
)
