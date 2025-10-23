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
import itertools
import logging
import math
import re
import numpy as np
import pandas as pd
from copy import deepcopy

logger = logging.getLogger()


class PostProcessor:
    def __init__(self, post_processing_config, general_output_path):
        """
        This class handles the generation of statistics (means, standard deviations, quantiles)
        of results, accounting for logic tree weights.

        Attrs:
            self.post_processing_config (dict):
                Post-processing configuration, i.e. the "post_processing" attribute of the
                "Configuration" class. Sub-parameters include:
                    "target_quantiles" (list of float):
                        List of quantiles in the range (0.0, 1.0) to be used for calculating
                        quantiles of results.
                    "logic_tree_meta" (dict):
                        Dictionary describing the logic trees of all hazards in the chain run so
                        far. The sub-keys are integers >= 1, indicating the order in which the
                        hazards were applied (1 = first hazard, 2 = second hazard, ...). For
                        each hazard, the subkey is a dictionary with the following parameters:
                            "hazard_prefix" (str):
                                'self.hazard_prefix' as used in the associated software run.
                            "logic_tree_path" (str):
                                Full path to CSV file containing the logic tree associated with
                                this hazard (the file contains all names and weights of the
                                logic tree branches).
                            "realisations" (int > 0):
                                Number of realisations per logic tree branch.
                    "initial_damage_range" (list of int):
                        List of integers designating the initial damage states (of the last
                        hazard run).
                    "final_damage_range" (list of int):
                        List of integers designating the final damage states (of the last hazard
                        run).
                    "types":
                        Dictionary indicating the kind of post-processing outputs to export, by
                        means of True/False. Options are sets of nested keys:
                            "by_initial_and_final_damage_all": Mean, quantiles and standard
                                deviation of number of buildings, incremental loss and
                                cumulative loss, per combination of initial-final damage states,
                                for all branches and realisations considered together, with
                                their weights.
                            "by_initial_and_final_damage_per_branch": Mean, quantiles and
                                standard deviation of number of buildings, incremental loss and
                                cumulative loss, per combination of initial-final damage states,
                                for each branch of each hazard run so far.
            self.general_output_path (str):
                Path to directory where outputs to be post-processed are stored, and where
                post-processing results will be stored (under the "statistics" sub-directory).
            self.all_initial_final_damage_combinations (Pandas MultiIndex):
                MultiIndex of all combinations of initial and final damage states that are
                physically possible, i.e. all cases in which initial damage <= final damage.
            self.rows_all_initial_final_damage_combinations (Numpy array):
                Array with row numbers of self.all_initial_final_damage_combinations.
            self.logic_tree_weights (dict):
                Dictionary with one key per hazard of "logic_tree_meta", and one sub-key per
                branch of the hazard's logic tree. Each of the latter sub-keys contains a float
                that is the weight of the branch. E.g.:
                {
                    "EQ": {"earthq_1": 0.5, "earthq_2": 0.2, "earthq_3": 0.3},
                    "TSU": {"tsun_1": 0.25, "tsun_2": 0.75}
                }
            self.all_logic_tree_combination_weights (Pandas DataFrame):
                DataFrame with the full-path end-branch weights that result from combining all
                branches for all hazards ("weight_branches" column) as well as the full-path
                end-branch realisation weights that result from combining all branches for all
                hazards and the number of realisations per hazard ("weight_realisations" column).
                It also contains one column per hazard, indicating the name of the branch of each
                hazard associated with a row. Each row is one full-path end-branch combination.
        """
        self.post_processing_config = post_processing_config
        self.general_output_path = general_output_path

        self.all_initial_final_damage_combinations = calculate_all_damage_combinations(
            self.post_processing_config["initial_damage_range"],
            self.post_processing_config["final_damage_range"]
        )

        self.rows_all_initial_final_damage_combinations = np.array(
            range(self.all_initial_final_damage_combinations.shape[0])
        )

        self.all_logic_tree_combination_weights, self.logic_tree_weights = (
            calculate_all_logic_tree_combination_weights(
                self.post_processing_config["logic_tree_meta"]
            )
        )

    def export(self):
        summaries = {}

        if self.post_processing_config["types"]["by_initial_and_final_damage_per_branch"]:
            summaries["by_initial_and_final_damage_per_branch"] = (
                self.calculate_by_initial_and_final_damage_per_branch()
            )

        return summaries
        
    def calculate_by_initial_and_final_damage_per_branch(self):
        """
        This method calculates weighted means, weighted standard deviations and weighted
        quantiles of the number of buildings, incremental losses and cumulative losses by
        combination of initial and final damage state, per branch of each hazard indicated in
        'self.post_processing_config["logic_tree_meta"]'.

        Resulting statistics are exported to `self.general_output_path`\statistics with
        filenames following the pattern
        "by_initial_and_final_damage_by_branch_STATNAME_HAZPREFIX_b_BRANCHNAME.csv", where:
        - STATNAME: name of the statistics (means, stdev, ...)
        - HAZPREFIX: hazard prefix
        - BRANCHNAME: branch name

        Returns:
            summary_number_files (Pandas DataFrame):
                DataFrame summarising the number of files that were found and used to calculate
                the statistics of each branch of each hazard. Columns:
                    "hazard": Name (prefix) of the hazard.
                    "branch": Name of the branch,
                    "number_files": Number of files.
        """
        logger.info(
            "Calculating per-branch stats of number of buildings and losses "
            "per initial and final damage state"
        )

        columns_to_use = ["number", "incremental_loss", "cum_loss_value"]

        gather_hazards = []
        gather_branches = []
        gather_number_files = []

        for haz in self.post_processing_config["logic_tree_meta"].keys():

            haz_prefix = self.post_processing_config["logic_tree_meta"][haz]["hazard_prefix"]

            logger.info("    Working on hazard %s: %s" % (haz, haz_prefix))

            for branch in self.logic_tree_weights[haz_prefix]:
                logger.info("        Working on branch %s" % (branch))

                # Retrieve filenames associated with this branch of this hazard
                substring = ("%s_b_%s_r_" % (haz_prefix, branch))

                matching_files = [
                    f for f in os.listdir(self.general_output_path)
                    if substring.lower() in f.lower()
                ]

                # Now filter those 'matching_files' to be only those that contain
                # "by_initial_and_final_damage" results
                target_output = "by_initial_and_final_damage"

                matching_files = [
                    f for f in matching_files
                    if target_output.lower() in f.lower()
                ]

                logger.info("            Found %s files" % (len(matching_files)))
                
                gather_hazards.append(haz_prefix)
                gather_branches.append(branch)
                gather_number_files.append(len(matching_files))

                all_data = np.zeros(
                    (
                        self.all_initial_final_damage_combinations.shape[0],
                        len(columns_to_use),
                        len(matching_files)
                    )
                )
                weights = np.zeros(len(matching_files))

                for k, filename in enumerate(matching_files):
                    # Retrieve results of this realisation
                    df = pd.read_csv(
                        os.path.join(self.general_output_path, filename),
                        index_col=[0, 1]
                    )

                    # It may be that this df does not have all possible combinations of
                    # initial and final damage, so cast into standard shape
                    rows_to_fill = self.rows_all_initial_final_damage_combinations[
                        self.all_initial_final_damage_combinations.isin(df.index)
                    ]
                    all_data[rows_to_fill, :, k] = df[columns_to_use].to_numpy()

                    # Retrieve weight of this realisation
                    haz_branch_realisation_info = (
                        retrieve_hazard_branch_realisation_from_filename(filename)
                    )
                    filtered_weights = retrieve_weight(
                        haz_branch_realisation_info, self.all_logic_tree_combination_weights
                    )
                    weights[k] = filtered_weights.loc[0, "weight_realisations"]

                normalised_weights = weights / weights.sum()

                filename_stem = ("%s_b_%s" % (haz_prefix, branch))
                
                weighted_means = np.average(
                    all_data, axis=2, weights=normalised_weights
                )
                weighted_means_df = pd.DataFrame(
                    weighted_means,
                    columns=columns_to_use,
                    index=self.all_initial_final_damage_combinations
                )
                weighted_means_df.to_csv(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "by_initial_and_final_damage_by_branch_means_%s.csv" % (filename_stem)
                    ),
                    index=True
                )

                weighted_st_dev_df = pd.DataFrame(
                    weighted_sample_unbiased_stdev_3D(
                        all_data, normalised_weights, weighted_means
                    ),
                    columns=columns_to_use,
                    index=self.all_initial_final_damage_combinations
                )
                weighted_st_dev_df.to_csv(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "by_initial_and_final_damage_by_branch_stdev_%s.csv" % (filename_stem)
                    ),
                    index=True
                )

                quantiles = np.quantile(
                    all_data,
                    self.post_processing_config["target_quantiles"],
                    axis=2,
                    weights=normalised_weights,
                    method="inverted_cdf"
                )

                for q, quantile in enumerate(self.post_processing_config["target_quantiles"]):
                    quantile_str = "{:.2f}".format(quantile).replace(".", "_")

                    quantile_df = pd.DataFrame(
                        quantiles[q, :, :],
                        columns=columns_to_use,
                        index=self.all_initial_final_damage_combinations
                    )
                    quantile_df.to_csv(
                        os.path.join(
                            self.general_output_path, "statistics",
                            "by_initial_and_final_damage_by_branch_q_%s_%s.csv" % (
                                quantile_str, filename_stem
                            )
                        ),
                        index=True
                    )

        summary_number_files = pd.DataFrame(
            {
                "hazard": gather_hazards,
                "branch": gather_branches,
                "number_files": gather_number_files
            }
        )
        summary_number_files.to_csv(
            os.path.join(
                self.general_output_path,
                "statistics",
                "by_initial_and_final_damage_by_branch_meta_summary.csv"
            ),
            index=False
        )

        return summary_number_files


