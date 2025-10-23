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
import time
import logging
import numpy as np
import pandas as pd
from multiprocessing import Pool, Queue
from logging.handlers import QueueHandler, QueueListener
from functools import partial

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
from beyonddeus.post_processor import PostProcessor

# Worker functions use globals pickled at Pool startup
_config = None
_fragility_provider = None
_schema_mapper = None
_loss_provider = None
_usability_model = None
_exposure_geoms = None


def init_worker_for_by_exposure(log_queue):
    """
    Pool initializer: configure a QueueHandler and load shared data (configuration and
    providers) once per worker.

    Args:
        log_queue (Queue):
            Instance of Queue to handle the logging from multiple workers.
    """
    # Attach a QueueHandler so worker logs go to the main listener
    qh = QueueHandler(log_queue)
    root = logging.getLogger()
    root.handlers = []
    root.addHandler(qh)
    root.setLevel(logging.INFO)

    global _config, _fragility_provider, _schema_mapper, _exposure_geoms
    global _loss_provider, _usability_model

    # Read configuration
    _config = Configuration("config.yml")

    # Read intensity files
    logging.getLogger(__name__).info("Initialising worker: Reading input intensity file(s)")

    # Read fragility file
    logging.getLogger(__name__).info("Initialising worker: Reading input fragility file")

    _fragility_provider = Fragility.from_file(
       _config.input_paths["fragility"]
    ).to_fragility_provider()
    logging.getLogger(__name__).info(
        "    %s building classes found"
        % (len(_fragility_provider.get_taxonomies()))
    )

    if _fragility_provider.schema != _config.parameters["building_schema_fragility"]:
        error_message = (
            "The name of the target building classification schema, that is, the schema of the "
            "fragility model, as stated in the fragility input file, is different from the "
            "name stated in the config.yml file. Please check and adjust. The current names "
            "are %s and %s."
            % (_fragility_provider.schema, _config.parameters["building_schema_fragility"])
        )
        raise ValueError(error_message)

    # Read taxonomy and damage states compatibility matrices
    logging.getLogger(__name__).info(
        "Initialising worker: Reading input compatibility matrices"
    )
    if (
        _config.input_paths["conversion_taxonomy"] == "None"
        and _config.input_paths["conversion_damage_states"] == "None"
    ):
        _schema_mapper = SchemaMapper(None, None)
    else:
        _schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
            _config.input_paths["conversion_taxonomy"],
            _config.input_paths["conversion_damage_states"]
        )

    # Read exposure geometries
    logging.getLogger(__name__).info("Initialising worker: Reading exposure geometries")
    _exposure_geoms = read_exposure_geoms(_config.input_paths["exposure_gpkg"])

    # Read economic consequence model
    logging.getLogger(__name__).info(
        "Initialising worker: Reading input economic consequence model"
    )
    _loss_provider = LossProvider.from_files(_config.input_paths["consequence"])

    # Read usability model
    logging.getLogger(__name__).info("Initialising worker: Reading input usability model")
    _usability_model = Usability(_config.input_paths["usability"])

    if (
        (_usability_model.data is None) and
        (
            _config.output_types["full_updated_exposure"]["csv_usable"] or
            _config.output_types["full_updated_exposure"]["csv_unusable"]
        )
    ):
        error_message = (
            "The parameter(s) 'csv_usable' and/or 'csv_unusable' in the config.yml file is/are "
            "True but no usability model has been loaded. "
            "Have you indicated 'input_paths[usability]'?"
        )
        logging.getLogger(__name__).critical(error_message)
        raise OSError(error_message)

    logging.getLogger(__name__).info("Worker %s initialized" % (os.getpid()))


