from setuptools import setup, find_packages

setup(
    name="AnalyticalLabware",
    version="0.2.2",
    description="Analytical instruments for the Chemputer",
    url="https://gitlab.com/croningroup/chemputer/analyticallabware",
    author="Hessam Mehr, Artem Leonov, Graham Keenan, Alex Hammer",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "SerialLabware"
    ],
    zip_safe=False
)
