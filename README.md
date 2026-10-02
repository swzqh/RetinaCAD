# RetinaCAD

RetinaCAD is a local desktop research application for the fixed A3 ridge logistic regression model described in **Retinal Vascular Phenotypes in Coronary Artery Disease: A Genetic and Multimodal Imaging Study**. It combines clinical, echocardiographic, and retinal measurements to estimate the probability of angiographic coronary artery disease (CAD) under the study definition.

The application uses stored coefficients, scaling parameters, and missing-value fills. It does not select predictors or refit the model. The output concerns CAD status at assessment, rather than future cardiovascular events. Prospective external validation is required before clinical use.

## Repository contents

| Path | Contents |
| --- | --- |
| `app/retinacad/` | Desktop interface, model inference, image checks, local pipeline adapter, and report export |
| `app/tests/` | Model, input validation, report, image, pipeline adapter, and interface tests |
| `app/assets/` | Application icons |
| `app/wsl_engine/` | Setup and extraction scripts for the optional local image-processing engine |
| `model/` | Fixed A3 model, reference implementation, and 10 synthetic test vectors |
| `docs/` | Input definitions and external pipeline setup |
| `retina_pipeline/` | Instructions for installing external image-processing components |
| `licenses/` | Third-party notices and license texts |

Patient records, patient images, analysis outputs, development logs, compiled executables, and third-party pipeline source or weights are not included. The test vectors are synthetic.

## Run from source

Use Python 3.11 or later with Tk support. Windows 10/11 is the target platform. The desktop application requires Pillow; the reference model calculation uses only the Python standard library.

From the repository root, run in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r app/requirements.txt
.venv\Scripts\python.exe app/run_app.py
```

To open a synthetic demonstration:

```powershell
.venv\Scripts\python.exe app/run_app.py --demo
```

Manual entry of verified retinal measurements works without WSL or the external image-processing components.

## Workflow

1. Enter a case code and, if needed, select a fundus image in **Image review**.
2. Enter the clinical, echocardiographic, and retinal measurements in **Study inputs**. The two fundus measurements may be entered manually or obtained using a configured local extraction engine.
3. Calculate the probability in **Result** and export the HTML and JSON report.

Changing an input or selecting another image clears the previous result. A new calculation is required before export. Reports record the model identifier, inputs, imputed fields, and available image and phenotype provenance. Image checks describe technical properties and do not establish clinical image suitability.

All calculations and image processing run locally. Dependency installation requires internet access; normal use does not upload images or model inputs.

## Model and inputs

The authoritative model is `model/A3_locked_model.json`, with model identifier `A3_RIDGE_LAMBDA_MIN_LOCKED_20260817` and ridge penalty 0.1. It contains 13 predictors: five clinical, four echocardiographic, two deep macular OCTA, and two fundus-derived measurements. See [Input definitions](docs/INPUTS.md) for names, units, and coding.

The development cohort included 150 participants, of whom 104 had CAD. The median AUC from repeated nested cross-validation was 0.804. This is an internal validation estimate. The final model fitted to the full development cohort is supplied for independent evaluation.

The reference implementation can be used without the desktop interface:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("model").resolve()))
from a3_predict import predict_a3

vectors = json.loads(Path("model/A3_test_vectors.json").read_text(encoding="utf-8"))
probability = predict_a3(vectors[0]["inputs"])
print(probability)  # 0.22545899869472588
```

All 13 keys must be present. Unknown keys, nonnumeric inputs, nonfinite values other than missing-value NaN, and binary values outside 0/1 are rejected. In the reference implementation, `None` or numeric NaN is replaced by the stored development-cohort median. The desktop interface requires all measurements and binary selections before calculation. Preserve the original measurement definitions and input scales when evaluating the model.

## Verify the implementation

From the repository root:

```powershell
.venv\Scripts\python.exe model/verify_a3_model.py
Push-Location app
try {
    ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
} finally {
    Pop-Location
}
```

The reference check compares all 10 synthetic vectors with an absolute error tolerance of 1e-12. Desktop tests require a graphical session and Tk. The pipeline adapter tests do not run the complete external image-processing engine.

## Optional automatic retinal extraction

Automatic extraction uses L-WNET artery/vein segmentation, optic-disc localization, and ARIA vessel measurement to obtain `VD_orig_artery` and `ratio_AV_medianDiameter`. These upstream components and their weights must be installed separately. Their absence does not prevent manual-input calculations.

Follow [External pipeline setup](docs/EXTERNAL_PIPELINE.md) before running the WSL setup script. The tested engine configuration uses WSL 2, Ubuntu 24.04, GNU Octave 6.4.0, and the pinned Python dependencies. Setup installs a private environment under `~/.local/share/retinacad` in WSL. Numerical equivalence should be checked when changing an upstream component, model weight, or runtime version.

An independently validated local command may also be configured through `RETINACAD_PIPELINE_COMMAND`; see [Local pipeline contract](app/EXTERNAL_PIPELINE_CONTRACT.md).

## Build a Windows executable

From an activated Python environment:

```powershell
.\app\build_windows.ps1 -InstallDependencies
```

The output is `app/dist/RetinaCAD/RetinaCAD.exe`. Keep its complete directory together. A source-only build supports manual input. Automatic extraction requires the separately installed components and WSL runtime. Before distributing a build that includes external source or weights, confirm the applicable redistribution terms.

Compiled builds belong in GitHub Releases rather than the source tree.

## Citation and third-party components

The associated manuscript is titled **Retinal Vascular Phenotypes in Coronary Artery Disease: A Genetic and Multimodal Imaging Study**. A final journal citation and DOI are not yet supplied in this repository.

The fundus phenotype method is described by Ortín Vela et al., *Nature Communications* (2024), DOI: [10.1038/s41467-024-52334-1](https://doi.org/10.1038/s41467-024-52334-1). The corresponding code resource is [Zenodo record 13347953](https://zenodo.org/records/13347953). L-WNET is available from [agaldran/lwnet](https://github.com/agaldran/lwnet).

Third-party license texts and notices are retained in `licenses/` and `app/runtime_licenses/`. No project-wide software license has been assigned to RetinaCAD in this package; public repository availability alone does not grant redistribution or reuse rights. See [Third-party notices](licenses/THIRD_PARTY_NOTICES.md).
