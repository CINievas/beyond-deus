#!/usr/bin/env python3

# Copyright (C) 2025:
#  GFZ Helmholtz-Zentrum für Geoforschung | GFZ Helmholtz Centre for Geosciences
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

import collections
import json
import re

import numpy as np
from scipy.stats import lognorm


FactoryCacheKey = collections.namedtuple("FactoryCacheKey", ["mean", "stddev"])


class LogncdfFactory:
    """
    Class copied and adapted from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    This class is a factory for fragility models defined by the log-normal CDF.
    """

    def __init__(self):
        self.cache = {}

    def __call__(self, mean, stddev):
        """
        Args:
            mean (float): Mean in logarithmic space.
            stddev (float): Standard deviation in logarithmic space.
        """
        key = FactoryCacheKey(mean, stddev)

        if key in self.cache.keys():
            return self.cache[key]

        func = lognorm(scale=np.exp(mean), s=stddev)

        result = CachedFunction(func.cdf)

        self.cache[key] = result
        return result


class AllOnes:
    """
    This class returns 1 for all values equal to or larger than 0,
    and 0 for all values smaller than 0.
    
    """
    def __init__(self):
        """No parameters are needed"""
        pass

    def __call__(self, value):
        if value < 0:
            return 0.0
        else:
            return 1.0


class AllZeroes:
    """
    This class returns 0 for all input values.
    
    """
    def __init__(self):
        """No parameters are needed"""
        pass

    def __call__(self, value):
        return 0.0


class UnitPoE:
    """
    This class is a factory for fragility models defined by probability of exceedance (PoE)
    equal to 1 for all values of the IM >=0.
    """

    def __init__(self):
        self.cache = {}

    def __call__(self, mean=np.inf, stddev=0.0):
        """
        Args:
            mean
            stddev
        """
        key = FactoryCacheKey(mean, stddev)

        if key in self.cache.keys():
            return self.cache[key]

        func = AllOnes()

        result = CachedFunction(func)

        self.cache[key] = result
        return result


class NullPoE:
    """
    This class is a factory for fragility models defined by probability of exceedance (PoE)
    equal to 0 for all values of the IM.
    """

    def __init__(self):
        self.cache = {}

    def __call__(self, mean=np.inf, stddev=0.0):
        """
        Args:
            mean
            stddev
        """
        key = FactoryCacheKey(mean, stddev)

        if key in self.cache.keys():
            return self.cache[key]

        func = AllZeroes()

        result = CachedFunction(func)

        self.cache[key] = result
        return result


SUPPORTED_FRAGILITY_FUNCTION_FACTORIES = {
    "logncdf": LogncdfFactory(),
    "allones": UnitPoE(),
    "allzeroes": NullPoE(),
}


class CachedFunction:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to cache function calls.
    """

    def __init__(self, inner_function):
        """Init the instance with the given function."""
        self.inner_function = inner_function
        self.cache = {}

    def __call__(self, value):
        """Call the function with the value."""

        if value in self.cache.keys():
            return self.cache[value]

        result = self.inner_function(value)

        self.cache[value] = result

        return result


class DamageState:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to represent an individual fragility curve for a specific damage state.
    
    Example of use:
        dmg_state.get_probability_for_intensity({"PGA": 0.5}, {"PGA": "g"}):
            Returns the probability of exceedance of dmg_state.to_state, given an initial
            dmg_state.from_state, for a building with class dmg_state.taxonomy and the intensity
            measure's value and units passed on as arguments (i.e., PGA = 0.5 g in this
            example).
    """

    def __init__(
        self,
        taxonomy,
        from_state,
        to_state,
        intensity_field,
        intensity_unit,
        fragility_function,
    ):
        """
        Args:
            taxonomy (str):
                Name of the building class.
            from_state (int):
                Initial damage state.
            to_state (int):
                Final damage state.
            intensity_field (str):
                Name of intensity measure (IM).
            intensity_unit (str):
                Units of intensity measure.
            fragility_function (CachedFunction)                
        """

        self.taxonomy = taxonomy
        self.from_state = from_state
        self.to_state = to_state
        self.intensity_field = intensity_field.upper()
        self.intensity_unit = intensity_unit
        self.fragility_function = fragility_function

    def get_probability_for_intensity(self, intensity, units):
        """
        Returns the probability of occurrence for the given intensity.

        The intensity and units are given as dicts, for example:
        intensity = {
            'PGA': 1.0,
            'STDDEV_PGA': 7.0
        }
        units = {
            'PGA': 'g',
            'STDDEV_PGA': 'g'
        }

        This method returns an exception if the unit for the
        fragility function is not the expected one.
        """

        field = self.intensity_field
        value = intensity[field]
        unit = units[field]

        if unit != self.intensity_unit:
            raise Exception("Not supported IM unit")

        return self.fragility_function(value)


