# RetinaCAD Windows application

Keep the complete build directory together and double-click `RetinaCAD.exe`. The application calculates the fixed A3 model locally and exports local HTML and JSON reports. It does not upload images or model inputs.

## Manual input

The source-only build accepts clinical, echocardiographic, and verified retinal measurements without WSL. Complete all measurements and binary selections before calculating a probability.

## Optional image extraction

Automatic fundus measurement requires separately installed upstream source and weights, WSL 2, and Ubuntu 24.04. These upstream assets are not included in the public source package. The setup script installs runtime dependencies; it does not supply the omitted assets.

Follow `docs/EXTERNAL_PIPELINE.md` in the source repository before running `setup_wsl_engine.ps1` from the build directory. Setup requires internet access and installs WSL system packages as root. Normal extraction runs locally after setup. The tested runtime uses GNU Octave 6.4.0; changes to upstream assets or runtime versions require renewed numerical comparison.

The output estimates CAD status under the study definition. External validation is required before clinical use. Runtime license texts and third-party notices must accompany applicable binary distributions.
