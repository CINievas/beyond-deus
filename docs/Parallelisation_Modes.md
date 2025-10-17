# Parallelisation Modes

The `parallelisation_mode` attribute in the `config.yml` file allows the user to select how the
damage/loss calculations are parallelised.

Currently supported options are `by_input_exposure` (each CPU will process all hazard intensity
branches and realisations for one individual input exposure model) and 
`by_intensity_realisation` (each CPU will process one especific combination of a realisation of
hazard intensity and input exposure model).

In order to choose between one of the two modes, the user should consider the particular needs
of each run, apart from the capacity of the computer/server in which the software will be run.
For example, if running calculations on a server with many cores, for a case in which there are
thousands of input exposure files but only tens of branches/realisations of hazard intensity,
then `parallelisation_mode=by_input_exposure` is likely to be the best choice. If, on the
contrary, the calculation requires only one input exposure model but thousands of
branches/realisations of hazard intensity, then `parallelisation_mode=by_intensity_realisation`
would be the way to go.
