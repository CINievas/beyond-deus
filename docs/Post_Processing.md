# Post-Processing

If `running_mode` is either `post-processing` or `both`, the software will create statistics of
the damage and loss results, by gathering logic tree branches as well as realisations, and
accounting for their weights.

The branch weights need to be provided as CSV files, one for each of the hazards run so far.
Each CSV file must contain two columns: `branch` and `weight`. The `branch` name needs to match
the name provided in the input intensity file(s), as it is used to name the damage/loss output
files. The weights need to add up to 1.0 (for each individual hazard). This is an example of the
contents of the logic tree CSV file:

```
branch,weight
earthq_1,0.5
earthq_2,0.2
earthq_3,0.3
```

The final weight of each full-path end-branch realisation is calculated as the product of the
weights of all the hazard branches associated with it and the `weight_of_realisation` values of
each hazard specified in the `config.yml` file under `post_processing` > `logic_tree_meta` >
`weight_of_realisation`.

When running the software in either `by_input_exposure` or `by_intensity_realisation` modes, the
`weight_of_realisation` should simply be the inverse of the number of realisations in each
hazard branch.

Special caution is needed when specifying branch and realisation weights for calculations run in
the `by_exposure_intensity_combination` mode instead. As the user can enter any desired
combination of input exposure model and input hazard branch and realisation, it is up to the
user to make sure that the weights input in the logic tree CSV files and `weight_of_realisation`
reflect the combinations provided in the exposure-intensity combination CSV file.

## Example of `by_exposure_intensity_combination` weights

Let us assume the calculation to be post-processed corresponds to a second hazard already. The
logic tree for the first hazard (`HAZ1`) is:

```
branch,weight
haz1_b1,0.75
haz1_b2,0.25
```

The logic tree for the second hazard (`HAZ2`) is:

```
branch,weight
haz2_b1,0.15
haz2_b2,0.35
haz2_b3,0.3
haz2_b4,0.2
```

The exposure-itensity combinations CSV file is:

```
exposure_csv,branch,realisation
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b1,realisation_100
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b2,realisation_101
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b3,realisation_102
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b4,realisation_103
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b1,realisation_100
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b2,realisation_101
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b3,realisation_102
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b4,realisation_103
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b1,realisation_100
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b2,realisation_101
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b3,realisation_102
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b4,realisation_103
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b1,realisation_100
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b2,realisation_101
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b3,realisation_102
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b4,realisation_103
```

This file shows that:
- `HAZ1` has been run over the same initial exposure file, with two realisations (`r_0` and
`r1`) per branch, as reflected in the name of the input exposure files in the first column);
- a different realisation is selected to run each branch of the second hazard (`realisation_100`
for `haz2_b1`, `realisation_101` for `haz2_b2` and so on).

As a consequence, `weight_of_realisation` of `HAZ1` should be 0.5, due to the two realisations
(`r_0` and `r1`) per branch, while `weight_of_realisation` of `HAZ2` should be 1, irrespective
of how many realisations exist as input in the intensity files, because only realisation per
branch is being used. The `logic_tree_meta` info in the `config.yml` file under
`post_processing` should then be:

```
logic_tree_meta:
1:
  hazard_prefix: HAZ1
  logic_tree_path: path_to_HAZ1_logic_tree_file
  weight_of_realisation: 0.5
2:
  hazard_prefix: HAZ2
  logic_tree_path: path_to_HAZ2logic_tree_file
  weight_of_realisation: 1
```

The final weights of each of the exposure-itensity combinations would then be:

```
exposure_csv,branch,realisation
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b1,realisation_100 --> 0.75 * 0.5 * 0.15 * 1 = 0.05625
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b2,realisation_101 --> 0.75 * 0.5 * 0.35 * 1 = 0.13125
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b3,realisation_102 --> 0.75 * 0.5 * 0.30 * 1 = 0.11250
HAZ1_b_haz1_b1_r_0_exposed.zstd,haz2_b4,realisation_103 --> 0.75 * 0.5 * 0.20 * 1 = 0.07500
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b1,realisation_100 --> 0.25 * 0.5 * 0.15 * 1 = 0.01875
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b2,realisation_101 --> 0.25 * 0.5 * 0.35 * 1 = 0.04375
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b3,realisation_102 --> 0.25 * 0.5 * 0.30 * 1 = 0.03750
HAZ1_b_haz1_b2_r_0_exposed.zstd,haz2_b4,realisation_103 --> 0.25 * 0.5 * 0.20 * 1 = 0.02500
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b1,realisation_100 --> 0.75 * 0.5 * 0.15 * 1 = 0.05625
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b2,realisation_101 --> 0.75 * 0.5 * 0.35 * 1 = 0.13125
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b3,realisation_102 --> 0.75 * 0.5 * 0.30 * 1 = 0.11250
HAZ1_b_haz1_b1_r_1_exposed.zstd,haz2_b4,realisation_103 --> 0.75 * 0.5 * 0.20 * 1 = 0.07500
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b1,realisation_100 --> 0.25 * 0.5 * 0.15 * 1 = 0.01875
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b2,realisation_101 --> 0.25 * 0.5 * 0.35 * 1 = 0.04375
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b3,realisation_102 --> 0.25 * 0.5 * 0.30 * 1 = 0.03750
HAZ1_b_haz1_b2_r_1_exposed.zstd,haz2_b4,realisation_103 --> 0.25 * 0.5 * 0.20 * 1 = 0.02500
```

Return to [documentation index](README.md).
