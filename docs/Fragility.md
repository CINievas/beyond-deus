# Handling of Fragility Models

Fragility models are input as `.json` files.

Currently supported functional forms are:
- Log-normal Cumulative Distribution Function (CDF)
- Logistic function (`1.0 / (1.0 + exp(a * intensity + b))`)

When fragility models are defined in terms of a log-normal Cumulative Distribution Function
(CDF), the parameters to be input to the `.json` file are the mean and standard deviation of the
distribution, both in logarithmic space.

When fragility models are defined in terms of a logistic function, the parameters to be input to
the `.json` file are `a` and `b` of the equation `1.0 / (1.0 + exp(a * intensity + b))`. It is
assumed that the units in which `intensity` will be input in the [intensity fields](Intensity.md)
will be compatible with those implied by the fragility model.

Examples of fragility model input files can be found here:
- [Log-normal CDF](../tests/data/fragility_test.json)
- [Logistic function](../tests/data/fragility_test_logistic.json)

Return to [documentation index](README.md).
