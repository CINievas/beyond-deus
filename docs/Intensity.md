# Handling of Intensity Fields

Intensity fields are input as `.xml` files. Each file contains a realisation of the hazard
intensity. Each realisation may contain more than one intensity measure. For example, for
seismic hazard, a realisation of ground motions can contain values for peak ground acceleration
(PGA) and spectral acceleration (SA) at different fundamental periods.

If several intensity fields are input, they must all refer to the same geographic locations, as
the software will determine the nearest neighbour of each target exposure site once, based on
the first intensity field it retrieves.

An example of an intensity field input file can be found [here](../tests/data/intensity_test.xml).
