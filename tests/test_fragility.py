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
import pandas as pd
from beyonddeus.fragility import Fragility, LogncdfFactory, AllOnes, UnitPoE


def test_lognorm_fragility_data_without_sublevel():
    """
    Test adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus
        
    Test fragility data without sublevel
    """
    data = {
        "meta": {
            "shape": "logncdf",
            "id": "my_schema",
        },
        "data": [
            {
                "taxonomy": "URM1",
                "D1_mean": 5.9,
                "D1_stddev": 0.8,
                "D2_mean": 6.7,
                "D2_stddev": 0.8,
                "D3_mean": 7.2,
                "D3_stddev": 0.8,
                "imt": "PGA",
                "imu": "g",
            },
            {
                "taxonomy": "CM",
                "D1_mean": 7.6,
                "D1_stddev": 1.0,
                "D2_mean": 8.6,
                "D2_stddev": 1.0,
                "D3_mean": 9.1,
                "D3_stddev": 1.0,
                "imt": "PGA",
                "imu": "g",
            },
        ],
    }

    frag = Fragility(data)
    fragprov = frag.to_fragility_provider()

    assert fragprov.schema == "my_schema"

    returned_taxonomies = fragprov.get_taxonomies() # list of taxonomy strings

    for i in range(len(data["data"])):
        assert data["data"][i]["taxonomy"] in returned_taxonomies

    taxonomy_data_urm1 = fragprov.get_damage_states_for_taxonomy("URM1")

    assert len(taxonomy_data_urm1) == 12
    
    expected_poes = {
        0: {1: 0.133132, 2: 0.017356, 3: 0.003103},
        1: {1: 1.000000, 2: 0.017356, 3: 0.003103},
        2: {1: 0.000000, 2: 1.000000, 3: 0.003103},
        3: {1: 0.000000, 2: 0.000000, 3: 1.000000},
    }

    for from_damage_state in [0, 1, 2, 3]:
        for to_damage_state in [1, 2, 3]:
            ds_requested = [
                ds
                for ds in taxonomy_data_urm1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"PGA": 150.0}
            )
            assert round(poe_returned, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )


def test_fragility_data_exception_input_magic_repair():
    """
    Test fragility data when input includes a curve to transition
    from a larger damage state to a smaller damage state.
    """
    data = {
        "meta": {
            "shape": "logncdf",
            "id": "my_schema",
        },
        "data": [
            {
                "taxonomy": "URM1",
                "D1_mean": 5.9,
                "D1_stddev": 0.8,
                "D2_mean": 6.7,
                "D2_stddev": 0.8,
                "D_2_1_mean": 7.2,
                "D_2_1_stddev": 0.8,
                "imt": "PGA",
                "imu": "g",
            },
        ],
    }

    frag = Fragility(data)

    with pytest.raises(ValueError) as excinfo:
        fragprov = frag.to_fragility_provider()

    assert "ValueError" in str(excinfo.type)


def test_fragility_data_exception_input_missing_lower():
    """
    Test fragility data when "intermediate" damage state is missing from the input.
    """
    data = {
        "meta": {
            "shape": "logncdf",
            "id": "my_schema",
        },
        "data": [
            {
                "taxonomy": "URM1",
                "D1_mean": 5.9,
                "D1_stddev": 0.8,
                "D3_mean": 7.2,
                "D3_stddev": 0.8,
                "imt": "PGA",
                "imu": "g",
            },
        ],
    }

    frag = Fragility(data)

    with pytest.raises(OSError) as excinfo:
        fragprov = frag.to_fragility_provider()

    assert "OSError" in str(excinfo.type)


