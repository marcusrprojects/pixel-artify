import argparse
import os
import random
from PIL import Image, ImageOps

def apply_distress_edges(img, intensity_percent, pixel_size):
    """
    Applies a 'chipped edge' effect using blocks matching the pixel_size.

    Args:
        img (PIL.Image.Image): The image to modify (should be RGBA).
        intensity_percent (int): Percentage chance (0-100) for a border block to be chipped.
        pixel_size (int): The size of the blocks used for chipping.

    Returns:
        PIL.Image.Image: The image with distressed edges.
    """
    if not (0 < intensity_percent <= 100):
        print("Warning: Distress intensity out of range (1-100). Skipping distress.")
        return img

    if img.mode != 'RGBA':
        print("Warning: Cannot apply distress to non-RGBA image. Skipping.")
        return img

    if pixel_size <= 0:
         print("Warning: Invalid pixel_size for distress. Skipping.")
         return img

    print(f"Applying blocky distress effect (block size {pixel_size}x{pixel_size}) with intensity {intensity_percent}%...")
    pixels = img.load() # Load pixel data for modification
    width, height = img.size
    probability = intensity_percent / 100.0

    # Iterate through the image grid based on pixel_size
    for y_block in range(0, height, pixel_size):
        for x_block in range(0, width, pixel_size):
            # Check if the *block* is on the border
            # A block is on the border if its starting coordinate is 0
            # or if its ending coordinate extends beyond the image boundary
            # (effectively checking the first and last row/column of blocks)
            is_border_block = (
                x_block == 0 or
                y_block == 0 or
                x_block + pixel_size >= width or # Checks last column of blocks
                y_block + pixel_size >= height   # Checks last row of blocks
            )

            if is_border_block:
                # Randomly decide whether to chip this entire block
                if random.random() < probability:
                    # --- Make the entire block transparent ---
                    # Iterate through all pixels within this block
                    for y in range(y_block, min(y_block + pixel_size, height)):
                        for x in range(x_block, min(x_block + pixel_size, width)):
                            # Set Alpha to 0 (fully transparent)
                            # Keep original R, G, B values
                            current_pixel = pixels[x, y]
                            # Ensure we have 4 values (RGBA) before indexing
                            if len(current_pixel) == 4:
                                pixels[x, y] = (current_pixel[0], current_pixel[1], current_pixel[2], 0)
                            else:
                                # Should not happen if input is RGBA, but as a safeguard
                                print(f"Warning: Unexpected pixel format at ({x},{y}): {current_pixel}. Skipping pixel.")


    print("Blocky distress effect applied.")
    return img


