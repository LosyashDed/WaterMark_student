# Платформа для автообработки фото в реальном времени

Курсовой проект по дисциплине «Настройка и администрирование сервисного ПО»

## Структура проекта

```
project/
├── app/                     # Основная папка
│   ├── main.py              # FastAPI 
│   ├── services.py          # Логика обработки изображений
│   ├── Dockerfile           # Docker Python-сервиса
│   └── requirements.txt     # Зависимости Python
├── nginx/                   # Nginx
│   └── nginx.conf           # Nginx
├── docker-compose.yml       # Docker
└── README.md                # Документация
```

## Стек технологий

- **Backend:** Python 3.9+ с FastAPI
- **Обработка изображений:** Pillow (PIL)
- **Web-сервер:** Nginx (Reverse Proxy)
- **Контейнеризация:** Docker + Docker Compose

## Запуск проекта

### 1. Клонирование или переход в директорию проекта

```bash
cd path/to/project
```

### 2. Сборка и запуск контейнеров

```bash
docker-compose up --build
```

### 3. Проверка работоспособности

```bash
# Health check
curl http://localhost/health

# Ожидаемый ответ:
# {"status":"healthy","service":"watermark-processor"}
```

### 4. Тестирование обработки изображения

```bash
# Отправка изображения на обработку
curl -X POST -F "file=@/path/to/image.jpg" http://localhost/process --output result.jpg
```

## API 
| Метод | Путь      | Описание                           |
|-------|-----------|-------------------------------------|
| GET   | /health   | Проверка работоспособности сервиса |
| POST  | /process  | Добавление водяного знака          |

## Документация API

После запуска проекта доступна автоматическая документация:

- http://localhost/docs
- http://localhost/redoc

## Ограничения

- Максимальный размер загружаемого файла: **10 МБ** (настраивается в `nginx.conf`)
- Поддерживаемые форматы: JPEG, PNG, GIF, BMP
- Выходной формат: JPEG
