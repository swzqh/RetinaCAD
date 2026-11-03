# Input definitions

The fixed A3 model uses these 13 keys in the manifest's order.

| Key | Measurement | Unit or coding |
| --- | --- | --- |
| `Age` | Age | years |
| `Male` | Male sex | 0=female; 1=male |
| `HTN` | Hypertension | 0=no; 1=yes |
| `DM` | Diabetes mellitus | 0=no; 1=yes |
| `Smoke` | Smoking | 0=no; 1=yes, using the study definition |
| `LVEF_pct` | Left ventricular ejection fraction | % |
| `LVMI_g_m2` | Left ventricular mass index | g/m² |
| `RWT` | Relative wall thickness | unitless |
| `LVDdI_mm_m2` | Indexed LV end-diastolic diameter | mm/m² |
| `L2ParaFovea` | Deep parafoveal vessel density | original device-output scale |
| `L2PeriFovea` | Deep perifoveal vessel density | original device-output scale |
| `ratio_AV_medianDiameter` | Median arterial diameter divided by median venous diameter | unitless |
| `ratio_AV_DF` | Median arterial distance factor divided by median venous distance factor | unitless |

Distance factor is vessel path length divided by chord length. `ratio_AV_DF` describes relative arterial and venous tortuosity, not fractal dimension. The retired `VD` arterial-density key cannot substitute for it. Use the explicit diameter-ratio key instead of the retired `Ratio` alias.

OCTA values retain the device-output percentage scale; do not divide by 100. L2 is the device-defined deep vascular complex. Parafoveal and perifoveal annuli have diameters of 1–3 mm and 3–6 mm, respectively.

All keys must be present. The inference service permits explicit missing values only for `LVMI_g_m2` and `RWT`, handled by the fitted TabPFN preprocessing. The desktop interface requests complete measurements.

The outcome is study-defined coronary disease at assessment: at least 20% fixed luminal stenosis in a major epicardial coronary artery or evaluable branch. It is not a future-event risk estimate.
