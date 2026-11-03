# Model provenance

The public manifests describe fixed TabPFN 2.1.3 fit states. A3 is the default desktop model; A1F uses the same clinical and echocardiographic inputs and two fundus ratios without the two deep OCTA measures.

Each manifest records predictor order, model identifier, permitted missing fields, fit-state and foundation-checkpoint SHA-256 hashes, cohort counts, and internal cross-validation results. Parameters are not estimated or selected during application use.

Fit states contain numerical training context and are provided on approved request to the corresponding author. They are excluded from this repository. Foundation checkpoints must be obtained separately from the pinned upstream source under its applicable terms. Public manifests exclude development-workstation paths.

The loader verifies the original fit state and checkpoint. TabPFN 2.1.3 records an absolute checkpoint path in `init_params.json`; only that path is changed in a temporary local archive. Fitted arrays and inference settings remain unchanged. Synthetic vectors check predictions within `1e-5`.

The previous arterial-density ridge implementation is replaced by the current diameter-ratio and distance-factor-ratio schema. It is not loaded as a substitute when TabPFN files are unavailable.
