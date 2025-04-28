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
import collections
import json

import pandas as pd


CacheKey = collections.namedtuple(
    "CacheKey",
    "source_schema source_taxonomy source_damage_state target_schema",
)

CacheKeyTaxonomy = collections.namedtuple(
    "CacheKeyTaxonomy", "source_schema source_taxonomy target_schema"
)


def convert_dict_to_use_int_keys(d):
    """
    Method copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Takes a dict with string keys that should be int keys for faster work.

    Returns a generator, so that it can be used with dict(convert_dict_to_use_int_keys(...)).
    """
    for k, v in d.items():
        k = int(k)
        if type(v) == dict:
            v = dict(convert_dict_to_use_int_keys(v))
        yield k, v


class DamageStateMappingMatrix:
    """
    Class copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    This class represents the damage state mapping matrix.

    Attrs:
        pure_dict_conv_matrix (dict):
            Dictionary containing the damage state conversion matrix. Each of its keys
            correspond to the target damage states, while the sub-keys correspond to the source
            damage states. The summation per source damage state must be 1.0 (i.e. each original
            source damage state must be fully decomposed into target damage states).
            Example:
                {
                    "0": {"0": 0.05, "1": 0.01, "2": 0.00, "3": 0.00},
                    "1": {"0": 0.75, "1": 0.65, "2": 0.10, "3": 0.04},
                    "2": {"0": 0.20, "1": 0.30, "2": 0.45, "3": 0.06},
                    "3": {"0": 0.00, "1": 0.04, "2": 0.35, "3": 0.10},
                    "4": {"0": 0.00, "1": 0.00, "2": 0.10, "3": 0.80}
                }
            In this example, there are five target damage states (0 through 4) and four source
            damage states (0 through 3). According to the example, one building in source damage
            state 0 gets converted into 0.05 buildings in target damage state 0, 0.75 buildings
            in target damage state 1, and 0.20 buildings in target damage state 2.
    """

    def __init__(self, dict_conv_matrix):
        self.pure_dict_conv_matrix = dict_conv_matrix
        # do the init of the conv matrix lazy
        self.conv_matrix = None

    def _init_conv_matrix(self):
        self.conv_matrix = (
            pd.DataFrame(
                dict(convert_dict_to_use_int_keys(self.pure_dict_conv_matrix))
            )
            .transpose()
            .to_dict()
        )

    def contains_source_damage_state(self, source_damage_state_int):
        """
        Check if the source damage state is included in the matrix.
        """
        if self.conv_matrix is None:
            self._init_conv_matrix()
        return source_damage_state_int in self.conv_matrix.keys()

    def yield_target_damage_state_with_fraction(self, source_damage_state_int):
        """
        Returns a generator with the target damage state and the fraction
        of for the the specific target damage state.
        """
        for target_damage_state_int, fraction in self.conv_matrix[
            source_damage_state_int
        ].items():
            if fraction > 0:
                yield target_damage_state_int, fraction


