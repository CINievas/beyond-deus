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
import logging
import pandas as pd
import geopandas as gpd
import numpy as np
from copy import deepcopy

logger = logging.getLogger()


def retrieve_exposure_input_names(directory_csv):
    """
    Function to retrieve the names of all CSV or ZSTD files located in 'directory_csv',
    including their extension.
    """
    exposure_names = os.listdir(directory_csv)

    return exposure_names


def read_exposure_geoms(filename_geoms):
    """
    Function to read the exposure geometries from the GPKG input file.

    Args:
       filename_geoms (str):
            Path to the exposure GPKG file, which must contain one polygon per 'building_id' of
            all of the exposure CSV files.

    Returns:
        exposure_geoms (GeoPandas GeoDataFrame):
            GeoPandas GeoDataFrame with the contents of 'filename_geoms'.
    """
    # Read input GPKG
    exposure_geoms = gpd.read_file(filename_geoms)
    # Make sure "building_id" are strings
    exposure_geoms["building_id"] = exposure_geoms["building_id"].astype(str)

    return exposure_geoms


def read_exposure_csv(filename_csv):
    """
    Function to read the exposure CSV file, as CSV in itself or pre-compressed into ZSTD.

    If the CSV file contains an "id" column, it is discarded.

    If the CSV file contains a "final_damage" column, then it is assumed that this is a
    cumulative damage calculation and the contents of the "initial_damage" column are replaced
    by those of "final_damage", and the "final_damage" column is discarded.

    If the CSV file contains an "incremental_loss" column, it is discarded.

    If the CSV file contains an "transition" column, it is discarded.

    If the CSV file contains several rows with the same combination of
    ["building_id", "taxonomy", "initial_damage"], those rows are grouped together (with summed
    values of "number", "replacement_cost_tot", "ppl_census" and "cum_loss_value").

    If the CSV files does not contain a "cum_usability" column, it is added, assuming all assets
    are usable.

    Args:
        filename_csv (str):
            Path to the exposure CSV/ZSTD file, with one row per exposure asset (a number of
            buildings of a particular building class, in a particular damage state, at a
            particular location) and the following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets. All the "building_id"s
                    need to exist in "intensity_positions" (see below).
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.

    Returns:
        exposure_df (Pandas DataFrame):
            Pandas DataFrame with the contents of 'filename_csv' (see columns above).
    """
    # Determine extension of 'filename_csv':
    filename_extension = filename_csv.split(".")[-1]

    # Read input CSV/ZSTD
    if filename_extension.lower()=="csv":
        exposure_df = pd.read_csv(
            filename_csv, dtype={"building_id": str, "initial_damage":int}
        )
    elif filename_extension.lower()=="zstd":
        exposure_df = pd.read_csv(
            filename_csv, dtype={"building_id": str, "initial_damage":int}, compression="zstd"
        )
    else:
        error_message = (
            "Input exposure file extension not recognised. Supported formats: .csv, .zstd"
        )
        raise OSError(error_message)

    # Make sure "building_id" are strings
    exposure_df["building_id"] = exposure_df["building_id"].astype(str)
    # Make sure "initial_damage" is an integer
    exposure_df["initial_damage"] = exposure_df["initial_damage"].astype(int)

    if "id" in exposure_df.columns:
        del exposure_df["id"]

    if "final_damage" in exposure_df.columns:  # It means Beyond-DEUS has been run before
        exposure_df["final_damage"] = exposure_df["final_damage"].astype(int)
        # Make the final damage from a previous run the new initial damage
        exposure_df["initial_damage"] = deepcopy(exposure_df["final_damage"])
        del exposure_df["final_damage"]

    if "incremental_loss" in exposure_df.columns:  # It means Beyond-DEUS has been run before
        del exposure_df["incremental_loss"]
    if "transition" in exposure_df.columns:  # It means Beyond-DEUS has been run before
        del exposure_df["transition"]

    if "cum_loss_value" not in exposure_df.columns:
        exposure_df["cum_loss_value"] = np.zeros(exposure_df.shape[0], dtype=float)

    if "cum_usability" not in exposure_df.columns:
        exposure_df["cum_usability"] = np.ones(exposure_df.shape[0], dtype="int8")

    # Group combinations of ["building_id", "taxonomy", "initial_damage"], if duplicates exist
    # (index doesn't matter because 'unique_combis' is only used to check if duplicates exist)
    unique_combis = exposure_df[
        ["building_id", "taxonomy", "initial_damage", "cum_usability"]
    ].drop_duplicates()

    if unique_combis.shape[0] < exposure_df.shape[0]:
        exposure_df = exposure_df.groupby(
            ["building_id", "taxonomy", "initial_damage", "cum_usability"]
        ).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "cum_loss_value": "sum",
            }
        )
        exposure_df.reset_index(inplace=True)

    return exposure_df


def read_exposure_intensity_combinations(filename_csv):
    """
    This method reads the exposure-intensity combinations CSV file.

    Returns:
        combis_df (Pandas DataFrame):
            DataFrame in which each row is a combination of an input exposure file and a hazard
            realisation within a branch. Columns:
                "exposure_csv": Name of the input exposure CSV file.
                "branch": Name of the hazard branch.
                "realisation": Name of the realisation within the hazard branch.
    """

    combis_df = pd.read_csv(filename_csv)
    combis_df["branch"] = combis_df["branch"].astype(str)
    combis_df["realisation"] = combis_df["realisation"].astype(str)

    return combis_df