def test_lognorm_fragility_data_with_sublevel():
    """
    Test adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Test fragility data with sublevels.
    """
    data = {
        "meta": {
            "shape": "logncdf",
            "id": "SARA_v1.0",
        },
        "data": [
            {
                "taxonomy": "URM1",
                "D_0_1_mean": 5.9,
                "D_0_1_stddev": 0.8,
                "D_0_2_mean": 6.7,
                "D_0_2_stddev": 0.8,
                "D_1_2_mean": 7.2,
                "D_1_2_stddev": 0.8,
                "imt": "PGA",
                "imu": "g",
            },
            {
                "taxonomy": "CM",
                "D_0_1_mean": 7.6,
                "D_0_1_stddev": 1.0,
                "D_0_2_mean": 8.6,
                "D_0_2_stddev": 1.0,
                "imt": "PGA",
                "imu": "g",
            },
        ],
    }

    frag = Fragility(data)
    fragprov = frag.to_fragility_provider()

    taxonomy_data_urm1 = fragprov.get_damage_states_for_taxonomy("URM1")

    assert len(taxonomy_data_urm1) == 6
    
    expected_poes = {
        0: {1: 0.133132, 2: 0.017356},
        1: {1: 1.000000, 2: 0.003103},
        2: {1: 0.000000, 2: 1.000000},
    }

    for from_damage_state in [0, 1, 2]:
        for to_damage_state in [1, 2]:
            ds_requested = [
                ds
                for ds in taxonomy_data_urm1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"PGA": 150.0}
            )
            assert round(poe_returned, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )

    taxonomy_data_cm = fragprov.get_damage_states_for_taxonomy("CM")

    assert len(taxonomy_data_cm) == 6

    expected_poes = {
        0: {1: 0.004808, 2: 0.000166},
        1: {1: 1.000000, 2: 0.000166},
        2: {1: 0.000000, 2: 1.000000},
    }

    for from_damage_state in [0, 1, 2]:
        for to_damage_state in [1, 2]:
            ds_requested = [
                ds
                for ds in taxonomy_data_cm
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"PGA": 150.0}
            )
            assert round(poe_returned, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )
            # Test that also Pandas Series can be passed to get_probability_for_intensity()
            poe_returned_from_series = ds_requested[0].get_probability_for_intensity(
                pd.Series({"PGA": 150.0})
            )
            assert round(poe_returned_from_series, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )


def test_logistic_fragility_data_with_sublevel():
    """
    Test fragility data (logistic function) with sublevels.
    """
    data = {
        "meta": {
            "shape": "logistic",
            "id": "Test Model",
        },
        "data": [
            {
                "taxonomy": "URM1",
                "D_0_1_a" : -6.008596,
                "D_0_1_b" : 6.543512,
                "D_0_2_a" : -6.256472,
                "D_0_2_b" : 8.455764,
                "D_0_3_a" : -5.706633,
                "D_0_3_b" : 9.591508,
                "D_0_4_a" : -4.985643,
                "D_0_4_b" : 9.932733,
                "D_0_5_a": -4.773390,
                "D_0_5_b": 9.724112,
                "D_1_3_a" : -6.256472,
                "D_1_3_b" : 8.455764,
                "imt": "max_inundation_depth",
                "imu": "m",
            },
        ],
    }

    frag = Fragility(data)
    fragprov = frag.to_fragility_provider()

    taxonomy_data_urm1 = fragprov.get_damage_states_for_taxonomy("URM1")

    assert len(taxonomy_data_urm1) == 30

    expected_poes = {
        0: {1: 0.921967, 2: 0.716861, 3: 0.262782},
        1: {1: 1.000000, 2: 0.716861, 3: 0.716861},
        2: {1: 0.000000, 2: 1.000000, 3: 0.716861},
    } # values calculated with separate code

    for from_damage_state in [0, 1, 2]:
        for to_damage_state in [1, 2, 3]:
            ds_requested = [
                ds
                for ds in taxonomy_data_urm1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"max_inundation_depth": 1.5}
            )
            assert round(poe_returned, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )


def test_lognorm_fragility_read_from_file():
    """
    Test Fragility.from_file(), using realistic fragility curve values.
    Test that PoE = 0 for IM < 0 when using a lognormal CDF.
    """

    fragprov = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test.json")
    ).to_fragility_provider()

    assert len(fragprov.get_taxonomies()) == 2

    data_bdg_class_1 = fragprov.get_damage_states_for_taxonomy("source_1")
    
    assert len(data_bdg_class_1) == 20

    expected_poes = {
        0: {1: 0.719197, 2: 0.436205, 3: 0.309494, 4: 0.239456},
        1: {1: 1.000000, 2: 0.436205, 3: 0.309494, 4: 0.239456},
        2: {1: 0.000000, 2: 1.000000, 3: 0.309494, 4: 0.239456},
        3: {1: 0.000000, 2: 0.000000, 3: 1.000000, 4: 0.239456},
        4: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 1.000000},
    }  # values calculated with separate code

    for from_damage_state in [0, 1, 2, 3, 4]:
        for to_damage_state in [1, 2, 3, 4]:
            ds_requested = [
                ds
                for ds in data_bdg_class_1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"PGA": 2.0}
            )
            assert round(poe_returned, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )

    # It should return 0 for all IM < 0 (lognormal curve)
    expected_poes = {
        0: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000},
        1: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000},
        2: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000},
        3: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000},
        4: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000},
    }

    for from_damage_state in [0, 1, 2, 3, 4]:
        for to_damage_state in [1, 2, 3, 4]:
            ds_requested = [
                ds
                for ds in data_bdg_class_1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"PGA": -2.0}
            )
            assert round(poe_returned, 12) == round(
                expected_poes[from_damage_state][to_damage_state], 12
            )

    # When the target intensity value is 0.0, get_probability_for_intensity() should return:
    # * 0.0 if to_damage_state > from_damage_state (i.e. it is not possible to get more damage)
    # * 1.0 if to_damage_state = from_damage_state (i.e. the object is already in that damage state)
    data_bdg_class_2 = fragprov.get_damage_states_for_taxonomy("source_2")

    for from_damage_state in [0, 1, 2, 3]:
        for to_damage_state in [1, 2, 3]:
            ds_requested = [
                ds
                for ds in data_bdg_class_2
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"PGA": 0.0}
            )
            if from_damage_state == to_damage_state:
                assert round(poe_returned, 6) == 1.0
            else:
                assert round(poe_returned, 6) == 0.0


