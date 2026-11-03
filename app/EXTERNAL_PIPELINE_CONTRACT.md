# Local retinal pipeline contract

Configure an optional local extraction command with `RETINACAD_PIPELINE_COMMAND`. Use a command string or JSON array with `{input}` and `{output}` placeholders for the absolute fundus-image and output-JSON paths.

```powershell
$env:RETINACAD_PIPELINE_COMMAND='["C:\retina-runtime\python.exe", "C:\retina-runtime\extract.py", "--input", "{input}", "--output", "{output}"]'
```

Required UTF-8 JSON output:

```json
{
  "schema_version": "2.0",
  "ratio_AV_DF": 1.0,
  "ratio_AV_medianDiameter": 1.09
}
```

`ratio_AV_DF` is median arterial distance factor divided by median venous distance factor. In ARIA segment statistics, classify arteries with `AVScore > 0` and veins with `AVScore < 0`, then obtain medians from the `DF` column. Distance factor is path length divided by chord length.

`ratio_AV_medianDiameter` is the median arterial-to-venous diameter ratio across the measured network. Both ratios must be finite and positive. The adapter rejects the old `VD`/`Ratio` schema. Commands run locally and return a nonzero exit code when extraction fails.
