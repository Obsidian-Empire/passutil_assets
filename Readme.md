# Репозиторий с ассетами для passutil приложений

# Каталоги
- builder
  - Программа для минификации
- contents
  - assets (ассеты)
  - localization (файлы локализации)

# Как пользоваться сборщиком
- нужно установить [**uv**](https://docs.astral.sh/uv/getting-started/installation/)
- синхронизировать
```sh
cd builder
uv sync --all-extras --dev
```
- запустить
```sh
cd builder
uv run converter.py dir_from dir_to
```
