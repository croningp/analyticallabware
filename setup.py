from setuptools import setup, find_packages

setup(
    name="AnalyticalLabware",
    version="0.2.5",
    description="Analytical instruments for the Chemputer",
    url="https://gitlab.com/croningroup/chemputer/analyticallabware",
    author="Hessam Mehr, Artem Leonov, Graham Keenan, Alex Hammer",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        # general "scientific"
        "scipy",
        "matplotlib",
        "numpy",
        # Chemputer related
        "SerialLabware",
        "ChemputerAPI",
    ],
    extras_require={
        "advion": [
            # TODO - remove python requirement as soon as 3.9 is fully supported
            # in pythonnet, see issue #50 for details
            "pythonnet ; python_version<'3.9'",
        ],
        "oceanoptics": [
            "seabreeze",
        ],
        "spinsolve": [
            "scipy<1.8",
            "nmrglue",
        ],
        "agilent": [],
        "all": [
            "pythonnet ; python_version<'3.9'",
            "seabreeze",
            "scipy<1.8",
            "nmrglue",
            "pytest",
        ],
        "test": [
            "pytest",
        ]
    },
    zip_safe=False,
)
