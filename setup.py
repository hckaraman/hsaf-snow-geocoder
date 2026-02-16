from setuptools import setup, find_packages

setup(
    name='geocoder-cli',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    package_data={'geocoder': ['config.yaml']},
    install_requires=[
        'typer',
        'h5py',
        'cfgrib',
        'eccodes',
        'xarray',
        'gdal',
        'numpy',
        'pyyaml',
        'pytest',
        'pytest-mock'
    ],
    entry_points={
        'console_scripts': [
            'geocoder=geocoder_app:app',
        ],
    },
)