def check_exposure_intensity_combinations(
    exposure_intensity_combinations, exposure_input_names, intensity_provider
):

    # Check all exposure filenames exist in 'exposure_input_names'
    unique_exposure_filenames = exposure_intensity_combinations["exposure_csv"].unique()

    not_found = []
    for filename in unique_exposure_filenames:
        if filename not in exposure_input_names:
            not_found.append(filename)

    if len(not_found) > 0:
        error_message = (
            "Some input exposure files listed in the exposure-intensity combinations have not "
            "been found: %s. The program cannot run." % (", ".join(not_found))
        )
        logger.critical(error_message)
        raise OSError(error_message)

    # Check all hazard branch names exist in 'intensity_provider':
    unique_branches = exposure_intensity_combinations["branch"].unique()

    not_found = []
    for branch in unique_branches:
        if branch not in intensity_provider.keys():
            not_found.append(branch)

    if len(not_found) > 0:
        error_message = (
            "Some input hazard branches listed in the exposure-intensity combinations have not "
            "been found: %s. The program cannot run." % (", ".join(not_found))
        )
        logger.critical(error_message)
        raise OSError(error_message)

    # Check that the realisations exist within the branches
    branch_reals = exposure_intensity_combinations.groupby(
        ["branch", "realisation"]
    ).agg({"exposure_csv": "first"})  # it does not matter, it's just to get the index

    for i in range(branch_reals.shape[0]):
        if not(branch_reals.index[i][1] in intensity_provider[branch_reals.index[i][0]].keys()):
            error_message = (
                "Realisation '%s' cannot be found in branch '%s' of the intensity provider. "
                "Check of the exposure-intensity combinations has failed. "
                "The program cannot run." % (branch_reals.index[i][1], branch_reals.index[i][0])
            )
            logger.critical(error_message)
            raise OSError(error_message)


def check_all_building_ids_in_geoms(exposure_df, exposure_geoms):
    """
    Function to check that all "building_id"s from 'exposure_df' have a geometry in
    'exposure_geoms'. It raises an OSError if this is not the case.

    Args:
        exposure_df (Pandas DataFrame): As output by 'read_exposure_csv'.
        exposure_geoms (GeoPandas GeoDataFrame): As output by 'read_exposure_geoms'.
    """
    # Check all "building_id"s from exposure_df have a geometry in exposure_geoms
    unique_bdg_ids = exposure_df["building_id"].unique()
    geom_bdg_ids = exposure_geoms["building_id"].to_numpy()

    bdg_ids_not_found = []
    for building_id in unique_bdg_ids:
        if building_id not in geom_bdg_ids:
            bdg_ids_not_found.append(building_id)

    if len(bdg_ids_not_found) > 0:
        error_message = (
            "Not all exposure polygons (building_id) in the exposure CSV file are present "
            "in the exposure GPKG file. The following building_ids are missing: %s"
            % (", ".join(bdg_ids_not_found))
        )
        raise OSError(error_message)

    return


def update_exposure_transitions_and_losses(
    exposure,
    hazard_intensities,
    intensity_threshold,
    fragility_provider,
    loss_provider,
    usability_model,
):
    """
    Function copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    This function requests the updating of the input exposure model due to the hazard whose
    intensities are handled by the intensity provider. It does so by instanciating the
    Updater class and running its update function.

    The output is a GeoPandas GeoDataFrame similar to the input 'exposure' GeoDataFrame,
    but with updated damage states and additional columns, including information on damage
    transitions and losses.

    Args:
        exposure (Pandas DataFrame):
            DataFrame with one row per exposure asset (a number of buildings of a particular
            building class, in a particular damage state, at a particular location) and the
            following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets. All the "building_id"s
                    need to exist in "hazard_intensities" (see below).
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.
        hazard_intensities (Pandas DataFrame):
            DataFrame indicating the values of hazard intensity associated with all exposure
            polygons of 'exposure', identified by the "building_id" (index of the DataFrame).
            The DataFrame contains the following columns:
                - "nearest_neighbour" (int): The position of the nearest neighbour site.
                - One column per intensity measure type, containing the hazard intensity
                values (float) associated with that intensity measure type.
                - "run" (bool): True if at least one of the hazard intensity values is larger
                than the intensity_threshold set in the configuration, False if all of them are
                smaller. Buildings in exposure polygons with "run" = False are assumed to remain
                in the same current damage state (now damage calculation is run for them).
        intensity_threshold (float):
            Threshold of hazard intensity, to be used so that if the intensity value at a target
            exposure point is smaller than the threshold, no further damage is assumed (and the
            detailed calculation is avoided).
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.
        loss_provider (LossProvider):
            Instance of LossProvider to access the economic consequence model (loss ratios per
            damage state) and building replacement costs.
        usability_model (Usability):
            Instance of Usability to access the usability model (usable/unusable classification
            per damage state).

    Returns:
        updated_exposure_and_losses (Pandas DataFrame):
            DataFrame with one row per (updated) exposure asset. The number of rows of
            'updated_exposure_and_losses' is equal to or larger than the number of rows of
            the input 'exposure_df', as each row of 'exposure_df' may remain in the same
            damage state or transition to a new one, and each of these possible paths
            becomes a new exposed asset. It contains the following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets.
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "final_damage" (int):
                    Final damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "incremental_loss" (float):
                    Economic loss associated with the asset calculated in the current run of
                    this function.
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before) plus the incremental loss
                    calculated in this function (by calling 'compute_loss').
                "cum_usability" (int):
                    If usability_model.data is not None: Usability assessment from the current
                        calculation, accounting for the usability status from previous
                        calculations: 0 if unusable, 1 if usable.
                    If usability_model.data is None: Usability assessment from a previously-run
                        calculation, as in the input 'exposure_df': 0 if unusable, 1 if usable.
                "transition" (bool):
                    True if the asset has changed damage state, False if it has not.
    """
    updater = Updater(
        fragility_provider,
        hazard_intensities,
        intensity_threshold,
        loss_provider,
        usability_model
    )

    updated_exposure = updater.update_df(exposure)

    # This function can be used to parallelise the updating of the exposure model
    # Right now, it is not parallelised, so it just calls the Updater class and
    # the update_df method of the class.

    return updated_exposure


