# Handling of Usability Models

Post-hazard usability models are input as `.csv` files. The CSV file should contain two columns:
`damage_state` and `usability`. Under `damage_state`, the user should list all possible damage
states (including no damage, i.e. "0") as integers (0, ..., N). The labels `usable` and
`unusable` should be indicated for each damage state in the `usability` column.

An example of a usability model input file can be found [here](../tests/data/usability_test.csv).

The usability status of an exposed asset depends not only on the relation between its final
damage state from the current calculation and the usability model, but also on its cumulative
usability status from previous calculations. This is done to prevent assets from changing
usability status based solely on conversions of damage across damage scales. Firstly, a building
whose damage state does not change with the current hazard should not change its usability
status. Secondly, if previously assessed as unusable, it should not become usable simply for
using a different damage scale. The new usability status is thus calculated as follows:
- If the input exposure models do not contain a `cum_usability` column, the software assumes
that all assets are usable.
- If an asset does not transition damage states in the current calculation, it keeps its
previous usability status (as in the input exposure model).
- If an asset transitions damage states in the current calculation, it usability status is
updated. The asset is usable only if (1) its previous status was "usable" and (2) the new damage
state corresponds to a "usable" category of the input usability `.csv` file.

The usability status is exported to the updated exposure models, if the latter are requested as
outputs in the `config.yml` file. The usability status can also be used to split the updated
exposure model(s) into a "usable" and an "unusable" dataset, also if requested in the
`config.yml` file.

If no usability classification is desired, the user can enter "None" under `usability` in the
`config.yml` file. In this case, the `cum_usability` column from the input exposure model(s) is
kept as the current usability status.

Return to [documentation index](README.md).
