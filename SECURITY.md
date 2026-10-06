# Security policy

## Threat model

The console (port 8766) and the gateway (port 8080) have **no authentication** and are meant for `127.0.0.1` or a trusted LAN. The console container mounts `/var/run/docker.sock` to list containers (its code makes read calls only; the read-only flag is not a security boundary), so access to the console is access to Docker on that PC. **Never publish these ports to the internet**; restrict the firewall rule to your own subnet.

## What the repository must never contain

Passwords, tokens, SSH keys (the folder `secrets/` is ignored by Git), `.env` with personal values (only `.env.example` is committed), model weights, personal data. If you find any, please report it as below.

## Reporting a vulnerability

Please do **not** open a public issue for security problems. Write to info@homensai.com (author: Serhii Khomenko, <https://homensai.com>) and describe the problem, the affected file and how to reproduce it. You will get an answer as soon as possible; please allow a reasonable time to fix before disclosure.

## Supply chain

Base images, llama.cpp / whisper.cpp / stable-diffusion.cpp commits and llama-swap (release SHA-256) are pinned; model files should be verified against the SHA-256 sums in `MODELS.md` or on the model page before use.