def init_worker_for_by_itensity_realisation(log_queue):
    """
    Pool initializer: configure a QueueHandler and load shared data (configuration and
    providers) once per worker.

    Args:
        log_queue (Queue):
            Instance of Queue to handle the logging from multiple workers.
    """
    # Attach a QueueHandler so worker logs go to the main listener
    qh = QueueHandler(log_queue)
    root = logging.getLogger()
    root.handlers = []
    root.addHandler(qh)
    root.setLevel(logging.INFO)

    global _config, _fragility_provider, _schema_mapper, _loss_provider, _usability_model
    global _exposure_geoms

    # Read configuration
    _config = Configuration("config.yml")

    # Read fragility file
    logging.getLogger(__name__).info("Initialising worker: Reading input fragility file")

    _fragility_provider = Fragility.from_file(
       _config.input_paths["fragility"]
    ).to_fragility_provider()
    logging.getLogger(__name__).info(
        "    %s building classes found"
        % (len(_fragility_provider.get_taxonomies()))
    )

    if _fragility_provider.schema != _config.parameters["building_schema_fragility"]:
        error_message = (
            "The name of the target building classification schema, that is, the schema of the "
            "fragility model, as stated in the fragility input file, is different from the "
            "name stated in the config.yml file. Please check and adjust. The current names "
            "are %s and %s."
            % (_fragility_provider.schema, _config.parameters["building_schema_fragility"])
        )
        raise ValueError(error_message)

    # Read exposure geometries
    logging.getLogger(__name__).info("Initialising worker: Reading exposure geometries")
    _exposure_geoms = read_exposure_geoms(_config.input_paths["exposure_gpkg"])

    # Read economic consequence model
    logging.getLogger(__name__).info(
        "Initialising worker: Reading input economic consequence model"
    )
    _loss_provider = LossProvider.from_files(_config.input_paths["consequence"])

    # Read usability model
    logging.getLogger(__name__).info("Initialising worker: Reading input usability model")
    _usability_model = Usability(_config.input_paths["usability"])

    if (
        (_usability_model.data is None) and
        (
            _config.output_types["full_updated_exposure"]["csv_usable"] or
            _config.output_types["full_updated_exposure"]["csv_unusable"]
        )
    ):
        error_message = (
            "The parameter(s) 'csv_usable' and/or 'csv_unusable' in the config.yml file is/are "
            "True but no usability model has been loaded. "
            "Have you indicated 'input_paths[usability]'?"
        )
        logging.getLogger(__name__).critical(error_message)
        raise OSError(error_message)

    logging.getLogger(__name__).info("Worker %s initialized" % (os.getpid()))


def read_check_and_map_exposure(
    initial_exposure_name_raw,
    configuration,
    exposure_geoms,
    schema_mapper
):
    """
    This method reads the exposure CSV file whose name is 'initial_exposure_name_raw',
    checks that all its building_ids have geometries in 'exposure_geoms', and maps it onto the
    target schema, as specified in 'configuration' and 'schema_mapper'. If specified in
    'configuration', it also exports the mapped exposure.

    It calls the methods 'read_exposure_csv', 'check_all_building_ids_in_geoms' and
    'map_exposure' from exposure.py.

    Returns:
        mapped_exposure (Pandas DataFrame)
        initial_exposure_name (str)
    """
    # Attach exposure context
    base_logger = logging.getLogger(__name__)
    logger = logging.LoggerAdapter(
        base_logger, {"exposure": initial_exposure_name_raw.split(".")[0]}
    )

    # Read exposure CSV
    initial_exposure_df = read_exposure_csv(
        os.path.join(
            configuration.input_paths["exposure_csv"], initial_exposure_name_raw
        )
    )

    initial_exposure_name = initial_exposure_name_raw.split(".")[0].split("_updated")[0]

    # Make sure all building_ids have geometries
    logger.info("Checking all building_ids have associated geometries")
    check_all_building_ids_in_geoms(initial_exposure_df, exposure_geoms)

    # Map exposure from source to target schemas
    logger.info("Mapping input initial exposure model onto target schema")
    mapped_exposure = map_exposure(
        initial_exposure_df,
        configuration.parameters["building_schema_exposure"],
        configuration.parameters["building_schema_fragility"],
        schema_mapper,
    )

    if (
        configuration.output_types["mapped_exposure"]["csv"] and (
            configuration.parameters["building_schema_exposure"] !=
            configuration.parameters["building_schema_fragility"])
    ):
        logger.info("Exporting input initial exposure model mapped onto target schema")

        if configuration.output_types["compress_exposure_csvs"]:
            mapped_exposure.to_csv(
                os.path.join(
                    configuration.output_path,
                    "mapped_exposure_csv",
                    "%s_%s_mapped_exposure.zstd"
                    % (configuration.hazard_prefix, initial_exposure_name)
                ),
                compression="zstd",
                index=False
            )
        else:
            mapped_exposure.to_csv(
                os.path.join(
                    configuration.output_path,
                    "mapped_exposure_csv",
                    "%s_%s_mapped_exposure.csv"
                    % (configuration.hazard_prefix, initial_exposure_name)
                ),
                index=False
            )

    return mapped_exposure, initial_exposure_name


