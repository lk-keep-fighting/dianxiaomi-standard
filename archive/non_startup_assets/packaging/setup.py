#!/usr/bin/env python3
"""
Setup script for Digital Chief Automation project
"""

from setuptools import setup, find_packages

# Read the requirements from requirements.txt
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read the README for long description
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="digital-chief-automation",
    version="1.0.0",
    description="Browser automation tool for digital marketing and data extraction using Playwright",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Digital Chief Team",
    python_requires=">=3.7",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],
    entry_points={
        "console_scripts": [
            "digital-chief=src.main:main",
        ],
    },
)