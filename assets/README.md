# Application Assets

This directory contains assets for the HiCeeBox application.

## Application Icon

### Required Files

For macOS packaging, you need an application icon in `.icns` format:

- `icon.icns` - macOS application icon

### Creating the Icon

#### Method 1: From PNG (macOS command line)

1. Create a 1024x1024 PNG image named `icon_1024.png`
2. Run the following commands:

```bash
# Create iconset folder
mkdir HiCeeBox.iconset

# Generate all required sizes
sips -z 16 16     icon_1024.png --out HiCeeBox.iconset/icon_16x16.png
sips -z 32 32     icon_1024.png --out HiCeeBox.iconset/icon_16x16@2x.png
sips -z 32 32     icon_1024.png --out HiCeeBox.iconset/icon_32x32.png
sips -z 64 64     icon_1024.png --out HiCeeBox.iconset/icon_32x32@2x.png
sips -z 128 128   icon_1024.png --out HiCeeBox.iconset/icon_128x128.png
sips -z 256 256   icon_1024.png --out HiCeeBox.iconset/icon_128x128@2x.png
sips -z 256 256   icon_1024.png --out HiCeeBox.iconset/icon_256x256.png
sips -z 512 512   icon_1024.png --out HiCeeBox.iconset/icon_256x256@2x.png
sips -z 512 512   icon_1024.png --out HiCeeBox.iconset/icon_512x512.png
sips -z 1024 1024 icon_1024.png --out HiCeeBox.iconset/icon_512x512@2x.png

# Convert to .icns
iconutil -c icns HiCeeBox.iconset

# Move to assets folder
mv HiCeeBox.icns icon.icns

# Clean up
rm -rf HiCeeBox.iconset
```

#### Method 2: Online Conversion

1. Go to https://cloudconvert.com/png-to-icns
2. Upload your 1024x1024 PNG
3. Download the `.icns` file
4. Rename to `icon.icns` and place in this folder

#### Method 3: Using Photoshop/Sketch/Figma

1. Design your icon at 1024x1024
2. Export as PNG
3. Use Method 1 or 2 to convert to `.icns`

Use a 1024×1024 PNG; macOS will apply rounded corners. Without a custom icon, the build uses the default.

### Temporary icon

If you don't have an icon yet, the build scripts will work without it (using default Python icon). To create a simple placeholder:

```bash
# Create a simple colored square as placeholder
# (macOS only - requires ImageMagick)
convert -size 1024x1024 xc:'#2E86AB' icon_1024.png
```

Optional: `background.png` (DMG, 600×400), `logo.png`, `screenshot.png`. The spec uses `icon.icns` from this folder when present.

