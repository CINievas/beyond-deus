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
import h5py
import numpy as np
import pandas as pd
import geopandas as gpd
from copy import deepcopy


class OutputGenerator:
    def __init__(
        self,
        hazard_prefix,
        initial_exposure_name,
        output_path,
        output_types,
        branch,
        realisation,
        updated_exposure,
        exposure_geoms
    ):
        """
        Attrs:
            self.hazard_prefix (str):
                String to be used as a prefix in the naming of the output files.
            self.initial_exposure_name (str):
                Name of the input exposure model used to generate 'updated_exposure' (to be used
                in the naming of the output files).
            self.output_path (str):
                Path to directory where outputs will be written.
            self.output_types (dict):
                Dictionary indicating the kind of outputs to export, by means of True/False.
                Options are sets of nested keys:
                    "compress_exposure_csvs":
                        Boolean. If True, the CSVs containing updated exposures will be
                        compressed into zstd format.
                    "mapped_exposure":
                        "csv": The input exposure model, mapped onto the target building and
                        damage schemas (i.e., conversion of building classes and damage states
                        due to compatibility across schemas, not the action of the input
                        hazard), is written to a CSV file.
                    "full_updated_exposure":
                        "csv": The full updated exposure model as a CSV file.
                        "csv_usable": One CSV file containing the usable assets of the full
                            updated exposure model.
                        "csv_unusable": One CSV file containing the unusable assets of the full
                            updated exposure model.
                        "hdf5_per_realisation": The full updated exposure model as one HDF5 file
                            per realisation of each logic tree branch.
                    "by_final_damage":
                        "csv_per_realisation": Number of buildings, replacement cost, census
                            occupants and losses of the whole portfolio, reported per final
                            damage state, due to each realisation of each logic tree branch.
                    "by_initial_and_final_damage":
                        "csv_per_realisation: Number of buildings, replacement cost, census
                            occupants and losses of the whole portfolio, reported per all
                            combinations of initial and final damage states, due to each
                            realisation of each logic tree branch.
                    "by_usability":
                        "csv_per_realisation": Number of buildings, replacement cost, census
                            people and losses of the whole portfolio, reported per usability
                            status, due to each realisation of each logic tree branch.
                    "by_building_id":
                        "loss_csv_per_realisation": Losses per building_id of the exposed assets
                            due to each realisation of each logic tree branch.
                        "loss_gpkg_per_realisation": Same as "loss_csv_per_realisation", with
                            the associated exposure geometries.
                        "only_transitioned_loss_csv_per_realisation": Same as
                            'loss_csv_per_realisation', but keeping only the building_ids for
                            which at least one of the assets transitions damage state.
                        "only_transitioned_loss_gpkg_per_realisation": Same as
                            'loss_gpkg_per_realisation', but keeping only the building_ids for
                            which at least one of the assets transitions damage state.
                        "damage_csv_per_realisation": Number of buildings per final damage state
                            and usability due to each realisation of each logic tree branch.
                        "damage_gpkg_per_realisation": Same as "damage_csv_per_realisation",
                            with the associated exposure geometries.
                        "only_transitioned_damage_csv_per_realisation": Same as
                            'damage_csv_per_realisation', but keeping only the building_ids for
                            which at least one of the assets transitions damage state.
                        "only_transitioned_damage_gpkg_per_realisation": Same as
                            'damage_gpkg_per_realisation', but keeping only the building_ids for
                            which at least one of the assets transitions damage state.
                        "damage_with_people_csv_per_realisation": Same as
                            'damage_csv_per_realisation', plus columns with number of census
                            people per damage state.
                        "damage_with_people_gpkg_per_realisation": Same as
                            'damage_gpkg_per_realisation', plus columns with number of census
                            people per damage state.
                self.branch (str):
                Name of the logic tree branch that 'updated_exposure' belongs to.
            self.realisation (str):
                Name of the hazard intensity realisation that 'updated_exposure' belongs to,
                within the logic tree branch 'branch'.
            self.updated_exposure (Pandas DataFrame)
                Updated exposure model with damage and losses, as output by Beyond DEUS.
            self.exposure_geoms (GeoPandas GeoDataFrame):
                GeoDataFrame with the geometries of the exposure model (one polygon per
                'building_id' of self.updated_exposure).
        """
        self.hazard_prefix = hazard_prefix
        self.initial_exposure_name = initial_exposure_name
        self.output_path = output_path
        self.output_types = output_types
        self.branch = branch
        self.realisation = realisation
        self.updated_exposure = updated_exposure
        self.exposure_geoms = exposure_geoms

    def export(self):
        if self.output_types["full_updated_exposure"]["csv"]:
            out_filename = "%s_b_%s_r_%s_%s_updated_exposure" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )

            if self.output_types["compress_exposure_csvs"]:
                self.updated_exposure.to_csv(
                    os.path.join(
                        self.output_path, "updated_exposure_csv",
                        "%s.zstd" % (out_filename)
                    ),
                    compression="zstd",
                    index=False
                )
            else:
                self.updated_exposure.to_csv(
                    os.path.join(
                        self.output_path, "updated_exposure_csv",
                        "%s.csv" % (out_filename)
                    ),
                    index=False
                )

        if (
            self.output_types["full_updated_exposure"]["csv_usable"] or
            self.output_types["full_updated_exposure"]["csv_unusable"]
        ):
            usable_assets, unusable_assets = split_updated_exposure_by_usability(
                self.updated_exposure
            )

        if self.output_types["full_updated_exposure"]["csv_usable"]:
            out_filename = (
                "%s_b_%s_r_%s_%s_updated_exposure_usable" % (
                    self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
                )
            )

            if self.output_types["compress_exposure_csvs"]:
                usable_assets.to_csv(
                    os.path.join(
                        self.output_path,"updated_exposure_usable_csv",
                        "%s.zstd" % (out_filename)
                    ),
                    compression="zstd",
                    index=False
                )
            else:
                usable_assets.to_csv(
                    os.path.join(
                        self.output_path,"updated_exposure_usable_csv",
                        "%s.csv" % (out_filename)
                    ),
                    index=False
                )

        if self.output_types["full_updated_exposure"]["csv_unusable"]:
            out_filename = (
                "%s_b_%s_r_%s_%s_updated_exposure_unusable" % (
                    self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
                )
            )

            if self.output_types["compress_exposure_csvs"]:
                unusable_assets.to_csv(
                    os.path.join(
                        self.output_path, "updated_exposure_unusable_csv",
                        "%s.zstd" % (out_filename)
                    ),
                    compression="zstd",
                    index=False
                )
            else:
                unusable_assets.to_csv(
                    os.path.join(
                        self.output_path, "updated_exposure_unusable_csv",
                        "%s.csv" % (out_filename)
                    ),
                    index=False
                )

        if self.output_types["full_updated_exposure"]["hdf5_per_realisation"]:
            out_filename = "%s_b_%s_r_%s_%s_updated_exposure.hdf5" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            write_exposure_to_HDF5(
                self.updated_exposure, os.path.join(self.output_path, out_filename)
            )

        if self.output_types["by_final_damage"]["csv_per_realisation"]:
            out_filename = "%s_b_%s_r_%s_%s_by_final_damage.csv" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            write_output_by_final_damage(
                self.updated_exposure,
                os.path.join(self.output_path, out_filename)
            )

        if self.output_types["by_initial_and_final_damage"]["csv_per_realisation"]:
            out_filename = (
                "%s_b_%s_r_%s_%s_by_initial_and_final_damage.csv" % (
                    self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
                )
            )
            write_output_by_initial_and_final_damage(
                self.updated_exposure,
                os.path.join(self.output_path, out_filename)
            )

        if self.output_types["by_usability"]["csv_per_realisation"]:
            out_filename = "%s_b_%s_r_%s_%s_by_usability.csv" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            write_output_by_usability(
                self.updated_exposure,
                os.path.join(self.output_path, out_filename)
            )

        if (
            self.output_types["by_building_id"]["loss_csv_per_realisation"]
            or
            self.output_types["by_building_id"]["loss_gpkg_per_realisation"]
        ):
            out_filename_we = "%s_b_%s_r_%s_%s_loss_by_building_id" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            write_loss_by_building_id(
                self.updated_exposure,
                self.exposure_geoms,
                write_to_CSV=self.output_types["by_building_id"]["loss_csv_per_realisation"],
                write_to_GPKG=self.output_types["by_building_id"]["loss_gpkg_per_realisation"],
                filter_only_transitioned=False,
                outpath=self.output_path,
                filename_without_extension=out_filename_we
            )

        if (
            self.output_types["by_building_id"]["only_transitioned_loss_csv_per_realisation"]
            or
            self.output_types["by_building_id"]["only_transitioned_loss_gpkg_per_realisation"]
        ):
            out_filename_we = "%s_b_%s_r_%s_%s_loss_by_building_id_only_transitioned" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            write_loss_by_building_id(
                self.updated_exposure,
                self.exposure_geoms,
                write_to_CSV=self.output_types["by_building_id"][
                    "only_transitioned_loss_csv_per_realisation"
                ],
                write_to_GPKG=self.output_types["by_building_id"][
                    "only_transitioned_loss_gpkg_per_realisation"
                ],
                filter_only_transitioned=True,
                outpath=self.output_path,
                filename_without_extension=out_filename_we
            )

        # To avoid calculating 'damage_by_bdg_id' twice
        damage_by_bdg_id = None
        if (
            self.output_types["by_building_id"]["damage_with_people_csv_per_realisation"]
            or
            self.output_types["by_building_id"]["damage_with_people_gpkg_per_realisation"]
        ):
            out_filename_we = "%s_b_%s_r_%s_%s_damage_with_people_by_building_id" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            damage_by_bdg_id = write_damage_by_building_id(
                self.updated_exposure,
                self.exposure_geoms,
                write_to_CSV=self.output_types["by_building_id"][
                    "damage_with_people_csv_per_realisation"
                ],
                write_to_GPKG=self.output_types["by_building_id"][
                    "damage_with_people_gpkg_per_realisation"
                ],
                filter_only_transitioned=False,
                include_people=True,
                outpath=self.output_path,
                filename_without_extension=out_filename_we,
                previously_calculated_damage_by_bdg_id=None
            )

        # If 'damage_by_bdg_id' already exists, it contains people, so remove them
        if damage_by_bdg_id is not None:
            damage_by_bdg_id = damage_by_bdg_id.drop(
                columns=damage_by_bdg_id.filter(regex="^ppl_census_").columns
            )

        if (
            self.output_types["by_building_id"]["damage_csv_per_realisation"]
            or
            self.output_types["by_building_id"]["damage_gpkg_per_realisation"]
        ):
            out_filename_we = "%s_b_%s_r_%s_%s_damage_by_building_id" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            damage_by_bdg_id = write_damage_by_building_id(
                self.updated_exposure,
                self.exposure_geoms,
                write_to_CSV=self.output_types["by_building_id"]["damage_csv_per_realisation"],
                write_to_GPKG=self.output_types["by_building_id"]["damage_gpkg_per_realisation"],
                filter_only_transitioned=False,
                include_people=False,
                outpath=self.output_path,
                filename_without_extension=out_filename_we,
                previously_calculated_damage_by_bdg_id=damage_by_bdg_id # from above
            ) # if 'damage_by_bdg_id' exists, it will return the same

        if (
            self.output_types["by_building_id"]["only_transitioned_damage_csv_per_realisation"]
            or
            self.output_types["by_building_id"]["only_transitioned_damage_gpkg_per_realisation"]
        ):
            out_filename_we = "%s_b_%s_r_%s_%s_damage_by_building_id_only_transitioned" % (
                self.hazard_prefix, self.branch, self.realisation, self.initial_exposure_name
            )
            _ = write_damage_by_building_id(
                self.updated_exposure,
                self.exposure_geoms,
                write_to_CSV=self.output_types["by_building_id"][
                    "only_transitioned_damage_csv_per_realisation"],
                write_to_GPKG=self.output_types["by_building_id"][
                    "only_transitioned_damage_gpkg_per_realisation"
                ],
                filter_only_transitioned=True,
                include_people=False,
                outpath=self.output_path,
                filename_without_extension=out_filename_we,
                previously_calculated_damage_by_bdg_id=damage_by_bdg_id # from above
            )


