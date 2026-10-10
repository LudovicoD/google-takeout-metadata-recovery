# Google Takeout Photos Recover Metadata (Fork)

This is a modified and improved version of the original Google Takeout Photos Recover project. It parses all files (images and videos) and adds the metadata present in the JSON sidecar files provided by Google Takeout.

## Motivation
I recently needed to change my phone, but I had over 15 GB of photos and videos—exceeding the free storage limit on Google. To free up space, I downloaded my Google Photos archive using Google Takeout and backed up everything to an external hard drive.

Upon inspecting the files, I realized that all EXIF metadata (dates, locations, descriptions) was separated into JSON sidecar files rather than embedded into the images and videos themselves. I searched GitHub for a solution and found the original repository, which aimed to fix this exact issue. However, when I tested it on my setup, it didn't work out of the box. 

After applying several fixes and improvements, I got it running smoothly. I am making these modifications public so anyone facing the same issue can easily recover their photos' metadata.

## Modifications & Improvements
Compared to the original project, this version includes:
- **Dependency Optimization:** Removed the external dependency on `libmagic` to simplify installation and ensure cross-platform compatibility (especially on Windows).
- **Path and Special Characters Fix:** Improved handling of paths and special characters (such as emojis or accented characters) during file processing.
- **Bug Fixes & Stability:** Various code refinements to handle specific image formats and directory parsing more reliably.

## Installation

You will need Python 3 installed on your system.

### Requirements
You need `exiftool` installed:

- **macOS (via Homebrew):**
  ```sh
  brew install exiftool

```

* **Windows / Linux:** Make sure `exiftool` is installed and accessible in your system PATH.

### Setup Virtual Environment

It is recommended to use a Python virtual environment:

```sh
python3 -m venv venv
# On Windows use: venv\Scripts\activate
# On macOS/Linux use: source venv/bin/activate
pip install -r requirements.txt

```

### Running the tool

To run this tool, provide the folder containing your Google Takeout exported photos.

Unzip all files. If your export is split into multiple parts, copy all folders (ending with `0001`, `0002`, etc.) into the main `takeout` folder and pass it as input to the tool:

```sh
python main.py takeout recovered

```

The tool will process all photos and videos, embedding the correct EXIF metadata, and save the output into the `recovered` folder.

### Important Note

Always back up your photos and videos before running this tool. The author assumes no responsibility for any data loss or damage.

## Supported file types

* jpeg
* heic
* tiff
* png
* webp
* gif
* mp4

## Supported EXIF Tags

* DateTime
* DateTimeOriginal
* DateTimeDigitized
* GPSVersionID
* GPSLatitudeRef
* GPSLatitude
* GPSLongitudeRef
* GPSLongitude
* GPSAltitudeRef
* GPSAltitude
* Caption
* Description
* ImageDescription
* Title
* ObjectDescription
* PreservedFileName

## License

This project is licensed under the terms of the **GNU General Public License v3.0 (GPL-3.0)**. See the `LICENSE` file for details.

```

```