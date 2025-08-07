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
from beyonddeus.tsunami_netcdf_reader import TSU_NetCDF_fields


def test_intensity_from_TSU_NetCD():

    intensity_provider = TSU_NetCDF_fields(
        os.path.join(os.path.dirname(__file__), "data", "TSU_inundation_fields_test.nc"),
    ).to_intensity_provider()

    # 1
    target_lon = 14.86
    target_lat = 37.04
    expected = {"max_inundation_depth": 3.25}

    returned = intensity_provider.get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected.keys()):
        assert round(returned[im], 5) == round(expected[im], 5)

    # 2, point too far away
    target_lon = 13.5
    target_lat = 37.0
    expected = {"max_inundation_depth": 0.0}

    returned = intensity_provider.get_nearest(target_lon, target_lat)

    for i, im in enumerate(expected.keys()):
        assert round(returned[im], 5) == round(expected[im], 5)

    # 3, identify nearest neighbour positions
    target_locations = np.array([
        [14.86, 37.04], [14.84, 37.06], [16.0, 37.0], [14.6, 36.79], [-14.0, -36.0]
    ])
    returned_nearest_neighbours = intensity_provider.identify_nearest_neighbours(
        target_locations
    )

    expected_nearest_neighbours = np.array([11, 9, -999, 1, -999])

    for i in range(expected_nearest_neighbours.shape[0]):
        assert returned_nearest_neighbours[i] == expected_nearest_neighbours[i]

    expected_im_values = [
        {"max_inundation_depth": 3.25},
        {"max_inundation_depth": 2.75},
        {"max_inundation_depth": 0.00},
        {"max_inundation_depth": 0.75},
        {"max_inundation_depth": 0.00}
    ]

    for i in range(expected_nearest_neighbours.shape[0]):

        returned_ims = intensity_provider.get_values_at_position(
            expected_nearest_neighbours[i]
        )

        for im_type in expected_im_values[i]:
            assert round(returned_ims[im_type], 5) == round(expected_im_values[i][im_type], 5)
