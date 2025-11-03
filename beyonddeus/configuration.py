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

import sys
import logging
import yaml

logger = logging.getLogger()


class Configuration:
    """This class handles the configuration parameters.

    Attributes:
        self.hazard_prefix (str):
            Short string to be used as a prefix in the naming of output files.
        self.input_paths (dict):
            Dictionary with full paths to input files. Keys:
                "intensity":
                    Path to directory containing intensity input file(s).
                "fragility":
                    Path to fragility input file.
                "exposure_csv":
                    Path to the directory containing the exposure CSV input file(s).
                "exposure_gpkg":
                    Path to exposure GeoPackage input file.
                "conversion_taxonomy":
                    Path to directory containing conversion file(s) of building taxonomies.
                "conversion_damage_states":
                    Path to directory containing conversion file(s) of damage states.
                "consequence":
                    Path to file with input economic consequence model (loss ratios per damage
                    state).
                "usability":
                    Path to file indicating if buildings in each damage state are usable or
                    unusable.
        self.output_path (str):
            Path to directory where outputs will be written. It must be empty. If it does not
            exist, it will be created.
        self.output_path_profiling (str):
            Path to directory where outputs of profiling.py will be written, if manually run.
        self.running_mode (str):
            Mode in which the software runs. Currently supported options:
                - "processing": The software will calculate damage/losses only, without
                    outputting statistics.
                - "post-processing": The software will only calculate statistics of
                    previously-run calculations.
                - "both": The software will calculate damage/losses as well as the statistics of
                    the current calculation.
        self.parallelisation_mode (str):
            Parallelisation mode. Currently supported options are "by_input_exposure" (each CPU
            will process all hazard intensity branches and realisations for one individual input
            exposure model) and "by_intensity_realisation" (each CPU will process one especific
            combination of a realisation of hazard intensity and input exposure model).
        self.cpus (int):
            Number of processors to be used in the parallelisation of the calculations.
        self.parameters (dict):
            Dictionary with parameters for the calculations. Keys:
                "building_schema_exposure":
                    Name of the building classification schema of the input exposure.
                "building_schema_fragility":
                    Name of the building classification schema of the output, i.e. of the
                    input fragility and consequence models.
                "intensity_file_type":
                    Type of intensity input files. Supported values: xml, hdf5, netcdf_tsu,
                    netcdf_temp.
                "intensity_threshold":
                    Threshold of hazard intensity, to be used so that if the intensity value
                    at a target point is smaller than the threshold, no further damage is
                    assumed (and the detailed calculation is avoided).
        self.output_types (dict):
            Dictionary indicating the kind of outputs to export, by means of True/False. Options
            are sets of nested keys:
                "compress_exposure_csvs":
                    Boolean. If True, the CSVs containing updated exposures will be compressed
                    into zstd format.
                "mapped_exposure":
                    "csv": The input exposure model, mapped onto the target building and damage
                    schemas (i.e., conversion of building classes and damage states due to
                    compatibility across schemas, not the action of the input hazard), is
                    written to a CSV file.
                "full_updated_exposure":
                    "csv": The full updated exposure model as a CSV file.
                    "csv_usable": One CSV file containing the usable assets of the full updated
                        exposure model.
                    "csv_unusable": One CSV file containing the unusable assets of the full
                        updated exposure model.
                    "hdf5_per_realisation": The full updated exposure model as one HDF5 file per
                        realisation of each logic tree branch.
                "by_final_damage":
                    "csv_per_realisation": Number of buildings, replacement cost and losses of
                        the whole portfolio, reported per final damage state, due to each
                        realisation of each logic tree branch.
                "by_initial_and_final_damage":
                    "csv_per_realisation: Number of buildings, replacement cost and losses of
                        the whole portfolio, reported per all combinations of initial and final
                        damage states, due to each realisation of each logic tree branch.
                "by_building_id":
                    "loss_csv_per_realisation": Losses per building_id of the exposed assets due
                        to each realisation of each logic tree branch.
                    "loss_gpkg_per_realisation": Same as "loss_csv_per_realisation", with the
                        associated exposure geometries.
                    "only_transitioned_loss_csv_per_realisation": Same as
                        'loss_csv_per_realisation', but keeping only the building_ids for which
                        at least one of the assets transitions damage state.
                    "only_transitioned_loss_gpkg_per_realisation": Same as
                        'loss_gpkg_per_realisation', but keeping only the building_ids for which
                        at least one of the assets transitions damage state.
                    "damage_csv_per_realisation": Number of buildings per final damage state due
                        to each realisation of each logic tree branch.
                    "damage_gpkg_per_realisation": Same as "damage_csv_per_realisation", with
                        the associated exposure geometries.
                    "only_transitioned_damage_csv_per_realisation": Same as
                        'damage_csv_per_realisation', but keeping only the building_ids for
                        which at least one of the assets transitions damage state.
                    "only_transitioned_damage_gpkg_per_realisation": Same as
                        'damage_gpkg_per_realisation', but keeping only the building_ids for
                        which at least one of the assets transitions damage state.
                    "damage_with_people_csv_per_realisation": Same as
                        'damage_csv_per_realisation', plus columns with number of census people
                        per damage state.
                    "damage_with_people_gpkg_per_realisation": Same as
                        'damage_gpkg_per_realisation', plus columns with number of census people
                        per damage state.
        self.post_processing (dict):
            Dictionary indicating the parameters and info necessary for the post-processing of
            damage/loss results and calculation of statistics. Sub-parameters include:
                "target_quantiles" (list of float):
                    List of quantiles in the range (0.0, 1.0) to be used for calculating
                    quantiles of results.
                "logic_tree_meta" (dict):
                    Dictionary describing the logic trees of all hazards in the chain run so
                    far. The sub-keys are integers >= 1, indicating the order in which the
                    hazards were applied (1 = first hazard, 2 = second hazard, ...). For each
                    hazard, the subkey is a dictionary with the following parameters:
                        "hazard_prefix" (str):
                            'self.hazard_prefix' as used in the associated software run.
                        "logic_tree_path" (str):
                            Full path to CSV file containing the logic tree associated with this
                            hazard (the file contains all names and weights of the logic tree
                            branches).
                        "realisations" (int > 0):
                            Number of realisations per logic tree branch.
                "initial_damage_range" (list of int):
                    List of integers designating the initial damage states (of the last hazard
                    run).
                "final_damage_range" (list of int):
                    List of integers designating the final damage states (of the last hazard
                    run).
                "types":
                    Dictionary indicating the kind of post-processing outputs to export, by
                    means of True/False. Options are sets of nested keys:
                        "by_final_damage_all": Mean, quantiles and standard deviation of number
                            of buildings, incremental loss and cumulative loss, per final damage
                            state, for all branches and realisations considered together, with
                            their weights.
                        "by_final_damage_per_branch": Mean, quantiles and standard deviation of
                            number of buildings, incremental loss and cumulative loss, per final
                            damage state, for each branch of each hazard run so far.
                        "by_initial_and_final_damage_all": Mean, quantiles and standard
                            deviation of number of buildings, incremental loss and cumulative
                            loss, per combination of initial-final damage states, for all
                            branches and realisations considered together, with their weights.
                        "by_initial_and_final_damage_per_branch": Mean, quantiles and standard
                            deviation of number of buildings, incremental loss and cumulative
                            loss, per combination of initial-final damage states, for each
                            branch of each hazard run so far.
                        "loss_by_building_id_per_branch": Mean, quantiles and standard deviation
                            of incremental loss (absolute and ratio) and cumulative loss
                            (absolute and ratio) per building_id, for each branch of each hazard
                            run so far.
                        "damage_by_building_id_per_branch": Mean, quantiles and standard deviation
                            of number and proportion of buildings per damage state, per
                            building_id and for each branch of each hazard run so far.
                        "damage_with_people_by_building_id_per_branch": Mean, quantiles and
                            standard deviation of number and proportion of buildings, and number
                            of census people per damage state, per building_id and for each
                            branch of each hazard run so far.
    """

    def __init__(self, filepath):
        """
        Args:
            filepath (str):
                Full file path to the .yml configuration file.
        """

        config = self._read_config_file(filepath)

        self.hazard_prefix = self._assign_parameter(
            config, "hazard_prefix"
        )

        self.input_paths = {}
        self.input_paths["intensity"] = self._assign_parameter(
            config["input_paths"], "intensity"
        )
        self.input_paths["fragility"] = self._assign_parameter(
            config["input_paths"], "fragility"
        )
        self.input_paths["exposure_csv"] = self._assign_parameter(
            config["input_paths"], "exposure_csv"
        )
        self.input_paths["exposure_gpkg"] = self._assign_parameter(
            config["input_paths"], "exposure_gpkg"
        )
        self.input_paths["conversion_taxonomy"] = self._assign_parameter(
            config["input_paths"], "conversion_taxonomy"
        )
        self.input_paths["conversion_damage_states"] = self._assign_parameter(
            config["input_paths"], "conversion_damage_states"
        )
        self.input_paths["consequence"] = self._assign_parameter(
            config["input_paths"], "consequence"
        )
        self.input_paths["usability"] = self._assign_parameter(
            config["input_paths"], "usability"
        )

        self.output_path = self._assign_parameter(
            config, "output_path"
        )

        self.output_path_profiling = self._assign_parameter(
            config, "output_path_profiling"
        )

        self.running_mode = self._assign_parameter(
            config, "running_mode"
        )

        self.parallelisation_mode = self._assign_parameter(
            config, "parallelisation_mode"
        )

        self.cpus = self._assign_parameter(
            config, "cpus"
        )

        self.parameters = {}
        self.parameters["building_schema_exposure"] = self._assign_parameter(
            config["parameters"], "building_schema_exposure"
        )
        self.parameters["building_schema_fragility"] = self._assign_parameter(
            config["parameters"], "building_schema_fragility"
        )
        self.parameters["intensity_file_type"] = self._assign_parameter(
            config["parameters"], "intensity_file_type"
        )
        self.parameters["intensity_threshold"] = self._assign_parameter(
            config["parameters"], "intensity_threshold"
        )

        self.output_types = {}

        self.output_types["compress_exposure_csvs"] = self._assign_parameter(
            config["output_types"], "compress_exposure_csvs"
        )

        self.output_types["mapped_exposure"] = {}
        self.output_types["mapped_exposure"]["csv"] = self._assign_parameter(
            config["output_types"]["mapped_exposure"], "csv"
        )

        self.output_types["full_updated_exposure"] = {}
        self.output_types["full_updated_exposure"]["csv"] = self._assign_parameter(
            config["output_types"]["full_updated_exposure"], "csv"
        )
        self.output_types["full_updated_exposure"]["csv_usable"] = self._assign_parameter(
            config["output_types"]["full_updated_exposure"], "csv_usable"
        )
        self.output_types["full_updated_exposure"]["csv_unusable"] = self._assign_parameter(
            config["output_types"]["full_updated_exposure"], "csv_unusable"
        )
        self.output_types["full_updated_exposure"]["hdf5_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["full_updated_exposure"], "hdf5_per_realisation"
            )
        )

        self.output_types["by_final_damage"] = {}
        self.output_types["by_final_damage"]["csv_per_realisation"] = self._assign_parameter(
            config["output_types"]["by_final_damage"], "csv_per_realisation"
        )

        self.output_types["by_initial_and_final_damage"] = {}
        self.output_types["by_initial_and_final_damage"]["csv_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_initial_and_final_damage"], "csv_per_realisation"
            )
        )

        self.output_types["by_building_id"] = {}
        self.output_types["by_building_id"]["loss_csv_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"], "loss_csv_per_realisation"
            )
        )
        self.output_types["by_building_id"]["loss_gpkg_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"], "loss_gpkg_per_realisation"
            )
        )
        self.output_types["by_building_id"]["only_transitioned_loss_csv_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"],
                "only_transitioned_loss_csv_per_realisation"
            )
        )
        self.output_types["by_building_id"]["only_transitioned_loss_gpkg_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"],
                "only_transitioned_loss_gpkg_per_realisation"
            )
        )
        self.output_types["by_building_id"]["damage_csv_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"], "damage_csv_per_realisation"
            )
        )
        self.output_types["by_building_id"]["damage_gpkg_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"], "damage_gpkg_per_realisation"
            )
        )
        self.output_types["by_building_id"]["only_transitioned_damage_csv_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"],
                "only_transitioned_damage_csv_per_realisation"
            )
        )
        self.output_types["by_building_id"]["only_transitioned_damage_gpkg_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"],
                "only_transitioned_damage_gpkg_per_realisation"
            )
        )
        self.output_types["by_building_id"]["damage_with_people_csv_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"],
                "damage_with_people_csv_per_realisation"
            )
        )
        self.output_types["by_building_id"]["damage_with_people_gpkg_per_realisation"] = (
            self._assign_parameter(
                config["output_types"]["by_building_id"],
                "damage_with_people_gpkg_per_realisation"
            )
        )

        aux_post_processing = self._assign_parameter(
            config, "post_processing"
        )
        if aux_post_processing == "None":
            self.post_processing = aux_post_processing
        else:
            self.post_processing = {}

            self.post_processing["target_quantiles"] = self._assign_listed_parameters(
                aux_post_processing, "target_quantiles"
            )
            for i in range(len(self.post_processing["target_quantiles"])):
                self.post_processing["target_quantiles"][i] = float(
                    self.post_processing["target_quantiles"][i]
                )

            self.post_processing["logic_tree_meta"] = self._assign_hierarchical_parameters(
                aux_post_processing, "logic_tree_meta"
            )

            self.post_processing["initial_damage_range"] = self._assign_listed_parameters(
                aux_post_processing, "initial_damage_range"
            )
            for i in range(len(self.post_processing["initial_damage_range"])):
                self.post_processing["initial_damage_range"][i] = int(
                    self.post_processing["initial_damage_range"][i]
                )
            for i in range(len(self.post_processing["initial_damage_range"])-1):
                if (
                    self.post_processing["initial_damage_range"][i]
                    > self.post_processing["initial_damage_range"][i+1]
                ):
                    error_message = (
                        "The damage states in 'initial_damage_range' need to be in ascending "
                        "order (e.g., [0, 1, ...], not [4, 3, ...], not [0, 4, 2, ...])"
                    )
                    logger.critical(error_message)
                    raise OSError(error_message)

            self.post_processing["final_damage_range"] = self._assign_listed_parameters(
                aux_post_processing, "final_damage_range"
            )
            for i in range(len(self.post_processing["final_damage_range"])):
                self.post_processing["final_damage_range"][i] = int(
                    self.post_processing["final_damage_range"][i]
                )
            for i in range(len(self.post_processing["final_damage_range"])-1):
                if (
                    self.post_processing["final_damage_range"][i]
                    > self.post_processing["final_damage_range"][i+1]
                ):
                    error_message = (
                        "The damage states in 'final_damage_range' need to be in ascending "
                        "order (e.g., [0, 1, ...], not [4, 3, ...], not [0, 4, 2, ...])"
                    )
                    logger.critical(error_message)
                    raise OSError(error_message)

            self.post_processing["types"] = self._assign_hierarchical_parameters(
                aux_post_processing, "types"
            )

        if (
            (self.running_mode in ("post-processing", "both"))
            and (self.post_processing == "None")
        ):
            error_message = (
                "Running mode %s requires that 'post_processing' parameters "
                "be indicated in config.yml. The program cannot run."
                % (self.running_mode)
            )
            logger.critical(error_message)
            raise OSError(error_message)

    def _read_config_file(self, filepath):
        """This function attempts to open the configuration file. If not found, it logs a
        critical error and raises an OSError.

        Args:
            filepath (str):
                Full file path to the .yml configuration file.

        Returns:
            config (dictionary):
                The configuration file read as a dictionary, or an empty dictionary if the
                configuration file was not found.
        """

        try:
            with open(filepath, "r") as ymlfile:
                config = yaml.load(ymlfile, Loader=yaml.FullLoader)
        except FileNotFoundError:
            config = {}
            error_message = "Error instantiating Configuration: configuration file not found"
            logger.critical(error_message)
            raise OSError(error_message)

        return config

    def _assign_parameter(self, config, input_parameter):
        """This function searches for the key input_parameter in the dictionary config. If
        found, it returns its value (a string or a dictionary). If not found, it returns None.

        Args:
            config (dictionary):
                The configuration file read as a dictionary. It may be an empty dictionary.
            input_parameter (str):
                Name of the desired parameter, to be searched for as a primary key of config.
        Returns:
            assigned_parameter (str, dictionary or None):
                The content of config[input_parameter], which can be a string or a dictionary.
                It is None if input_parameter is not a key of config.
        """

        try:
            assigned_parameter = config[input_parameter]
        except KeyError:
            logger.warning(
                "Warning: parameter '%s' is missing from configuration file" % (input_parameter)
            )
            assigned_parameter = None

        return assigned_parameter

    def _assign_listed_parameters(self, config, input_parameter):
        """This function searches for the key input_parameter in the dictionary config, and
        splits its assigned value as per ", ", i.e. a comma plus space separation.

        If input_parameter is not a key of config, the output is None.

        Args:
            config (dictionary):
                The configuration file read as a dictionary. It may be an empty dictionary.
            input_parameter (str):
                Name of the desired parameter, to be searched for as a primary key of config.

        Returns:
            assigned_parameter (list of str):
                Each element of the list is an element of config[input_parameter], separated as
                per a comma followed by a space (", "). E.g. if 'config[input_parameter]' is
                "Name_A, Name_B", 'assigned_parameter' is ["Name_A", "Name_B"].
        """

        assigned_parameter = self._assign_parameter(config, input_parameter)

        if assigned_parameter is None:
            return None

        assigned_parameter = assigned_parameter.split(", ")

        return assigned_parameter

    def _assign_hierarchical_parameters(self, config, input_parameter, requested_nested=[]):
        """This function searches for the key input_parameter in the dictionary config, and for
        each of the elements of requested_nested as keys of config[input_parameter].

        If input_parameter is not a key of config, the output is None.

        If input_parameter is a key of config, but one of the elements of requested_nested is
        not a key of config[input_parameter], the output is None.

        Args:
            config (dictionary):
                The configuration file read as a dictionary. It may be an empty dictionary.
            input_parameter (str):
                Name of the desired parameter, to be searched for as a primary key of config.
            requested_nested (list of str):
                List of the names of the desired nested parameters, to be searched for as keys
                of config[input_parameter]. If empty, the function will retrieve all nested
                parameters available in 'config'.

        Returns:
            assigned_parameter (dictionary or None):
                The content of config[input_parameter], if input_parameter is a key of config
                and all elements of requested_nested are keys of config[input_parameter], or
                None otherwise.
        """

        assigned_parameter = self._assign_parameter(config, input_parameter)

        if assigned_parameter is None:
            return None

        if not isinstance(assigned_parameter, dict):
            return None

        if len(requested_nested) == 0:
            requested_nested = list(assigned_parameter.keys())

        sub_parameters_missing = False
        for requested_parameter in requested_nested:
            if requested_parameter not in assigned_parameter.keys():
                logger.critical(
                    "ERROR instantiating Configuration: parameter '%s' does not "
                    "exist in %s" % (requested_parameter, input_parameter)
                )
                sub_parameters_missing = True

        if sub_parameters_missing is True:
            return None

        return assigned_parameter
