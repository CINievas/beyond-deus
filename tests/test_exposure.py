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
import pandas as pd
import geopandas as gpd
from copy import deepcopy
from beyonddeus.schemamapping import SchemaMapper
from beyonddeus.fragility import Fragility, DamageState
from beyonddeus.shakemap import Shakemaps
from beyonddeus.loss import LossProvider
from beyonddeus.exposure import (
    read_exposure_csv, read_exposure_geoms, check_all_building_ids_in_geoms, map_exposure,
    get_sorted_damage_states, get_updated_exposure_and_transitions, compute_loss,
    update_exposure_transitions_and_losses, retrieve_exposure_input_names,
    read_exposure_intensity_combinations, check_exposure_intensity_combinations
)


def test_read_exposure_csv():

    # TEST 1, BASIC:
    initial_exposure = read_exposure_csv(
        os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
    )

    assert initial_exposure.shape[0] == 4  # rows

    expected_exposure_part = pd.DataFrame(
        {
            "building_id": ["1230", "1230", "1231", "1231"],
            "taxonomy": ["source_1", "source_2", "source_1", "source_2"]
        }
    )

    for row in expected_exposure_part.index:
        assert (
            initial_exposure.loc[row, "building_id"] ==
            expected_exposure_part.loc[row, "building_id"]
        )
        assert (
            initial_exposure.loc[row, "taxonomy"] ==
            expected_exposure_part.loc[row, "taxonomy"]
        )

    assert round(initial_exposure["number"].sum(), 5) == 21.5
    assert round(initial_exposure["replacement_cost_tot"].sum(), 5) == 12.5E6
    assert round(initial_exposure["ppl_census"].sum(), 5) == 123.0
    assert round(initial_exposure["cum_loss_value"].sum(), 5) == 0.0

    # TEST 2, make sure repeated combinations of ["building_id", "taxonomy", "initial_damage"]
    # are grouped together
    initial_exposure = read_exposure_csv(
        os.path.join(os.path.dirname(__file__), "data", "exposure_test_repeated_combis.csv")
    )

    assert initial_exposure.shape[0] == 4  # rows

    for row in expected_exposure_part.index:
        assert (
            initial_exposure.loc[row, "building_id"] ==
            expected_exposure_part.loc[row, "building_id"]
        )
        assert (
            initial_exposure.loc[row, "taxonomy"] ==
            expected_exposure_part.loc[row, "taxonomy"]
        )

    assert round(initial_exposure["number"].sum(), 5) == 21.5
    assert round(initial_exposure["replacement_cost_tot"].sum(), 5) == 12.5E6
    assert round(initial_exposure["ppl_census"].sum(), 5) == 123.0
    assert round(initial_exposure["cum_loss_value"].sum(), 5) == 0.0

    # TEST 3, same as TEST 1, but reading from a compressed ZSTD instead of CSV
    initial_exposure = read_exposure_csv(
        os.path.join(
            os.path.dirname(__file__), "data", "exposure_csvs", "exposure_test_01.zstd"
        )
    )

    assert initial_exposure.shape[0] == 4  # rows

    expected_exposure_part = pd.DataFrame(
        {
            "building_id": ["1230", "1230", "1231", "1231"],
            "taxonomy": ["source_1", "source_2", "source_1", "source_2"]
        }
    )

    for row in expected_exposure_part.index:
        assert (
            initial_exposure.loc[row, "building_id"] ==
            expected_exposure_part.loc[row, "building_id"]
        )
        assert (
            initial_exposure.loc[row, "taxonomy"] ==
            expected_exposure_part.loc[row, "taxonomy"]
        )

    assert round(initial_exposure["number"].sum(), 5) == 21.5
    assert round(initial_exposure["replacement_cost_tot"].sum(), 5) == 12.5E6
    assert round(initial_exposure["ppl_census"].sum(), 5) == 123.0
    assert round(initial_exposure["cum_loss_value"].sum(), 5) == 0.0


