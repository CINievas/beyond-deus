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
import numpy as np
import pandas as pd
from beyonddeus.post_processor import (
    PostProcessor,
    calculate_all_damage_combinations, load_logic_tree_weights, retrieve_weight,
    calculate_all_logic_tree_combination_weights, weighted_sample_unbiased_stdev_1D,
    retrieve_hazard_branch_realisation_from_filename, weighted_sample_unbiased_stdev_3D,
)


def test_calculate_all_damage_combinations():

    initial_damage_range = [0, 1, 2, 3, 4]
    final_damage_range = [0, 1, 2, 3, 4]

    returned = calculate_all_damage_combinations(initial_damage_range, final_damage_range)

    expected = pd.MultiIndex.from_arrays(
        [
            [0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4],
            [0, 1, 2, 3, 4, 1, 2, 3, 4, 2, 3, 4, 3, 4, 4]
        ],
        names=("initial_damage", "final_damage")
    )

    assert returned.shape[0] == expected.shape[0]

    for i in range(expected.shape[0]):
        assert isinstance(returned[i], tuple)

        for pos in [0, 1]:
            assert returned[i][pos] == expected[i][pos]


def test_load_logic_tree_weights():
    # TEST 1
    logic_tree_meta = {
        1: {
            "hazard_prefix": "EQ",
            "logic_tree_path": os.path.join(
                os.path.dirname(__file__), "data", "test_EQ_logic_tree.csv"
            )
        },
        2: {
            "hazard_prefix": "TSU",
            "logic_tree_path": os.path.join(
                os.path.dirname(__file__), "data", "test_TSU_logic_tree.csv"
            )
        },
    }

    returned = load_logic_tree_weights(logic_tree_meta)

    expected = {
        "EQ": {"earthq_1": 0.5, "earthq_2": 0.2, "earthq_3": 0.3},
        "TSU": {"tsun_1": 0.25, "tsun_2": 0.75}
    }

    for hazard in expected:
        assert hazard in returned

        for branch in expected[hazard]:
            assert branch in returned[hazard]

            assert round(returned[hazard][branch], 2) == round(expected[hazard][branch], 2)

    # TEST 2: case in which weights do not add up to 1
    logic_tree_meta = {
        1: {
            "hazard_prefix": "EQ",
            "logic_tree_path": os.path.join(
                os.path.dirname(__file__), "data", "test_EQ_logic_tree_bad_sum.csv"
            )
        }
    }

    with pytest.raises(OSError) as excinfo:
        returned = load_logic_tree_weights(logic_tree_meta)

    assert "OSError" in str(excinfo.type)


def test_calculate_all_logic_tree_combination_weights():

    logic_tree_meta = {
        1: {
            "hazard_prefix": "EQ",
            "logic_tree_path": os.path.join(
                os.path.dirname(__file__), "data", "test_EQ_logic_tree.csv"
            ),
            "weight_of_realisation": 0.005  # 200 realisations
        },
        2: {
            "hazard_prefix": "TSU",
            "logic_tree_path": os.path.join(
                os.path.dirname(__file__), "data", "test_TSU_logic_tree.csv"
            ),
            "weight_of_realisation": 0.2  # 5
        },
    }

    returned, _ = calculate_all_logic_tree_combination_weights(logic_tree_meta)

    expected = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__), "data", "expected_all_logic_tree_combination_weights.csv"
        )
    )

    assert returned.shape[0] == expected.shape[0]
    assert returned.shape[1] == expected.shape[1]

    col_str = ["EQ", "TSU"]
    col_float = ["weight_branches", "weight_realisations"]

    for row in expected.index:
        for col in col_str:
            assert returned.loc[row, col] == expected.loc[row, col]
        for col in col_float:
            assert round(returned.loc[row, col], 6) == round(expected.loc[row, col], 6)


