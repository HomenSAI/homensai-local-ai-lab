import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark" / "q4kv-20260929"
BENCH.mkdir(parents=True, exist_ok=True)
RAW = ROOT / "benchmark" / "q4kv-20260929.jsonl"
BASELINE = ROOT / "config" / "recommended-settings-20260929.json"
VIDEO_ROOT = ROOT / "video-generation"

profiles = {
    "Qwen3.5-9B-MTP-Q4_K_XL": {
        "recommended_context_tokens": 131072, "recommended_max_input_tokens": 107609,
        "largest_tested_context_tokens": 262144, "largest_tested_input_tokens": 215088,
        "largest_tested_input_recall_pass": True, "peak_vram_mib": 9723,
        "cache_type_k": "q4_0", "cache_type_v": "q4_0", "runtime": "upstream llama.cpp; MTP n-max=2",
        "use": "Основная текстовая модель и длинные документы",
        "notes": "262144 и вход 215088 токенов прошли извлечение кода, но осталось около 517 МиБ VRAM. Для ежедневной работы рекомендовано 131072; максимальный режим включать только при свободной GPU и отсутствии других задач."
    },
    "Qwen3.5-9B-MTP-Q4_K_XL-Vision": {
        "recommended_context_tokens": 98304, "recommended_max_input_tokens": 80739,
        "largest_tested_context_tokens": 131072, "largest_tested_input_tokens": 107609,
        "largest_tested_input_recall_pass": True, "peak_vram_mib": 9142,
        "cache_type_k": "q4_0", "cache_type_v": "q4_0", "runtime": "upstream llama.cpp; F16 mmproj; MTP off",
        "use": "Изображения и мультимодальный разбор",
        "notes": "На тексте успешно извлекала код при 131072; 163840 не ответил за 240 секунд. Q4/KV длинный прогон был текстовым; фактические изображения отдельно подтверждались в базовом аудите при 49152. Для image prompts оставлен консервативный лимит 49152."
    },
    "Qwen3.5-9B-Q5_K_S": {
        "recommended_context_tokens": 262144, "recommended_max_input_tokens": 215088,
        "largest_tested_context_tokens": 262144, "largest_tested_input_tokens": 215088,
        "largest_tested_input_recall_pass": True, "peak_vram_mib": 8984,
        "cache_type_k": "q4_0", "cache_type_v": "q4_0", "runtime": "upstream llama.cpp; без MTP",
        "use": "Предпочтительный профиль для очень длинного текста",
        "notes": "Успешный поиск кода на входе 215088 токенов; около 1256 МиБ VRAM оставались свободными. Из протестированных профилей это наиболее сбалансированный максимальный контекст."
    },
    "MiniCPM5-2B-Q4_K_M": {
        "recommended_context_tokens": 8192, "recommended_max_input_tokens": 123,
        "largest_tested_context_tokens": 131072, "largest_tested_input_tokens": 107615,
        "largest_tested_input_recall_pass": False, "peak_vram_mib": 5713,
        "cache_type_k": "q5_0", "cache_type_v": "q5_0", "runtime": "upstream llama.cpp; DSpark off",
        "use": "Короткие задачи и черновики",
        "notes": "Короткая проверка прошла с KV Q5_0. На входах 4136–107615 токенов контрольный код не восстановлен; большой технический n_ctx загружался, но не подтверждает практическую точность."
    },
    "Spark-X2.5-4B-Q4_K_M": {
        "recommended_context_tokens": 32768, "recommended_max_input_tokens": 16166,
        "largest_tested_context_tokens": 524288, "largest_tested_input_tokens": 215124,
        "largest_tested_input_recall_pass": False, "best_retrieval_input_tokens": 16166,
        "best_retrieval_repeats_passed": 2, "peak_vram_mib": 9748,
        "cache_type_k": "q4_0", "cache_type_v": "q4_0", "runtime": "upstream llama.cpp; thinking off",
        "use": "Инструменты и умеренный контекст",
        "notes": "Вход 16166 прошёл извлечение кода дважды. На 24166 и выше поиск проваливался; 524288 проверен только коротким запросом, занял 9748 МиБ и оставил около 492 МиБ VRAM. Большое окно не считать рабочей памятью."
    },
    "Ternary-Bonsai-2-27B-PTQ1_0": {
        "recommended_context_tokens": 65536, "recommended_max_input_tokens": 53869,
        "largest_tested_context_tokens": 131072, "largest_tested_input_tokens": 107609,
        "largest_tested_input_recall_pass": True, "peak_vram_mib": 9564,
        "cache_type_k": "q4_0", "cache_type_v": "q4_0", "runtime": "PrismML llama-server через существующий llama-swap",
        "upstream_llama_cpp_load": "failed: GGUF tensor output.weight type 143 unsupported",
        "use": "Экспериментальная модель; оставлять в существующем PrismML runtime",
        "notes": "В PrismML с KV Q4_0 режим 65536 подтвердил контекст на 53869 токенах; 131072 также ответил, но оставил лишь около 676 МиБ VRAM. Перенос именно на upstream llama.cpp не удался: upstream вернул HTTP 500, тип GGUF 143 вне диапазона [0,43). Модель уже доступна в llama-swap через PrismML; production runtime не переключался."
    },
    "Qwen3-VL-8B-Instruct-Q4_K_M": {
        "recommended_context_tokens": 32768, "recommended_image_context_tokens": 16384,
        "recommended_max_input_tokens": 16166, "largest_tested_context_tokens": 32768,
        "largest_tested_input_tokens": 27006, "largest_tested_input_recall_pass": "pass in 1 of 2 repeated runs",
        "peak_vram_mib": 8799, "cache_type_k": "q5_0", "cache_type_v": "q5_0",
        "runtime": "upstream llama.cpp; F16 mmproj",
        "use": "Текст и понимание изображений",
        "notes": "При 32768 длинный тест извлёк код в одном из двух повторов; 65536 завершился таймаутом 240 секунд. Для изображений рекомендовано 16384: в базовом аудите этот размер прошёл реальный image prompt."
    }
}
profiles["MiniCPM5-2B-Q4_K_M"]["weights_file"] = "MiniCPM5/MiniCPM5-2B-Q4_K_M.gguf"
profiles["MiniCPM5-2B-Q4_K_M"]["weights_sha256"] = "ec2d5801640099e97d8d7e8003ad4d81f336e757811f03a26173dddf386602fd"
profiles["MiniCPM5-2B-Q4_K_M"]["weights_source"] = "openbmb/MiniCPM5-2B-GGUF, revision 2079a22f3beaa4e306449978533478fe0522f4b3"
profiles["Spark-X2.5-4B-Q4_K_M"]["weights_file"] = "Spark/Spark-X2.5-4B-Q4_K_M.gguf"
profiles["Spark-X2.5-4B-Q4_K_M"]["weights_sha256"] = "dc08c21953fbdf797d77fbe7cdecb353d8dc6cb3517c2f911e209bb37633726a"
profiles["Spark-X2.5-4B-Q4_K_M"]["weights_source"] = "stornic56/Spark-X2.5-4B-GGUF, revision 7ce72e5cba148e5e4bcd0ff0e59c8268f9820619"

