$ErrorActionPreference = 'Stop'
$ContainerName = 'open-webui'
$GatewayBase = 'http://llama-swap-gateway:8080/v1'
$py = @'
import datetime, json, os, re, sqlite3
db_path = "/app/backend/data/webui.db"
backup_dir = "/app/backend/data/config-backups"
os.makedirs(backup_dir, exist_ok=True)
keys = ("openai.api_base_urls", "openai.api_configs", "openai.api_keys")
con = sqlite3.connect(db_path, timeout=30)
con.execute("BEGIN IMMEDIATE")
old = {key: con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()[0] for key in keys}
decoded = {key: json.loads(value) for key, value in old.items()}
urls = decoded[keys[0]]
configs = decoded[keys[1]]
api_keys = decoded[keys[2]]
if any(api_keys):
    con.rollback()
    raise SystemExit("Refusing automatic URL-list rewrite because configured API keys are nonempty; no database changes made.")
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_path = os.path.join(backup_dir, "openai-endpoints-before-llama-swap-" + stamp + ".json")
with open(backup_path, "x", encoding="utf-8") as f:
    json.dump({"created_utc": stamp, "settings": {key: decoded[key] for key in keys}}, f, ensure_ascii=False, indent=2)
stale = re.compile(r"^http://(?:qwen(?:-q5|-vision)?|minicpm|spark|bonsai|dual-minicpm|dual-spark):\d+/v1/?$", re.I)
new_urls, new_configs = [], {}
for index, url in enumerate(urls):
    if stale.match(url):
        continue
    new_configs[str(len(new_urls))] = configs.get(str(index), {})
    new_urls.append(url)
gateway = os.environ.get("AI_GATEWAY_BASE", "http://llama-swap-gateway:8080/v1")
if gateway not in new_urls:
    new_configs[str(len(new_urls))] = {}
    new_urls.append(gateway)
new_keys = [""] * len(new_urls)
values = (new_urls, new_configs, new_keys)
for key, value in zip(keys, values):
    con.execute("UPDATE config SET value=? WHERE key=?", (json.dumps(value, ensure_ascii=False), key))
con.commit()
print("OPENWEBUI_ENDPOINTS_UPDATED=" + str(len(new_urls)))
print("GATEWAY_ENDPOINT=" + gateway)
print("CONFIG_BACKUP=" + backup_path)
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($py))
docker exec -e AI_GATEWAY_BASE=$GatewayBase $ContainerName python3 -c "import base64; exec(base64.b64decode('$encoded'))"
if ($LASTEXITCODE -ne 0) { throw 'Open WebUI connection update failed; see container output. Existing chats and other config were not edited.' }
docker restart $ContainerName
if ($LASTEXITCODE -ne 0) { throw 'Open WebUI settings were saved, but the container restart failed.' }
Write-Output 'Open WebUI restarted with its existing persistent volume. Only stale local OpenAI endpoints were replaced.'
