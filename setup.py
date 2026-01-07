"""
Setup configuration for Quip Folder Mirror.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="quip-folder-mirror",
    version="0.1.0",
    author="Amazon Developer",
    author_email="developer@amazon.com",
    description="CLI tool for mirroring Quip folders to local filesystem",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/amazon/quip-folder-mirror",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0", 
            "pytest-cov>=4.0.0",
            "responses>=0.22.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "cli": [
            "click>=8.0.0",
            "tqdm>=4.64.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "quip-mirror=quip_mirror.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)