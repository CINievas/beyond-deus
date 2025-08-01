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
from beyonddeus.intensity_reader import read_intensity_files


def test_read_intensity_files():

    # 1 One HDF5 file provided
    intensity_provider = read_intensity_files(
        os.path.join(os.path.dirname(__file__), "data", "EQ_ground_motion_fields_test.hdf5"),
        "hdf5"
    )

    expected_branches = ["GMPE1", "GMPE2"]
    expected_realisations = [0, 1, 2, 3, 4]

    assert len(intensity_provider.keys()) == len(expected_branches)

    for branch in expected_branches:

        assert branch in intensity_provider.keys()
        assert len(intensity_provider[branch].keys()) == len(expected_realisations)

        for realisation in expected_realisations:
            assert realisation in intensity_provider[branch].keys()

    # 2 Set of XML files provided directly under the main intensity file path
    intensity_provider = read_intensity_files(
        os.path.join(os.path.dirname(__file__), "data", "reading_intensity_one_branch"),
        "xml"
    )

    expected_branches = ["unique"]
    expected_realisations = [0, 1]

    assert len(intensity_provider.keys()) == len(expected_branches)

    for branch in expected_branches:
    
        assert branch in intensity_provider.keys()
        assert len(intensity_provider[branch].keys()) == len(expected_realisations)

        for realisation in expected_realisations:
            assert realisation in intensity_provider[branch].keys()

    # 3 Set of XML files provided in sub-directories
    intensity_provider = read_intensity_files(
        os.path.join(os.path.dirname(__file__), "data", "reading_intensity_two_branches"),
        "xml"
    )

    expected_branches = ["subdir_1", "subdir_2"]
    expected_realisations = [0, 1, 2]

    assert len(intensity_provider.keys()) == len(expected_branches)

    for branch in expected_branches:

        assert branch in intensity_provider.keys()
        assert len(intensity_provider[branch].keys()) == len(expected_realisations)

        for realisation in expected_realisations:
            assert realisation in intensity_provider[branch].keys()

    # 4 No files or sub-directories found
    with pytest.raises(OSError) as excinfo:
        intensity_provider = read_intensity_files(
            os.path.join(os.path.dirname(__file__), "data", "reading_intensity_empty"),
            "xml"
        )
    assert "OSError" in str(excinfo.type)

    # 5 Both files and sub-directories found
    with pytest.raises(OSError) as excinfo:
        intensity_provider = read_intensity_files(
            os.path.join(
                os.path.dirname(__file__), "data", "reading_intensity_files_and_subdirs"
            ),
            "xml"
        )
    assert "OSError" in str(excinfo.type)
    
    # 6 The intensity_file_type is not supported
    intensity_provider = read_intensity_files(
        os.path.join(os.path.dirname(__file__), "data", "reading_intensity_one_branch"),
        "csv"
    )

    assert isinstance(intensity_provider, dict)
    assert len(intensity_provider.keys()) == 0
    
    # 7 Set of Tsunami NetCDF files provided in sub-directories
    intensity_provider = read_intensity_files(
        os.path.join(os.path.dirname(__file__), "data", "reading_intensity_two_branch_Tsu"),
        "netcdf_tsu"
    )

    expected_branches = ["subdir_1", "subdir_2"]
    expected_realisations = [0, 1]

    assert len(intensity_provider.keys()) == len(expected_branches)

    for branch in expected_branches:
    
        assert branch in intensity_provider.keys()
        assert len(intensity_provider[branch].keys()) == len(expected_realisations)

        for realisation in expected_realisations:
            assert realisation in intensity_provider[branch].keys()
