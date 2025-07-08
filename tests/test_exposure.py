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
import pytest
import collections
import numpy as np
import geopandas as gpd
from copy import deepcopy
from beyonddeus.schemamapping import SchemaMapper
from beyonddeus.fragility import Fragility, DamageState
from beyonddeus.shakemap import Shakemaps
from beyonddeus.loss import LossProvider
from beyonddeus.exposure import (
    ExpoValues, empty_expo_values, read_exposure, map_exposure, expo_from_series_to_dict,
    get_sorted_damage_states, get_updated_exposure_and_transitions, TransitionValues,
    compute_loss, update_exposure_transitions_and_losses
)


def test_read_exposure():

    initial_exposure = read_exposure(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.json")
    )

    assert initial_exposure.shape[0] == 2  # rows

    quadkeys = ["1230", "1231"]  # implicitly checking "gid" column read as strings
    initial_exposure_quadkeys = initial_exposure["gid"].to_numpy()

    expo_keys = ["Taxonomy", "Damage", "Buildings"]

    for quadkey in quadkeys:
        assert quadkey in initial_exposure_quadkeys

        row = np.where(initial_exposure_quadkeys == quadkey)[0][0]

        expo_dict = eval(initial_exposure.loc[row, "expo"])

        assert isinstance(expo_dict, dict)

        for expo_key in expo_keys:
            assert expo_key in expo_dict.keys()


def test_map_exposure():
    """
    See as well test_schema_mapping() in test_schemamapping.py
    """

    schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
        os.path.join(os.path.dirname(__file__), "data", "conversion_taxonomy"),
        os.path.join(os.path.dirname(__file__), "data", "conversion_damage")
    )

    # Test trivial case in which source_schema == target_schema,
    # so the output is the same as the input 'expo'
    expo = "trivial"
    result_expo_returned = map_exposure(expo, "my_schema", "my_schema", schema_mapper)
    assert result_expo_returned == expo

    # Test case in which conversion is actually done
    old_exposure = expo_from_series_to_dict(
        {
            "Taxonomy": ["source_1", "source_3"],
            "Damage": ["D0", "D0"],
            "Buildings": [2.5, 5.0]
        }
    )
    result_expo_returned = map_exposure(
        old_exposure, "source_schema_name", "target_schema_name", schema_mapper
    )

    ExpoKey = collections.namedtuple("ExpoKey", ["taxonomy", "damage_state"])

    result_expo_expected = collections.defaultdict(empty_expo_values)
    result_expo_expected[ExpoKey("target_1", 0)] = ExpoValues(0.0875, 0, 0)
    result_expo_expected[ExpoKey("target_1", 1)] = ExpoValues(1.3125, 0, 0)
    result_expo_expected[ExpoKey("target_1", 2)] = ExpoValues(0.35, 0, 0)
    # "target_2" gets contributions from both "source_1" and "source_3"
    result_expo_expected[ExpoKey("target_2", 0)] = ExpoValues(0.2875, 0, 0)  # 0.0375 + 0.25
    result_expo_expected[ExpoKey("target_2", 1)] = ExpoValues(4.3125, 0, 0)  # 0.5625 + 3.75
    result_expo_expected[ExpoKey("target_2", 2)] = ExpoValues(1.15, 0, 0)  # 0.15 + 1.0

    for expo_expected_key, expo_expected_value in result_expo_expected.items():
        assert (
            round(expo_expected_value.buildings, 4)
            == round(result_expo_returned[expo_expected_key].buildings, 4)
        )
        assert (
            round(expo_expected_value.population, 4)
            == round(result_expo_returned[expo_expected_key].population, 4)
        )
        assert (
            round(expo_expected_value.replcostbdg, 4)
            == round(result_expo_returned[expo_expected_key].replcostbdg, 4)
        )


