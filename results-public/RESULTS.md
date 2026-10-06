# Test results / Результаты тестов / Testergebnisse

Server version 1.0.0 · snapshot 2026-10-06T13:50:04Z · NVIDIA GeForce RTX 3080 (10 GB video memory), Windows 10 + Docker Desktop (WSL2)

23 models tested, 15 admitted to the later stages (stable GPU context of at least 64K). How the numbers were produced (server core -> Claude as supervisor -> results): [METHODOLOGY](../docs/METHODOLOGY.en.md) · [RU](../docs/METHODOLOGY.ru.md) · [DE](../docs/METHODOLOGY.de.md).

Data: homensai.com (https://homensai.com), CC BY 4.0. Results are from one machine and from small task sets: use them as a guide, not as a ranking of model quality.

## All models

| Model | Quant | Size, GB | VRAM peak, MiB | Prompt tok/s | Gen tok/s | General % | German % | Stable context, K | Math+Physics % | Chemistry % | Code, of 20 | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bonsai-2-27B | PTQ1_0 | 5.95 | 7640 | 860.5 | 46.6 | 100 | 77 | 128 | 98 | 100 | 18 | admitted |
| Qwen3-VL-8B | Q4_K_M | 6.19 | 8602 | 3346.1 | 86.7 | 87 | 70 | 64 | 95 | 100 | 17 | admitted |
| Qwen3.5-9B | Q5_K_S | 5.16 | 6127 | 2228.7 | 91.3 | 86 | 73 | 256 | 100 | 100 | 18 | admitted |
| Mistral-Nemo-12B | Q4_K_M | 7.48 | 9565 | 2554.2 | 69.2 | 83 | 60 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| Gemma-4-E4B | Q4_K_M | 5.97 | 5697 | 2029.8 | 94.8 | 79 | 77 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| Llama-3.1-8B | Q4_K_M | 4.92 | 6903 | 3906.4 | 95.9 | 79 | 43 | 64 | 75 | 70 | 15 | admitted |
| Spark-X2.5-4B-Q8 | Q8_0 | 4.38 | 5964 | 3646.6 | 79.3 | 79 | 30 | 256 | 98 | 100 | 14 | admitted |
| Qwen3.5-9B-MTP | UD-Q4_K_XL | 7.05 | 8136 | 2048.3 | 82.4 | 78 | 73 | 256 | 98 | 100 | 17 | admitted |
| Gemma-3-12B | Q4_K_M | 7.3 | 9469 | 1569.9 | 61.8 | 73 | 70 | 96 | 92 | 100 | 14 | admitted |
| Gemma-4-12B-QAT | QAT Q4_0 | 7.15 | 9112 | 1315.5 | 61.9 | 73 | 70 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| Qwen2.5-Coder-7B | Q4_K_M | 4.68 | 6155 | 3688.4 | 100.8 | 73 | 53 | 64 | 88 | 90 | 14 | admitted |
| MiMo-9B | Q4_K_M | 5.84 | 6802 | 1943.4 | 82.3 | 72 | 67 | 256 | 95 | 100 | 12 | admitted |
| MiMo-9B-MTP | Q4_K_M+MTP | 6.1 | 6794 | 1912.3 | 81.9 | 72 | 67 | 256 | 95 | 100 | 12 | admitted |
| Ornith-1.5-9B | Q4_K_M | 5.78 | 6574 | 2033.9 | 83.8 | 72 | 73 | 256 | 100 | 100 | 14 | admitted |
| Qwen3-8B | Q4_K_M | 5.03 | 7085 | 3638.6 | 95.7 | 72 | 80 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| Spark-X2.5-4B-Q4 | Q4_K_M | 2.6 | 4303 | 3235.9 | 88.3 | 70 | 23 | 256 | 88 | 100 | 12 | admitted |
| Qwen2.5-VL-7B | Q4_K_M | 6.04 | 8167 | 3875.4 | 101.3 | 68 | 43 | 64 | 78 | 90 | 10 | admitted |
| Gemma-4-12B | Q4_K_M | 7.3 | 9291 | 1405.1 | 60.4 | 66 | 77 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| LFM2.5-8B-A1B | Q4_K_M | 5.16 | 6426 | 5322.4 | 209.8 | 66 | 10 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| MiniCPM5-2B-Q4 | Q4_K_M | 1.56 | 3061 | 7149.6 | 171.6 | 64 | 17 | 128 | 82 | 60 | 12 | admitted |
| MiniCPM5-2B-Q8 | Q8_0 | 2.68 | 3987 | 6596.2 | 138.7 | 59 | 10 | 128 | 82 | 40 | 16 | admitted |
| LFM2.5-2.6B | Q4_K_M | 1.67 | 3155 | 6747.5 | 190.6 | 58 | 13 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |
| R1-Distill-Llama-8B | Q4_K_M | 4.92 | 6967 | 3831.8 | 97.7 | 41 | 20 | - | - | - | - | removed from later tests: no stable GPU context of 64K or more |

## General test, %

| Model | General test, % |
|---|---|
| Bonsai-2-27B | 100 |
| Qwen3-VL-8B | 87 |
| Qwen3.5-9B | 86 |
| Mistral-Nemo-12B | 83 |
| Gemma-4-E4B | 79 |
| Llama-3.1-8B | 79 |
| Spark-X2.5-4B-Q8 | 79 |
| Qwen3.5-9B-MTP | 78 |
| Gemma-3-12B | 73 |
| Gemma-4-12B-QAT | 73 |
| Qwen2.5-Coder-7B | 73 |
| MiMo-9B | 72 |
| MiMo-9B-MTP | 72 |
| Ornith-1.5-9B | 72 |
| Qwen3-8B | 72 |
| Spark-X2.5-4B-Q4 | 70 |
| Qwen2.5-VL-7B | 68 |
| Gemma-4-12B | 66 |
| LFM2.5-8B-A1B | 66 |
| MiniCPM5-2B-Q4 | 64 |
| MiniCPM5-2B-Q8 | 59 |
| LFM2.5-2.6B | 58 |
| R1-Distill-Llama-8B | 41 |


## German, %

| Model | German, % |
|---|---|
| Qwen3-8B | 80 |
| Bonsai-2-27B | 77 |
| Gemma-4-E4B | 77 |
| Gemma-4-12B | 77 |
| Qwen3.5-9B | 73 |
| Qwen3.5-9B-MTP | 73 |
| Ornith-1.5-9B | 73 |
| Qwen3-VL-8B | 70 |
| Gemma-3-12B | 70 |
| Gemma-4-12B-QAT | 70 |
| MiMo-9B | 67 |
| MiMo-9B-MTP | 67 |
| Mistral-Nemo-12B | 60 |
| Qwen2.5-Coder-7B | 53 |
| Llama-3.1-8B | 43 |
| Qwen2.5-VL-7B | 43 |
| Spark-X2.5-4B-Q8 | 30 |
| Spark-X2.5-4B-Q4 | 23 |
| R1-Distill-Llama-8B | 20 |
| MiniCPM5-2B-Q4 | 17 |
| LFM2.5-2.6B | 13 |
| LFM2.5-8B-A1B | 10 |
| MiniCPM5-2B-Q8 | 10 |


## Stable context, K

| Model | Stable context, K |
|---|---|
| Qwen3.5-9B | 256 |
| Spark-X2.5-4B-Q8 | 256 |
| Qwen3.5-9B-MTP | 256 |
| MiMo-9B | 256 |
| MiMo-9B-MTP | 256 |
| Ornith-1.5-9B | 256 |
| Spark-X2.5-4B-Q4 | 256 |
| Bonsai-2-27B | 128 |
| MiniCPM5-2B-Q4 | 128 |
| MiniCPM5-2B-Q8 | 128 |
| Gemma-3-12B | 96 |
| Qwen3-VL-8B | 64 |
| Llama-3.1-8B | 64 |
| Qwen2.5-Coder-7B | 64 |
| Qwen2.5-VL-7B | 64 |


## Math + Physics, %

| Model | Math + Physics, % |
|---|---|
| Qwen3.5-9B | 100 |
| Ornith-1.5-9B | 100 |
| Bonsai-2-27B | 98 |
| Spark-X2.5-4B-Q8 | 98 |
| Qwen3.5-9B-MTP | 98 |
| Qwen3-VL-8B | 95 |
| MiMo-9B | 95 |
| MiMo-9B-MTP | 95 |
| Gemma-3-12B | 92 |
| Qwen2.5-Coder-7B | 88 |
| Spark-X2.5-4B-Q4 | 88 |
| MiniCPM5-2B-Q4 | 82 |
| MiniCPM5-2B-Q8 | 82 |
| Qwen2.5-VL-7B | 78 |
| Llama-3.1-8B | 75 |


## Chemistry, %

| Model | Chemistry, % |
|---|---|
| Bonsai-2-27B | 100 |
| Qwen3-VL-8B | 100 |
| Qwen3.5-9B | 100 |
| Spark-X2.5-4B-Q8 | 100 |
| Qwen3.5-9B-MTP | 100 |
| Gemma-3-12B | 100 |
| MiMo-9B | 100 |
| MiMo-9B-MTP | 100 |
| Ornith-1.5-9B | 100 |
| Spark-X2.5-4B-Q4 | 100 |
| Qwen2.5-Coder-7B | 90 |
| Qwen2.5-VL-7B | 90 |
| Llama-3.1-8B | 70 |
| MiniCPM5-2B-Q4 | 60 |
| MiniCPM5-2B-Q8 | 40 |


## Code, of 20

| Model | Code, of 20 |
|---|---|
| Bonsai-2-27B | 18 |
| Qwen3.5-9B | 18 |
| Qwen3-VL-8B | 17 |
| Qwen3.5-9B-MTP | 17 |
| MiniCPM5-2B-Q8 | 16 |
| Llama-3.1-8B | 15 |
| Spark-X2.5-4B-Q8 | 14 |
| Gemma-3-12B | 14 |
| Qwen2.5-Coder-7B | 14 |
| Ornith-1.5-9B | 14 |
| MiMo-9B | 12 |
| MiMo-9B-MTP | 12 |
| Spark-X2.5-4B-Q4 | 12 |
| MiniCPM5-2B-Q4 | 12 |
| Qwen2.5-VL-7B | 10 |


## Generation speed, tok/s

| Model | Generation speed, tok/s |
|---|---|
| LFM2.5-8B-A1B | 209.8 |
| LFM2.5-2.6B | 190.6 |
| MiniCPM5-2B-Q4 | 171.6 |
| MiniCPM5-2B-Q8 | 138.7 |
| Qwen2.5-VL-7B | 101.3 |
| Qwen2.5-Coder-7B | 100.8 |
| R1-Distill-Llama-8B | 97.7 |
| Llama-3.1-8B | 95.9 |
| Qwen3-8B | 95.7 |
| Gemma-4-E4B | 94.8 |
| Qwen3.5-9B | 91.3 |
| Spark-X2.5-4B-Q4 | 88.3 |
| Qwen3-VL-8B | 86.7 |
| Ornith-1.5-9B | 83.8 |
| Qwen3.5-9B-MTP | 82.4 |
| MiMo-9B | 82.3 |
| MiMo-9B-MTP | 81.9 |
| Spark-X2.5-4B-Q8 | 79.3 |
| Mistral-Nemo-12B | 69.2 |
| Gemma-4-12B-QAT | 61.9 |
| Gemma-3-12B | 61.8 |
| Gemma-4-12B | 60.4 |
| Bonsai-2-27B | 46.6 |