def calculate_all_damage_combinations(initial_damage_range, final_damage_range):
    """
    This method determines all possible combinations of initial and final damage states that are
    phisically possible (without repairs), i.e., where initial damage <= final damage.

    Args:
        initial_damage_range, final_damage_range (lists of int):
             List of integers designating the initial/final damage states, ordered from smallest
             (0) to largest.

    Returns:
        all_initial_final_damage_combinations (Pandas MultiIndex):
            MultiIndex of all combinations of initial and final damage states that are
            physically possible, i.e. all cases in which initial damage <= final damage.
    """
    all_combinations_initial = []
    all_combinations_final = []

    for initial_dmg in initial_damage_range:
        for final_dmg in final_damage_range:
            if initial_dmg <= final_dmg:
                all_combinations_initial.append(initial_dmg)
                all_combinations_final.append(final_dmg)

    aux = [all_combinations_initial, all_combinations_final]
    all_initial_final_damage_combinations = pd.MultiIndex.from_arrays(
        aux, names=("initial_damage", "final_damage")
    )

    return all_initial_final_damage_combinations


def calculate_all_logic_tree_combination_weights(logic_tree_meta):
    """
    This method determines all the full-path end-branch combinations of all logic tree branches
    of all hazards indicated in the logic tree metadata ('logic_tree_meta'), as well as their
    associated weights, both at the branch level and considering all realisations of each hazard.

    Args:
        logic_tree_meta (dict):
            Dictionary with integers >=1 as sub-keys, indicating the order in which the hazards
            are applied. For each hazard, the subkey is a dictionary with at least the following
            parameters:
                "hazard_prefix" (str):
                    E.g. "EQ", "TSU".
                "logic_tree_path" (str):
                    Full path to CSV file containing the logic tree associated with this
                    hazard (the file contains all names and weights of the logic tree
                    branches).
                "realisations" (int > 0):
                    Number of realisations per logic tree branch.

    Returns:
        all_logic_tree_combination_weights (Pandas DataFrame):
            DataFrame with the full-path end-branch weights that result from combining all
            branches for all hazards ("weight_branches" column) as well as the full-path
            end-branch realisation weights that result from combining all branches for all
            hazards and the number of realisations per hazard ("weight_realisations" column).
            It also contains one column per hazard, indicating the name of the branch of each
            hazard associated with a row. Each row is one full-path end-branch combination.
        logic_tree_weights (dict):
            Dictionary with one key per hazard of 'logic tree' (the key is the "hazard_prefix"
            of 'logic tree'), and one sub-key per branch of the hazard's logic tree. Each of the
            latter sub-keys contains a float that is the weight of the branch. E.g.:
            {
                "EQ": {"earthq_1": 0.5, "earthq_2": 0.2, "earthq_3": 0.3},
                "TSU": {"tsun_1": 0.25, "tsun_2": 0.75}
            }
    """
    logic_tree_weights = load_logic_tree_weights(logic_tree_meta)

    main_keys = list(logic_tree_weights.keys())
    value_lists = [list(logic_tree_weights[k].items()) for k in main_keys]

    # Create all logic tree paths (all possible combinations of branches of different hazards)
    rows = []
    for combo in itertools.product(*value_lists):
        row = { mk: sk for mk, (sk, _) in zip(main_keys, combo) }
        row["weight_branches"] = math.prod(w for (_, w) in combo)
        rows.append(row)

    all_logic_tree_combination_weights = pd.DataFrame(rows)

    # Reorder columns so main_keys come first
    all_logic_tree_combination_weights = all_logic_tree_combination_weights[
        [*main_keys, "weight_branches"]
    ]

    # Calculate weights of each realisation (= weight of branch / number of realisations)
    all_logic_tree_combination_weights["weight_realisations"] = deepcopy(
        all_logic_tree_combination_weights["weight_branches"]
    )

    for haz in logic_tree_meta.keys():
        number_realisations = logic_tree_meta[haz]["realisations"]
        realisation_weight = 1.0 / number_realisations

        all_logic_tree_combination_weights["weight_realisations"] = (
            all_logic_tree_combination_weights["weight_realisations"]
            * realisation_weight
        )

    return all_logic_tree_combination_weights, logic_tree_weights