def test_read_exposure_geoms():

    exposure_geometries = read_exposure_geoms(
        os.path.join(os.path.dirname(__file__), "data", "exposure_polygons_test.gpkg")
    )

    assert exposure_geometries.shape[0] == 2
    assert type(exposure_geometries.loc[0, "building_id"]) is str


def test_retrieve_exposure_input_names():

    returned_input_names = retrieve_exposure_input_names(
         os.path.join(os.path.dirname(__file__), "data", "exposure_csvs")
    )

    expected_input_names = ["exposure_test_01.zstd", "exposure_test_02.zstd"]

    assert len(returned_input_names) == len(expected_input_names)

    for filename in expected_input_names:
        assert filename in returned_input_names


def test_check_all_building_ids_in_geoms():

    # Test case in which GPKG does not contain polygons for all building_id of CSV
    initial_exposure = read_exposure_csv(
        os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
    )
    exposure_geometries = read_exposure_geoms(
        os.path.join(os.path.dirname(__file__), "data", "exposure_polygons_test_wrong.gpkg")
    )

    # Test case in which GPKG does not contain polygons for all building_id of CSV
    with pytest.raises(OSError) as excinfo:
        check_all_building_ids_in_geoms(initial_exposure, exposure_geometries)

    assert "OSError" in str(excinfo.type)


def test_read_exposure_intensity_combinations():
    # TEST 1: open a real file, everything as it should
    returned_combinations = read_exposure_intensity_combinations(
        os.path.join(
            os.path.dirname(__file__), "data", "test_exposure_intensity_combinations.csv"
        )
    )

    assert returned_combinations.shape[0] == 4
    assert returned_combinations.shape[1] == 3


def test_check_exposure_intensity_combinations():
    returned_combinations = read_exposure_intensity_combinations(
        os.path.join(
            os.path.dirname(__file__), "data", "test_exposure_intensity_combinations.csv"
        )
    )

    # TEST 1: all good
    exposure_input_names = ["exposure_test_01.zstd", "exposure_test_02.zstd"]
    intensity_provider = {
        "subdir_1": {
            "TSU_inundation_fields_test_01": None, "TSU_inundation_fields_test_02": None
        },
        "subdir_2": {
            "TSU_inundation_fields_test_01": None, "TSU_inundation_fields_test_02": None
        }
    }

    check_exposure_intensity_combinations(
        returned_combinations, exposure_input_names, intensity_provider
    )

    # TEST 2: exposure input names error
    exposure_input_names = ["exposure_test_03.zstd", "exposure_test_02.zstd"]

    with pytest.raises(OSError) as excinfo:
        check_exposure_intensity_combinations(
            returned_combinations, exposure_input_names, intensity_provider
        )

    assert "OSError" in str(excinfo.type)

    # TEST 3: intensity_provider error
    exposure_input_names = ["exposure_test_01.zstd", "exposure_test_02.zstd"]
    intensity_provider = {
        "subdir_1": {
            "TSU_inundation_fields_test_04": None, "TSU_inundation_fields_test_02": None
        },
        "subdir_2": {
            "TSU_inundation_fields_test_01": None, "TSU_inundation_fields_test_02": None
        }
    }

    with pytest.raises(OSError) as excinfo:
        check_exposure_intensity_combinations(
            returned_combinations, exposure_input_names, intensity_provider
        )

    assert "OSError" in str(excinfo.type)


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
    old_exposure = read_exposure_csv(
        os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
    )
    expected_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "expected_mapped_exposure.csv")
    )
    expected_exposure.sort_values(
        by=["building_id", "taxonomy", "initial_damage"], inplace=True
    )
    expected_exposure.reset_index(inplace=True)

    returned_exposure = map_exposure(
        old_exposure, "source_schema_name", "target_schema_name", schema_mapper
    )

    string_cols = ["building_id", "taxonomy"]
    numeric_cols = [
        "number", "initial_damage", "replacement_cost_tot", "ppl_census", "cum_loss_value"
    ]

    for row in expected_exposure.index:
        for col in string_cols:
            assert returned_exposure.loc[row, col] == expected_exposure.loc[row, col]
        for col in numeric_cols:
            assert (
                round(returned_exposure.loc[row, col], 5) ==
                round(expected_exposure.loc[row, col], 5)
            )


