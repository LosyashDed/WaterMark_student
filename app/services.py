from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import math



# Текст водяного знака по умолчанию
DEFAULT_WATERMARK_TEXT = "Sample"

# Минимальный размера изображения для переключения режима шрифта
SIZE_THRESHOLD = 1000

FIXED_FONT_SIZE = 50
RELATIVE_FONT_DIVISOR = 15
MIN_FONT_SIZE = 24

WATERMARK_FILL_COLOR = (255, 255, 255, 150)  
WATERMARK_STROKE_COLOR = (0, 0, 0, 220)  
STROKE_WIDTH = 6
WATERMARK_ROTATION = -30

OVERLAP_FACTOR = 0.8


def get_font_size(width: int, height: int) -> int:
    # Вычисляет размер шрифта в зависимости от размера изображения.
    if width > SIZE_THRESHOLD and height > SIZE_THRESHOLD:
        return FIXED_FONT_SIZE
    else:
        min_dimension = min(width, height)
        relative_size = min_dimension // RELATIVE_FONT_DIVISOR
        return max(relative_size, MIN_FONT_SIZE)


def load_font(font_size: int) -> ImageFont.FreeTypeFont:
    # Загружает шрифт указанного размера.
    font_paths = [
        "arial.ttf",  
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, font_size)
        except (OSError, IOError):
            continue
    
    return ImageFont.load_default()


def add_watermark(image_bytes: bytes, watermark_text: str = None) -> BytesIO:
    # Добавление водяного знака
    
    if watermark_text is None or watermark_text.strip() == "":
        watermark_text = DEFAULT_WATERMARK_TEXT
    
    original_image = Image.open(BytesIO(image_bytes))
    
    try:
        from PIL import ExifTags
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = original_image._getexif()
        if exif is not None:
            orientation_value = exif.get(orientation)
            if orientation_value == 3:
                original_image = original_image.rotate(180, expand=True)
            elif orientation_value == 6:
                original_image = original_image.rotate(270, expand=True)
            elif orientation_value == 8:
                original_image = original_image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError, TypeError):
        pass
    
    if original_image.mode != 'RGBA':
        original_image = original_image.convert('RGBA')
    
    width, height = original_image.size
    
    font_size = get_font_size(width, height)
    
    stroke_width = max(1, int(STROKE_WIDTH * font_size / FIXED_FONT_SIZE))
    
    font = load_font(font_size)
    
    temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    text_bbox = temp_draw.textbbox(
        (0, 0), watermark_text, font=font, 
        stroke_width=stroke_width
    )
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    padding = stroke_width + 2
    single_watermark = Image.new(
        'RGBA', 
        (text_width + padding * 2, text_height + padding * 2), 
        (255, 255, 255, 0)
    )
    
    draw_single = ImageDraw.Draw(single_watermark)
    draw_single.text(
        (padding, padding), 
        watermark_text, 
        font=font, 
        fill=WATERMARK_FILL_COLOR,
        stroke_width=stroke_width,
        stroke_fill=WATERMARK_STROKE_COLOR
    )
    
    rotated_watermark = single_watermark.rotate(
        WATERMARK_ROTATION, 
        expand=True,  
        resample=Image.BICUBIC
    )
    
    rotated_width, rotated_height = rotated_watermark.size
    
    spacing_x = int(rotated_width * OVERLAP_FACTOR)
    spacing_y = int(rotated_height * OVERLAP_FACTOR)
    
    watermark_layer = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    
    start_x = -rotated_width
    start_y = -rotated_height
    
    y = start_y
    row = 0
    while y < height + rotated_height:
        offset = (row % 2) * (spacing_x // 2)
        x = start_x + offset
        
        while x < width + rotated_width:
            watermark_layer.paste(rotated_watermark, (int(x), int(y)), rotated_watermark)
            x += spacing_x
        
        y += spacing_y
        row += 1
    
    watermarked_image = Image.alpha_composite(original_image, watermark_layer)
    
    final_image = watermarked_image.convert('RGB')
    
    output_buffer = BytesIO()
    final_image.save(output_buffer, format='JPEG', quality=95)
    output_buffer.seek(0)
    
    return output_buffer
