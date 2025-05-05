import argparse
import os
from PIL import Image, ImageOps

def pixelate_image(input_path, output_path, pixel_size, color_count=None):
    """
    Pixelates an image by downscaling, optionally reducing colors,
    and upscaling with nearest neighbor interpolation.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path to save the pixelated output image.
        pixel_size (int): The size (in pixels) of the 'blocks' in the final image.
                          Larger values mean more pixelation. Must be > 0.
        color_count (int, optional): The maximum number of colors in the final image.
                                     If None, original colors are kept (after downscaling).
                                     Defaults to None.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    if pixel_size <= 0:
        print("Error: Pixel size must be greater than 0.")
        return

    try:
        img = Image.open(input_path)
        original_size = img.size

        # Convert to RGB if it's RGBA or P (palette) to handle transparency consistently
        # and prepare for potential quantization
        if img.mode == 'RGBA' or img.mode == 'P':
             # If RGBA, create a white background and paste the image onto it
             # This avoids issues with transparent pixels becoming black during quantization
             img = img.convert('RGBA')
             background = Image.new('RGB', img.size, (255, 255, 255))
             background.paste(img, mask=img.split()[3]) # Paste using alpha channel as mask
             img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')


        # 1. Downscale
        # Calculate the size of the small intermediate image
        small_width = max(1, original_size[0] // pixel_size)
        small_height = max(1, original_size[1] // pixel_size)

        # Resize down using a good quality filter like LANCZOS or BILINEAR
        # This averages the colors within each 'block' before pixelation
        small_img = img.resize((small_width, small_height), Image.Resampling.LANCZOS)

        # 2. Optional: Reduce Colors (Quantization)
        if color_count is not None and color_count > 0:
            # Quantize to reduce the number of colors.
            # Use MEDIANCUT or FASTOCTREE for potentially better results than default.
            # Note: Quantize returns a 'P' (palette) mode image.
            small_img = small_img.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT)
            # Convert back to RGB for consistent upscaling
            small_img = small_img.convert('RGB')


        # 3. Upscale
        # Resize back up to the original size using NEAREST neighbor interpolation
        # This creates the blocky pixel effect without smoothing
        pixelated_img = small_img.resize(original_size, Image.Resampling.NEAREST)

        # 4. Save the result
        pixelated_img.save(output_path)
        print(f"Pixelated image saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description="Turn an image into pixel art.")
    parser.add_argument("input_image", help="Path to the input image file.")
    parser.add_argument("output_image", help="Path to save the pixelated output image.")
    parser.add_argument("-p", "--pixel_size", type=int, default=8,
                        help="Size of the pixel blocks (e.g., 8 means each block is 8x8 original pixels). Default: 8")
    parser.add_argument("-c", "--colors", type=int, default=None,
                        help="Maximum number of colors in the output image (optional). e.g., 16 or 32.")

    args = parser.parse_args()

    pixelate_image(args.input_image, args.output_image, args.pixel_size, args.colors)

if __name__ == "__main__":
    main()