def pixelate_image(input_path, output_path, pixel_size, color_count=None, distress_intensity=0):
    """
    Pixelates an image, preserving transparency and optionally adding distressed edges.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path to save the pixelated output image (PNG recommended for transparency).
        pixel_size (int): The size (in pixels) of the 'blocks' in the final image. Must be > 0.
        color_count (int, optional): Max number of colors. Defaults to None.
        distress_intensity (int): Percentage chance (1-100) to chip border blocks
                                  if the original image was opaque. Defaults to 0 (no distress).
    """
    # --- Input validation and setup (mostly unchanged) ---
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    if pixel_size <= 0:
        print("Error: Pixel size must be greater than 0.")
        return

    output_ext = os.path.splitext(output_path)[1].lower()
    if distress_intensity > 0 and output_ext != '.png':
        print("Warning: Distress effect adds transparency. Output format should ideally be PNG.")

    try:
        img = Image.open(input_path)
        original_size = img.size
        original_mode = img.mode

        original_has_alpha = original_mode in ('RGBA', 'LA') or \
                             (original_mode == 'P' and 'transparency' in img.info)

        if original_has_alpha and distress_intensity == 0 and output_ext != '.png':
             print(f"Warning: Input image has transparency, but output format '{output_ext}' may not support it. PNG is recommended.")

        # --- Start Processing (mostly unchanged) ---
        if original_has_alpha:
            img = img.convert('RGBA')
            print("Input has transparency, converting to RGBA.")
            current_mode = 'RGBA'
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
                print(f"Converting input mode '{original_mode}' to RGB.")
            else:
                print("Input does not have transparency, using RGB.")
            current_mode = 'RGB'

        # 1. Downscale (unchanged)
        small_width = max(1, original_size[0] // pixel_size)
        small_height = max(1, original_size[1] // pixel_size)
        small_img = img.resize((small_width, small_height), Image.Resampling.LANCZOS)
        print(f"Downscaled to {small_img.size} using LANCZOS.")

        # 2. Optional: Quantize Colors (unchanged)
        processed_small_img = small_img
        if color_count is not None and color_count > 0:
            print(f"Quantizing colors to {color_count}...")
            if current_mode == 'RGBA':
                alpha = small_img.getchannel('A')
                rgb_img = small_img.convert('RGB')
                quantized_rgb = rgb_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb.copy()
                processed_small_img.putalpha(alpha)
                print("Quantized RGB channels and re-applied alpha channel.")
            else: # Mode is RGB
                quantized_rgb = small_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb
                print("Quantized RGB image.")
        else:
            print("Skipping color quantization.")

        # 3. Upscale (unchanged)
        print(f"Upscaling to {original_size} using NEAREST...")
        pixelated_img = processed_small_img.resize(original_size, Image.Resampling.NEAREST)

        # --- Final Adjustments (mostly unchanged) ---
        if original_has_alpha and pixelated_img.mode != 'RGBA':
             pixelated_img = pixelated_img.convert('RGBA')
        elif not original_has_alpha and pixelated_img.mode != 'RGB' and distress_intensity == 0:
             pixelated_img = pixelated_img.convert('RGB')
        elif not original_has_alpha and distress_intensity > 0 and pixelated_img.mode != 'RGBA':
             print("Converting final image to RGBA for distress effect.")
             pixelated_img = pixelated_img.convert('RGBA')

        # 4. Optional: Apply Distress Edges
        final_img = pixelated_img
        if distress_intensity > 0 and not original_has_alpha:
            # *** MODIFIED CALL: Pass pixel_size to the distress function ***
            final_img = apply_distress_edges(pixelated_img, distress_intensity, pixel_size)
        elif distress_intensity > 0 and original_has_alpha:
            print("Skipping distress effect: Original image already had transparency.")

        # 5. Save the result (unchanged)
        final_img.save(output_path)
        print(f"Pixelated image saved to {output_path} (Mode: {final_img.mode})")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

def main():
    # --- Argument parsing (unchanged) ---
    parser = argparse.ArgumentParser(
        description="Turn an image into pixel art, preserving transparency and optionally adding distressed edges.",
        formatter_class=argparse.RawTextHelpFormatter
        )
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", help="Path to save the pixelated output image (PNG recommended for transparency/distress).")
    parser.add_argument("-p", "--pixel_size", type=int, default=8,
                        help="Size of the pixel blocks (e.g., 8 means 8x8 original pixels).\nAlso used for blocky distress effect size.\nDefault: 8")
    parser.add_argument("-c", "--colors", type=int, default=None,
                        help="Maximum number of colors in the output image (optional).\nQuantization might simplify transparency.\ne.g., 16 or 32.")
    parser.add_argument("-d", "--distress-edges", type=int, default=0, metavar='PERCENT',
                        help="Percentage chance (1-100) to 'chip' edge blocks (size matching --pixel_size).\nOnly applies if the original input image does *not* have transparency.\nRequires saving as PNG. Example: 20\nDefault: 0 (no distress)")

    args = parser.parse_args()

    # --- Argument validation (unchanged) ---
    distress_value = 0
    if args.distress_edges:
        if 1 <= args.distress_edges <= 100:
            distress_value = args.distress_edges
        else:
            print("Warning: Distress intensity must be between 1 and 100. Ignoring.")

    # --- Function call (unchanged) ---
    pixelate_image(args.input_image, args.output_image, args.pixel_size, args.colors, distress_value)

if __name__ == "__main__":
    main()
