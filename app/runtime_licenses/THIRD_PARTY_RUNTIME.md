# Runtime notices

The portable build includes or embeds the following runtimes:

- CPython 3.14.0: see `PYTHON_LICENSE.txt`.
- Tcl/Tk 8.6: see `TK_LICENSE.txt`.
- Pillow 12.3.0: see `PILLOW_LICENSE.txt`.
- PyInstaller 6.22.1 bootloader: see `PYINSTALLER_COPYING.txt` and its bootloader exception.

The portable folder also carries the retinal phenotype source, neural-network
weights and hidden WSL launcher. Their notices remain under the handoff root
`licenses/` directory. Public redistribution is not permitted until the
aggregate retina-phenotypes licensing question is resolved in writing.

The one-time setup downloads GNU Octave 6.4.0, compatible Octave Forge
packages, micromamba, Python packages and the CPU PyTorch runtime into the
user's WSL home. Those components are not embedded in `RetinaCAD.exe`; their
licenses and package metadata are installed with the corresponding packages.