def write_exposure_to_HDF5(exposure, filename, dataset_name="updated_exposure"):
    """
    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        filename (str):
            Full path to the HDF5 file to which 'exposure' will be written.
        dataset_name (str):
            Name to be used for the dataset within the HDF5 file. Default: "updated_exposure".
    """
    fle = h5py.File(filename, "a")

    # NOTE: It was not possible to use pandas.DataFrame.to_records() directly because
    # of problems converting the string columns in 'exposure'

    # Define the structure (data types) and data of the Numpy Structured Array
    # to be used to create the HDF5 file
    arr_structure = {}
    arr_data = {}

    for col in exposure:
        if col in ["building_id", "taxonomy"]:
            # String columns need special care!
            str_length = exposure[col].str.len().max()
            arr_col = exposure[col].to_numpy().astype((np.bytes_, str_length))
        else:
            # Simple conversion for all other data types (int, float)
            arr_col = exposure[col].to_numpy()

        arr_data[col] = arr_col
        arr_structure[col] = arr_col.dtype

    arr_dtype = np.dtype(list(arr_structure.items()))

    # Create the Numpy Structured Array
    exposure_arr = np.zeros(exposure.shape[0], arr_dtype)
    for col in arr_data:
        exposure_arr[col] = arr_data[col]

    # Write the Numpy Structured Array to the HDF5 file
    exposure_ctxt = fle.create_dataset(
        dataset_name,
        exposure_arr.shape,
        dtype=exposure_arr.dtype,
    )
    exposure_ctxt[:] = exposure_arr

    fle.close()


