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

import logging
import numpy as np
from netCDF4 import Dataset

from beyonddeus.intensityprovider import IntensityProvider
from beyonddeus.intensitydatawrapper import DictWithListDataWrapper


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TEMP_NetCDF_fields:
    """
    Factory class for reading temperature fields from a NetCDF file.
    """

    def __init__(self, file_name):

        (
            self.sites,
            self.time,
            self.temperature,
            self.number_fields
        ) = read_temperatures_NetCDF(file_name)


    def to_intensity_provider(self):
        """
        Returns an instance of intensityprovider.IntensityProvider, which later enables access
        to the intensity data point that is closest to a target location.
        """

        intensity_provider = {}

        for k in range(self.number_fields):

            data_k = {}
            all_lats, all_lons = np.meshgrid(self.sites["lat"], self.sites["lon"])
            data_k["lon"] = all_lons.flatten()
            data_k["lat"] = all_lats.flatten()
            data_k["temperature"] = np.transpose(self.temperature[k, :, :]).flatten()

            wrapped_data = DictWithListDataWrapper(
                data=data_k,
                possible_x_columns=["lon"],
                possible_y_columns=["lat"],
            )
            intensity_provider[k] = IntensityProvider(
                intensity_data=wrapped_data, na_value=-1000.0
            )

        return intensity_provider


def read_temperatures_NetCDF(file_name):
    """
    Method for reading temperature fields from a NetCDF file.

    Args:
        file_name (str):
            Full path to the NetCDF file.

    Returns:
        sites (dict)
            Dictionary containing the sites (locations) at which the inundation values are
            provided. Keys:
            - "lon": Longitude (decimal float).
            - "lat": Latitude (decimal float).
        time (arr of float):
            Days since 1949-12-01T00:00:00Z (calendar: proleptic_gregorian).
        temperature (arr of float):
            Array of values of temperatures for each point defined by (lons, lats) and time.
            Dimensions are [time, lat, lon].
        number_fields (int):
            Number of different temperature fields (realisations) in the file. This is the
            "time" dimension of "temperature".
    """

    nc_dataset = Dataset(file_name)

    sites = {}
    sites["lon"] = nc_dataset["lon"][:]
    sites["lat"] = nc_dataset["lat"][:]

    time = nc_dataset["time"][:]

    # Near-Surface Air Temperature, dimensions: [time, lat, lon]
    temperature = nc_dataset["tas"][:].filled(-1000.0)

    # Number of realisations (fields)
    if len(temperature.shape) == 3:
        number_fields = temperature.shape[0]
    elif len(temperature.shape) == 2:
        number_fields = 1
    else:
        error_message = (
            "The dimensions of 'temperature' in %s do not allow to estimate the number of "
            "realisations of the branch. Please check the input NetCDF files"
            % (file_name)
        )
        raise OSError(error_message)

    return sites, time, temperature, number_fields
