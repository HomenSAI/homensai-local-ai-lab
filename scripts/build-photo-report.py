from __future__ import annotations
import base64, hashlib, html, json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
image_path = root / 'media' / 'images' / 'alpine-foal-spring-1280x832.png'
telemetry_path = image_path.with_name(image_path.name + '.telemetry.json')
report_path = image_path.parent / 'alpine-foal-spring-report.html'
data = json.loads(telemetry_path.read_text(encoding='utf-8-sig'))
image_bytes = image_path.read_bytes()
sha256 = hashlib.sha256(image_bytes).hexdigest()
size_mib = len(image_bytes) / (1024 * 1024)
prompt = html.escape(data['prompt'])
when = html.escape(data['timestamp_utc'])
duration = data['elapsed_seconds']
peak_vram = data['peak_vram_mib']
peak_ram = data['peak_container_ram_mib']
util = data['gpu_utilization_avg_percent']
power = data['power_avg_w']
image_data = base64.b64encode(image_bytes).decode('ascii')
template = r'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Локальная генерация — жеребёнок в Альпах</title>
<style>
:root{color-scheme:dark;--bg:#10151d;--card:#19232f;--line:#324253;--mint:#98e4cc;--muted:#b8c7d5;--blue:#9bd6fa}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 20% 0,#203c47 0,transparent 45%),var(--bg);color:#eff5f7;font:16px/1.65 Segoe UI,Arial,sans-serif}main{max-width:1160px;margin:auto;padding:28px 22px 60px}header,.card,section{background:color-mix(in srgb,var(--card) 94%,transparent);border:1px solid var(--line);border-radius:18px;padding:22px;margin-bottom:18px}header{padding:34px;background:linear-gradient(120deg,#183a44,#1d2d44)}h1{font-size:clamp(28px,5vw,44px);line-height:1.12;margin:0 0 12px}h2{margin:0 0 14px;color:var(--mint);font-size:22px}p{margin:.55em 0}.muted,small{color:var(--muted)}.badges{display:flex;gap:9px;flex-wrap:wrap;margin-top:17px}.badge{border:1px solid #547286;border-radius:999px;padding:5px 11px;color:#d6edf6;font-size:14px}.hero{width:100%;height:auto;display:block;border-radius:12px;border:1px solid #45596c}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.metric{background:#111b25;border:1px solid var(--line);border-radius:12px;padding:15px}.metric strong{display:block;font-size:22px;color:#fff}.metric span{font-size:13px;color:var(--muted)}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}th{width:230px;color:var(--mint)}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#101820;border:1px solid var(--line);padding:15px;border-radius:10px;color:#d9e9f2;font:14px/1.6 Consolas,monospace}code{background:#101820;padding:2px 5px;border-radius:5px}a{color:var(--blue)}ol{padding-left:23px}li{padding:4px 0}.note{border-left:4px solid var(--mint);padding:10px 14px;background:#14262a;border-radius:5px}footer{color:var(--muted);font-size:13px;padding:6px 2px}@media(max-width:620px){main{padding:12px}header,.card,section{padding:16px}th{width:auto}}
</style></head><body><main>
<header><h1>Весна в Альпах</h1><p>Фотореалистичный жеребёнок на цветущем горном лугу, созданный локальной моделью в Docker на RTX 3080.</p><div class="badges"><span class="badge">Qwen-Image-2.1 Q5_K_M</span><span class="badge">1280 × 832</span><span class="badge">30 шагов</span><span class="badge">Генерация завершена</span></div></header>
<section><h2>Результат</h2><img class="hero" src="data:image/png;base64,%%IMAGE%%" alt="Молодой рыжий конь среди весенних альпийских цветов на фоне заснеженных Альп"><p><a href="%%PNG_NAME%%" download>Скачать исходный PNG</a> · %%SIZE%% МиБ · SHA-256: <code>%%SHA256%%</code></p></section>
<section><h2>Проверка прогона</h2><div class="metrics"><div class="metric"><strong>%%DURATION%% с</strong><span>Полное время команды с загрузкой модели и декодированием</span></div><div class="metric"><strong>%%VRAM%% / 10 240 МиБ</strong><span>Пиковая занятая видеопамять</span></div><div class="metric"><strong>%%RAM%% МиБ</strong><span>Пиковая RAM контейнера</span></div><div class="metric"><strong>%%UTIL%%%</strong><span>Средняя загрузка GPU</span></div><div class="metric"><strong>%%POWER%% Вт</strong><span>Средняя мощность GPU</span></div><div class="metric"><strong>PNG · %%WIDTH%%×%%HEIGHT%%</strong><span>Файл создан, статус генерации complete</span></div></div><p class="muted">UTC: %%WHEN%% · Seed: %%SEED%% · Ошибок генерации: нет.</p></section>
<section><h2>Параметры генерации</h2><div style="overflow:auto"><table>
<tr><th>Модель изображения</th><td>Qwen-Image-2.1 Q5_K_M (локальный GGUF)</td></tr><tr><th>Текстовый энкодер</th><td>Qwen3-VL-8B-Instruct Q4_K_M; загрузка энкодера на CPU</td></tr><tr><th>VAE</th><td>Qwen Image 2.1 BF16; тайлинг декодирования 256×256, overlap 0.5</td></tr><tr><th>Размер и шаги</th><td>%%WIDTH%%×%%HEIGHT%% пикселей, 30 шагов</td></tr><tr><th>Sampler / CFG / seed</th><td>Euler / 6.0 / %%SEED%%</td></tr><tr><th>Память и ускорение</th><td><code>--offload-to-cpu</code>, <code>diffusion=disk</code>, Flash Attention; автоматический VRAM лимит с резервом 1 ГиБ</td></tr><tr><th>Промпт</th><td><details><summary>Показать полный промпт</summary><pre>%%PROMPT%%</pre></details></td></tr></table></div></section>
<section><h2>Шаги выполнения</h2><ol><li>Освободил GPU: временно остановил контейнеры llama-swap и ComfyUI video, а также stats-report; файл и настройки этих сервисов не менялись.</li><li>Запустил Docker Compose сервис <code>qwen-image</code> через проектный скрипт <code>ai-server/scripts/start-qwen-image.ps1</code>. Веса изображения Q5 размещены между VRAM и RAM; генерация прошла на RTX 3080 без out-of-memory.</li><li>Подал подробный англоязычный фотопромпт для точного управления сценой: жеребёнок в полный рост, цветы в переднем плане, долина и заснеженные пики Альп, естественный весенний свет.</li><li>Сгенерировал один кадр на Euler, CFG 6, seed %%SEED%%, 30 шагов и 1280×832. Для стабильной работы включены CPU offload, диск-бэкенд, Flash Attention и тайловый VAE.</li><li>Проверил статус завершения, размеры, PNG-файл, телеметрию и SHA-256. После генерации ранее запущенные контейнеры Docker возвращены в работу.</li></ol><p class="note">Разрешение выбрано широкоформатным при почти том же числе пикселей, что и проверенный ранее стабильный квадратный режим 1024×1024. Это даёт композицию пейзажа и сохраняет запас VRAM на RTX 3080 с 10 ГБ.</p></section>
<footer>Отчёт создан автоматически из телеметрии локального Docker-прогона. PNG встроен в HTML, поэтому изображение видно и при переносе отчёта; исходный PNG лежит рядом с ним.</footer>
</main></body></html>'''
values = {
    '%%IMAGE%%': image_data,
    '%%PNG_NAME%%': html.escape(image_path.name, quote=True),
    '%%SIZE%%': f'{size_mib:.2f}',
    '%%SHA256%%': sha256,
    '%%DURATION%%': f'{duration:.1f}',
    '%%VRAM%%': f'{peak_vram:.0f}',
    '%%RAM%%': f'{peak_ram:.1f}',
    '%%UTIL%%': f'{util:.1f}',
    '%%POWER%%': f'{power:.1f}',
    '%%WIDTH%%': str(data['width']),
    '%%HEIGHT%%': str(data['height']),
    '%%WHEN%%': when,
    '%%SEED%%': str(data['seed']),
    '%%PROMPT%%': prompt,
}
for key, value in values.items():
    template = template.replace(key, value)
report_path.write_text(template, encoding='utf-8')
print(json.dumps({'report': str(report_path), 'image': str(image_path), 'report_bytes': report_path.stat().st_size, 'image_bytes': len(image_bytes), 'sha256': sha256}, ensure_ascii=False, indent=2))
