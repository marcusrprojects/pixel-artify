import argparse
import os
import random
import math # Needed for ceil
from PIL import Image, ImageOps

# --- Default Directory Names ---
DEFAULT_INPUT_DIR = 'input_images'
DEFAULT_OUTPUT_DIR = 'output_images'

def apply_distress_to_small_image(small_img, intensity_percent, decay_rate):
    """
    Applies a 'chipped edge' effect directly to the small, pre-upscaled image.
    The probability of chipping decreases for pixels/blocks further from the edge.

    Args:
        small_img (PIL.Image.Image): The small, downscaled image (will be converted to RGBA if needed).
        intensity_percent (int): Base percentage chance (0-100) for an edge pixel/block to be chipped.
        decay_rate (float): Factor (0 to 1) by which probability decreases per pixel/block distance
                            from the edge. Lower values mean faster decay.

    Returns:
        PIL.Image.Image: The small image with distressed edges (in RGBA mode).
    """
    if not (0 < intensity_percent <= 100):
        print("Warning: Distress intensity out of range (1-100). Skipping distress.")
        return small_img

    # Ensure the small image is RGBA to modify alpha channel
    if small_img.mode != 'RGBA':
        small_img = small_img.convert('RGBA')
    else:
        small_img = small_img.copy()

    # Decay rate validation is now primarily handled in main, but keep a basic check
    if not (0.0 < decay_rate <= 1.0):
        print(f"Warning: Invalid decay rate ({decay_rate}) received. Using 0.65.")
        decay_rate = 0.65

    pixels = small_img.load()
    grid_width, grid_height = small_img.size
    initial_probability = intensity_percent / 100.0

    for by in range(grid_height):
        for bx in range(grid_width):
            dist_x = min(bx, grid_width - 1 - bx)
            dist_y = min(by, grid_height - 1 - by)
            distance_from_edge = min(dist_x, dist_y)
            adjusted_probability = initial_probability * (decay_rate ** distance_from_edge)

            if random.random() < adjusted_probability:
                current_pixel = pixels[bx, by]
                pixels[bx, by] = (current_pixel[0], current_pixel[1], current_pixel[2], 0)

    # print("Decaying distress effect applied to small image.") # Less verbose
    return small_img