def test_get_sorted_damage_states():

    fragprov = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Initial damage state 0
    dmg_states_returned = get_sorted_damage_states(fragprov, "source_1", 0)

    dmg_states_expected = [
        DamageState("source_1", 0, 4, "PGA", "not_needed_here"),
        DamageState("source_1", 0, 3, "PGA", "not_needed_here"),
        DamageState("source_1", 0, 2, "PGA", "not_needed_here"),
        DamageState("source_1", 0, 1, "PGA", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 1
    dmg_states_returned = get_sorted_damage_states(fragprov, "source_1", 1)

    dmg_states_expected = [
        DamageState("source_1", 1, 4, "PGA", "not_needed_here"),
        DamageState("source_1", 1, 3, "PGA", "not_needed_here"),
        DamageState("source_1", 1, 2, "PGA", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 2
    dmg_states_returned = get_sorted_damage_states(fragprov, "source_1", 2)

    dmg_states_expected = [
        DamageState("source_1", 2, 4, "PGA", "not_needed_here"),
        DamageState("source_1", 2, 3, "PGA", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 3
    dmg_states_returned = get_sorted_damage_states(fragprov, "source_1", 3)

    dmg_states_expected = [
        DamageState("source_1", 3, 4, "PGA", "not_needed_here"),
    ]

    for i, dmg_state in enumerate(dmg_states_expected):
        assert dmg_states_returned[i].from_state == dmg_state.from_state
        assert dmg_states_returned[i].to_state == dmg_state.to_state

    # Initial damage state 4
    dmg_states_returned = get_sorted_damage_states(fragprov, "source_1", 4)

    assert len(dmg_states_returned) == 0


def test_get_updated_exposure_and_transitions():

    # TEST 1

    # Read test exposure file
    initial_exposure = read_exposure_csv(
        os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
    )

    # Focus on the first exposure polygon of the file
    old_exposure = initial_exposure[initial_exposure.building_id == "1230"].copy()
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8]},
        index=["1230"]
    )
    intensity_positions.index.name = "building_id"

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    intensity_threshold = 0.001
    all_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    returned_updated_exposure = get_updated_exposure_and_transitions(
        old_exposure,
        all_intensities.loc["1230", :],
        intensity_threshold,
        fragility_provider
    )

    # Read expected results
    expected_updated_exposure = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_no_previous_loss.csv"
       )
    )
    # 'read_exposure_csv' will rename "final_damage" as "initial_damage", and would eliminate
    # the "incremental_loss" column, so need to address this:
    expected_updated_exposure.rename(
        columns={
            "initial_damage": "final_damage", "transition_trick": "transition"
        }, inplace=True
    )
    expected_updated_exposure["initial_damage"] = np.zeros(
        expected_updated_exposure.shape[0], dtype=int
    )

    expected_updated_exposure = expected_updated_exposure[
        expected_updated_exposure.building_id == "1230"
    ].copy()
    expected_updated_exposure = expected_updated_exposure.drop(columns=["incremental_loss_trick"])

    for col in expected_updated_exposure.columns:
        assert col in returned_updated_exposure

    cols_str_or_int = ["building_id", "taxonomy", "initial_damage", "final_damage"]
    cols_floats = ["number", "replacement_cost_tot", "ppl_census"]

    for row in expected_updated_exposure.index:
        for col in cols_str_or_int:
            assert (
                returned_updated_exposure.loc[row, col] ==
                expected_updated_exposure.loc[row, col]
            )
        for col in cols_floats:
            if col == "number":
                assert (
                    round(returned_updated_exposure.loc[row, col], 10) ==
                    round(expected_updated_exposure.loc[row, col], 10)
                )
            else:
                assert (
                    round(returned_updated_exposure.loc[row, col], 5) ==
                    round(expected_updated_exposure.loc[row, col], 5)
                )

    # TEST 2: CASE IN WHICH THE NUMBER OF INPUT BUILDINGS ~0
    # (It uses some data already loaded for TEST 1)

    old_exposure["number"] = np.zeros(old_exposure.shape[0])

    returned_updated_exposure_trivial = get_updated_exposure_and_transitions(
        old_exposure,
        all_intensities.loc["1230", :],
        intensity_threshold,
        fragility_provider
    )

    assert returned_updated_exposure_trivial.shape[0] == old_exposure.shape[0]

    for row in old_exposure.index:
        assert (
            returned_updated_exposure_trivial.loc[row, "final_damage"]
            == old_exposure.loc[row, "initial_damage"]
        )

    # TEST 3: CASE IN WHICH THE OUTPUT HAS REPEATED ROWS THAT NEED TO BE GROUPED
    # (It uses data already loaded for TEST 1)
    # Create a new input expose from two rows of 'returned_updated_exposure'
    new_exposure_without_duplicates = returned_updated_exposure.loc[0:1, :].copy()
    del new_exposure_without_duplicates["initial_damage"]
    new_exposure_without_duplicates.rename(
        columns={"final_damage": "initial_damage"},
        inplace=True
    )

    # Now take 'new_exposure_without_duplicates' and concatenate it twice, dividing the number
    # of buildings, costs, people by 2, so that the total number remains the same (i.e., like
    # splitting each row of 'new_exposure_without_duplicates' into two, so as to create
    # duplicate combinations that the method needs to group together
    new_exposure_with_duplicates = pd.concat((
        new_exposure_without_duplicates, new_exposure_without_duplicates
    ))
    new_exposure_with_duplicates.reset_index(inplace=True)
    for col in ["number", "replacement_cost_tot", "ppl_census", "cum_loss_value"]:
        new_exposure_with_duplicates[col] = new_exposure_with_duplicates[col] / 2.0

    # Updated exposure for 'returned_without_duplicates'
    returned_without_duplicates = get_updated_exposure_and_transitions(
        new_exposure_without_duplicates,
        all_intensities.loc["1230", :],
        intensity_threshold,
        fragility_provider
    )
    returned_without_duplicates.sort_values(
        by=["building_id", "taxonomy", "initial_damage", "final_damage"], inplace=True
    )  # sort so that it is possible to compare
    returned_without_duplicates.reset_index(inplace=True)

    # Updated exposure for 'returned_with_duplicates'
    returned_with_duplicates = get_updated_exposure_and_transitions(
        new_exposure_with_duplicates,
        all_intensities.loc["1230", :],
        intensity_threshold,
        fragility_provider
    )
    returned_with_duplicates.sort_values(
        by=["building_id", "taxonomy", "initial_damage", "final_damage"], inplace=True
    )  # sort so that it is possible to compare
    returned_with_duplicates.reset_index(inplace=True)

    # After the sorting and re-setting of the indices, the two returned DFs need to be the same
    # (because the input exposure was esentially the same, just split into more or less rows)
    assert returned_without_duplicates.shape[0] == returned_with_duplicates.shape[0]
    assert returned_without_duplicates.shape[1] == returned_with_duplicates.shape[1]

    for col in expected_updated_exposure.columns:
        assert col in returned_without_duplicates
        assert col in returned_with_duplicates

    cols_str_or_int = ["building_id", "taxonomy", "initial_damage", "final_damage"]
    cols_floats = ["number", "replacement_cost_tot", "ppl_census"]

    for row in returned_without_duplicates.index:
        for col in cols_str_or_int:
            assert (
                returned_with_duplicates.loc[row, col] ==
                returned_without_duplicates.loc[row, col]
            )
        for col in cols_floats:
            if col == "number":
                assert (
                    round(returned_with_duplicates.loc[row, col], 10) ==
                    round(returned_without_duplicates.loc[row, col], 10)
                )
            else:
                assert (
                    round(returned_with_duplicates.loc[row, col], 5) ==
                    round(returned_without_duplicates.loc[row, col], 5)
                )


def test_compute_loss():

    # TEST 1: NO PRE-EXISTING CUMULATIVE LOSSES

    # Read test exposure file
    initial_exposure = read_exposure_csv(
        os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
    )

    # Focus on the first exposure polygon of the file
    old_exposure = initial_exposure[initial_exposure.building_id == "1230"].copy()
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8]},
        index=["1230"]
    )
    intensity_positions.index.name = "building_id"

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    intensity_threshold = 0.001
    all_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_test.json")
    )

    updated_exposure = get_updated_exposure_and_transitions(
        old_exposure,
        all_intensities.loc["1230", :],
        intensity_threshold,
        fragility_provider
    )

    # Calculate economic losses
    returned_updated_exposure_and_losses = compute_loss(
        updated_exposure,
        loss_provider=loss_provider,
        schema=fragility_provider.schema,
    )

    # Read expected results
    expected_updated_exposure_and_losses = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_no_previous_loss.csv"
       )
    )
    # 'read_exposure_csv' would eliminate the incremental_loss" column, so need to address this:
    expected_updated_exposure_and_losses.rename(
        columns={
            "incremental_loss_trick": "incremental_loss", "transition_trick": "transition"
        }, inplace=True
    )

    expected_updated_exposure_and_losses = expected_updated_exposure_and_losses[
        expected_updated_exposure_and_losses.building_id == "1230"
    ].copy()

    cols = ["incremental_loss", "cum_loss_value"]

    for row in expected_updated_exposure_and_losses.index:
        for col in cols:
            assert (
                round(returned_updated_exposure_and_losses.loc[row, col], 5) ==
                round(expected_updated_exposure_and_losses.loc[row, col], 5)
            )

    assert round(
        returned_updated_exposure_and_losses["incremental_loss"].sum(), 6
    ) == 396541.620518
    assert round(
        returned_updated_exposure_and_losses["cum_loss_value"].sum(), 6
    ) == 396541.620518

    # TEST 2: WITH PRE-EXISTING CUMULATIVE LOSSES,
    # INCLUDING ASSETS FOR WHICH ADJUSTMENT IS NEEDED TO AVOID CUMULATIVE LOSS>REPLACEMENT COST

    # Read test exposure file
    initial_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test_with_previous_loss.csv")
    )

    # Focus on the first exposure polygon of the file
    old_exposure = initial_exposure[initial_exposure.building_id == "1230"].copy()
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8]},
        index=["1230"]
    )
    intensity_positions.index.name = "building_id"

    # Read fragility input
    fragility_provider = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    # Read intensity provider
    intensity_provider = Shakemaps.from_file(
        os.path.join(os.path.dirname(__file__), "data", "intensity_test.xml"),
    ).to_intensity_provider()

    intensity_threshold = 0.001
    all_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_test.json")
    )

    updated_exposure = get_updated_exposure_and_transitions(
        old_exposure,
        all_intensities.loc["1230", :],
        intensity_threshold,
        fragility_provider
    )

    # Calculate economic losses
    returned_updated_exposure_and_losses = compute_loss(
        updated_exposure,
        loss_provider=loss_provider,
        schema=fragility_provider.schema,
    )

    # Read expected results
    expected_updated_exposure_and_losses = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_with_previous_loss.csv"
       )
    )
    # 'read_exposure_csv' would eliminate the incremental_loss" column, so need to address this:
    expected_updated_exposure_and_losses.rename(
        columns={"incremental_loss_trick": "incremental_loss"}, inplace=True
    )

    expected_updated_exposure_and_losses = expected_updated_exposure_and_losses[
        expected_updated_exposure_and_losses.building_id == "1230"
    ].copy()

    cols = ["incremental_loss", "cum_loss_value"]

    for row in expected_updated_exposure_and_losses.index:
        for col in cols:
            assert (
                round(returned_updated_exposure_and_losses.loc[row, col], 3) ==
                round(expected_updated_exposure_and_losses.loc[row, col], 3)
            )

    assert round(
        returned_updated_exposure_and_losses["incremental_loss"].sum(), 5
    ) == 395582.45595
    assert round(
        returned_updated_exposure_and_losses["cum_loss_value"].sum(), 3
    ) == 545582.456


