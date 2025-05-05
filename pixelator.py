import argparse
import os
from PIL import Image, ImageOps

def pixelate_image(input_path, output_path, pixel_size, color_count=None):
    """
    Pixelates an image, preserving transparency if present.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path to save the pixelated output image (PNG recommended for transparency).
        pixel_size (int): The size (in pixels) of the 'blocks' in the final image.
                          Larger values mean more pixelation. Must be > 0.
        color_count (int, optional): The maximum number of colors in the final image.
                                     If None, original colors are kept (after downscaling).
                                     Transparency might be simplified (binary) if quantization is used.
                                     Defaults to None.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    if pixel_size <= 0:
        print("Error: Pixel size must be greater than 0.")
        return

    # Recommend PNG for output if transparency might be involved
    output_ext = os.path.splitext(output_path)[1].lower()
    if output_ext != '.png' and color_count is not None:
         print("Warning: Output format is not PNG. Transparency might not be saved correctly.")
    elif output_ext != '.png':
         # Check input format later if no quantization
         pass


    try:
        img = Image.open(input_path)
        original_size = img.size
        original_mode = img.mode # Store original mode

        # Determine if the image has an alpha channel
        has_alpha = original_mode in ('RGBA', 'LA') or (original_mode == 'P' and 'transparency' in img.info)

        # Recommend PNG for output if input has alpha
        if has_alpha and output_ext != '.png':
             print(f"Warning: Input image has transparency, but output format '{output_ext}' may not support it. PNG is recommended.")


        # Convert to RGBA if it has alpha, otherwise RGB
        if has_alpha:
            img = img.convert('RGBA')
            print("Input has transparency, converting to RGBA.")
        else:
            # Keep as RGB or convert if necessary (e.g. from P without transparency, or L)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                print(f"Converting input mode '{original_mode}' to RGB.")
            else:
                print("Input does not have transparency, using RGB.")

        current_mode = img.mode # Should be RGBA or RGB

        # 1. Downscale using a high-quality filter
        # Calculate the size of the small intermediate image
        small_width = max(1, original_size[0] // pixel_size)
        small_height = max(1, original_size[1] // pixel_size)

        # Resize down
        small_img = img.resize((small_width, small_height), Image.Resampling.LANCZOS)
        print(f"Downscaled to {small_img.size} using LANCZOS.")

        # 2. Optional: Reduce Colors (Quantization)
        processed_small_img = small_img # Start with the downscaled image

        if color_count is not None and color_count > 0:
            print(f"Quantizing colors to {color_count}...")
            if current_mode == 'RGBA':
                # Separate alpha channel
                alpha = small_img.getchannel('A')

                # Convert to RGB, quantize, and convert back to RGB
                rgb_img = small_img.convert('RGB')
                quantized_rgb = rgb_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')

                # Re-add the alpha channel
                processed_small_img = quantized_rgb.copy() # Make a copy to add alpha
                processed_small_img.putalpha(alpha)
                print("Quantized RGB channels and re-applied alpha channel.")

            else: # Mode is RGB
                quantized_rgb = small_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT).convert('RGB')
                processed_small_img = quantized_rgb
                print("Quantized RGB image.")
        else:
            print("Skipping color quantization.")


        # 3. Upscale using NEAREST neighbor interpolation
        print(f"Upscaling to {original_size} using NEAREST...")
        pixelated_img = processed_small_img.resize(original_size, Image.Resampling.NEAREST)

        # 4. Save the result
        # Ensure the final image mode matches (especially for RGBA)
        if current_mode == 'RGBA' and pixelated_img.mode != 'RGBA':
             pixelated_img = pixelated_img.convert('RGBA')
        elif current_mode == 'RGB' and pixelated_img.mode != 'RGB':
             pixelated_img = pixelated_img.convert('RGB')


        pixelated_img.save(output_path)
        print(f"Pixelated image saved to {output_path} (Mode: {pixelated_img.mode})")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback for debugging

def main():
    parser = argparse.ArgumentParser(
        description="Turn an image into pixel art, preserving transparency.",
        formatter_class=argparse.RawTextHelpFormatter # Keep newline formatting in help
        )
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", help="Path to save the pixelated output image (PNG recommended for transparency).")
    parser.add_argument("-p", "--pixel_size", type=int, default=8,
                        help="Size of the pixel blocks (e.g., 8 means each block is 8x8 original pixels).\nDefault: 8")
    parser.add_argument("-c", "--colors", type=int, default=None,
                        help="Maximum number of colors in the output image (optional).\nQuantization might simplify transparency.\ne.g., 16 or 32.")

    args = parser.parse_args()

    pixelate_image(args.input_image, args.output_image, args.pixel_size, args.colors)

if __name__ == "__main__":
    main()
