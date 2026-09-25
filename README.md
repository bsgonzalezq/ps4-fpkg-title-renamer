# ps4-title-renamer

Renames PS4 game folders and files named after title IDs (`CUSA00900`, `CHTM00777`, ...) to the game's title.

```
CUSA00900/                          Bloodborne/
├── CUSA00900_base.pkg      ->      ├── Bloodborne_base.pkg
└── CUSA00900_patch.pkg             └── Bloodborne_patch.pkg
```

- Reads titles directly from the `param.sfo` inside each `.pkg`, so no guessing or online title-ID database is needed
- Looks up English names online for Japanese / Korean / Chinese titles
- Dry run by default, with a results log and a one-command undo
- Output names are safe for exFAT/NTFS drives

## Prerequisites

| Requirement | Why |
|---|---|
| Python 3.8+ | Runs the script. Only the standard library is used, so there's nothing to `pip install` |
| git | Clones and updates the repo |
| Internet access | Only needed for the English-name lookup in `--build-db`. Use `--offline` to skip it |

The prerequisites are also listed in [`requirements.txt`](requirements.txt), which names no packages, and checked by [`install_prereqs.sh`](install_prereqs.sh).

## Installation

### Linux / macOS

```bash
# 1. get git if you don't have it (Debian/Ubuntu shown; the script below handles other distros)
sudo apt-get update && sudo apt-get install -y git

# 2. clone the repo (it's private, so log in first: `gh auth login`, or use an SSH key)
git clone https://github.com/bsgonzalezq/ps4-title-renamer.git
cd ps4-title-renamer

# 3. install / verify Python 3.8+ and git (apt, dnf, pacman, zypper or Homebrew)
./install_prereqs.sh
```

`install_prereqs.sh` installs only what's missing, checks the Python version, and runs `pip install -r requirements.txt` if packages are ever added there.

If you'd rather install by hand:

| Distro | Command |
|---|---|
| Debian / Ubuntu | `sudo apt-get install -y python3 git` |
| Fedora / RHEL | `sudo dnf install -y python3 git` |
| Arch | `sudo pacman -S --needed python git` |
| openSUSE | `sudo zypper install -y python3 git` |
| macOS (Homebrew) | `brew install python git` |

### Windows

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
# reopen the terminal so both are on PATH, then:
git clone https://github.com/bsgonzalezq/ps4-title-renamer.git
cd ps4-title-renamer
python ps4_rename.py --help
```

On Windows, use `python` where this README shows `python3`.

### Updating

```bash
cd ps4-title-renamer
git pull
```

## Quick start

```bash
cd /path/to/your/pkg/folders
python3 ~/ps4-title-renamer/ps4_rename.py --build-db   # 1. create ps4_titles.db from the .pkg files
python3 ~/ps4-title-renamer/ps4_rename.py              # 2. dry run: shows what would change
python3 ~/ps4-title-renamer/ps4_rename.py --apply      # 3. rename
python3 ~/ps4-title-renamer/ps4_rename.py --undo       #    revert, if needed
```

With no path the script works on the current directory. Pass a path to work elsewhere:

```bash
python3 ~/ps4-title-renamer/ps4_rename.py /media/usb/PS4 --apply
```

Optional: to run it as just `ps4_rename.py`, link it into your PATH:

```bash
mkdir -p ~/.local/bin && ln -sf ~/ps4-title-renamer/ps4_rename.py ~/.local/bin/ps4_rename.py
```

## Options

| Option | Description |
|---|---|
| `PATH` | Directory to process (default: current directory) |
| `--apply` | Perform the renames (default is a dry run) |
| `--undo` | Revert the renames recorded in `PATH/rename_undo.log` |
| `--keep-id` | Keep the ID after the title: `Bloodborne [CUSA00900]` |
| `--build-db` | Add games to the db from the `.pkg` files in `PATH` |
| `--rebuild` | With `--build-db`: start a fresh db, dropping old entries |
| `--offline` | With `--build-db`: skip the English-name lookup |
| `--db FILE` | Title db to use (see below) |
| `--log FILE` | Where to write the results log |
| `-h`, `--help` | Show help |

## Title database

`ps4_titles.db` is plain text with one game per line, and you can edit it by hand:

```
# ID|Title|Region
CUSA00900|Bloodborne™|USA
CUSA07439|DARK SOULS™ III|EUR
CUSA10207|Battle Garegga Rev.2016|ASIA
CHTM00777|PS4 Cheats Manager|HB
```

- **Title** comes from the PKG's `param.sfo`. The English localized title (`TITLE_01`) is used when the PKG has one.
- **Region** comes from the content ID prefix: `UP` = USA, `EP` = EUR, `JP` = JPN, `HP` = ASIA, `KP` = KOR. Homebrew is marked `HB`.
- By default the script uses `PATH/ps4_titles.db`. If that doesn't exist, it falls back to the `ps4_titles.db` next to the script, so one db can serve several folders.
- `--build-db` only adds games that aren't in the db yet, so your manual edits are kept. Use `--rebuild` to start over.

The `ps4_titles.db` in this repo is an example generated from a real collection.

### English names for non-English titles

Some Asian releases only have a Japanese or Korean title. For those, `--build-db` searches English Wikipedia and then Wikidata, and only accepts results described as a video game:

```
CUSA10207: 배틀 가레가 Rev.2016      ->  Battle Garegga Rev.2016
CUSA32997: 怒首領蜂大往生 臨廻転生   ->  DoDonPachi DaiOuJou
```

- The lookup often returns the original game's name, so an edition suffix may be missing. Edit the db if you want the exact PS4 name.
- If nothing is found, the original title is kept.
- Requests are limited to about one per second to respect Wikimedia's rate limits.

## Logs

Every run except `--build-db` writes `rename_results_<dryrun|apply|undo>_<timestamp>.log` into `PATH`:

```
=== CHANGED (143) ===
CUSA00900/CUSA00900_base.pkg  ->  Bloodborne_base.pkg
=== NOT CHANGED (39) ===
Bloodborne [CUSA00900]/Bloodborne The Old Hunters.pkg  (no game ID in name)
CUSA99999  (ID not in db: CUSA99999)
=== ERRORS (1) ===
CUSA00900/CUSA00900_patch.pkg  (target already exists: Bloodborne_patch.pkg)
```

`--apply` also appends every rename to `PATH/rename_undo.log`, which `--undo` uses to restore the original names. If you move that file, move it back before running `--undo`.

## Notes

- Characters that exFAT/NTFS don't allow are replaced: `:` becomes ` - `; `? * " < > |`, `™` and `®` are removed or replaced.
- Existing files are never overwritten. A name collision is logged as an error and skipped.
- `System Volume Information`, `$RECYCLE.BIN` and the script's own files are skipped.
- Check that your install tools don't rely on ID-named folders. If they do, use `--keep-id`.
