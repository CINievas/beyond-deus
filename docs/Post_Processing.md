# Post-Processing

If `running_mode` is either `post-processing` or `both`, the software will create statistics of
the damage and loss results, by gathering logic tree branches as well as realisations, and
accounting for their weights.

The weights need to be provided as CSV files, one for each of the hazards run so far. Each CSV
file must contain two columns: `branch` and `weight`. The `branch` name needs to match the name
provided in the input intensity file(s), as it is used to name the damage/loss output files. The
weights need to add up to 1.0 (for each individual hazard). This is an example of the contents
of the logic tree CSV file:

```
branch,weight
earthq_1,0.5
earthq_2,0.2
earthq_3,0.3
```
