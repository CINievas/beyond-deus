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

import json


class LossProvider:
    """
    Class copied and adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to access the economic consequence model (loss ratios per damage state) and building
    replacement costs.
    """

    def __init__(self, data):
        self._data = data

    @classmethod
    def from_files(cls, filename):
        """
        Reads the economic consequence model (loss ratios per damage state) and building
        replacement costs from a json file.
        """
        data = {}
        with open(filename, "rt") as input_file:
            single_data = json.load(input_file)
            schema = single_data["meta"]["id"]
            data[schema] = single_data

        return cls(data)
