#!/usr/bin/env python
# encoding: utf-8

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
   requirements = fh.readlines()

setuptools.setup(
    name="WOSRaw",
    version="0.1.1",
    author="Filipi N. Silva",
    author_email="filipi@iu.edu",
    description="Collection of utilities to process raw XML data from the Web of Science",
    install_requires=[req for req in requirements if req[:2] != "# "],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/filipinascimento/WOSRaw",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)