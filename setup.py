#!/usr/bin/env python3
"""
Setup script for pinkweather - Weather Display System

Provides backward compatibility for older Python packaging systems.
For modern installations, prefer pyproject.toml.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return 'Weather display system for e-ink displays with web development interface'

# Read requirements
def read_requirements(filename):
    req_path = os.path.join(os.path.dirname(__file__), filename)
    requirements = []
    if os.path.exists(req_path):
        with open(req_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-r'):
                    requirements.append(line)
    return requirements

setup(
    name='pinkweather',
    version='0.1.0',
    description='Weather display system for e-ink displays with web development interface',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='Weather Display Developer',
    author_email='developer@example.com',
    url='https://github.com/yourusername/pinkweather',

    # Package discovery
    packages=find_packages(),
    py_modules=[
        'display_renderer',
        'http_server',
        'weather_example',
    ],

    # Include non-Python files
    package_data={
        '': ['*.ttf', '*.bmp', 'README.md', 'requirements*.txt'],
    },
    include_package_data=True,

    # Dependencies
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'dev': read_requirements('requirements-dev.txt'),
    },

    # Python version requirement
    python_requires='>=3.8',

    # Entry points for command-line scripts
    entry_points={
        'console_scripts': [
            'weather-server=http_server:run_server',
            'weather-preview=weather_example:main',
        ],
    },

    # Classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: System :: Hardware',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Scientific/Engineering :: Atmospheric Science',
    ],

    # Keywords for package discovery
    keywords='weather display eink epaper circuitpython raspberry-pi pico',

    # Project URLs
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/pinkweather/issues',
        'Source': 'https://github.com/yourusername/pinkweather',
        'Documentation': 'https://github.com/yourusername/pinkweather#readme',
    },

    # License
    license='MIT',

    # Zip safe
    zip_safe=False,
)
