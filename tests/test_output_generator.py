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
import pandas as pd
from beyonddeus.output_generator import damage_by_building_id_as_columns


def test_damage_by_building_id_as_columns():

    updated_exposure = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__),
            "data", "exposure_for_damage_by_building_id_as_columns.csv"
        )
    )

    returned_damage_by_bdg_id = damage_by_building_id_as_columns(updated_exposure)

    expected_damage_by_bdg_id = pd.DataFrame(
        {
            "number": [126.0, 12.0],
            "number_D0": [10.0, 12.0],
            "number_D1": [32.0, 0.0],
            "number_D2": [34.0, 0.0],
            "number_D3": [36.0, 0.0],
            "number_D4": [14.0, 0.0],
            "proportion_D0": [0.079365, 1.0],
            "proportion_D1": [0.253968, 0.0],
            "proportion_D2": [0.269841, 0.0],
            "proportion_D3": [0.285714, 0.0],
            "proportion_D4": [0.111111, 0.0],
        },
        index=["B1", "B2"]
    )
    expected_damage_by_bdg_id.index.name = "building_id"

    assert returned_damage_by_bdg_id.shape[0] == expected_damage_by_bdg_id.shape[0]
    assert returned_damage_by_bdg_id.shape[1] == expected_damage_by_bdg_id.shape[1]

    for bdg_id in expected_damage_by_bdg_id.index:
        for col in expected_damage_by_bdg_id.columns:
            assert (
                round(returned_damage_by_bdg_id.loc[bdg_id, col], 6) ==
                round(expected_damage_by_bdg_id.loc[bdg_id, col], 6)
            )