class Fragility:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to represent the whole fragility model (all curves associated with all building
    classes and all damage state transitions).
    
    Example of use:
        frag = Fragility(data) (where data = dictionary)
        fragprov = frag.to_fragility_provider()
        fragprov.get_taxonomies(): list of building classes
        fragprov.get_damage_states_for_taxonomy("bdg_class"): list of DamageState objects. Each
            DamageState object represents one fragility curve of the model.
    """

    def __init__(self, data):
        self._data = data

    @classmethod
    def from_file(cls, json_file):
        """
        Reads the data from a given json file.
        """
        with open(json_file, "rt") as input_file:
            # Load all of the json file into a 'data' dictionary
            data = json.load(input_file)

        return cls(data)  # instantiate Fragility(data) (__init__)

    def to_fragility_provider_with_specified_fragility_function(
        self, fragility_function
    ):
        """
        Transforms the data, so that a
        provider for the supported taxonomies
        and the damage states (with the fragility functions)
        are returned.
        """

        damage_states_by_taxonomy = collections.defaultdict(list)

        shape = self._data["meta"]["shape"]

        for dataset in self._data["data"]:
            taxonomy = dataset["taxonomy"]
            intensity_field = dataset["imt"]
            intensity_unit = dataset["imu"]

            for damage_state_mean_key in [
                k
                for k in dataset.keys()
                if k.startswith("D") and k.endswith("_mean")
            ]:
                #
                # the data is in the format
                # D1_mean, D2_mean, D3_mean
                # (as there are is no from data state at the moment)
                # but this code can also handle them the in the way
                # D01, so that it is the damage state from 0 to 1 or
                # D_0_1 or D0_1
                #
                to_state = int(
                    re.search(r"(\d)_mean$", damage_state_mean_key).group(1)
                )
                from_state = int(
                    re.search(r"^D_?(\d)_", damage_state_mean_key).group(1)
                )

                if to_state == from_state:
                    # there is no from state given
                    # both regexp read the same value
                    from_state = 0

                mean = dataset[damage_state_mean_key]
                stddev = dataset[
                    damage_state_mean_key.replace("_mean", "_stddev")
                ]

                damage_state = DamageState(
                    taxonomy=taxonomy,
                    from_state=from_state,
                    to_state=to_state,
                    intensity_field=intensity_field,
                    intensity_unit=intensity_unit,
                    fragility_function=fragility_function(mean, stddev),
                )

                damage_states_by_taxonomy[taxonomy].append(damage_state)

        Fragility._add_damage_states_if_missing(damage_states_by_taxonomy)

        schema = self._data["meta"]["id"]

        return FragilityProvider(damage_states_by_taxonomy, schema)

    def to_fragility_provider(self):
        """
        Transforms the data, so that a
        provider for the supported taxonomies
        and the damage states (with the fragility functions)
        are returned.
        """

        shape = self._data["meta"]["shape"]
        fragility_function = SUPPORTED_FRAGILITY_FUNCTION_FACTORIES[shape]

        return self.to_fragility_provider_with_specified_fragility_function(
            fragility_function
        )

    @staticmethod
    def _add_damage_states_if_missing(damage_states_by_taxonomy):
        """
        Adds missing damage states for example from 1 to 2, 2 to 3, 1 to 3, ...
        if just the 0 to x are given.
        """

        for taxonomy in damage_states_by_taxonomy.keys():
            Fragility._add_damage_states_if_missing_to_dataset_list(
                damage_states_by_taxonomy[taxonomy], taxonomy
            )

    @staticmethod
    def _add_damage_states_if_missing_to_dataset_list(damage_states, taxonomy_name):
        """
        This method identifies the "largest" damage state (i.e., the damage state with the
        largest number as name) and makes sure that fragility curves exist for all non-trivial
        damage state transitions.
        
        For example, if 'max_damage_state' is 3, then it will check that all of the following
        curves exist:
        - DS1, DS2 and DS3 given DS0
        - DS1, DS2 and DS3 given DS1
        - DS1, DS2 and DS3 given DS2 
        - DS1, DS2 and DS3 given DS3
        
        If any of the curves do not exist, they are created as follows. For an initial damage
        state 'from_damage_state' and final damage state 'to_damage_state'
        - If from_damage_state == to_damage_state: The fragility curve is a step function with
        PoE=0 for IM<0 and PoE=1 for IM>=0.
        - If from_damage_state > to_damage_state: The fragility curve returns zero for all
        values of the IM (it is not allowed to go back to a lower damage state).
        - If from_damage_state < to_damage_state: The fragility curve for
        (from_damage_state - 1) and to_damage_state is retrieved. This assumes that this curve
        always exists.

        Args:
            damage_states (list of DamageState objects):
                Existing (from input source) damage states for building class 'taxonomy_name'.
            taxonomy_name (str):
                Name of the building class the 'damage_states' refer to.
        """

        max_damage_state = max([ds.to_state for ds in damage_states])

        # Identify the IM type
        im_types = np.array([ds.intensity_field for ds in damage_states])
        if len(np.unique(im_types)) == 1:
            im_type = np.unique(im_types)[0]
        else:
            raise ValueError(
                "The IM type of fragility curves for %s is different for different damage states"
                % (taxonomy_name)
            )

        # Identify the IM unit
        im_units = np.array([ds.intensity_unit for ds in damage_states])
        if len(np.unique(im_units)) == 1:
            im_unit = np.unique(im_units)[0]
        else:
            raise ValueError(
                "The IM units of fragility curves for %s is different for different damage states"
                % (taxonomy_name)
            )

        for from_damage_state in range(0, max_damage_state + 1):
            for to_damage_state in range(1, max_damage_state + 1):
                ds_option = [
                    ds
                    for ds in damage_states
                    if ds.from_state == from_damage_state
                    and ds.to_state == to_damage_state
                ]  # search for this fragility curve in 'damage_states'
                
                if ds_option and from_damage_state >= to_damage_state:
                    # It found an input curve for transitioning from a larger to a lower state
                    error_message = (
                        "The fragility model contains input curves for transitioning from "
                        "damage state %s to damage state %s. "
                        "Reducing the damage state is not allowed."
                        % (from_damage_state, to_damage_state)
                    )
                    raise ValueError(error_message)

                if not ds_option:  # if fragility not already in 'damage_states'
                    if from_damage_state == to_damage_state:
                        # Starting and finishing DS is the same, so the PoE is 1 for all values
                        # of the IM
                        fragility_function = UnitPoE()
                        ds_new = DamageState(
                            taxonomy=taxonomy_name,
                            from_state=from_damage_state,
                            to_state=to_damage_state,
                            intensity_field=im_type,
                            intensity_unit=im_unit,
                            fragility_function=fragility_function(),
                        )
                        damage_states.append(ds_new)
                    elif from_damage_state > to_damage_state:
                        # Starting with a larger damage state and finishing with a lower one
                        # (PoE = 0 for all values of the IM)
                        fragility_function = NullPoE()
                        ds_new = DamageState(
                            taxonomy=taxonomy_name,
                            from_state=from_damage_state,
                            to_state=to_damage_state,
                            intensity_field=im_type,
                            intensity_unit=im_unit,
                            fragility_function=fragility_function(),
                        )
                        damage_states.append(ds_new)
                    else:
                        # Try to take the fragility corresponding to one degree less of
                        # "from damage state" (e.g., if trying to define DS3 conditioned on DS1,
                        # search for DS3 conditioned on DS0)
                        ds_option_lower = [
                            ds
                            for ds in damage_states
                            if ds.from_state == from_damage_state - 1
                            and ds.to_state == to_damage_state
                        ]
                        if ds_option_lower:
                            ds_lower = ds_option_lower[0]
                            ds_new = DamageState(
                                taxonomy=taxonomy_name,
                                from_state=from_damage_state,
                                to_state=to_damage_state,
                                intensity_field=ds_lower.intensity_field,
                                intensity_unit=ds_lower.intensity_unit,
                                fragility_function=ds_lower.fragility_function,
                            )
                            damage_states.append(ds_new)
                        else:
                            error_message = (
                                "It was not possible to identify a suitable fragility curve "
                                "for %s, for transitioning from damage state %s to "
                                "damage state %s. "
                                % (taxonomy_name, from_damage_state, to_damage_state)
                            )
                            raise OSError(error_message)


class FragilityProvider:
    """
    Class copied from:
        Brinckmann, Nils; Gomez-Zapata, Juan Camilo; Pittore, Massimiliano; Rüster, Matthias
        (2021): DEUS: Damage-Exposure-Update-Service. V. 1.0. GFZ Data Services.
        https://doi.org/10.5880/riesgos.2021.011, https://github.com/gfzriesgos/deus

    Class to give access to the taxonomies and the damage states with the fragility functions.
    """

    def __init__(self, damage_states_by_taxonomy, schema):
        self._damage_states_by_taxonomy = damage_states_by_taxonomy
        self.schema = schema

    def get_damage_states_for_taxonomy(self, taxonomy):
        """
        Returns all the damage states for the given taxonomy.

        Returns list of DamageState objects.
        """

        if not taxonomy in self._damage_states_by_taxonomy.keys():
            error_message = (
                "Building class '%s' from exposure not found in FragilityProvider"
                % (taxonomy)
            )
            raise KeyError(error_message)

        return self._damage_states_by_taxonomy[taxonomy]

    def get_taxonomies(self):
        """
        Returns the taxonomy strings from the data.
        """

        return self._damage_states_by_taxonomy.keys()
