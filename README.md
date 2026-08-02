<p align="left">
  <img src="assets/readme-logo-outlined.png" alt="Caude o'clock" width="310">
</p>

### Your Claude usage, quietly visible.

Caude o'clock is a tiny macOS menu-bar companion for Claude Code: your 5-hour
and weekly windows and reset times — without another dashboard or login.

<p align="left">
  <a href="https://github.com/KarlinskyS/caude-o-clock/releases/latest/download/Caude-o-clock.pkg">
    <img src="https://img.shields.io/badge/Download_for_macOS-0A84FF?style=for-the-badge&logo=apple&logoColor=white" alt="Download for macOS">
  </a>
  <a href="https://github.com/KarlinskyS/caude-o-clock">
    <img src="https://img.shields.io/badge/View_on_GitHub-101828?style=for-the-badge&logo=github&logoColor=white" alt="View on GitHub">
  </a>
</p>

### Other ways to install

**Homebrew**<br>
```bash
brew install KarlinskyS/caude-o-clock/caude && caude start
```

---

**From GitHub**<br>
```bash
git clone https://github.com/KarlinskyS/caude-o-clock.git && cd caude-o-clock && ./caude start
```

<img src="assets/readme-hero.png" alt="Caude o'clock menu-bar companion" width="880">

After installation, run `caude start`. The app appears in the macOS menu bar;
everything else happens from its popover.

<details>
<summary><strong>Why macOS may show a security notice</strong></summary>

The downloadable package is currently unsigned and not notarized because the
project has no Apple Developer ID. If you trust this repository, try opening
the package once, then select **Open Anyway** in **System Settings → Privacy &
Security**. Download packages only from this repository.
</details>

<details>
<summary><strong>If the icon doesn't appear in the menu bar</strong></summary>

Rare, but seen: macOS's menu bar rendering can get into a bad state after
a Mac has been running a long time (weeks of uptime, many menu-bar apps
installed) and silently refuses to register a new icon — with no error
shown anywhere. This isn't specific to Caude o'clock; any menu-bar app can
hit it. If `caude start` reports success but no icon shows up, try these
in order (each is more disruptive than the last, so try them top-down):

1. **Run `caude start` again** (or quit and reopen if you installed the
   `.pkg`). This alone often clears it.
2. **Log out and log back in** — resets macOS's window/menu-bar system
   without a full restart.
3. **Restart your Mac.**

</details>

<details>
<summary><strong>For contributors</strong></summary>

Release, package-build, and implementation notes live in
[docs/RELEASING.md](docs/RELEASING.md).
</details>