def test_retrieve_hazard_branch_realisation_from_filename():

    # TEST 1
    returned = retrieve_hazard_branch_realisation_from_filename(
        "HAZ_B_b_CCC_r_SSS_HAZ_A_b_BBB_r_RRR_EXPOSUREFILENAME_output_type.extension"
    )
    expected = [
        {"prefix": "HAZ_B", "b": "CCC", "r": "SSS"},
        {"prefix": "HAZ_A", "b": "BBB", "r": "RRR"}
    ]

    assert len(returned) == len(expected)

    for i in range(len(expected)):
        for key in expected[i].keys():
            assert returned[i][key] == expected[i][key]

    # TEST 2
    returned = retrieve_hazard_branch_realisation_from_filename(
        "TSU_b_rlz_106_r_0_EQ_b_SKGW_r_0_something_by_final_damage.csv"
    )
    expected = [
        {"prefix": "TSU", "b": "rlz_106", "r": "0"},
        {"prefix": "EQ", "b": "SKGW", "r": "0"}
    ]

    assert len(returned) == len(expected)

    for i in range(len(expected)):
        for key in expected[i].keys():
            assert returned[i][key] == expected[i][key]

    # TEST 3
    returned = retrieve_hazard_branch_realisation_from_filename(
        "AAA_b_10_r_20_BBB_b_30_r_40_CCC_b_5.5_r_99.csv"
    )
    expected = [
        {"prefix": "AAA", "b": "10", "r": "20"},
        {"prefix": "BBB", "b": "30", "r": "40"},
        {"prefix": "CCC", "b": "5.5", "r": "99"}
    ]

    assert len(returned) == len(expected)

    for i in range(len(expected)):
        for key in expected[i].keys():
            assert returned[i][key] == expected[i][key]


def test_retrieve_weight():

    # TEST 1
    haz_branch_realisation_info = [
        {"prefix": "TSU", "b": "tsun_2"},
        {"prefix": "EQ", "b": "earthq_2"}
    ]

    all_logic_tree_combination_weights = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__), "data", "expected_all_logic_tree_combination_weights.csv"
        )
    )

    returned = retrieve_weight(haz_branch_realisation_info, all_logic_tree_combination_weights)

    assert returned.shape[0] == 1
    assert round(returned.loc[0, "weight_branches"], 6) == 0.15
    assert round(returned.loc[0, "weight_realisations"], 6) == 0.00015

    # TEST 2: error should be raised because "returned" would have zero rows
    # 'all_logic_tree_combination_weights' as above
    haz_branch_realisation_info = [
        {"prefix": "TSU", "b": "tsun_5"},  # this branch does not exist
        {"prefix": "EQ", "b": "earthq_2"}
    ]

    with pytest.raises(OSError) as excinfo:
        returned = retrieve_weight(
            haz_branch_realisation_info, all_logic_tree_combination_weights
        )

    assert "OSError" in str(excinfo.type)


def test_weighted_sample_unbiased_stdev_1D():

    data_1D = np.array([5.2, 3.12, 12.8, 3.1, 4.5, 23.5, 8.9, 9.1, 4.5, 2.2])
    weights = np.array([0.09, 0.08, 0.07, 0.06, 0.05, 0.11, 0.12, 0.13, 0.14, 0.15])
    weighted_mean = 7.8206

    returned = weighted_sample_unbiased_stdev_1D(data_1D, weights, weighted_mean)

    assert round(returned, 6) == 6.681528


def test_weighted_sample_unbiased_stdev_3D():
    # The test data is the same as for 'test_weighted_sample_unbiased_stdev_1D', just repeated
    # in a larger array. "data_3D" has shape (3, 2, 10)
    data_1D = np.array([5.2, 3.12, 12.8, 3.1, 4.5, 23.5, 8.9, 9.1, 4.5, 2.2])
    data_2D = np.stack((data_1D, data_1D), axis=0)
    data_3D = np.stack((data_2D, data_2D, data_2D), axis=0)

    weights = np.array([0.09, 0.08, 0.07, 0.06, 0.05, 0.11, 0.12, 0.13, 0.14, 0.15])

    weighted_means = 7.8206 * np.ones((3, 2))

    returned = weighted_sample_unbiased_stdev_3D(data_3D, weights, weighted_means)

    expected = 6.681528 * np.ones_like(weighted_means)

    assert returned.shape == expected.shape

    for i in range(expected.shape[0]):
        for j in range(expected.shape[1]):
            assert round(returned[i, j], 6) == round(expected[i, j], 6)


