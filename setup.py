#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

setup(
    name="sardana_linkam",
    version="1.0.4",
    author="ALBA Controls Group",
    author_email="controls@cells.es",
    maintainer="Gabriel Jover-Manas",
    maintainer_email="gjover@cells.es",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
    ],
    url="https://github.com/ALBA-Synchrotron/sardana-linkam",
    packages=find_packages(),
    description="sardana linkam controllers & macros",
    license="GPLv3",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="linkam,sardana",
    python_requires=">=3.5",
    install_requires=["sardana", "pytango"]
)
