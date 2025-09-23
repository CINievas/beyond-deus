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
import logging
from beyonddeus.shakemap import Shakemaps
from beyonddeus.earthquake_hdf_reader import EQ_HDF_fields
from beyonddeus.tsunami_netcdf_reader import TSU_NetCDF_fields


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def read_intensity_files(intensity_path, intensity_file_type):
    """
    Function to load the intensity fields.

    Two supported input formats:
        (1) A series of .xml or NetCDF files:
            In this case, 'intensity_path' must be a path to a directory in which the files
            are located. If the files are not organised into sub-directories, they are all
            treated as realisations of intensity of one logic tree branch. If the files are
            organised into sub-folders, it is assumed that each sub-folder corresponds to a
            logic tree branch, and all files within are realisations within each branch.
        (2) One HDF5 file in the format of shakyground2 (earthquake ground motion fields,
            https://git.gfz.de/shakemap/shakyground2). The distinction between logic tree
            branches and realisations within each branch is implicit within the HDF5 file in
            this case.

    Args:
        intensity_path (str):
            Path to either (1) a directory containing a series of .xml or NetCDF files or
            (2) an HDF5 file with shakyground2 format (https://git.gfz.de/shakemap/shakyground2).
        intensity_file_type (str):
            Type of intensity input files. Supported values: xml, hdf5.

    Returns:
        intensity_provider (dict):
            Dictionary with two levels of keys. The first level is the name of the logic tree
            branch, while the second level is the realisation number. Within each [key][subkey],
            there is an instance of intensityprovider.IntensityProvider that enables access to
            the intensity data for that specific branch and realisation. If the
            'intensity_file_type' is not a supported format, 'intensity_provider' is empty.
    """

    if intensity_file_type.lower() == "hdf5":

        intensity_provider = EQ_HDF_fields(intensity_path).to_intensity_provider()

        return intensity_provider

    if intensity_file_type.lower() == "xml":

        filenames, sub_dirs = get_list_of_contents(intensity_path)

        intensity_provider = {}

        if len(sub_dirs) > 0 :
            # There are logic tree branches
            logger.info(
                "  %s branches of a logic tree found" % (len(sub_dirs))
            )

            for branch in sub_dirs:
                intensity_provider[branch] = {}

                branch_filenames = os.listdir(os.path.join(intensity_path, branch))
                number_intensity_reals = len(branch_filenames)

                logger.info(
                    "    Branch '%s': %s file(s) found"
                    % (branch, number_intensity_reals)
                )

                for k, filename in enumerate(branch_filenames):
                    intensity_provider[branch][k] = Shakemaps.from_file(
                        os.path.join(intensity_path, branch, filename)
                    ).to_intensity_provider()

        if len(filenames) > 0:
            # Only one logic tree branch
            logger.info(
                "  Only one logic tree branch found, with %s file(s)" % (len(filenames))
            )
            intensity_provider["unique"] = {}

            for k, filename in enumerate(filenames):
                intensity_provider["unique"][k] = Shakemaps.from_file(
                    os.path.join(intensity_path, filename)
                ).to_intensity_provider()

        return intensity_provider

    if intensity_file_type.lower() == "netcdf_tsu":

        filenames, sub_dirs = get_list_of_contents(intensity_path)

        intensity_provider = {}

        if len(sub_dirs) > 0 :
            # There are logic tree branches
            logger.info(
                "      %s branches of a logic tree found" % (len(sub_dirs))
            )

            for branch in sub_dirs:
                intensity_provider[branch] = {}

                branch_filenames = os.listdir(os.path.join(intensity_path, branch))
                number_intensity_reals = len(branch_filenames)

                logger.info(
                    "          Branch '%s': %s file(s) found"
                    % (branch, number_intensity_reals)
                )

                for k, filename in enumerate(branch_filenames):
                    intensity_provider[branch][k] = TSU_NetCDF_fields(
                        os.path.join(intensity_path, branch, filename)
                    ).to_intensity_provider()

        if len(filenames) > 0:
            # Only one logic tree branch
            logger.info(
                "      Only one logic tree branch found, with %s file(s)" % (len(filenames))
            )
            intensity_provider["unique"] = {}

            for k, filename in enumerate(filenames):
                intensity_provider["unique"][k] = TSU_NetCDF_fields(
                    os.path.join(intensity_path, filename)
                ).to_intensity_provider()

        return intensity_provider

    # The intensity_file_type is not supported --> return empty dictionary
    intensity_provider = {}

    return intensity_provider


def get_list_of_contents(intensity_path):
    
    filenames = [
        f for f in os.listdir(intensity_path)
        if os.path.isfile(os.path.join(intensity_path, f))
    ]
    sub_dirs = [
        f for f in os.listdir(intensity_path)
        if os.path.isdir(os.path.join(intensity_path, f))
    ]

    if len(filenames) > 0 and len(sub_dirs) > 0:
        error_message = (
            "The path '%s' contains both files and sub-directories. Only one of the two is "
            "possible, as sub-directories are interpreted as branches of a logic tree."
            % (intensity_path)
        )
        raise OSError(error_message)

    if len(filenames) == 0 and len(sub_dirs) == 0:
        error_message = (
            "The path '%s' contains neither files nor sub-directories. "
            "No intensity input files found."
            % (intensity_path)
        )
        raise OSError(error_message)

    return filenames, sub_dirs