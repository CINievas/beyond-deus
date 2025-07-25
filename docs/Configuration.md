# Configuration YML File

The software automatically searches for the `config.yml` file. This file should contain the
following parameters:

- `input_paths`:
  - `intensity`: Path to directory that contains the hazard intensity input files. All files in
  this directory will be processed.
  - `fragility`: Path to fragility `.json` file.
  - `exposure_csv`: Path to exposure `.csv` file with one row per exposure asset (a number of
  buildings of a particular building class, in a particular damage state, at a particular
  location). See details [here](Exposure.md).
  - `exposure_gpkg`: Path to exposure `.gpkg` file with exposure polygons and their centroids.
  There needs to be one polygon for each `building_id` in the exposure `.csv` file. See details
  [here](Exposure.md).
  - `conversion_taxonomy`: Path to directory that contains the building taxonomy conversion
  `.json` file. Write "None" (without quotation marks) if this file is not needed, i.e. when the
  building taxonomies of exposure (`building_schema_exposure`) and fragility
  (`building_schema_fragility`) models are the same.
  - `conversion_damage_states`: Path to directory that contains the damage states conversion
  files. All files in this directory will be read. Write "None" (without quotation marks) if
  these files are not needed, i.e. when the damage scales of the input exposure
  (`building_schema_exposure`) and fragility (`building_schema_fragility`) models are the same.
  - `consequence`: Path to `.json` file with the economic consequence model.
- `output_path`: Path to the folder to which the outputs will be written. If it does not exist,
it will be created. If it exists, it must be empty, otherwise the software will not run (to
avoid overwritting results from previous runs).
- `parameters`:
  - `building_schema_exposure`: Name of the building classification schema of the input exposure
  (one string).
  - `building_schema_fragility`: Name of the building classification schema of the output, i.e.
  of the fragility model (one string).

An example of a config.yml file can be found [here](../config_example.yml).
