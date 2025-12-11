"""
Главный модуль FastAPI приложения.
Определяет API-эндпоинты для обработки изображений и проверки здоровья сервиса.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from typing import Optional

# Импортируем функцию обработки из модуля сервисов
from services import add_watermark


# Инициализация FastAPI приложения
app = FastAPI(
    title="Платформа для автообработки фото",
    description="API для добавления водяных знаков на изображения в реальном времени",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности сервиса (health check).
    
    Используется:
    - Docker для проверки здоровья контейнера
    - Load balancer'ами для проверки доступности сервиса
    - Системами мониторинга
    
    Возвращает:
        dict: Статус сервиса
    """
    return {"status": "healthy", "service": "watermark-processor"}


@app.post("/process")
async def process_image(
    file: UploadFile = File(...),
    watermark: Optional[str] = Form(default=None)
):
    """
    Эндпоинт для обработки изображения — добавления водяного знака.
    
    Принимает:
        file: Загружаемый файл изображения (multipart/form-data)
        watermark: Текст водяного знака (опционально, по умолчанию "Sample")
        
    Возвращает:
        StreamingResponse: Обработанное изображение в формате JPEG
        
    Исключения:
        HTTPException 400: Если загружен не файл изображения
        HTTPException 500: При ошибке обработки изображения
    """
    
    # Проверяем, что загружен именно файл изображения
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Загруженный файл не является изображением. Поддерживаются форматы: JPEG, PNG, GIF, BMP"
        )
    
    try:
        # Читаем содержимое загруженного файла в байты
        image_bytes = await file.read()
        
        # Вызываем функцию обработки изображения с опциональным текстом
        processed_image = add_watermark(image_bytes, watermark_text=watermark)
        
        # Возвращаем обработанное изображение через StreamingResponse
        return StreamingResponse(
            processed_image,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"attachment; filename=watermarked_{file.filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке изображения: {str(e)}"
        )


# Точка входа для локального запуска (без Docker)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
