# Sicherheitsrichtlinie

Andere Sprachen: [English](SECURITY.md) · [Русский](SECURITY.ru.md)

## Bedrohungsmodell

Die Konsole (Port 8766) und das Gateway (Port 8080) sind für `127.0.0.1` oder ein **vertrauenswürdiges LAN** gebaut. Sie sind nicht für das Internet gehärtet. **Veröffentlichen Sie die Ports 8766, 8080, 3010 oder 8767 nie im Internet**; beschränken Sie die Firewall-Regel auf Ihr eigenes Subnetz.

Wie sich die Konsole schützt (`console/security.py`, `console/container_server.py`):

| Bedrohung | Schutz |
|---|---|
| Eine Webseite im Browser des Bedieners startet, stoppt oder entlädt Modelle (seitenübergreifende Anfragefälschung) | Jeder `POST` muss `Content-Type: application/json` haben (eine fremde Seite kann das nicht ohne CORS-Preflight senden, den die Konsole nie erlaubt), darf nicht von einem anderen Ursprung kommen (`Origin`, `Sec-Fetch-Site` werden geprüft) und wird sonst mit `415` / `403` beantwortet |
| DNS-Rebinding (ein fremder Hostname, der auf Ihren PC zeigt) | Als `Host` werden nur `localhost`, IP-Adressen und die Namen in `AI_CONSOLE_ALLOWED_HOSTS` akzeptiert; alles andere erhält `421` (`/health` ist für die Zustandsprüfung des Containers ausgenommen) |
| Eine andere Person im LAN benutzt die Konsole | `AI_CONSOLE_PASSWORD` in `.env` setzen: Die Konsole verlangt dann HTTP-Basic-Authentifizierung (beliebiger Benutzername) für alles außer `/health`. Immer verwenden, wenn `AI_CONSOLE_BIND_IP` nicht `127.0.0.1` ist. Basic-Authentifizierung sendet das Passwort unverschlüsselt: In einem nicht vertrauenswürdigen Netz einen TLS-Reverse-Proxy oder ein VPN davorschalten |
| Einbetten in Frames, Content-Sniffing, eingeschleuste Skripte | Jede Antwort trägt `Content-Security-Policy` (nur eigene Skripte, keine Frames), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` |
| Path Traversal in `/report/` und `/legal/` | Pfade werden aufgelöst und müssen innerhalb des Ordners bleiben; getestet |
| Der Docker-Socket | Siehe unten |

### Der Docker-Socket

Der Konsolen-Container bindet `/var/run/docker.sock` ein. Das `read_only`-Flag dieser Einbindung ist **keine** Sicherheitsgrenze, und der Socket ist gleichbedeutend mit Root auf dem Host. Die Konsole nutzt ihn, um Container aufzulisten und einen festen Befehl in einem Modell-Container auszuführen (`curl` gegen die Adresse `/health`, `/slots` oder `/metrics` von `llama-server` auf `127.0.0.1`). Jeden anderen Befehl lehnt der Code ab: Der Containername muss ein einfacher Docker-Name sein und die URL muss dieser festen Form entsprechen (`docker_exec_read`, durch Tests abgedeckt). Der Container läuft mit `cap_drop: ALL`, `no-new-privileges` und einem schreibgeschützten Root-Dateisystem. Trotzdem gilt: **Wer die volle Kontrolle über die Konsole erlangt, erhält Docker auf diesem PC**, halten Sie die Erreichbarkeit im Netz also gering und setzen Sie das Passwort.

### Bekannte Grenzen

- Das Gateway (llama-swap, Port 8080) hat überhaupt keine Authentifizierung; es ist nur auf `127.0.0.1` veröffentlicht. Ändern Sie das nicht ohne einen Reverse-Proxy, der authentifiziert.
- `scripts/setup_git.py` übergibt das erzeugte Gitea-Administratorpasswort einmal auf der Befehlszeile an `docker exec`; andere Benutzer des Docker-Daemons auf demselben PC können es kurz sehen. Das Passwort wird in `secrets/gitea-admin.txt` gespeichert (von Git ignoriert).
- Die Basic-Authentifizierung hat keine Ratenbegrenzung und keine Sperre.

## Was das Repository nie enthalten darf

Passwörter, Tokens, SSH-Schlüssel (der Ordner `secrets/` wird von Git ignoriert), `.env` mit persönlichen Werten (nur `.env.example` wird committet; `.env` wird ignoriert, deshalb darf `AI_CONSOLE_PASSWORD` dort stehen), Modellgewichte, personenbezogene Daten. Wenn Sie so etwas finden, melden Sie es bitte wie unten beschrieben.

## Eine Schwachstelle melden

Bitte öffnen Sie für Sicherheitsprobleme **kein** öffentliches Issue. Schreiben Sie an info@homensai.com (Autor: Serhii Khomenko, <https://homensai.com>) und beschreiben Sie das Problem, die betroffene Datei und wie es sich reproduzieren lässt. Sie erhalten so bald wie möglich eine Antwort; bitte geben Sie vor einer Veröffentlichung angemessen Zeit für die Behebung.

## Lieferkette

Basis-Images, die Commits von llama.cpp / whisper.cpp / stable-diffusion.cpp und llama-swap (SHA-256 des Releases) sind fest angeheftet; Modelldateien sollten vor der Verwendung mit den SHA-256-Summen in `MODELS.md` oder auf der Modellseite abgeglichen werden. `MANIFEST.json` listet Größe und SHA-256 jeder Datei des Repositorys auf; `python scripts/make_manifest.py --check` prüft sie (CI tut dasselbe). `python scripts/install.py doctor` lädt das 5,6 GB große CUDA-Prüfimage nie herunter, es sei denn, Sie übergeben `--pull`.