def test_update_exposure_transitions_and_losses():

    # TEST 1
    # Test case in which no conversion of building classes or damage states is needed
    # In this test, the exposure model does not include previous values of losses
    # (no existing "cum_loss_value" column)

    # Read test exposure file
    initial_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
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

    # Intensity positions
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8, 11]},
        index=["1230", "1231"]
    )
    intensity_positions.index.rename("building_id", inplace=True)

    # Intensity values
    intensity_threshold = 0.001
    all_hazard_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_test.json")
    )

    returned_updated_exposure_and_losses = update_exposure_transitions_and_losses(
        initial_exposure,
        all_hazard_intensities,
        intensity_threshold,
        fragility_provider,
        loss_provider,
    )

    # Read expected results
    expected_updated_exposure_and_losses = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_no_previous_loss.csv"
       )
    )
    # 'read_exposure_csv' will rename "final_damage" as "initial_damage", and would eliminate
    # the "incremental_loss" column, so need to address this:
    expected_updated_exposure_and_losses.rename(
        columns={
            "initial_damage": "final_damage",
            "incremental_loss_trick": "incremental_loss",
            "transition_trick": "transition"
        }, inplace=True
    )
    expected_updated_exposure_and_losses["initial_damage"] = np.zeros(
        expected_updated_exposure_and_losses.shape[0], dtype=int
    )

    for col in expected_updated_exposure_and_losses.columns:
        assert col in returned_updated_exposure_and_losses

    cols_str_or_int_or_bool = [
        "building_id", "taxonomy", "initial_damage", "final_damage", "transition"
    ]
    cols_floats = [
        "number", "replacement_cost_tot", "ppl_census", "incremental_loss", "cum_loss_value"
    ]

    for row in expected_updated_exposure_and_losses.index:
        for col in cols_str_or_int_or_bool:
            assert (
                returned_updated_exposure_and_losses.loc[row, col] ==
                expected_updated_exposure_and_losses.loc[row, col]
            )
        for col in cols_floats:
            if col == "number":
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 10) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 10)
                )
            else:
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 5) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 5)
                )

    # TEST 2
    # Test case in which no conversion of building classes or damage states is needed
    # In this test, the exposure model includes previous values of losses (i.e.,
    # "cum_loss_value" column). It also includes a "loss_value" that should be ignored.

    # Read test exposure file
    initial_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test_with_previous_loss.csv")
    )

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

    # Intensity positions
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8, 11]},
        index=["1230", "1231"]
    )
    intensity_positions.index.rename("building_id", inplace=True)

    # Intensity values
    intensity_threshold = 0.001
    all_hazard_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_test.json")
    )

    returned_updated_exposure_and_losses = update_exposure_transitions_and_losses(
        initial_exposure,
        all_hazard_intensities,
        intensity_threshold,
        fragility_provider,
        loss_provider,
    )

    # Read expected results
    expected_updated_exposure_and_losses = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_with_previous_loss.csv"
       )
    )
    # 'read_exposure_csv' will rename "final_damage" as "initial_damage", and would eliminate
    # the "incremental_loss" column, so need to address this:
    expected_updated_exposure_and_losses.rename(
        columns={
            "initial_damage": "final_damage",
            "incremental_loss_trick": "incremental_loss",
            "transition_trick": "transition"
        }, inplace=True
    )
    expected_updated_exposure_and_losses["initial_damage"] = np.zeros(
        expected_updated_exposure_and_losses.shape[0], dtype=int
    )

    for col in expected_updated_exposure_and_losses.columns:
        assert col in returned_updated_exposure_and_losses

    cols_str_or_int_or_bool = [
        "building_id", "taxonomy", "initial_damage", "final_damage", "transition"
    ]
    cols_floats = [
        "number", "replacement_cost_tot", "ppl_census", "incremental_loss", "cum_loss_value"
    ]

    for row in expected_updated_exposure_and_losses.index:
        for col in cols_str_or_int_or_bool:
            assert (
                returned_updated_exposure_and_losses.loc[row, col] ==
                expected_updated_exposure_and_losses.loc[row, col]
            )
        for col in cols_floats:
            if col == "number":
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 10) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 10)
                )
            else:
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 3) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 3)
                )

    # TEST 3: SAME AS TEST 2 BUT MODIFIED INTENSITIES & SETTING AN "intensity_threshold"
    #         SO THAT ONE OF THE building_ids IS NOT PROCESSED
    #         (i.e., ALL INTENSITIES BELOW THRESHOLD)
    # Test case in which no conversion of building classes or damage states is needed
    # In this test, the exposure model includes previous values of losses (i.e.,
    # "cum_loss_value" column). It also includes a "loss_value" that should be ignored.

    # Read test exposure file
    initial_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test_with_previous_loss.csv")
    )

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
        os.path.join(
            os.path.dirname(__file__), "data", "intensity_for_not_run_threshold_test.xml"
        ),
    ).to_intensity_provider()

    # Intensity positions
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8, 11]},
        index=["1230", "1231"]
    )
    intensity_positions.index.rename("building_id", inplace=True)

    # Intensity values
    intensity_threshold = 0.001
    all_hazard_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_test.json")
    )

    returned_updated_exposure_and_losses = update_exposure_transitions_and_losses(
        initial_exposure,
        all_hazard_intensities,
        intensity_threshold,
        fragility_provider,
        loss_provider,
    )

    # Read expected results
    expected_updated_exposure_and_losses = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_with_previous_loss_intensity_threshold.csv"
       )
    )
    # 'read_exposure_csv' will rename "final_damage" as "initial_damage", and would eliminate
    # the "incremental_loss" column, so need to address this:
    expected_updated_exposure_and_losses.rename(
        columns={
            "initial_damage": "final_damage",
            "incremental_loss_trick": "incremental_loss",
            "transition_trick": "transition"
        }, inplace=True
    )
    expected_updated_exposure_and_losses["initial_damage"] = np.zeros(
        expected_updated_exposure_and_losses.shape[0], dtype=int
    )

    for col in expected_updated_exposure_and_losses.columns:
        assert col in returned_updated_exposure_and_losses

    cols_str_or_int_or_bool = [
        "building_id", "taxonomy", "initial_damage", "final_damage", "transition"
    ]
    cols_floats = [
        "number", "replacement_cost_tot", "ppl_census", "incremental_loss", "cum_loss_value"
    ]

    for row in expected_updated_exposure_and_losses.index:
        for col in cols_str_or_int_or_bool:
            assert (
                returned_updated_exposure_and_losses.loc[row, col] ==
                expected_updated_exposure_and_losses.loc[row, col]
            )
        for col in cols_floats:
            if col == "number":
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 10) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 10)
                )
            else:
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 3) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 3)
                )

    # TEST 4: SAME AS TEST 2 BUT MODIFIED INTENSITIES & SETTING AN "intensity_threshold"
    #         SO THAT ONE OF THE building_ids IS INITIALLY PROCESSED BUT THEN DAMAGE NOT CALC'D
    #         (i.e. NOT ALL INTENSITIES < THRESHOLD, ONLY THE ONE THAT MATTERS)
    # Test case in which no conversion of building classes or damage states is needed
    # In this test, the exposure model includes previous values of losses (i.e.,
    # "cum_loss_value" column). It also includes a "loss_value" that should be ignored.

    # Read test exposure file
    initial_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test_with_previous_loss.csv")
    )

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
        os.path.join(
            os.path.dirname(__file__), "data", "intensity_for_partial_run_threshold_test.xml"
        ),
    ).to_intensity_provider()

    # Intensity positions
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8, 11]},
        index=["1230", "1231"]
    )
    intensity_positions.index.rename("building_id", inplace=True)

    # Intensity values
    intensity_threshold = 0.001
    all_hazard_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Read loss model provider
    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_test.json")
    )

    returned_updated_exposure_and_losses = update_exposure_transitions_and_losses(
        initial_exposure,
        all_hazard_intensities,
        intensity_threshold,
        fragility_provider,
        loss_provider,
    )

    # Read expected results
    expected_updated_exposure_and_losses = read_exposure_csv(
       os.path.join(
           os.path.dirname(__file__), "data",
           "expected_updated_exposure_damage_losses_with_previous_loss_intensity_threshold.csv"
       )
    )
    # 'read_exposure_csv' will rename "final_damage" as "initial_damage", and would eliminate
    # the "incremental_loss" column, so need to address this:
    expected_updated_exposure_and_losses.rename(
        columns={
            "initial_damage": "final_damage",
            "incremental_loss_trick": "incremental_loss",
            "transition_trick": "transition"
        }, inplace=True
    )
    expected_updated_exposure_and_losses["initial_damage"] = np.zeros(
        expected_updated_exposure_and_losses.shape[0], dtype=int
    )

    for col in expected_updated_exposure_and_losses.columns:
        assert col in returned_updated_exposure_and_losses

    cols_str_or_int_or_bool = [
        "building_id", "taxonomy", "initial_damage", "final_damage", "transition"
    ]
    cols_floats = [
        "number", "replacement_cost_tot", "ppl_census", "incremental_loss", "cum_loss_value"
    ]

    for row in expected_updated_exposure_and_losses.index:
        for col in cols_str_or_int_or_bool:
            assert (
                returned_updated_exposure_and_losses.loc[row, col] ==
                expected_updated_exposure_and_losses.loc[row, col]
            )
        for col in cols_floats:
            if col == "number":
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 10) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 10)
                )
            else:
                assert (
                    round(returned_updated_exposure_and_losses.loc[row, col], 3) ==
                    round(expected_updated_exposure_and_losses.loc[row, col], 3)
                )

    # TEST 5: The same as TEST 1, but with loss_provider = None, i.e. no economic losses
    # should be calculated

    # Read test exposure file
    initial_exposure = read_exposure_csv(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.csv")
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

    # Intensity positions
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": [8, 11]},
        index=["1230", "1231"]
    )
    intensity_positions.index.rename("building_id", inplace=True)

    # Intensity values
    intensity_threshold = 0.001
    all_hazard_intensities = intensity_provider.get_values_at_multiple_positions(
        intensity_positions, intensity_threshold
    )

    # Set loss_provider
    loss_provider = None

    returned_updated_exposure_and_losses = update_exposure_transitions_and_losses(
        initial_exposure,
        all_hazard_intensities,
        intensity_threshold,
        fragility_provider,
        loss_provider,
    )

    # Check that no economic loss columns have been created
    assert "cum_loss_value" not in returned_updated_exposure_and_losses.columns
    assert "incremental_loss" not in returned_updated_exposure_and_losses.columns
