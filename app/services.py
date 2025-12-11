"""
Модуль сервисов для обработки изображений.
Содержит бизнес-логику добавления водяного знака на изображения.
"""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import math


# ============================================================
# Настройки водяного знака
# ============================================================

# Текст водяного знака по умолчанию
DEFAULT_WATERMARK_TEXT = "Sample"

# Порог размера изображения для переключения режима шрифта
# Если ОБА измерения > 1000, используем фиксированный размер
SIZE_THRESHOLD = 1000

# Фиксированный размер шрифта для больших изображений (>1000x1000)
FIXED_FONT_SIZE = 72

# Коэффициент для относительного размера шрифта (для маленьких изображений)
# Размер = min(width, height) / RELATIVE_FONT_DIVISOR
RELATIVE_FONT_DIVISOR = 8

# Минимальный размер шрифта (чтобы текст не стал нечитаемым)
MIN_FONT_SIZE = 24

# Цвета водяного знака
# Основной цвет — белый с прозрачностью
WATERMARK_FILL_COLOR = (255, 255, 255, 150)  # Белый, 60% непрозрачности
# Цвет обводки — чёрный с прозрачностью
WATERMARK_STROKE_COLOR = (0, 0, 0, 120)  # Чёрный, 47% непрозрачности
# Толщина обводки в пикселях (жирная обводка для лучшей видимости)
STROKE_WIDTH = 4

# Угол поворота текста водяного знака (в градусах)
WATERMARK_ROTATION = -30

# Базовое расстояние между водяными знаками (будет масштабироваться)
BASE_SPACING_X = 280
BASE_SPACING_Y = 200


def get_font_size(width: int, height: int) -> int:
    """
    Вычисляет размер шрифта в зависимости от размера изображения.
    
    Правила:
    - Если ОБА измерения > 1000: фиксированный размер 72px
    - Иначе: относительный размер, пропорциональный меньшей стороне
    """
    if width > SIZE_THRESHOLD and height > SIZE_THRESHOLD:
        # Большое изображение — фиксированный размер
        return FIXED_FONT_SIZE
    else:
        # Маленькое изображение — относительный размер
        min_dimension = min(width, height)
        relative_size = min_dimension // RELATIVE_FONT_DIVISOR
        return max(relative_size, MIN_FONT_SIZE)


def get_spacing(font_size: int) -> tuple:
    """
    Вычисляет расстояние между водяными знаками на основе размера шрифта.
    Масштабируем базовое расстояние пропорционально размеру шрифта.
    """
    scale = font_size / FIXED_FONT_SIZE
    spacing_x = int(BASE_SPACING_X * scale)
    spacing_y = int(BASE_SPACING_Y * scale)
    return spacing_x, spacing_y


def load_font(font_size: int) -> ImageFont.FreeTypeFont:
    """
    Загружает шрифт указанного размера.
    Пробует разные пути для совместимости с Windows и Linux.
    """
    # Используем обычный шрифт (не Bold) для более гладкого отображения
    font_paths = [
        "arial.ttf",  # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux (более гладкий)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux (жирный, резервный)
    ]
    
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, font_size)
        except (OSError, IOError):
            continue
    
    # Fallback — стандартный шрифт
    return ImageFont.load_default()


def add_watermark(image_bytes: bytes, watermark_text: str = None) -> BytesIO:
    """
    Добавляет повторяющийся полупрозрачный водяной знак на изображение.
    Водяной знак равномерно распределяется по всей площади изображения.
    
    Особенности:
    - Белый текст с чёрной обводкой (виден на любом фоне)
    - Адаптивный размер шрифта для маленьких изображений
    - Фиксированный размер 72px для изображений > 1000x1000
    
    Аргументы:
        image_bytes: Байты исходного изображения
        watermark_text: Текст водяного знака (опционально, по умолчанию "Sample")
        
    Возвращает:
        BytesIO: Буфер с обработанным изображением в формате JPEG
    """
    
    # Используем текст по умолчанию, если не указан
    if watermark_text is None or watermark_text.strip() == "":
        watermark_text = DEFAULT_WATERMARK_TEXT
    
    # Открываем изображение из байтов
    original_image = Image.open(BytesIO(image_bytes))
    
    # Обрабатываем EXIF-ориентацию (важно для фото с телефона)
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
    
    # Конвертируем в RGBA для поддержки прозрачности
    if original_image.mode != 'RGBA':
        original_image = original_image.convert('RGBA')
    
    width, height = original_image.size
    
    # Вычисляем размер шрифта в зависимости от размера изображения
    font_size = get_font_size(width, height)
    
    # Масштабируем толщину обводки для маленьких шрифтов
    stroke_width = max(1, int(STROKE_WIDTH * font_size / FIXED_FONT_SIZE))
    
    # Загружаем шрифт
    font = load_font(font_size)
    
    # Вычисляем расстояние между водяными знаками
    spacing_x, spacing_y = get_spacing(font_size)
    
    # Создаём прозрачный слой для водяных знаков
    watermark_layer = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    
    # Измеряем размер текста
    temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    text_bbox = temp_draw.textbbox(
        (0, 0), watermark_text, font=font, 
        stroke_width=stroke_width
    )
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Создаём изображение для одного водяного знака
    # Увеличиваем размер для поворота и обводки
    padding = stroke_width * 2 + 10
    diagonal = int(math.sqrt(text_width**2 + text_height**2)) + padding * 2
    single_watermark = Image.new('RGBA', (diagonal, diagonal), (255, 255, 255, 0))
    
    # Рисуем текст с обводкой по центру
    draw_single = ImageDraw.Draw(single_watermark)
    text_x = (diagonal - text_width) // 2
    text_y = (diagonal - text_height) // 2
    
    # Рисуем текст с обводкой (stroke)
    # Белый текст с чёрной обводкой — виден на любом фоне!
    draw_single.text(
        (text_x, text_y), 
        watermark_text, 
        font=font, 
        fill=WATERMARK_FILL_COLOR,
        stroke_width=stroke_width,
        stroke_fill=WATERMARK_STROKE_COLOR
    )
    
    # Поворачиваем водяной знак
    rotated_watermark = single_watermark.rotate(
        WATERMARK_ROTATION, 
        expand=False, 
        resample=Image.BICUBIC
    )
    wm_width, wm_height = rotated_watermark.size
    
    # Размещаем водяные знаки в шахматном порядке
    start_x = -wm_width
    start_y = -wm_height
    
    y = start_y
    row = 0
    while y < height + wm_height:
        # Смещение для шахматного порядка
        offset = (row % 2) * (spacing_x // 2)
        x = start_x + offset
        
        while x < width + wm_width:
            watermark_layer.paste(rotated_watermark, (int(x), int(y)), rotated_watermark)
            x += spacing_x
        
        y += spacing_y
        row += 1
    
    # Накладываем слой с водяными знаками
    watermarked_image = Image.alpha_composite(original_image, watermark_layer)
    
    # Конвертируем в RGB для JPEG
    final_image = watermarked_image.convert('RGB')
    
    # Сохраняем результат
    output_buffer = BytesIO()
    final_image.save(output_buffer, format='JPEG', quality=95)
    output_buffer.seek(0)
    
    return output_buffer