class Updater:
    """
    Class attrributes and rationale of its methods copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    The methods themselves are substantially different from those in DEUS, but the logic behind
    them is based on them.

    Class used for running updates on the exposure.

    Attributes:
        exposure (Pandas DataFrame):
            DataFrame with one row per exposure asset (a number of buildings of a particular
            building class, in a particular damage state, at a particular location) and the
            following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets. All the "building_id"s
                    need to exist in "hazard_intensities" (see below).
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.
        hazard_intensities (Pandas DataFrame):
            DataFrame indicating the values of hazard intensity associated with all exposure
            polygons of 'exposure', identified by the "building_id" (index of the DataFrame).
            The DataFrame contains the following columns:
                - "nearest_neighbour" (int): The position of the nearest neighbour site.
                - One column per intensity measure type, containing the hazard intensity
                values (float) associated with that intensity measure type.
                - "run" (bool): True if at least one of the hazard intensity values is larger
                than the intensity_threshold set in the configuration, False if all of them are
                smaller. Buildings in exposure polygons with "run" = False are assumed to remain
                in the same current damage state (now damage calculation is run for them).
        intensity_threshold (float):
            Threshold of hazard intensity, to be used so that if the intensity value at a target
            exposure point is smaller than the threshold, no further damage is assumed (and the
            detailed calculation is avoided).
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.
        loss_provider (LossProvider):
            Instance of LossProvider to access the economic consequence model (loss ratios per
            damage state) and building replacement costs.
        usability_model (Usability):
            Instance of Usability to access the usability model (usable/unusable classification
            per damage state).
    """

    def __init__(
        self,
        fragility_provider,
        hazard_intensities,
        intensity_threshold,
        loss_provider,
        usability_model
    ):
        self.fragility_provider = fragility_provider
        self.hazard_intensities = hazard_intensities
        self.intensity_threshold = intensity_threshold
        self.loss_provider = loss_provider
        self.usability_model = usability_model

    def update_df(self, exposure_df):
        """
        Runs the update for each row of the input exposure model ('exposure_df').

        If self.usability_model.data is not None, the updating of 'cum_usability' is carried out
        in this method, by calling 'classify_updated_exposure_by_usability'.

        Args:
        exposure_df (Pandas DataFrame):
            DataFrame with one row per exposure asset (a number of buildings of a particular
            building class, in a particular damage state, at a particular location) and the
            following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets.
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.

        Returns:
            updated_exposure_and_losses (Pandas DataFrame):
                DataFrame with one row per (updated) exposure asset. The number of rows of
                'updated_exposure_and_losses' is equal to or larger than the number of rows of
                the input 'exposure_df', as each row of 'exposure_df' may remain in the same
                damage state or transition to a new one, and each of these possible paths
                becomes a new exposed asset. It contains the following columns:
                    "building_id" (str):
                        ID of the exposure polygon that the asset belongs to. One exposure polygon
                        (i.e., a geographic area) can contain several assets.
                    "taxonomy" (str):
                        Building class of the asset.
                    "initial_damage" (int):
                        Initial damage state of the asset, as an integer.
                    "final_damage" (int):
                        Final damage state of the asset, as an integer.
                    "number" (float):
                        Number of buildings in the asset.
                    "replacement_cost_tot" (float):
                        Total replacement cost of all the buildings in the asset. The replacement
                        cost per building is equal to "replacement_cost_tot"/"number".
                    "ppl_census" (float):
                        Total number of people who normally occupy all the buildings in the asset,
                        independent of the time of the day or other factors. The number of people
                        per building is equal to "ppl_census"/"number".
                    "incremental_loss" (float):
                        Economic loss associated with the asset calculated in the current run of
                        this function.
                    "cum_loss_value" (float):
                        Economic loss associated with the asset from a previously-run calculation
                        (i.e., a hazardous event that occurred before) plus the incremental loss
                        calculated in this function (by calling 'compute_loss').
                    "cum_usability" (int):
                        If self.usability_model.data is not None: Usability assessment from the
                            current calculation, accounting for the usability status from
                            previous calculations: 0 if unusable, 1 if usable.
                        If self.usability_model.data is None: Usability assessment from a
                            previously-run calculation, as in the input 'exposure_df': 0 if
                            unusable, 1 if usable.
                    "transition" (bool):
                        True if the asset has changed damage state, False if it has not.
        """
        # If exposure_df is empty return None (otherwise "apply" would return an empty
        # GeoDataFrame with the columns of the input.
        if exposure_df.empty:
            return None

        # Split input 'exposure_df' into rows for which damage needs to be calculated and rows
        # for which not
        need_to_run = pd.Series([
            self.hazard_intensities.loc[bdg_id, "run"] for bdg_id in exposure_df["building_id"]
        ])

        exposure_df_run = exposure_df.loc[need_to_run].copy()

        exposure_df_not_run = exposure_df.loc[~need_to_run].copy()
        exposure_df_not_run["final_damage"] = exposure_df_not_run["initial_damage"].copy()
        exposure_df_not_run["incremental_loss"] = [
            0.0 for i in range(exposure_df_not_run.shape[0])
        ]
        exposure_df_not_run["transition"] = [False for i in range(exposure_df_not_run.shape[0])]

        # Go one by one each of the exposure polygons (i.e., "building_id") of 'exposure_df_run'
        all_updated_exposure_bdg_id = []
        bdg_ids_to_run = exposure_df_run["building_id"].unique()

        for bdg_id in bdg_ids_to_run:
            # Retrieve assets of this building_id
            exposure_bdg_id = exposure_df_run[exposure_df_run.building_id == bdg_id]
            # Calculate new damage, incremental and cumulative losses
            updated_exposure_bdg_id = self.update_exposure_polygon(
                exposure_bdg_id,
                self.hazard_intensities.loc[bdg_id, :],
                self.intensity_threshold
            )

            all_updated_exposure_bdg_id.extend(updated_exposure_bdg_id.to_dict(orient="records"))

        updated_exposure_df = pd.DataFrame(all_updated_exposure_bdg_id)
        updated_exposure_df.reset_index(inplace=True)
        updated_exposure_df.drop(columns=["index"], inplace=True)

        updated_exposure_df = pd.concat((updated_exposure_df, exposure_df_not_run))
        updated_exposure_df.reset_index(inplace=True)
        updated_exposure_df.drop(columns=["index"], inplace=True)

        # if one of the two DFs concatenated is empty, "transition" is no longer boolean
        updated_exposure_df["transition"] = updated_exposure_df["transition"].astype(bool)

        # Update usability (only for assets that transition, accounted for in the sub-method)
        # (if self.usability_model is None, then "cum_usability" is not updated and the values
        # in the input exposure model from the previous calculation are kept)
        if self.usability_model.data is not None:
            updated_exposure_df = classify_updated_exposure_by_usability(
                updated_exposure_df, self.usability_model.data
            )

        if self.loss_provider is None:
            if "cum_loss_value" in updated_exposure_df.columns:
                del updated_exposure_df["cum_loss_value"]
            if "incremental_loss" in updated_exposure_df.columns:
                del updated_exposure_df["incremental_loss"]

        return updated_exposure_df

    def update_exposure_polygon(self, exposure, intensity_values, intensity_threshold):
        """
        Updates a set of assets of the exposure model associated with one exposure polygon.

        If self.loss_provider is not None, economic losses are calculated.

        Args:
            exposure (Pandas DataFrame):
                Exposure associated with one "building_id".
            intensity_values (Pandas Series):
                Values of hazard intensity associated with the exposure polygon that the input
                'exposure' corresponds to. The labels of the Series are the hazard intensity
                measure types.
            intensity_threshold (float):
                Threshold of hazard intensity, to be used so that if the intensity value at a
                target exposure point is smaller than the threshold, no further damage is
                assumed (and the detailed calculation is avoided).

        Returns:
            updated_exposure_and_losses (Pandas DataFrame):
                DataFrame with one row per (updated) exposure asset. The number of rows of
                'updated_exposure_and_losses' is equal to or larger than the number of rows of
                the input 'exposure', as each row of 'exposure' may remain in the same damage
                state or transition to a new one, and each of these possible paths becomes a new
                exposed asset. It contains the following columns:
                    "building_id" (str):
                        ID of the exposure polygon that the asset belongs to. One exposure polygon
                        (i.e., a geographic area) can contain several assets.
                    "taxonomy" (str):
                        Building class of the asset.
                    "initial_damage" (int):
                        Initial damage state of the asset, as an integer.
                    "final_damage" (int):
                        Final damage state of the asset, as an integer.
                    "number" (float):
                        Number of buildings in the asset.
                    "replacement_cost_tot" (float):
                        Total replacement cost of all the buildings in the asset. The replacement
                        cost per building is equal to "replacement_cost_tot"/"number".
                    "ppl_census" (float):
                        Total number of people who normally occupy all the buildings in the asset,
                        independent of the time of the day or other factors. The number of people
                        per building is equal to "ppl_census"/"number".
                    "incremental_loss" (float):
                        Economic loss associated with the asset calculated in the current run of
                        this function.
                    "cum_loss_value" (float):
                        Economic loss associated with the asset from a previously-run calculation
                        (i.e., a hazardous event that occurred before) plus the incremental loss
                        calculated in this function (by calling 'compute_loss').
                    "cum_usability" (int):
                        Usability assessment from a previously-run calculation: 0 if unusable, 1
                        if usable. (Same values as in input).
                    "transition" (bool):
                        True if the asset has changed damage state, False if it has not.
        """

        # Calculate new damage states (transitions) and update the exposure model
        updated_exposure = get_updated_exposure_and_transitions(
            exposure,
            intensity_values,
            intensity_threshold,
            self.fragility_provider
        )

        if self.loss_provider is None:
            return updated_exposure

        # Compute the incremental and cumulative economic losses
        updated_exposure_and_losses = compute_loss(
            updated_exposure,
            loss_provider=self.loss_provider,
            schema=self.fragility_provider.schema,
        )

        return updated_exposure_and_losses


