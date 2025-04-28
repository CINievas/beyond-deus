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
import pytest
from beyonddeus.schemamapping import SchemaMapper


def test_schema_mapping():

    schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
        os.path.join(os.path.dirname(__file__), "data", "conversion_taxonomy"),
        os.path.join(os.path.dirname(__file__), "data", "conversion_damage")
    )

    # Check taxonomy compatibility matrix
    expected_taxonomy_conversion = {
        "source_schema": "source_schema_name",
        "target_schema": "target_schema_name",
        "source_taxonomies": ["source_1", "source_2", "source_3"],
        "target_taxonomies": ["target_1", "target_2"],
        "conv_matrix": {
            "source_1": {"target_1": 0.7, "target_2": 0.3},
            "source_2": {"target_1": 0.0, "target_2": 1.0},
            "source_3": {"target_1": 0.0, "target_2": 1.0}
        }
    }
    
    for source_tax in expected_taxonomy_conversion["conv_matrix"]:

        assert source_tax in schema_mapper._tax_mapping_data["source_schema_name", "target_schema_name"]

        for target_tax in expected_taxonomy_conversion["conv_matrix"][source_tax]:

            assert round(
                schema_mapper._tax_mapping_data["source_schema_name", "target_schema_name"][
                    source_tax
                ][target_tax], 2) == round(
                expected_taxonomy_conversion["conv_matrix"][source_tax][target_tax], 2
            )
            
    # Check damage compatibility matrix
    expected_damage_conversion = {
        "0": {"0": 0.05, "1": 0.01, "2": 0.00, "3": 0.00},
        "1": {"0": 0.75, "1": 0.65, "2": 0.10, "3": 0.04},
        "2": {"0": 0.20, "1": 0.30, "2": 0.45, "3": 0.06},
        "3": {"0": 0.00, "1": 0.04, "2": 0.35, "3": 0.10},
        "4": {"0": 0.00, "1": 0.00, "2": 0.10, "3": 0.80}
    }

    returned_damage_conversion = schema_mapper._ds_mapping_data[
        "source_schema_name", "target_schema_name", "source_1", "target_2"
    ].pure_dict_conv_matrix
    
    for target_damage_state in expected_damage_conversion:
        for source_damage_state in expected_damage_conversion[target_damage_state]:
            assert round(
                expected_damage_conversion[target_damage_state][source_damage_state], 3
            ) == round(returned_damage_conversion[target_damage_state][source_damage_state], 3)

    # Convert 1 building of building class "source_1" in damage state 0 to the target schema
    mapping_results = schema_mapper.map_schema(
        source_schema="source_schema_name",
        source_taxonomy="source_1",
        source_damage_state=0,
        target_schema="target_schema_name",
        n_buildings=1,
    )

    assert len(mapping_results) == 2*3

    expected_mapping_results = {  # keys: target building classes, subkeys: target damage states
        "target_1": {0: 0.7*0.05, 1: 0.7*0.75, 2: 0.7*0.2},
        "target_2": {0: 0.3*0.05, 1: 0.3*0.75, 2: 0.3*0.2},
    }  # see expected_taxonomy_conversion and expected_damage_conversion matrices

    for pos in range(len(mapping_results)):
        target_tax = mapping_results[pos].taxonomy
        target_damage_state = mapping_results[pos].damage_state
        
        assert target_tax in expected_mapping_results
        assert target_damage_state in expected_mapping_results[target_tax]
        assert round(
            expected_mapping_results[target_tax][target_damage_state], 5
        ) == round(mapping_results[pos].n_buildings, 5)

        
def test_schema_mapping_validate_summation_taxonomy_conversion_one():

    with pytest.raises(ValueError) as excinfo:
        schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
            os.path.join(os.path.dirname(__file__), "data", "conversion_taxonomy_error"),
            os.path.join(os.path.dirname(__file__), "data", "conversion_damage")
        )

    assert "ValueError" in str(excinfo.type)

        
def test_schema_mapping_validate_summation_damage_conversion_one():

    with pytest.raises(ValueError) as excinfo:
        schema_mapper = SchemaMapper.from_taxonomy_and_damage_state_conversion_files(
            os.path.join(os.path.dirname(__file__), "data", "conversion_taxonomy"),
            os.path.join(os.path.dirname(__file__), "data", "conversion_damage_error")
        )

    assert "ValueError" in str(excinfo.type)
