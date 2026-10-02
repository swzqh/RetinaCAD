# A3 software integration contract

## Output

The function returns a number from 0 to 1: the estimated probability of
angiographic CAD as defined in this study (fixed stenosis >=20%). It is a
cross-sectional classification probability, not a future-event probability.

## Required input keys

`Age, Male, HTN, DM, Smoke, LVEF_pct, LVMI_g_m2, RWT, LVDdI_mm_m2, L2ParaFovea, L2PeriFovea, VD, Ratio`

All keys must be present. Binary fields must be numeric 0 or 1. A JSON `null`
or numeric `NaN` is replaced by the locked training-cohort median. Unknown
keys and missing keys are rejected. The canonical coefficients and input
metadata are in `A3_locked_model.json`.

## Implementation test

Run `verify_a3_model.py`. A conforming implementation must reproduce every
probability in `A3_test_vectors.json` with absolute error <= 1e-12 when using
IEEE-754 double precision.

## Version

Model ID: `A3_RIDGE_LAMBDA_MIN_LOCKED_20260817`  
Lambda: `0.10000000000000001`  
Source data SHA-256: `96E7021EBABFE0167C6229A8E27F1D0912253933DF5BBE14355F3CD15C38B963`
