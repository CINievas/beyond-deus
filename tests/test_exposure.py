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
import numpy as np
from beyonddeus.exposure import read_exposure


def test_read_exposure():

    initial_exposure = read_exposure(
       os.path.join(os.path.dirname(__file__), "data", "exposure_test.json")
    )

    assert initial_exposure.shape[0] == 2  # rows

    quadkeys = ["1230", "1231"]  # implicitly checking "gid" column read as strings
    initial_exposure_quadkeys = initial_exposure["gid"].to_numpy()

    expo_keys = ["Taxonomy", "Damage", "Buildings"]

    for quadkey in quadkeys:
        assert quadkey in initial_exposure_quadkeys

        row = np.where(initial_exposure_quadkeys == quadkey)[0][0]

        expo_dict = eval(initial_exposure.loc[row, "expo"])

        assert isinstance(expo_dict, dict)

        for expo_key in expo_keys:
            assert expo_key in expo_dict.keys()
