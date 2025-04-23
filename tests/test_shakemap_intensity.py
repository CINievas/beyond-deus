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

import os
from beyonddeus.shakemap import Shakemaps


def test_intensity_from_shakemap():

    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    # 1
    target_lon = 13.55
    target_lat = 36.1
    expected = (
        {"PGA": 0.1, "SA(0.3)": 0.2, "SA(0.6)": 0.3, "SA(1.0)": 0.4},
        {"PGA": "g", "SA(0.3)": "g", "SA(0.6)": "g", "SA(1.0)": "g"}
    )

    returned = intensity_provider.get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected[0].keys()):
        assert round(returned[0][im], 5) == round(expected[0][im], 5)
        assert returned[1][im] == expected[1][im]

    # 2, point too far away
    target_lon = 12.5
    target_lat = 36.1
    expected = (
        {"PGA": 0.0, "SA(0.3)": 0.0, "SA(0.6)": 0.0, "SA(1.0)": 0.0},
        {"PGA": "g", "SA(0.3)": "g", "SA(0.6)": "g", "SA(1.0)": "g"}
    )

    returned = intensity_provider.get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected[0].keys()):
        assert round(returned[0][im], 5) == round(expected[0][im], 5)
        assert returned[1][im] == expected[1][im]
