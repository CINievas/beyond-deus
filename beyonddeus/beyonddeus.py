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
import sys
import logging

from beyonddeus.configuration import Configuration
from beyonddeus.shakemap import Shakemaps

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


def main():

    # Log the start of the run
    logger.info("Beyond-DEUS has started")

    # Read configuration parameters
    config = Configuration("config.yml")

    # Read intensity files
    filenames = os.listdir(config.input_paths["intensity"])
    logger.info("Reading input intensity files: %s files found" % (len(filenames)))
    intensity_provider = {}
    
    for i, filename in enumerate(filenames):
        intensity_provider[i] = Shakemaps.from_file(
            os.path.join(config.input_paths["intensity"], filename)
        ).to_intensity_provider()


if __name__ == "__main__":
    main()
