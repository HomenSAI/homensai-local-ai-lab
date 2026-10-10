#!/usr/bin/env python3
"""One-time setup of the local Git service for the model-test reports (run from ai-server/):  python scripts/setup_git.py

Starts Gitea, creates the admin user, an access token for the versioner, an SSH key for you, and the empty repository.
Secrets are written to secrets/ (ignored by Git, not part of the Drive backup): gitea-admin.txt, gitea-token, id_ed25519(.pub).
Safe to run again: existing user / repository / key are reused.
"""
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / "secrets"
ENV = {}
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        key, _, value = line.partition("=")
        ENV[key.strip()] = value.strip()
USER = ENV.get("GITEA_REPORT_OWNER", "reports-admin")
REPO = ENV.get("GITEA_REPORT_REPO", "model-test-reports")
PORT = ENV.get("GITEA_WEB_PORT", "3001")
API = f"http://127.0.0.1:{PORT}/api/v1"


def run(*args, check=True, **kw):
    done = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, **kw)
    if check and done.returncode:
        sys.exit(f"{' '.join(args[:4])} failed (rc={done.returncode}): {done.stderr.strip()[-600:]}")
    return done


def docker_exec(*cmd, check=True):
    return run("docker", "exec", "ai-gitea", *cmd, check=check)


def api(method, path, body=None, auth=None):
    request = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", **({"Authorization": auth} if auth else {})})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
            return response.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:300]


def main():
    SECRETS.mkdir(exist_ok=True)
    token_file, admin_file = SECRETS / "gitea-token", SECRETS / "gitea-admin.txt"
    if not token_file.exists():
        token_file.write_text("", encoding="utf-8")
    run("docker", "compose", "up", "-d", "gitea")
    for _ in range(60):
        if run("docker", "inspect", "-f", "{{.State.Health.Status}}", "ai-gitea", check=False).stdout.strip() == "healthy":
            break
        time.sleep(3)
    else:
        sys.exit("gitea did not become healthy; see: docker logs ai-gitea")

    password = None
    if admin_file.exists():
        for line in admin_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("password:"):
                password = line.split(":", 1)[1].strip()
    if not password:
        password = secrets.token_urlsafe(24)
        created = docker_exec("gitea", "admin", "user", "create", "--admin", "--username", USER, "--password", password,
                              "--email", f"{USER}@local.invalid", "--must-change-password=false", check=False)
        if created.returncode and "already exists" not in created.stderr + created.stdout:
            sys.exit("user creation failed: " + created.stderr.strip()[:300])
        if created.returncode:  # user exists but the password file is lost: set a new password
            docker_exec("gitea", "admin", "user", "change-password", "--username", USER, "--password", password, "--must-change-password=false")
        admin_file.write_text(f"user: {USER}\npassword: {password}\nweb: http://127.0.0.1:{PORT}/\n", encoding="utf-8")

    import base64
    basic = "Basic " + base64.b64encode(f"{USER}:{password}".encode()).decode()
    if not token_file.read_text(encoding="utf-8").strip():
        name = "versioner-" + time.strftime("%Y%m%d%H%M%S")
        status, data = api("POST", f"/users/{USER}/tokens", {"name": name, "scopes": ["write:repository", "read:repository", "write:user", "read:user"]}, basic)
        if status not in (200, 201):
            sys.exit(f"token creation failed: {status} {data}")
        token_file.write_text(data["sha1"], encoding="utf-8")
    token = "token " + token_file.read_text(encoding="utf-8").strip()

    status, _ = api("GET", f"/repos/{USER}/{REPO}", auth=token)
    if status == 404:
        status, data = api("POST", "/user/repos", {"name": REPO, "private": True, "auto_init": False, "default_branch": "main",
                                                  "description": "Версии отчётов тестирования локальных ИИ-моделей (создаёт report-versioner)"}, token)
        if status not in (200, 201):
            sys.exit(f"repository creation failed: {status} {data}")

    key = SECRETS / "id_ed25519"
    if not key.exists() and shutil.which("ssh-keygen"):
        run("ssh-keygen", "-t", "ed25519", "-N", "", "-C", "model-test-reports", "-f", str(key))
    if key.exists():  # the key is only for cloning the versions yourself; the versioner uses the token
        public = (SECRETS / "id_ed25519.pub").read_text(encoding="utf-8").strip()
        status, keys = api("GET", "/user/keys", auth=token)
        if status == 200 and not any(k.get("key", "").split()[:2] == public.split()[:2] for k in keys):
            api("POST", "/user/keys", {"title": "workstation", "key": public}, token)
    else:
        print("[warn] ssh-keygen not found: no SSH key created. The versioner works without it; clone the versions over "
              f"HTTP with the login in secrets/gitea-admin.txt (http://127.0.0.1:{PORT}/{USER}/{REPO}.git).")

    run("docker", "compose", "up", "-d", "report-versioner")   # built by `install.py build`; built here only if missing
    ip = ENV.get("AI_CONSOLE_BIND_IP", "127.0.0.1")
    print(f"""Git is ready.
  Web:   http://{ip}:{PORT}/   (login data are in secrets/gitea-admin.txt)
  Repo:  {USER}/{REPO}
  Clone: git clone -c core.sshCommand="ssh -i secrets/id_ed25519 -o StrictHostKeyChecking=accept-new -p {ENV.get('GITEA_SSH_PORT', '2222')}" ssh://git@127.0.0.1:{ENV.get('GITEA_SSH_PORT', '2222')}/{USER}/{REPO}.git
  Versions: tags v0001, v0002 ... (every change), stage-<id>-done, final-<date>""")


if __name__ == "__main__":
    main()
