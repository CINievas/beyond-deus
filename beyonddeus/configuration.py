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
        self.input_paths (dict):
            Dictionary with full paths to input files. Keys:
                "intensity":
                    Path to directory containing intensity input file(s).
                "fragility":
                    Path to fragility input file.
                "exposure_csv":
                    Path to exposure CSV input file.
                "exposure_gpkg":
                    Path to exposure GeoPackage input file.
                "conversion_taxonomy":
                    Path to directory containing conversion file(s) of building taxonomies.
                "conversion_damage_states":
                    Path to directory containing conversion file(s) of damage states.
                "consequence":
                    Path to file with input economic consequence model (loss ratios per damage
                    state).
        self.output_path (str):
            Path to directory where outputs will be written. It must be empty. If it does not
            exist, it will be created.
        self.output_path_profiling (str):
            Path to directory where outputs of profiling.py will be written, if manually run.
        self.parameters (dict):
            Dictionary with parameters for the calculations. Keys:
                "building_schema_exposure":
                    Name of the building classification schema of the input exposure.
                "building_schema_fragility":
                    Name of the building classification schema of the output, i.e. of the
                    input fragility and consequence models.
                "intensity_file_type":
                    Type of intensity input files. Supported values: xml, hdf5, netcdf_tsu.
                "intensity_threshold":
                    Threshold of hazard intensity, to be used so that if the intensity value
                    at a target point is smaller than the threshold, no further damage is
                    assumed (and the detailed calculation is avoided).
    """

    def __init__(self, filepath):
        """
        Args:
            filepath (str):
                Full file path to the .yml configuration file.
        """

        config = self._read_config_file(filepath)

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

        self.output_path = self._assign_parameter(
            config, "output_path"
        )

        self.output_path_profiling = self._assign_parameter(
            config, "output_path_profiling"
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
