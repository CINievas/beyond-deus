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
from beyonddeus.exposure import (
    read_exposure_intensity_combinations,
    check_exposure_intensity_combinations
)

logger = logging.getLogger()


class PostProcessor:
    def __init__(
        self, post_processing_config, general_output_path, economic_consequence_input_path
    ):
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
                    "export_weight_per_file" (bool): If True, the weights used for each results
                        file of each post-processing ouput will be exported to a CSV.
                    "export_filenames_in_all_values_outputs" (bool): If True, the names of the
                        filenames from which each value stems are exported to the "all_values"
                        output CSVs.
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
                            "weight_of_realisation" (0 < float <= 1):
                                Weight of one realisation of this hazard, independently of the
                                branch weight.
                    "initial_damage_range" (list of int):
                        List of integers designating the initial damage states (of the last
                        hazard run).
                    "final_damage_range" (list of int):
                        List of integers designating the final damage states (of the last hazard
                        run).
                    "per_branch_which_hazards" (list of str):
                        List of hazards (as hazard prefixes from "logic_tree_meta") for which
                        the per-branch results will be post-processed (if options such as
                        "by_final_damage_per_branch", etc., are selected).
                    "types":
                        Dictionary indicating the kind of post-processing outputs to export, by
                        means of True/False. Options are sets of nested keys:
                            "by_final_damage_all": Mean, quantiles and standard deviation of
                                number of buildings, incremental loss and cumulative loss, per
                                final damage state, for all branches and realisations considered
                                together, with their weights. All individual values are exported
                                as well.
                            "by_final_damage_per_branch": Mean, quantiles and standard deviation
                                of number of buildings, incremental loss and cumulative loss,
                                per final damage state, for each branch of each hazard run so
                                far.
                            "by_initial_and_final_damage_all": Mean, quantiles and standard
                                deviation of number of buildings, incremental loss and
                                cumulative loss, per combination of initial-final damage states,
                                for all branches and realisations considered together, with
                                their weights. All individual values are exported as well.
                            "by_initial_and_final_damage_per_branch": Mean, quantiles and
                                standard deviation of number of buildings, incremental loss and
                                cumulative loss, per combination of initial-final damage states,
                                for each branch of each hazard run so far.
                            "loss_by_building_id_all": Mean, quantiles and standard deviation
                                of incremental loss (absolute and ratio) and cumulative loss
                                (absolute and ratio) per building_id, for all branches and
                                realisations considered together, with their weights.
                            "damage_by_building_id_all": Mean, quantiles and standard deviation
                                of number and proportion of buildings per damage state, per
                                building_id and for all branches and realisations considered
                                together, with their weights.
                            "damage_with_people_by_building_id_all": Mean, quantiles and
                                standard deviation of number and proportion of buildings, and
                                number of census people per damage state, per building_id and
                                or all branches and realisations considered together, with their
                                weights.
                            "loss_by_building_id_per_branch": Mean, quantiles and standard
                                deviation of incremental loss (absolute and ratio) and
                                cumulative loss (absolute and ratio) per building_id, for each
                                branch of each hazard run so far.
                            "damage_by_building_id_per_branch": Mean, quantiles and standard
                                deviation of number and proportion of buildings per damage state,
                                per building_id and for each branch of each hazard run so far.
                            "damage_with_people_by_building_id_per_branch": Mean, quantiles and
                                standard deviation of number and proportion of buildings, and
                                number of census people per damage state, per building_id and
                                for each branch of each hazard run so far.
            self.general_output_path (str):
                Path to directory where outputs to be post-processed are stored, and where
                post-processing results will be stored (under the "statistics" sub-directory).
            self.include_economic_losses (bool):
                If True, outputs associated with economic losses will be post-processed. If
                False, they will not.
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

        if economic_consequence_input_path != "None":
            self.include_economic_losses = True
        else:
            self.include_economic_losses = False

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

    def export(self, exposure_geoms):
        """
        Args:
            exposure_geoms (GeoPandas GeoDataFrame):
                GeoDataFrame with the geometries of the exposure polygons. The indices are the
                exposure "building_id"s. Only necessary if post-processing "by_building"
                results, otherwise can be None.
        """
        summaries = {}

        if self.post_processing_config["types"]["by_final_damage_all"]:
            summaries["by_final_damage_all"] = (
                self.calculate_total_stats_by_initial_and_final_damage(
                    "by_final_damage",
                    self.post_processing_config["export_filenames_in_all_values_outputs"]
                )
            )

        if self.post_processing_config["types"]["by_final_damage_per_branch"]:
            summaries["by_final_damage_per_branch"] = (
                self.calculate_by_initial_and_final_damage_per_branch(
                    "by_final_damage", self.post_processing_config["per_branch_which_hazards"]
                )
            )

        if self.post_processing_config["types"]["by_initial_and_final_damage_all"]:
            summaries["by_initial_and_final_damage_all"] = (
                self.calculate_total_stats_by_initial_and_final_damage(
                    "by_initial_and_final_damage",
                    self.post_processing_config["export_filenames_in_all_values_outputs"]
                )
            )

        if self.post_processing_config["types"]["by_initial_and_final_damage_per_branch"]:
            summaries["by_initial_and_final_damage_per_branch"] = (
                self.calculate_by_initial_and_final_damage_per_branch(
                    "by_initial_and_final_damage",
                    self.post_processing_config["per_branch_which_hazards"]
                )
            )

        if self.post_processing_config["types"]["loss_by_building_id_all"]:
            columns_to_use = [
                "number",
                "incremental_loss",
                "cum_loss_value",
                "incremental_loss_ratio",
                "cum_loss_ratio"
            ]
            summaries["loss_by_building_id_all"] = (
                self.calculate_stats_by_building_id_total(
                    "loss", columns_to_use, exposure_geoms
                )
            )

        if self.post_processing_config["types"]["damage_by_building_id_all"]:

            columns_to_use = ["number"]
            subtypes = ["number", "proportion"]
            for subtype in subtypes:
                for dmg_state in self.post_processing_config["final_damage_range"]:
                    columns_to_use.append("%s_D%s" % (subtype, dmg_state))

            summaries["damage_by_building_id_all"] = (
                self.calculate_stats_by_building_id_total(
                    "damage", columns_to_use, exposure_geoms
                )
            )

        if self.post_processing_config["types"]["damage_with_people_by_building_id_all"]:

            columns_to_use = ["number"]
            subtypes = ["number", "proportion", "ppl_census"]
            for subtype in subtypes:
                for dmg_state in self.post_processing_config["final_damage_range"]:
                    columns_to_use.append("%s_D%s" % (subtype, dmg_state))

            summaries["damage_with_people_by_building_id_all"] = (
                self.calculate_stats_by_building_id_total(
                    "damage_with_people", columns_to_use, exposure_geoms
                )
            )

        if self.post_processing_config["types"]["loss_by_building_id_per_branch"]:
            columns_to_use = [
                "number",
                "incremental_loss",
                "cum_loss_value",
                "incremental_loss_ratio",
                "cum_loss_ratio"
            ]
            summaries["loss_by_building_id_per_branch"] = (
                self.calculate_stats_by_building_id_per_branch(
                    "loss", columns_to_use, exposure_geoms,
                    self.post_processing_config["per_branch_which_hazards"]
                )
            )

        if self.post_processing_config["types"]["damage_by_building_id_per_branch"]:

            columns_to_use = ["number"]
            subtypes = ["number", "proportion"]
            for subtype in subtypes:
                for dmg_state in self.post_processing_config["final_damage_range"]:
                    columns_to_use.append("%s_D%s" % (subtype, dmg_state))

            summaries["damage_by_building_id_per_branch"] = (
                self.calculate_stats_by_building_id_per_branch(
                    "damage", columns_to_use, exposure_geoms,
                    self.post_processing_config["per_branch_which_hazards"]
                )
            )

        if self.post_processing_config["types"]["damage_with_people_by_building_id_per_branch"]:

            columns_to_use = ["number"]
            subtypes = ["number", "proportion", "ppl_census"]
            for subtype in subtypes:
                for dmg_state in self.post_processing_config["final_damage_range"]:
                    columns_to_use.append("%s_D%s" % (subtype, dmg_state))

            summaries["damage_with_people_by_building_id_per_branch"] = (
                self.calculate_stats_by_building_id_per_branch(
                    "damage_with_people", columns_to_use, exposure_geoms,
                    self.post_processing_config["per_branch_which_hazards"]
                )
            )

        return summaries


    def calculate_by_initial_and_final_damage_per_branch(self, target_output, hazards):
        r"""
        This method calculates weighted means, weighted standard deviations and weighted
        quantiles of the number of buildings, incremental losses and cumulative losses by
        combination of initial and final damage state (target_output =
        "by_initial_and_final_damage"), or by final damage state only (target_output =
        "by_final_damage"), per branch of each hazard indicated in
        'self.post_processing_config["logic_tree_meta"]' and 'hazards'.

        Resulting statistics are exported to `self.general_output_path`\statistics with
        filenames following the pattern
        "by_initial_and_final_damage_by_branch_STATNAME_HAZPREFIX_b_BRANCHNAME.csv", where:
        - STATNAME: name of the statistics (means, stdev, ...)
        - HAZPREFIX: hazard prefix
        - BRANCHNAME: branch name

        If self.post_processing_config["export_weight_per_file"] is True, a CSV file containing
        the list of results files and weights used for the statistics is created.

        Args:
            target_output (str):
                Kind of output over which to calculate stats. Supported values:
                "by_initial_and_final_damage", "by_final_damage".
            hazards (list of str):
                List of hazard prefixes to be used.

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
            "%s state" % (target_output.replace("_", " ").replace("by", "per"))
        )

        # Use either all combinations of initial and final damage, or just the final damage
        if target_output=="by_initial_and_final_damage":
            out_combinations = deepcopy(self.all_initial_final_damage_combinations)
            index_columns=[0, 1]
        elif target_output=="by_final_damage":
            out_combinations = pd.Index(self.post_processing_config["final_damage_range"])
            index_columns=0
        else:
            out_combinations = None
        rows_out_combinations = np.array(
            range(out_combinations.shape[0])
        )

        if self.include_economic_losses:
            columns_to_use = ["number", "incremental_loss", "cum_loss_value"]
        else:
            columns_to_use = ["number"]

        gather_hazards = []
        gather_branches = []
        gather_number_files = []

        for haz in self.post_processing_config["logic_tree_meta"].keys():

            haz_prefix = self.post_processing_config["logic_tree_meta"][haz]["hazard_prefix"]

            if haz_prefix not in hazards:
                continue  # skip this hazard

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
                # "by_initial_and_final_damage" or "by_final_damage" (target_output) results
                matching_files = [
                    f for f in matching_files
                    if target_output.lower() in f.lower()
                ]

                logger.info("            Found %s files" % (len(matching_files)))

                gather_hazards.append(haz_prefix)
                gather_branches.append(branch)
                gather_number_files.append(len(matching_files))

                if len(matching_files) < 1:  # No files found
                    logger.info("                No stats to be produced")
                    break

                all_data = np.zeros(
                    (
                        out_combinations.shape[0],
                        len(columns_to_use),
                        len(matching_files)
                    )
                )
                weights = np.zeros(len(matching_files))

                for k, filename in enumerate(matching_files):
                    # Retrieve results of this realisation
                    df = pd.read_csv(
                        os.path.join(self.general_output_path, filename),
                        index_col=index_columns
                    )

                    # It may be that this df does not have all possible combinations of
                    # initial and final damage, so cast into standard shape
                    rows_to_fill = rows_out_combinations[out_combinations.isin(df.index)]
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

                if self.post_processing_config["export_weight_per_file"]:
                    weights_df = pd.DataFrame(
                        {
                            "weights_raw": weights,
                            "weights_final": normalised_weights
                        },
                        index=matching_files
                    )
                    weights_df.to_csv(
                        os.path.join(
                            self.general_output_path, "statistics",
                            "%s_by_branch_stats_weights_%s.csv" % (target_output, filename_stem)
                        ),
                        index=True
                    )

                weighted_means = np.average(
                    all_data, axis=2, weights=normalised_weights
                )
                weighted_means_df = pd.DataFrame(
                    weighted_means,
                    columns=columns_to_use,
                    index=out_combinations
                )
                weighted_means_df.to_csv(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "%s_by_branch_means_%s.csv" % (target_output, filename_stem)
                    ),
                    index=True
                )

                weighted_st_dev_df = pd.DataFrame(
                    weighted_sample_unbiased_stdev_3D(
                        all_data, normalised_weights, weighted_means
                    ),
                    columns=columns_to_use,
                    index=out_combinations
                )
                weighted_st_dev_df.to_csv(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "%s_by_branch_stdev_%s.csv" % (target_output, filename_stem)
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
                        index=out_combinations
                    )
                    quantile_df.to_csv(
                        os.path.join(
                            self.general_output_path, "statistics",
                            "%s_by_branch_q_%s_%s.csv" % (
                                target_output, quantile_str, filename_stem
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
                "%s_by_branch_meta_summary.csv" % (target_output)
            ),
            index=False
        )

        return summary_number_files


    def calculate_total_stats_by_initial_and_final_damage(self, target_output, exportfilenames):
        r"""
        This method calculates weighted means, weighted standard deviations and weighted
        quantiles of the number of buildings, incremental losses and cumulative losses by
        combination of initial and final damage state (target_output =
        "by_initial_and_final_damage") or by final damage state only (target_output =
        "by_final_damage"), for the whole set of results available in 'self.general_output_path',
        assumed to correspond to all branches and realisations of
        'self.post_processing_config["logic_tree_meta"]'.

        Resulting statistics are exported to `self.general_output_path`\statistics with
        filenames following the pattern "by_initial_and_final_damage_by_branch_STATNAME.csv", or
        "by_final_damage_by_branch_STATNAME.csv", where STATNAME is the name of the statistics
        (means, stdev, ...).

        All the individual values from all realisations are also exported as (economic losses
        only if self.include_economic_losses is True):
        - "portfolio_total_losses_all_values.csv": One row per inidividual realisation, three
        columns (number of buildings, incremental losses and cumulative losses), for all damage
        states together.
        - "TARGET_OUTPUT_total_all_values_cum_loss_value.csv": One row per inidividual
        realisation, one column per final damage state (target_output = "by_final_damage" ) or
        combination of initial-final damage states (target_output =
        "by_initial_and_final_damage"). Values are cumulative economic losses.
        - "TARGET_OUTPUT_total_all_values_incremental_loss.csv: One row per inidividual
        realisation, one column per final damage state (target_output = "by_final_damage" ) or
        combination of initial-final damage states (target_output =
        "by_initial_and_final_damage"). Values are incremental economic losses.
        - "TARGET_OUTPUT_total_all_values_number.csv": One row per inidividual
        realisation, one column per final damage state (target_output = "by_final_damage" ) or
        combination of initial-final damage states (target_output =
        "by_initial_and_final_damage"). Values are number of buildings.
        In all of the above, if 'exportfilenames' is True, source filenames are included.

        If self.post_processing_config["export_weight_per_file"] is True, a CSV file containing
        the list of results files and weights used for the statistics is created.

        Args:
            target_output (str):
                Kind of output over which to calculate stats. Supported values:
                "by_initial_and_final_damage", "by_final_damage".
            exportfilenames (bool):
                If True, the names of the filenames from which each value of the "all_values"
                files comes is exported.

        Returns:
            summary_number_files (Pandas DataFrame):
                DataFrame summarising the number of files that were found and used to calculate
                the statistics of each branch of each hazard. Columns:
                    "hazard": Name (prefix) of the hazard.
                    "branch": Name of the branch,
                    "number_files": Number of files.
        """
        logger.info(
            "Calculating total stats of number of buildings and losses "
            "%s state" % (target_output.replace("_", " ").replace("by", "per"))
        )

        # Use either all combinations of initial and final damage, or just the final damage
        if target_output=="by_initial_and_final_damage":
            out_combinations = deepcopy(self.all_initial_final_damage_combinations)
            index_columns=[0, 1]
        elif target_output=="by_final_damage":
            out_combinations = pd.Index(self.post_processing_config["final_damage_range"])
            index_columns=0
        else:
            out_combinations = None
        rows_out_combinations = np.array(
            range(out_combinations.shape[0])
        )

        if self.include_economic_losses:
            columns_to_use = ["number", "incremental_loss", "cum_loss_value"]
        else:
            columns_to_use = ["number"]

        # Initialise list to collect all data:
        all_data_slices = []  # each element will be a 2D array

        # Initialise "weights" to collect weights, same dimension as "depth" of "all_data"
        weights = []

        matching_files = [
            f for f in os.listdir(self.general_output_path)
            if target_output.lower() in f.lower()
        ]

        summary_number_files = pd.DataFrame(
            {
                "hazard": ["all"],
                "branch": ["all"],
                "number_files": [len(matching_files)]
            }
        )
        summary_number_files.to_csv(
            os.path.join(
                self.general_output_path,
                "statistics",
                "%s_total_meta_summary.csv" % (target_output)
            ),
            index=False
        )

        logger.info("    Found %s files" % (len(matching_files)))

        if len(matching_files) < 1:  # No files found
            logger.info("        No stats to be produced")
            return summary_number_files

        for k, filename in enumerate(matching_files):
            # Retrieve results of this realisation
            df = pd.read_csv(
                os.path.join(self.general_output_path, filename),
                index_col=index_columns
            )

            # All arrays that go into "all_data_slices" need to have the same shape, but it may
            # be that this df does not have all possible combinations of initial and final
            # damage, so cast into standard shape
            structure_array = np.zeros((out_combinations.shape[0], len(columns_to_use)))
            rows_to_fill = rows_out_combinations[out_combinations.isin(df.index)]
            structure_array[rows_to_fill, :] = df[columns_to_use].to_numpy()
            # If this df didn't have all combinations, those rows will have zeroes

            all_data_slices.append(structure_array)

            # Retrieve weight of this realisation
            haz_branch_realisation_info = (
                retrieve_hazard_branch_realisation_from_filename(filename)
            )
            filtered_weights = retrieve_weight(
                haz_branch_realisation_info, self.all_logic_tree_combination_weights
            )
            weights.append(filtered_weights.loc[0, "weight_realisations"])

        all_data = np.stack(all_data_slices, axis=2)
        # Dimensions of "all_data":
        # rows: all initial and final damage combinations
        # columns: columns_to_use
        # depth: the number of data results

        logger.info("    A total of %s realisations were retrieved" % (all_data.shape[2]))

        weights = np.array(weights)
        normalised_weights = weights / weights.sum()

        if self.post_processing_config["export_weight_per_file"]:
            weights_df = pd.DataFrame(
                {
                    "weights_raw": weights,
                    "weights_final": normalised_weights
                },
                index=matching_files
            )
            weights_df.to_csv(
                os.path.join(
                    self.general_output_path, "statistics",
                    "%s_total_stats_weights.csv" % (target_output)
                ),
                index=True
            )

        weighted_means = np.average(
            all_data, axis=2, weights=normalised_weights
        )
        weighted_means_df = pd.DataFrame(
            weighted_means,
            columns=columns_to_use,
            index=out_combinations
        )
        weighted_means_df.to_csv(
            os.path.join(
                self.general_output_path, "statistics",
                "%s_total_means.csv" % (target_output)
            ),
            index=True
        )

        weighted_st_dev_df = pd.DataFrame(
            weighted_sample_unbiased_stdev_3D(
                all_data, normalised_weights, weighted_means
            ),
            columns=columns_to_use,
            index=out_combinations
        )
        weighted_st_dev_df.to_csv(
            os.path.join(
                self.general_output_path, "statistics",
                "%s_total_stdev.csv" % (target_output)
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
                index=out_combinations
            )
            quantile_df.to_csv(
                os.path.join(
                    self.general_output_path, "statistics",
                    "%s_total_q_%s.csv" % (target_output, quantile_str)
                ),
                index=True
            )

        # Export all individual values from all realisations
        for j, parameter in enumerate(columns_to_use):
            # One row per realisation, one column per initial-final damage combination
            out_df = pd.DataFrame(
                all_data[:, j, :].T,
                columns=out_combinations
            )
            if exportfilenames:
                out_df["filename"] = matching_files

            out_df.to_csv(
                os.path.join(
                    self.general_output_path, "statistics",
                    "%s_total_all_values_%s.csv" % (target_output, parameter)
                ),
                index=False
            )

        # One row per realisation, one column per parameter, all damage states together
        out_df = pd.DataFrame(
            all_data.sum(axis=0).T,
            columns=columns_to_use,
        )
        if exportfilenames:
            out_df["filename"] = matching_files

        out_df.to_csv(
            os.path.join(
                self.general_output_path, "statistics",
                "portfolio_total_losses_all_values.csv"
            ),
            index=False
        )

        return summary_number_files


    def calculate_stats_by_building_id_per_branch(
        self, output_type, columns_to_use, exposure_geoms, hazards
    ):
        r"""
        This method calculates weighted means, weighted standard deviations and weighted
        quantiles of the columns in 'columns_to_use' of 'output_type', per branch of each
        hazard indicated in 'self.post_processing_config["logic_tree_meta"]' and 'hazards'.

        Resulting statistics are exported to `self.general_output_path`\statistics with
        filenames following the pattern
        "OUTPUTTYPE_by_building_id_by_branch_STATNAME_HAZPREFIX_b_BRANCHNAME.csv", where:
        - OUTPUTTYPE: output_type (e.g., "loss", "damage_with_people").
        - STATNAME: name of the statistics (means, stdev, ...)
        - HAZPREFIX: hazard prefix
        - BRANCHNAME: branch name

        All resulting statistics, combined with the exposure geometries in 'exposure_geoms', are
        exported to a GeoPackage file as well. The filename follows the pattern:
        "OUTPUTTYPE_by_building_id_by_branch_stats_HAZPREFIX_b_BRANCHNAME.gpkg".

        If self.post_processing_config["export_weight_per_file"] is True, a CSV file containing
        the list of results files and weights used for the statistics is created.

        Args:
            output_type (str):
                Type of output to calculate statistics from. E.g.: "loss", "damage_with_people".
            columns_to_use (list of str):
                List of names of columns of the output file (of 'output_type') to be used for
                the statistics.
            exposure_geoms (GeoPandas GeoDataFrame):
                GeoDataFrame with the geometries of the exposure polygons. The indices are the
                exposure "building_id"s.
            hazards (list of str):
                List of hazard prefixes to be used.

        Returns:
            summary_number_files (Pandas DataFrame):
                DataFrame summarising the number of files that were found and used to calculate
                the statistics of each branch of each hazard. Columns:
                    "hazard": Name (prefix) of the hazard.
                    "branch": Name of the branch,
                    "number_files": Number of files.
        """
        logger.info("Calculating per-branch %s stats per building_id" % (output_type))

        columns_to_use_as_index = pd.Index(columns_to_use)

        gather_hazards = []
        gather_branches = []
        gather_number_files = []

        for haz in self.post_processing_config["logic_tree_meta"].keys():

            haz_prefix = self.post_processing_config["logic_tree_meta"][haz]["hazard_prefix"]

            if haz_prefix not in hazards:
                continue  # skip this hazard

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
                # "output_type" results
                target_output = "%s_by_building_id.csv" % (output_type)

                matching_files = [
                    f for f in matching_files
                    if target_output.lower() in f.lower()
                ]

                logger.info("            Found %s files" % (len(matching_files)))

                gather_hazards.append(haz_prefix)
                gather_branches.append(branch)
                gather_number_files.append(len(matching_files))

                if len(matching_files) < 1:  # No files found
                    logger.info("                No stats to be produced")
                    break

                all_data = None
                last_building_id_list = None
                weights = np.zeros(len(matching_files))

                for k, filename in enumerate(matching_files):
                    # Retrieve results of this realisation
                    df = pd.read_csv(
                        os.path.join(self.general_output_path, filename),
                        index_col=0
                    )

                    if all_data is None: # create data structure for the first time
                        all_data = np.zeros(
                            (
                                df.shape[0],  # reason why we cannot create this outside
                                len(columns_to_use),
                                len(matching_files)
                            )
                        )

                    # Check if all "columns_to_use" exist in df (they may not if, for example,
                    # some damage states did not occur for this exposure/intensity)
                    columns_exist = columns_to_use_as_index.isin(df.columns)
                    if not columns_exist.all():
                        missing_columns = columns_to_use_as_index[~columns_exist]
                        for col_name in missing_columns:
                            df[col_name] = np.zeros(df.shape[0])

                    all_data[:, :, k] = df[columns_to_use].to_numpy()

                    # Make sure building_ids are in the same order in all files (they should be)
                    building_ids = df.index.astype(str).to_list()  # current list of building_ids
                    if last_building_id_list is not None:
                        # Compare the last building_id list with the current one
                        the_same = (building_ids == last_building_id_list)  # boolean
                        if not the_same:
                            error_message = (
                                "The order of the building_ids is not the same in different "
                                "result files. The method "
                                "'calculate_stats_by_building_id_per_branch' cannot run"
                            )
                            logger.critical(error_message)
                            raise ValueError(error_message)

                    last_building_id_list = deepcopy(building_ids)

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

                if self.post_processing_config["export_weight_per_file"]:
                    weights_df = pd.DataFrame(
                        {
                            "weights_raw": weights,
                            "weights_final": normalised_weights
                        },
                        index=matching_files
                    )
                    weights_df.to_csv(
                        os.path.join(
                            self.general_output_path, "statistics",
                            "%s_by_building_id_by_branch_stats_weights_%s.csv" % (
                                output_type, filename_stem
                            )
                        ),
                        index=True
                    )

                weighted_means = np.average(
                    all_data, axis=2, weights=normalised_weights
                )
                weighted_means_df = pd.DataFrame(
                    weighted_means,
                    columns=columns_to_use,
                    index=last_building_id_list
                )
                weighted_means_df.to_csv(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "%s_by_building_id_by_branch_means_%s.csv" % (
                            output_type, filename_stem
                        )
                    ),
                    index=True
                )

                stats_with_geoms = exposure_geoms.join(weighted_means_df)

                weighted_st_dev_df = pd.DataFrame(
                    weighted_sample_unbiased_stdev_3D(
                        all_data, normalised_weights, weighted_means
                    ),
                    columns=columns_to_use,
                    index=last_building_id_list
                )
                weighted_st_dev_df.to_csv(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "%s_by_building_id_by_branch_stdev_%s.csv" % (
                            output_type, filename_stem
                        )
                    ),
                    index=True
                )

                stats_with_geoms = stats_with_geoms.join(
                    weighted_st_dev_df, lsuffix="_mean", rsuffix="_stdev"
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
                        index=last_building_id_list
                    )
                    quantile_df.to_csv(
                        os.path.join(
                            self.general_output_path, "statistics",
                            "%s_by_building_id_by_branch_q_%s_%s.csv" % (
                                output_type, quantile_str, filename_stem
                            )
                        ),
                        index=True
                    )

                    stats_with_geoms = stats_with_geoms.join(
                        quantile_df, rsuffix="_q_%s" % (quantile_str)
                    )

                    if q == 0:
                        # Manually add statistic's name
                        renaming_dict = {}
                        for col in columns_to_use:
                            renaming_dict[col] = "%s_q_%s" % (col, quantile_str)
                        stats_with_geoms.rename(
                            columns=renaming_dict,
                            inplace=True
                        )

                stats_with_geoms.to_file(
                    os.path.join(
                        self.general_output_path, "statistics",
                        "%s_by_building_id_by_branch_stats_%s.gpkg" % (
                            output_type, filename_stem
                        )
                    ),
                    driver="GPKG"
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
                "%s_by_building_id_by_branch_meta_summary.csv" % (output_type)
            ),
            index=False
        )

        return summary_number_files


    def calculate_stats_by_building_id_total(
        self, output_type, columns_to_use, exposure_geoms
    ):
        r"""
        This method calculates weighted means, weighted standard deviations and weighted
        quantiles of the columns in 'columns_to_use' of 'output_type', for the whole set of
        results available in 'self.general_output_path', assumed to correspond to all branches
        and realisations of 'self.post_processing_config["logic_tree_meta"]'.

        Resulting statistics are exported to `self.general_output_path`\statistics with
        filenames following the pattern
        "OUTPUTTYPE_by_building_id_total_STATNAME.csv", where:
        - OUTPUTTYPE: output_type (e.g., "loss", "damage_with_people").
        - STATNAME: name of the statistics (means, stdev, ...)

        All resulting statistics, combined with the exposure geometries in 'exposure_geoms', are
        exported to a GeoPackage file as well. The filename follows the pattern:
        "OUTPUTTYPE_by_building_id_total_stats.gpkg".

        If self.post_processing_config["export_weight_per_file"] is True, a CSV file containing
        the list of results files and weights used for the statistics is created.

        Args:
            output_type (str):
                Type of output to calculate statistics from. E.g.: "loss", "damage_with_people".
            columns_to_use (list of str):
                List of names of columns of the output file (of 'output_type') to be used for
                the statistics.
            exposure_geoms (GeoPandas GeoDataFrame):
                GeoDataFrame with the geometries of the exposure polygons. The indices are the
                exposure "building_id"s.

        Returns:
            summary_number_files (Pandas DataFrame):
                DataFrame summarising the number of files that were found and used to calculate
                the statistics of each branch of each hazard. Columns:
                    "hazard": Name (prefix) of the hazard.
                    "branch": Name of the branch,
                    "number_files": Number of files.
        """
        logger.info("Calculating total %s stats per building_id" % (output_type))

        columns_to_use_as_index = pd.Index(columns_to_use)

        # Initialise list to collect all data:
        all_data_slices = []  # each element will be a 2D array

        # Initialise "weights" to collect weights, same dimension as "depth" of "all_data"
        weights = []

        target_output = "%s_by_building_id.csv" % (output_type)
        matching_files = [
            f for f in os.listdir(self.general_output_path)
            if target_output.lower() in f.lower()
        ]

        summary_number_files = pd.DataFrame(
            {
                "hazard": ["all"],
                "branch": ["all"],
                "number_files": [len(matching_files)]
            }
        )
        summary_number_files.to_csv(
            os.path.join(
                self.general_output_path,
                "statistics",
                "%s_by_building_id_total_meta_summary.csv" % (output_type)
            ),
            index=False
        )

        logger.info("    Found %s files" % (len(matching_files)))

        if len(matching_files) < 1:  # No files found
            logger.info("        No stats to be produced")
            return summary_number_files

        # Start gathering the data
        all_data = None
        last_building_id_list = None
        weights = np.zeros(len(matching_files))

        for k, filename in enumerate(matching_files):
            # Retrieve results of this realisation
            df = pd.read_csv(
                os.path.join(self.general_output_path, filename),
                index_col=0
            )

            if all_data is None: # create data structure for the first time
                all_data = np.zeros(
                    (
                        df.shape[0],  # reason why we cannot create this outside
                        len(columns_to_use),
                        len(matching_files)
                    )
                )

            # Check if all "columns_to_use" exist in df (they may not if, for example, some
            # damage states did not occur for this exposure/intensity)
            columns_exist = columns_to_use_as_index.isin(df.columns)
            if not columns_exist.all():
                missing_columns = columns_to_use_as_index[~columns_exist]
                for col_name in missing_columns:
                    df[col_name] = np.zeros(df.shape[0])

            all_data[:, :, k] = df[columns_to_use].to_numpy()

            # Make sure building_ids are in the same order in all files (they should be)
            building_ids = df.index.astype(str).to_list()  # current list of building_ids
            if last_building_id_list is not None:
                # Compare the last building_id list with the current one
                the_same = (building_ids == last_building_id_list)  # boolean
                if not the_same:
                    error_message = (
                        "The order of the building_ids is not the same in different "
                        "result files. The method "
                        "'calculate_stats_by_building_id_total' cannot run"
                    )
                    logger.critical(error_message)
                    raise ValueError(error_message)

            last_building_id_list = deepcopy(building_ids)

            # Retrieve weight of this realisation
            haz_branch_realisation_info = (
                retrieve_hazard_branch_realisation_from_filename(filename)
            )
            filtered_weights = retrieve_weight(
                haz_branch_realisation_info, self.all_logic_tree_combination_weights
            )
            weights[k] = filtered_weights.loc[0, "weight_realisations"]

        normalised_weights = weights / weights.sum()

        if self.post_processing_config["export_weight_per_file"]:
            weights_df = pd.DataFrame(
                {
                    "weights_raw": weights,
                    "weights_final": normalised_weights
                },
                index=matching_files
            )
            weights_df.to_csv(
                os.path.join(
                    self.general_output_path, "statistics",
                    "%s_by_building_id_total_stats_weights.csv" % (output_type)
                ),
                index=True
            )

        logger.info("    A total of %s realisations were retrieved" % (all_data.shape[2]))

        weighted_means = np.average(
            all_data, axis=2, weights=normalised_weights
        )
        weighted_means_df = pd.DataFrame(
            weighted_means,
            columns=columns_to_use,
            index=last_building_id_list
        )
        weighted_means_df.to_csv(
            os.path.join(
                self.general_output_path, "statistics",
                "%s_by_building_id_total_means.csv" % (output_type)
            ),
            index=True
        )

        stats_with_geoms = exposure_geoms.join(weighted_means_df)

        weighted_st_dev_df = pd.DataFrame(
            weighted_sample_unbiased_stdev_3D(
                all_data, normalised_weights, weighted_means
            ),
            columns=columns_to_use,
            index=last_building_id_list
        )
        weighted_st_dev_df.to_csv(
            os.path.join(
                self.general_output_path, "statistics",
                "%s_by_building_id_total_stdev.csv" % (output_type)
            ),
            index=True
        )

        stats_with_geoms = stats_with_geoms.join(
            weighted_st_dev_df, lsuffix="_mean", rsuffix="_stdev"
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
                index=last_building_id_list
            )
            quantile_df.to_csv(
                os.path.join(
                    self.general_output_path, "statistics",
                    "%s_by_building_id_total_q_%s.csv" % (output_type, quantile_str)
                ),
                index=True
            )

            stats_with_geoms = stats_with_geoms.join(
                quantile_df, rsuffix="_q_%s" % (quantile_str)
            )

            if q == 0:
                # Manually add statistic's name
                renaming_dict = {}
                for col in columns_to_use:
                    renaming_dict[col] = "%s_q_%s" % (col, quantile_str)
                stats_with_geoms.rename(
                    columns=renaming_dict,
                    inplace=True
                )

        stats_with_geoms.to_file(
            os.path.join(
                self.general_output_path, "statistics",
                "%s_by_building_id_total_stats.gpkg" % (output_type)
            ),
            driver="GPKG"
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
                "weight_of_realisation" (0 < float <= 1):
                    Weight of one realisation of this hazard, independently of the
                    branch weight.

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
        all_logic_tree_combination_weights["weight_realisations"] = (
            all_logic_tree_combination_weights["weight_realisations"]
            * logic_tree_meta[haz]["weight_of_realisation"]
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
