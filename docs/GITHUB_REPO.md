# Repository page (copy these into GitHub)

## About (the one-line description field, 350 characters max)

**English:** Local AI server for one NVIDIA GPU: llama-swap gateway, web console in English/German/Russian, automatic test reports with versioned results (Git), operated and supervised by an AI assistant (Claude or ChatGPT). Author: Serhii Khomenko, homensai.com

**Русский:** Локальный ИИ-сервер для одной видеокарты NVIDIA: шлюз llama-swap, веб-консоль на русском/английском/немецком, автоматические отчёты по тестам с версиями результатов (Git); устанавливается и контролируется ИИ-ассистентом (Claude или ChatGPT). Автор: Serhii Khomenko, homensai.com

**Deutsch:** Lokaler KI-Server für eine NVIDIA-GPU: llama-swap-Gateway, Web-Konsole auf Deutsch/Englisch/Russisch, automatische Testberichte mit versionierten Ergebnissen (Git); von einem KI-Assistenten (Claude oder ChatGPT) installiert und überwacht. Autor: Serhii Khomenko, homensai.com

## Names and account

- Account: `HomenSAI` (https://github.com/HomenSAI)
- PC-test repository: `homensai-local-ai-lab` -> https://github.com/HomenSAI/homensai-local-ai-lab
- Video repository: `homensai-video-studio` -> https://github.com/HomenSAI/homensai-video-studio
- Author and contact: Serhii Khomenko, https://homensai.com, info@homensai.com

## Website field

`https://homensai.com`

## Topics

`llm` `local-llm` `llama-cpp` `llama-swap` `gguf` `nvidia` `rtx-3080` `docker` `benchmark` `llm-benchmark` `self-hosted` `openai-compatible` `ai-operator` `claude` `chatgpt` `multilingual` `german` `russian`

## Suggested social-preview text

"One GPU, many local models, honest numbers: gateway + console + reports + Git history, run by your AI assistant."

## Suggested first release

- Tag `v1.0.0`, title "Local AI Server 1.0.0".
- Text: copy the 1.0.0 section of `CHANGELOG.md`; add: results snapshot in `results-public/`, methodology in `docs/METHODOLOGY.en.md`, installation by an AI assistant in `docs/AI_OPERATOR.en.md`.
- License line: results and texts CC BY 4.0 (credit to https://homensai.com required), code MIT.

## After the repository is public

1. Put its address into `.env` as `PUBLIC_REPO_URL=https://github.com/HomenSAI/homensai-local-ai-lab` (the console and report footers then show a "GitHub" link) and into the README clone commands.
2. Link the two projects to each other (this repository: "PC test"; the other: "Video Studio") in both READMEs.
3. Enable "Private vulnerability reporting" in the repository settings (see `SECURITY.md`).
