# Handling of Fragility Models

Fragility models are input as `.json` files.

When fragility models are defined in terms of a log-normal Cumulative Distribution Function
(CDF), the parameters to be input to the `.json` file are the mean and standard deviation of the
distribution, both in logarithmic space.

An example of a fragility model input file can be found [here](../tests/data/fragility_test.json).
