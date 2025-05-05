import argparse
import os
import random
import math # Needed for ceil
from PIL import Image, ImageOps

def apply_distress_to_small_image(small_img, intensity_percent, decay_rate=0.65):
    """
    Applies a 'chipped edge' effect directly to the small, pre-upscaled image.
    Each pixel in the small image represents a block.
    The probability of chipping decreases for pixels/blocks further from the edge.

    Args:
        small_img (PIL.Image.Image): The small, downscaled image (will be converted to RGBA if needed).
        intensity_percent (int): Base percentage chance (0-100) for an edge pixel/block to be chipped.
        decay_rate (float): Factor (0 to 1) by which probability decreases per pixel/block distance
                            from the edge. Lower values mean faster decay. Defaults to 0.65.

    Returns:
        PIL.Image.Image: The small image with distressed edges (in RGBA mode).
    """
    if not (0 < intensity_percent <= 100):
        print("Warning: Distress intensity out of range (1-100). Skipping distress.")
        return small_img

    # Ensure the small image is RGBA to modify alpha channel
    if small_img.mode != 'RGBA':
        print("Converting small image to RGBA for distress effect.")
        small_img = small_img.convert('RGBA')
    else:
        # Make a copy to avoid modifying the original if it was already RGBA
        small_img = small_img.copy()


    if not (0 < decay_rate <= 1.0):
        print("Warning: Decay rate must be between 0 and 1. Using default 0.65.")
        decay_rate = 0.65

    print(f"Applying decaying blocky distress effect (intensity {intensity_percent}%, decay {decay_rate}) to small image...")
    pixels = small_img.load() # Load pixel data for modification
    grid_width, grid_height = small_img.size # Grid dimensions are the small image dimensions
    initial_probability = intensity_percent / 100.0

    # Iterate through the pixels (blocks) of the small image
    for by in range(grid_height): # Block y-coordinate (pixel y)
        for bx in range(grid_width): # Block x-coordinate (pixel x)
            # Calculate distance 'd' from the nearest edge (in pixels/blocks)
            dist_x = min(bx, grid_width - 1 - bx)
            dist_y = min(by, grid_height - 1 - by)
            distance_from_edge = min(dist_x, dist_y)

            # Calculate the probability for this pixel/block based on distance
            adjusted_probability = initial_probability * (decay_rate ** distance_from_edge)

            # Randomly decide whether to chip this entire pixel/block based on adjusted probability
            if random.random() < adjusted_probability:
                # --- Make this pixel/block transparent ---
                # Get current R, G, B values
                current_pixel = pixels[bx, by]
                # Set Alpha to 0 (fully transparent)
                pixels[bx, by] = (current_pixel[0], current_pixel[1], current_pixel[2], 0)

    print("Decaying distress effect applied to small image.")
    return small_img # Return the modified small image


