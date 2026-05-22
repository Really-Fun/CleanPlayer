# run.py (лежит в корне проекта)
import sys
from pathlib import Path

# Добавляем папку src в системный путь Питона
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Теперь Питон видит папку quantis! Запускаем:
from quantis.main import main

if __name__ == "__main__":
    main()