rows = [json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines() if line.strip()]
by_model = {}
for row in rows:
    by_model.setdefault(row["model"], []).append(row)

baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
baseline_names = {
    "Qwen3.5-9B-MTP-Q4_K_XL": "Qwen3.5-9B-MTP-Q4_K_XL",
    "Qwen3.5-9B-MTP-Q4_K_XL-Vision": "Qwen3.5-9B-MTP-Q4_K_XL-Vision",
    "Qwen3.5-9B-Q5_K_S": "Qwen3.5-9B-Q5_K_S",
    "MiniCPM5-2B-Q4_K_M": "MiniCPM5-2B-Q8_0",
    "Spark-X2.5-4B-Q4_K_M": "Spark-X2.5-4B-Q8_0",
    "Ternary-Bonsai-2-27B-PTQ1_0": "Ternary-Bonsai-2-27B-PTQ1_0",
    "Qwen3-VL-8B-Instruct-Q4_K_M": "Qwen3-VL-8B-Instruct-Q4_K_M",
}
for profile_name, baseline_name in baseline_names.items():
    old = baseline["model_profiles"].get(baseline_name, {})
    profiles[profile_name]["baseline_profile"] = baseline_name
    profiles[profile_name]["baseline_recommended_context_tokens"] = old.get("recommended_context_tokens")
    profiles[profile_name]["baseline_runtime_settings"] = old.get("runtime_settings")
