from setuptools import find_packages, setup


setup(
    name="starcloud_integration",
    version="0.1.0",
    description="Native ERPNext integration boundary for Starcloud",
    author="Skychip",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[],
)