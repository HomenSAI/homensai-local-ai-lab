# Security policy

## Threat model

The console (port 8766) and the gateway (port 8080) are built for `127.0.0.1` or a **trusted LAN**. They are not hardened for the internet. **Never publish ports 8766, 8080, 3010 or 8767 to the internet**; restrict the firewall rule to your own subnet.

What the console does to protect itself (`console/security.py`, `console/container_server.py`):

| Threat | Protection |
|---|---|
| A web page in the operator's browser starts, stops or unloads models (cross-site request forgery) | Every `POST` must be `Content-Type: application/json` (a foreign page cannot send that without a CORS preflight, which the console never allows), must not come from another origin (`Origin`, `Sec-Fetch-Site` are checked) and answers `415` / `403` otherwise |
| DNS rebinding (a foreign host name that points to your PC) | Only `localhost`, IP addresses and the names in `AI_CONSOLE_ALLOWED_HOSTS` are accepted as `Host`; anything else gets `421` (`/health` is exempt for the container health check) |
| Another person on the LAN uses the console | Set `AI_CONSOLE_PASSWORD` in `.env`: the console then asks for HTTP Basic authentication (any user name) on everything except `/health`. Use it whenever `AI_CONSOLE_BIND_IP` is not `127.0.0.1`. Basic authentication sends the password unencrypted: on an untrusted network put a TLS reverse proxy or a VPN in front |
| Framing, content sniffing, injected scripts | Every answer carries `Content-Security-Policy` (own scripts only, no framing), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` |
| Path traversal in `/report/` and `/legal/` | Paths are resolved and must stay inside the folder; tested |
| The Docker socket | See below |

### The Docker socket

The console container mounts `/var/run/docker.sock`. The `read_only` flag on that mount is **not** a security boundary, and the socket is equivalent to root on the host. The console uses it to list containers and to run one fixed command inside a model container (`curl` against the `/health`, `/slots` or `/metrics` address of `llama-server` on `127.0.0.1`). The code refuses any other command: the container name must be a plain Docker name and the URL must match that fixed form (`docker_exec_read`, covered by tests). The container runs with `cap_drop: ALL`, `no-new-privileges` and a read-only root file system. Even so, **whoever gets full control of the console gets Docker on this PC**, so keep the network exposure small and set the password.

### Known limits

- The gateway (llama-swap, port 8080) has no authentication at all; it is published on `127.0.0.1` only. Do not change that without a reverse proxy that authenticates.
- `scripts/setup_git.py` passes the generated Gitea admin password to `docker exec` on the command line once; other users of the Docker daemon on the same PC can see it for a moment. The password is stored in `secrets/gitea-admin.txt` (ignored by Git).
- Basic authentication has no rate limit and no lock-out.

## What the repository must never contain

Passwords, tokens, SSH keys (the folder `secrets/` is ignored by Git), `.env` with personal values (only `.env.example` is committed; `.env` is ignored, which is why `AI_CONSOLE_PASSWORD` may live there), model weights, personal data. If you find any, please report it as below.

## Reporting a vulnerability

Please do **not** open a public issue for security problems. Write to info@homensai.com (author: Serhii Khomenko, <https://homensai.com>) and describe the problem, the affected file and how to reproduce it. You will get an answer as soon as possible; please allow a reasonable time to fix before disclosure.

## Supply chain

Base images, llama.cpp / whisper.cpp / stable-diffusion.cpp commits and llama-swap (release SHA-256) are pinned; model files should be verified against the SHA-256 sums in `MODELS.md` or on the model page before use. `MANIFEST.json` lists the size and SHA-256 of every file of the repository; `python scripts/make_manifest.py --check` verifies it (CI does the same). `python scripts/install.py doctor` never downloads the 5.6 GB CUDA test image unless you pass `--pull`.