def load_logic_tree_weights(logic_tree_meta):
    """
    This method retrieves the logic trees associated with all hazards in 'logic_tree_meta'.

    Args:
        logic_tree_meta (dict):
            Dictionary with integers >=1 as sub-keys, indicating the order in which the hazards
            are applied. For each hazard, the subkey is a dictionary with at least the following
            parameters:
                "hazard_prefix" (str):
                    E.g. "EQ", "TSU".
                "logic_tree_path" (str):
                    Full path to CSV file containing the logic tree associated with this
                    hazard (the file contains all names and weights of the logic tree
                    branches).

    Returns:
        logic_tree_weights (dict):
            Dictionary with one key per hazard of 'logic tree' (the key is the "hazard_prefix"
            of 'logic tree'), and one sub-key per branch of the hazard's logic tree. Each of the
            latter sub-keys contains a float that is the weight of the branch. E.g.:
            {
                "EQ": {"earthq_1": 0.5, "earthq_2": 0.2, "earthq_3": 0.3},
                "TSU": {"tsun_1": 0.25, "tsun_2": 0.75}
            }
    """
    logic_tree_weights = {}

    for haz in logic_tree_meta.keys():
        haz_prefix = logic_tree_meta[haz]["hazard_prefix"]
        logic_tree_weights[haz_prefix] = {}
        haz_weights = pd.read_csv(logic_tree_meta[haz]["logic_tree_path"], index_col=0)

        sum_of_weights = haz_weights["weight"].sum()

        if round(sum_of_weights, 5) != 1.0:
            error_message = (
                "The weights of the logic tree branches of hazard %s do not add up to 1. "
                "The program cannot run." % (haz_prefix)
            )
            logger.critical(error_message)
            raise OSError(error_message)

        for branch in haz_weights.index:
            logic_tree_weights[haz_prefix][branch] = haz_weights.loc[branch, "weight"]

    return logic_tree_weights