def test_get_sorted_damage_states():

    fragprov = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Initial damage state 0
    dmg_states_returned = get_sorted_damage_states(fragprov, "bdg_class_1", 0)

    dmg_states_expected = [
        DamageState("bdg_class_1", 0, 4, "PGA", "g", "not_needed_here"),
        DamageState("bdg_class_1", 0, 3, "PGA", "g", "not_needed_here"),
        DamageState("bdg_class_1", 0, 2, "PGA", "g", "not_needed_here"),
        DamageState("bdg_class_1", 0, 1, "PGA", "g", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 1
    dmg_states_returned = get_sorted_damage_states(fragprov, "bdg_class_1", 1)

    dmg_states_expected = [
        DamageState("bdg_class_1", 1, 4, "PGA", "g", "not_needed_here"),
        DamageState("bdg_class_1", 1, 3, "PGA", "g", "not_needed_here"),
        DamageState("bdg_class_1", 1, 2, "PGA", "g", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 2
    dmg_states_returned = get_sorted_damage_states(fragprov, "bdg_class_1", 2)

    dmg_states_expected = [
        DamageState("bdg_class_1", 2, 4, "PGA", "g", "not_needed_here"),
        DamageState("bdg_class_1", 2, 3, "PGA", "g", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 3
    dmg_states_returned = get_sorted_damage_states(fragprov, "bdg_class_1", 3)

    dmg_states_expected = [
        DamageState("bdg_class_1", 3, 4, "PGA", "g", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 4
    dmg_states_returned = get_sorted_damage_states(fragprov, "bdg_class_1", 4)

    assert len(dmg_states_returned) == 0


def test_get_updated_exposure_and_transitions():

    # Read test exposure file
    initial_exposure = read_exposure(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.json")
    )

    # Focus on the first exposure polygon of the file
    # and transform to a collections.defaultdict
    old_exposure = expo_from_series_to_dict(eval(initial_exposure.loc[0, "expo"]))

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    returned_result_expo, returned_result_transitions = (
        get_updated_exposure_and_transitions(
            initial_exposure.loc[0, "geometry"],
            old_exposure,
            intensity_provider,
            fragility_provider
        )
    )

    ExpoKey = collections.namedtuple("ExpoKey", ["taxonomy", "damage_state"])

    expected_result_expo = collections.defaultdict(empty_expo_values)
    expected_result_expo[ExpoKey("bdg_class_1", 1)] = ExpoValues(3.5236E-5, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_1", 2)] = ExpoValues(8.9000E-7, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_1", 3)] = ExpoValues(1.2502E-7, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_1", 4)] = ExpoValues(5.6467E-8, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_2", 1)] = ExpoValues(1.22604768, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_2", 2)] = ExpoValues(2.94083859, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_2", 3)] = ExpoValues(0.73493773, 0, 0)
    expected_result_expo[ExpoKey("bdg_class_2", 4)] = ExpoValues(0.04795817, 0, 0)

    for expo_expected_key, expo_expected_value in expected_result_expo.items():
        assert (
            round(expo_expected_value.buildings, 6)
            == round(returned_result_expo[expo_expected_key].buildings, 6)
        )
        assert (
            round(expo_expected_value.population, 6)
            == round(returned_result_expo[expo_expected_key].population, 6)
        )
        assert (
            round(expo_expected_value.replcostbdg, 6)
            == round(returned_result_expo[expo_expected_key].replcostbdg, 6)
        )

    TransitionKey = collections.namedtuple(
        "TransitionKey",
        ["taxonomy", "from_damage_state", "to_damage_state"],
    )

    expected_result_transit = collections.defaultdict(empty_expo_values)
    expected_result_transit[TransitionKey("bdg_class_1", 0, 1)] = TransitionValues(3.5236E-5, 0)
    expected_result_transit[TransitionKey("bdg_class_1", 0, 2)] = TransitionValues(8.9000E-7, 0)
    expected_result_transit[TransitionKey("bdg_class_1", 0, 3)] = TransitionValues(1.2502E-7, 0)
    expected_result_transit[TransitionKey("bdg_class_1", 0, 4)] = TransitionValues(5.6467E-8, 0)
    expected_result_transit[TransitionKey("bdg_class_2", 0, 1)] = TransitionValues(1.22604768, 0)
    expected_result_transit[TransitionKey("bdg_class_2", 0, 2)] = TransitionValues(2.94083859, 0)
    expected_result_transit[TransitionKey("bdg_class_2", 0, 3)] = TransitionValues(0.73493773, 0)
    expected_result_transit[TransitionKey("bdg_class_2", 0, 4)] = TransitionValues(0.04795817, 0)


    for transit_expected_key, transit_expected_value in expected_result_transit.items():

        assert (
            round(transit_expected_value.buildings, 6)
            == round(returned_result_transitions[transit_expected_key].buildings, 6)
        )
        assert (
            round(transit_expected_value.replcostbdg, 6)
            == round(returned_result_transitions[transit_expected_key].replcostbdg, 6)
        )


def test_compute_loss():

    # Read test exposure file
    initial_exposure = read_exposure(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.json")
    )

    # Focus on the first exposure polygon of the file
    # and transform to a collections.defaultdict
    old_exposure = expo_from_series_to_dict(eval(initial_exposure.loc[0, "expo"]))

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_costs_test.json")
    )

    # Calculate damage transitions
    _, result_transitions = (
        get_updated_exposure_and_transitions(
            initial_exposure.loc[0, "geometry"],
            old_exposure,
            intensity_provider,
            fragility_provider
        )
    )

    # Calculate economic losses
    returned_loss_value = compute_loss(
        transitions=result_transitions,
        loss_provider=loss_provider,
        schema=fragility_provider.schema,
    )

    assert round(returned_loss_value, 6) == 396541.620518


def test_update_exposure_transitions_and_losses():

    # TEST 1
    # Test case in which no conversion of building classes or damage states is needed
    # In this test, the exposure model does not include previous values of losses
    # (no existing "cum_loss_value" column)

    # Read test exposure file
    initial_exposure = read_exposure(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.json")
    )

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read schema mapper (will not be used)
    schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
        os.path.join(os.path.dirname(__file__), "data", "conversion_taxonomy"),
        os.path.join(os.path.dirname(__file__), "data", "conversion_damage")
    )

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_costs_test.json")
    )

    returned_updated_exposure = update_exposure_transitions_and_losses(
        "target_schema_name",
        "target_schema_name",
        initial_exposure,
        schema_mapper,
        intensity_provider,
        fragility_provider,
        loss_provider,
    )

    expected_updated_exposure = deepcopy(initial_exposure)

    # First exposure polygon (1230)
    new_expo_1230 = {
        "Taxonomy": [
            "bdg_class_1", "bdg_class_1", "bdg_class_1", "bdg_class_1", "bdg_class_1",
            "bdg_class_2", "bdg_class_2", "bdg_class_2", "bdg_class_2", "bdg_class_2",
        ],
        "Damage": ["D4", "D3", "D2", "D1", "D0", "D4", "D3", "D2", "D1", "D0"],
        "Buildings": [
            5.6467E-8, 1.2502E-7, 8.9000E-7, 3.5236E-5, 2.49996369,
            0.04795817, 0.73493773, 2.94083859, 1.22604768, 0.05021783
        ],
        "Population": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "ReplCostPerBdg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    }

    transitions_1230 = {
        "taxonomy": [
            "bdg_class_1", "bdg_class_1", "bdg_class_1", "bdg_class_1",
            "bdg_class_2", "bdg_class_2", "bdg_class_2", "bdg_class_2",
        ],
        "from_damage_state": [0, 0, 0, 0, 0, 0, 0, 0],
        "to_damage_state": [4, 3, 2, 1, 4, 3, 2, 1],
        "n_buildings": [
            5.6467E-8, 1.2502E-7, 8.9000E-7, 3.5236E-5,
            0.04795817, 0.73493773, 2.94083859, 1.22604768
        ],
        "replacement_costs_usd_bdg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    }

    # Second exposure polygon (1231)
    new_expo_1231 = {
        "Taxonomy": [
            "bdg_class_1", "bdg_class_1", "bdg_class_1", "bdg_class_1", "bdg_class_1",
            "bdg_class_2", "bdg_class_2", "bdg_class_2", "bdg_class_2", "bdg_class_2",
        ],
        "Damage": ["D4", "D3", "D2", "D1", "D0", "D4", "D3", "D2", "D1", "D0"],
        "Buildings": [
            2.8014E-6, 5.0933E-6, 2.99149E-5, 0.00077346, 3.99918874,
            1.60989335, 4.73186377, 3.43587520, 0.22118432, 0.00118336
        ],
        "Population": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "ReplCostPerBdg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    }

    transitions_1231 = {
        "taxonomy": [
            "bdg_class_1", "bdg_class_1", "bdg_class_1", "bdg_class_1",
            "bdg_class_2", "bdg_class_2", "bdg_class_2", "bdg_class_2",
        ],
        "from_damage_state": [0, 0, 0, 0, 0, 0, 0, 0],
        "to_damage_state": [4, 3, 2, 1, 4, 3, 2, 1],
        "n_buildings": [
            2.8014E-6, 5.0933E-6, 2.99149E-5, 0.00077346,
            1.60989335, 4.73186377, 3.43587520, 0.22118432
        ],
        "replacement_costs_usd_bdg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    }

    # Update (i.e., replace existing) "expo" column
    expected_updated_exposure["expo"] = [new_expo_1230, new_expo_1231]
    # New columns
    expected_updated_exposure["schema"] = ["target_schema_name", "target_schema_name"]
    expected_updated_exposure["transitions"] = [transitions_1230, transitions_1231]
    expected_updated_exposure["loss_value"] = [396541.620518, 1990229.860346]
    expected_updated_exposure["cum_loss_value"] = [396541.620518, 1990229.860346]

    assert returned_updated_exposure.shape[0] == expected_updated_exposure.shape[0]
    assert returned_updated_exposure.shape[1] == expected_updated_exposure.shape[1]

    simple_cols = ["gid", "geometry", "schema"]
    float_cols = ["loss_value", "cum_loss_value"]

    for row in expected_updated_exposure.index:
        for col in simple_cols:
            assert (
                returned_updated_exposure.loc[row, col] ==
                expected_updated_exposure.loc[row, col]
            )

        for col in float_cols:
            assert (
                round(returned_updated_exposure.loc[row, col], 6) ==
                round(expected_updated_exposure.loc[row, col], 6)
            )

        # col = expo
        returned_expo = returned_updated_exposure.loc[row, "expo"]
        expected_expo = expected_updated_exposure.loc[row, "expo"]

        expected_keys_str = ["Taxonomy", "Damage"]
        expected_keys_float = ["Buildings", "Population", "ReplCostPerBdg"]

        for key in expected_keys_str:
            assert len(returned_expo[key]) == len(expected_expo[key])

            for i, expected_element in enumerate(expected_expo[key]):
                assert returned_expo[key][i] == expected_element

        for key in expected_keys_float:
            assert len(returned_expo[key]) == len(expected_expo[key])

            for i, expected_val in enumerate(expected_expo[key]):
                assert round(returned_expo[key][i], 6) == round(expected_val, 6)

        # col = transitions
        returned_transitions = returned_updated_exposure.loc[row, "transitions"]
        expected_transitions = expected_updated_exposure.loc[row, "transitions"]

        expected_keys_str = ["taxonomy"]
        expected_keys_float = ["n_buildings", "replacement_costs_usd_bdg"]
        expected_keys_int = ["from_damage_state", "to_damage_state"]

        for key in expected_keys_str:
            assert len(returned_transitions[key]) == len(expected_transitions[key])

            for i, expected_element in enumerate(expected_transitions[key]):
                assert returned_transitions[key][i] == expected_element

        for key in expected_keys_float:
            assert len(returned_transitions[key]) == len(expected_transitions[key])

            for i, expected_val in enumerate(expected_transitions[key]):
                assert round(returned_transitions[key][i], 6) == round(expected_val, 6)

        for key in expected_keys_int:
            assert len(returned_transitions[key]) == len(expected_transitions[key])

            for i, expected_val in enumerate(expected_transitions[key]):
                assert returned_transitions[key][i] == expected_val

    # TEST 2
    # Test case in which no conversion of building classes or damage states is needed
    # In this test, the exposure model includes previous values of losses (i.e.,
    # "cum_loss_value" column). It also includes a "loss_value" that should be ignored.

    # Read test exposure file
    initial_exposure = read_exposure(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test_with_previous_loss.json")
    )

    assert "loss_value" in initial_exposure.columns
    assert "cum_loss_value" in initial_exposure.columns

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read schema mapper (will not be used)
    schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
        os.path.join(os.path.dirname(__file__), "data", "conversion_taxonomy"),
        os.path.join(os.path.dirname(__file__), "data", "conversion_damage")
    )

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_costs_test.json")
    )

    returned_updated_exposure = update_exposure_transitions_and_losses(
        "target_schema_name",
        "target_schema_name",
        initial_exposure,
        schema_mapper,
        intensity_provider,
        fragility_provider,
        loss_provider,
    )

    expected_loss_value = [396541.620518, 1990229.860346]
    expected_cum_loss_value = [396541.620518+150000.0, 1990229.860346+120000.0]

    for row in returned_updated_exposure.index:
        assert (
            round(returned_updated_exposure.loc[row, "loss_value"], 6) ==
            round(expected_loss_value[row], 6)
        )
        assert (
            round(returned_updated_exposure.loc[row, "cum_loss_value"], 6) ==
            round(expected_cum_loss_value[row], 6)
        )

    # All other results are the same as for Test 1
