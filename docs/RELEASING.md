# Releasing Caude o'clock

## Prerequisites

- macOS and Python 3.12 or later.
- Claude Code installed and logged in, for a manual app check.
- A clean `main` branch in both `caude-o-clock` and `homebrew-caude-oc`.

## Verify locally

```bash
./tests/test_launcher.sh
scripts/build-pkg.sh 0.2.0
pkgutil --check-signature release/Caude-o-clock.pkg
```

The package is intentionally unsigned until the project receives an Apple
Developer ID. `pkgutil` must therefore report `Status: no signature`.

## Publish a release

1. Commit and push the intended source revision to `main`.
2. In the `homebrew-caude-oc` tap, update the formula's `tag` and `revision`
   to the new source tag and commit SHA; commit and push that tap change.
3. Create and push the matching source tag:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

The tag triggers `.github/workflows/release.yml`, which builds the `.pkg` and
attaches it to the GitHub Release. The Download button always targets the
latest release asset named `Caude-o-clock.pkg`.

## Architecture notes

`py2app` embeds the Python runtime used by the macOS runner. Build release
artifacts on the architecture you intend to support and test the resulting
package on a clean Mac before publishing it.
