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
import sys
import logging
import datetime
import numpy as np
import pandas as pd

from beyonddeus.configuration import Configuration
from beyonddeus.intensity_reader import read_intensity_files
from beyonddeus.fragility import Fragility
from beyonddeus.schemamapping import SchemaMapper
from beyonddeus.exposure import (
    retrieve_exposure_input_names, read_exposure_geoms, read_exposure_csv,
    check_all_building_ids_in_geoms, map_exposure,
    update_exposure_transitions_and_losses
)
from beyonddeus.loss import LossProvider
from beyonddeus.usability import Usability
from beyonddeus.output_generator import OutputGenerator

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


def main():

    # Log the start of the run
    now = datetime.datetime.now()
    logger.info(
        "%s: Beyond-DEUS has started"
        % (format_time(now))
    )

    # Read configuration parameters
    config = Configuration("config.yml")

    if not os.path.exists(config.output_path):
        # Create output directory if it does not exist yet
        os.mkdir(config.output_path)

    # Check if output directory is empty (it needs to be)
    if not len(os.listdir(config.output_path)) == 0:
        error_message = (
            "The directory '%s' is not empty but should be. The program will stop."
            % (config.output_path)
        )
        logger.critical(error_message)
        raise OSError(error_message)

    # Create sub-directories to store updated exposure models
    os.mkdir(os.path.join(config.output_path, "updated_exposure_csv"))
    os.mkdir(os.path.join(config.output_path, "updated_exposure_usable_csv"))
    os.mkdir(os.path.join(config.output_path, "updated_exposure_unusable_csv"))
    os.mkdir(os.path.join(config.output_path, "mapped_exposure_csv"))

    # Read intensity files
    now = datetime.datetime.now()
    logger.info("%s: Reading input intensity file(s)" % (format_time(now)))
    intensity_provider = read_intensity_files(
        config.input_paths["intensity"],
        config.parameters["intensity_file_type"]
    )

    if len(intensity_provider.keys()) == 0:
        logger.info(
            "No intensity files found. Check if 'intensity_file_type' "
            "in 'config.yml' is supported."
        )
        return

    # Read fragility file
    now = datetime.datetime.now()
    logger.info("%s: Reading input fragility file" % (format_time(now)))

    fragility_provider = Fragility.from_file(
       config.input_paths["fragility"]
    ).to_fragility_provider()
    logger.info(
        "    %s building classes found"
        % (len(fragility_provider.get_taxonomies()))
    )

    if fragility_provider.schema != config.parameters["building_schema_fragility"]:
        error_message = (
            "The name of the target building classification schema, that is, the schema of the "
            "fragility model, as stated in the fragility input file, is different from the "
            "name stated in the config.yml file. Please check and adjust. The current names "
            "are %s and %s."
            % (fragility_provider.schema, config.parameters["building_schema_fragility"])
        )
        raise ValueError(error_message)

    # Read taxonomy and damage states compatibility matrices
    now = datetime.datetime.now()
    logger.info("%s: Reading input compatibility matrices" % (format_time(now)))
    if (
        config.input_paths["conversion_taxonomy"] == "None"
        and config.input_paths["conversion_damage_states"] == "None"
    ):
        schema_mapper = SchemaMapper(None, None)
    else:
        schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
            config.input_paths["conversion_taxonomy"],
            config.input_paths["conversion_damage_states"]
        )

    # Read exposure input names and geometries
    now = datetime.datetime.now()
    logger.info(
        "%s: Retrieving name(s) of input initial exposure model(s)" % (format_time(now))
    )
    exposure_input_names = retrieve_exposure_input_names(config.input_paths["exposure_csv"])

    now = datetime.datetime.now()
    logger.info("%s: Reading exposure geometries" % (format_time(now)))
    exposure_geoms = read_exposure_geoms(config.input_paths["exposure_gpkg"])

    # Read economic consequence model
    now = datetime.datetime.now()
    logger.info("%s: Reading input economic consequence model" % (format_time(now)))
    loss_provider = LossProvider.from_files(config.input_paths["consequence"])

    # Read usability model
    now = datetime.datetime.now()
    logger.info("%s: Reading input usability model" % (format_time(now)))
    usability_model = Usability(config.input_paths["usability"])

    if (
        (usability_model.data is None) and
        (config.output_types["full_updated_exposure"]["csv_by_usability"])
    ):
        error_message = (
            "The parameter 'csv_by_usability' in the config.yml file is True but "
            "no usability model has been loaded. Have you indicated 'input_paths[usability]'?"
        )
        logger.critical(error_message)
        raise OSError(error_message)

    # Retrieve location (nearest neighbour position) of hazard intensity measures at the
    # centroids indicated in the input exposure geometries
    now = datetime.datetime.now()
    logger.info(
        "%s: Determining nearest-neighbour hazard positions for all exposure sites"
        % (format_time(now))
    )
    target_locations = np.array(
        [exposure_geoms["centroid_lon"], exposure_geoms["centroid_lat"]]
    ).T
    first_branch = list(intensity_provider.keys())[0]
    nearest_neighbours = intensity_provider[first_branch][0].identify_nearest_neighbours(
        target_locations
    )
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": nearest_neighbours},
        index=exposure_geoms["building_id"]
    )

    # Calculate damage and economic losses
    now = datetime.datetime.now()
    logger.info(
        "%s: Calculating damage and economic losses for "
        "each realisation of intensity and input exposure model"
        % (format_time(now))
    )

    number_branches = len(intensity_provider.keys())

    for p, initial_exposure_name_raw in enumerate(exposure_input_names):
        initial_exposure_name = initial_exposure_name_raw.split("_updated")[0]

        # Read exposure CSV
        now = datetime.datetime.now()
        logger.info(
            "   %s: Reading input initial exposure model '%s'"
            % (format_time(now), initial_exposure_name_raw)
        )
        initial_exposure_df = read_exposure_csv(
            os.path.join(
                config.input_paths["exposure_csv"], "%s.csv" % (initial_exposure_name_raw)
            )
        )

        # Make sure all building_ids have geometries
        now = datetime.datetime.now()
        logger.info(
            "   %s: Checking all building_ids have associated geometries"
            % (format_time(now))
        )
        check_all_building_ids_in_geoms(initial_exposure_df, exposure_geoms)

        # Map exposure from source to target schemas
        now = datetime.datetime.now()
        logger.info(
            "   %s: Mapping input initial exposure model onto target schema"
            % (format_time(now))
        )
        mapped_exposure = map_exposure(
            initial_exposure_df,
            config.parameters["building_schema_exposure"],
            config.parameters["building_schema_fragility"],
            schema_mapper,
        )

        if (
            config.output_types["mapped_exposure"]["csv"] and (
                config.parameters["building_schema_exposure"] !=
                config.parameters["building_schema_fragility"])
        ):
            now = datetime.datetime.now()
            logger.info(
                "   %s: Exporting input initial exposure model mapped onto target schema"
                % (format_time(now))
            )
            mapped_exposure.to_csv(
                os.path.join(
                    config.output_path,
                    "mapped_exposure_csv",
                    "%s_%s_mapped_exposure.csv" % (config.hazard_prefix, initial_exposure_name)
                ),
                index=False
            )

        for l, branch in enumerate(intensity_provider.keys()):
            now = datetime.datetime.now()
            logger.info(
                "      %s: Working on logic tree branch '%s' (%s of %s)"
                % (format_time(now), branch, l+1, number_branches)
            )

            number_intensity_reals = len(intensity_provider[branch].keys())

            for k, realisation in enumerate(intensity_provider[branch]):
                now = datetime.datetime.now()
                logger.info(
                    "         %s: Working on intensity realisation %s of %s"
                    % (format_time(now), k+1, number_intensity_reals)
                )

                all_intensities_lk = (
                    intensity_provider[branch][k].get_values_at_multiple_positions(
                        intensity_positions, config.parameters["intensity_threshold"]
                    )
                )
                logger.info(
                    "                              %s out of %s building_id "
                    "assumed with no further damage (intensity < threshold)"
                    % (
                        all_intensities_lk.shape[0] - all_intensities_lk["run"].sum(),
                        all_intensities_lk.shape[0]
                    )
                )

                updated_exposure = update_exposure_transitions_and_losses(
                    mapped_exposure,
                    all_intensities_lk,
                    config.parameters["intensity_threshold"],
                    fragility_provider,
                    loss_provider,
                )

                now = datetime.datetime.now()
                logger.info(
                    "                              %s: Exporting results" % (format_time(now))
                )

                outputgen = OutputGenerator(
                    config.hazard_prefix,
                    initial_exposure_name,
                    config.output_path,
                    config.output_types,
                    usability_model.data,
                    branch,
                    str(realisation),
                    updated_exposure,
                    exposure_geoms
                )
                outputgen.export()

    now = datetime.datetime.now()
    logger.info(
        "%s: Beyond-DEUS has finished"
        % (format_time(now))
    )


def format_time(timeval):
    formatted_time = "%s-%s-%s %s:%s:%s" % (
        str(timeval.year),
        str(timeval.month).zfill(2),
        str(timeval.day).zfill(2),
        str(timeval.hour).zfill(2),
        str(timeval.minute).zfill(2),
        str(timeval.second).zfill(2),
    )
    return formatted_time


if __name__ == "__main__":
    main()
