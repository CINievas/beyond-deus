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

import collections
import ctypes
import pandas
import geopandas
import numpy as np
from copy import deepcopy
from beyonddeus.loss import combine_losses


ExpoKey = collections.namedtuple("ExpoKey", ["taxonomy", "damage_state"])

TransitionKey = collections.namedtuple(
    "TransitionKey",
    ["taxonomy", "from_damage_state", "to_damage_state"],
)


def zero():
    """Return 0. Needed as a function to pass as argument to collections.defaultdict()"""
    return 0


def read_exposure(filename):
    """
    Function to read the exposure from the file.

    Function copied and adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """
    gdf = geopandas.read_file(filename)
    gdf["gid"] = gdf["gid"].astype(str)  # Read the ID of the cell as a string

    return gdf


def str_Dx_to_int(damage_state_with_d_prefix):
    """
    Function to convert damage state name strings (e.g. "D2") into integers (e.g., 2).

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """
    return int(damage_state_with_d_prefix[1:])


def int_x_to_str_Dx(damage_state_without_d_prefix):
    """
    Function to convert damage states integers (e.g., 2) into name strings (e.g. "D2").

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """
    return "D" + str(damage_state_without_d_prefix)


def empty_transition_values():
    """
    Return an empty transition value.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """
    return TransitionValues(0, 0)


class ExpoValues(ctypes.Structure):
    """
    Class to store the information for the values of an expo dict.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """

    _fields_ = [
        ("buildings", ctypes.c_double),
        ("population", ctypes.c_double),
        ("replcostbdg", ctypes.c_double),
    ]

    def __repr__(self):
        return (
            "ExpoValues("
            + "buildings={0}, population={1}, replcostbdg={2})".format(
                repr(self.buildings),
                repr(self.population),
                repr(self.replcostbdg),
            )
        )


def empty_expo_values():
    """
    Function copied and adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Return an empty expo value.
    """
    return ExpoValues(0, 0, 0)


class TransitionValues(ctypes.Structure):
    """
    Class to store the keys in the transition dict.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """

    _fields_ = [
        ("buildings", ctypes.c_double),
        ("replcostbdg", ctypes.c_double),
    ]

    def __repr__(self):
        return "TransitionValues(buildings={0}, replcostbdg={1})".format(
            repr(self.buildings), repr(self.replcostbdg)
        )


