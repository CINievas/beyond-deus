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
from beyonddeus.output_generator import (
    damage_by_building_id_as_columns, split_updated_exposure_by_usability,
    filter_damage_by_bdg_id_only_transitioned
)


def test_damage_by_building_id_as_columns():

    updated_exposure = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__),
            "data", "exposure_for_damage_by_building_id_as_columns.csv"
        )
    )

    expected_damage_by_bdg_id = pd.DataFrame(
        {
            "number": [126.0, 12.0],
            "number_usable": [42.0, 12.0],
            "number_unusable": [84.0, 0.0],
            "proportion_usable": [0.3333333333, 1.0],
            "proportion_unusable": [0.6666666667, 0.0],
            "ppl_census_usable": [84.0, 24.0],
            "ppl_census_unusable": [168.0, 0.0],
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
            "ppl_census_D0": [20.0, 24.0],
            "ppl_census_D1": [64.0, 0.0],
            "ppl_census_D2": [68.0, 0.0],
            "ppl_census_D3": [72.0, 0.0],
            "ppl_census_D4": [28.0, 0.0],            
        },
        index=["B1", "B2"]
    )
    expected_damage_by_bdg_id.index.name = "building_id"

    # Including census people
    returned_damage_by_bdg_id = damage_by_building_id_as_columns(
        updated_exposure, include_people=True
    )

    assert returned_damage_by_bdg_id.shape[0] == expected_damage_by_bdg_id.shape[0]
    assert returned_damage_by_bdg_id.shape[1] == expected_damage_by_bdg_id.shape[1]

    for bdg_id in expected_damage_by_bdg_id.index:
        for col in expected_damage_by_bdg_id.columns:
            assert (
                round(returned_damage_by_bdg_id.loc[bdg_id, col], 6) ==
                round(expected_damage_by_bdg_id.loc[bdg_id, col], 6)
            )

    # Excluding census people
    for dmg_state in range(5):
        del expected_damage_by_bdg_id["ppl_census_D%s" % (dmg_state)]
    del expected_damage_by_bdg_id["ppl_census_usable"]
    del expected_damage_by_bdg_id["ppl_census_unusable"]

    returned_damage_by_bdg_id = damage_by_building_id_as_columns(
        updated_exposure, include_people=False
    )

    assert returned_damage_by_bdg_id.shape[0] == expected_damage_by_bdg_id.shape[0]
    assert returned_damage_by_bdg_id.shape[1] == expected_damage_by_bdg_id.shape[1]

    for bdg_id in expected_damage_by_bdg_id.index:
        for col in expected_damage_by_bdg_id.columns:
            assert (
                round(returned_damage_by_bdg_id.loc[bdg_id, col], 6) ==
                round(expected_damage_by_bdg_id.loc[bdg_id, col], 6)
            )

    # Case in which one usability value does not exist in the input DataFrame
    updated_exposure_usable = updated_exposure[updated_exposure.cum_usability == 1]

    expected_damage_by_bdg_id = pd.DataFrame(
        {
            "number": [42.0, 12.0],
            "number_usable": [42.0, 12.0],
            "number_unusable": [0.0, 0.0],
            "proportion_usable": [1.0, 1.0],
            "proportion_unusable": [0.0, 0.0],
            "ppl_census_usable": [84.0, 24.0],
            "ppl_census_unusable": [0.0, 0.0],
            "number_D0": [10.0, 12.0],
            "number_D1": [32.0, 0.0],
            "proportion_D0": [0.238095238, 1.0],
            "proportion_D1": [0.761904762, 0.0],
            "ppl_census_D0": [20.0, 24.0],
            "ppl_census_D1": [64.0, 0.0]
        },
        index=["B1", "B2"]
    )
    expected_damage_by_bdg_id.index.name = "building_id"

    # Including census people
    returned_damage_by_bdg_id = damage_by_building_id_as_columns(
        updated_exposure_usable, include_people=True
    )

    assert returned_damage_by_bdg_id.shape[0] == expected_damage_by_bdg_id.shape[0]
    assert returned_damage_by_bdg_id.shape[1] == expected_damage_by_bdg_id.shape[1]

    for bdg_id in expected_damage_by_bdg_id.index:
        for col in expected_damage_by_bdg_id.columns:
            assert (
                round(returned_damage_by_bdg_id.loc[bdg_id, col], 6) ==
                round(expected_damage_by_bdg_id.loc[bdg_id, col], 6)
            )


def test_filter_damage_by_bdg_id_only_transitioned():

    updated_exposure = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__),
            "data", "exposure_for_damage_by_building_id_as_columns.csv"
        )
    )

    returned_damage_by_bdg_id = damage_by_building_id_as_columns(
        updated_exposure, include_people=True
    )

    filtered_damage_by_bdg_id = filter_damage_by_bdg_id_only_transitioned(
        updated_exposure, returned_damage_by_bdg_id
    )

    expected_damage_by_bdg_id = pd.DataFrame(
        {
            "number": [126.0],
            "number_usable": [42.0],
            "number_unusable": [84.0],
            "proportion_usable": [0.3333333333],
            "proportion_unusable": [0.6666666667],
            "ppl_census_usable": [84.0],
            "ppl_census_unusable": [168.0],
            "number_D0": [10.0],
            "number_D1": [32.0],
            "number_D2": [34.0],
            "number_D3": [36.0],
            "number_D4": [14.0],
            "proportion_D0": [0.079365],
            "proportion_D1": [0.253968],
            "proportion_D2": [0.269841],
            "proportion_D3": [0.285714],
            "proportion_D4": [0.111111],
            "ppl_census_D0": [20.0],
            "ppl_census_D1": [64.0],
            "ppl_census_D2": [68.0],
            "ppl_census_D3": [72.0],
            "ppl_census_D4": [28.0],
        },
        index=["B1"]
    )
    expected_damage_by_bdg_id.index.name = "building_id"

    assert filtered_damage_by_bdg_id.shape[0] == expected_damage_by_bdg_id.shape[0]
    assert filtered_damage_by_bdg_id.shape[1] == expected_damage_by_bdg_id.shape[1]

    for bdg_id in expected_damage_by_bdg_id.index:
        for col in expected_damage_by_bdg_id.columns:
            assert (
                round(filtered_damage_by_bdg_id.loc[bdg_id, col], 6) ==
                round(expected_damage_by_bdg_id.loc[bdg_id, col], 6)
            )


def test_split_updated_exposure_by_usability():

    updated_exposure = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__),
            "data", "expected_updated_exposure_damage_losses_with_previous_loss.csv"
        )
    )

    returned_usable_assets, returned_unusable_assets = split_updated_exposure_by_usability(
        updated_exposure
    )

    assert returned_usable_assets.shape[0] == 8
    assert returned_unusable_assets.shape[0] == 12

    assert round(returned_usable_assets["number"].sum(), 6) == 7.998594
    assert round(returned_unusable_assets["number"].sum(), 6) == 13.501406

    assert len(returned_usable_assets["final_damage"].unique()) == 2
    assert len(returned_unusable_assets["final_damage"].unique()) == 3

    assert round(returned_usable_assets["cum_loss_value"].sum(), 3) == 146288.926
    assert round(returned_unusable_assets["cum_loss_value"].sum(), 3) == 2496644.215
