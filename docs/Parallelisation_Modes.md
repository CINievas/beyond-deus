# Parallelisation Modes

The `parallelisation_mode` attribute in the `config.yml` file allows the user to select how the
damage/loss calculations are parallelised.

Currently supported options are:
  - `by_input_exposure`: All possible combinations of input exposure and hazard intensities are
  run. Each CPU will process all hazard intensity branches and realisations for one individual
  input exposure model.
  - `by_intensity_realisation`: All possible combinations of input exposure and hazard
  intensities are run. Each CPU will process one especific combination of a realisation of
  hazard intensity and input exposure model.
  - `by_exposure_intensity_combination`: Only the combinations of input exposure and hazard
  intensities specified in `exposure_intensity_combinations` (in the `config.yml` file) are run.
  Each CPU will process one of these combinations.

In order to choose between one of the three modes, the user should consider the particular needs
of each run, apart from the capacity of the computer/server in which the software will be run.
The first decision to be made is whether the calculation is to combine all possible input
exposure files with all input hazard intensities, in which case the modes `by_input_exposure` or
`by_intensity_realisation` should be used, or whether only the combinations of input exposure
and hazard intensities specified in `exposure_intensity_combinations` are to be run, in which
case the mode needs to be `by_exposure_intensity_combination`.

If running all possible combinations of input exposure and intensity on a server with many
cores, for a case in which there are thousands of input exposure files but only tens of
branches/realisations of hazard intensity, then `parallelisation_mode=by_input_exposure` is
likely to be the best choice. If, on the contrary, the calculation requires only one input
exposure model but thousands of branches/realisations of hazard intensity, then
`parallelisation_mode=by_intensity_realisation` would be the way to go.

When running calculations with multiple input exposure models (i.e., multiple input exposure
`csv` files), it is assumed that all of them correspond to the same set of geometries, defined
in the exposure GeoPackage (`.gpkg`) file.

The `exposure_intensity_combinations` CSV file must contain three columns:

```
exposure_csv,branch,realisation
exposure_01.csv,branch_01,a_real
exposure_02.csv,branch_01,another_real
...
```

In the example above, the input exposure `exposure_01.csv` will be run with realisation`a_real`
of the hazard intensity branch `branch_01`, while `exposure_02.csv1` will be run with
realisation `another_real` of the same branch instead.

Return to [documentation index](README.md).