upstream_bonsai_path = BENCH / "bonsai-upstream-protocol-A.json"
upstream_bonsai = json.loads(upstream_bonsai_path.read_text(encoding="utf-8")) if upstream_bonsai_path.exists() else None
video_test = VIDEO_ROOT / "output" / "test-summary.json"
video_full = VIDEO_ROOT / "output" / "generation-summary.json"
video_verify = VIDEO_ROOT / "output" / "verification.json"
video_smoke_file = VIDEO_ROOT / "output" / "video" / "smoke_test_00001_.mp4"
video_final_file = VIDEO_ROOT / "output" / "superhero_10s.mp4"
video_scene_files = sorted((VIDEO_ROOT / "output" / "video").glob("scene_*.mp4"))
try:
    inspect = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}|{{.State.ExitCode}}|{{.State.OOMKilled}}|{{.State.FinishedAt}}", "video-generation-comfyui-video-1"],
        check=True, capture_output=True, text=True, timeout=15,
    ).stdout.strip().split("|", 3)
    video_container = {"status": inspect[0], "exit_code": int(inspect[1]), "oom_killed": inspect[2].lower() == "true", "finished_utc": inspect[3]}
except Exception:
    video_container = None
if video_verify.exists():
    video_status = "generated_and_verified"
elif video_full.exists():
    video_status = "generated_not_verified"
elif video_test.exists():
    video_status = "smoke_passed_full_pending"
elif video_container and video_container["status"] == "running":
    video_status = "smoke_running"
elif video_container and video_container["oom_killed"]:
    video_status = "failed_oom"
else:
    video_status = "smoke_pending_or_failed"

