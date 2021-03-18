from setuptools import setup, find_packages

setup(
    name="AnalyticalLabware",
    version="0.2.4",
    description="Analytical instruments for the Chemputer",
    url="https://gitlab.com/croningroup/chemputer/analyticallabware",
    author="Hessam Mehr, Artem Leonov, Graham Keenan, Alex Hammer",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "scipy",
        "matplotlib",
        "seabreeze",
        "numpy",
        "nmrglue",
        "pytest",
        # TODO - remove python requirement as soon as 3.9 is fully supported in pythonnet
        # see issue #50 for details
        "pythonnet ; python_version<'3.9'",
        # Chemputer related
        "SerialLabware",
        "ChemputerAPI",
    ],
    zip_safe=False,
)