def test_logistic_fragility_read_from_file():
    """
    Test Fragility.from_file(), using realistic fragility curve values.
    Test that PoE = 0 for IM < 0 when using a logistic function.
    """

    fragprov = Fragility.from_file(
       os.path.join(os.path.dirname(__file__), "data", "fragility_test_logistic.json")
    ).to_fragility_provider()

    assert len(fragprov.get_taxonomies()) == 2

    data_bdg_class_1 = fragprov.get_damage_states_for_taxonomy("source_1")

    assert len(data_bdg_class_1) == 30

    expected_poes = {
        0: {1: 0.921967, 2: 0.716861, 3: 0.262782, 4: 0.079127, 5: 0.071490},
        1: {1: 1.000000, 2: 0.716861, 3: 0.262782, 4: 0.079127, 5: 0.071490},
        2: {1: 0.000000, 2: 1.000000, 3: 0.262782, 4: 0.079127, 5: 0.071490},
        3: {1: 0.000000, 2: 0.000000, 3: 1.000000, 4: 0.079127, 5: 0.071490},
        4: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 1.000000, 5: 0.071490},
        5: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 1.000000}
    }  # values calculated with separate code

    for from_damage_state in [0, 1, 2, 3, 4, 5]:
        for to_damage_state in [1, 2, 3, 4, 5]:
            ds_requested = [
                ds
                for ds in data_bdg_class_1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"max_inundation_depth": 1.5}
            )
            assert round(poe_returned, 6) == round(
                expected_poes[from_damage_state][to_damage_state], 6
            )

    # It should return 0 for all IM < 0 (logistic curve)
    expected_poes = {
        0: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 0.000000},
        1: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 0.000000},
        2: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 0.000000},
        3: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 0.000000},
        4: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 0.000000},
        5: {1: 0.000000, 2: 0.000000, 3: 0.000000, 4: 0.000000, 5: 0.000000}
    }

    for from_damage_state in [0, 1, 2, 3, 4, 5]:
        for to_damage_state in [1, 2, 3, 4, 5]:
            ds_requested = [
                ds
                for ds in data_bdg_class_1
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"max_inundation_depth": -2.0}
            )
            assert round(poe_returned, 12) == round(
                expected_poes[from_damage_state][to_damage_state], 12
            )

    # When the target intensity value is 0.0, get_probability_for_intensity() should return:
    # * 0.0 if to_damage_state > from_damage_state (i.e. it is not possible to get more damage)
    # * 1.0 if to_damage_state = from_damage_state (i.e. the object is already in that damage state)
    data_bdg_class_2 = fragprov.get_damage_states_for_taxonomy("source_2")

    for from_damage_state in [0, 1, 2, 3, 4, 5]:
        for to_damage_state in [1, 2, 3, 4, 5]:
            ds_requested = [
                ds
                for ds in data_bdg_class_2
                if ds.from_state == from_damage_state
                and ds.to_state == to_damage_state
            ]
            assert len(ds_requested) == 1
            assert ds_requested[0].from_state == from_damage_state
            assert ds_requested[0].to_state == to_damage_state
            poe_returned = ds_requested[0].get_probability_for_intensity(
                {"max_inundation_depth": 0.0}
            )
            if from_damage_state == to_damage_state:
                assert round(poe_returned, 6) == 1.0
            else:
                assert round(poe_returned, 6) == 0.0