def map_exposure(old_exposure, source_schema, target_schema, schema_mapper):
    """
    Function to map the exposure to another schema if necessary.

    The input 'expo' refers to one exposure polygon, which contains a series of building classes
    (taxonomy) with their own damage states.

    If the source building schema ('source_schema') and the target building schema
    ('target_schema') match, this function returns the same input exposure model ('expo').
    Otherwise, it uses the 'schema_mapper' to convert the building classes and damage states of
    the input expoure model ('expo') from their original 'source_schema' to the 'target_schema'.

    Args:
        old_exposure (Pandas DataFrame):
            DataFrame with one row per exposure asset (a number of buildings of a particular
            building class, in a particular damage state, at a particular location) and the
            following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets.
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.
        source_schema (string):
            Name of the source building schema, that is, the one used within the input
            'exposure'.
        target_schema (string):
            Name of the target building schema, that is, the one used by the
            'fragility_provider'.
        schema_mapper (SchemaMapper):
            Instance of SchemaMapper containing the compatibility matrices needed to map from
            one schema to another, both in terms of building taxonomies and damage scales.

    Returns:
        mapped_exposure (Pandas DataFrame):
            DataFrame with the same structure as 'old_exposure', and with each combination of
            taxonomy and damage state of 'old_exposure' converted from the 'source_schema' to
            the 'target_schema'. Its rows are ordered as per the contents of the following
            columns (in order of consideration for sorting): "building_id", "taxonomy",
            "initial_damage" and "cum_usability". The "building_id"s of 'old_exposure' are kept.
    """

    if source_schema == target_schema:
        return old_exposure

    # Identify unique combinations of "taxonomy" and "initial_damage"
    unique_dmgd_bdg_classes = old_exposure[["taxonomy", "initial_damage"]].drop_duplicates(
        ignore_index=True
    )

    # Do the mapping for those unique combinations of "taxonomy" and "initial_damage"
    all_mappings = []
    for i in unique_dmgd_bdg_classes.index:
        old_taxonomy = unique_dmgd_bdg_classes.loc[i, "taxonomy"]
        old_dmg_state = unique_dmgd_bdg_classes.loc[i, "initial_damage"]

        mapping_results = schema_mapper._map_schema_1(
            source_taxonomy=old_taxonomy,
            source_damage_state=old_dmg_state,
            source_schema=source_schema,
            target_schema=target_schema,
        ) # "mapping_results" is a list of SchemaMapperResult objects

        # Vectorise results
        new_taxonomies = []
        new_dmg_states = []
        new_proportions = []

        for result_object in mapping_results:
            new_taxonomies.append(result_object.taxonomy)
            new_dmg_states.append(result_object.damage_state)
            new_proportions.append(result_object.n_buildings)

        all_mappings.append(
            {
                "taxonomy": np.array(new_taxonomies, dtype=object),
                "damage_state": np.array(new_dmg_states, dtype=object),
                "proportions": np.array(new_proportions)
            }
        )
    unique_dmgd_bdg_classes["mapping"] = all_mappings

    all_mapped_sub_exposure = {}
    all_mapped_sub_exposure["building_id"] = []
    all_mapped_sub_exposure["taxonomy"] = []
    all_mapped_sub_exposure["initial_damage"] = []
    all_mapped_sub_exposure["number"] = []
    all_mapped_sub_exposure["replacement_cost_tot"] = []
    all_mapped_sub_exposure["ppl_census"] = []
    all_mapped_sub_exposure["cum_loss_value"] = []
    all_mapped_sub_exposure["cum_usability"] = []

    # Go one by one each unique combination of "taxonomy" and "initial_damage" and "cum_usability"
    for i in unique_dmgd_bdg_classes.index:
        old_taxonomy = unique_dmgd_bdg_classes.loc[i, "taxonomy"]
        old_dmg_state = unique_dmgd_bdg_classes.loc[i, "initial_damage"]
        mapping = unique_dmgd_bdg_classes.loc[i, "mapping"]

        # Retrieve rows of "old_exposure" with this combination ("taxonomy" & "initial_damage")
        sub_exposure = old_exposure[
            (old_exposure["taxonomy"]==old_taxonomy) &
            (old_exposure["initial_damage"]==old_dmg_state)
        ]

        new_number = np.outer(
            sub_exposure["number"].to_numpy(), mapping["proportions"]
        ).flatten()
        # for inputs a & b, the order of "new_number" is: a1*b1, a1*b2, a1*b3...
        # i.e. buildings of the same building_id will end up grouped together

        new_costs = np.outer(
            sub_exposure["replacement_cost_tot"].to_numpy(), mapping["proportions"]
        ).flatten()

        new_ppl_census = np.outer(
            sub_exposure["ppl_census"].to_numpy(), mapping["proportions"]
        ).flatten()

        # Split exising cum_loss_value proportionally to "proportions"
        new_cum_loss_values = np.outer(
            sub_exposure["cum_loss_value"].to_numpy(), mapping["proportions"]
        ).flatten()

        new_taxonomies = np.outer(
            np.ones(sub_exposure.shape[0], dtype=int), mapping["taxonomy"]
        ).flatten()

        new_dmg_states = np.outer(
            np.ones(sub_exposure.shape[0], dtype=int), mapping["damage_state"]
        ).flatten()

        new_building_id = np.outer(
            sub_exposure["building_id"], np.ones(len(mapping["proportions"]), dtype=int)
        ).flatten()

        new_cum_usability = np.outer(
            sub_exposure["cum_usability"], np.ones(len(mapping["proportions"]), dtype="int8")
        ).flatten()

        all_mapped_sub_exposure["building_id"].extend(new_building_id)
        all_mapped_sub_exposure["taxonomy"].extend(new_taxonomies)
        all_mapped_sub_exposure["initial_damage"].extend(new_dmg_states)
        all_mapped_sub_exposure["number"].extend(new_number)
        all_mapped_sub_exposure["replacement_cost_tot"].extend(new_costs)
        all_mapped_sub_exposure["ppl_census"].extend(new_ppl_census)
        all_mapped_sub_exposure["cum_loss_value"].extend(new_cum_loss_values)
        all_mapped_sub_exposure["cum_usability"].extend(new_cum_usability)

    mapped_exposure = pd.DataFrame(all_mapped_sub_exposure)

    # Group combinations of ["building_id", "taxonomy", "initial_damage", "cum_usability"]
    # There might be several rows repeating a combination due to them stemming from different
    # assets of the input 'old_exposure'
    mapped_exposure = mapped_exposure.groupby(
        ["building_id", "taxonomy", "initial_damage", "cum_usability"]
    ).agg(
        {
            "number": "sum",
            "replacement_cost_tot": "sum",
            "ppl_census": "sum",
            "cum_loss_value": "sum"
        }
    )
    mapped_exposure.reset_index(inplace=True)

    return mapped_exposure


