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
import pandas as pd
from beyonddeus.usability import Usability


def test_read_usability_model():

    returned_usability = Usability(
        os.path.join(os.path.dirname(__file__), "data", "usability_test.csv")
    )

    expected_usability = pd.DataFrame(
        {"usable": [True, True, False, False, False]},
        index=[0, 1, 2, 3, 4],
    )
    expected_usability.index.name = "damage_state"

    for dmg_state in expected_usability.index:
        assert (
            returned_usability.data.loc[dmg_state, "usable"] ==
            expected_usability.loc[dmg_state, "usable"]
        )

    returned_usability = Usability("None")
    assert returned_usability.data is None
