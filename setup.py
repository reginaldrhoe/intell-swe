from setuptools import setup, find_packages

setup(
    name="rag_poc",
    version="2.4.0",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
)
