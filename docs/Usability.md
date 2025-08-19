# Handling of Usability Models

Post-hazard usability models are input as `.csv` files. They are used at the stage of producing
the output, once damage and losses have been calculated, to split the updated exposure model
into a "usable" and an "unusable" dataset.

The CSV file should contain two columns: `damage_state` and `usability`. Under `damage_state`,
the user should list all possible damage states (including no damage, i.e. "0") as integers
(0, ..., N). The labels `usable` and `unusable` should be indicated for each damage state
in the `usability` column.

An example of a fragility model input file can be found [here](../tests/data/usability_test.csv).
