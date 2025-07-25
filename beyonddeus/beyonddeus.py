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
import numpy as np
import pandas as pd

from beyonddeus.configuration import Configuration
from beyonddeus.shakemap import Shakemaps
from beyonddeus.fragility import Fragility
from beyonddeus.schemamapping import SchemaMapper
from beyonddeus.exposure import (
    read_exposure, map_exposure, update_exposure_transitions_and_losses
)
from beyonddeus.loss import LossProvider

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


def main():

    # Log the start of the run
    logger.info("Beyond-DEUS has started")

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

    # Read intensity files
    intensity_filenames = os.listdir(config.input_paths["intensity"])
    number_intensity_reals = len(intensity_filenames)
    logger.info("Reading input intensity files: %s files found" % (number_intensity_reals))
    intensity_provider = {}
    
    for i, filename in enumerate(intensity_filenames):
        intensity_provider[i] = Shakemaps.from_file(
            os.path.join(config.input_paths["intensity"], filename)
        ).to_intensity_provider()

    # Read fragility file
    logger.info("Reading input fragility file")

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
    logger.info("Reading input compatibility matrices")
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

    # Read exposure
    logger.info("Reading input initial exposure model")
    initial_exposure_df, exposure_geoms = read_exposure(
        config.input_paths["exposure_csv"], config.input_paths["exposure_gpkg"]
    )

    # Map exposure from source to target schemas
    logger.info("Mapping input initial exposure model onto target schema")
    mapped_exposure = map_exposure(
        initial_exposure_df,
        config.parameters["building_schema_exposure"],
        config.parameters["building_schema_fragility"],
        schema_mapper,
    )

    # Read economic consequence model and building replacement costs
    logger.info("Reading input economic consequence model")
    loss_provider = LossProvider.from_files(config.input_paths["consequence"])

    # Retrieve location (nearest neighbour position) of hazard intensity measures at the
    # centroids indicated in the input exposure geometries
    logger.info("Determining nearest-neighbour hazard positions for all exposure sites")
    target_locations = np.array(
        [exposure_geoms["centroid_lon"], exposure_geoms["centroid_lat"]]
    ).T
    nearest_neighbours = intensity_provider[0].identify_nearest_neighbours(target_locations)
    intensity_positions = pd.DataFrame(
        {"nearest_neighbour": nearest_neighbours},
        index=exposure_geoms["building_id"]
    )

    # Calculate damage and economic losses
    logger.info("Calculating damage and economic losses for each realisation of intensity")
    for i, filename in enumerate(intensity_filenames):
        logger.info(
            "   Working on intensity realisation %s of %s" % (i+1, number_intensity_reals)
        )
        updated_exposure = update_exposure_transitions_and_losses(
            mapped_exposure,
            intensity_provider[i],
            intensity_positions,
            fragility_provider,
            loss_provider,
        )

        logger.info("      Exporting results")
        out_filename = "%s_updated_exposure.csv" % (os.path.splitext(filename)[0])
        updated_exposure.to_csv(os.path.join(config.output_path, out_filename), index=False)



if __name__ == "__main__":
    main()
