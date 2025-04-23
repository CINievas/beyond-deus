#!/usr/bin/env python3

# Copyright (C) 2025:
#  GFZ Helmholtz-Zentrum für Geoforschung | GFZ Helmholtz Centre for Geosciences
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

from setuptools import setup, find_packages

tests_require = ["pytest"]

setup(
    name="beyonddeus",
    version="0.1.0",
    description="",
    keywords="multi-hazard, multi-risk, damage assessment, loss assessment",
    author="Cecilia Nievas",
    license="AGPLv3+",
    install_requires=[
        "pyyaml>=6.0.2",
        "numpy>=2.2.5",
        "scipy>=1.15.2",
        "lxml>=5.4",
    ],
    extras_require={
        "tests": tests_require,
    },
    packages=find_packages(),
    entry_points={"console_scripts": ["beyonddeus = beyonddeus.beyonddeus:main"]},
    python_requires=">=3.12",
)
