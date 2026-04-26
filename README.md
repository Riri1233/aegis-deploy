# Aegis Comply — fullstack RegTech product

Fullstack-прототип RegTech-платформы для санкционного комплаенса, экспортного контроля и проверки ВЭД-сделок.

## Структура проекта

- frontend — пользовательский интерфейс
- backend — FastAPI backend (risk engine + API)
- backend/data — справочники и тестовые данные

---

## Быстрый запуск (локально)

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate

pip install -r requirements.txt

# создать файл .env
DADATA_API_KEY=your_api_key

python run.py