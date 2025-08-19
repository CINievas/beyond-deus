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

import pandas as pd


class Usability:
    """
    Class to access the usability model.
    
    Attrs:
        data (Pandas DataFrame):
            DataFrame with index "damage_state", in terms of integers and one column labelled
            "usable" (bool), containing True/False.
    """

    def __init__(self, filename):
        self.data = self._read_usability_model(filename)

    def _read_usability_model(self, filename):
        if filename == "None":
            return None

        data = pd.read_csv(filename)

        if ("damage_state" not in data.columns) or ("usability" not in data.columns):
            error_message = (
                "The usability CSV file must contain the columns 'damage_state' and 'usability"
            )
            raise OSError(error_message)

        # Make sure "damage_state" is an integer
        data["damage_state"] = data["damage_state"].astype(int)
        # Make "usability" lower case
        data["usability"] = [usability_val.lower() for usability_val in data["usability"]]
        # Set "damage_state" as index
        data.set_index(data["damage_state"], inplace=True)
        data.drop(columns=["damage_state"], inplace=True)

        usable_aux = []

        for dmg_state in data.index:
            if data.loc[dmg_state, "usability"]=="usable":
                usable_aux.append(True)
            elif data.loc[dmg_state, "usability"]=="unusable":
                usable_aux.append(False)
            else:
                error_message = (
                    "The usability CSV file contains values "
                    "different from 'usable' and 'unusable'"
                )
                raise OSError(error_message)                

        data["usable"] = usable_aux 
        #usability = {}
        #usability["usable"] = data.loc[data.usability=="usable", "damage_state"].to_list()
        #usability["unusable"] = data.loc[data.usability=="unusable", "damage_state"].to_list()

        return data
