"""Build a standalone Russian HTML report and machine-readable settings from live probes."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark"
OUT = BENCH / "context-audit-20260929"
OUT.mkdir(parents=True, exist_ok=True)

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

base = {r["model"]: r for r in rows(BENCH / "context-20260929.jsonl")}
expanded = {r["model"]: r for r in rows(BENCH / "expanded-context-20260929.jsonl")}
models = [
    ("Qwen3.5-9B-MTP-Q4_K_XL", 65536, "Основная работа, код, длинные документы", "MTP n-max=2; F16 KV", "80K обработано, но ответ деградировал; 64K вернул код."),
    ("Qwen3.5-9B-MTP-Q4_K_XL-Vision", 49152, "Анализ изображений", "mmproj F16; MTP off; F16 KV", "Проверка 48K была текстовой; изображения занимают часть окна."),
    ("Qwen3.5-9B-Q5_K_S", 65536, "Альтернатива Qwen без MTP", "F16 KV", "96K обработано, но ответ деградировал; 64K вернул код."),
    ("MiniCPM5-2B-Q8_0", 131072, "Быстрые и простые задачи", "DSpark off; F16 KV", "На 64K и 128K запрос принят, но контрольный код не восстановлен."),
    ("Spark-X2.5-4B-Q8_0", 98304, "Агентные задачи и инструменты", "thinking off; F16 KV", "На 64K и 96K запрос принят, но контрольный код не восстановлен."),
    ("Ternary-Bonsai-2-27B-PTQ1_0", 32768, "Экспериментальная 27B", "PrismML; F16 KV", "48K вернул код, но оставил лишь 422 МиБ VRAM; для работы выбран 32K."),
    ("Qwen3-VL-8B-Instruct-Q4_K_M", 16384, "Анализ изображений", "mmproj F16; F16 KV", "16K вернул код; запас VRAM около 830 МиБ."),
]

settings = {"date": "2026-09-29", "hardware": "NVIDIA RTX 3080 10240 MiB", "gateway_config": str(ROOT / "config" / "llama-swap.yaml"), "model_profiles": {}}
for name, recommended, role, opts, note in models:
    b, e = base[name], expanded[name]
    settings["model_profiles"][name] = {
        "recommended_context_tokens": recommended,
        "largest_tested_context_tokens": e["target_context"],
        "largest_tested_input_tokens": e.get("prompt_tokens"),
        "largest_tested_vram_mib": int(e["gpu_mib"].split(",")[0]) if e.get("gpu_mib") else None,
        "largest_tested_recall_pass": e.get("recall"),
        "baseline_input_tokens": b.get("prompt_tokens"),
        "baseline_recall_pass": b.get("status") == "pass",
        "role": role, "runtime_settings": opts, "qualification": note,
    }
settings["photo_generation"] = {
    "model": "Qwen-Image-2.1 Q5_K_M", "width": 1024, "height": 1024, "steps": 20,
    "seed": 42, "cfg_scale": 6.0, "sampler": "euler", "cpu_offload": True,
    "params_backend": "diffusion=disk", "diffusion_flash_attention": True,
    "vae_tiling": "256x256; overlap 0.5", "entrypoint": str(ROOT / "scripts" / "start-qwen-image.ps1"),
    "requires_gateway_stopped": True,
}
settings["photo_editing"] = {"status": "failed_in_current_runtime", "reference_projector": "mmproj-Qwen3VL-8B-Instruct-F16.gguf", "tested_sizes": [512, 1024], "failure": "diffusion GGUF read tensor data failed during sampling; source GGUF SHA256 still matches manifest"}
settings["video_generation"] = {"status": "not_installed", "note": "No text-to-video or image-to-video model/runtime found; existing ffmpeg pipeline only analyzes video."}
settings["speech_to_text"] = {"model": "Whisper large-v3-turbo Q8_0", "endpoint": "http://127.0.0.1:8082/inference", "on_demand": True}
(ROOT / "config" / "recommended-settings-20260929.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

def esc(value):
    return html.escape(str(value))

trs = []
for name, recommended, role, opts, note in models:
    b, e = base[name], expanded[name]
    recall = "да" if e.get("recall") else "нет"
    vram = e.get("gpu_mib", "").split(",")[0]
    trs.append(f"<tr><td><strong>{esc(name)}</strong><small>{esc(role)}</small></td><td>{recommended:,}</td><td>{e['target_context']:,}</td><td>{e.get('prompt_tokens', '—'):,}</td><td>{esc(vram)}</td><td>{recall}</td><td>{esc(note)}</td></tr>")

telemetry = json.loads((ROOT / "media" / "images" / "context-audit-image-20260929.png.telemetry.json").read_text(encoding="utf-8-sig"))
edit_telemetry = json.loads((ROOT / "media" / "images" / "context-audit-edit-retry-20260929.png.telemetry.json").read_text(encoding="utf-8-sig"))
vision_files = sorted((BENCH / "gateway-acceptance").glob("vision-image-test-*.json"))
vision_note = "Проверка изображений не найдена."
if vision_files:
    vision = json.loads(vision_files[-1].read_text(encoding="utf-8"))
    vision_note = ", ".join(f"{r['model']}: {r['status']}" for r in vision["results"])

page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Аудит локальных ИИ — 29.09.2026</title><style>
:root{{font-family:Inter,Segoe UI,Arial,sans-serif;color:#eaf0ff;background:#0c1220}}body{{margin:0}}header{{background:linear-gradient(115deg,#152647,#173b4e);padding:48px max(24px,calc((100vw - 1180px)/2))}}h1{{font-size:clamp(30px,4vw,48px);margin:0 0 12px}}h2{{margin-top:0}}p{{line-height:1.55}}main{{max-width:1180px;margin:auto;padding:28px 24px 70px}}.lede{{color:#b9cbdf;font-size:18px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:25px 0}}.card,section{{background:#151e30;border:1px solid #2b3d56;border-radius:15px;padding:20px}}.card b{{display:block;font-size:27px;color:#87e9d1}}section{{margin:18px 0}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #33445a}}th{{color:#9ddbd1}}td small{{display:block;color:#9baec7;margin-top:5px}}.scroll{{overflow-x:auto}}code{{background:#263951;padding:2px 5px;border-radius:4px}}a{{color:#90d8ff}}.warn{{border-left:4px solid #ffbd69;padding-left:14px}}img{{max-width:360px;width:100%;border-radius:10px}}footer{{color:#93a9c3;font-size:13px}}</style></head><body>
<header><h1>Аудит локальных ИИ</h1><div class="lede">Docker · RTX 3080 10 GiB · 29 сентября 2026</div></header><main>
<div class="cards"><div class="card"><b>7 / 7</b>чат-профилей обработали большой вход без падения</div><div class="card"><b>131 072</b>самое большое проверенное окно — MiniCPM</div><div class="card"><b>5 / 7</b>профилей восстановили код на исходном длинном запросе</div><div class="card"><b>1024²</b>генерация фото проверена повторно</div></div>
<section><h2>Настройки для работы</h2><p>«Проверенное окно» — размер контекста сервера. «Фактический вход» — число токенов, которое API посчитал в длинном запросе. Контрольное задание требовало вернуть код из начала запроса после длинной последовательности слов. Значения являются наибольшими проверенными в этом прогоне, а не доказанной абсолютной границей оборудования.</p><div class="scroll"><table><thead><tr><th>Модель</th><th>Рабочее окно</th><th>Макс. проверено</th><th>Вход токенов</th><th>VRAM МиБ</th><th>Код извлечён</th><th>Вывод</th></tr></thead><tbody>{''.join(trs)}</tbody></table></div></section>
<section><h2>Как понимать предел</h2><p>Сервер резервирует память под окно при загрузке. Проверка полного входа подтвердила обработку 80–88% окна, но не доказала, что все произвольные документы такой длины будут отвечены правильно. MiniCPM и Spark на искусственном повторяющемся тексте давали неверный ответ при успешной обработке; для задач, где важна точная ссылка на начало документа, рекомендуется Qwen3.5. Видеопамять занята также Windows и другими приложениями; при изменении фоновой нагрузки запас может уменьшиться.</p><p class="warn">Bonsai 48K занял 9 818 МиБ, поэтому рабочий профиль оставлен на 32K. Qwen3.5 MTP 80K и Q5 96K были технически стабильны, но ответ деградировал; оба оставлены на 64K.</p></section>
<section><h2>Изображения</h2><p><strong>Генерация:</strong> Qwen-Image-2.1 Q5_K_M, 1024×1024, 20 шагов, Euler, CFG 6, seed 42, CPU offload, diffusion=disk, Flash Attention и VAE tiling 256×256 с overlap 0.5. Сегодняшняя генерация: {telemetry['elapsed_seconds']:.1f} с; пик VRAM {telemetry['peak_vram_mib']:.0f} МиБ; RAM контейнера {telemetry['peak_container_ram_mib']:.0f} МиБ. Для запуска нужен остановленный gateway.</p><p class="warn"><strong>Редактирование по референсу:</strong> два прогона, 512×512 и 1024×1024, завершились ошибкой чтения тензоров diffusion GGUF во время генерации. Повторная SHA256-проверка файла совпала с манифестом, поэтому этот режим сейчас нельзя рекомендовать как рабочий. Лог второго прогона: <code>benchmark/context-audit-20260929/edit-retry.log</code>; пик VRAM {edit_telemetry['peak_vram_mib']:.0f} МиБ.</p><p><strong>Понимание изображений:</strong> {esc(vision_note)}. У Qwen3.5 Vision длинный вход 48K проверялся текстом; изображение уменьшает доступное место под текст.</p><img src="../../media/images/context-audit-image-20260929.png" alt="Контрольное изображение с лисой"></section>
<section><h2>Видео и речь</h2><p><strong>Создание видео:</strong> отдельной модели text-to-video или image-to-video и её Docker-профиля здесь нет. Параметры генерации видео пока назначить нельзя. Имеющийся ffmpeg + Whisper + Vision pipeline извлекает звук и кадры для анализа готового видео; это не генератор видео.</p><p><strong>Речь:</strong> Whisper large-v3-turbo Q8_0 повторно распознал тестовый WAV через Docker за 0.89 с. Запуск по требованию на порту 8082, затем остановка для освобождения GPU.</p></section>
<section><h2>Файлы и воспроизводимость</h2><p>Живой gateway: <code>ai-server/config/llama-swap.yaml</code>. Свод настроек: <code>ai-server/config/recommended-settings-20260929.json</code>. Сырые измерения: <code>benchmark/context-20260929.jsonl</code> и <code>benchmark/expanded-context-20260929.jsonl</code>. Команды прогона: <code>scripts/probe-live-context.py</code>, <code>scripts/probe-expanded-context.py</code>, <code>scripts/start-qwen-image.ps1</code>, <code>scripts/test-whisper.ps1</code>.</p></section>
<footer>После тестов gateway снова запущен и отвечает; модель при старте не загружена. Все выводы относятся к текущему Docker runtime, драйверу, GPU и фоновым процессам.</footer></main></body></html>"""
(OUT / "index.html").write_text(page, encoding="utf-8")
print(OUT / "index.html")