def process_by_exposure(all_intensity_values, initial_exposure_name_raw):
    """
    Run all intensity branches and realisations for one input exposure model.

    Args:
        all_intensity_values (dict of Pandas DataFrame):
            Dictionary whose first-level keys are the names of the branches of the intensity
            logic tree, and whose second-level keys are the realisations of intensities within
            each branch. The Pandas DataFrames contained by these keys are the output of
            IntensityProvider.get_values_at_multiple_positions().
        initial_exposure_name_raw (str):
            Name of the input exposure CSV file to process.
    """

    # Attach exposure context
    base_logger = logging.getLogger(__name__)
    logger = logging.LoggerAdapter(
        base_logger, {"exposure": initial_exposure_name_raw.split(".")[0]}
    )
    logger.info("START processing")

    logger.info("Loading exposure model")
    mapped_exposure, initial_exposure_name = read_check_and_map_exposure(
        initial_exposure_name_raw,
        _config,
        _exposure_geoms,
        _schema_mapper
    )

    number_branches = len(all_intensity_values)

    for l, branch in enumerate(all_intensity_values):

        number_intensity_reals = len(all_intensity_values[branch].keys())

        for k, realisation in enumerate(all_intensity_values[branch]):

            # Logger
            ctx = {"branch": branch, "realisation": realisation}
            step_logger = logging.LoggerAdapter(
                base_logger, {"exposure": initial_exposure_name_raw.split(".")[0], **ctx}
            )
            step_logger.info(
                "Calculating damage and losses, branch %s/%s, realisation %s/%s"
                % (l+1, number_branches, k+1, number_intensity_reals)
            )

            updated_exposure = update_exposure_transitions_and_losses(
                mapped_exposure,
                all_intensity_values[branch][realisation],
                _config.parameters["intensity_threshold"],
                _fragility_provider,
                _loss_provider
            )

            step_logger.info("Exporting results")
            outputgen = OutputGenerator(
                _config.hazard_prefix,
                initial_exposure_name,
                _config.output_path,
                _config.output_types,
                _usability_model.data,
                branch,
                str(realisation),
                updated_exposure,
                _exposure_geoms
            )
            outputgen.export()
            step_logger.info("Results exported")

    logger.info("END processing")


def process_by_intensity_realisation(task: tuple):
    """
    Process a single (exposure, branch, realisation) task.

    Args:
        task (tuple):
            Tuple of (
                    initial_exposure_name_raw,
                    mapped_exposure,
                    branch,
                    realisation,
                    intensity_provider_branch_real,
                    intensity_positions
                    ):
                initial_exposure_name_raw (str)
                mapped_exposure (Pandas DataFrame)
                branch (str):
                    Name of the branch of the intensity logic tree.
                realisation (int):
                    Number of the realisation of intensity within 'branch'.
                intensity_provider_branch_real (intensityprovider.IntensityProvider):
                    Instance of intensityprovider.IntensityProvider for this 'branch' and
                    'realisation'.
                intensity_positions (Pandas DataFrame):
                    DataFrame with index "building_id", indicating the ID of exposure polygons,
                    and one column "nearest_neighbour", with the position of the nearest
                    neighbour site of the hazard intensitiy fields.
    """
    (
        initial_exposure_name_raw,
        mapped_exposure,
        branch,
        realisation,
        intensity_provider_branch_real,
        intensity_positions
    ) = task

    # Attach exposure, branch and realisation context
    base_logger = logging.getLogger(__name__)
    logger = logging.LoggerAdapter(base_logger, {
        "exposure": initial_exposure_name_raw.split(".")[0],
        "branch": branch,
        "realisation": realisation
    })

    logger.info("START processing")

    initial_exposure_name = initial_exposure_name_raw.split(".")[0].split("_updated")[0]

    all_intensities = intensity_provider_branch_real.get_values_at_multiple_positions(
        intensity_positions,
        _config.parameters["intensity_threshold"]
    )

    logger.info(
        "%s out of %s building_id "
        "assumed with no further damage (intensity < threshold)"
        % (
            all_intensities.shape[0] - all_intensities["run"].sum(),
            all_intensities.shape[0]
        )
    )

    updated_exposure = update_exposure_transitions_and_losses(
        mapped_exposure,
        all_intensities,
        _config.parameters["intensity_threshold"],
        _fragility_provider,
        _loss_provider
    )

    logger.info("Exporting results")
    outputgen = OutputGenerator(
        _config.hazard_prefix,
        initial_exposure_name,
        _config.output_path,
        _config.output_types,
        _usability_model.data,
        branch,
        str(realisation),
        updated_exposure,
        _exposure_geoms
    )
    outputgen.export()
    logger.info("Results exported")

    logger.info("END processing")


