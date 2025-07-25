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

    Class to access the economic consequence model (loss ratios per damage state).
    """

    def __init__(self, data):
        self._data = data

    @classmethod
    def from_files(cls, filename):
        """
        Reads the economic consequence model (loss ratios per damage state) from a json file.
        """
        data = {}
        with open(filename, "rt") as input_file:
            single_data = json.load(input_file)
            schema = single_data["meta"]["id"]
            data[schema] = single_data

        return cls(data)

    def get_incremental_loss_ratio(
        self,
        schema,
        taxonomy,
        from_damage_state,
        to_damage_state
    ):
        """
        Returns the loss ratio for the transition, i.e. the difference between the loss ratio at
        'to_damage_state' and the loss ratio at 'from_damage_state'.
        """

        if schema not in self._data:
            raise Exception("schema is not known for loss computation")
        data_for_schema = self._data[schema]["data"]
        steps = data_for_schema["steps"]

        str_from_damage_state = str(from_damage_state)
        str_to_damage_state = str(to_damage_state)

        coeff_from = 0
        if str_from_damage_state in steps.keys():
            coeff_from = steps[str_from_damage_state]

        coeff_to = steps[str_to_damage_state]
        coeff = coeff_to - coeff_from

        return coeff