def pixelate_image(input_path, output_path, pixel_size, color_count=None, distress_intensity=0):
    """
    Pixelates an image, preserving transparency and optionally adding aligned distressed edges.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path to save the pixelated output image (PNG recommended for transparency).
        pixel_size (int): The size (in pixels) of the 'blocks' in the final image. Must be > 0.
        color_count (int, optional): Max number of colors. Defaults to None.
        distress_intensity (int): Base percentage chance (1-100) to chip edge blocks
                                  if the original image was opaque. Probability decays inwards.
                                  Defaults to 0 (no distress).
    """
    # --- Input validation and setup ---
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

        # --- Start Processing ---
        # Convert to RGBA if it has alpha, otherwise RGB for initial processing
        if original_has_alpha:
            img = img.convert('RGBA')
            print("Input has transparency, converting to RGBA.")
            current_mode = 'RGBA' # Keep track if we started with alpha
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
                print(f"Converting input mode '{original_mode}' to RGB.")
            else:
                print("Input does not have transparency, using RGB.")
            current_mode = 'RGB' # Keep track if we started without alpha


        # 1. Downscale
        small_width = max(1, original_size[0] // pixel_size)
        small_height = max(1, original_size[1] // pixel_size)
        # Use LANCZOS for potentially better color averaging during downscale
        small_img_base = img.resize((small_width, small_height), Image.Resampling.LANCZOS)
        print(f"Downscaled to {small_img_base.size} using LANCZOS.")


        # 2. Optional: Quantize Colors (operate on the downscaled image)
        processed_small_img = small_img_base # Start with the base downscaled image
        if color_count is not None and color_count > 0:
            print(f"Quantizing colors to {color_count}...")
            # Temporarily store original mode before potential quantization changes it
            small_img_mode_before_quant = processed_small_img.mode
            if small_img_mode_before_quant == 'RGBA':
                alpha = processed_small_img.getchannel('A')
                rgb_img = processed_small_img.convert('RGB')
                quantized_rgb = rgb_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb.copy()
                processed_small_img.putalpha(alpha)
                print("Quantized RGB channels and re-applied alpha channel.")
            else: # Mode is RGB or other (convert to RGB first)
                if processed_small_img.mode != 'RGB':
                    processed_small_img = processed_small_img.convert('RGB')
                quantized_rgb = processed_small_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb
                print("Quantized image (started as non-RGBA or already RGB).")
        else:
            print("Skipping color quantization.")


        # 3. Optional: Apply Distress Edges *to the small image*
        final_small_img = processed_small_img # Assume no distress initially
        if distress_intensity > 0 and not original_has_alpha:
            # Only apply if requested AND original image was opaque
            final_small_img = apply_distress_to_small_image(processed_small_img, distress_intensity) # Default decay_rate=0.65 used
            # Distress function ensures output is RGBA
            current_mode = 'RGBA' # Update mode tracker as distress adds alpha
        elif distress_intensity > 0 and original_has_alpha:
            print("Skipping distress effect: Original image already had transparency.")


        # 4. Upscale the *final* small image using NEAREST neighbor
        print(f"Upscaling to {original_size} using NEAREST...")
        # Use the potentially distressed small image for upscaling
        pixelated_img = final_small_img.resize(original_size, Image.Resampling.NEAREST)

        # 5. Final Mode Check (Optional but good practice)
        # If distress was applied, it should be RGBA. If original had alpha, it should be RGBA.
        # Otherwise, it should be RGB.
        if current_mode == 'RGBA' and pixelated_img.mode != 'RGBA':
             print("Ensuring final image mode is RGBA.")
             pixelated_img = pixelated_img.convert('RGBA')
        elif current_mode == 'RGB' and pixelated_img.mode != 'RGB':
             # This case should be less common now, only if no distress and no original alpha
             print("Ensuring final image mode is RGB.")
             pixelated_img = pixelated_img.convert('RGB')


        # 6. Save the result
        pixelated_img.save(output_path)
        print(f"Pixelated image saved to {output_path} (Mode: {pixelated_img.mode})")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

def main():
    # --- Argument parsing (Help text updated slightly) ---
    parser = argparse.ArgumentParser(
        description="Turn an image into pixel art, preserving transparency and optionally adding aligned distressed edges with decay.",
        formatter_class=argparse.RawTextHelpFormatter
        )
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", help="Path to save the pixelated output image (PNG recommended for transparency/distress).")
    parser.add_argument("-p", "--pixel_size", type=int, default=8,
                        help="Size of the pixel art blocks (e.g., 8 means 8x8 original pixels).\nDefault: 8")
    parser.add_argument("-c", "--colors", type=int, default=None,
                        help="Maximum number of colors in the output image (optional).\nQuantization might simplify transparency.\ne.g., 16 or 32.")
    parser.add_argument("-d", "--distress-edges", type=int, default=0, metavar='PERCENT',
                        help="Base percentage chance (1-100) to 'chip' edge blocks by removing them before upscaling.\nProbability decays inwards (decay rate ~0.65).\nOnly applies if the original input image does *not* have transparency.\nRequires saving as PNG. Example: 20\nDefault: 0 (no distress)")

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
