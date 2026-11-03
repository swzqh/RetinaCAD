# RetinaCAD

RetinaCAD is a local desktop research application for assessing angiographic coronary atherosclerosis using clinical, resting echocardiographic, and retinal measurements. Its fixed A3 TabPFN model uses 13 predictors, including artery-to-vein median diameter and distance factor ratios and deep parafoveal and perifoveal vessel density.

The application accompanies **Retinal vascular morphology and deep macular perfusion in coronary atherosclerosis: genetic associations and clinical imaging**. The model was developed in 150 participants, including 104 with study-defined coronary disease. Its median AUC across 20 repetitions of stratified fivefold cross-validation was 0.801. Independent clinical validation is required before clinical use.

**Prediction requires approved model files.** Source code, model manifests, and synthetic test cases are public. TabPFN fit states retain participant-level training context and may be requested from the corresponding author, Yuqing Lan, at **lanyq@mail.sysu.edu.cn**, subject to ethical and institutional restrictions. Patient records, patient images, fit states, and foundation checkpoints are not included here.

## Install and run

Use Python 3.11 or 3.12 with Tk support. From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r app/requirements.txt
```

After obtaining the approved `A3.tabpfn_fit`, keep it in a private folder outside this repository. Obtain `tabpfn-v2-classifier-finetuned-zk73skhh.ckpt` from the [pinned upstream source](https://huggingface.co/Prior-Labs/TabPFN-v2-clf/tree/275f19d2add9c2c0de38f9ebaded3856599fa2e7) under its applicable terms. Configure both locations:

```powershell
$env:RETINACAD_MODEL_DIR = "C:\RetinaCAD-private"
$env:RETINACAD_CHECKPOINT = "C:\RetinaCAD-private\tabpfn-v2-classifier-finetuned-zk73skhh.ckpt"
.venv\Scripts\python.exe app/run_app.py
```

The loader checks both SHA-256 hashes against the public manifest. It performs inference without refitting, selecting predictors, or downloading models. A temporary local copy relocates the checkpoint path recorded in the fit state; fitted arrays remain unchanged. Set `RETINACAD_DEVICE` to `cpu` or `cuda` to choose a device explicitly.

Add `--demo` to load synthetic demonstration inputs. This also requires the approved model files and does not substitute for the fitted model.

## Use

1. Optionally select a fundus image in **Image review**.
2. Enter clinical, echocardiographic, OCTA, and fundus measurements in **Study inputs**.
3. Calculate the probability in **Result** and export matching HTML and JSON reports.

Changing inputs or selecting another image clears the previous result before export. Reports record the model identifier, measurements, missing fields, and available image provenance. Inference and image processing run locally and do not upload images or measurements.

See [Input definitions](docs/INPUTS.md) for units and coding. The distance factor ratio describes relative arterial and venous tortuosity; it is not arterial vessel density or a fractal-dimension ratio.

## Verify

The unit tests cover input validation, image checks, pipeline parsing, report export, and interface state without private model files:

```powershell
Push-Location app
try {
    ..\.venv\Scripts\python.exe -m unittest discover -s tests -v
} finally {
    Pop-Location
}
```

With approved model files configured, check fixed inference against the 10 public synthetic A3 vectors:

```powershell
.venv\Scripts\python.exe model/verify_models.py --model A3
```

The absolute tolerance is `1e-5` to allow small CPU/GPU differences. A1F manifests and synthetic vectors describe the fixed model without the two OCTA predictors; `--model all` checks both when both approved fit states are available. These numerical checks do not estimate clinical performance.

## Optional fundus extraction

Manual entry works without the image-processing engine. Automatic extraction uses separately installed L-WNET segmentation, optic-disc localization, and ARIA vessel measurements. It returns `ratio_AV_medianDiameter` and `ratio_AV_DF` using the study definitions.

Follow [External pipeline setup](docs/EXTERNAL_PIPELINE.md). A local replacement can use the [pipeline contract](app/EXTERNAL_PIPELINE_CONTRACT.md). Obtain upstream source and weights separately under their applicable terms.

## Files

| Path | Contents |
| --- | --- |
| `app/retinacad/` | Interface, fixed-model loader, input and image checks, extraction adapter, and report export |
| `app/tests/` | Tests that do not require private model states |
| `app/wsl_engine/` | Optional local fundus extraction scripts |
| `model/` | Public manifests, synthetic vectors, and numerical verification command |
| `docs/` | Input definitions, model provenance, and pipeline setup |
| `licenses/` | Retained third-party notices and license texts |

## Methods and attribution

Fundus phenotyping: Ortín Vela et al., *Nature Communications* (2024), [doi:10.1038/s41467-024-52334-1](https://doi.org/10.1038/s41467-024-52334-1); [code resource](https://zenodo.org/records/13347953).

TabPFN: Hollmann et al., *Nature* (2025), [doi:10.1038/s41586-024-08328-6](https://doi.org/10.1038/s41586-024-08328-6); [upstream software](https://github.com/PriorLabs/TabPFN).

Third-party components retain their original terms; see [Third-party notices](licenses/THIRD_PARTY_NOTICES.md). No project-wide software license has been assigned to RetinaCAD.
