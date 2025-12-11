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

# Коэффициент отступа между водяными знаками (множитель от размера шрифта)
# Чем больше значение, тем больше "воздуха" между текстами
MARGIN_MULTIPLIER = 1.5


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
    - Динамический расчёт расстояния на основе реальных размеров повёрнутого текста
    
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
    
    # ============================================================
    # Шаг 1: Измеряем точные размеры текста
    # ============================================================
    temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    text_bbox = temp_draw.textbbox(
        (0, 0), watermark_text, font=font, 
        stroke_width=stroke_width
    )
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # ============================================================
    # Шаг 2: Создаём изображение строго по размеру текста
    # ============================================================
    # Добавляем небольшой padding для обводки
    padding = stroke_width + 2
    single_watermark = Image.new(
        'RGBA', 
        (text_width + padding * 2, text_height + padding * 2), 
        (255, 255, 255, 0)
    )
    
    # Рисуем текст с обводкой
    draw_single = ImageDraw.Draw(single_watermark)
    draw_single.text(
        (padding, padding), 
        watermark_text, 
        font=font, 
        fill=WATERMARK_FILL_COLOR,
        stroke_width=stroke_width,
        stroke_fill=WATERMARK_STROKE_COLOR
    )
    
    # ============================================================
    # Шаг 3: Поворачиваем с expand=True для получения точного bounding box
    # ============================================================
    rotated_watermark = single_watermark.rotate(
        WATERMARK_ROTATION, 
        expand=True,  # Важно! Расширяем холст под повёрнутый текст
        resample=Image.BICUBIC
    )
    
    # Получаем реальные размеры повёрнутого изображения
    rotated_width, rotated_height = rotated_watermark.size
    
    # ============================================================
    # Шаг 4: Динамический расчёт spacing на основе размеров
    # ============================================================
    # Отступ (margin) зависит от размера шрифта
    margin = int(font_size * MARGIN_MULTIPLIER)
    
    # Шаг сетки = размер повёрнутого текста + отступ
    spacing_x = rotated_width + margin
    spacing_y = rotated_height + margin
    
    # ============================================================
    # Шаг 5: Размещаем водяные знаки по сетке
    # ============================================================
    # Создаём прозрачный слой для водяных знаков
    watermark_layer = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    
    # Начинаем за пределами изображения для равномерного покрытия
    start_x = -rotated_width
    start_y = -rotated_height
    
    y = start_y
    row = 0
    while y < height + rotated_height:
        # Смещение для шахматного порядка
        offset = (row % 2) * (spacing_x // 2)
        x = start_x + offset
        
        while x < width + rotated_width:
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
