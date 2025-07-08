# Handling of Schema Mapping

## Compatibility Matrix of Building Taxonomies

The compatibility matrix between building classes of two different taxonomies is input as a
`.json` file.

An example of a taxonomy compatibility input file can be found
[here](../tests/data/conversion_taxonomy/conversion_taxonomy_test.json).

## Compatibility Matrices of Damage States

The compatibility matrices between damage states of different damage scales and associated with
building classes of different taxonomies are input as a series of `.json` files, one for each
possible combination of building classes from the two taxonomies.

In each file, the compatibility matrix is defined as a dictionary in which the primary keys
correspond to the target damage states while the sub-keys correspond to the source damage
states. For example:

```
"source_damage_states": [0, 1, 2, 3],
"target_damage_states": [0, 1, 2, 3, 4],
"conv_matrix": {
    "0": {"0": 0.05, "1": 0.01, "2": 0.00, "3": 0.00},
    "1": {"0": 0.75, "1": 0.65, "2": 0.10, "3": 0.04},
    "2": {"0": 0.20, "1": 0.30, "2": 0.45, "3": 0.06},
    "3": {"0": 0.00, "1": 0.04, "2": 0.35, "3": 0.10},
    "4": {"0": 0.00, "1": 0.00, "2": 0.10, "3": 0.80}
}
```

In the example, one building originally in damage state 0 (as per the source damage scale) gets
decomposed into 0.05 buildings in damage state 0, 0.75 buildings in damage state 1, and 0.20
buildings in damage state 2.

Examples of damage scale compatibility input files can be found
[here](../tests/data/conversion_damage).
