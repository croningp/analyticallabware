from setuptools import setup, find_packages

setup(name="AnalyticalLabware",
      version="0.1",
      description="Analytical instruments for the Chemputer",
      url="http://datalore.chem.gla.ac.uk/Chemputer/AnalyticalLabware",
      author="Hessam Mehr, Artem Leonov",
      license="MIT",
      packages=find_packages(),
      install_requires=[
            "SerialLabware",
            "advion-wrapper",
            "matplotlib",
            "numpy",
            "pytest"],
      zip_safe=False)