def get_updated_exposure_and_transitions(
    exposure, intensity_values, intensity_threshold, fragility_provider
):
    """
    This function returns the exposure with damage updated due to the current run of the
    software for one exposure polygon whose building information is contained in the input
    'exposure' and for which the location of the nearest-neighbour hazard point is
    'intensity_position'. The replacement costs and previous losses associated with each asset
    (i.e., each row of the input 'exposure') are distributed proportionally to the probability
    of occurrence of each new damage state.

    The intensity measures are retrieved from the 'intensity_provider' at the position defined
    by 'intensity_position'.

    The 'cum_usability' column of 'exposure' is NOT updated here. The output 'cum_usability'
    from this method is the same as in the input.

    Args:
        exposure (Pandas DataFrame):
            DataFrame with one row per exposure asset of one exposure polygon, which is defined
            by a "building_id" and whose hazard will be retrieved at 'intensity_position', and
            the following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets.
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.
        intensity_values (Pandas Series):
            Values of hazard intensity associated with the exposure polygon that the input
            'exposure' corresponds to. The labels of the Series are the hazard intensity
            measure types.
        intensity_threshold (float):
            Threshold of hazard intensity, to be used so that if the intensity value at a target
            exposure point is smaller than the threshold, no further damage is assumed.
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.

    Returns:
        result_expo (Pandas DataFrame):
            DataFrame with the same base structure as the input 'exposure', but with all
            building classes and damage state combinations updated as per the input hazard
            ('intensity_provider') and fragility ('fragility_provider'). I.e., these are the
            post-event damage states. Additional columns with respecto to 'exposure'):
                "final_damage" (int):
                    Final damage state of the asset, as an integer.
                "transition" (bool):
                    True if the asset has changed damage state, False if it has not.
    """

    # Do not perform any operations if there are no buildings
    if exposure["number"].sum() < 1E-10:  # <1E-10 taken as zero
        result_expo = deepcopy(exposure)
        result_expo["final_damage"] = exposure["initial_damage"]
        result_expo["transition"] = [False for i in range(result_expo.shape[0])]
        # "cum_usability" remains the same
        return result_expo

    aux_result_expo = {}
    aux_result_expo["building_id"] = []
    aux_result_expo["taxonomy"] = []
    aux_result_expo["initial_damage"] = []
    aux_result_expo["final_damage"] = []
    aux_result_expo["number"] = []
    aux_result_expo["replacement_cost_tot"] = []
    aux_result_expo["ppl_census"] = []
    aux_result_expo["cum_loss_value"] = []
    aux_result_expo["cum_usability"] = []

    for row in exposure.index:
        n_bdgs = exposure.loc[row, "number"]
        old_damage_state = exposure.loc[row, "initial_damage"]
        taxonomy = exposure.loc[row, "taxonomy"]
        replacement_cost = exposure.loc[row, "replacement_cost_tot"]
        ppl_census = exposure.loc[row, "ppl_census"]
        cum_loss_value = exposure.loc[row, "cum_loss_value"]
        cum_usability = exposure.loc[row, "cum_usability"]
        building_id = exposure.loc[row, "building_id"]

        # Retrieve damage states that are worse than 'old_damage_state'
        # (it also returns the fragility curve corresponding to this damage transition)
        damage_states_to_care = get_sorted_damage_states(
            fragility_provider, taxonomy, old_damage_state
        )

        # Ignore all worse damage states if the intensity value is smaller than
        # 'intensity_threshold'
        if len(damage_states_to_care) > 0:  # i.e. there are worse damage states to consider
            intensity_val = intensity_values[damage_states_to_care[0].intensity_field]
            if intensity_val < intensity_threshold:
                damage_states_to_care = []

        # Initialise Probability of Exceedance (PoE) array
        # poes[-1] = 1, i.e. PoE the current damage state
        poes = np.ones(len(damage_states_to_care)+1)

        final_damage_states = []

        for position, single_damage_state in enumerate(damage_states_to_care):
            # position != damage state value
            # position=0 belongs to the worst damage state
            # position=-1 will belong to the initial damage state, with PoE=1
            poes[position] = single_damage_state.get_probability_for_intensity(
                intensity_values
            )

            final_damage_states.append(single_damage_state.to_state)

        final_damage_states.append(old_damage_state)

        # Probabilities of occurrence (the position order is the same as in poes)
        poos = np.zeros_like(poes)
        poos[0] = poes[0]  # first element is the worst damage state, for which PoE=PoO
        poos[1:] = np.flip(np.flip(poes)[:-1] - np.flip(poes)[1:])

        aux_result_expo["building_id"].extend([building_id for i in range(poos.shape[0])])
        aux_result_expo["taxonomy"].extend([taxonomy for i in range(poos.shape[0])])
        aux_result_expo["initial_damage"].extend([old_damage_state for i in range(poos.shape[0])])
        aux_result_expo["final_damage"].extend(final_damage_states)
        aux_result_expo["number"].extend(list(n_bdgs * poos))
        aux_result_expo["replacement_cost_tot"].extend(list(replacement_cost * poos))
        aux_result_expo["ppl_census"].extend(list(ppl_census * poos))
        aux_result_expo["cum_loss_value"].extend(list(cum_loss_value * poos))
        # at this stage, keep on carrying the previous-run usability
        aux_result_expo["cum_usability"].extend([cum_usability for i in range(poos.shape[0])])

    result_expo = pd.DataFrame(aux_result_expo)

    result_expo["initial_damage"] = result_expo["initial_damage"].astype(int)
    result_expo["final_damage"] = result_expo["final_damage"].astype(int)

    # Group duplicate combinations, if duplicates exist
    criteria_cols = [
        "building_id", "taxonomy", "initial_damage", "final_damage", "cum_usability"
    ]
    unique_combis = result_expo[criteria_cols].drop_duplicates()  # index doesn't matter

    if unique_combis.shape[0] < result_expo.shape[0]:
        # There are duplicate combinations that can be grouped
        result_expo = result_expo.groupby(criteria_cols).agg(
            {
                "number": "sum",
                "replacement_cost_tot": "sum",
                "ppl_census": "sum",
                "cum_loss_value": "sum"
            }
        )
        result_expo.reset_index(inplace=True)
    else:
        result_expo.reset_index(inplace=True)
        result_expo = result_expo.drop(columns=["index"])

    result_expo["transition"] = (result_expo["initial_damage"] != result_expo["final_damage"])

    return result_expo


