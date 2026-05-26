#!/usr/bin/env python3
"""Генерация файлов knowledge_base из единого каталога products.json.

Запуск:
    python scripts/generate_kb_from_catalog.py

Этот скрипт читает webapp/products.json и генерирует txt-файлы
для базы знаний RAG-бота. Запускайте после каждого обновления каталога.
"""

import json
import os
import sys

# Пути
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CATALOG_PATH = os.path.join(PROJECT_DIR, "webapp", "products.json")
KB_DIR = os.path.join(PROJECT_DIR, "data", "knowledge_base")

# Маппинг категорий на файлы и названия
CATEGORY_MAP = {
    "hardware": {
        "file_prefix": "catalog_hardware",
        "title": "Физические товары (устройства)",
    },
    "software": {
        "file_prefix": "catalog_software",
        "title": "Цифровые продукты и ПО",
    },
    "services": {
        "file_prefix": "catalog_services",
        "title": "IT-услуги",
    },
}

# Максимум товаров в одном файле (чтобы чанки не были слишком большими)
MAX_ITEMS_PER_FILE = 15


def load_catalog() -> list[dict]:
    """Загрузить каталог из products.json."""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_kb_file(items: list[dict], category_info: dict, part: int = 0) -> str:
    """Сгенерировать текст файла базы знаний для группы товаров."""
    lines = [
        f"=== КАТАЛОГ NICO MARKET: {category_info['title']} ===",
        f"(Часть {part + 1})" if part > 0 else "",
        "",
    ]
    
    for item in items:
        lines.append(f"--- {item['title']} ---")
        lines.append(f"Цена: ${item['price']}")
        lines.append(f"Описание: {item['desc']}")
        lines.append(f"Категория: {category_info['title']}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    products = load_catalog()
    print(f"📦 Загружено товаров из каталога: {len(products)}")
    
    # Удаляем старые catalog_* файлы
    for filename in os.listdir(KB_DIR):
        if filename.startswith("catalog_"):
            os.remove(os.path.join(KB_DIR, filename))
            print(f"  🗑️ Удалён старый файл: {filename}")
    
    # Группируем по категориям
    by_category: dict[str, list] = {}
    for product in products:
        cat = product.get("category", "other")
        by_category.setdefault(cat, []).append(product)
    
    generated = 0
    for category, items in by_category.items():
        cat_info = CATEGORY_MAP.get(category, {"file_prefix": f"catalog_{category}", "title": category})
        
        # Разбиваем на части если слишком много товаров
        for part_idx in range(0, len(items), MAX_ITEMS_PER_FILE):
            part_items = items[part_idx:part_idx + MAX_ITEMS_PER_FILE]
            part_num = part_idx // MAX_ITEMS_PER_FILE
            
            suffix = f"_part{part_num + 1}" if len(items) > MAX_ITEMS_PER_FILE else ""
            filename = f"{cat_info['file_prefix']}{suffix}.txt"
            filepath = os.path.join(KB_DIR, filename)
            
            content = generate_kb_file(part_items, cat_info, part_num)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"  ✅ {filename} ({len(part_items)} товаров)")
            generated += 1
    
    print(f"\n✅ Сгенерировано {generated} файлов базы знаний")
    print("💡 Не забудьте перезагрузить индекс бота (/reload_kb или рестарт)")


if __name__ == "__main__":
    main()
