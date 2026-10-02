# Input definitions

The fixed A3 model requires all 13 keys. Measurements must follow the study definitions.

| Key | Measurement | Unit or coding |
| --- | --- | --- |
| `Age` | Age | years |
| `Male` | Male sex | 0=female; 1=male |
| `HTN` | Hypertension | 0=no; 1=yes |
| `DM` | Diabetes mellitus | 0=no; 1=yes |
| `Smoke` | Smoking | 0=no; 1=yes, as recorded |
| `LVEF_pct` | Left ventricular ejection fraction | % |
| `LVMI_g_m2` | Left ventricular mass index | g/m^2 |
| `RWT` | Relative wall thickness | unitless |
| `LVDdI_mm_m2` | Indexed LV end-diastolic diameter | mm/m^2 |
| `L2ParaFovea` | Deep-layer parafoveal vessel density | device output |
| `L2PeriFovea` | Deep-layer perifoveal vessel density | device output |
| `VD` | Retinal arterial vessel density | pipeline output |
| `Ratio` | Artery-to-vein median diameter ratio | unitless |

`VD` is a fraction on the 0–1 scale. Do not enter it as a percentage. The OCTA annular measures retain the device-output scale used in the development cohort; do not divide them by 100.

L2 denotes the deep retinal vascular layer. The parafoveal and perifoveal measurements refer to the 1–3-mm and 3–6-mm annuli, respectively. `Ratio` is the artery-to-vein median diameter ratio, rather than the equivalent central retinal artery-to-vein caliber ratio.

Binary definitions, including smoking, must match the manuscript. The desktop interface requires complete inputs. The reference implementation accepts explicit missing values and fills them with stored development-cohort medians; this does not make unavailable or incorrectly defined measurements interchangeable.

CAD is defined in the model as fixed stenosis of at least 20% in a major epicardial coronary artery or branch. The output is a cross-sectional probability under that definition.
