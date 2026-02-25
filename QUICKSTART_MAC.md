# macOS Build Quick Start

## Step 1: Get the project on your Mac

Download or clone the project folder to your Mac (e.g. `~/Downloads/HiCeeBox` or wherever you keep it).

## Step 2: Set up the environment

Open Terminal and run (adjust the path to your project):

```bash
cd /path/to/HiCeeBox   # your actual path

# Install Conda if needed: https://docs.conda.io/en/latest/miniconda.html

conda create -n HiCeeBox python=3.10 -y
conda activate HiCeeBox

pip install -e .
pip install PySide6 pyinstaller

conda install -c conda-forge libcurl -y
pip install hic-straw cooler pyBigWig pandas
```

## Step 3: Test the app

```bash
# Test that GUI starts
hiceebox-gui
```

If the window opens, setup is successful. Press `Cmd+Q` to quit.

## Step 4: One-command build

```bash
# Run the build script
./build_macos.sh
```

The script will:
1. Build the app with PyInstaller
2. Create `dist/HiCeeBox.app`
3. Create `HiCeeBox-0.1.0.dmg`

## Step 5: Test the DMG

```bash
# Mount DMG
open HiCeeBox-0.1.0.dmg

# Drag HiCeeBox.app to Applications and launch from there
```

You now have a distributable DMG: `HiCeeBox-0.1.0.dmg`.

---

## Distributing to others

**What to give:** The file `HiCeeBox-0.1.0.dmg` (in the project folder after `./build_macos.sh`). Recipients do **not** need Python, Conda, or any dev tools—just macOS 10.15 or later.

**How to share:**
- **DMG (recommended):** Upload `HiCeeBox-0.1.0.dmg` to Google Drive, Dropbox, OneDrive, or create a [GitHub Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) and attach the DMG.
- **Alternative:** Zip the app: `zip -r HiCeeBox-0.1.0.zip dist/HiCeeBox.app`, then share the zip.

**Instructions for recipients:**
1. Download the DMG (or unzip the .app).
2. Open the DMG and drag **HiCeeBox.app** to **Applications** (or double‑click to run from the DMG).
3. First time: if macOS says the app is from an unidentified developer, go to **System Settings → Privacy & Security** and click **Open Anyway** for HiCeeBox. If it says "damaged", they can run in Terminal: `xattr -cr /Applications/HiCeeBox.app`.
4. Launch HiCeeBox from Applications or Spotlight.

---

## Common issues

### 1. "command not found: pyinstaller"

```bash
pip install pyinstaller
```

### 2. "Permission denied: ./build_macos.sh"

```bash
chmod +x build_macos.sh
./build_macos.sh
```

### 3. "App is damaged and can't be opened"

Open System Preferences → Security & Privacy → allow opening the app.

Or run in Terminal:
```bash
xattr -cr dist/HiCeeBox.app
```

### 4. App or DMG opens then crashes immediately

The app was updated to force the matplotlib Qt backend in the frozen build. If it still crashes:

1. Run the app from Terminal to see the error:
   ```bash
   /path/to/HiCeeBox/dist/HiCeeBox.app/Contents/MacOS/HiCeeBox
   ```
2. Or run with console enabled: edit `HiCeeBox.spec`, set `console=True` in the `EXE(...)` call, rebuild with `./build_macos.sh --clean`, then open the app to see the console window with the traceback.

### 5. Cannot type in text fields (Gene, region, etc.)

The packaged app sets `QT_IM_MODULE=""` so Qt uses the system (Cocoa) input. If you still cannot type:

1. **Run from Terminal** with Qt’s input module:
   ```bash
   QT_IM_MODULE=qt /path/to/HiCeeBox/dist/HiCeeBox.app/Contents/MacOS/HiCeeBox
   ```
2. Or try leaving it unset:
   ```bash
   unset QT_IM_MODULE
   /path/to/HiCeeBox/dist/HiCeeBox.app/Contents/MacOS/HiCeeBox
   ```
3. Rebuild after any spec change: `./build_macos.sh --clean`.

### 6. Qt platform plugin not found

```bash
conda install -c conda-forge qt-main
```

### 7. Build fails: missing module

Add the missing module to the `hiddenimports` list in `HiCeeBox.spec`.

### 8. Build error: Failed building wheel for hic-straw/pyBigWig

**Error:**
```
xcode-select: note: No developer tools were found
RuntimeError: Unsupported compiler -- at least C++11 support is needed!
```

**Fix:**

**Option 1: Install Xcode Command Line Tools (recommended)**

In Terminal:
```bash
xcode-select --install
```

If you see "no install could be requested", install manually:
1. Open **System Settings** > **Privacy & Security** > **Developer Mode**
2. Or go to https://developer.apple.com/download/all/
3. Download and install "Command Line Tools for Xcode"

**Option 2: Use conda for prebuilt packages**

If Xcode tools are problematic, try conda-forge:
```bash
conda activate HiCeeBox
conda install -c conda-forge pybigwig -y
pip install hic-straw
```

**Verify:**
```bash
python -c "import hic_straw; import pyBigWig; print('OK')"
```

---

## Advanced options

### Custom app icon

1. Use a 1024×1024 PNG.
2. Put it in `assets/` as `icon_1024.png`.
3. See `assets/README.md` for the full `sips`/`iconutil` commands to generate `icon.icns`.

### Code signing (optional)

If you have an Apple Developer account:

```bash
# List certificates
security find-identity -v -p codesigning

# Sign
codesign --deep --force --sign "Developer ID Application: Your Name" dist/HiCeeBox.app

# Verify
codesign --verify --deep --strict dist/HiCeeBox.app
```

### Reduce app size

Edit `HiCeeBox.spec` and add unneeded libraries to the `excludes` list.

---

## File reference

- `HiCeeBox.spec` - PyInstaller config
- `build_macos.sh` - Build script
- `setup_py2app.py` - Alternative py2app setup (optional)
- `pyproject.toml` - Project config

## More info

- Python API: `examples/HiCeeBox_Tutorial.ipynb`
- Full example: `examples/HiCeeBox_Demo.ipynb`
- Main docs: `README.md`


