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
import numpy as np
from beyonddeus.earthquake_hdf_reader import EQ_HDF_fields


def test_intensity_from_shakemap():

    intensity_provider = EQ_HDF_fields(
        os.path.join(os.path.dirname(__file__), "data", "EQ_ground_motion_fields_test.hdf5"),
    ).to_intensity_provider()

    # 1
    gmpe_name = "GMPE1"
    realisation = 0
    target_lon = 13.55
    target_lat = 36.1
    expected = (
        {"PGA": 0.1, "SA(0.3)": 0.2, "SA(0.6)": 0.3, "SA(1.0)": 0.4},
        {"PGA": "g", "SA(0.3)": "g", "SA(0.6)": "g", "SA(1.0)": "g"}
    )

    returned = intensity_provider[gmpe_name][realisation].get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected[0].keys()):
        assert round(returned[0][im], 5) == round(expected[0][im], 5)
        assert returned[1][im] == expected[1][im]

    # 2, same as # 1, but for a different GMPE name and realisation number
    gmpe_name = "GMPE2"
    realisation = 2
    target_lon = 13.55
    target_lat = 36.1
    expected = (
        {"PGA": 0.6, "SA(0.3)": 1.2, "SA(0.6)": 1.8, "SA(1.0)": 2.4},
        {"PGA": "g", "SA(0.3)": "g", "SA(0.6)": "g", "SA(1.0)": "g"}
    )

    returned = intensity_provider[gmpe_name][realisation].get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected[0].keys()):
        assert round(returned[0][im], 5) == round(expected[0][im], 5)
        assert returned[1][im] == expected[1][im]

    # 3, point too far away
    gmpe_name = "GMPE1"
    realisation = 0
    target_lon = 12.5
    target_lat = 36.1
    expected = (
        {"PGA": 0.0, "SA(0.3)": 0.0, "SA(0.6)": 0.0, "SA(1.0)": 0.0},
        {"PGA": "g", "SA(0.3)": "g", "SA(0.6)": "g", "SA(1.0)": "g"}
    )

    returned = intensity_provider[gmpe_name][realisation].get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected[0].keys()):
        assert round(returned[0][im], 5) == round(expected[0][im], 5)
        assert returned[1][im] == expected[1][im]

    # 4, identify nearest neighbour positions
    gmpe_name = "GMPE1"
    realisation = 0
    target_locations = np.array([
        [14.6, 37.1], [14.9, 36.9], [16.0, 37.0], [15.5, 37.0], [-14.0, -36.0]
    ])
    returned_nearest_neighbours = intensity_provider[
        gmpe_name
    ][realisation].identify_nearest_neighbours(target_locations)

    expected_nearest_neighbours = np.array([8, 11, -999, 11, -999])

    for i in range(expected_nearest_neighbours.shape[0]):
        assert returned_nearest_neighbours[i] == expected_nearest_neighbours[i]

    expected_im_values = [
        {"PGA": 0.10, "SA(0.3)": 0.20, "SA(0.6)": 0.30, "SA(1.0)": 0.40},
        {"PGA": 0.15, "SA(0.3)": 0.25, "SA(0.6)": 0.35, "SA(1.0)": 0.45},
        {"PGA": 0.00, "SA(0.3)": 0.00, "SA(0.6)": 0.00, "SA(1.0)": 0.00},
        {"PGA": 0.15, "SA(0.3)": 0.25, "SA(0.6)": 0.35, "SA(1.0)": 0.45},
        {"PGA": 0.00, "SA(0.3)": 0.00, "SA(0.6)": 0.00, "SA(1.0)": 0.00}
    ]

    for i in range(expected_nearest_neighbours.shape[0]):

        returned_ims, returned_units = intensity_provider[
            gmpe_name][realisation
                      ].get_values_at_position(expected_nearest_neighbours[i])

        for im_type in expected_im_values[i]:
            assert round(returned_ims[im_type], 5) == round(expected_im_values[i][im_type], 5)
            assert returned_units[im_type] == "g"
