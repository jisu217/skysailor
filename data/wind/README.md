# 실측 바람 / Measured wind replay

Source: Schön, Martin; Büchau, Yann; zum Berge, Kjell; Bange, Jens; Platis, Andreas.
PARASITE UAS wind measurement and ultrasonic anemometer/radiosonde reference
measurements (Jülich 08/2024, Falkenberg 02/2025).
https://doi.org/10.5281/zenodo.18268508 — CC BY 4.0
License: https://creativecommons.org/licenses/by/4.0/

Only the **reference sonic** `mike_u`, `mike_v`, `mike_w` columns from
`hopper_mike_combined.csv` are used. Drone-estimated wind is NOT used.
METEK USA-1 at 50 m above ground, Falkenberg, Germany. The published dataset
is resampled to nominal 10 Hz and filtered by the authors for their mast/UAS
comparison. Published timestamps contain gaps; we reject windows with any gap
larger than 0.2 seconds and linearly interpolate smaller intervals. We do not
fill long gaps, scale the amplitudes, subtract means or loop the time series.
X=east, Y=north, Z=up, m/s.

`measured.json` is our extracted/modified subset. It contains source checksum,
author names, timestamps, processing description and three 10-second windows.
Candidate windows begin every 10 source rows. Choose smallest mean speed,
largest mean W and smallest mean W; these are illustrative extremes, not random
or representative sampling. Labels summarize the FULL 10-second window. The
wind during an earlier-ending drop can have a different mean/sign.

This is a **spatially uniform replay of 50 m measurements**, NOT measured air
along a 0–3 m falling trajectory and NOT a reconstruction of local turbulence.
Even the lowest-speed selected interval averages ~3.3 m/s. No near-calm interval
is supplied in this small selection. The source's instrument sampling rate does
not guarantee accuracy of the simplified cap CFD/dynamics under fast gusts.

Rebuild from the downloaded source in raw/:
`.venv/bin/python experiments/import_measured_wind.py`
Source download:
https://zenodo.org/api/records/18268508/files/hopper_mike_combined.csv/content
The full API source metadata is preserved in `source-metadata.json`.
The unused spectral file in raw/ was inspected but is not part of the replay.
