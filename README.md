# PS4 PKG Title Renamer

**Rename PS4 `.pkg` files and `CUSA` title-ID folders to game names, automatically.** `ps4-pkg-title-renamer` reads the `param.sfo` inside each PS4 PKG. From it, the script gets the game title, title ID, type (base game, patch or DLC), version and content ID, and uses them to give every file and folder a clear, consistent name. It's a small Python script with no dependencies, and it runs on Linux, macOS and Windows.

```
CUSA00900/                                   Bloodborne [CUSA00900]/
├── CUSA00900_base.pkg                ->     ├── Bloodborne [CUSA00900] [v1.00] [base].pkg
├── update.pkg                               ├── Bloodborne [CUSA00900] [v1.09] [patch].pkg
└── Bloodborne The Old Hunters.pkg           └── Bloodborne The Old Hunters [CUSA00900] [v1.00] [dlc].pkg
CUSA11253_base.pkg  (loose in root)          Dead Cells [CUSA11253]/
                                             └── Dead Cells [CUSA11253] [v1.00] [base].pkg
```
<sub>Example with `--keep-id --add-version`. The default is just `Bloodborne [base].pkg`, and every tag is optional.</sub>

## Features

- **Renames by what's inside the PKG,** not by its file name. It uses the title, title ID, type, version and content ID from `param.sfo`, so it needs no guessing and no online title-ID database.
- **Recognises base games, patches and DLC** (`CATEGORY` `gd`, `gp`, `ac`) and tags them `[base]`, `[patch]` and `[dlc]`.
- **Optional tags:** title ID (`CUSA00900`), version (`v1.09`), region (`USA`/`EUR`/`JPN`/`ASIA`), content ID. You can also choose the separator, write tags without brackets, or name by ID only.
- **Turns `CUSA` / `CUSAXXXXX` folders into game-name folders,** and moves loose PKGs into their game's folder.
- **English names** for Japanese / Korean / Chinese titles, looked up online once and stored in an editable title database.
- **Safe:**
  - Dry run by default, with a results log.
  - Undo everything, only the last run, or only matching names ([Undo](#undo)).
  - Never overwrites a file.
  - Never changes the contents of a PKG, only names.
- **Detects broken PKGs:** those with a corrupt or missing `param.sfo` are reported and left alone.
- **Safe for exFAT/NTFS drives:** names are valid on USB drives used with a PS4, GoldHEN or Itemzflow.

## Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Linux / macOS](#linux--macos)
  - [Windows](#windows)
  - [Updating](#updating)
- [Quick start](#quick-start)
- [Options](#options)
- [Title database](#title-database)
  - [Why keep a db?](#why-keep-a-db)
  - [GAMES section](#games-section)
  - [PKGS section](#pkgs-section)
  - [Using the db](#using-the-db)
  - [Updating the db](#updating-the-db)
  - [English names for non-English titles](#english-names-for-non-english-titles)
- [Naming scheme](#naming-scheme)
  - [Name style options](#name-style-options)
  - [Loose PKGs in the top folder](#loose-pkgs-in-the-top-folder)
- [Running again](#running-again)
- [Undo](#undo)
  - [Examples](#examples)
  - [How `--undo-match` finds renames](#how---undo-match-finds-renames)
  - [What undo takes care of](#what-undo-takes-care-of)
  - [The undo log](#the-undo-log)
- [Logs](#logs)
- [FAQ](#faq)
- [Notes](#notes)

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

# 2. clone the repo
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
- **Old folder name:** `ps4-title-renamer`, the repo's previous name, is still accepted, so existing clones keep working.

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
| `--no-title` | Use the title ID instead of the game title: `CUSA00900 [patch].pkg` |
| `--add-version` | Add the PKG version to `.pkg` names: `Bloodborne [v1.09] [patch].pkg` |
| `--add-content-id` | Add the content ID to `.pkg` names: `Bloodborne [UP9000-CUSA00900_00-BLOODBORNE000000] [base].pkg` |
| `--no-type` | Leave out the `[base]` / `[patch]` / `[dlc]` tag: `Bloodborne [v1.09].pkg` |
| `--add-region` | Add the region tag after the title/ID: `Bloodborne [CUSA00900] [USA] [patch].pkg` |
| `--sep SEP` | Use `SEP` instead of spaces in generated names: `--sep _` gives `Grand_Theft_Auto_V_[patch].pkg`. `""` means no separator |
| `--no-brackets` | Write tags without `[ ]`: `Bloodborne CUSA00900 v1.09 patch.pkg` |
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

`ps4_titles.db` is a plain-text file next to the script. It has two sections, and you can edit both by hand:

```
# GAMES: TitleID|Title|Region
CUSA00900|Bloodborne™|USA
CUSA07439|DARK SOULS™ III|EUR
CUSA10207|Battle Garegga Rev.2016|ASIA
CHTM00777|PS4 Cheats Manager|HB

# PKGS: ContentID|Version|Type|TitleID|Title
UP9000-CUSA00900_00-BLOODBORNE000000|01.00|base|CUSA00900|Bloodborne™
UP9000-CUSA00900_00-BLOODBORNE000000|01.09|patch|CUSA00900|Bloodborne™
UP9000-CUSA00900_00-SPEXPANSIONDLC03|01.00|dlc|CUSA00900|Bloodborne The Old Hunters
```

### Why keep a db?

Every run reads each PKG's `param.sfo` anyway, so the db isn't a speed-up. It's there for things the PKGs alone can't give you:

| The db | Without it |
|---|---|
| Remembers English names found online for Japanese/Korean titles | Every run would repeat the online lookups: slower, rate-limited, and needs internet |
| Keeps your fixes: edit a game or DLC title and every run uses it ([Using the db](#using-the-db)) | No way to change a name without editing the script |
| Keeps game titles for folders with only DLC, or no PKGs | DLC PKGs only contain the DLC's own name, so the game title would be unknown |
| Gives one title per game, taken from the base game, for all its files | Patch PKGs sometimes word the title differently |
| Holds the region used by `--add-region` | |
| Records every PKG you have, with content ID, version and type | |

### GAMES section

- **Title:** comes from the PKG's `param.sfo`. The English localized title (`TITLE_01`) is used when the PKG has one. The title is taken from the base game PKG, or from a patch if there's no base game. Edit it to rename the game everywhere.
- **Region:** comes from the content ID prefix: `UP` = USA, `EP` = EUR, `JP` = JPN, `HP` = ASIA, `KP` = KOR. Homebrew is marked `HB`. `--add-region` uses it.
- **Missing games:** an ID with only DLC, or only a folder name, is reported as not in the db and has to be added by hand.

### PKGS section

- **Lines:** one line per PKG file and version.
  - **ContentID:** the PKG's content ID. A base game and its patches share one, and each DLC has its own.
  - **Version:** the version the PKG is known by. That's `APP_VER` for patches and `VERSION` for base games and DLC. See **Version** under [Name style options](#name-style-options).
  - **Type:** `base`, `patch` or `dlc`.
  - **TitleID:** the game the PKG belongs to.
  - **Title:** the title as written in that PKG. For DLC it's the DLC's name. For base games and patches it's the game title as the PKG spells it.
- **What's used for naming:**
  - **DLC:** the DLC's Title is used in `[dlc]` names, so you can edit it to rename a DLC, e.g. to fix a Japanese-only DLC name. It's placed right after the game title, before any tags, and a repeated game title at its start is dropped: `Bloodborne The Old Hunters [CUSA00900] [dlc].pkg`.
  - **Base games and patches:** their Title is normally only a record. The script uses it to recognise the original game title at the start of a DLC's name, even after you've edited the game's title in GAMES. If you edit it, whatever you add goes into that PKG's name, like a DLC title. See [Using the db](#using-the-db).
- **What's only a record:** type and version are always read from the PKG itself. The PKGS section is a record of your collection, and a newer patch simply adds a new line.

### Using the db

The db is plain text, so you can open it in any text editor. After editing, do a dry run to check the new names, then `--apply`. The examples assume the script's folder is `ps4-pkg-title-renamer/` inside your games folder.

**Rename a game.** Edit its title in the GAMES section:

```
CUSA00900|Bloodborne™|USA             ->   CUSA00900|Bloodborne GOTY|USA
```

The game's folder and all its PKGs follow, in whatever style you use: `Bloodborne GOTY [CUSA00900]/Bloodborne GOTY [CUSA00900] [patch].pkg`. DLC names follow too, keeping their DLC part: `Bloodborne GOTY The Old Hunters [CUSA00900] [dlc].pkg`. Use this to fix a lookup that missed an edition suffix, e.g. `DoDonPachi DaiOuJou` becomes `DoDonPachi DaiOuJou Re-incarnation`, or to shorten long titles.

**Rename a DLC.** Edit the last field of its PKGS line:

```
UP9000-CUSA00900_00-SPEXPANSIONDLC03|01.00|dlc|CUSA00900|Bloodborne The Old Hunters
                                                ->   ...|dlc|CUSA00900|The Old Hunters Expansion
```

This is the way to give a Japanese-only DLC an English name, since DLC titles are never looked up online. If a PKG isn't in the db yet, run a dry run first. It adds every new PKG to the db, so you can edit the line and then `--apply`.

**Label a patch or base game PKG,** e.g. a mod or a special build. Edit the Title field of its PKGS line and add your label:

```
UP1004-CUSA23501_00-GTATHREE00000001|01.08|patch|CUSA23501|Grand Theft Auto III – The Definitive Edition
                     ->   ...|patch|CUSA23501|Grand Theft Auto III – The Definitive Edition Soundtrack Restoration Mod
```

On the next `--apply`, what you added goes right after the game title: `Grand Theft Auto III – The Definitive Edition Soundtrack Restoration Mod [CUSA23501] [v1.08] [patch].pkg`. You can also replace the whole Title, e.g. `Soundtrack Restoration Mod`. The game title is still added in front. To go back to the plain name, restore the original Title, i.e. what the PKG says.

- **Only edited titles count:** a base or patch Title is used only when it differs from the title inside the PKG.
- **One line per content ID, type and version:** a line applies to every PKG with the same content ID, type and version. A mod patch built from an official patch usually has exactly the same `param.sfo` values as that patch. If both are on the drive, they share one line, so the label applies to both, and they'd get the same name. The second one is then reported as an error and left alone.

**Change or fix a region tag** (`--add-region`). Edit the Region field of the game. The recognised values are `USA`, `EUR`, `JPN`, `ASIA`, `KOR` and `HB`. Any other value is kept in the db but isn't added as a tag.

**Name a game the script can't find.** A folder or file with a title ID but no base game or patch PKG, e.g. only DLC, is reported as `ID not in db`. Add a GAMES line yourself and run again:

```
CUSA12345|My Game|USA
```

**See what you have.** The PKGS section lists every PKG, with its type and version:

```bash
grep '|patch|' ps4-pkg-title-renamer/ps4_titles.db             # every patch and its version
grep '|dlc|CUSA00900|' ps4-pkg-title-renamer/ps4_titles.db     # all DLC of one game
grep 'CUSA00900' ps4-pkg-title-renamer/ps4_titles.db           # everything for one game
```

```powershell
Select-String '\|patch\|' ps4-pkg-title-renamer\ps4_titles.db  # Windows
```

A game with several `patch` lines has had more than one patch version on your drive. The db keeps a line for each version it has seen.

**Work offline.** Once the db holds the English names, runs don't need internet. `--offline` skips the online lookup for any new game.

**Use the same names on another machine.** Copy `ps4_titles.db` next to the script there. Your edited titles, DLC names and English names come along. It's plain UTF-8 text, so it works on Linux, macOS and Windows.

**Back up your edits.** Git ignores the db, so copy `ps4_titles.db` somewhere safe before `--build-db --rebuild`. A rebuild starts from the PKGs again and discards every edit.

### Updating the db

- **Location:** the db is always `ps4_titles.db` next to the script. `--db FILE` overrides this. A `ps4_titles.db` left in `PATH` by older versions is merged into it automatically and then removed.
- **Your edits are kept:** `--build-db` only adds games and PKGs that aren't in the db yet. Use `--rebuild` to start over.
- **Automatic updates:** a normal run checks every PKG first. If a game or PKG isn't in the db, or there's no db yet, it runs `--build-db` before renaming, so you never need to run `--build-db` yourself. Use `--no-auto-db` to turn this off.
- **Older dbs:** a db from an older version, with the games section only, keeps working and gets its PKGS section on the next run.

`ps4_titles.db` isn't part of the repo and is listed in `.gitignore`. It's created on the first run and grows as new games are found. Because git ignores it, it's safe to keep next to the script in a clone, and `git pull` never conflicts with it.

### English names for non-English titles

Some Asian releases only have a Japanese or Korean title. For those, `--build-db` searches English Wikipedia and then Wikidata, and only accepts results described as a video game:

```
CUSA10207: 배틀 가레가 Rev.2016      ->  Battle Garegga Rev.2016
CUSA32997: 怒首領蜂大往生 臨廻転生   ->  DoDonPachi DaiOuJou
```

- **Only game descriptions accepted:** results describing a studio, a person or a series are rejected, and parts of a title shorter than 2 characters aren't searched. A wrong English name is worse than none.
- **Edition suffixes:** the lookup often returns the original game's name, so an edition suffix may be missing. Edit the db if you want the exact PS4 name.
- **Nothing found:** the original title is kept.
- **DLC titles are never looked up:** searches for them return the base game, its studio or its director, not the DLC. A non-English DLC title stays as in the PKG, and you can edit it in the PKGS section.
- Requests are limited to about one per second to respect Wikimedia's rate limits.

## Naming scheme

Every PS4 PKG is named from its own `param.sfo`, whatever it's currently called. The PKG type is a tag like the others, `[base]`, `[patch]` or `[dlc]`, and it's always the last tag:

```
<title>[ <ID>][ <region>][ <version>][ <content ID>] [base].pkg
<title>[ <ID>][ <region>][ <version>][ <content ID>] [patch].pkg
<title> <DLC title>[ <ID>][ <region>][ <version>][ <content ID>] [dlc].pkg
```

- **`<title>`:** the game title, or the title ID with `--no-title`, in which case there's no separate ID tag.
- **DLC title:** comes right after the game title, before every tag, so the full name of a DLC reads as one piece, e.g. `Bloodborne The Old Hunters`.
- **Tags:** `[ID]` with `--keep-id`, `[region]` with `--add-region`, plus version and content ID. Each is joined with `--sep` and written in brackets unless you use `--no-brackets`.
- **Type tag:** always last. `--no-type` leaves it out.
- **Folders:** named `<title>[ <ID>][ <region>]`, e.g. `Bloodborne [CUSA00900] [USA]/`.

| `CATEGORY` in param.sfo | Type | Default | `--keep-id` | `--no-title` |
|---|---|---|---|---|
| `gd`, `gde` | base game / app | `Bloodborne [base].pkg` | `Bloodborne [CUSA00900] [base].pkg` | `CUSA00900 [base].pkg` |
| `gp` | patch | `Bloodborne [patch].pkg` | `Bloodborne [CUSA00900] [patch].pkg` | `CUSA00900 [patch].pkg` |
| `ac` | DLC / add-on | `Bloodborne The Old Hunters [dlc].pkg` | `Bloodborne The Old Hunters [CUSA00900] [dlc].pkg` | `CUSA00900 Bloodborne The Old Hunters [dlc].pkg` |
| folder | | `Bloodborne/` | `Bloodborne [CUSA00900]/` | `CUSA00900/` |

- **DLC names:** the DLC title comes from the DLC PKG's `param.sfo`. It goes right after the game title, before the ID and all other tags, joined with the normal separator (a space, or `--sep`). If it starts with the game title, that part isn't repeated: "Bloodborne The Old Hunters" becomes `Bloodborne The Old Hunters [CUSA00900] [dlc].pkg`, not `Bloodborne Bloodborne The Old Hunters …`. A DLC title that doesn't start with the game title is simply added after it: `Pre-order` becomes `FANTASY LIFE i - The Girl Who Steals Time Pre-order [dlc].pkg`. With `--no-title`, the full DLC title follows the ID: `CUSA00900 Bloodborne The Old Hunters [dlc].pkg`.
- **Folders:**
  - A folder with a title ID in its name is renamed to its game's name, keeping any other text: `CUSA00900 backup/` becomes `Bloodborne backup/`.
  - A folder without an ID is only renamed when its name starts with the game title and all the PKGs directly inside it belong to that game. That's what lets a folder renamed earlier as `Bloodborne/` be switched to `CUSA00900/` or `Bloodborne [CUSA00900]/`.
- **Other files:** files that aren't PS4 PKGs and have no ID, such as logs, are left alone.
- **Duplicate names:** two patches for the same game in one folder would both become `Bloodborne [patch].pkg`. The second one is logged as an error and left as it is. Dry runs catch this too. Use `--add-version` to give each patch its own name, e.g. `Bloodborne [v1.04] [patch].pkg` and `Bloodborne [v1.09] [patch].pkg`. With `--no-type`, a base game and its patch collide the same way, so combine `--no-type` with `--add-version`.

### Name style options

These options can be combined freely:

| Option | Effect | Applies to | Example |
|---|---|---|---|
| `--keep-id` | adds the title ID after the title | folders and files | `Bloodborne [CUSA00900] [patch].pkg` |
| `--no-title` | uses the title ID instead of the game title | folders and files | `CUSA00900 [patch].pkg` |
| `--add-version` | adds a version tag before the type tag | `.pkg` files | `Bloodborne [v1.09] [patch].pkg` |
| `--add-content-id` | adds a content ID tag before the type tag | `.pkg` files | `Bloodborne [UP9000-CUSA00900_00-BLOODBORNE000000] [patch].pkg` |
| `--no-type` | leaves out the type tag | `.pkg` files | `Bloodborne [v1.09].pkg` |
| `--add-region` | adds the region tag (from the db) after the title/ID | folders and files | `Bloodborne [CUSA00900] [USA] [patch].pkg` |
| `--sep SEP` | uses `SEP` instead of spaces, in titles and between tags | folders and files | `--sep _`: `Grand_Theft_Auto_V_[CUSA00419]_[patch].pkg` |
| `--no-brackets` | writes tags without `[ ]` | folders and files | `Bloodborne CUSA00900 v1.09 patch.pkg` |

Examples with several options:

```
--keep-id --add-version --add-content-id
Bloodborne [CUSA00900]/
├── Bloodborne [CUSA00900] [v1.00] [UP9000-CUSA00900_00-BLOODBORNE000000] [base].pkg
├── Bloodborne [CUSA00900] [v1.09] [UP9000-CUSA00900_00-BLOODBORNE000000] [patch].pkg
└── Bloodborne The Old Hunters [CUSA00900] [v1.00] [UP9000-CUSA00900_00-SPEXPANSIONDLC03] [dlc].pkg

--keep-id --add-version --sep _
Grand_Theft_Auto_V_[CUSA00419]/
└── Grand_Theft_Auto_V_[CUSA00419]_[v13.37]_[patch].pkg

--no-title --add-version --no-brackets
CUSA00900/
├── CUSA00900 v1.09 patch.pkg
└── CUSA00900 Bloodborne The Old Hunters v1.00 dlc.pkg

--add-version --no-type
Bloodborne/
├── Bloodborne [v1.00].pkg
├── Bloodborne [v1.09].pkg
└── Bloodborne The Old Hunters [v1.00].pkg
```

- **Version:** read from the PKG's `param.sfo`, and the field used depends on the type. Leading zeros are dropped, so `01.09` becomes `v1.09`:

  | Type | Field | Why |
  |---|---|---|
  | patch | `APP_VER` | the version the patch updates the game to. A patch's `VERSION` is usually `01.00` |
  | base game | `VERSION` | the version the base PKG was built at, e.g. `v1.07` for a base PKG that already contains updates. A base PKG's `APP_VER` is always `01.00` |
  | DLC | `VERSION` | DLC has no `APP_VER` |
- **Content ID:** the PKG's full content ID, `<region prefix>-<title ID>_00-<label>`. It's unique per PKG: each DLC has its own, and a base game and its patches share one. The prefix also shows the region: `UP` = USA, `EP` = EUR, `JP` = JPN, `HP` = Asia.
- **Folders:** version, content ID and type are only added to `.pkg` files, because a folder holds several PKGs of different versions and types.
- **`--sep`:**
  - `SEP` can be any characters that are valid in file names, e.g. `_`, `.` or `-`. `--sep ""` removes spaces entirely.
  - It replaces the spaces the script generates, in titles, DLC titles and between tags, including before the type tag: `Bloodborne_The_Old_Hunters_[CUSA00900]_[dlc].pkg`.
  - Text the script doesn't generate keeps its spaces, e.g. `backup` in `Bloodborne backup/`.
- **`--no-brackets`:** tags are then separated only by `SEP`. The script still recognises its own names when you switch styles later.
- **Switching styles:** each style is applied in full on every run. See [Running again](#running-again).

### Loose PKGs in the top folder

A PKG directly in `PATH`, rather than in a game folder, is moved into its game's folder:

- **Existing folder:** if one exists for that ID, like `CUSA00900/`, `Bloodborne [CUSA00900]/` or `Bloodborne/`, the PKG is moved there.
- **New folder:** otherwise a folder is created, named `<game>` in the current style: `Bloodborne/`, `Bloodborne [CUSA00900]/` with `--keep-id`, or `CUSA00900/` with `--no-title`. A folder holding only that game's PKGs also counts as existing.
- **Undo:** any undo that covers the PKG, whether `--undo`, `--undo-last` or `--undo-match`, moves it back and removes the folder it created once that's empty.

## Running again

Each run applies the naming options you give to everything, so re-running never renames anything twice:

- **Same options:** a second run with the same options changes nothing.
- **Different options:** a run with different options re-styles existing names instead of adding to them. So you can switch styles at any time:

  ```
  (default)                  Bloodborne/Bloodborne [patch].pkg
  --keep-id --add-version    Bloodborne [CUSA00900]/Bloodborne [CUSA00900] [v1.09] [patch].pkg
  --no-title --no-type       CUSA00900/CUSA00900.pkg
  --keep-id --sep _          Bloodborne_[CUSA00900]/Bloodborne_[CUSA00900]_[patch].pkg
  (default)                  Bloodborne/Bloodborne [patch].pkg
  ```

- **Where names come from:** PKG names are rebuilt from `param.sfo` every time. Folder names are rebuilt from the title ID in the name, or from the PKGs inside.
- **Undo:** every switch is recorded, so undo still works across style changes.

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
/games/Bloodborne/Bloodborne The Old Hunters [dlc].pkg -> /games/Bloodborne/Bloodborne The Old Hunters.pkg  (preview)

Preview only. Re-run with --apply to undo.
```

### How `--undo-match` finds renames

- **What's compared:** the text is compared, ignoring case, with the old and the new path of each rename, relative to `PATH`.
- **Folder names:** a game or folder name matches the folder and everything in it. `Bloodborne` matches `Bloodborne/`, `Bloodborne [base].pkg`, `Bloodborne The Old Hunters [dlc].pkg` and so on.
- **Title IDs:** an ID only matches where it appears in the old or new name. Folders and base/patch files always had the ID in their original name. A DLC file without `--keep-id` usually didn't, e.g. `Bloodborne The Old Hunters.pkg` became `Bloodborne The Old Hunters [dlc].pkg`. Use the game name to catch a whole game.
- **Check first:** run without `--apply` to see exactly what matches.

### What undo takes care of

- **Renamed folders:** a single file can be reverted even after its folder was renamed. It's renamed back inside the folder's current name.
- **Items renamed more than once:** if an item was renamed again in a later run, for example a re-run with `--keep-id` or another style, `--undo-match` reverts those later renames too. Otherwise the log would no longer match the files.
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
CUSA00900/CUSA00900_base.pkg  ->  Bloodborne [base].pkg
=== NOT CHANGED (39) ===
itemzflow/daemon.log  (no game ID in name)
Bloodborne [CUSA00900]/Bloodborne [CUSA00900] [base].pkg  (already named)
CUSA99999  (ID not in db: CUSA99999)
=== ERRORS (1) ===
CUSA00900/CUSA00900_patch.pkg  (target already exists: Bloodborne [patch].pkg)
```

`--apply` also records every rename in `rename_undo.log`, which the undo options use. See [Undo](#undo).

To delete old results logs:

```bash
python3 ps4_rename.py --clean-logs
```

This deletes every `rename_results_*.log` in the script's folder, plus any left in `PATH` by older versions. It never deletes `rename_undo.log` or `rename_undo.log.done`.

## FAQ

**How do I rename PS4 PKG files to their game names?**
Put the script in your PKG folder and run a dry run, then apply:
```bash
python3 ps4-pkg-title-renamer/ps4_rename.py            # preview
python3 ps4-pkg-title-renamer/ps4_rename.py --apply    # rename
```
See [Quick start](#quick-start) for more.

**What is a CUSA number / PS4 title ID?**
Every PS4 game has a title ID such as `CUSA00900`, which is Bloodborne (USA). PKG dumps and downloads are often named only by that ID or by their content ID, e.g. `UP9000-CUSA00900_00-BLOODBORNE000000`. The script reads the ID and the real game title from the PKG's `param.sfo` and renames the files for you.

**How can I tell whether a PKG is the base game, a patch (update) or DLC?**
The script reads the `CATEGORY` field in `param.sfo` (`gd` = base game, `gp` = patch, `ac` = DLC/add-on) and tags the file `[base]`, `[patch]` or `[dlc]`. Add `--add-version` to also see the version, e.g. `[v1.09]` for a patch.

**Which version does `--add-version` show?**
For a patch, the version it updates the game to (`APP_VER` in `param.sfo`). For a base game, the version the base PKG was built at (`VERSION`), because a base PKG's `APP_VER` is always `01.00`. For example, Vice City's base PKG is `v1.07` and its patch is `v1.08`.

**Does it work with fake PKGs (fPKG), GoldHEN and Itemzflow?**
It works with any PS4 PKG whose `param.sfo` can be read, which includes fake PKGs and homebrew. It only renames files and folders. It never changes the contents of a PKG, so the PKGs install the same way afterwards. Check whether your install tool expects ID-named folders. If it does, use `--keep-id` or `--no-title`.

**Can I keep the CUSA ID in the name?**
Yes, `--keep-id` gives `Bloodborne [CUSA00900] [base].pkg`. `--no-title` gives `CUSA00900 [base].pkg`, and `--add-region` adds `[USA]`.

**Can I undo a rename?**
Yes. `--undo` reverts everything, `--undo-last` reverts the last run, and `--undo-match TEXT` reverts only matching names, e.g. one game or one file. See [Undo](#undo).

**Does it need an internet connection?**
Only to look up English names for Japanese/Korean/Chinese titles, and only once per game, because results are saved in the db. Use `--offline` to skip the lookup.

**Does it run on Windows?**
Yes, Windows 10/11, Linux and macOS, with Python 3.8+ and no other dependencies. See [Installation](#installation).

## Notes

- Characters that exFAT/NTFS don't allow are replaced: `:` becomes ` - `; `? * " < > |`, `™` and `®` are removed or replaced.
- Existing files are never overwritten. A name collision is logged as an error and skipped.
- **Broken or unreadable PKGs:** every `.pkg` is checked before its `param.sfo` is used. A PS4 PKG whose `param.sfo` can't be used is logged under ERRORS with the reason and left as it is. It's usually a bad or incomplete download. The possible reasons are:

  | Reason in the log | Meaning |
  |---|---|
  | `param.sfo not found in pkg` | the PKG has no `param.sfo` entry |
  | `param.sfo corrupt or encrypted: bad signature` | the data isn't a valid, unencrypted `param.sfo` |
  | `param.sfo corrupt: ...` / `pkg corrupt: ...` | offsets, sizes or tables point outside the file |
  | `pkg unreadable: ...` | the file couldn't be read, e.g. permissions or a disk error |

  - **Summary:** both a rename run and `--build-db` end with a count of the PKGs that couldn't be read. `--build-db` also lists each one.
  - **Size limit:** a `param.sfo` is never read past 1 MB, even if a corrupt header claims more.
  - **Other `.pkg` files:** a file with a `.pkg` extension that isn't a PS4 PKG at all, i.e. has no PKG header, is treated like any other file. It's renamed only if its name contains a title ID, and otherwise logged as `not a PS4 pkg`.
- `System Volume Information`, `$RECYCLE.BIN` and the script's own files are skipped.
- Check that your install tools don't rely on ID-named folders. If they do, use `--keep-id`.
