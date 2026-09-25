# ps4-pkg-title-renamer

Renames PS4 PKG files to a consistent `<ID>_base` / `_patch` / `_<DLC>_dlc` scheme, puts each game in its own folder, and replaces title IDs (`CUSA00900`, `CHTM00777`, ...) with the game's title.

```
CUSA00900/                                   Bloodborne/
├── CUSA00900_base.pkg                ->     ├── Bloodborne_base.pkg
├── update.pkg                               ├── Bloodborne_patch.pkg
└── Bloodborne The Old Hunters.pkg           └── Bloodborne_The Old Hunters_dlc.pkg
CUSA11253_base.pkg  (loose in root)          Dead Cells/
                                             └── Dead Cells_base.pkg
```

- Reads titles directly from the `param.sfo` inside each `.pkg`, so no guessing or online title-ID database is needed
- Looks up English names online for Japanese / Korean / Chinese titles
- Dry run by default, with a results log and undo: everything, only the last run, or only matching names ([Undo](#undo))
- Base game, patch or DLC is detected from each PKG's `param.sfo`, not from the file name
- Loose PKGs in the top folder are moved into their game's folder, which is created if needed
- Safe to run again: already-renamed items are left alone
- Output names are safe for exFAT/NTFS drives

## Prerequisites

| Requirement | Why |
|---|---|
| Python 3.8+ | Runs the script. Only the standard library is used, so there's nothing to `pip install` |
| git | Clones and updates the repo |
| Internet access | Only needed for the English-name lookup in `--build-db`. Use `--offline` to skip it |

The prerequisites are also listed in [`requirements.txt`](requirements.txt), which names no packages, and checked by [`install_prereqs.sh`](install_prereqs.sh) (Linux/macOS) or [`install_prereqs.ps1`](install_prereqs.ps1) (Windows).

## Installation

### Linux / macOS

```bash
# 1. get git if you don't have it (Debian/Ubuntu shown; the script below handles other distros)
sudo apt-get update && sudo apt-get install -y git

# 2. clone the repo (it's private, so log in first: `gh auth login`, or use an SSH key)
git clone https://github.com/bsgonzalezq/ps4-pkg-title-renamer.git
cd ps4-pkg-title-renamer

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
winget install -e --id Git.Git          # skip if git is installed
# reopen the terminal so git is on PATH, then:
git clone https://github.com/bsgonzalezq/ps4-pkg-title-renamer.git
cd ps4-pkg-title-renamer
powershell -ExecutionPolicy Bypass -File .\install_prereqs.ps1   # installs / checks Python 3.8+ and git
py ps4_rename.py --help
```

`install_prereqs.ps1` works like `install_prereqs.sh`: it installs only what's missing (through `winget`), checks the Python version, and checks the script runs.

**Using the script on Windows:**

- **Commands:** use `py` or `python` where this README shows `python3`, and `\` in paths, e.g. `py ps4-pkg-title-renamer\ps4_rename.py D:\PS4 --apply`.
- **Everything else works as on Linux:** a drive root like `D:\` works as `PATH`, and the script checks the OS when it starts. It handles Windows differences automatically:
  - **Long paths:** paths longer than 260 characters work even if Windows' long-path support is off.
  - **Case:** Windows ignores letter case in names and paths (`C:\Games` = `c:\games`), and so does the script, including renames that only change letter case.
  - **Names:** file names that Windows can't use are made safe. That covers `:` and similar characters, the reserved names `CON`, `NUL` and `COM1`, and trailing dots.
  - **Console:** titles with characters like `™`, `Ψ` or Japanese text never crash the output, even when it's redirected to a file.
- **Same drive on both systems:** a drive renamed on Linux can be used on Windows and the other way round. Names are already safe for exFAT/NTFS, and the db and logs are plain UTF-8 text.
- **`rename_undo.log`:** records full paths, so run `--undo` on the same OS and drive letter or mount point you used for `--apply`.

### Updating

```bash
cd ps4-pkg-title-renamer
git pull
```

If you keep a copy of `ps4_rename.py` somewhere else, such as next to your games, copy it over again after pulling.

## Quick start

The script always lives in a folder named `ps4-pkg-title-renamer`, together with its db (`ps4_titles.db`) and all its logs:

- **Moving itself:** if you run it from a folder with any other name, it creates `ps4-pkg-title-renamer/` in your current directory. It moves itself there along with its db and logs, removes the old folder if that's now empty, and carries on. So you can drop `ps4_rename.py` into your games folder and run it.
- **Git clones:** the script never moves out of a git clone.
- **Existing copy:** it won't overwrite a `ps4_rename.py` that's already in `./ps4-pkg-title-renamer/`.

The examples use relative paths.

The script takes one optional `PATH`: the folder that holds your PKG folders. With no `PATH` it works on the current directory. `PATH` can be relative or absolute.

Both examples use this layout, with the script in a subfolder of the games folder:

```
games/                  <- games folder (holds the PKG folders)
├── CUSA00900/
├── CUSA00419/
└── ps4-pkg-title-renamer/  <- script folder (a clone of this repo, or created automatically)
    ├── ps4_rename.py
    ├── ps4_titles.db
    └── rename_undo.log, rename_results_*.log
```

**Option 1: your terminal is in the games folder** (`games/`). No `PATH` is needed because the current directory is already the games folder:

```bash
cd games
python3 ps4-pkg-title-renamer/ps4_rename.py --build-db   # 1. create ps4_titles.db (optional, done automatically)
python3 ps4-pkg-title-renamer/ps4_rename.py              # 2. dry run: shows what would change
python3 ps4-pkg-title-renamer/ps4_rename.py --apply      # 3. rename
python3 ps4-pkg-title-renamer/ps4_rename.py --undo       #    revert everything, if needed
python3 ps4-pkg-title-renamer/ps4_rename.py --undo-last  #    or preview reverting just the last run (see Undo)
```

**Option 2: your terminal is in the script folder** (`games/ps4-pkg-title-renamer/`). Pass `..`, the parent folder, as `PATH`:

```bash
cd games/ps4-pkg-title-renamer
python3 ps4_rename.py .. --build-db
python3 ps4_rename.py ..
python3 ps4_rename.py .. --apply
python3 ps4_rename.py .. --undo
python3 ps4_rename.py .. --undo-last
```

The db and all logs are always kept in the script's folder, whichever `PATH` you process, so one db serves all your game folders.

Optional: to run it as just `ps4_rename.py` from anywhere, run this from the script's folder to link it into your PATH:

```bash
mkdir -p ~/.local/bin && ln -sf "$PWD/ps4_rename.py" ~/.local/bin/ps4_rename.py
```

Re-run the link command if you move the script.

## Options

| Option | Description |
|---|---|
| `PATH` | Directory to process (default: current directory) |
| `--apply` | Perform the renames (default is a dry run) |
| `--undo` | Revert all renames under `PATH` recorded in `rename_undo.log` |
| `--undo-last` | Revert only the most recent `--apply` run. Previews unless `--apply` is added |
| `--undo-match TEXT` | Revert only renames whose path contains `TEXT`. Previews unless `--apply` is added |
| `--keep-id` | Keep the ID after the title: `Bloodborne [CUSA00900]` |
| `--build-db` | Add games to the db from the `.pkg` files in `PATH` |
| `--rebuild` | With `--build-db`: start a fresh db, dropping old entries |
| `--offline` | Skip the English-name lookup when building the db |
| `--no-auto-db` | Don't build the db automatically when IDs are missing |
| `--db FILE` | Title db to use (see below) |
| `--log FILE` | Where to write the results log (default: the script's folder) |
| `--keep-logs N` | Number of results logs to keep; older ones are deleted. Default 5, and `0` keeps all |
| `--clean-logs` | Delete the results logs; `rename_undo.log` is kept |
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
- The db is always `ps4_titles.db` next to the script. `--db FILE` overrides this. A `ps4_titles.db` left in `PATH` by older versions is merged into it automatically and then removed.
- `--build-db` only adds games that aren't in the db yet, so your manual edits are kept. Use `--rebuild` to start over.
- **Automatic updates:** a normal run checks every base and patch PKG first. If an ID isn't in the db, or there's no db yet, it runs `--build-db` before renaming. So new games are picked up without running `--build-db` yourself. Use `--no-auto-db` to turn this off.
- **Where titles come from:** the title is taken from the base game PKG. If there isn't one, the patch PKG is used, since it holds the game title too. DLC PKGs only hold the DLC's own name. An ID with only DLC, or only a folder name, is reported as not in the db and has to be added by hand.

`ps4_titles.db` isn't part of the repo and is listed in `.gitignore`. It's created on the first run and grows as new games are found. Because git ignores it, it's safe to keep next to the script in a clone, and `git pull` never conflicts with it.

### English names for non-English titles

Some Asian releases only have a Japanese or Korean title. For those, `--build-db` searches English Wikipedia and then Wikidata, and only accepts results described as a video game:

```
CUSA10207: 배틀 가레가 Rev.2016      ->  Battle Garegga Rev.2016
CUSA32997: 怒首領蜂大往生 臨廻転生   ->  DoDonPachi DaiOuJou
```

- The lookup often returns the original game's name, so an edition suffix may be missing. Edit the db if you want the exact PS4 name.
- If nothing is found, the original title is kept.
- Requests are limited to about one per second to respect Wikimedia's rate limits.

## Naming scheme

Every PS4 PKG is named from its own `param.sfo`, whatever it's currently called:

| `CATEGORY` in param.sfo | Type | Name before titles | Final name (default) | Final name (`--keep-id`) |
|---|---|---|---|---|
| `gd`, `gde` | base game / app | `CUSA00900_base.pkg` | `Bloodborne_base.pkg` | `Bloodborne [CUSA00900]_base.pkg` |
| `gp` | patch | `CUSA00900_patch.pkg` | `Bloodborne_patch.pkg` | `Bloodborne [CUSA00900]_patch.pkg` |
| `ac` | DLC / add-on | `CUSA00900_<DLC title>_dlc.pkg` | `Bloodborne_The Old Hunters_dlc.pkg` | `Bloodborne [CUSA00900]_The Old Hunters_dlc.pkg` |

- **DLC names:** the DLC title comes from the DLC PKG's `param.sfo`. If it starts with the game title, that part is dropped because the name already starts with it: "Bloodborne The Old Hunters" becomes `…_The Old Hunters_dlc.pkg`.
- **Folders:** folders and other files with an ID in their name get the ID replaced by the title, e.g. `CUSA00900/` becomes `Bloodborne/`.
- **Other files:** files that aren't PS4 PKGs and have no ID, such as logs, are left alone.
- **Duplicate names:** two patches for the same game in one folder would both become `_patch.pkg`. The second one is logged as an error and left as it is.

### Loose PKGs in the top folder

A PKG directly in `PATH`, rather than in a game folder, is moved into its game's folder:

- **Existing folder:** if one exists for that ID, like `CUSA00900/`, `Bloodborne [CUSA00900]/` or `Bloodborne/`, the PKG is moved there.
- **New folder:** otherwise a folder is created, named like the other game folders: `Bloodborne/`, or `Bloodborne [CUSA00900]/` with `--keep-id`.
- **Undo:** any undo that covers the PKG, whether `--undo`, `--undo-last` or `--undo-match`, moves it back and removes the folder it created once that's empty.

## Running again

Running the script again on renamed items doesn't rename them twice:

- With `--keep-id`, names like `Bloodborne [CUSA00900]` are left as they are.
- Without `--keep-id`, the ` [CUSA00900]` tag is removed, giving `Bloodborne`. So you can switch between the two styles by re-running with or without the option.

## Undo

Every `--apply` records each rename and move in `rename_undo.log`, in the script's folder, so you can reverse them later. There are three ways to undo:

| Command | Reverts | Acts |
|---|---|---|
| `--undo` | Everything recorded under `PATH`, from every `--apply` run | Immediately |
| `--undo-last` | Only the most recent `--apply` run under `PATH` | Preview. Add `--apply` to do it |
| `--undo-match TEXT` | Only renames whose path contains `TEXT` | Preview. Add `--apply` to do it |

`--undo-last` and `--undo-match` can be combined, for example to undo only the matching renames from the last run. Undo always works newest first.

### Examples

Run these from the games folder:

```bash
# revert everything
python3 ps4-pkg-title-renamer/ps4_rename.py --undo

# step back one --apply run at a time: preview, then do it
python3 ps4-pkg-title-renamer/ps4_rename.py --undo-last
python3 ps4-pkg-title-renamer/ps4_rename.py --undo-last --apply

# a single file
python3 ps4-pkg-title-renamer/ps4_rename.py --undo-match "Old Hunters" --apply

# one game: its folder and every file in it
python3 ps4-pkg-title-renamer/ps4_rename.py --undo-match Bloodborne --apply

# games in another folder: pass it as PATH
python3 ps4-pkg-title-renamer/ps4_rename.py ../other-games --undo-last --apply
```

A preview lists every rename it would revert as `current name -> original name` and changes nothing:

```
/games/Bloodborne/Bloodborne_The Old Hunters_dlc.pkg -> /games/Bloodborne/Bloodborne The Old Hunters.pkg  (preview)

Preview only. Re-run with --apply to undo.
```

### How `--undo-match` finds renames

- **What's compared:** the text is compared, ignoring case, with the old and the new path of each rename, relative to `PATH`.
- **Folder names:** a game or folder name matches the folder and everything in it. `Bloodborne` matches `Bloodborne/`, `Bloodborne_base.pkg`, `Bloodborne_The Old Hunters_dlc.pkg` and so on.
- **Title IDs:** an ID only matches where it appears in the old or new name. Folders and base/patch files always had the ID in their original name. A DLC file without `--keep-id` usually didn't, e.g. `Bloodborne The Old Hunters.pkg` became `Bloodborne_The Old Hunters_dlc.pkg`. Use the game name to catch a whole game.
- **Check first:** run without `--apply` to see exactly what matches.

### What undo takes care of

- **Renamed folders:** a single file can be reverted even after its folder was renamed. It's renamed back inside the folder's current name.
- **Items renamed more than once:** if an item was renamed again in a later run, for example a re-run with `--keep-id`, `--undo-match` reverts those later renames too. Otherwise the log would no longer match the files.
- **Loose PKGs:** a PKG that was moved into its game folder goes back to `PATH`. A folder the script created for it is removed once it's empty. If it isn't empty yet, it stays in the log and is removed by a later undo.
- **Several game folders:** every `PATH` shares the same `rename_undo.log`, but undo only touches entries under the `PATH` you give it. Entries for other folders stay in the log.
- **Case-only renames:** renames that only change letter case are handled on case-insensitive drives, such as NTFS and exFAT.

### The undo log

- **Archive:** reverted entries are moved to `rename_undo.log.done` with a note of what was undone and when. Entries that couldn't be restored stay in `rename_undo.log` so you can retry.
- **Runs:** each `--apply` run starts with a `# <timestamp>` line in the log. That's how `--undo-last` knows where the last run begins.
- **Full paths:** the log records full paths. Run undo before moving or re-mounting the games folder under a different path or drive letter, and on the same OS you used for `--apply`.
- **Never deleted automatically:** `--clean-logs` and log rotation never delete `rename_undo.log` or `rename_undo.log.done`.
- **Older versions:** older versions of the script kept `rename_undo.log` in `PATH`. It's merged into the script-folder log automatically on the next run.

## Logs

All logs are kept in the script's folder, not in `PATH`. In a git clone, `.gitignore` excludes them. Every rename or undo run writes `rename_results_<dryrun|apply|undo>_<timestamp>.log`. Only the 5 newest are kept, and older ones are deleted automatically after each run. Use `--keep-logs N` to change the limit, or `--keep-logs 0` to keep every log. `rename_undo.log` is never rotated.

```
=== CHANGED (143) ===
CUSA00900/CUSA00900_base.pkg  ->  Bloodborne_base.pkg
=== NOT CHANGED (39) ===
itemzflow/daemon.log  (no game ID in name)
Bloodborne [CUSA00900]/Bloodborne [CUSA00900]_base.pkg  (already named)
CUSA99999  (ID not in db: CUSA99999)
=== ERRORS (1) ===
CUSA00900/CUSA00900_patch.pkg  (target already exists: Bloodborne_patch.pkg)
```

`--apply` also records every rename in `rename_undo.log`, which the undo options use. See [Undo](#undo).

To delete old results logs:

```bash
python3 ps4_rename.py --clean-logs
```

This deletes every `rename_results_*.log` in the script's folder, plus any left in `PATH` by older versions. It never deletes `rename_undo.log` or `rename_undo.log.done`.

## Notes

- Characters that exFAT/NTFS don't allow are replaced: `:` becomes ` - `; `? * " < > |`, `™` and `®` are removed or replaced.
- Existing files are never overwritten. A name collision is logged as an error and skipped.
- `System Volume Information`, `$RECYCLE.BIN` and the script's own files are skipped.
- Check that your install tools don't rely on ID-named folders. If they do, use `--keep-id`.
