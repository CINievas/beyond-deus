# Configuration YML File

The software automatically searches for the `config.yml` file. This file should contain the
following parameters:

- `hazard_prefix`: A short string to be used as a prefix in the naming of output files.
  Suggested prefixes: EQ for earthquake, TSU for tsunami, HW for heatwave, FL for flood.
- `input_paths`:
  - `intensity`: This can be:
    - A path to a directory that contains several hazard intensity input files. All files in
    this directory will be processed. If the files are not organised into sub-directories, they
    are all treated as realisations of intensity of one logic tree branch. If the files are
    organised into sub-directories, it is assumed that each sub-directory corresponds to a logic
    tree branch, and all files within are realisations within each branch.
    - A path to one earthquake HDF5 file, which may contain intensity fields for more than one
    logic tree branch and more than one realisations per branch.
  - `fragility`: Path to fragility `.json` file.
  - `exposure_csv`: Path to directory that contains the exposure `.csv` and/or `.zstd` file(s)
  with one row per exposure asset (a number of buildings of a particular building class, in a
  particular damage state, at a particular location). See details [here](Exposure.md). All files
  in this directory will be read by the software and each of them will be used in combination
  with each realisation of intensity of each branch to calculate resulting damage and losses.
  - `exposure_gpkg`: Path to exposure `.gpkg` file with exposure polygons and their centroids.
  There needs to be one polygon for each `building_id` in the exposure `.csv` file. See details
  [here](Exposure.md).
  - `exposure_intensity_combinations`: Path to CSV file indicating the combination of input
  exposure files and input intensity files to be run. Only necessary if `parallelisation_mode`
  (see below) is `by_exposure_intensity_combination`, otherwise write "None" (without quotation
  marks).
  - `conversion_taxonomy`: Path to directory that contains the building taxonomy conversion
  `.json` file. Write "None" (without quotation marks) if this file is not needed, i.e. when the
  building taxonomies of exposure (`building_schema_exposure`) and fragility
  (`building_schema_fragility`) models are the same.
  - `conversion_damage_states`: Path to directory that contains the damage states conversion
  files. All files in this directory will be read. Write "None" (without quotation marks) if
  these files are not needed, i.e. when the damage scales of the input exposure
  (`building_schema_exposure`) and fragility (`building_schema_fragility`) models are the same.
  - `consequence`: Path to `.json` file with the economic consequence model. Write "None"
  (without quotation marks) if economic losses are not to be calculated.
  - `usability`: Path to `.csv` file indicating if buildings in each damage state are usable or
  unusable. This information is used to split the output updated exposure into one usable and
  one unusable file, if `csv_by_usability` is True (see below).
- `output_path`: Path to the folder to which the outputs will be written. If it does not exist,
it will be created. If it exists, it must be empty, otherwise the software will not run (to
avoid overwritting results from previous runs).
- `output_path_profiling`: Path to the folder to which the outputs of `profiling.py` will be
written, if `profiling.py` is manually run.
- `running_mode`: Mode in which the software runs. Currently supported options:
  - `processing`: The software will calculate damage/losses only, without outputting statistics.
  - `post-processing`: The software will only calculate statistics of previously-run
  calculations.
  - `both`: The software will calculate damage/losses as well as the statistics of the current
  calculation.
- `parallelisation_mode`: Parallelisation mode. Currently supported options are:
  - `by_input_exposure`: All possible combinations of input exposure and hazard intensities are
  run. Each CPU will process all hazard intensity branches and realisations for one individual
  input exposure model.
  - `by_intensity_realisation`: All possible combinations of input exposure and hazard
  intensities are run. Each CPU will process one especific combination of a realisation of
  hazard intensity and input exposure model.
  - `by_exposure_intensity_combination`: Only the combinations of input exposure and hazard
  intensities specified in `exposure_intensity_combinations` (see above) are run. Each CPU will
  process one of these combinations.