class SchemaMapperResult:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to store the mapping results in.

    Attrs:
        schema (str):
            The name of the target schema.
        taxonomy (str):
            The target building class.
        damage_state (int):
            The target damage state.
        n_buildings (float):
            The number of buildings from the original input that result in this combination of
            target building class and damage state.
    """

    def __init__(self, schema, taxonomy, damage_state, n_buildings):
        self.schema = schema
        self.taxonomy = taxonomy
        self.damage_state = damage_state
        self.n_buildings = n_buildings


SourceTargetSchemaTuple = collections.namedtuple(
    "SourceTargetSchemaTuple", "source_schema target_schema"
)

SourceTargetSchemaTaxonomyTuple = collections.namedtuple(
    "SourceTargetSchemaTaxonomyTuple",
    "source_schema target_schema source_taxonomy target_taxonomy",
)


class SchemaMapper:
    """
    Class copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Mapper class to map from one schema to another, both in terms of building taxonomies and
    damage scales.

    Attrs:
        self._tax_mapping_data (dict):
            Dictionary containing the taxonomy compatibility matrices in dictionary form. For
            example, if a source schema "source_schema_name" has three building classes,
            "source_1", "source_2" and "source_3", and a target schema has two building classes,
            "target_1" and "target_2", self._tax_mapping_data would contain a key 
            self._tax_mapping_data["source_schema_name", "target_schema_name"] with the
            following sub-keys and contents (numbers are just an example):
                {
                'source_1': {'target_1': 0.7, 'target_2': 0.3},
                'source_2': {'target_1': 0.0, 'target_2': 1.0},
                'source_3': {'target_1': 0.0, 'target_2': 1.0}
                }
            The summation of the values within each source building class should be equal to 1.
        self._ds_mapping_data (dict):
            Dictionary containing the damage states compatbility matrices in dictionary form.
            Following the previous example, this dictionary would contain different keys for all
            possible combinations of source and target building classes. Example keys would be:
                ["source_schema_name", "target_schema_name", "source_1", "target_1"]
                ["source_schema_name", "target_schema_name", "source_1", "target_2"]
                etc.
            Within each key there is a DamageStateMappingMatrix object with the attribute
            "pure_dict_conv_matrix", which can look as the following example:
            self._ds_mapping_data[
            "source_schema_name", "target_schema_name", "source_1", "target_1"
            ].pure_dict_conv_matrix = {
                "0": {"0": 0.05, "1": 0.01, "2": 0.00, "3": 0.00},
                "1": {"0": 0.75, "1": 0.65, "2": 0.10, "3": 0.04},
                "2": {"0": 0.20, "1": 0.30, "2": 0.45, "3": 0.06},
                "3": {"0": 0.00, "1": 0.04, "2": 0.35, "3": 0.10},
                "4": {"0": 0.00, "1": 0.00, "2": 0.10, "3": 0.80}
            }
            The keys ("0" through "4") are the target damage states, while the sub-keys ("0"
            through "3") are the source damage states. The summation per source damage state
            (i.e., "vertically" in the way the matrix looks above) is 1.0 (i.e. each original
            source damage state must be fully decomposed into target damage states).

    Methods:
        self.map_schema:
            It returns the number of buildings under the target taxonomy and damage scale
            schemas for an input number of buildings in the source taxonomy and damage scales
            (see explanation further below under the method itself).
    """

    def __init__(self, tax_mapping_data, ds_mapping_data):
        self._tax_mapping_data = tax_mapping_data
        self._ds_mapping_data = ds_mapping_data

        self._cached_mappings = {}
        self._cached_mappings_taxonomy = {}

    @classmethod
    def from_taxonomy_and_damage_state_conversion_files(
        cls, tax_mapping_path, damage_mapping_path
    ):
        """
        Reads the data from files.
        """

        filenames_taxonomy = os.listdir(tax_mapping_path)
        filenames_damage = os.listdir(damage_mapping_path)

        tax_mapping_data = []
        ds_mapping_data = []

        for mapping_file in filenames_taxonomy:
            with open(os.path.join(tax_mapping_path, mapping_file), "rt") as input_file:
                data = json.load(input_file)
                tax_mapping_data.append(data)

        for mapping_file in filenames_damage:
            with open(os.path.join(damage_mapping_path, mapping_file), "rt") as input_file:
                data = json.load(input_file)
                ds_mapping_data.append(data)

        return cls.from_taxonomy_and_damage_state_conversion_data(
            tax_mapping_data, ds_mapping_data
        )

    @classmethod
    def from_taxonomy_and_damage_state_conversion_data(
        cls, tax_mapping_data, ds_mapping_data
    ):
        """
        Class method to init the data from a list of taxonomy-rlated datasets
        and a list for the damage state related datasets.
        """

        # first make an index for the taxonomy schema
        # mapping datasets
        tax_mapping_data_by_schemas = {}
        for dataset in tax_mapping_data:
            source_schema = dataset["source_schema"]
            target_schema = dataset["target_schema"]
            conv_matrix = dataset["conv_matrix"]

            source_target_schema_tuple = SourceTargetSchemaTuple(
                source_schema=source_schema,
                target_schema=target_schema,
            )

            tax_mapping_data_by_schemas[
                source_target_schema_tuple
            ] = conv_matrix

            cls._validate_summation_taxonomy_conversion_one(
                conv_matrix, source_schema, target_schema
            )

        # then to the very same for the damage state
        # schema mapping datasets
        # but here we need the target and the source taxonomies too
        ds_mapping_data_by_taxonomies = {}
        for dataset in ds_mapping_data:
            source_schema = dataset["source_schema"]
            target_schema = dataset["target_schema"]
            source_taxonomy = dataset["source_taxonomy"]
            target_taxonomy = dataset["target_taxonomy"]

            conv_matrix = DamageStateMappingMatrix(dataset["conv_matrix"])

            setting_tuple = SourceTargetSchemaTaxonomyTuple(
                source_schema=source_schema,
                target_schema=target_schema,
                source_taxonomy=source_taxonomy,
                target_taxonomy=target_taxonomy,
            )

            ds_mapping_data_by_taxonomies[setting_tuple] = conv_matrix

            cls._validate_summation_damage_conversion_one(
                conv_matrix.pure_dict_conv_matrix,
                source_schema, target_schema, source_taxonomy, target_taxonomy
            )

        return cls(tax_mapping_data_by_schemas, ds_mapping_data_by_taxonomies)

    def _validate_summation_taxonomy_conversion_one(conv_matrix, source_schema, target_schema):
        """
        This method checks that the taxonomy conversion matrices add up to 1 for each source
        building class (and raises an error if this is not the case).
        """

        classes_with_problems = []

        for source_class in conv_matrix:
            summation = 0
            for target_class in conv_matrix[source_class]:
                summation += conv_matrix[source_class][target_class]

            if summation > 1.000001 or summation < 0.999999:
                classes_with_problems.append(source_class)

        if len(classes_with_problems) > 0:
            error_message = (
                "The conversion coefficients of the following source building classes of "
                " source schema %s to target schema %s do not add up to 1: %s"
                % (source_schema, target_schema, ", ".join(classes_with_problems))
            )
            raise ValueError(error_message)

    def _validate_summation_damage_conversion_one(
        conv_matrix, source_schema, target_schema, source_taxonomy, target_taxonomy
    ):
        """
        This method checks that the damage conversion matrices add up to 1 for each source
        damage state (and raises an error if this is not the case).
        """

        damage_states_with_problems = []

        summations = {}

        for target_damage_state in conv_matrix:
            for source_damage_state in conv_matrix[target_damage_state]:
                if source_damage_state not in summations:
                    summations[source_damage_state] = conv_matrix[
                        target_damage_state
                    ][source_damage_state]
                else:
                    summations[source_damage_state] += conv_matrix[
                        target_damage_state
                    ][source_damage_state]                    

        for source_damage_state in summations:
            if (
                summations[source_damage_state] > 1.000001
                or summations[source_damage_state] < 0.999999
            ):
                damage_states_with_problems.append(source_damage_state)

        if len(damage_states_with_problems) > 0:
            error_message = (
                "The conversion coefficients of the following source damage states of "
                "source schema %s to target schema %s, building class %s to %s, "
                "do not add up to 1: %s"
                % (
                    source_schema, target_schema, source_taxonomy, target_taxonomy,
                    ", ".join(damage_states_with_problems)
                )
            )
            raise ValueError(error_message)      

    def map_schema(
        self,
        source_schema,
        source_taxonomy,
        source_damage_state,
        target_schema,
        n_buildings=1.0,
    ):
        """
        Maps the data to another schema.

        It returns the number of buildings under the target taxonomy and damage scale
        schemas for an input number of buildings in the source taxonomy and damage scales
        (see explanation further below under the method itself).

        Args:
            source_schema (str): Name of the source schema.
            source_taxonomy (str): Name of the source building class.
            source_damage_state (int): Source damage state.
            target_schema (str): Name of the target schema.
            n_buildings (float): Number of buildings to convert.

        Returns:
            List of as many SchemaMapperResult objects as non-zero combinations of target
            building classes and target damage states exist for the input source building class
            and source damage state.

        Example (following the examples of the attributes of this class, see above):
            self.map_schema(
                source_schema="source_schema_name",
                source_taxonomy="source_1",
                source_damage_state=0,
                target_schema="target_schema_name",
                n_buildings=1,
            )
            Returns a list of 6 SchemaMapperResult objects. Each object contains the following
            attributes:
                taxonomy (str): The target building class.
                damage_state (int): The target damage state.
                n_buildings (float): The number of buildings from the original input that result
                    in this combination of target building class and damage state.
        """

        if source_schema == target_schema:
            return [
                SchemaMapperResult(
                    schema=source_schema,
                    taxonomy=source_taxonomy,
                    damage_state=source_damage_state,
                    n_buildings=n_buildings,
                )
            ]
        # otherwise we have to map
        results_for_1_building = self._map_schema_1(
            source_schema, source_taxonomy, source_damage_state, target_schema
        )

        results_for_n_buildings = []
        for result in results_for_1_building:
            results_for_n_buildings.append(
                SchemaMapperResult(
                    result.schema,
                    result.taxonomy,
                    result.damage_state,
                    result.n_buildings * n_buildings,
                )
            )

        return results_for_n_buildings

    def _map_schema_1(
        self,
        source_schema,
        source_taxonomy,
        source_damage_state,
        target_schema,
    ):

        cachekey = CacheKey(
            source_schema, source_taxonomy, source_damage_state, target_schema
        )

        if cachekey in self._cached_mappings:
            return self._cached_mappings[cachekey]

        results = self._do_map_schema_1(
            source_schema, source_taxonomy, source_damage_state, target_schema
        )

        self._cached_mappings[cachekey] = results
        return results

    def _map_schema_1_just_taxonomy(
        self, source_schema, source_taxonomy, target_schema
    ):

        key = CacheKeyTaxonomy(
            source_schema=source_schema,
            source_taxonomy=source_taxonomy,
            target_schema=target_schema,
        )

        if key not in self._cached_mappings_taxonomy.keys():
            result = self._do_map_schema_1_just_taxonomy(
                source_schema=source_schema,
                source_taxonomy=source_taxonomy,
                target_schema=target_schema,
            )
            self._cached_mappings_taxonomy[key] = result
            return result

        return self._cached_mappings_taxonomy[key]

    def _do_map_schema_1_just_taxonomy(
        self, source_schema, source_taxonomy, target_schema
    ):

        source_target_schema_tuple = SourceTargetSchemaTuple(
            source_schema=source_schema,
            target_schema=target_schema,
        )
        if source_target_schema_tuple not in self._tax_mapping_data.keys():
            raise Exception(
                (
                    "There is no data for the schema "
                    + "mapping between the source schema "
                    + "{0} and the target schema {1}"
                ).format(source_schema, target_schema)
            )

        tax_conv_matrix = self._tax_mapping_data[source_target_schema_tuple]

        if source_taxonomy not in tax_conv_matrix.keys():
            raise Exception(
                (
                    "There is no data for the schema mapping "
                    + "for the source taxonomy {0}"
                ).format(source_taxonomy)
            )

        return tax_conv_matrix[source_taxonomy]

    def _do_map_schema_1(
        self,
        source_schema,
        source_taxonomy,
        source_damage_state,
        target_schema,
    ):

        mapping_results = []

        tax_conv_row = self._map_schema_1_just_taxonomy(
            source_schema=source_schema,
            source_taxonomy=source_taxonomy,
            target_schema=target_schema,
        )

        for target_taxonomy in tax_conv_row.keys():
            n_buildings_in_target_taxonomy = (
                1.0 * tax_conv_row[target_taxonomy]
            )

            if tax_conv_row[target_taxonomy] > 0:
                # now we can do the damage state conversion

                schema_taxonomy_setting = SourceTargetSchemaTaxonomyTuple(
                    source_schema=source_schema,
                    target_schema=target_schema,
                    source_taxonomy=source_taxonomy,
                    target_taxonomy=target_taxonomy,
                )

                if schema_taxonomy_setting not in self._ds_mapping_data.keys():
                    raise Exception(
                        (
                            "There is no data for the damage "
                            + "state schema mapping for "
                            + "target taxonomy {0} from source taxonomy {1}"
                        ).format(target_taxonomy, source_taxonomy)
                    )

                ds_conv_matrix = self._ds_mapping_data[schema_taxonomy_setting]

                if not ds_conv_matrix.contains_source_damage_state(
                    source_damage_state
                ):
                    raise Exception(
                        (
                            "There is no data for the damage state schema"
                            + " mapping for damage state {0}"
                        ).format(source_damage_state)
                    )

                for (
                    target_damage_state,
                    ds_fraction,
                ) in ds_conv_matrix.yield_target_damage_state_with_fraction(
                    source_damage_state
                ):
                    n_buildings_in_target_damage_state = (
                        n_buildings_in_target_taxonomy * ds_fraction
                    )

                    single_mapping_result = SchemaMapperResult(
                        schema=target_schema,
                        taxonomy=target_taxonomy,
                        damage_state=target_damage_state,
                        n_buildings=n_buildings_in_target_damage_state,
                    )

                    mapping_results.append(single_mapping_result)

        return mapping_results
