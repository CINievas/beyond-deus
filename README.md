# Beyond DEUS

**Beyond DEUS** is a multi-hazard risk calculation engine developed in Python. It builds upon
components and concepts from the software [DEUS](https://github.com/gfzriesgos/deus)
([Brinckmann et al., 2021](https://dataservices.gfz-potsdam.de/riesgos/showshort.php?id=d38d2b34-d5ba-11eb-9603-497c92695674)).

Just like **DEUS**, **Beyond DEUS** carries out damage and economic loss calculations of
successive hazardous events, such as earthquakes, tsunamis, floods or heatwaves, accounting for
the updated damage or usability status of the exposed buildings after each event. The software
takes as input the intensity fields from each hazard calculated with other relevant software and
is thus hazard-agnostic. The occurrence of each hazardous event is a run of **Beyond DEUS**.
Subsequent hazardous events can subsequently take as input the damaged exposure model output by
the previous calculation. The hazards chained in a calculation can either use the same building
taxonomies and damage scales in their exposure and vulnerability models or adopt different
ones together with compatibility matrices that enable the conversion across taxonomies and
damage scales as per the method of
[Gomez-Zapata et al. (2023)](https://doi.org/10.5194/nhess-23-2203-2023).


## Installation

This software requires Python 3.12 or above. It is recommended that a virtual environment be
created so as to install and run the software from within it.

Dependencies are installed automatically when installing this software. They are listed under
`install_requires` in [setup.py](./setup.py).

To install, navigate to your preferred directory and clone the repository:

```bash
git clone https://git.gfz-potsdam.de/casco/beyond-deus.git
```

With the Python virtual environment activated, navigate to that same repository and do:

```bash
cd beyond-deus
pip3 install -e .
```


# Running

Beyond DEUS expects a `config.yml` file to be located in the running directory. To run the
software, navigate to the running directory and type:

```bash
beyonddeus
```


## Citation

Software: COMING SOON.

Journal paper: COMING SOON.


## Acknowledgements

This work is part of the “risk workflow for CAScading and COmpounding hazards in COastal urban
areas” (CASCO) project, funded by the [Innovation Pool](https://earthenvironment.helmholtz.de/changing-earth/innopool-projects/)
of the Research Field Earth and Environment of the
[Research Program “Changing Earth – Sustaining our Future”](https://earthenvironment.helmholtz.de/changing-earth/program/)
from the Helmholtz Association of German Research Centres.


## Copyright and copyleft

Copyright (C) 2026

* GFZ Helmholtz-Zentrum für Geoforschung | GFZ Helmholtz Centre for Geosciences

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see http://www.gnu.org/licenses/.

Also add information on how to contact you by electronic and paper mail.

If your software can interact with users remotely through a computer
network, you should also make sure that it provides a way for users to
get its source. For example, if your program is a web application, its
interface could display a "Source" link that leads users to an archive
of the code. There are many ways you could offer source, and different
solutions will be better for different programs; see section 13 for the
specific requirements.

Portions of this software are derived from work licensed under the
Apache License, Version 2.0.

In accordance with Section 4 of the Apache License, we include a copy of
the Apache License 2.0 and any required NOTICE files with this
distribution (no NOTICE files existed in the original software).

The Apache‑licensed components remain under the terms of the Apache
License, Version 2.0.

All original modifications and all other parts of this program are
licensed under the GNU Affero General Public License, version 3 or any
later version.

See the [LICENSE](./LICENSE) for the full license text.
