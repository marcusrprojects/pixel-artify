import argparse
import os
import random # Added for distress effect
from PIL import Image, ImageOps

def apply_distress_edges(img, intensity_percent):
    """
    Applies a 'chipped edge' effect by making some border pixels transparent.

    Args:
        img (PIL.Image.Image): The image to modify (should be RGBA).
        intensity_percent (int): Percentage chance (0-100) for a border pixel to be chipped.

    Returns:
        PIL.Image.Image: The image with distressed edges.
    """
    if not (0 < intensity_percent <= 100):
        print("Warning: Distress intensity out of range (1-100). Skipping distress.")
        return img

    if img.mode != 'RGBA':
        print("Warning: Cannot apply distress to non-RGBA image. Skipping.")
        return img

    print(f"Applying distress effect with intensity {intensity_percent}%...")
    pixels = img.load() # Load pixel data for modification
    width, height = img.size
    probability = intensity_percent / 100.0
    # Define how many pixels deep from the edge the effect can apply
    border_depth = 2 # Apply effect up to 2 pixels from any edge

    for y in range(height):
        for x in range(width):
            # Check if the pixel is within the border_depth
            is_border_pixel = (
                x < border_depth or
                x >= width - border_depth or
                y < border_depth or
                y >= height - border_depth
            )

            if is_border_pixel:
                # Randomly decide whether to chip this pixel
                if random.random() < probability:
                    # Set Alpha to 0 (fully transparent)
                    # Keep original R, G, B values
                    current_pixel = pixels[x, y]
                    pixels[x, y] = (current_pixel[0], current_pixel[1], current_pixel[2], 0)

    print("Distress effect applied.")
    return img


def pixelate_image(input_path, output_path, pixel_size, color_count=None, distress_intensity=0):
    """
    Pixelates an image, preserving transparency and optionally adding distressed edges.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path to save the pixelated output image (PNG recommended for transparency).
        pixel_size (int): The size (in pixels) of the 'blocks' in the final image. Must be > 0.
        color_count (int, optional): Max number of colors. Defaults to None.
        distress_intensity (int): Percentage chance (1-100) to chip border pixels
                                  if the original image was opaque. Defaults to 0 (no distress).
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    if pixel_size <= 0:
        print("Error: Pixel size must be greater than 0.")
        return

    output_ext = os.path.splitext(output_path)[1].lower()
    # Always recommend PNG if distress is applied, as it adds transparency
    if distress_intensity > 0 and output_ext != '.png':
        print("Warning: Distress effect adds transparency. Output format should ideally be PNG.")


    try:
        img = Image.open(input_path)
        original_size = img.size
        original_mode = img.mode

        # Determine if the *original* image had an alpha channel
        original_has_alpha = original_mode in ('RGBA', 'LA') or \
                             (original_mode == 'P' and 'transparency' in img.info)

        # Recommend PNG for output if input has alpha (unless distress is already forcing PNG)
        if original_has_alpha and distress_intensity == 0 and output_ext != '.png':
             print(f"Warning: Input image has transparency, but output format '{output_ext}' may not support it. PNG is recommended.")

        # --- Start Processing ---
        # Convert to RGBA if it has alpha, otherwise RGB for initial processing
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


        # 1. Downscale
        small_width = max(1, original_size[0] // pixel_size)
        small_height = max(1, original_size[1] // pixel_size)
        small_img = img.resize((small_width, small_height), Image.Resampling.LANCZOS)
        print(f"Downscaled to {small_img.size} using LANCZOS.")

        # 2. Optional: Quantize Colors
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

        # 3. Upscale
        print(f"Upscaling to {original_size} using NEAREST...")
        pixelated_img = processed_small_img.resize(original_size, Image.Resampling.NEAREST)

        # --- Final Adjustments ---

        # Ensure correct mode before potential distress effect
        # If original had alpha, it should be RGBA. If not, it should be RGB *unless* distress is applied.
        if original_has_alpha and pixelated_img.mode != 'RGBA':
             pixelated_img = pixelated_img.convert('RGBA')
        elif not original_has_alpha and pixelated_img.mode != 'RGB' and distress_intensity == 0:
             # Only convert back to RGB if no distress is happening
             pixelated_img = pixelated_img.convert('RGB')
        elif not original_has_alpha and distress_intensity > 0 and pixelated_img.mode != 'RGBA':
             # If distress is requested for an originally opaque image, convert to RGBA now
             print("Converting final image to RGBA for distress effect.")
             pixelated_img = pixelated_img.convert('RGBA')


        # 4. Optional: Apply Distress Edges
        final_img = pixelated_img # Assume no distress initially
        if distress_intensity > 0 and not original_has_alpha:
            # Only apply if requested AND original image was opaque
            final_img = apply_distress_edges(pixelated_img, distress_intensity)
        elif distress_intensity > 0 and original_has_alpha:
            print("Skipping distress effect: Original image already had transparency.")


        # 5. Save the result
        final_img.save(output_path)
        print(f"Pixelated image saved to {output_path} (Mode: {final_img.mode})")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(
        description="Turn an image into pixel art, preserving transparency and optionally adding distressed edges.",
        formatter_class=argparse.RawTextHelpFormatter
        )
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", help="Path to save the pixelated output image (PNG recommended for transparency/distress).")
    parser.add_argument("-p", "--pixel_size", type=int, default=8,
                        help="Size of the pixel blocks (e.g., 8 means 8x8 original pixels).\nDefault: 8")
    parser.add_argument("-c", "--colors", type=int, default=None,
                        help="Maximum number of colors in the output image (optional).\nQuantization might simplify transparency.\ne.g., 16 or 32.")
    parser.add_argument("-d", "--distress-edges", type=int, default=0, metavar='PERCENT',
                        help="Percentage chance (1-100) to 'chip' edge pixels by making them transparent.\nOnly applies if the original input image does *not* have transparency.\nRequires saving as PNG. Example: 20\nDefault: 0 (no distress)")

    args = parser.parse_args()

    # Validate distress intensity range
    distress_value = 0
    if args.distress_edges:
        if 1 <= args.distress_edges <= 100:
            distress_value = args.distress_edges
        else:
            print("Warning: Distress intensity must be between 1 and 100. Ignoring.")

    pixelate_image(args.input_image, args.output_image, args.pixel_size, args.colors, distress_value)

if __name__ == "__main__":
    main()