- `cpus`: Number of processors to be used in the parallelisation of the calculations.
- `parameters`:
  - `building_schema_exposure`: Name of the building classification schema of the input exposure
  (one string).
  - `building_schema_fragility`: Name of the building classification schema of the output, i.e.
  of the fragility model (one string).
  - `intensity_file_type`: Type of intensity input files. Currently supported values: "xml",
  "hdf5" (i.e., earthquake ground motions as output by
  [shakyground2](https://git.gfz.de/shakemap/shakyground2)), "netcdf_tsu" (i.e., tsunami
  inundations as output by [TsunAWI](https://tsunami.awi.de/), and "netcdf_temp" (i.e.,
  temperature fields).
  - `intensity_threshold`: Threshold of hazard intensity, to be used so that if the intensity
  value at a target exposure location is smaller than the threshold, no further damage is
  assumed (i.e., the current damage state remains unmodified and the detailed calculation is
  avoided). WARNING: Setting this threshold is an implicit decision regarding the fragility of
  the exposed assets, be careful!
- `output_types`:  Write True/False next to each option, to export or not export the
corresponding output type:
  - `compress_exposure_csvs`:
    If True, the CSVs containing updated/mapped/(un)usable exposures will be compressed into
    `.zstd` format (which can also be read as input exposure in a subsequent run).
  - `mapped_exposure`:
    - `csv`: The input exposure model, mapped onto the target building and damage schemas (i.e.,
    conversion of building classes and damage states due to compatibility across schemas, not
    the action of the input hazard), is written to a CSV file.
  - `full_updated_exposure`:
    - `csv`: The full updated exposure model is written to a CSV file.
    - `csv_usable`: One CSV file containing the usable assets (rows) of the full updated
    exposure model, as per the `usability` input file.
    - `csv_unusable`: One CSV file containing the unusable assets (rows) of the full updated
    exposure model, as per the `usability` input file.
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
    - `damage_csv_per_realisation`: A summary of number of buildings per final damage state due
    to each realisation of each logic tree branch is written to a CSV file.
    - `damage_gpkg_per_realisation`: The same summary as in `damage_csv_per_realisation` and the
    associated exposure geometries are written to a GeoPackage file.
    - `only_transitioned_damage_csv_per_realisation`: Same as `damage_csv_per_realisation`, but
    keeping only the building_ids for which at least one of the assets transitions damage state.
    - `only_transitioned_damage_gpkg_per_realisation`: Same as `damage_gpkg_per_realisation`,
    but keeping only the building_ids for which at least one of the assets transitions damage
    state.
    - `damage_with_people_csv_per_realisation`: Same as `damage_csv_per_realisation`, plus
    columns with number of census people per damage state.
    - `damage_with_people_gpkg_per_realisation`: Same as `damage_gpkg_per_realisation`, plus
    columns with number of census people per damage state.
- `post_processing`: If `running_mode` is either `post-processing` or `both`, these
post-processing parameters need to be provided for the generation of statistics on damage/loss.
Sub-parameters include:
  - `target_quantiles`: List of quantiles in the range (0.0, 1.0) to be used for calculating
  quantiles of results.
  - `export_weight_per_file`: If True, the weights used for each results file of each
  post-processing ouput will be exported to a CSV. This option is useful to make sure the
  weights are as intended, specially when running in `by_exposure_intensity_combination` mode.
  - `export_filenames_in_all_values_outputs`: If True, the names of the filenames from which
  each value stems are exported to the "all_values" output CSVs.
  - `logic_tree_meta`: Nested dictionaries describing the logic trees of all hazards in the
  chain run so far. The sub-keys need to be integers >= 1, indicating the order in which the
  hazards were applied (1 = first hazard, 2 = second hazard, ...). For each hazard, the subkey
  is a dictionary with the following parameters:
    - `hazard_prefix`: `hazard_prefix` (see above) as used in the associated software run.
    - `logic_tree_path`: Full path to CSV file containing the logic tree associated with this
    hazard (the file contains all names and weights of the logic tree branches; see
    [here](Post_Processing.md)).
    - `weight_of_realisation`: Weight of one realisation of this hazard, independently of the
    branch weight. It must be a float larger than 0 and smaller than or equal to 1.
  - `initial_damage_range`: List of integers designating the initial damage states of the last
  hazard run.
  - `final_damage_range`: List of integers designating the final damage states of the last
  hazard run.
  - `per_branch_which_hazards`: List of hazards (as hazard prefixes from `logic_tree_meta`) for
  which the per-branch results will be post-processed (if options such as
  `by_final_damage_per_branch`, etc., are selected). If the prefixes here do not match those in
  `logic_tree_meta`, no statistics will be produced (for example, if "None" is written), even if
  the corresponding options in `types` are set to True).
  - `types`: Write True/False next to each option, to calculate and export or not each type of
  post-processing output:
    - `by_final_damage_all`: Mean, quantiles and standard deviation of number of buildings,
    incremental loss and cumulative loss, per final damage state, for all branches and
    realisations considered together, with their weights. All individual values are exported as
    well.
    - `by_final_damage_per_branch`: Mean, quantiles and standard deviation of number of
    buildings, incremental loss and cumulative loss, per final damage state, for each branch of
    each hazard run so far.
    - `by_initial_and_final_damage_all`: Mean, quantiles and standard deviation of number of
    buildings, incremental loss and cumulative loss, per combination of initial-final damage
    states, for all branches and realisations considered together, with their weights. All
    individual values are exported as well.
    - `by_initial_and_final_damage_per_branch`: Mean, quantiles and standard deviation of number
    of buildings, incremental loss and cumulative loss, per combination of initial-final damage
    states, for each branch of each hazard run so far.
    - `loss_by_building_id_all`: Mean, quantiles and standard deviation of incremental loss
    (absolute and ratio) and cumulative loss (absolute and ratio) per building_id, for all
    branches and realisations considered together, with their weights.
    - `damage_by_building_id_all`: Mean, quantiles and standard deviation of number and
    proportion of buildings per damage state, per building_id and for all branches and
    realisations considered together, with their weights.
    - `damage_with_people_by_building_id_all`: Mean, quantiles and standard deviation of number
    and proportion of buildings, and number of census people per damage state, per building_id
    and for all branches and realisations considered together, with their weights.
    - `loss_by_building_id_per_branch`: Mean, quantiles and standard deviation of incremental
    loss (absolute and ratio) and cumulative loss (absolute and ratio) per building_id, for each
    branch of each hazard run so far.
    - `damage_by_building_id_per_branch`: Mean, quantiles and standard deviation of number and
    proportion of buildings per damage state, per building_id and for each branch of each hazard
    run so far.
    - `damage_with_people_by_building_id_per_branch`: Mean, quantiles and standard deviation of
    number and proportion of buildings, and number of census people per damage state, per
    building_id and for each branch of each hazard run so far.

An example of a config.yml file can be found [here](../config_example.yml).
