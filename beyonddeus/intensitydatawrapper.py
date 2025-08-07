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

class DictWithListDataWrapper:
    """
    Class copied and modified from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Wrapper for accessing the intensity data using a dictionary with lists for the data.

    Attrs:
        data (dict):
            Dictionary with individual keys for the longitude and latitude of the sites, as well
            as for the different intensity measures. Each of the keys contains a list with
            values (float) of lon/lat or intensity measures.
        _x_column (str):
            Name of the key of 'data' that contains the longitude coordinates.
        _y_column (str):
            Name of the key of 'data' that contains the latitude coordinates.
    """
    def __init__(self, data, possible_x_columns, possible_y_columns):
        """
        Args:
            data (dict):
                See description in attrs.
            possible_x_columns (list of str):
                Possible names of the key of 'data' that contains the longitude coordinates.
            possible_y_columns (list of str):
                Possible names of the key of 'data' that contains the latitude coordinates.
        """
        self._data = data

        self._x_column = None
        self._y_column = None

        for possible_column in possible_x_columns:
            if possible_column in self._data.keys():
                self._x_column = possible_column
                break

        assert self._x_column is not None

        for possible_column in possible_y_columns:
            if possible_column in self._data.keys():
                self._y_column = possible_column
                break

        assert self._y_column is not None

    def get_list_x_coordinates(self):
        """
        Returns a list / series / array of the x coordinates.
        """
        return self._data[self._x_column]

    def get_list_y_coordinates(self):
        """
        Returns a list / series / array of the y coordinates.
        """
        return self._data[self._y_column]

    def get_data_columns(self):
        """
        Returns a generator to go over all of the
        data columns for the intensity data.
        """
        for column in self._data.keys():
            if column != self._x_column:
                if column != self._y_column:
                    yield column

    def get_value_for_column_and_index(self, column, index):
        """
        Returns the value for the column and the index.
        """
        return self._data[column][index]
