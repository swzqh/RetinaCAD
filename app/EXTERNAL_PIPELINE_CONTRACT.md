# Local retinal pipeline contract

The packaged hidden WSL engine is the default implementation. The environment
variable below is retained only for development or an independently validated
local replacement.

The desktop app supports an optional local extraction command through the environment variable `RETINACAD_PIPELINE_COMMAND`.

The command must be either a shell-like command string or a JSON array. It may contain two placeholders:

- `{input}`: absolute path to the selected fundus image.
- `{output}`: absolute path where the command must write UTF-8 JSON.

Example:

```powershell
$env:RETINACAD_PIPELINE_COMMAND='["C:\retina-runtime\python.exe", "C:\retina-runtime\extract.py", "--input", "{input}", "--output", "{output}"]'
```

Required output:

```json
{
  "VD": 0.037,
  "Ratio": 1.09
}
```

`VD` must be `VD_orig_artery`. `Ratio` must be `ratio_AV_medianDiameter`. The command must run locally, must not upload data, and must return a nonzero exit code when image processing fails.
