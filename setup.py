from setuptools import setup, find_packages

setup(
    name='geocoder-cli',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'typer',
        # other dependencies
    ],
    entry_points={
        'console_scripts': [
            'geocoder=geocoder_app:app',
        ],
    },
)