def write_output_by_final_damage(exposure, filename):
    """
    This method outputs number of buildings, total repleacement costs, total number of census
    occupants, total incremental losses and total cumulative losses aggregated by final damage
    state, to a CSV file.

    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        filename (str):
            Full path to the CSV file to which results by final damage state will be written.
    """
    if ("incremental_loss" in exposure.columns) and ("cum_loss_value" in exposure.columns):
        by_damage = exposure.groupby(
            ["final_damage"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "incremental_loss": "sum",
                "cum_loss_value": "sum"
            },
        )
    else:
        by_damage = exposure.groupby(
            ["final_damage"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum"
            },
        )

    by_damage.to_csv(filename, index=True)


def write_output_by_initial_and_final_damage(exposure, filename):
    """
    This method outputs number of buildings, total repleacement costs, total number of census
    occupants, total incremental losses and total cumulative losses aggregated by initial and
    final damage states, to a CSV file.

    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        filename (str):
            Full path to the CSV file to which results by initial and final damage states will
            be written.
    """
    if ("incremental_loss" in exposure.columns) and ("cum_loss_value" in exposure.columns):
        by_initial_and_final_damage = exposure.groupby(
            ["initial_damage", "final_damage"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "incremental_loss": "sum",
                "cum_loss_value": "sum"
            },
        )
    else:
        by_initial_and_final_damage = exposure.groupby(
            ["initial_damage", "final_damage"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum"
            },
        )

    by_initial_and_final_damage.to_csv(filename, index=True)


