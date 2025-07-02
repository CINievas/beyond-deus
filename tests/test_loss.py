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
from beyonddeus.loss import LossProvider


def test_from_files():

    loss_provider = LossProvider.from_files(
        os.path.join(os.path.dirname(__file__), "data", "consequence_costs_test.json")
    )

    assert isinstance(loss_provider._data, dict)

    assert "data" in loss_provider._data["my_id"].keys()

    assert loss_provider._data["my_id"]["data"]["steps"]["3"] == 0.6
    assert loss_provider._data["my_id"]["data"]["replacementCosts"]["bdg_class_1"] == 1000000
