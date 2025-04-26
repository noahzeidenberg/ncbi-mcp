#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="ncbi-mcp",
    version="2.0.0",
    description="NCBI Model Context Protocol (MCP) adapter for Cursor and Claude Desktop",
    author="Noah Zeidenberg",
    author_email="happyomics@gmail.com",
    url="https://github.com/noahzeidenberg/ncbi-mcp",
    packages=find_packages(),
    install_requires=[
        "modelcontextprotocol>=0.1.0",
        "requests>=2.31.0",
        "python-dotenv>=0.19.0",
        "argparse>=1.4.0",
    ],
    entry_points={
        "console_scripts": [
            "ncbi-mcp=ncbi_mcp:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    python_requires=">=3.8",
) 