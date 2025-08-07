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
import pandas as pd
from beyonddeus.shakemap import Shakemaps


def test_get_values_at_multiple_positions():

    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    # Prepare the input
    building_ids = ["bdg_1", "bdg_2", "bdg_3", "bdg_4", "bdg_5"]
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": np.array([8, 11, -999, 11, -999])},
        index=building_ids
    )
    intensity_positions.index.name = "building_id"

    intensity_threshold = 0.12

    # Prepare the expected output
    expected_im_values = [
        {"PGA": 0.10, "SA(0.3)": 0.20, "SA(0.6)": 0.30, "SA(1.0)": 0.40},
        {"PGA": 0.15, "SA(0.3)": 0.25, "SA(0.6)": 0.35, "SA(1.0)": 0.45},
        {"PGA": 0.00, "SA(0.3)": 0.00, "SA(0.6)": 0.00, "SA(1.0)": 0.00},
        {"PGA": 0.15, "SA(0.3)": 0.25, "SA(0.6)": 0.35, "SA(1.0)": 0.45},
        {"PGA": 0.00, "SA(0.3)": 0.00, "SA(0.6)": 0.00, "SA(1.0)": 0.00}
    ]

    expected_intensities = intensity_positions.copy()
    expected_intensities = pd.concat(
        (
            expected_intensities,
            pd.DataFrame(
                expected_im_values,
                index=building_ids
            )
        ),
        axis=1
    )
    expected_intensities["run"] = [True, True, False, True, False]

    # Run 'get_values_at_multiple_positions'
    returned_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    assert returned_intensities.shape == expected_intensities.shape

    cols_equal = ["nearest_neighbour", "run"]
    cols_float = ["PGA", "SA(0.3)", "SA(0.6)", "SA(1.0)"]

    for bdg_id in expected_intensities.index:
        for col in cols_equal:
            assert (
                returned_intensities.loc[bdg_id, col] == expected_intensities.loc[bdg_id, col]
            )

    for bdg_id in expected_intensities.index:
        for col in cols_float:
            assert (
                round(returned_intensities.loc[bdg_id, col], 5) == 
                round(expected_intensities.loc[bdg_id, col], 5)
            )
