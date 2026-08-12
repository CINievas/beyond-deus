# Handling of Intensity Fields

Intensity fields can be input in different ways and formats:
- `.xml` files: Each file contains a realisation of the hazard intensity. Each realisation may
contain more than one intensity measure. For example, for seismic hazard, a realisation of
ground motions can contain values for peak ground acceleration (PGA) and spectral acceleration
(SA) at different fundamental periods. More than one file can be provided under the path defined
in the [configuration file](Configuration.md). If the files are not organised into
sub-directories, they are all treated as realisations of intensity of one logic tree branch. If
the files are organised into sub-directories, it is assumed that each sub-directory corresponds
to a logic tree branch, and all files within are realisations within each branch.
- Earthquake ground motion `.hdf5` files (generated with
[shakyground2](https://git.gfz.de/shakemap/shakyground2)): Only one file is provided, and this
file may contain several realisations of ground motions for different logic tree branches.
- Tsunami inundation depth `NetCDF` files (generated with [TsunAWI](https://tsunami.awi.de/)):
Each file contains a realisation of the tsunami intensity. More than one file can be provided
under the path defined in the [configuration file](Configuration.md). If the files are not
organised into sub-directories, they are all treated as realisations of intensity of one logic
tree branch. If the files are organised into sub-directories, it is assumed that each
sub-directory corresponds to a logic tree branch, and all files within are realisations within
each branch.
- Temperature fields in `NetCDF` files. The software expects at least one sub-directory under
the path defined in the [configuration file](Configuration.md), and only one `NetCDF` file per
sub-directory. Each sub-directory (and thus, each file) is interpreted as a logic tree branch,
which is assumed to contain one or more realisations for that branch.
- Flood flow depth `NetCDF` files: Each file contains a realisation of the flood intensity,
which is assumed to be "flow_depth". More than one file can be provided under the path defined
in the [configuration file](Configuration.md). If the files are not organised into
sub-directories, they are all treated as realisations of intensity of one logic tree branch. If
the files are organised into sub-directories, it is assumed that each sub-directory corresponds
to a logic tree branch, and all files within are realisations within each branch.

In each run of Beyond DEUS, all intensity files must be of the same kind.

If several intensity fields are input, they must all refer to the same geographic locations, as
the software will determine the nearest neighbour of each target exposure site once, based on
the first intensity field it retrieves.

An example of an intensity field input file can be found [here](../tests/data/intensity_test.xml).

Return to [documentation index](README.md).
