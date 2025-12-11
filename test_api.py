"""
Автоматический скрипт тестирования API обработки изображений.
Обрабатывает все изображения из папки test/ и сохраняет результаты.
"""
import requests
import os
from pathlib import Path
import time


# Конфигурация
API_URL = "http://localhost"
TEST_DIR = Path("test")
OUTPUT_DIR = Path("test/results")


def test_health():
    """Проверка работоспособности API."""
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
    """
    Отправляет изображение на обработку и сохраняет результат.
    
    Аргументы:
        image_path: Путь к исходному изображению
        watermark: Текст водяного знака (опционально)
        
    Возвращает:
        bool: True если обработка успешна
    """
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
            # Создаём папку для результатов
            OUTPUT_DIR.mkdir(exist_ok=True)
            
            # Формируем имя выходного файла
            suffix = f"_{watermark}" if watermark else ""
            output_name = f"{image_path.stem}{suffix}_watermarked.jpg"
            output_path = OUTPUT_DIR / output_name
            
            # Сохраняем результат
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            # Проверяем, что изображение валидно
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
    """Запускает полный цикл тестирования."""
    print("=" * 60)
    print("🧪 АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ API ВОДЯНЫХ ЗНАКОВ")
    print("=" * 60)
    
    # Проверка здоровья сервиса
    print("\n📡 Проверка API...")
    if not test_health():
        print("\n⚠️  Сервер недоступен. Запустите docker-compose up -d")
        return
    
    # Поиск тестовых изображений
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
    
    # Тестирование с водяным знаком по умолчанию
    print("\n" + "-" * 60)
    print("🔹 Тест 1: Водяной знак по умолчанию (Sample)")
    print("-" * 60)
    
    success_count = 0
    for img_path in test_images:
        if process_image(img_path):
            success_count += 1
    
    # Тестирование с кастомным водяным знаком
    print("\n" + "-" * 60)
    print("🔹 Тест 2: Кастомный водяной знак (CONFIDENTIAL)")
    print("-" * 60)
    
    for img_path in test_images:
        if process_image(img_path, watermark="CONFIDENTIAL"):
            success_count += 1
    
    # Итоги
    total_tests = len(test_images) * 2
    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ: {success_count}/{total_tests} тестов пройдено")
    print(f"📂 Результаты сохранены в: {OUTPUT_DIR.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
