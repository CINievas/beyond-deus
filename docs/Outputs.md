# Outputs

The outputs are exported to the path indicated as `output_path` in the `config.yml` file. The
names of the output files include information on the hazard being run (as specified by the
user by means of the `hazard_prefix` in `config.yml`), the branch of the logic tree and the
realisation of intensity as well as the input exposure model that the results correspond to. The
patter is as follows:

`HAZ_b_BBB_r_RRR_EXPOSUREFILENAME_output_type.extension`

where:

- `HAZ` is the `hazard_prefix` in `config.yml`,
- `BBB` is the name of the hazard intensity logic tree,
- `RRR` is the number of the realisation of hazard intensity, within branch `BBB`,
- `EXPOSUREFILENAME` is the name of the input exposure file, removing the extension, and
- `output_type` is the type of output.

When the software is run several times, using as input for run `B` the updated exposure
from run `A`, the output file names continue to concatenate this information, for example:

`HAZ_B_b_CCC_r_SSS_HAZ_A_b_BBB_r_RRR_EXPOSUREFILENAME_output_type.extension`

Such a file name implies that `HAZ_B`'s branch `CCC`, realisation `SSS` was run after `HAZ_A`,
using the updated exposure from `HAZ_A`, branch `BBB`, realisation `RRR`.

The kind of outputs exported is controlled by the following parameters (True/False) set in the
`config.yml` file under `output_types`:

- `compress_exposure_csvs`:
  If True, the CSVs containing updated/mapped/(un)usable exposures will be compressed into
  `.zstd` format (which can also be read as input exposure in a subsequent run). If False, they
  will be exported as simple CSVs.
- `mapped_exposure`:
  - `csv`: The input exposure model, mapped onto the target building and damage schemas (i.e.,
  conversion of building classes and damage states due to compatibility across schemas, not
  the action of the input hazard), is written to a CSV file.
- `full_updated_exposure`:
  - `csv`: The full updated exposure model is written to a CSV file.
  - `csv_usable`: One CSV file containing the usable assets (rows) of the full updated exposure
  model, as per the `usability` input file and usability status from previously-run calculations
  (i.e., as in the input exposure model(s)).
  - `csv_unusable`: One CSV file containing the unusable assets (rows) of the full updated
  exposure model, as per the `usability` input file and usability status from previously-run
  calculations (i.e., as in the input exposure model(s)).
  - `hdf5_per_realisation`: The full updated exposure model is written to one HDF5 file per
  realisation of each logic tree branch.
- `by_final_damage`:
  - `csv_per_realisation`: A summary of number of buildings, replacement cost and losses of
  the whole portfolio, reported per final damage state, due to each realisation of each logic
  tree branch is written to a CSV file.
- `by_initial_and_final_damage`:
  - `csv_per_realisation`: A summary of number of buildings, replacement cost and losses of
  the whole portfolio, reported per all combinations of initial and final damage states, due
  to each realisation of each logic tree branch is written to a CSV file.
- `by_building_id`:
  - `loss_csv_per_realisation`: A summary of losses per building_id of the exposed assets due
  to each realisation of each logic tree branch is written to a CSV file.
  - `loss_gpkg_per_realisation`: The same summary as in `loss_csv_per_realisation` and the
  associated exposure geometries are written to a GeoPackage file.
  - `only_transitioned_loss_csv_per_realisation`: Same as `loss_csv_per_realisation`, but
  keeping only the building_ids for which at least one of the assets transitions damage state.
  - `only_transitioned_loss_gpkg_per_realisation`: Same as `loss_gpkg_per_realisation`, but
  keeping only the building_ids for which at least one of the assets transitions damage state.
  - `damage_csv_per_realisation`: A summary of number of buildings per final damage state and
  usability status due to each realisation of each logic tree branch is written to a CSV file.
  - `damage_gpkg_per_realisation`: The same summary as in `damage_csv_per_realisation` and the
  associated exposure geometries are written to a GeoPackage file.
  - `only_transitioned_damage_csv_per_realisation`: Same as `damage_csv_per_realisation`, but
  keeping only the building_ids for which at least one of the assets transitions damage state.
  - `only_transitioned_damage_gpkg_per_realisation`: Same as `damage_gpkg_per_realisation`,
  but keeping only the building_ids for which at least one of the assets transitions damage
  state.
  - `damage_with_people_csv_per_realisation`: Same as `damage_csv_per_realisation`, plus columns
  with number of census people per damage state.
  - `damage_with_people_gpkg_per_realisation`: Same as `damage_gpkg_per_realisation`, plus
  columns with number of census people per damage state.

Return to [documentation index](README.md).