def retrieve_hazard_branch_realisation_from_filename(filename):
    """
    This method decodes the 'filename' string to retrieve information on the whole hazard chain
    that the results it contains refers to. For each hazard, it retrieves its prefix, branch
    name and realisation number.

    This method assumes filenames are created with the 'OutputGenerator' class.

    Args:
        filename (str):
            Name of the output file with pattern
            "HAZ_B_b_CCC_r_SSS_HAZ_A_b_BBB_r_RRR_EXPOSUREFILENAME_output_type.extension",
            where:
            - "HAZ_B", "HAZ_A", etc, are the "hazard_prefix"
            - "BBB", "CCC", etc, are the names of the branches of the hazard intensity logic tree
                (for each hazard that has been run)
            - "RRR", "SSS", etc, are the realisation numbers within branches "BBB", "CCC", etc,
                respectively
            - "EXPOSUREFILENAME" is the name of the input exposure file, removing the extension, 
            - "output_type" is the type of output.
            
    Returns:
        results (list of dict):
            List with one dictionary per hazard that has been run. Each dictionary contains:
                {
                    "prefix": hazard prefix, e.g., "HAZ_A", "HAZ_B",
                    "b": branch name, e.g., "BBB", "CCC",
                    "r": realisation number, e.g., "RRR", "SSS"
                }
    """
    # Remove extension
    base = filename.rsplit(".", 1)[0]

    pattern = re.compile(
        r"(?:^|_)(?P<prefix>.+?)(?=_b_)"   # either start‐of‐string or “_”, then prefix up to “_b_”
        r"_b_(?P<b>.+?)(?=_r_)"           # “_b_” then b‐value (can have “_”) up to “_r_”
        r"_r_(?P<r>[^_\.]+)"              # “_r_” then r‐value (no “_” or “.”)
    )

    # Find all non‐overlapping matches
    matches = pattern.finditer(base)

    # Collect into a list of dicts
    results = []
    for m in matches:
        d = m.groupdict()
        results.append(d)

    return results