def main():
    # Main logger & listener
    log_queue = Queue()
    fmt = (
        "%(asctime)s %(processName)s "
        "[exp=%(exposure)s branch=%(branch)s real=%(realisation)s] "
        "%(message)s" #"%(levelname)s %(message)s"
    )
    datefmt = "%Y-%m-%d %H:%M:%S"  # date format with no fractional seconds
    handler = logging.StreamHandler()
    handler.setFormatter(SafeFormatter(fmt, datefmt=datefmt))
    listener = QueueListener(log_queue, handler)
    listener.start()

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = []
    root.addHandler(QueueHandler(log_queue))

    # Silence/raise level for noisy third-party loggers
    logging.getLogger("geopandas").setLevel(logging.WARNING)
    logging.getLogger("fiona").setLevel(logging.WARNING)
    logging.getLogger("pyogrio").setLevel(logging.WARNING)

    # Log the start of the run
    logging.getLogger(__name__).info("Beyond-DEUS has started")

    # Read configuration parameters
    config = Configuration("config.yml")

    if config.running_mode in ("processing", "both"):
        processing_mode(config, log_queue)

    if config.running_mode in ("post-processing", "both"):
        post_processing_mode(config)

    if config.running_mode not in ("processing", "post-processing", "both"):
        error_message = (
            "Running mode %s not recognised. The program will stop."
            % (config.running_mode)
        )
        logging.getLogger(__name__).critical(error_message)
        raise OSError(error_message)

    logging.getLogger(__name__).info("Beyond-DEUS has finished")
    listener.stop()

    # If the listener has a private thread attribute, join it
    thread = getattr(listener, '_thread', None) or getattr(listener, 'thread', None)
    if thread:
        thread.join()
    else:
        # Fallback: give it a moment to drain the queue
        import time
        time.sleep(0.2)

    # Flush and close all handlers
    logging.shutdown()


