# Releasing Caude o'clock

## Prerequisites

- macOS and Python 3.
- A clean `main` branch in both `caude-o-clock` and `homebrew-caude-o-clock`.

## Verify locally

```bash
./caude start
```

Confirm the icon appears in the menu bar and the usage card opens before
tagging a release.

## Publish a release

1. Commit and push the intended source revision to `main`.
2. In the `homebrew-caude-o-clock` tap, update the formula's `tag` and
   `revision` to the new source tag and commit SHA; commit and push that tap
   change.
3. Create and push the matching source tag:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

There is no compiled binary or `.pkg` step: the app is a pure-Python
PyObjC/AppKit script, installed into a virtualenv by `./caude start` (git
clone) or by the Homebrew formula. The Homebrew tag/revision bump above is
the only thing that needs to happen per release.
