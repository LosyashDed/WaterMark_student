import requests
import os
from pathlib import Path
import time
import sys


API_URL = "http://localhost"
TEST_DIR = Path("test")
OUTPUT_DIR = Path("test/results")


def test_health():
    # Проверка API
    url = f"{API_URL}/health"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ Health check: OK")
            return True
        else:
            print(f"❌ Health check: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Health check: Сервер недоступен")
        return False


def process_image(image_path: Path, watermark: str = None) -> bool:
    # Отправляет изображение на обработку
    url = f"{API_URL}/process"
    
    try:
        with open(image_path, "rb") as f:
            files = {"file": (image_path.name, f, "image/jpeg")}
            data = {}
            if watermark:
                data["watermark"] = watermark
            
            start_time = time.time()
            response = requests.post(url, files=files, data=data, timeout=30)
            elapsed = time.time() - start_time
        
        if response.status_code == 200:
            OUTPUT_DIR.mkdir(exist_ok=True)
            
            suffix = f"_{watermark}" if watermark else ""
            output_name = f"{image_path.stem}{suffix}_watermarked.jpg"
            output_path = OUTPUT_DIR / output_name
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            try:
                from PIL import Image
                img = Image.open(output_path)
                print(f"  ✅ {image_path.name} → {output_name}")
                print(f"     Размер: {img.size}, Время: {elapsed:.2f}с")
                return True
            except Exception as e:
                print(f"  ❌ {image_path.name}: Ошибка открытия результата - {e}")
                return False
        else:
            print(f"  ❌ {image_path.name}: HTTP {response.status_code}")
            print(f"     {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"  ❌ {image_path.name}: {e}")
        return False


def run_tests():
    print("=" * 60)
    print("🧪 АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ API ВОДЯНЫХ ЗНАКОВ")
    print("=" * 60)
    
    print("\n📡 Проверка API...")
    if not test_health():
        print("\n⚠️  Сервер недоступен. Запустите docker-compose up -d")
        sys.exit(1)
    
    print(f"\n📁 Поиск изображений в {TEST_DIR}/...")
    
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
    test_images = [
        f for f in TEST_DIR.iterdir() 
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    
    if not test_images:
        print("⚠️  Тестовые изображения не найдены")
        return
    
    print(f"   Найдено изображений: {len(test_images)}")
    
    print("\n" + "-" * 60)
    print("🔹 Тест 1: Водяной знак по умолчанию (Sample)")
    print("-" * 60)
    
    success_count = 0
    for img_path in test_images:
        if process_image(img_path):
            success_count += 1
    
    print("\n" + "-" * 60)
    print("🔹 Тест 2: Кастомный водяной знак (CONFIDENTIAL)")
    print("-" * 60)
    
    for img_path in test_images:
        if process_image(img_path, watermark="CONFIDENTIAL"):
            success_count += 1
    
    total_tests = len(test_images) * 2
    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ: {success_count}/{total_tests} тестов пройдено")
    print(f"📂 Результаты сохранены в: {OUTPUT_DIR.absolute()}")
    print("=" * 60)

    if success_count < total_tests:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