def write_output_by_usability(exposure, filename):
    """
    This method outputs number of buildings, total repleacement costs, total number of census
    occupants, total incremental losses and total cumulative losses aggregated by usability
    status, to a CSV file.

    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        filename (str):
            Full path to the CSV file to which results by final damage state will be written.
    """
    if ("incremental_loss" in exposure.columns) and ("cum_loss_value" in exposure.columns):
        by_usability = exposure.groupby(
            ["cum_usability"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "incremental_loss": "sum",
                "cum_loss_value": "sum"
            },
        )
    else:
        by_usability = exposure.groupby(
            ["cum_usability"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum"
            },
        )

    # Rename index
    mapping = {0: "unusable", 1: "usable"}
    by_usability.rename(index=mapping, inplace=True)

    by_usability.to_csv(filename, index=True)


def write_loss_by_building_id(
    exposure,
    exposure_geoms,
    write_to_CSV=False,
    write_to_GPKG=False,
    filter_only_transitioned=False,
    outpath=None,
    filename_without_extension=None
):
    """
    This methods outputs number of buildings, total repleacement costs, total number of census
    occupants, total incremental losses and total cumulative losses, both in absolute value and
    as loss ratios, per 'building_id' of the exposure model.

    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        exposure_geoms (GeoPandas GeoDataFrame):
            GeoDataFrame with the geometries of the exposure model (one polygon per 'building_id'
            of 'exposure').
        write_to_CSV (bool):
            If True, the output will be written as a CSV to 'filename_without_extension'.csv.
        write_to_GPKG (bool):
            If True, the output, including the exposure geometries, will be written as a GPKG to
            'filename_without_extension'.gpkg.
        filter_only_transitioned (bool):
            If True, only output building_ids for which at least one of their associated assets
            transitions to a worse damage state.
        outpath (str):
            Directory to which the results will be written.
        filename_without_extension (str):
            Name of the CSV and/or GPKG file to which results will be written, without the
            corresponding file extension.
    """

    if not filter_only_transitioned:
        loss_by_bdg_id = exposure.groupby(
            ["building_id"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "incremental_loss": "sum",
                "cum_loss_value": "sum"
            }
        )
    else:
        loss_by_bdg_id = exposure.groupby(
            ["building_id"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "incremental_loss": "sum",
                "cum_loss_value": "sum",
                # "transition"=True if at least one row of 'building_id' has transitioned damage
                "transition": lambda x: x.any()
            }
        )
        loss_by_bdg_id = loss_by_bdg_id[loss_by_bdg_id.transition]
        del loss_by_bdg_id["transition"]

    loss_by_bdg_id["incremental_loss_ratio"] = (
        loss_by_bdg_id["incremental_loss"] /
        loss_by_bdg_id["replacement_cost_tot"]
    )
    loss_by_bdg_id["cum_loss_ratio"] = (
        loss_by_bdg_id["cum_loss_value"] /
        loss_by_bdg_id["replacement_cost_tot"]
    )

    if write_to_CSV:
        out_filename = "%s.csv" % (filename_without_extension)
        loss_by_bdg_id.to_csv(os.path.join(outpath, out_filename), index=True)

    if write_to_GPKG:
        loss_by_bdg_id_with_geoms_aux = pd.merge(
            loss_by_bdg_id, exposure_geoms, on="building_id"
        )
        loss_by_bdg_id_with_geoms = gpd.GeoDataFrame(
            loss_by_bdg_id_with_geoms_aux,
            geometry=loss_by_bdg_id_with_geoms_aux["geometry"],
            crs=exposure_geoms.crs
        )
        loss_by_bdg_id_with_geoms.set_index(
            loss_by_bdg_id_with_geoms["building_id"], inplace=True
        )
        loss_by_bdg_id_with_geoms.drop(columns=["building_id"], inplace=True)

        out_filename = "%s.gpkg" % (filename_without_extension)

        loss_by_bdg_id_with_geoms.to_file(os.path.join(outpath, out_filename), driver="GPKG")


