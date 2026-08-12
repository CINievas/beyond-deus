# Beyond DEUS: Overview

**Beyond DEUS** is a multi-hazard risk calculation engine developed in Python. It builds upon
components and concepts from the software [DEUS](https://github.com/gfzriesgos/deus)
([Brinckmann et al., 2021](https://dataservices.gfz-potsdam.de/riesgos/showshort.php?id=d38d2b34-d5ba-11eb-9603-497c92695674)).

**Beyond DEUS** carries out damage and economic loss calculations of successive hazardous
events, such as earthquakes, tsunamis, floods or heatwaves, accounting for the updated damage or
usability status of the exposed buildings after each event. The software takes as input the
intensity fields from each hazard calculated with other relevant software and is thus
hazard-agnostic. The occurrence of each hazardous event is a run of **Beyond DEUS**. Subsequent
hazardous events can subsequently take as input the damaged exposure model output by the
previous calculation. The hazards chained in a calculation can either use the same building
taxonomies and damage scales in their exposure and vulnerability models or adopt different ones
together with compatibility matrices that enable the conversion across taxonomies and damage
scales as per the method of
[Gomez-Zapata et al. (2023)](https://doi.org/10.5194/nhess-23-2203-2023).

**Beyond DEUS** was developed as part of the “risk workflow for CAScading and COmpounding
hazards in COastal urban areas” (CASCO) project, funded by the
[Innovation Pool](https://earthenvironment.helmholtz.de/changing-earth/innopool-projects/)
of the Research Field Earth and Environment of the
[Research Program “Changing Earth – Sustaining our Future”](https://earthenvironment.helmholtz.de/changing-earth/program/)
from the Helmholtz Association of German Research Centres.

## Key Features

### Cumulative Consequences

**Beyond DEUS** carries out damage, usability and economic loss calculations of successive
hazardous events, such as earthquakes, tsunamis, floods or heatwaves, accounting for the updated
damage or usability status of the exposed buildings after each event.

Each hazard in a multi-hazard chain of events is one run of **Beyond DEUS**. After one hazard is
run, the software outputs the updated (damaged) exposure model. The next hazard is then set up
to take these damaged exposure models as input for the accumulation of damage to continue. The
user needs to provide adequate state-dependent fragility models that account for the existence
of damage.

Just like [DEUS](https://github.com/gfzriesgos/deus), **Beyond DEUS** can be run either with
input exposure and fragility models that are already compatible across hazards in terms of
building taxonomies and damage scales, or with input exposure and fragility models that differ
in their taxonomies and scales, together with relevant
[compatibility matrices](Schema_Mapping.md) that enable conversions to be calculated as per the
method of [Gomez-Zapata et al. (2023)](https://doi.org/10.5194/nhess-23-2203-2023). In the
second case, **Beyond DEUS** starts by converting the input exposure model(s) so that both
building classes and current damage states become expressed in the taxonomy and scale of the new
hazard to run. The user should then be cautious in interpreting the final damage states after
the new hazard is applied, so as to not interpret the conversions as damage transitions caused
by the new hazard.

If the user provides a post-hazard [usability model](Usability.md), the output (damaged)
exposure models can be exported in terms of usable/unusable buildings. This can be desirable for
a subsequent calculation that wants to focus on a hazard such as a heatwave, during which it is
expected that only usable buildings will contain occupants (e.g., Nievas et al., 2026a, 2026b).

### Hazard-Agnostic

**Beyond DEUS** follows the philoshopy of [DEUS](https://github.com/gfzriesgos/deus) of being
hazard-agnostic and taking as input hazard intensity fields that are pre-calculated with
specialised software of each area of expertise. This means that, in principle, **Beyond DEUS**
can be used to model any multi-hazard chain, as long as the necessary inputs exist or can be
defined. Each hazard is one run of the software.

The software currently supports a series of [input formats](Intensity.md). Readers for other
formats can be implemented following the same pattern.

### Running Modes

**Beyond DEUS** contemplates two running modes: "processing" and
["post-processing"](Post_Processing.md). Any run of the software can be one of the two, or both
(i.e., processing followed by post-processing).

In "processing" mode, the software calculates damage/losses/usability/displaced people only,
without outputting statistics. In "post-processing" mode, the software calculates statistics of
such calculations by gathering logic tree branches as well as realisations, and accounting for
their weights. Both modes need to be run for each of the hazards in a multi-hazard chain of
events. However, the "post-processing" mode takes as input data from the logic trees and
aleatory realisations of all hazards to produce meaningful statistics of the chain until that
point in time.

### Handling of Logic Trees

**Beyond DEUS** can handle both logic trees that allow to model epistemic uncertainty as well as
the use of different realisations of the same logic tree branch to capture aleatory variability.
The weight of different logic tree branches as well as the individual weight of a realisation
within a branch are input by the user. When several hazards in the same chain have already been
run, the software automatically calculates the final end-branch weights of the full logic tree
and sets of realisations.

### Paralellisation Modes

**Beyond DEUS** offers three different [parallelisation modes](Parallelisation_Modes.md) to
speed-up any particular run. The most efficient parallelisation mode to use depends on the
nature of the calculation and is deeply associated with the use of logic trees to model
uncertainty. For example, if a run consists of one input undamaged exposure model and a large
number of hazard intensity fields, parallelisation `by_intensity_realisation` might be the most
appropriate. If a subsequent run then takes all the damaged exposure models output by this
initial calculation and subjects them to a more reduced set of intensity fields of a second
hazard event, then parallelisation `by_input_exposure` might become more appropriate. When
running sampled end branches from a big logic tree, in which neither all previously-damaged
exposure models nor all new intensity fields might be combined with one another, setting up a
user-defined list of combinations and using the `by_exposure_intensity_combination` mode is
likely to be the most efficient.

Return to [documentation index](README.md).