def retrieve_weight(haz_branch_realisation_info, all_logic_tree_combination_weights):
    """
    This method retrieves from 'all_logic_tree_combination_weights' the full-path logic tree end
    branch weight of the combination of hazard branches specified in
    'haz_branch_realisation_info'.

    Args:
        haz_branch_realisation_info (list of dict):
            List with one dictionary per hazard that has been run, indicating the branch and
            realisation. It is the output of 'retrieve_hazard_branch_realisation_from_filename'.
            Each dictionary contains:
                {"prefix": hazard prefix, "b": branch name, "r": realisation number}
        all_logic_tree_combination_weights (Pandas DataFrame):
            DataFrame with the full-path end-branch weights that result from combining all
            branches for all hazards ("weight_branches" column) as well as the full-path
            end-branch realisation weights that result from combining all branches for all
            hazards and the number of realisations per hazard ("weight_realisations" column).
            It also contains one column per hazard, indicating the name of the branch of each
            hazard associated with a row. Each row is one full-path end-branch combination.
            It is the output of 'calculate_all_logic_tree_combination_weights'.
        
    Returns:
        filtered_weights (Pandas DataFrame):
            The one row of 'all_logic_tree_combination_weights' that refers to the full-path
            logic tree end branch requested in 'haz_branch_realisation_info'. Same structure and
            contents of 'all_logic_tree_combination_weights'.
    """

    filtered_weights = None

    for q in range(len(haz_branch_realisation_info)):
        file_hazard_prefix = haz_branch_realisation_info[q]["prefix"]
        file_hazard_branch = haz_branch_realisation_info[q]["b"]

        if filtered_weights is None:
            filtered_weights = all_logic_tree_combination_weights[
                all_logic_tree_combination_weights[file_hazard_prefix] == file_hazard_branch
            ].copy()
        else:
            filtered_weights = filtered_weights[
                filtered_weights[file_hazard_prefix] == file_hazard_branch
            ].copy()
        filtered_weights.reset_index(inplace=True)
        filtered_weights.drop(columns=["index"], inplace=True)

    if filtered_weights.shape[0] != 1:
        problem_data = []
        for q in range(len(haz_branch_realisation_info)):
            file_hazard_prefix = haz_branch_realisation_info[q]["prefix"]
            file_hazard_branch = haz_branch_realisation_info[q]["b"]
            problem_data.append("%s: %s" % (file_hazard_prefix, file_hazard_branch))

        error_message = (
            "The search for full-path end branch weights by 'retrieve_weight' has yielded %s "
            "rows instead of 1. The program cannot run. Please check the input logic trees and "
            "logic tree metadata. Problem found with %s."
            % (filtered_weights.shape[0], ", ".join(problem_data))
        )
        logger.critical(error_message)
        raise OSError(error_message)

    return filtered_weights


