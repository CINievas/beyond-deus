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

import h5py
import numpy as np


def write_exposure_to_HDF5(exposure, filename, dataset_name="updated_exposure"):
    """
    Args:
        exposure (Pandas DataFrame)
        filename (str)
    """
    fle = h5py.File(filename, "a")

    # NOTE: It was not possible to use pandas.DataFrame.to_records() directly because
    # of problems converting the string columns in 'exposure'

    # Define the structure (data types) and data of the Numpy Structured Array
    # to be used to create the HDF5 file
    arr_structure = {}
    arr_data = {}

    for col in exposure:
        if col in ["id", "building_id", "taxonomy"]:
            # String columns need special care!
            str_length = exposure[col].str.len().max()
            arr_col = exposure[col].to_numpy().astype((np.bytes_, str_length))
        else:
            # Simple conversion for all other data types (int, float)
            arr_col = exposure[col].to_numpy()

        arr_data[col] = arr_col
        arr_structure[col] = arr_col.dtype

    arr_dtype = np.dtype(list(arr_structure.items()))

    # Create the Numpy Structured Array
    exposure_arr = np.zeros(exposure.shape[0], arr_dtype)
    for col in arr_data:
        exposure_arr[col] = arr_data[col]

    # Write the Numpy Structured Array to the HDF5 file
    exposure_ctxt = fle.create_dataset(
        dataset_name,
        exposure_arr.shape,
        dtype=exposure_arr.dtype,
    )
    exposure_ctxt[:] = exposure_arr

    fle.close()
