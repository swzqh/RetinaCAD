# External retinal pipeline

This repository includes the RetinaCAD extraction adapter, but excludes upstream pipeline source and neural-network weights. The local aggregate pipeline has no confirmed single redistribution license covering all bundled modifications. Obtain those components from their original sources under the applicable terms.

## Sources

- Retinal phenotyping code: [Zenodo record 13347953](https://zenodo.org/records/13347953), associated with DOI [10.1038/s41467-024-52334-1](https://doi.org/10.1038/s41467-024-52334-1).
- L-WNET: [agaldran/lwnet](https://github.com/agaldran/lwnet), including the artery/vein configuration and weights for `big_wnet_drive_av`.
- Optic-disc localization: the `optic-nerve-cnn` component distributed with the retinal phenotype pipeline, using `04.02.18_unet_on_ukbiobank_256px/last_checkpoint.hdf5`.
- ARIA: the modified measurement routines used by the phenotype pipeline, under `petebankhead-ARIA-328853d`.

## Local directory layout

Install the compatible components beneath the repository root:

```text
retina_pipeline/
  lwnet/
    predict_one_image_av.py
    models/
    utils/
    experiments/big_wnet_drive_av/
      config.cfg
      model_checkpoint.pth
  retina-phenotypes/preprocessing/
    optic-nerve-cnn/models_weights/
      04.02.18_unet_on_ukbiobank_256px/last_checkpoint.hdf5
    helpers/MeasureVessels/src/petebankhead-ARIA-328853d/
      ARIA_tests/ARIA_run_tests.m
      ...
```

The layout shows key assets, rather than a complete upstream file list. Retain all code required by each component. Generic upstream versions may differ from the locally validated versions; matching the directory names alone does not establish numerical equivalence. `UPSTREAM_ASSETS.json` records file hashes from the validated local tree for comparison. It contains no upstream source or weights.

## WSL setup

Install WSL 2 and Ubuntu 24.04. Then run from the repository root:

```powershell
.\app\wsl_engine\setup_wsl_engine.ps1
```

The setup installs Python dependencies, CPU PyTorch 2.8.0/torchvision 0.23.0, GNU Octave 6.4.0, and the specified Octave packages. It requires internet access and installs WSL system packages as root. The script ends with an environment and asset check.

For a different distribution, provide `-Distribution` to the setup script and set `RETINACAD_WSL_DISTRIBUTION` to the same name before starting the app.

After setup, the app runs image extraction in a background WSL process. Failed stages return an error rather than replacement measurements. Verify extracted values against the original pipeline before using them in an external model evaluation. Do not upload installed upstream trees, images, processing outputs, or local environments with this repository.