def classify_updated_exposure_by_usability(exposure, usability):
    """
    This method updates the 'cum_usability' column of 'exposure', as a function of the usability
    model 'usability'.

    The update is as follows:
    - If the asset does not transition (column 'transition' is False), the input values of
    'cum_usability' are kept (this method introduces no change to those assets).
    - If the asset does transition (column 'transition' is True), the values of 'cum_usability'
    are updated. Any asset remains usable only if it was usable before (input 'cum_usability')
    and is assessed as usable based on the input 'final_damage' and 'usability' (i.e., any asset
    is unusable if assessed as unusable by at least one of the two assessments, the one from the
    previous calculation and the one from the current calculation).

    Args:
        exposure (Pandas DataFrame):
            DataFrame with one row per exposure asset (a number of buildings of a particular
            building class, in a particular damage state, at a particular location) and the
            following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets.
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "final_damage" (int):
                    Final damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "cum_usability" (int):
                    Usability assessment from a previously-run calculation: 0 if unusable, 1
                    if usable.
                "transition" (bool):
                    True if the asset has changed damage state, False if it has not.
        usability (Pandas DataFrame):
            DataFrame with index "damage_state", in terms of integers and one column labelled
            "usable" (bool), containing True/False.

    Returns:
        exposure (Pandas DataFrame):
            Same DataFrame as input, with an updated 'cum_usability' column.
    """

    # New usability of assets that transition
    new_usability_transitioned = np.array([
        usability.loc[final_damage, "usable"]
        for final_damage in exposure[exposure.transition]["final_damage"]
    ]).astype("int8") # 0 if unusable, 1 if usable

    # Assets that do not transition keep the usability assessment from the previous calculation
    # Nothing to be done here, as it would be overwriting with the same values

    # Assets that transition: currently usable only if usable now and before\
    exposure.loc[exposure.index[exposure.transition], "cum_usability"] = (
        exposure[exposure.transition]["cum_usability"] * new_usability_transitioned
    )  # product of previous usability and new usability (will only be 1 if both are 1)

    return exposure


