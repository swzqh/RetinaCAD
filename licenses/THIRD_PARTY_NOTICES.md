# Third-party notices

## External image-processing components

The following components are referenced by the optional extraction engine. Their source and weights are not included in this repository.

| Component | Source | License information retained locally |
| --- | --- | --- |
| L-WNET | https://github.com/agaldran/lwnet | MIT; see `L-WNET_LICENSE_MIT.txt` |
| optic-nerve-cnn | Retinal phenotyping code resource | MIT; see `OPTIC_NERVE_CNN_LICENSE_MIT.txt` |
| ARIA | Modified routines in the retinal phenotype pipeline | Copyright, redistribution conditions, and disclaimer in `ARIA_Copyright.m` |
| retina-phenotypes aggregate | https://zenodo.org/records/13347953 | The record describes CC BY 4.0; a single license covering the local aggregate and all modifications has not been confirmed |

License texts are retained for attribution. Their inclusion does not extend their terms to unrelated RetinaCAD code or establish rights to every external weight or modification. Confirm component-specific redistribution terms before publishing an executable that bundles these assets.

## Desktop runtime

The source application uses Python, Tcl/Tk, and Pillow. The optional Windows build uses PyInstaller. Runtime notices and license texts are included under `app/runtime_licenses/`; they must accompany applicable binary distributions.

## RetinaCAD

No project-wide license has been assigned in this package. The original rights holders retain their rights. A software license for RetinaCAD should be selected by its rights holders before granting general reuse or redistribution permissions.
