# A3 locked Ridge model

Model ID: `A3_RIDGE_LAMBDA_MIN_LOCKED_20260817`  
Created: `2026-08-17T14:14:23+08:00`  
Development cohort: 150 patients (104 CAD; 46 non-CAD)  
Selected lambda-min: `0.1`

## Software formula

After applying the locked missing-value fills, calculate:

```text
linear_predictor = 8.50257499006
  +0.00885790374159 * Age
  +0.670136332589 * Male
  +0.794886635981 * HTN
  +0.568895673504 * DM
  +0.07463446956 * Smoke
  -0.0202183055525 * LVEF_pct
  +0.00550435337352 * LVMI_g_m2
  +1.49026541777 * RWT
  -0.0943938780693 * LVDdI_mm_m2
  -0.0481097818248 * L2ParaFovea
  -0.0239416974231 * L2PeriFovea
  -15.9544835752 * VD
  -1.52501347745 * Ratio

probability = 1 / (1 + exp(-linear_predictor))
```

The JSON file is the machine-readable source of truth. Do not manually round
coefficients when implementing the model. Binary inputs must be coded exactly
as specified in the JSON file.

## Performance

- Repeated nested-CV median AUC: 0.804452
- Repeated nested-CV median Brier score: 0.163226
- Repeated nested-CV median log-loss: 0.492218
- Apparent full-cohort AUC of the locked fit: 0.862876

The apparent full-cohort metrics describe the frozen fit and must not replace
the repeated nested-CV estimates in scientific reporting.