def write_damage_by_building_id(
    exposure,
    exposure_geoms,
    write_to_CSV=False,
    write_to_GPKG=False,
    filter_only_transitioned=False,
    include_people=False,
    outpath=None,
    filename_without_extension=None,
    previously_calculated_damage_by_bdg_id=None
):
    """
    This methods outputs number and proportion of buildings in each final damage state, per
    'building_id' of the exposure model.

    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        exposure_geoms (GeoPandas GeoDataFrame):
            GeoDataFrame with the geometries of the exposure model (one polygon per 'building_id'
            of 'exposure').
        write_to_CSV (bool):
            If True, the output will be written as a CSV to 'filename_without_extension'.csv.
        write_to_GPKG (bool):
            If True, the output, including the exposure geometries, will be written as a GPKG to
            'filename_without_extension'.gpkg.
        filter_only_transitioned (bool):
            If True, only output building_ids for which at least one of their associated assets
            transitions to a worse damage state.
        include_people (bool):
            If True, the output includes the number of census people per building_id and damage
            state.
        outpath (str):
            Directory to which the results will be written.
        filename_without_extension (str):
            Name of the CSV and/or GPKG file to which results will be written, without the
            corresponding file extension.
        previously_calculated_damage_by_bdg_id (Pandas DataFrame):
            If not None, this is taken as the output to export. If None, it is calculated herein
            by means of the 'damage_by_building_id_as_columns' method.

    Returns:
        damage_by_bdg_id (Pandas DataFrame):
            DataFrame with index equal to 'building_id', and the following columns:
                "number" (float):
                    Total number of buildings of 'building_id'.
                "number_usable" (float):
                    Number of buildings of 'building_id' that are usable.
                "number_unusable" (float):
                    Number of buildings of 'building_id' that are unusable.
                "proportion_usable" (float):
                    Proportion of buildings of 'building_id' that are usable.
                "proportion_unusable" (float):
                    Proportion of buildings of 'building_id' that are unusable.
                "ppl_census_usable" (float):
                    Number of census people of 'building_id' in usable buildings (if
                    'include_people' is True).
                "ppl_census_unusable" (float):
                    Number of census people of 'building_id' in unusable buildings (if
                    'include_people' is True).
                "number_DX" (float):
                    Number of buildings of 'building_id' in damage state "X".
                "proportion_DX" (float):
                    Proportion of buildings of 'building_id' in damage state "X".
                "ppl_census_DX" (float):
                    Number of census people of 'building_id' in damage state "X" (if
                    'include_people' is True).
    """

    if previously_calculated_damage_by_bdg_id is None:
        damage_by_bdg_id = damage_by_building_id_as_columns(exposure, include_people)
    else:
        damage_by_bdg_id = deepcopy(previously_calculated_damage_by_bdg_id)

    if filter_only_transitioned:
        damage_by_bdg_id = filter_damage_by_bdg_id_only_transitioned(exposure, damage_by_bdg_id)

    if write_to_CSV:
        out_filename = "%s.csv" % (filename_without_extension)
        damage_by_bdg_id.to_csv(os.path.join(outpath, out_filename), index=True)

    if write_to_GPKG:
        damage_by_bdg_id_with_geoms_aux = pd.merge(
            damage_by_bdg_id, exposure_geoms, on="building_id"
        )
        damage_by_bdg_id_with_geoms = gpd.GeoDataFrame(
            damage_by_bdg_id_with_geoms_aux,
            geometry=damage_by_bdg_id_with_geoms_aux["geometry"],
            crs=exposure_geoms.crs
        )
        damage_by_bdg_id_with_geoms.set_index(
            damage_by_bdg_id_with_geoms["building_id"], inplace=True
        )
        damage_by_bdg_id_with_geoms.drop(columns=["building_id"], inplace=True)

        out_filename = "%s.gpkg" % (filename_without_extension)

        damage_by_bdg_id_with_geoms.to_file(os.path.join(outpath, out_filename), driver="GPKG")

    return damage_by_bdg_id


