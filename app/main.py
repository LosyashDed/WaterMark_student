from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from typing import Optional

from services import add_watermark


app = FastAPI(
    title="Платформа для автообработки фото",
    description="API для добавления водяных знаков на изображения в реальном времени",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "watermark-processor"}


@app.post("/process")
async def process_image(
    file: UploadFile = File(...),
    watermark: Optional[str] = Form(default=None)
):
    
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Загруженный файл не является изображением. Поддерживаются форматы: JPEG, PNG, GIF, BMP"
        )
    
    try:
        image_bytes = await file.read()
        
        processed_image = add_watermark(image_bytes, watermark_text=watermark)
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
