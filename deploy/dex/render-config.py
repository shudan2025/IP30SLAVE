#!/usr/bin/env python3
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path("/opt/ip30slave")


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def quote(value):
    return json.dumps(value)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run this script as root.")

    dex_env = read_env(ROOT / "dex" / ".env")
    lldap_env = read_env(ROOT / "lldap" / ".env")
    gitlab_env = read_env(ROOT / "gitlab" / ".env")
    outline_env = read_env(ROOT / "outline" / ".env")

    issuer = dex_env["DEX_OIDC_ISSUER"].rstrip("/")
    issuer_url = urlsplit(issuer)
    if issuer_url.scheme != "https" or not issuer_url.hostname:
        raise SystemExit("DEX_OIDC_ISSUER must be an HTTPS URL.")
    if issuer_url.path.rstrip("/") != "/dex" or issuer_url.port not in (None, 443):
        raise SystemExit("DEX_OIDC_ISSUER must use the /dex path on HTTPS port 443.")
    for service, environment in (("GitLab", gitlab_env), ("Outline", outline_env)):
        if environment["DEX_OIDC_ISSUER"].rstrip("/") != issuer:
            raise SystemExit(f"{service} DEX_OIDC_ISSUER must match Dex.")
    ldap_dn = "uid=admin,ou=people,dc=agigactu,dc=com"
    ldap_password = lldap_env["LLDAP_ADMIN_PASSWORD"]

    clients = [
        {
            "id": gitlab_env["GITLAB_OIDC_CLIENT_ID"],
            "name": "GitLab",
            "secret": gitlab_env["GITLAB_OIDC_CLIENT_SECRET"],
            "redirect_uri": gitlab_env["GITLAB_OIDC_REDIRECT_URI"],
        },
        {
            "id": outline_env["OUTLINE_OIDC_CLIENT_ID"],
            "name": "Outline",
            "secret": outline_env["OUTLINE_OIDC_CLIENT_SECRET"],
            "redirect_uri": (
                outline_env["OUTLINE_URL"].rstrip("/") + "/auth/oidc.callback"
            ),
        },
    ]

    lines = [
        f"issuer: {quote(issuer)}",
        "storage:",
        "  type: sqlite3",
        "  config:",
        "    file: /var/dex/dex.db",
        "web:",
        "  http: 0.0.0.0:5556",
        "oauth2:",
        "  skipApprovalScreen: true",
        "connectors:",
        "  - type: ldap",
        "    id: lldap",
        "    name: LLDAP",
        "    config:",
        "      host: lldap:3890",
        "      insecureNoSSL: true",
        f"      bindDN: {quote(ldap_dn)}",
        f"      bindPW: {quote(ldap_password)}",
        "      usernamePrompt: Corporate email",
        "      userSearch:",
        "        baseDN: ou=people,dc=agigactu,dc=com",
        '        filter: "(objectClass=person)"',
        "        username: mail",
        "        idAttr: uid",
        "        emailAttr: mail",
        "        nameAttr: mail",
        "        preferredUsernameAttr: mail",
        "staticClients:",
    ]
    for client in clients:
        lines.extend(
            [
                f"  - id: {quote(client['id'])}",
                f"    name: {quote(client['name'])}",
                f"    secret: {quote(client['secret'])}",
                "    redirectURIs:",
                f"      - {quote(client['redirect_uri'])}",
            ]
        )

    directory = ROOT / "dex"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)

    temporary = directory / "config.yaml.tmp"
    destination = directory / "config.yaml"
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chown(temporary, 1001, 1001)
    os.chmod(temporary, 0o400)
    temporary.replace(destination)
    os.chown(destination, 1001, 1001)
    os.chmod(destination, 0o400)

    print("Dex configuration rendered.")


if __name__ == "__main__":
    main()