settings = {
    "date": "2026-09-29",
    "test_variant": "weights Q4/Q5 where available; KV cache Q4_0/Q5_0; maximum stable n_ctx",
    "hardware": "NVIDIA RTX 3080 10240 MiB",
    "source_data": str(RAW),
    "protocol": "Variant 2 user prompt plus long-context needle retrieval; exact request/response records in JSONL.",
    "global_runtime_recommendations": {
        "gpu_layers": "all", "flash_attention": "on", "parallel": 1,
        "batch_size": 512, "ubatch_size": 128,
        "note": "Сохранять один активный GPU inference профиль. Квантованные веса занимают меньше постоянной VRAM, а Q4/Q5 KV cache снижает память на токен и оставляет больше места под n_ctx. Это расширяет доступное окно, но не гарантирует точное извлечение длинного текста; recall проверен отдельно.",
        "llama_cpp_cache_type_docs": "https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md"
    },
    "model_profiles": profiles,
    "photo_generation": {
        "status": "tested_in_baseline_audit",
        "model": "Qwen-Image-2.1 Q5_K_M",
        "width": 1024, "height": 1024, "steps": 20, "sampler": "euler",
        "cfg_scale": 6.0, "seed": 42, "cpu_offload": True,
        "params_backend": "diffusion=disk", "diffusion_flash_attention": True,
        "vae_tiling": {"tile": "256x256", "overlap": 0.5},
        "start_script": str(ROOT / "scripts" / "start-qwen-image.ps1"),
        "operational_note": "Image generation uses its separate Docker service and competes for GPU memory. Reference-based editing at 512 and 1024 failed during diffusion tensor reads; do not treat editing as validated."
    },
    "video_generation": {
        "status_at_report_build": video_status,
        "smoke_video_file": str(video_smoke_file) if video_smoke_file.exists() else None,
        "generated_scene_files": [str(path) for path in video_scene_files],
        "final_video_file": str(video_final_file) if video_final_file.exists() else None,
        "container_result": video_container,
        "smoke_test_summary": json.loads(video_test.read_text(encoding="utf-8")) if video_test.exists() else None,
        "full_generation_summary": json.loads(video_full.read_text(encoding="utf-8")) if video_full.exists() else None,
        "verification": json.loads(video_verify.read_text(encoding="utf-8")) if video_verify.exists() else None,
        "runtime": "Docker Compose + ComfyUI; Wan 2.1 T2V 1.3B FP16",
        "text_encoder": "UMT5-XXL FP8 E4M3FN scaled on CPU",
        "vae": "Wan 2.1 VAE on CPU",
        "resolution": "832x480", "fps": 16,
        "scene_frames": 81, "scenes": 2, "assembled_frames": 160,
        "duration_seconds": 10, "steps": 20, "cfg": 6.0,
        "sampler": "uni_pc", "scheduler": "simple", "shift": 8,
        "seeds": [26092901, 26092902], "low_vram": True,
        "allocator_environment": "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True",
        "compose_file": str(VIDEO_ROOT / "docker-compose.yml"),
        "workflow_file": str(VIDEO_ROOT / "workflows" / "text_to_video_wan_official.json"),
        "operational_note": "Имеется отдельный локальный T2V профиль. Один smoke дошёл до декодирования VAE, затем завершился с кодом 137 и OOMKilled=true. ComfyUI сообщал 7910 MiB системной RAM; актуальное состояние контейнера и итоговых файлов записывается отдельно."
    },
    "photo_editing": baseline.get("photo_editing"),
    "speech_to_text": baseline.get("speech_to_text"),
    "bonsai_upstream_attempt": {
        "evidence_file": str(upstream_bonsai_path),
        "status": upstream_bonsai.get("status") if upstream_bonsai else "not_run",
        "error": upstream_bonsai.get("gateway_logs_tail", "")[-2500:] if upstream_bonsai else None,
        "model_sha256": upstream_bonsai.get("model_sha256") if upstream_bonsai else None
    }
}
(BENCH / "recommended-settings-q4kv-20260929.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

# Ready-to-review llama-swap profile. It is deliberately separate from the live config.
source_yaml = ROOT / "config" / "llama-swap-q4kv.yaml"
recommended_yaml = ROOT / "config" / "llama-swap-q4kv-recommended.yaml"
yaml_text = source_yaml.read_text(encoding="utf-8")
yaml_text = "\n".join(line for line in yaml_text.splitlines() if not line.startswith("#")) + "\n"
yaml_contexts = {
    "Qwen3.5-9B-MTP-Q4_K_XL": 131072,
    "Qwen3.5-9B-MTP-Q4_K_XL-Vision": 98304,
    "Qwen3.5-9B-Q5_K_S": 262144,
    "MiniCPM5-2B-Q4_K_M": 8192,
    "Spark-X2.5-4B-Q4_K_M": 32768,
    "Ternary-Bonsai-2-27B-PTQ1_0": 65536,
    "Qwen3-VL-8B-Instruct-Q4_K_M": 32768,
}
yaml_descriptions = {
    "Qwen3.5-9B-MTP-Q4_K_XL": "Qwen3.5 9B MTP Q4_K_XL with Q4_0 KV; daily context 131072; validated through 262144 with low VRAM headroom.",
    "Qwen3.5-9B-MTP-Q4_K_XL-Vision": "Qwen3.5 Q4 with F16 vision projector, MTP off, Q4_0 KV; text context 98304; image prompts use 49152.",
    "Qwen3.5-9B-Q5_K_S": "Qwen3.5 9B Q5_K_S with Q4_0 KV; context 262144 and exact retrieval verified at 215088 input tokens.",
    "MiniCPM5-2B-Q4_K_M": "MiniCPM5 2B native Q4_K_M with Q5_0 KV; short tasks only, context 8192; long retrieval not reliable.",
    "Spark-X2.5-4B-Q4_K_M": "Spark X2.5 native Q4_K_M with Q4_0 KV; context 32768; exact retrieval verified at 16166 input tokens.",
    "Ternary-Bonsai-2-27B-PTQ1_0": "Bonsai PTQ1_0; PrismML backend required (upstream llama.cpp rejects GGUF tensor type 143); Q4_0 KV, context 65536.",
    "Qwen3-VL-8B-Instruct-Q4_K_M": "Qwen3-VL Q4_K_M with F16 projector and Q5_0 KV; text context 32768, image context 16384.",
}
yaml_names = list(yaml_contexts)
for index, model_name in enumerate(yaml_names):
    start = yaml_text.index(f"  {model_name}:\n")
    if index + 1 < len(yaml_names):
        end = yaml_text.index(f"  {yaml_names[index + 1]}:\n", start)
    else:
        end = yaml_text.index("\nrouting:\n", start)
    block = yaml_text[start:end]
    ctx = yaml_contexts[model_name]
    block = re.sub(r"--ctx-size \d+", f"--ctx-size {ctx}", block, count=1)
    block = re.sub(r"context: \d+", f"context: {ctx}", block, count=1)
    block = re.sub(r"(?m)^    description:.*$", f"    description: {yaml_descriptions[model_name]}", block, count=1)
    if model_name == "Ternary-Bonsai-2-27B-PTQ1_0":
        block = block.replace(
            "/app/llama-server --host 127.0.0.1 --port ${PORT}",
            "env LD_LIBRARY_PATH=/opt/prism:/usr/local/cuda/lib64 /opt/prism/llama-server --host 127.0.0.1 --port ${PORT}",
            1,
        )
    block = block.replace("\r\n", "\n")
    yaml_text = yaml_text[:start] + block + yaml_text[end:]
yaml_text = "# Recommended Q4/Q5 weights and Q4/Q5 KV profile from the 2026-09-29 tests.\n# Reviewable profile only; the live llama-swap.yaml was not changed.\n" + yaml_text
recommended_yaml.write_text(yaml_text, encoding="utf-8")

def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def fmt_tokens(value):
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return esc(value)

trs = []
for name, profile in profiles.items():
    ctx = fmt_tokens(profile["recommended_context_tokens"])
    if "recommended_image_context_tokens" in profile:
        ctx += f" (изображения: {fmt_tokens(profile['recommended_image_context_tokens'])})"
    success = profile.get("largest_tested_input_recall_pass")
    success_text = "да" if success is True else ("нет" if success is False else esc(success))
    input_tokens = profile.get("largest_tested_input_tokens")
    if "best_retrieval_input_tokens" in profile:
        input_tokens = f"{fmt_tokens(profile['best_retrieval_input_tokens'])} (2/2)"
    trs.append(
        "<tr>" +
        f"<td><strong>{esc(name)}</strong><small>{esc(profile['use'])}</small></td>" +
        f"<td>{fmt_tokens(profile.get('baseline_recommended_context_tokens'))}</td>" +
        f"<td>{ctx}</td><td>{fmt_tokens(profile['largest_tested_context_tokens'])}</td>" +
        f"<td>{fmt_tokens(input_tokens)}</td><td>{success_text}</td>" +
        f"<td>{fmt_tokens(profile['peak_vram_mib'])} МиБ</td><td>{esc(profile['cache_type_k'])}/{esc(profile['cache_type_v'])}</td>" +
        f"<td>{esc(profile['notes'])}</td></tr>"
    )

test_rows = []
for name, model_rows in by_model.items():
    n = len(model_rows)
    ok = sum(1 for x in model_rows if x.get("status") == "ok")
    recalled = sum(1 for x in model_rows if x.get("recall") is True)
    timeouts = sum(1 for x in model_rows if x.get("status") == "error")
    max_ctx = max((x.get("context", 0) for x in model_rows), default=0)
    test_rows.append(f"<tr><td>{esc(name)}</td><td>{n}</td><td>{ok}</td><td>{recalled}/{n}</td><td>{fmt_tokens(max_ctx)}</td><td>{timeouts}</td></tr>")

if video_status == "smoke_passed_full_pending":
    video_phrase = "Короткий smoke пройден; полный 10-секундный клип ещё не собран."
elif video_status == "generated_and_verified":
    video_phrase = "Итоговое видео создано и проверено через ffprobe."
elif video_status == "generated_not_verified":
    video_phrase = "Генерация закончилась; итоговая ffprobe-проверка ещё отсутствует."
elif video_status == "smoke_running":
    video_phrase = "Smoke-прогон запущен; output/test-summary.json пока не записан. Один предыдущий запуск завершился OOMKilled (код 137), поэтому итог этого повторного прогона ещё не подтверждён."
elif video_status == "failed_oom":
    video_phrase = "Smoke не завершился: после 20/20 шагов sampler контейнер завершился с кодом 137 (OOMKilled=true) на декодировании VAE; ComfyUI видел около 7910 МиБ системной RAM. Итоговый MP4 не создан."
else:
    video_phrase = "Финальный smoke-статус нужно сверить с generation.log и output/test-summary.json."
if video_final_file.exists():
    video_preview_html = '<p><video controls playsinline preload="metadata" src="../../video-generation/output/superhero_10s.mp4"></video><a href="../../video-generation/output/superhero_10s.mp4">Открыть MP4</a></p>'
elif video_scene_files:
    video_preview_html = '<p><video controls playsinline preload="metadata" src="../../video-generation/output/video/scene_01_rooftop_00001_.mp4"></video><a href="../../video-generation/output/video/scene_01_rooftop_00001_.mp4">Открыть готовую сцену 1</a></p>'
elif video_smoke_file.exists():
    video_preview_html = '<p><video controls playsinline preload="metadata" src="../../video-generation/output/video/smoke_test_00001_.mp4"></video><a href="../../video-generation/output/video/smoke_test_00001_.mp4">Открыть smoke MP4</a></p>'
else:
    video_preview_html = ""

page = f"""<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Q4/KV контекст — аудит локальных ИИ</title>
<style>body{{margin:0;background:#101827;color:#eaf0fb;font:15px/1.6 Segoe UI,Arial,sans-serif}}main{{max-width:1440px;margin:auto;padding:28px}}header,.card,section{{background:#19263a;border:1px solid #30415a;border-radius:14px;padding:20px;margin-bottom:16px}}h1{{font-size:2rem;margin:.2em 0}}h2{{color:#9fe0d7;margin:.2em 0 .7em}}.lede,small,.muted{{color:#b1bfd2}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}.card strong{{display:block;font-size:1.6rem;color:#fff}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:1100px}}td,th{{padding:10px;border-bottom:1px solid #34465f;text-align:left;vertical-align:top}}th{{color:#9fe0d7}}small{{display:block;font-size:.84rem;margin-top:4px}}code{{background:#263951;padding:2px 5px;border-radius:4px}}.warn{{border-left:4px solid #ffbe67;padding:10px 14px;background:#2b2b2a}}a{{color:#9edaff}}footer{{color:#a9b8cb;padding:10px}}@media(max-width:700px){{main{{padding:12px}}}}</style></head><body><main>
<header><div>Docker · NVIDIA RTX 3080 10 GiB · 29 сентября 2026</div><h1>Контекстный аудит Q4/KV Q4–Q5</h1><div class=\"lede\">Вариант 2: квантованные веса, KV cache Q4/Q5, максимально допустимый n_ctx. Здесь отдельно указаны технический размер окна и подтверждённое извлечение фактов. Снижение разрядности весов и KV cache экономит VRAM и даёт место под большее окно; точный retrieval всё равно проверяется отдельно. <a href=\"https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md\">Параметры типов KV в upstream llama.cpp</a>.</div></header>
<div class=\"cards\"><div class=\"card\"><strong>262 144</strong>максимум, прошедший извлечение факта: Qwen3.5 Q5</div><div class=\"card\"><strong>215 088</strong>токенов во входном тесте с точным recall</div><div class=\"card\"><strong>9 748 / 10 240 МиБ</strong>пик GPU у Spark на коротком запросе при n_ctx 524 288</div><div class=\"card\"><strong>5 120–5 713 МиБ</strong>пик MiniCPM Q4; длинный recall не подтвердился</div></div>
<section><h2>Рекомендуемые настройки для работы</h2><p>«Базовый n_ctx» — прошлый профиль с KV FP16; «рабочий контекст» учитывает запас видеопамяти и точность извлечения; «максимум проверен» — наибольший заданный серверу n_ctx. Большой n_ctx сам по себе не означает, что модель удерживает начало длинного документа.</p><div class=\"scroll\"><table><thead><tr><th>Модель</th><th>Базовый n_ctx</th><th>Рабочий контекст</th><th>Максимум проверен</th><th>Вход/извлечение</th><th>Recall</th><th>Пик VRAM</th><th>KV cache K/V</th><th>Результат и ограничение</th></tr></thead><tbody>{''.join(trs)}</tbody></table></div></section>
<section><h2>Объём прогонов</h2><div class=\"scroll\"><table><thead><tr><th>Модель из JSONL</th><th>Запросов</th><th>Ответили</th><th>Вернули код</th><th>Макс. n_ctx</th><th>Ошибки/таймауты</th></tr></thead><tbody>{''.join(test_rows)}</tbody></table></div><p>Проверочный длинный prompt повторял маркер у начала и требовал вернуть его в конце. Это проверяет точный retrieval и стабильность, но не измеряет качество на любых реальных документах. Строки с суффиксом <code>-requant</code> — ранние эксперименты локального переквантования; итоговые профили используют нативные Q4-файлы, проверенные SHA-256.</p><p class=\"warn\"><strong>Bonsai в upstream llama.cpp.</strong> {esc(upstream_bonsai.get('error', 'Проверка не записана.')[-350:]) if upstream_bonsai else 'Проверка не записана.'} Поддерживаемый вариант — оставить Bonsai в существующем llama-swap через PrismML. На PrismML профиль Q4 KV с n_ctx 65536 прошёл вход 53869 токенов; 131072 запустился, но имел малый запас VRAM.</p></section>
<section><h2>Фото: рекомендуемый профиль генерации</h2><p><strong>Qwen-Image-2.1 Q5_K_M:</strong> 1024×1024, 20 шагов, Euler, CFG 6.0, seed 42, CPU offload, <code>diffusion=disk</code>, Flash Attention, VAE tiling 256×256 с overlap 0.5. Запуск через <code>ai-server/scripts/start-qwen-image.ps1</code>; image pipeline отдельный от текстового llama-server. Генерация 1024² подтверждена в базовом аудите.</p><p class=\"warn\">Редактирование фотографии по референсу не прошло проверку при 512² и 1024²: ошибка чтения тензоров diffusion GGUF. Этот режим не включён в рекомендации.</p><p>Базовый аудит: <a href=\"../context-audit-20260929/index.html\">HTML-отчёт</a>.</p></section>
<section><h2>Распознавание речи</h2><p><strong>Whisper large-v3-turbo Q8_0</strong> — отдельный Docker-профиль, ранее распознал контрольный WAV за 0,89 с. Параметры Q4/KV и контекст llama.cpp к Whisper неприменимы; использовать отдельный endpoint <code>http://127.0.0.1:8082/inference</code>.</p></section>
<section><h2>Видео: отдельный профиль генерации</h2><p><strong>Wan 2.1 T2V 1.3B FP16 + ComfyUI в Docker.</strong> 832×480, 16 fps; 2 сцены × 81 кадр; итог 160 кадров / 10 секунд; sampler uni_pc, scheduler simple, 20 шагов, CFG 6, shift 8, seeds 26092901 и 26092902. UMT5-XXL FP8 и VAE работают на CPU, включён low-VRAM режим. Результат — беззвучный MP4 H.264.</p><p>{esc(video_phrase)} Две отдельно сгенерированные сцены могут различаться деталями персонажа.</p>{video_preview_html}<p>Конфигурация: <a href=\"../../video-generation/docker-compose.yml\">Docker Compose</a>, <a href=\"../../video-generation/workflows/text_to_video_wan_official.json\">workflow</a>; сводка: <a href=\"../../video-generation/README.md\">README</a>.</p></section>
<section><h2>Файлы и воспроизводимость</h2><ul><li>Настройки и результаты: <a href=\"recommended-settings-q4kv-20260929.json\">recommended-settings-q4kv-20260929.json</a>.</li><li>Рекомендованный, но не применённый профиль: <a href=\"../../config/llama-swap-q4kv-recommended.yaml\">llama-swap-q4kv-recommended.yaml</a>.</li><li>Тестовая конфигурация максимальных окон: <a href=\"../../config/llama-swap-q4kv.yaml\">llama-swap-q4kv.yaml</a>.</li><li>Тестовые запросы и ответы: <a href=\"../q4kv-20260929.jsonl\">q4kv-20260929.jsonl</a>.</li><li>Подробный upstream Bonsai error: <a href=\"bonsai-upstream-protocol-A.json\">bonsai-upstream-protocol-A.json</a>.</li><li>Настройки генерации видео и smoke-логи: <a href=\"../../video-generation/logs/generation.log\">generation.log</a>.</li></ul><p>Прогоны выполнены последовательно на одной RTX 3080 10 ГиБ. Тестовый шлюз применялся отдельно от производственного. Контексты, таймауты и сырые ответы сохранены в JSONL.</p></section>
<footer>Сгенерировано {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Максимальные значения — только наблюдавшиеся пределы на текущем хосте и Docker runtime.</footer></main></body></html>"""
(BENCH / "index.html").write_text(page, encoding="utf-8")
print(BENCH / "recommended-settings-q4kv-20260929.json")
print(BENCH / "index.html")
print(recommended_yaml)
