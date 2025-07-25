# Handling of Exposure Models

Exposure models are input as a combination of one `.csv` file and one GeoPackage (`.gpkg`) file.

Each row of the `.csv` file is referred to as an "asset". An "asset" is herein defined as a
number of buildings of a particular building class, in a particular damage state, at a
particular location. Each asset is characterised by the following parameters, which are the
columns of the `.csv` file:

- `id` (str): Unique ID of the asset.
- `building_id` (str): ID of the exposure polygon that the asset belongs to. One exposure polygon
(i.e., a geographic area) can contain several assets (i.e., buildings of different building
classes in different damage states).
- `taxonomy` (str): Building class of the asset.
- `initial_damage` (str): Initial damage state of the asset. "Initial" refers to the start of
the current calculation.
- `number` (float): Number of buildings in the asset. It does not need to be an integer.
- `replacement_cost_tot` (float): Total replacement cost of all the buildings in the asset. The
replacement cost per building is equal to `replacement_cost_tot/number`.
- `cum_loss_value` (float): Economic loss associated with the asset from a previously-run
calculation (i.e., a hazardous event that occurred before).

The GeoPackage (`.gpkg`) file contains the exposure polygons associated with each `building_id`
of the `.csv` file. For each `building_id`, the file must contain the following data:

- `geometry`: The geometry of the exposure polygon.
- `centroid_lon` (float): Longitude (decimal degrees) of the centroid of the exposure polygon.
- `centroid_lat` (float): Latitude (decimal degrees) of the centroid of the exposure polygon.

The coordinates of the centroid are used to determine the hazard intensity measure of the assets
in the exposure polygon. The user can decide whether these coordinates refer to the geometric
centroid or to any other location they deem relevant for the determination of the hazard
intensity (e.g., weighted centroid, see
[Dabbeek et al., 2021](https://link.springer.com/article/10.1007/s10518-021-01194-x)).

Examples of input exposure files can be found here: [csv](../tests/data/exposure.csv),
[csv](../tests/data/exposure_polygons.gpkg).
