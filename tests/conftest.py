"""Общие фикстуры для тестов."""
import sys
import os
import pytest

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
