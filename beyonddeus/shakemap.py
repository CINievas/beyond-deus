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

import collections
import io
import tokenize

import lxml.etree as le
from lxml.etree import XMLParser

from beyonddeus.intensityprovider import IntensityProvider
from beyonddeus.intensitydatawrapper import DictWithListDataWrapper


class Shakemaps:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Factory class for reading shakemaps.
    """
    @staticmethod
    def from_file(file_name):
        """
        Read the shakemap from an xml file.
        """
        huge_parser = XMLParser(
            encoding='utf-8',
            recover=True,
            huge_tree=True
        )
        xml = le.parse(file_name, huge_parser)
        root = xml.getroot()

        return EqShakemap(root)


class EqShakemap:
    """
    Class copied and adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to handle the xml access to the shakemap xml elements.
    """
    def __init__(self, root):
        self._root = root

    def _find_grid_fields(self):
        grid_fields = self._root.findall(
            '{http://earthquake.usgs.gov/eqcenter/shakemap}grid_field')
        # fallback if namespace is not proper
        if len(grid_fields) == 0:
            grid_fields = self._root.findall('grid_field')

        return [ShakemapGridField(x) for x in grid_fields]

    def _find_grid_data(self):
        grid_data = self._root.find(
            '{http://earthquake.usgs.gov/eqcenter/shakemap}grid_data')
        # fallback if namespace is not proper
        if grid_data is None:
            grid_data = self._root.find('grid_data')
        return ShakemapGridData(grid_data)

    def to_intensity_provider(self):
        """
        Returns an instance of intensityprovider.IntensityProvider, which later
        enables access to the intensity data point that is closest to a given location.
        """
        data = read_shakemap_data(
            grid_fields=self._find_grid_fields(),
            grid_data=self._find_grid_data())

        wrapped_data = DictWithListDataWrapper(
            data=data,
            possible_x_columns=['LON', 'CENTROID_LON'],
            possible_y_columns=['LAT', 'CENTROID_LAT'],
        )

        return IntensityProvider(intensity_data=wrapped_data)


class ShakemapGridField:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to represent a shakemap grid field.
    """
    def __init__(self, xml):
        self._xml = xml

    def get_index(self):
        """
        Returns the index value of the field (one-based).
        """
        return self._xml.get('index')

    def get_name(self):
        """
        Returns the name of the field.
        """
        return self._xml.get('name')


class ShakemapGridData:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class for the xml element with the grid data.
    """
    def __init__(self, xml):
        self._xml = xml

    def get_text(self):
        """
        Returns the text of the data.
        This is a tsv content without header (as this is in the grid fields).
        """
        return self._xml.text


def read_shakemap_data_from_str(grid_data_text):
    """
    Method copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Helper to work with the tokens.
    Can work with both strings and floats.
    """
    # it must be tokenized (because of xml processing the newlines
    # may not be consistent)
    tokens = tokenize.tokenize(
        io.BytesIO(
            grid_data_text.encode('utf-8')).readline)
    token_before = None
    for token in tokens:
        # 2 is number
        if token.type == 2:
            value = float(token.string)
            if token_before is not None and token_before.string == '-':
                value = -1 * value
            yield value
        # 3 is str
        elif token.type == 3:
            raw_value = token.string
            # remove quotes around
            value = raw_value[1:-1]
            yield value
        # take care about the before token for negative numbers
        token_before = token


def read_shakemap_data(grid_fields, grid_data):
    """
    Method copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Function to read the grid_data and the grid fields.
    Returns a dict with the values (in lists) for the different fields.
    """
    names = [x.get_name().upper() for x in grid_fields]
    data = collections.defaultdict(list)
    values = read_shakemap_data_from_str(grid_data.get_text())
    for idx, value in enumerate(values):
        name_idx = idx % len(names)
        name = names[name_idx]
        data[name].append(value)
    return data