def update_exposure_transitions_and_losses(
    source_schema,
    target_schema,
    exposure,
    schema_mapper,
    intensity_provider,
    fragility_provider,
    loss_provider,
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
        source_schema (string):
            Name of the source building schema, that is, the one used within the input
            'exposure'.
        target_schema (string):
            Name of the target building schema, that is, the one used by the
            'fragility_provider'.
        exposure (GeoPandas GeoDataFrame):
            GeoDataFrame with one row per exposure polygon and the following columns:
                "gid":
                    ID of the exposure polygon.
                "expo":
                    Dictionary in string format, with the following keys and contents:
                        "Taxonomy":
                            List with the names of the building classes present in the exposure
                            polygon. If the exposure polygon contains instances of the same
                            building class but different damage states, the name of the building
                            classes needs to be repeated here.
                        "Damage":
                            List with the names of the damage states associated with the
                            building classes listed in "Taxonomy".
                        "Buildings":
                            List with the number of buildings in exposure polygon associated
                            with each element of "Taxonomy" and "Damage".
                        "Population":
                            To be fully implemented.
                        "ReplCostPerBdg":
                            To be fully implemented.
                    "Taxonomy", "Damage" and "Buildings" must all be of the same length.
                    Example of an "expo" cell:
                        "{ "Taxonomy": [ "bdg_class_1", "bdg_class_2" ],
                        "Damage": [ "D0", "D0" ],
                        "Buildings": [ 2.5, 5.0 ] }"
                "geometry":
                    Geometry of the exposure polygon.
                "cum_loss_value" (optional, float):
                    Economic losses associated with the exposure polygon from a previously-run
                    hazard.
        schema_mapper (SchemaMapper):
            Instance of SchemaMapper containing the compatibility matrices needed to map from
            one schema to another, both in terms of building taxonomies and damage scales.
        intensity_provider (IntensityProvider):
            Instance of IntensityProvider for retrieving the hazard intensities at a location.
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.
        loss_provider (LossProvider):
            Instance of LossProvider to access the economic consequence model (loss ratios per
            damage state) and building replacement costs.

    Returns:
        updated_exposure (GeoPandas GeoDataFrame):
            GeoDataFrame with one row per exposure polygon and the following columns:
                "gid":
                    ID of the exposure polygon.
                "expo":
                    Dictionary in string format, with the same keys and types of contents as in
                    the input 'exposure' (but with updated damage states), all of the same length: 
                        "Taxonomy"
                        "Damage"
                        "Buildings"
                "geometry":
                    Geometry of the exposure polygon.
                "schema":
                    Name of the target building schema ('target_schema'), which is the schema to
                    which the contents of expo["Taxonomy"] belong in 'updated_exposure'.
                "transitions":
                    Dictionary in string format, with the following keys and contents:
                        "Taxonomy":
                            List with the names of the building classes.
                        "from_damage_state":
                            List with the initial damage state of the transition.
                        "to_damage_state":
                            List with the final damage state of the transition.
                        "n_buildings":
                            List with the number of buildings in exposure polygon associated
                            with each element of "Taxonomy", "from_damage_state" and
                            "to_damage_state".
                        "replacement_costs_usd_bdg":
                            Replacement costs.
                    Example of a "transitions" cell:
                        {'taxonomy': ['bdg_class_1', 'bdg_class_1', 'bdg_class_1', 'bdg_class_1',
                                      'bdg_class_2', 'bdg_class_2', 'bdg_class_2', 'bdg_class_2'],
                         'from_damage_state': [0, 0, 0, 0, 0, 0, 0, 0],
                         'to_damage_state': [4, 3, 2, 1, 4, 3, 2, 1],
                         'n_buildings': [5.647e-08, 1.815e-07, 1.071e-06, 3.631e-05,
                                         1.129e-07, 3.630e-07, 2.143e-06, 7.262e-05],
                         'replacement_costs_usd_bdg': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
                "loss_value":
                    Value of the buildings in the exposure polygon that has been lost due to the
                    hazard intensities in the 'intensity_provider'.
                "cum_loss_value" (float):
                    Economic losses associated with the exposure polygon from a previously-run
                    hazard plus those calculated from the current hazard ("loss_value").
    """
    updater = Updater(
        source_schema,
        target_schema,
        fragility_provider,
        schema_mapper,
        intensity_provider,
        loss_provider,
    )

    updated_exposure = updater.update_df(exposure)

    # This function can be used to parallelise the updating of the exposure model
    # Right now, it is not parallelised, so it just calls the Updater class and
    # the update_df method of the class.

    return updated_exposure


class Updater:
    """
    Class and methods copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class used for running updates on the exposure.

    Attributes:
        source_schema (string):
            Name of the source building schema, that is, the one used within the input
            'exposure'.
        target_schema (string):
            Name of the target building schema, that is, the one used by the
            'fragility_provider'.
        exposure (GeoPandas GeoDataFrame):
            GeoDataFrame with one row per exposure polygon and the following columns:
                "gid":
                    ID of the exposure polygon.
                "expo":
                    Dictionary in string format, with the following keys and contents:
                        "Taxonomy":
                            List with the names of the building classes present in the exposure
                            polygon. If the exposure polygon contains instances of the same
                            building class but different damage states, the name of the building
                            classes needs to be repeated here.
                        "Damage":
                            List with the names of the damage states associated with the
                            building classes listed in "Taxonomy".
                        "Buildings":
                            List with the number of buildings in exposure polygon associated
                            with each element of "Taxonomy" and "Damage".
                    "Taxonomy", "Damage" and "Buildings" must all be of the same length.
                    Example of an "expo" cell:
                        "{ "Taxonomy": [ "bdg_class_1", "bdg_class_2" ],
                        "Damage": [ "D0", "D0" ],
                        "Buildings": [ 2.5, 5.0 ] }"
                "geometry":
                    Geometry of the exposure polygon.
                "cum_loss_value" (optional, float):
                    Economic losses associated with the exposure polygon from a previously-run
                    hazard.
        schema_mapper (SchemaMapper):
            Instance of SchemaMapper containing the compatibility matrices needed to map from
            one schema to another, both in terms of building taxonomies and damage scales.
        intensity_provider (IntensityProvider):
            Instance of IntensityProvider for retrieving the hazard intensities at a location.
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.
        loss_provider (LossProvider):
            Instance of LossProvider to access the economic consequence model (loss ratios per
            damage state) and building replacement costs.
    """

    def __init__(
        self,
        source_schema,
        target_schema,
        fragility_provider,
        schema_mapper,
        intensity_provider,
        loss_provider,
    ):
        self.source_schema = source_schema
        self.target_schema = target_schema
        self.fragility_provider = fragility_provider
        self.schema_mapper = schema_mapper
        self.intensity_provider = intensity_provider
        self.loss_provider = loss_provider

    def update_df(self, exposure_df):
        """
        Runs the update for each row of the input exposure model ('exposure_df').

        Args:
        exposure_df (GeoPandas GeoDataFrame):
            GeoDataFrame with one row per exposure polygon and the following columns:
                "gid":
                    ID of the exposure polygon.
                "expo":
                    Dictionary in string format, with the following keys and contents:
                        "Taxonomy":
                            List with the names of the building classes present in the exposure
                            polygon. If the exposure polygon contains instances of the same
                            building class but different damage states, the name of the building
                            classes needs to be repeated here.
                        "Damage":
                            List with the names of the damage states associated with the
                            building classes listed in "Taxonomy".
                        "Buildings":
                            List with the number of buildings in exposure polygon associated
                            with each element of "Taxonomy" and "Damage".
                    "Taxonomy", "Damage" and "Buildings" must all be of the same length.
                    Example of an "expo" cell:
                        "{ "Taxonomy": [ "bdg_class_1", "bdg_class_2" ],
                        "Damage": [ "D0", "D0" ],
                        "Buildings": [ 2.5, 5.0 ] }"
                "geometry":
                    Geometry of the exposure polygon.
                "cum_loss_value" (optional, float):
                    Economic losses associated with the exposure polygon from a previously-run
                    hazard.
        """
        # If exposure_df is empty return None (otherwise "apply" would return an empty
        # GeoDataFrame with the columns of the input.
        if exposure_df.empty:
            return None

        list_of_series = exposure_df.apply(self.update_series, axis=1)

        return geopandas.GeoDataFrame(list_of_series)

    def update_series(self, series):
        """
        Updates one row of the exposure model (input as 'series').

        Args:
            series (GeoPandas series):
                One row of 'exposure_df' (see args for 'update_df' method).

        Returns:
            GeoPandas series, the updated version of the input 'series', with the following
            columns:
                "gid":
                    ID of the exposure polygon.
                "expo":
                    Dictionary in string format, with the same keys and types of contents as in
                    the input 'series' (but with updated damage states), all of the same length: 
                        "Taxonomy"
                        "Damage"
                        "Buildings"
                "geometry":
                    Geometry of the exposure polygon.
                "schema":
                    Name of the target building schema ('target_schema'), which is the schema to
                    which the contents of expo["Taxonomy"] belong in 'updated_exposure'.
                "transitions":
                    Dictionary in string format, with the following keys and contents:
                        "Taxonomy":
                            List with the names of the building classes.
                        "from_damage_state":
                            List with the initial damage state of the transition.
                        "to_damage_state":
                            List with the final damage state of the transition.
                        "n_buildings":
                            List with the number of buildings in exposure polygon associated
                            with each element of "Taxonomy", "from_damage_state" and
                            "to_damage_state".
                        "replacement_costs_usd_bdg":
                            Replacement costs.
                    Example of a "transitions" cell:
                        {'taxonomy': ['bdg_class_1', 'bdg_class_1', 'bdg_class_1', 'bdg_class_1',
                                      'bdg_class_2', 'bdg_class_2', 'bdg_class_2', 'bdg_class_2'],
                         'from_damage_state': [0, 0, 0, 0, 0, 0, 0, 0],
                         'to_damage_state': [4, 3, 2, 1, 4, 3, 2, 1],
                         'n_buildings': [5.647e-08, 1.815e-07, 1.071e-06, 3.631e-05,
                                         1.129e-07, 3.630e-07, 2.143e-06, 7.262e-05],
                         'replacement_costs_usd_bdg': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
                "loss_value":
                    Value of the buildings in the exposure polygon that has been lost due to the
                    hazard intensities in the 'intensity_provider'.
                "cum_loss_value" (float):
                    Economic losses associated with the exposure polygon from a previously-run
                    hazard plus those calculated from the current hazard ("loss_value").
        """
        # Prepare the input
        # Convert the existing expo to an exposure dict (ExpoKeys & ExpoValues)
        old_exposure = expo_from_series_to_dict(eval(series.expo))

        # Map the building classes from the source schema (the one of "old exposure")
        # to the target schema (the one of the fragility model)
        mapped_exposure = map_exposure(
            expo=old_exposure,
            source_schema=self.source_schema,
            target_schema=self.target_schema,
            schema_mapper=self.schema_mapper,
        )

        # Calculate new damage states (transitions) and update the exposure model
        (
            updated_exposure,
            transitions,
        ) = get_updated_exposure_and_transitions(
            geometry=series.geometry,
            expo=mapped_exposure,
            intensity_provider=self.intensity_provider,
            fragility_provider=self.fragility_provider,
        )

        # Compute the loss of all the transitions in the exposure polygon
        # ('loss_value' is the total loss for the whole exposure polygon)
        loss_value = compute_loss(
            transitions=transitions,
            loss_provider=self.loss_provider,
            schema=self.fragility_provider.schema,
        )

        # Cumulative loss value from previous DEUS runs
        existing_loss_value = series.get("cum_loss_value", 0.0)
        # New cumulative loss value (i.e., existing + new)
        combined_loss_value = combine_losses(loss_value, existing_loss_value)

        return pandas.Series(
            {
                "gid": series.gid,
                "geometry": series.geometry,
                "expo": updated_exposure_output_to_dict(updated_exposure),
                "schema": self.fragility_provider.schema,
                "transitions": transitions_output_to_dict(transitions),
                "loss_value": loss_value, # due to this hazard being run
                "cum_loss_value": combined_loss_value, # due to all cumulative hazards run
            }
        )


def updated_exposure_output_to_dict(updated_exposure):
    """
    Convert data to a dictionary for output.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Args:
        updated_exposure (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and damage state of
            an exposure polygon (a row of the overall exposure GeoDataFrame). Keys are ExpoKey
            instances, values are ExpoValues instances.
    """
    result = {}
    for key in [
        "Taxonomy",
        "Damage",
        "Buildings",
        "Population",
        "ReplCostPerBdg",
    ]:
        result[key] = [None] * len(updated_exposure)

    for idx, (expo_key, expo_value) in enumerate(updated_exposure.items()):
        result["Taxonomy"][idx] = expo_key.taxonomy
        result["Damage"][idx] = int_x_to_str_Dx(expo_key.damage_state)
        result["Buildings"][idx] = expo_value.buildings
        result["Population"][idx] = expo_value.population
        result["ReplCostPerBdg"][idx] = expo_value.replcostbdg

    return result


def transitions_output_to_dict(transitions):
    """
    Convert the transitions to a dict for output.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Args:
        transitions (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and transition (i.e.,
            change) from an initial damage state to a final damage state, and details on the
            buildings associated with those transitions.
    """
    result = {}

    for key in [
        "taxonomy",
        "from_damage_state",
        "to_damage_state",
        "n_buildings",
        "replacement_costs_usd_bdg",
    ]:
        result[key] = [None] * len(transitions)

    for idx, (transition_key, transition_value) in enumerate(
        transitions.items()
    ):
        result["taxonomy"][idx] = transition_key.taxonomy
        result["from_damage_state"][idx] = transition_key.from_damage_state
        result["to_damage_state"][idx] = transition_key.to_damage_state
        result["n_buildings"][idx] = transition_value.buildings
        result["replacement_costs_usd_bdg"][idx] = transition_value.replcostbdg

    return result


def expo_from_series_to_dict(expo):
    """
    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Convert the existing expo to an exposure dict (ExpoKey & ExpoValues).

    The resulting expo is the one to work with in the mapping & the update function.

    Args:
        expo (dict):
            Dictionary in string format, corresponding to one exposure polygon (i.e. one row) of
            the exposure GeoDataFrame, with the following keys and contents:
                "Taxonomy":
                    List with the names of the building classes present in the exposure
                    polygon. If the exposure polygon contains instances of the same
                    building class but different damage states, the name of the building
                    classes needs to be repeated here.
                "Damage":
                    List with the names of the damage states associated with the
                    building classes listed in "Taxonomy".
                "Buildings":
                    List with the number of buildings in exposure polygon associated
                    with each element of "Taxonomy" and "Damage".
                "Population":
                    To be fully implemented.
                "ReplCostPerBdg":
                    To be fully implemented.
            Example:
                {'Taxonomy': ['bdg_class_1', 'bdg_class_2'],
                 'Damage': ['D0', 'D0'],
                 'Buildings': [2.5, 5.0]}

    Returns:
        as_dict (collections.defaultdict):
            Dictionary with one key-value pair per element of the lists of the input 'expo'
            (i.e., each combination of taxonomy and damage state). Keys are ExpoKey instances,
            values are ExpoValues instances.

            If no population or building replacement costs are present in 'expo', they are set
            to 0.0 in the 'as_dict' output.

            Example for the example input 'expo' above:
                defaultdict(
                    {ExpoKey(taxonomy='bdg_class_1', damage_state=0):
                        ExpoValues(buildings=2.5, population=0.0, replcostbdg=0.0),
                     ExpoKey(taxonomy='bdg_class_2', damage_state=0):
                        ExpoValues(buildings=5.0, population=0.0, replcostbdg=0.0)}
    """
    as_dict = collections.defaultdict(empty_expo_values)

    if isinstance(expo["Taxonomy"], list):
        idx_generator = range(len(expo["Taxonomy"]))
    else:
        idx_generator = expo["Taxonomy"].keys()

    for idx in idx_generator:
        expo_key = ExpoKey(
            get_from_series_expo(expo["Taxonomy"], idx, None),
            str_Dx_to_int(get_from_series_expo(expo["Damage"], idx, None)),
        )
        buildings = get_from_series_expo(expo.get("Buildings", []), idx, 0)
        population = get_from_series_expo(expo.get("Population", []), idx, 0)
        replcostbdg = get_from_series_expo(
            expo.get("ReplCostPerBdg", []), idx, 0
        )
        expo_value = ExpoValues(buildings, population, replcostbdg)
        as_dict[expo_key] = expo_value

    return as_dict


def get_from_series_expo(column, idx, default):
    """
    Get the values from the expo. This is a helper function only.

    Function copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
    """
    if isinstance(column, list):
        if idx < len(column):
            return column[idx]
        return default
    return column.get(idx, default)


def map_exposure(expo, source_schema, target_schema, schema_mapper):
    """
    Function copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    The function to map the exposure to another schema if necessary.

    The input 'expo' refers to one exposure polygon, which contains a series of building classes
    (taxonomy) with their own damage states.

    If the source building schema ('source_schema') and the target building schema
    ('target_schema') match, this function returns the same input exposure model ('expo').
    Otherwise, it uses the 'schema_mapper' to convert the building classes and damage states of
    the input expoure model ('expo') from their original 'source_schema' to the 'target_schema'.

    Args:
        source_schema (string):
            Name of the source building schema, that is, the one used within the input
            'exposure'.
        target_schema (string):
            Name of the target building schema, that is, the one used by the
            'fragility_provider'.
        expo (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and damage state of
            an exposure polygon (a row of the overall exposure GeoDataFrame). Keys are ExpoKey
            instances, values are ExpoValues instances.
            Example:
                defaultdict(
                    {ExpoKey(taxonomy='bdg_class_1', damage_state=0):
                        ExpoValues(buildings=2.5, population=0.0, replcostbdg=0.0),
                     ExpoKey(taxonomy='bdg_class_2', damage_state=0):
                        ExpoValues(buildings=5.0, population=0.0, replcostbdg=0.0)}
        schema_mapper (SchemaMapper):
            Instance of SchemaMapper containing the compatibility matrices needed to map from
            one schema to another, both in terms of building taxonomies and damage scales.

    Returns:
        result_expo (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and damage state of
            an exposure polygon (a row of the overall exposure GeoDataFrame). Keys are ExpoKey
            instances, values are ExpoValues instances. I.e., the same format as the input
            'expo', but with all building expressed in terms of the building taxonomy and damage
            scale of the 'target_schema'.
    """

    if source_schema == target_schema:
        return expo

    result_expo = collections.defaultdict(empty_expo_values)

    # From DEUS, not clear if this is being used elsewhere or not, it is not output by this method.
    # Moreover, note that if source_schema == target_schema (above), 'expo' is returned, so the
    # calculation of n_buildings_per_tax and total_repl_per_tax would have not happened
    # We have to collect the replacement costs over all
    # damage states of the results (for each taxonomy).
    #n_buildings_per_tax = collections.defaultdict(zero)
    #total_repl_per_tax = collections.defaultdict(zero)

    # Go one by one each source building class (taxonomy)-damage state combination in 'expo'
    for old_expo_key, old_expo_value in expo.items():
        # One taxonomy class with a damage state can map to different other taxonomy classes and
        # different damage states --> mapping_results is a list of SchemaMapperResult objects,
        # each for a particular combination of target building class and target damage state
        mapping_results = schema_mapper.map_schema(
            source_taxonomy=old_expo_key.taxonomy,
            source_damage_state=old_expo_key.damage_state,
            source_schema=source_schema,
            target_schema=target_schema,
            n_buildings=1.0,  # return proportions, not total number of buildings
        )

        # Go one by one each target building class (taxonomy)-damage state combination
        # (stemming from the conversion of (old_expo_key, old_expo_value))
        for res in mapping_results:
            expo_key = ExpoKey(res.taxonomy, res.damage_state)
            # res.n_buildings is now only a number from 0 to 1 (proportion)
            expo_value = result_expo[expo_key]

            new_buildings = res.n_buildings * old_expo_value.buildings
            # Summing because different source taxonomy-damage
            # can contribute to this target taxonomy-damage
            expo_value.buildings += new_buildings
            #n_buildings_per_tax[res.taxonomy] += new_buildings SEE NOTE ABOVE ABOUT n_buildings_per_tax

            # From DEUS partial implementation of pop/costs, to be further evaluated
            #new_pop = res.n_buildings * old_expo_value.population  # population input for all n_buildings
            #expo_value.population += new_pop

            # From DEUS partial implementation of pop/costs, to be further evaluated
            #new_repl = new_buildings * old_expo_value.replcostbdg  # but cost is by bdg... but below it is divided?
            #total_repl_per_tax[res.taxonomy] += new_repl

    # From DEUS partial implementation of pop/costs, to be further evaluated
    #for expo_key, expo_value in result_expo.items():
    #    taxonomy = expo_key.taxonomy
    #    n_bdg = n_buildings_per_tax[taxonomy]
    #    if n_bdg != 0:
    #        expo_value.replcostbdg = total_repl_per_tax[taxonomy] / n_bdg  # back to cost per bdg? why this process?

    return result_expo


def get_updated_exposure_and_transitions(
    geometry, expo, intensity_provider, fragility_provider
):
    """
    Function copied and **significantly** modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    This function returns the update exposure and all of the transitions that happend in this step.

    The intensity measures are retrieved from the 'intensity_provider' at the centroid of the
    input 'geometry'.

    Args:
        geometry:
            Geometry of the exposure polygon.
        expo (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and damage state of
            an exposure polygon. Keys are ExpoKey instances, values are ExpoValues instances.
            Example:
                defaultdict(
                    {ExpoKey(taxonomy='bdg_class_1', damage_state=0):
                        ExpoValues(buildings=2.5, population=0.0, replcostbdg=0.0),
                     ExpoKey(taxonomy='bdg_class_2', damage_state=0):
                        ExpoValues(buildings=5.0, population=0.0, replcostbdg=0.0)}
        intensity_provider (IntensityProvider):
            Instance of IntensityProvider for retrieving the hazard intensities at a location.
        fragility_provider (FragilityProvider):
            Instance of FragilityProvider that gives access to the fragility functions.

    Returns:
        result_expo (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and damage state of
            an exposure polygon (a row of the overall exposure GeoDataFrame). Keys are ExpoKey
            instances, values are ExpoValues instances. I.e., the same format as the input
            'expo', but with all building classes and damage state combinations updated as per
            the input hazard ('intensity_provider') and fragility ('fragility_provider'). I.e.,
            these are the post-event damage states.
        result_transitions (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and transition (i.e.,
            change) from an initial damage state to a final damage state, and details on the
            buildings associated with those transitions.
    """

    # Initialise results with zeroes
    result_transitions = collections.defaultdict(empty_transition_values)

    # Do not perform any operations if there are no buildings
    if not any(expo_value.buildings > 0 for expo_value in expo.values()):
        return expo, result_transitions

    # Read intensity measures at the centroid of the exposure polygon
    centroid = geometry.centroid
    lon, lat = centroid.x, centroid.y
    intensity, units = intensity_provider.get_nearest(lon=lon, lat=lat)

    result_expo = collections.defaultdict(empty_expo_values)

    for old_expo_key, old_expo_value in expo.items():
        n_bdgs = old_expo_value.buildings

        old_damage_state = old_expo_key.damage_state
        taxonomy = old_expo_key.taxonomy

        # Retrieve damage states that are worse than 'old_damage_state'
        # (it also returns the fragility curve corresponding to this damage transition)
        damage_states_to_care = get_sorted_damage_states(
            fragility_provider, taxonomy, old_damage_state
        )

        # Initialise Probability of Exceedance (PoE) array
        # poes[-1] = 1, i.e. PoE the current damage state
        poes = np.ones(len(damage_states_to_care)+1)

        for position, single_damage_state in enumerate(damage_states_to_care):
            # position != damage state value
            # position=0 belongs to the worst damage state
            # position=-1 will belong to the initial damage state, with PoE=1
            poes[position] = single_damage_state.get_probability_for_intensity(
                intensity, units
            )

        # Probabilities of occurrence (the position order is the same as in poes)
        poos = np.zeros_like(poes)
        poos[0] = poes[0]  # first element is the worst damage state, for which PoE=PoO
        poos[1:] = np.flip(np.flip(poes)[:-1] - np.flip(poes)[1:])

        for position, single_damage_state in enumerate(damage_states_to_care):
            expo_key = ExpoKey(taxonomy, single_damage_state.to_state)

            n_buildings_in_damage_state = poos[position] * n_bdgs

            expo_value = result_expo[expo_key]

            expo_value.buildings += n_buildings_in_damage_state

            transition_key = TransitionKey(
                taxonomy,
                old_damage_state,
                single_damage_state.to_state,
            )
            result_transitions[
                transition_key
            ].buildings += n_buildings_in_damage_state

        # Buildings that remain in the same damage state
        expo_key = ExpoKey(taxonomy, old_damage_state)
        expo_value = result_expo[expo_key]
        expo_value.buildings += poos[-1] * n_bdgs

    return result_expo, result_transitions


def compute_loss(transitions, loss_provider, schema):
    """
    Function copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Calculate the total economic loss associated due to all the damage 'transitions' associated
    with one exposure polygon. As the economic loss is transition-based, it is incremental by
    nature.

    Args:
        transitions (collections.defaultdict):
            Dictionary with one key-value pair per combination of taxonomy and transition (i.e.,
            change) from an initial damage state to a final damage state, and details on the
            buildings associated with those transitions. All this, for one exposure polygon.
        loss_provider (LossProvider):
            Instance of LossProvider to access the economic consequence model (loss ratios per
            damage state) and building replacement costs.
        schema (str):
            Name of the schema associated with the consequence model of 'loss_provider'.

    Returns:
        loss_value (float):
            Incremental economic loss associated with the exposure polygon whose damage
            transitions are described in 'transitions'.
    """
    loss_value = 0

    for transition_key, transition_value in transitions.items():

        replacement_cost = transition_value.replcostbdg

        # If replacement costs are not given within the exposure,
        # retrieve them from the loss_provider
        if replacement_cost == 0:
            replacement_cost = loss_provider.get_fallback_replacement_cost(
                schema=schema, taxonomy=transition_key.taxonomy
            )

        # Incremental loss (additional loss starting from 'from_damage_state' and
        # moving up to 'to_damage_state')
        single_loss_value = loss_provider.get_loss(
            schema=schema,
            taxonomy=transition_key.taxonomy,
            from_damage_state=transition_key.from_damage_state,
            to_damage_state=transition_key.to_damage_state,
            replacement_cost=replacement_cost,
        )
        # single_loss_value refers to one building (because replacement_cost is for one
        # building) --> multiply by the number of buildings in this transition
        n_loss_value = single_loss_value * transition_value.buildings

        loss_value += n_loss_value

    return loss_value


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
