# Handling of Exposure Models

Exposure models are input as GeoJSON (`.json`) files with the following attributes per geometric
feature:

- `gid`: ID of the exposure polygon.
- `expo`: Dictionary in string format, with the following keys and contents:
  - `Taxonomy`: List with the names of the building classes present in the exposure polygon. If
  the exposure polygon contains instances of the same building class but different damage
  states, the name of the building classes needs to be repeated here.
  - `Damage`: List with the names of the damage states associated with the building classes
  listed in `Taxonomy`.
  - `Buildings`: List with the number of buildings in exposure polygon associated with each
  element of `Taxonomy` and `Damage`.
- `cum_loss_value` (optional): Economic losses associated with the exposure polygon from a
previously-run hazard.

`Taxonomy`, `Damage` and `Buildings` must all be of the same length.

Example of "expo":
```
{
    "Taxonomy": [ "bdg_class_1", "bdg_class_2" ],
    "Damage": [ "D0", "D0" ],
    "Buildings": [ 2.5, 5.0 ]
}
```

Examples of input exposure files can be found [here](../tests/data/exposure_test.json) and
[here](../tests/data/exposure_test_with_previous_loss.json).
