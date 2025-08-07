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

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

class IntensityProvider:
    """
    Class copied and adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class for retrieving the intensities at a location.
    
    Attributes:
        self._intensity_data
        self._na_value (float):
            Value to be returned by get_nearest() when the queried coordinates are too far away
            from the locations of the input intensities.
        self._spatial_index:
            scipy.spatial._ckdtree.cKDTree object, i.e., "kd-tree for quick nearest-neighbor
            lookup".
        self._max_dist (float):
            Maximum distance allowed between a queried location and its nearest neighbour. If
            the distance between the queried location and its nearest neighbour is longer than
            this value, get_nearest() returns self._na_value.
            This maximum distance is calculated by _estimate_max_dist() as the maximum distance
            between any point of self._intensity_data and its four nearest neighbours. If the
            input intensity data (self._intensity_data) is a regular grid with spacing dx and
            dy, then self._max_dist = sqrt(dx^2 + dy^2).
    """
    def __init__(self, intensity_data, na_value=0.0):
        self._intensity_data = intensity_data
        self._na_value = na_value
        self._spatial_index = self._build_spatial_index()
        self._max_dist = self._estimate_max_dist()

    def _build_spatial_index(self):
        coords = self._get_coords()
        return cKDTree(coords)

    def _get_coords(self):
        x_coordinates = self._intensity_data.get_list_x_coordinates()
        y_coordinates = self._intensity_data.get_list_y_coordinates()
        coords = np.array(list(zip(x_coordinates, y_coordinates)))
        return coords

    def _estimate_max_dist(self, n_nearest_neighbours=4):
        """
        Calculate maximum distance between any point of self._intensity_data and their 4
        (or n_nearest_neighbours) nearest neighbours.

        By using 4 nearest neighbours, if the input intensity grid is a regular grid, then
        the maximum distance ends up being the diagonal distance between grid points. If
        the spacing of the grid is dx and dy, then max_dist = sqrt(dx^2 + dy^2).
        """

        coords = self._get_coords()  # N x 2 array (cols: lon, lat)
        # Distances between each point and its n_nearest_neighbours (4), N x 4 array
        dists, _ = self._spatial_index.query(coords, k=n_nearest_neighbours)
        # Ignore first column, which is distance between points and themselves
        dists_without_nearests = dists[:, 1:]

        return np.max(dists_without_nearests)

    def get_nearest(self, lon, lat):
        """
        Returns a dict with the values of the intensities that the provider has at a given
        location (longitude, latitude).

        If the point is too far away from all of the intensity measurements (i.e., more distant
        to its nearest neighbour than self._max_dist), the returned value is self._na_value.

        Returns:
            intensities (dict):
                Dictionary with as many keys as intensity measures in self._intensity_data, and
                values associated with the nearest neighbour of the requested (lon, lat).
        """
        coord = np.array([lon, lat])
        dist, idx = self._spatial_index.query(coord, k=1)

        intensities = {}

        for column in self._intensity_data.get_data_columns():  # each column is an IM
            if dist <= self._max_dist:
                value = self._intensity_data.get_value_for_column_and_index(
                    column=column,
                    index=idx
                )
            else:
                value = self._na_value

            intensities[column] = value

        return intensities

    def get_values_at_position(self, target_position):
        """
        Returns a dict with the values of the intensities that the provider has at a given
        position of the data.

        If the 'target_position' is a negative number, it is assumed that the target point is
        too far away from all of the intensity points, and the returned value is self._na_value.

        Args:
            target_position (integer):
                Position of the target intensity point, as in "self._intensity_data".

        Returns:
            intensities (dict):
                Dictionary with as many keys as intensity measures in self._intensity_data, and
                values associated with the requested 'target_position'.
        """
        intensities = {}

        for column in self._intensity_data.get_data_columns():  # each column is an IM
            if target_position >= 0:
                value = self._intensity_data.get_value_for_column_and_index(
                    column=column,
                    index=target_position
                )
            else:
                value = self._na_value

            intensities[column] = value

        return intensities

    def get_values_at_multiple_positions(self, intensity_positions, intensity_threshold):
        """
        This method retrieves the hazard intensity values at all hazard positions specified in
        the input 'intensity_positions', and determines, for each "building_id" in
        'intensity_positions', whether the hazard intensity values exceed 'intensity_threshold'.
        The output is a Pandas DataFrame with the hazard intensity values for all intensity
        measure types and a boolean column "run". For any "building_id" (i.e., row of the
        DataFrame), if "run" is False, it means that all hazard intensity values are lower than
        'intensity_threshold'. If "run" is True, at least one hazard intensity value is larger
        than 'intensity_threshold'.

        Args:
            intensity_positions (Pandas DataFrame):
                DataFrame with index "building_id", indicating the ID of exposure polygons, and
                one column "nearest_neighbour", with the position of the nearest neighbour site
                of the hazard intensitiy fields.
            intensity_threshold (float):
                Threshold of hazard intensity, to be used so that if the intensity value at a
                target exposure location is smaller than the threshold, no further damage is
                assumed.

        Returns:
            all_intensities (Pandas DataFrame):
                DataFrame with index "building_id", indicating the ID of exposure polygons, and
                the following columns:
                    - "nearest_neighbour" (int):
                        The position of the nearest neighbour site (as in 'intensity_positions')
                    - One column per intensity measure type, containing the hazard intensity
                    values (float) associated with that intensity measure type.
                    - "run" (bool):
                        True if at least one of the hazard intensity values is larger than
                        'intensity_threshold', False if all of them are smaller (for each row).
        """

        target_positions = intensity_positions["nearest_neighbour"]
        unique_target_positions = target_positions.unique()

        intensities = {}

        for target_pos in unique_target_positions:
            intensities[target_pos] = self.get_values_at_position(target_pos)

        # The intensity measure types are the same for all points
        intensities_keys = list(intensities.keys())
        intensity_measure_types = intensities[intensities_keys[0]].keys()

        # Initialise output DataFrame
        all_intensities = intensity_positions.copy()
        # In all_intensities: index=building_id, col="nearest_neighbour"

        # Add a column for each intensitiy measure type, and an auxiliary boolean column to know
        # if the intensity value exceeds the intensity threshold
        for imt in intensity_measure_types:
            all_intensities[imt] = [intensities[pos][imt] for pos in target_positions]
            all_intensities["%s_run" % (imt)] = (all_intensities[imt] >= intensity_threshold)

        # The building_id needs to be run (to calculate damage) if any of the intensity values
        # exceeds the threshold (even if some other intensity values do not):
        all_intensities["run"] = [False for i in range(all_intensities.shape[0])]

        for imt in intensity_measure_types:
            all_intensities["run"] = (all_intensities["run"] | all_intensities["%s_run" % (imt)])
            all_intensities.drop(columns=["%s_run" % (imt)], inplace=True)  # delete aux columns

        return all_intensities

    def identify_nearest_neighbours(self, target_locations, not_available=-999):
        """
        This function determines the position of the nearest neighbours of all elements of
        'target_locations'. If the nearest neighbour is too far away from the target location
        (i.e., distance larger than self._max_dist), the returned position is 'not_available'.

        Args:
            target_locations (NumPy array):
                Array with two columns, first longitude, second latitude, and as many rows as
                target locations of interest.
            not_available (int):
                Position value to return if the nearest neighbour is too far away from the target
                location. Default value: -999.

        Returns:
            nearest_neighbours (NumPy array):
                Array with one element per row of 'target_locations'. It contains the position
                of the nearest neighbour of each target location in self._intensity_data.
        """
        nearest_neighbours = np.zeros(target_locations.shape[0], dtype=int)
        aux_distances = np.zeros(target_locations.shape[0])

        for i, coord in enumerate(target_locations):
            aux_distances[i], nearest_neighbours[i] = self._spatial_index.query(coord, k=1)

        nearest_neighbours[np.where(aux_distances > self._max_dist)[0]] = not_available

        return nearest_neighbours
