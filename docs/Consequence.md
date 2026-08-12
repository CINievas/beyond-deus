# Handling of Consequence Models

Economic consequence models are input as `.json` files.

Economic consequence models are input as ratios (between 0 and 1) of the full replacement cost
of the building associated with each damage state of the fragility model.

Conceptually, economic loss ratios can be larger than 1 when accounting for the additional costs
of demolishing the remains of the building and clearing out the rubble. However, the current
version of the software is limited to values up to 1, as a means to guarantee that total
cumulative losses are not fictitiously inflated as an artifact of using different consequence
models for different hazards.

An example of a consequence model input file can be found [here](../tests/data/consequence_test.json).

Return to [documentation index](README.md).