def damage_by_building_id_as_columns(exposure, include_people=False):
    """
    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        include_people (bool):
            If True, the output includes the number of census people per 'building_id' and
            damage state.

    Returns:
        damage_by_bdg_id (Pandas DataFrame):
            DataFrame with index equal to 'building_id', and the following columns:
                "number" (float):
                    Total number of buildings of 'building_id'.
                "number_usable" (float):
                    Number of buildings of 'building_id' that are usable.
                "number_unusable" (float):
                    Number of buildings of 'building_id' that are unusable.
                "proportion_usable" (float):
                    Proportion of buildings of 'building_id' that are usable.
                "proportion_unusable" (float):
                    Proportion of buildings of 'building_id' that are unusable.
                "ppl_census_usable" (float):
                    Number of census people of 'building_id' in usable buildings (if
                    'include_people' is True).
                "ppl_census_unusable" (float):
                    Number of census people of 'building_id' in unusable buildings (if
                    'include_people' is True).
                "number_DX" (float):
                    Number of buildings of 'building_id' in damage state "X".
                "proportion_DX" (float):
                    Proportion of buildings of 'building_id' in damage state "X".
                "ppl_census_DX" (float):
                    Number of census people of 'building_id' in damage state "X" (if
                    'include_people' is True).
    """
    if include_people:

        damage_by_bdg_id_aux = exposure.groupby(
            ["building_id", "final_damage"]
        ).agg({"number": "sum", "ppl_census": "sum"})

        usability_by_bdg_id_aux = exposure.groupby(
            ["building_id", "cum_usability"]
        ).agg({"number": "sum", "ppl_census": "sum"})

    else:

        damage_by_bdg_id_aux = exposure.groupby(
            ["building_id", "final_damage"]
        ).agg({"number": "sum"})

        usability_by_bdg_id_aux = exposure.groupby(
            ["building_id", "cum_usability"]
        ).agg({"number": "sum"})

    unique_damage_levels = damage_by_bdg_id_aux.index.get_level_values("final_damage").unique()

    # Initialise output
    damage_by_bdg_id = exposure.groupby(["building_id"]).agg({"number": "sum"})

    damage_by_bdg_id["number_usable"] = np.zeros(damage_by_bdg_id.shape[0])
    damage_by_bdg_id["number_unusable"] = np.zeros(damage_by_bdg_id.shape[0])
    damage_by_bdg_id["proportion_usable"] = np.zeros(damage_by_bdg_id.shape[0])
    damage_by_bdg_id["proportion_unusable"] = np.zeros(damage_by_bdg_id.shape[0])
    if include_people:
        damage_by_bdg_id["ppl_census_usable"] = np.zeros(damage_by_bdg_id.shape[0])
        damage_by_bdg_id["ppl_census_unusable"] = np.zeros(damage_by_bdg_id.shape[0])

    for final_damage in unique_damage_levels:
        damage_by_bdg_id["number_D%s" % (final_damage)] = np.zeros(damage_by_bdg_id.shape[0])

    if include_people:  # Separate for loop so that all "number" and all "ppl" cols are together
        for final_damage in unique_damage_levels:
            damage_by_bdg_id["ppl_census_D%s" % (final_damage)] = np.zeros(
                damage_by_bdg_id.shape[0]
            )

    for final_damage in unique_damage_levels:
        # Filter rows associated with 'final_damage'
        # (note not all combinations of (building_id, final_damage)
        # exist in 'damage_by_bdg_id_aux')
        just_final_damage_rows = damage_by_bdg_id_aux.loc[:, final_damage, :]

        # 'idx' is boolean for each element of the index of 'damage_by_bdg_id', indicating
        # whether that index exists in the index of 'just_final_damage_rows'
        idx = damage_by_bdg_id.index.isin(just_final_damage_rows.index)

        # For those rows whose index exist, add the corresponding buildings
        damage_by_bdg_id.loc[idx, "number_D%s" % (final_damage)] += (
            just_final_damage_rows.loc[:, "number"]
        )

        if include_people:
            # For those rows whose index exist, add the corresponding census people
            damage_by_bdg_id.loc[idx, "ppl_census_D%s" % (final_damage)] += (
                just_final_damage_rows.loc[:, "ppl_census"]
            )

    for final_damage in unique_damage_levels:
        damage_by_bdg_id["proportion_D%s" % (final_damage)] = (
            damage_by_bdg_id["number_D%s" % (final_damage)] / damage_by_bdg_id["number"]
        )

    usability_labels = {0: "unusable", 1: "usable"}
    existing_usability_vals = usability_by_bdg_id_aux.index.get_level_values(
        "cum_usability"
    ).unique()  # usability_by_bdg_id_aux may not have both usability values (0 and 1)

    for usability_val in existing_usability_vals:
        usability_label = usability_labels[usability_val]

        # Filter rows associated with 'usability_val'
        # (note not all combinations of (building_id, usability_val)
        # exist in 'usability_by_bdg_id_aux')
        just_usability_val_rows = usability_by_bdg_id_aux.loc[:, usability_val, :]

        # 'idx' is boolean for each element of the index of 'damage_by_bdg_id', indicating
        # whether that index exists in the index of 'just_usability_val_rows'
        idx = damage_by_bdg_id.index.isin(just_usability_val_rows.index)

        # For those rows whose index exist, add the corresponding buildings
        damage_by_bdg_id.loc[idx, "number_%s" % (usability_label)] += (
            just_usability_val_rows.loc[:, "number"]
        )

        if include_people:
            # For those rows whose index exist, add the corresponding census people
            damage_by_bdg_id.loc[idx, "ppl_census_%s" % (usability_label)] += (
                just_usability_val_rows.loc[:, "ppl_census"]
            )

    damage_by_bdg_id["proportion_usable"] = (
        damage_by_bdg_id["number_usable"] / damage_by_bdg_id["number"]
    )
    damage_by_bdg_id["proportion_unusable"] = (
        damage_by_bdg_id["number_unusable"] / damage_by_bdg_id["number"]
    )

    return damage_by_bdg_id


