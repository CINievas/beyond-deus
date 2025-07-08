# Handling of Consequence Models

Economic consequence models are input as `.json` files.

Economic consequence models are input as ratios (between 0 and 1) of the full replacement cost
of the building associated with each damage state of the fragility model.

The consequence model input file may also contain the individual replacement costs for each of
the building classes defined in the exposure model. The software is agnostic to the currency of
these costs and assumes that all replacement costs are input in consistent currencies/units.

An example of a consequence model input file can be found [here](../tests/data/consequence_costs_test.json).
