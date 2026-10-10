# Права третьих лиц · Third-party notices · Hinweise zu Rechten Dritter

Этот проект **не содержит и не распространяет** веса моделей, чужие датасеты, видео или пароли и ключи; публикуются только
результаты измерений, настройки запуска и собственный код. Чужие программы запускаются из официальных образов и исходников
на условиях их собственных лицензий.
This project does **not** contain or redistribute model weights, third-party datasets, videos, passwords or keys; only measurement
results, launch settings and original code are published. Third-party software is used under its own licenses.

## Программы, которые использует сервер / Software used (check the current licenses at the source)

| Компонент | Назначение | Где смотреть лицензию |
|---|---|---|
| llama.cpp | запуск моделей | https://github.com/ggml-org/llama.cpp (MIT) |
| llama-swap | шлюз профилей моделей | https://github.com/mostlygeek/llama-swap (MIT) |
| whisper.cpp, stable-diffusion.cpp | речь, изображения | репозитории проектов на GitHub (MIT) |
| Gitea | хранение версий отчётов | https://github.com/go-gitea/gitea (MIT) |
| Open WebUI | чат-интерфейс (отдельная установка) | https://github.com/open-webui/open-webui — условия включают требования к сохранению брендинга |
| ComfyUI, Wan 2.1 | генерация видео | https://github.com/comfyanonymous/ComfyUI (GPL-3.0), https://github.com/Wan-Video/Wan2.1 |
| Python, nginx, Alpine, Docker | окружение | официальные образы и их лицензии |

## Модели / Models

Каждая модель (Qwen, Llama, Gemma, MiMo, MiniCPM, Ornith, Spark, Bonsai и другие) принадлежит своему автору и распространяется на
условиях своей лицензии (часть лицензий ограничивает коммерческое использование, масштаб или требует указания «Built with …»).
Перед использованием или распространением модели проверьте лицензию на её странице (model card). Имена моделей в таблицах
используются только для идентификации; сами файлы не распространяются.
Each model belongs to its author and is governed by its own license; some limit commercial use or require attribution. Check
the model card before use or redistribution. Model names are used for identification only.

## Данные и тесты / Data and tests

Задачи тестов созданы автором проекта или сгенерированы программно; не добавляйте в тесты и результаты материалы, на которые у вас
нет прав (чужие учебники, закрытые датасеты, персональные данные). Видео и изображения, созданные моделями, могут иметь
ограничения лицензии соответствующей модели.
Do not add third-party material you have no rights to. Generated media may carry restrictions from the model's license.

## Персональные данные и безопасность / Privacy and security

В копии и репозитории версий нет персональных данных, паролей и токенов (сборка копии проверяет это автоматически, папка `secrets/`
исключена). Панель доступна из локальной сети без пароля — не открывайте её в интернет.
No personal data, passwords or tokens are stored in the backup or the versions repository. The panel has no password: do not expose it to the internet.

## Товарные знаки и отказ от ответственности

Все названия продуктов и компаний — товарные знаки их владельцев; проект с ними не связан и не одобрен ими.
Все материалы предоставляются «как есть» (см. `LICENSE-RESULTS-CC-BY-NC-4.0.md` и `LICENSE-CODE-POLYFORM-NC.txt`). Это не юридическая консультация.
