# Image Pixelator

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/downloads/)

A simple command-line tool written in Python to convert images into pixel art.

This script takes an input image, downscales it to create larger "pixels", optionally reduces the color palette, and then scales it back up to the original size using nearest-neighbor interpolation to maintain the blocky aesthetic.

## Features

* Adjustable pixel block size.
* Optional color palette reduction (quantization).
* Handles various image formats supported by Pillow (PNG, JPG, etc.).
* Command-line interface for easy scripting.

## Requirements

* Python 3.6 or higher
* Pillow library (`pip install Pillow`)

## Setup

Follow these steps to set up the project and its dependencies using a virtual environment.

1.  **Clone or Download:**
    Get the `pixelator.py` script into a directory on your computer.

2.  **Navigate to Directory:**
    Open your terminal or command prompt and change to the directory containing the script:
    ```bash
    cd path/to/your/pixelator_directory
    ```

3.  **Create Virtual Environment:**
    Create a Python virtual environment named `.venv`:
    ```bash
    python -m venv .venv
    ```
    *(On some systems, you might need to use `python3` instead of `python`)*

4.  **Activate Virtual Environment:**
    * **macOS / Linux:**
        ```bash
        source .venv/bin/activate
        ```
    * **Windows (Command Prompt):**
        ```bash
        .\.venv\Scripts\activate
        ```
    * **Windows (PowerShell):**
        ```bash
        .\.venv\Scripts\Activate.ps1
        ```
    You should see `(.venv)` at the beginning of your terminal prompt, indicating the environment is active.

5.  **Install Dependencies:**
    Install the required Pillow library:
    ```bash
    pip install Pillow
    ```

## Usage

Run the script from your terminal while the virtual environment is active.

**Basic Syntax:**

```bash
python pixelator.py <input_image_path> <output_image_path> [options]
```

**Arguments:**

- `input_image_path`: Path to the image file you want to pixelate.
- `output_image_path`: Path where the pixelated image will be saved.

**Options:**

- `-p PIXEL_SIZE`, `--pixel_size PIXEL_SIZE`:

    Sets the size of the pixel blocks. For example, `8` means each block in the output corresponds to an 8x8 area in the original image. Larger values result in more noticeable pixelation. (Default: `8`)

-`c COLORS`, `--colors COLORS`:
    
    Sets the maximum number of colors in the final image. This performs color quantization. If omitted, the script attempts to preserve the colors from the downscaled version. (Default: `None`)

- `-h`, `--help`:

    Show the help message and exit.

**Example:**

To pixelate an image named `image3.jpg`, creating blocks equivalent to 50x50 pixels from the original, reducing the color palette to a maximum of 50 colors, and saving it as `pixel_image3.jpg`:

```bash
python pixelator.py image3.jpg pixel_image3.jpg -p 50 -c 50
```

## Deactivating the Virtual Environment

When you are finished using the script, you can deactivate the virtual environment by simply running

```
deactivate
```