def test_PostProcessor_export():

    post_processing = {
        "target_quantiles": [0.5, 0.95],
        "export_weight_per_file": True,
        "export_filenames_in_all_values_outputs": False,
        "logic_tree_meta":  {
            1: {
                "hazard_prefix": "EQ",
                "logic_tree_path": os.path.join(
                    os.path.dirname(__file__), "data", "test_EQ_logic_tree.csv"
                ),
                "weight_of_realisation": 0.5
            },
            2: {
                "hazard_prefix": "TSU",
                "logic_tree_path": os.path.join(
                    os.path.dirname(__file__), "data", "test_TSU_logic_tree.csv"
                ),
                "weight_of_realisation": 1
            },
        },
        "initial_damage_range": [0, 1, 2, 3, 4],
        "final_damage_range": [0, 1, 2, 3, 4],
        "per_branch_which_hazards": ["EQ", "TSU"],
        "types": {
            "by_final_damage_all": False,
            "by_final_damage_per_branch": False,
            "by_initial_and_final_damage_all": True,
            "by_initial_and_final_damage_per_branch": True,
            "loss_by_building_id_all": False,
            "damage_by_building_id_all": False,
            "damage_with_people_by_building_id_all": False,
            "loss_by_building_id_per_branch": False,
            "damage_by_building_id_per_branch": False,
            "damage_with_people_by_building_id_per_branch": False
        }
    }

    output_path = os.path.join(
        os.path.dirname(__file__), "data", "output_for_stats"
    )

    # Create temporary output directory (as the main software would do)
    stats_output_path = os.path.join(output_path, "statistics")
    os.mkdir(stats_output_path)

    exposure_geoms = None  # Not testing this functionality yet

    postprocessor = PostProcessor(post_processing, output_path, "some_path")
    returned_summaries = postprocessor.export(exposure_geoms)

    # Build names of expected output files
    eq_branches = ["earthq_1", "earthq_2", "earthq_3"]
    tsu_branches = ["tsun_1", "tsun_2"]
    stats = ["means", "stdev", "q_0_50", "q_0_95"]

    expected_filenames = [
        "by_initial_and_final_damage_total_meta_summary.csv",
        "by_initial_and_final_damage_by_branch_meta_summary.csv",
        "by_initial_and_final_damage_total_stats_weights.csv",
        "by_initial_and_final_damage_total_means.csv",
        "by_initial_and_final_damage_total_stdev.csv",
        "by_initial_and_final_damage_total_q_0_50.csv",
        "by_initial_and_final_damage_total_q_0_95.csv",
        "by_initial_and_final_damage_total_all_values_cum_loss_value.csv",
        "by_initial_and_final_damage_total_all_values_incremental_loss.csv",
        "by_initial_and_final_damage_total_all_values_number.csv",
        "by_initial_and_final_damage_total_all_values_ppl_census.csv",
        "portfolio_total_losses_all_values.csv"
    ]

    for branch in tsu_branches:
        for stat in stats:
            expected_filenames.append(
                "by_initial_and_final_damage_by_branch_%s_TSU_b_%s.csv" % (stat, branch)
            )
        expected_filenames.append(
            "by_initial_and_final_damage_by_branch_stats_weights_TSU_b_%s.csv" % (branch)
        )

    for branch in eq_branches:
        for stat in stats:
            expected_filenames.append(
                "by_initial_and_final_damage_by_branch_%s_EQ_b_%s.csv" % (stat, branch)
            )
        expected_filenames.append(
            "by_initial_and_final_damage_by_branch_stats_weights_EQ_b_%s.csv" % (branch)
        )

    # Check all expected files have been created
    returned_filenames = os.listdir(stats_output_path)

    for filename in expected_filenames:
        assert filename in returned_filenames

    # Check summary of number of files:
    assert len(returned_summaries.keys()) == 2

    expected_summary = pd.DataFrame(
        {
            "hazard": ["EQ", "EQ", "EQ", "TSU", "TSU"], 
            "branch": [*eq_branches, *tsu_branches],
            "number_files": [4, 4, 4, 6, 6]

        }
    )

    key = "by_initial_and_final_damage_per_branch"
    assert returned_summaries[key].shape == expected_summary.shape

    for row in expected_summary.index:
        for col in expected_summary.columns:
            assert returned_summaries[key].loc[row, col] == expected_summary.loc[row, col]

    # Check stats for one per-branch case: number of buildings that transitioned
    # from DS1 to DS2, for the earthquake branch "earthq_2":
    expected_mean = 72.964025
    expected_stdev = 2.992626
    expected_q_0_50 = 71.929000
    expected_q_0_95 = 77.7205500

    mean_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_by_branch_means_EQ_b_earthq_2.csv"
        ),
        index_col = [0, 1]
    )
    assert round(mean_df.loc[(1, 2), "number"], 5) == round(expected_mean, 5)

    stdev_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_by_branch_stdev_EQ_b_earthq_2.csv"
        ),
        index_col = [0, 1]
    )
    assert round(stdev_df.loc[(1, 2), "number"], 5) == round(expected_stdev, 5)

    q_0_50_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_by_branch_q_0_50_EQ_b_earthq_2.csv"
        ),
        index_col = [0, 1]
    )
    assert round(q_0_50_df.loc[(1, 2), "number"], 5) == round(expected_q_0_50, 5)

    q_0_95_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_by_branch_q_0_95_EQ_b_earthq_2.csv"
        ),
        index_col = [0, 1]
    )
    assert round(q_0_95_df.loc[(1, 2), "number"], 5) == round(expected_q_0_95, 5)

    # Check stats for one total case: number of buildings that transitioned
    # from DS1 to DS2:
    expected_mean = 122.87894875
    expected_stdev = 29.13962854
    expected_q_0_50 = 139.9373
    expected_q_0_95 = 158.3046

    mean_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_total_means.csv"
        ),
        index_col = [0, 1]
    )
    assert round(mean_df.loc[(1, 2), "number"], 5) == round(expected_mean, 5)

    stdev_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_total_stdev.csv"
        ),
        index_col = [0, 1]
    )
    assert round(stdev_df.loc[(1, 2), "number"], 5) == round(expected_stdev, 5)

    q_0_50_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_total_q_0_50.csv"
        ),
        index_col = [0, 1]
    )
    assert round(q_0_50_df.loc[(1, 2), "number"], 4) == round(expected_q_0_50, 4)

    q_0_95_df = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_total_q_0_95.csv"
        ),
        index_col = [0, 1]
    )
    assert round(q_0_95_df.loc[(1, 2), "number"], 4) == round(expected_q_0_95, 4)

    # Check weights per file for total stats
    returned_weights = pd.read_csv(
        os.path.join(
            stats_output_path, "by_initial_and_final_damage_total_stats_weights.csv"
        ),
        index_col = 0
    )
    expected_weights = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__), "data",
            "expected_by_initial_and_final_damage_total_stats_weights.csv"
        ),
        index_col = 0
    )

    assert returned_weights.shape[0] == expected_weights.shape[0]
    assert returned_weights.shape[1] == expected_weights.shape[1]

    for filename in expected_weights.index:
        assert filename in returned_weights.index
        for col in ["weights_raw", "weights_final"]:
            assert (
                round(returned_weights.loc[filename, col], 5) ==
                round(expected_weights.loc[filename, col], 5)
            )

    # Check weights per file for per-branch stats of TSU branch tsun_1
    returned_weights = pd.read_csv(
        os.path.join(
            stats_output_path,
            "by_initial_and_final_damage_by_branch_stats_weights_TSU_b_tsun_1.csv"
        ),
        index_col = 0
    )
    expected_weights = pd.read_csv(
        os.path.join(
            os.path.dirname(__file__), "data",
            "expected_by_initial_and_final_damage_by_branch_stats_weights_TSU_b_tsun_1.csv"
        ),
        index_col = 0
    )

    assert returned_weights.shape[0] == expected_weights.shape[0]
    assert returned_weights.shape[1] == expected_weights.shape[1]

    for filename in expected_weights.index:
        assert filename in returned_weights.index
        for col in ["weights_raw", "weights_final"]:
            assert (
                round(returned_weights.loc[filename, col], 5) ==
                round(expected_weights.loc[filename, col], 5)
            )

    # Delete created output files
    for filename in expected_filenames:
        os.remove(os.path.join(stats_output_path, filename))

    # Delete temporary directory
    os.rmdir(stats_output_path)
