from PIL import Image, ImageDraw

def make_circle(img_path):
    # Open image
    img = Image.open(img_path).convert("RGBA")
    
    # Create mask
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
    
    # Apply mask
    result = img.copy()
    result.putalpha(mask)
    
    # Save back
    result.save(img_path, "WEBP")

make_circle("web/dashboard/public/foxy-bot-pp.webp")
print("Successfully made the image circular.")
