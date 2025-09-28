from setuptools import find_packages
from setuptools import setup

setup(
    name="cauldron",
    version="0.0.1",
    packages=find_packages("cauldron"),
    package_dir={"": "cauldron"},
    author="Tommy Kardach",
    author_email="tommy@kardach.com",
)
