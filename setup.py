from setuptools import setup, find_packages

setup(
    name="rag_poc",
    version="0.0.0",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
)