# --- pixelate_image function ---
def pixelate_image(input_path, output_path, pixel_size, color_count=None, distress_intensity=0, decay_rate=0.65):
    """
    Pixelates an image, preserving transparency and optionally adding aligned distressed edges.

    Args:
        input_path (str): Full path to the input image file.
        output_path (str): Full path to save the pixelated output image.
        pixel_size (int): The size (in pixels) of the 'blocks' in the final image. Must be > 0.
        color_count (int, optional): Max number of colors. Defaults to None.
        distress_intensity (int): Base percentage chance (1-100) to chip edge blocks. Defaults to 0.
        decay_rate (float): Decay rate for distress effect (0.0 to 1.0). Defaults to 0.65.
    """
    # --- Input validation and setup ---
    if pixel_size <= 0:
        print("Error: Pixel size must be greater than 0.")
        return

    output_ext = os.path.splitext(output_path)[1].lower()
    if distress_intensity > 0 and output_ext != '.png':
        print("Warning: Distress effect modifies transparency. Output format should ideally be PNG.")

    try:
        print(f"Processing '{os.path.basename(input_path)}'...")
        img = Image.open(input_path)
        original_size = img.size
        original_mode = img.mode
        original_has_alpha = original_mode in ('RGBA', 'LA') or \
                             (original_mode == 'P' and 'transparency' in img.info)

        if original_has_alpha and distress_intensity == 0 and output_ext != '.png':
             print(f"Warning: Input image has transparency, but output format '{output_ext}' may not support it well. PNG is recommended.")

        # --- Start Processing ---
        if original_has_alpha or distress_intensity > 0:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            current_mode = 'RGBA'
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            current_mode = 'RGB'

        # 1. Downscale
        small_width = max(1, original_size[0] // pixel_size)
        small_height = max(1, original_size[1] // pixel_size)
        small_img_base = img.resize((small_width, small_height), Image.Resampling.LANCZOS)

        # 2. Optional: Quantize Colors
        processed_small_img = small_img_base
        if color_count is not None and color_count > 0:
            small_img_mode_before_quant = processed_small_img.mode
            if small_img_mode_before_quant == 'RGBA':
                alpha = processed_small_img.getchannel('A')
                rgb_img = processed_small_img.convert('RGB')
                quantized_rgb = rgb_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb.copy()
                processed_small_img.putalpha(alpha)
            else: # RGB or other
                if processed_small_img.mode != 'RGB':
                    processed_small_img = processed_small_img.convert('RGB')
                quantized_rgb = processed_small_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb
                if distress_intensity > 0:
                    processed_small_img = processed_small_img.convert('RGBA')

        # 3. Optional: Apply Distress Edges *to the small image*
        final_small_img = processed_small_img
        if distress_intensity > 0:
            final_small_img = apply_distress_to_small_image(processed_small_img, distress_intensity, decay_rate)
            current_mode = 'RGBA'

        # 4. Upscale
        pixelated_img = final_small_img.resize(original_size, Image.Resampling.NEAREST)

        # 5. Final Mode Check
        if current_mode == 'RGBA' and pixelated_img.mode != 'RGBA':
             pixelated_img = pixelated_img.convert('RGBA')
        elif current_mode == 'RGB' and pixelated_img.mode != 'RGB':
             pixelated_img = pixelated_img.convert('RGB')

        # 6. Save
        pixelated_img.save(output_path)
        print(f"-> Saved pixelated image to '{output_path}' (Mode: {pixelated_img.mode})")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred while processing {os.path.basename(input_path)}: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(
        description="Turn an image into pixel art. Handles default folders and auto-suffixes filenames to avoid overwrites.",
        formatter_class=argparse.RawTextHelpFormatter
        )

    # --- Input/Output Arguments ---
    parser.add_argument("input_image",
                        help="Path to the input image file.\n"
                             "Can be a full path or just a filename relative to --input-dir.")
    parser.add_argument("-o", "--output",
                        help="Full path for the output image file.\n"
                             "If omitted, automatically generates '<output_dir>/pixel_<input_name>(_N).png',\n"
                             "adding '_N' if needed to avoid overwriting existing files.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR,
                        help=f"Directory to look for input images if 'input_image' is just a filename.\n"
                             f"Default: '{DEFAULT_INPUT_DIR}'")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Directory to save output images if --output is not specified.\n"
                             f"Default: '{DEFAULT_OUTPUT_DIR}'")

    # --- Pixelation Arguments ---
    parser.add_argument("-p", "--pixel_size", type=int, default=8,
                        help="Size of the pixel art blocks (e.g., 8 means 8x8 original pixels).\nDefault: 8")
    parser.add_argument("-c", "--colors", type=int, default=None,
                        help="Maximum number of colors in the output image (optional).\nQuantization might simplify transparency.\ne.g., 16 or 32.")
    parser.add_argument("-d", "--distress-edges", type=int, default=0, metavar='PERCENT',
                        help="Base percentage chance (1-100) to 'chip' edge blocks before upscaling.\nProbability decays inwards.\nApplies to both opaque and transparent images.\nRequires PNG output. Example: 20\nDefault: 0 (no distress)")
    parser.add_argument("--decay-rate", type=float, default=0.65, metavar='RATE',
                        help="Decay rate for distress effect probability (0.0 to 1.0).\nLower values decay faster (more edge-focused).\nHigher values penetrate deeper.\nDefault: 0.65")

    args = parser.parse_args()

    # --- Determine Full Input Path ---
    input_arg = args.input_image
    if os.path.dirname(input_arg):
        full_input_path = input_arg
    else:
        full_input_path = os.path.join(args.input_dir, input_arg)

    # --- Validate Input Path ---
    if not os.path.isfile(full_input_path):
        print(f"Error: Input image not found at calculated path: {full_input_path}")
        return

    # --- Determine Full Output Path ---
    if args.output:
        full_output_path = args.output
    else:
        input_basename = os.path.basename(full_input_path)
        input_name_part, _ = os.path.splitext(input_basename)
        base_output_filename = f"pixel_{input_name_part}.png"
        potential_output_path = os.path.join(args.output_dir, base_output_filename)
        counter = 1
        while os.path.exists(potential_output_path):
            output_filename_suffix = f"pixel_{input_name_part}_{counter}.png"
            potential_output_path = os.path.join(args.output_dir, output_filename_suffix)
            counter += 1
        full_output_path = potential_output_path
        if counter > 1:
             print(f"Default output path existed, using auto-suffixed name: {full_output_path}")


    # --- Ensure Output Directory Exists ---
    output_dir_actual = os.path.dirname(full_output_path)
    if output_dir_actual:
        try:
            os.makedirs(output_dir_actual, exist_ok=True)
        except OSError as e:
            print(f"Error: Could not create output directory '{output_dir_actual}': {e}")
            return

    # --- Validate Distress Intensity---
    distress_value = 0
    if args.distress_edges:
        if 1 <= args.distress_edges <= 100:
            distress_value = args.distress_edges
        else:
            print("Warning: Distress intensity must be between 1 and 100. Ignoring.")

    decay_rate_value = args.decay_rate
    if not (0.0 < decay_rate_value <= 1.0):
        print(f"Warning: Decay rate ({decay_rate_value}) must be between 0.0 (exclusive) and 1.0 (inclusive). Using default 0.65.")
        decay_rate_value = 0.65

    # --- Call the Image Processing Function ---
    pixelate_image(
        input_path=full_input_path,
        output_path=full_output_path,
        pixel_size=args.pixel_size,
        color_count=args.colors,
        distress_intensity=distress_value,
        decay_rate=decay_rate_value
    )

if __name__ == "__main__":
    main()