def filter_damage_by_bdg_id_only_transitioned(exposure, damage_by_bdg_id):
    """
    This method keeps in 'damage_by_bdg_id' only the building_ids for which at least one asset
    transitions damage state. The latter condition is determined from the input 'exposure'.

    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        damage_by_bdg_id (Pandas DataFrame, output of 'damage_by_building_id_as_columns'):
            DataFrame with index equal to 'building_id', and the following columns:
                "number" (float):
                    Total number of buildings of 'building_id'.
                "number_usable" (float):
                    Number of buildings of 'building_id' that are usable.
                "number_unusable" (float):
                    Number of buildings of 'building_id' that are unusable.
                "number_DX" (float):
                    Number of buildings of 'building_id' in damage state "X".
                "proportion_DX" (float):
                    Proportion of buildings of 'building_id' in damage state "X".

    Returns:
        damage_by_bdg_id (Pandas DataFrame):
            The same as the input, but only with rows of 'building_id' for which at least one
            asset transitions damage state.
    """

    # "transition"=True if at least one row of 'building_id' has transitioned damage
    transitioned_by_bdg_id = exposure.groupby(["building_id"]).agg(
        {"transition": lambda x: x.any()}
    )
    damage_by_bdg_id = damage_by_bdg_id.join(transitioned_by_bdg_id) # index=building_id in both
    damage_by_bdg_id = damage_by_bdg_id[damage_by_bdg_id.transition]
    del damage_by_bdg_id["transition"]

    return damage_by_bdg_id


def split_updated_exposure_by_usability(exposure):

    usable_assets = exposure[exposure.cum_usability==1].copy()
    unusable_assets = exposure[exposure.cum_usability==0].copy()

    return usable_assets, unusable_assets
