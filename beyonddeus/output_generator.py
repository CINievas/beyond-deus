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
import h5py
import numpy as np


class OutputGenerator:
    def __init__(self, output_path, output_types, branch, realisation, updated_exposure):
        """
        Attrs:
            self.output_path (str):
                Path to directory where outputs will be written.
            self.output_types (dict):
                Dictionary indicating the kind of outputs to export, by means of True/False.
                Options are sets of nested keys:
                    "full_updated_exposure":
                        "csv": The full updated exposure model as a CSV file.
                        "hdf5_per_realisation": The full updated exposure model as one HDF5 file
                            per realisation of each logic tree branch.
                        "hdf5_per_branch": The full updated exposure model as one HDF5 file per
                            logic tree branch.
                        "hdf5_for_all": The full updated exposure model as one HDF5 file for all
                            logic tree branches and realisations.
            self.branch (str):
                Name of the logic tree branch that 'updated_exposure' belongs to.
            self.realisation (str):
                Name of the hazard intensity realisation that 'updated_exposure' belongs to,
                within the logic tree branch 'branch'.
            self.updated_exposure (Pandas DataFrame)
                Updated exposure model with damage and losses, as output by Beyond DEUS.
        """
        self.output_path = output_path
        self.output_types = output_types
        self.branch = branch
        self.realisation = realisation
        self.updated_exposure = updated_exposure

    def export(self):
        if self.output_types["full_updated_exposure"]["csv"]:
            out_filename = "b_%s_r_%s_updated_exposure.csv" % (self.branch, self.realisation)
            self.updated_exposure.to_csv(
                os.path.join(self.output_path, out_filename), index=False
            )

        if self.output_types["full_updated_exposure"]["hdf5_per_realisation"]:
            out_filename = "b_%s_r_%s_updated_exposure.hdf5" % (self.branch, self.realisation)
            write_exposure_to_HDF5(
                self.updated_exposure, os.path.join(self.output_path, out_filename)
            )

        if self.output_types["full_updated_exposure"]["hdf5_per_branch"]:
            out_filename = "b_%s_updated_exposure.hdf5" % (self.branch)
            write_exposure_to_HDF5(
                self.updated_exposure,
                os.path.join(self.output_path, out_filename),
                dataset_name=self.realisation
            )

        if self.output_types["full_updated_exposure"]["hdf5_for_all"]:
            out_filename = "updated_exposure_all.hdf5"
            write_exposure_to_HDF5(
                self.updated_exposure,
                os.path.join(self.output_path, out_filename),
                dataset_name="b_%s_r_%s" % (self.branch, self.realisation)
            )


def write_exposure_to_HDF5(exposure, filename, dataset_name="updated_exposure"):
    """
    Args:
        exposure (Pandas DataFrame):
            Exposure Pandas DataFrame.
        filename (str):
            Full path to the HDF5 file to which 'exposure' will be written.
        dataset_name (str):
            Name to be used for the dataset within the HDF5 file. Default: "updated_exposure".
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
