from setuptools import setup, find_packages

setup(
    name="intell_swe",
    version="3.0.0",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    description="Intelligent Software Engineering Framework - Enterprise Multiuser AI Code Analysis",
    author="Reginald Rhoe",
    python_requires=">=3.11",
)