def compute_loss(updated_exposure, loss_provider, schema):
    """
    This function calculates the economic losses associated with the transitions from the
    "initial_damage" states to the "final_damage" states in the input 'updated_exposure', as per
    the consequence model (loss ratios per damage state) contained in 'loss_provider' for the
    corresponding 'schema'.

    Assets (rows of 'updated_exposure') for which the damage state remains the same have zero
    incremental loss and their cumulative loss remains the same as in the input.

    Assets (rows of 'updated_exposure') for which the damage state gets worse have a non-zero
    incremental loss, calculated as:
        incremental loss = replacement cost * [LR(new damage state) - LR(previous_damage state)]

    As pre-existing cumulative loss values (i.e., the "cum_loss_value" column of the input
    'updated_exposure') may have been calculated with a different consequence model than the one
    of the current run, it is possible to calculate new cumulative loss values that are larger
    than 100% the replacement cost of the building. For this reason, this function checks if
    this happens and adjusts these cases by setting the maximum cumulative loss value to be
    equal to 100% the replacement cost, and back-calculating the associated incremental loss.
    This assumption requires that the consequence model contained in 'loss_provider' contains
    only loss ratios equal to or smaller than 100% (i.e., no possibility of accounting for
    additional costs due to, for e.g., demolition).

    Args:
        updated_exposure (Pandas DataFrame):
            DataFrame with one row per exposure asset and the following columns:
                "building_id" (str):
                    ID of the exposure polygon that the asset belongs to. One exposure polygon
                    (i.e., a geographic area) can contain several assets.
                "taxonomy" (str):
                    Building class of the asset.
                "initial_damage" (int):
                    Initial damage state of the asset, as an integer.
                "final_damage" (int):
                    Final damage state of the asset, as an integer.
                "number" (float):
                    Number of buildings in the asset.
                "replacement_cost_tot" (float):
                    Total replacement cost of all the buildings in the asset. The replacement
                    cost per building is equal to "replacement_cost_tot"/"number".
                "ppl_census" (float):
                    Total number of people who normally occupy all the buildings in the asset,
                    independent of the time of the day or other factors. The number of people
                    per building is equal to "ppl_census"/"number".
                "cum_loss_value" (float):
                    Economic loss associated with the asset from a previously-run calculation
                    (i.e., a hazardous event that occurred before).
                "transition" (bool):
                    True if the asset has changed damage state, False if it has not.
        loss_provider (LossProvider):
            Instance of LossProvider to access the economic consequence model (loss ratios per
            damage state) and building replacement costs.
        schema (str):
            Name of the schema associated with the consequence model of 'loss_provider'.

    Returns:
        updated_exposure_with_losses (Pandas DataFrame):
            The same as the input 'updated_exposure', with an additional column
            'incremental_loss', which contains the incremental losses due to the current hazard,
            and with updated values of 'cum_loss_value' (= previously-existing values of
            'cum_loss_value' plus new 'incremental_loss').
    """

    # Split the input into rows that transition and rows that do not
    transitions = updated_exposure[updated_exposure.transition].copy()
    nontransitions = updated_exposure[~ updated_exposure.transition].copy()
    nontransitions["incremental_loss"] = np.zeros(nontransitions.shape[0])
    #nontransitions["cum_loss_value"] remains the same

    # Calculate incremental losses for rows that transition
    incremental_loss_ratios = np.zeros(transitions.shape[0])

    for i, row in enumerate(transitions.index):
        incremental_loss_ratios[i] = loss_provider.get_incremental_loss_ratio(
            schema=schema,
            from_damage_state=transitions.loc[row, "initial_damage"],
            to_damage_state=transitions.loc[row, "final_damage"],
        )

    # Calculate incremental loss
    transitions["incremental_loss"] = (
        transitions["replacement_cost_tot"] * incremental_loss_ratios
    )

    # Make sure that no new cumulative loss is larger than the replacement cost of the building
    previous_cum_loss_value = transitions["cum_loss_value"].to_numpy()
    transitions["cum_loss_value"] = (
        transitions["cum_loss_value"] + transitions["incremental_loss"]
    )
    which_exceed_replacement_cost = (
        transitions.cum_loss_value > transitions.replacement_cost_tot
    )  # rows in which the new cumulative loss is larger than the replacement cost

    if which_exceed_replacement_cost.any():
        # Adjust rows that need adjustment
        transitions.loc[which_exceed_replacement_cost, "incremental_loss"] = (
            transitions.loc[which_exceed_replacement_cost, "replacement_cost_tot"] -
            previous_cum_loss_value[which_exceed_replacement_cost]
        ) # new incremental loss is the replacement cost minus the pre-existing cumulative loss
        transitions.loc[which_exceed_replacement_cost, "cum_loss_value"] = (
            transitions.loc[which_exceed_replacement_cost, "replacement_cost_tot"]
        )  # new cumulative loss is the replacement cost

    # Join the transition and non-transition rows back together
    updated_exposure_with_losses = pd.concat(
        (transitions, nontransitions)
    )
    # Sort by the original indices (the same as in input 'updated_exposure')
    updated_exposure_with_losses.sort_index(inplace=True)

    return updated_exposure_with_losses


def get_sorted_damage_states(fragility_provider, taxonomy, old_damage_state):
    """
    Return the sorted damage states that are above (i.e., more damage) than the input one
    ('old_damage_state').

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Args:
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.
        taxonomy (str):
            Building class for which to retrieve the damage states, as named in the
            'fragility_provider'.
        old_damage_state (int):
            Damage state, as a number only (i.e., 1, not "D1").

    Returns:
        damage_states_to_care (list of DamageState objects):
            List with all damage states that are worse (i.e., more damage) than the input
            'old_damage_state', sorted in descending order (i.e., worst damage first).
    """

    damage_states = fragility_provider.get_damage_states_for_taxonomy(taxonomy)

    damage_states_to_care = [
        ds
        for ds in damage_states
        if ds.from_state == old_damage_state and ds.to_state > old_damage_state
    ]

    damage_states_to_care.sort(key=sort_by_to_damage_state_desc)

    return damage_states_to_care


def sort_by_to_damage_state_desc(damage_state):
    """
    Sort the damage states with the highest first.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """
    return damage_state.to_state * -1