def processing_mode(config, log_queue):
    """
    Run damage/loss calculations.
    """
    logger = logging.getLogger(__name__)
    logger.info("Running in processing mode")

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

    # Read exposure input names
    logger.info("Retrieving name(s) of input initial exposure model(s)")
    exposure_input_names = retrieve_exposure_input_names(config.input_paths["exposure_csv"])

    logger.info(
        "Running of calculations will be parallelised %s"
        % (config.parallelisation_mode.replace("_", " "))
    )

    if config.parallelisation_mode == "by_input_exposure":
        # Load objects necessary for pre-loading all intensity values
        # (exposure_geoms, intensity_provider)
        # Read intensity files
        logger.info("Reading input intensity file(s)")
        intensity_provider = read_intensity_files(
            config.input_paths["intensity"],
            config.parameters["intensity_file_type"]
        )

        if len(intensity_provider.keys()) == 0:
            logger.info(
                "No intensity files found. "
                "Check if 'intensity_file_type' in 'config.yml' is supported."
            )
            return

        # Read exposure geometries
        logger.info("Reading exposure geometries")
        exposure_geoms = read_exposure_geoms(config.input_paths["exposure_gpkg"])

        # Retrieve location (nearest neighbour position) of hazard intensity measures at the
        # centroids indicated in the input exposure geometries
        logger.info("Determining nearest-neighbour hazard positions for all exposure sites")
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

        # Read all hazard intensities for all branches and realisations
        all_branches_and_reals = {}

        for branch in intensity_provider:

            all_branches_and_reals[branch] = {}

            for realisation in intensity_provider[branch]:
                # Set up internal logger
                step_logger = logging.LoggerAdapter(
                    logger, {"branch": branch, "realisation": realisation}
                )

                all_intensities = (
                    intensity_provider[branch][realisation].get_values_at_multiple_positions(
                        intensity_positions,
                        config.parameters["intensity_threshold"]
                    )
                )
                step_logger.info(
                    "Branch %s, realisation %s: %s out of %s building_id "
                    "assumed with no further damage (intensity < threshold)"
                    % (
                        branch,
                        realisation,
                        all_intensities.shape[0] - all_intensities["run"].sum(),
                        all_intensities.shape[0]
                    )
                )

                all_branches_and_reals[branch][realisation] = all_intensities

        # Prepare a partial function to pass on to Pool
        func = partial(process_by_exposure, all_branches_and_reals)

        # Dispatch the pool
        with Pool(
            processes=config.cpus,
            initializer=init_worker_for_by_exposure,
            initargs=(log_queue,)
        ) as pool:
            pool.map(func, exposure_input_names)

    elif config.parallelisation_mode == "by_intensity_realisation":
        # Read intensity files
        logger.info("Reading input intensity file(s)")
        intensity_provider = read_intensity_files(
            config.input_paths["intensity"],
            config.parameters["intensity_file_type"]
        )

        if len(intensity_provider.keys()) == 0:
            logger.info(
                "No intensity files found. "
                "Check if 'intensity_file_type' in 'config.yml' is supported."
            )
            return

        # Load objects necessary for pre-loading all exposure models
        # (exposure_geoms, schema_mapper)
        logger.info("Reading exposure geometries")
        exposure_geoms = read_exposure_geoms(config.input_paths["exposure_gpkg"])

        # Retrieve location (nearest neighbour position) of hazard intensity measures at the
        # centroids indicated in the input exposure geometries
        logger.info("Determining nearest-neighbour hazard positions for all exposure sites")
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

        # Read, check and map all input exposure models
        logger.info("Reading all input exposure models")
        mapped_exposures = {}
        for initial_exposure_name_raw in exposure_input_names:
            mapped_exposure, _ = read_check_and_map_exposure(
                initial_exposure_name_raw, config, exposure_geoms, schema_mapper
            )
            mapped_exposures[initial_exposure_name_raw] = mapped_exposure

        del exposure_geoms, schema_mapper

        # Gather task tuples (individual combinations of each input exposure model with each
        # realisation of each branch of the hazard intensity)
        tasks = [
            (
                ename,
                mapped_exposures[ename],
                branch,
                realisation,
                intensity_provider[branch][realisation],
                intensity_positions
            )
            for ename in exposure_input_names
            for branch in intensity_provider
            for realisation in intensity_provider[branch]
        ]
        runner = process_by_intensity_realisation

        # Dispatch the pool
        with Pool(
            processes=config.cpus,
            initializer=init_worker_for_by_itensity_realisation,
            initargs=(log_queue,)
        ) as pool:
            pool.map(runner, tasks)

    else:
        error_message = (
            "Parallelisation mode %s not recognised. The program will stop."
            % (config.parallelisation_mode)
        )
        logger.critical(error_message)
        raise OSError(error_message)

    logger.info("Running in processing mode has finished")


def post_processing_mode(config):
    """
    Calculate statistics of previously-run damage/loss calculations.
    """
    logger = logging.getLogger(__name__)
    logger.info("Running in post-processing mode")

    if not os.path.exists(config.output_path):
        error_message = (
            "The path '%s' does not exist. No results can be retrieved to be post-processed. "
            "The program will stop." % (config.output_path)
        )
        logger.critical(error_message)
        raise OSError(error_message)

    # Check if output directory is empty
    if len(os.listdir(config.output_path)) == 0:
        error_message = (
            "The directory '%s' is empty. No results can be retrieved to be post-processed. "
            "The program will stop." % (config.output_path)
        )
        logger.critical(error_message)
        raise OSError(error_message)

    # Prepare directory to output statistics
    stats_output_path = os.path.join(config.output_path, "statistics")
    if os.path.exists(stats_output_path):
        # If it exists, check if there are files in it
        if not len(os.listdir(stats_output_path)) == 0:
            error_message = (
                "The path '%s' contains previously-calculated statistics. "
                "The program will stop." % (config.output_path)
            )
            logger.critical(error_message)
            raise OSError(error_message)
    else:
        # Create sub-directory to store statistics
        os.mkdir(stats_output_path)

    postprocessor = PostProcessor(config.post_processing, config.output_path)
    postprocessor.export()

    logger.info("Running in post-processing mode has finished")


class SafeFormatter(logging.Formatter):
    """
    This class makes the logging formatter robust to missing extras. By means of it, stray
    logging messages lacking extra fields will still format cleanly and not crash the listener.
    """
    def format(self, record):
        for name, default in (("exposure", "-"), ("branch", "-"), ("realisation", "-")):
            if not hasattr(record, name):
                setattr(record, name, default)
        return super().format(record)


if __name__ == "__main__":
    main()