def weighted_sample_unbiased_stdev_1D(data_1D, weights, weighted_mean):
    """
    This method calculates the unbiased weighted sample standard deviation for a 1D array
    ('data_1D') with reliability weights 'weights' and weighted mean 'weighted_mean'. It is
    assumed that 'weighted_mean' has been calcualted with the same 'data_1D' and 'weights'.

    See Wikipedia for further details:
    https://en.wikipedia.org/wiki/Weighted_arithmetic_mean#Weighted_sample_variance

    Args:
        data_1D (arr of float): 1D array of individual data values. Length "L".
        weights (arr of float): 1D array of data weights. Length "L".
        weighted_mean (float): weighted mean of 'data_1D' and 'weights'.

    Returns:
        sw (float): Unbiased weighted sample standard deviation.
    """
    v1 = weights.sum()
    v2 = (np.power(weights, 2.0)).sum()

    numerator = (weights * np.power(data_1D - weighted_mean, 2.0)).sum()
    sw = np.sqrt(numerator / (v1 - (v2/v1)))

    return sw


def weighted_sample_unbiased_stdev_3D(data_3D, weights, weighted_means):
    """
    This method calculates the unbiased weighted sample standard deviation along axis=2 of a 3D
    array ('data_3D') with reliability weights 'weights' and weighted mean 'weighted_means'
    (2D array). It is assumed that 'weighted_means' has been calcualted with the same 'data_3D'
    and 'weights', also along axis=2. It calls 'weighted_sample_unbiased_stdev_1D'.
    
    Args:
        data_3D (arr of float): 3D array of individual data values.
            Dimensions: num_rows x num_cols x num_data_points.
        weights (arr of float): 1D array of data weights. Length: num_data_points.
        weighted_means (arr of float): 2D array with weighted means of 'data_3D' (along axis=2)
            and 'weights'. Dimensions: num_rows x num_cols.

    Returns:
        sw (arr of float): 2D array with unbiased weighted sample standard deviation.
    """

    num_rows, num_cols, num_data_points = data_3D.shape

    sw = np.zeros_like(weighted_means)

    for row in range(num_rows):
        for col in range(num_cols):
            sw[row, col] = weighted_sample_unbiased_stdev_1D(
                data_3D[row, col, :], weights, weighted_means[row, col]
            )

    return sw
