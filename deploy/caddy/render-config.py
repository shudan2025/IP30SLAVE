#!/usr/bin/env python3
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


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run this script as root.")

    issuer = read_env(ROOT / "dex" / ".env")["DEX_OIDC_ISSUER"].rstrip("/")
    issuer_url = urlsplit(issuer)
    if issuer_url.scheme != "https" or not issuer_url.hostname:
        raise SystemExit("DEX_OIDC_ISSUER must be an HTTPS URL.")
    if issuer_url.path.rstrip("/") != "/dex" or issuer_url.port not in (None, 443):
        raise SystemExit("DEX_OIDC_ISSUER must use the /dex path on HTTPS port 443.")

    host = issuer_url.hostname
    caddy_host = f"[{host}]" if ":" in host else host
    directory = ROOT / "caddy"
    directory.mkdir(mode=0o755, parents=True, exist_ok=True)

    caddyfile = directory / "Caddyfile"
    temporary_caddyfile = directory / "Caddyfile.tmp"
    temporary_caddyfile.write_text(
        f"{{\n    admin off\n    default_sni {caddy_host}\n    auto_https disable_redirects\n}}\n\n"
        f"http://{caddy_host} {{\n"
        f"    redir https://{caddy_host}{{uri}} 308\n"
        "}\n\n"
        f"https://{caddy_host}:5556 {{\n"
        "    tls internal\n"
        "    @dex_path path /dex /dex/*\n"
        "    handle @dex_path {\n"
        f"        redir https://{caddy_host}{{uri}} 308\n"
        "    }\n"
        "    handle {\n"
        f"        redir https://{caddy_host}/dex{{uri}} 308\n"
        "    }\n"
        "}\n\n"
        f"https://{caddy_host} {{\n"
        "    tls internal\n"
        "    route {\n"
        "        @dex_path path /dex /dex/*\n"
        "        handle @dex_path {\n"
        "            reverse_proxy dex:5556\n"
        "        }\n"
        "        @gitlab path /gitlab /gitlab/*\n"
        "        handle @gitlab {\n"
        "            reverse_proxy gitlab:80 {\n"
        "                header_up X-Forwarded-Ssl on\n"
        "            }\n"
        "        }\n"
        "        @svn path /svn /svn/*\n"
        "        @svn_no_slash path /svn\n"
        "        handle @svn_no_slash {\n"
        f"            redir https://{caddy_host}/svn/ 308\n"
        "        }\n"
        "        handle @svn {\n"
        "            reverse_proxy svn:80\n"
        "        }\n"
        "        @outline path /outline /outline/*\n"
        "        @outline_no_slash path /outline\n"
        "        handle @outline_no_slash {\n"
        f"            redir https://{caddy_host}/outline/ 308\n"
        "        }\n"
        "        handle @outline {\n"
        "            uri strip_prefix /outline\n"
        "            reverse_proxy outline:3000 {\n"
        "                header_up X-Forwarded-Prefix /outline\n"
        "            }\n"
        "        }\n"
        "        @outline_oidc path /auth/oidc\n"
        "        handle @outline_oidc {\n"
        "            reverse_proxy outline:3000 {\n"
        "                header_up X-Forwarded-Prefix /outline\n"
        "            }\n"
        "        }\n"
        "        @ldap path /ldap /ldap/*\n"
        "        @ldap_no_slash path /ldap\n"
        "        handle @ldap_no_slash {\n"
        f"            redir https://{caddy_host}/ldap/ 308\n"
        "        }\n"
        "        handle @ldap {\n"
        "            uri strip_prefix /ldap\n"
        "            reverse_proxy lldap-path-proxy:8080 {\n"
        "                header_up X-Forwarded-Prefix /ldap\n"
        "            }\n"
        "        }\n"
        "        @outline_sw path /static/sw.js\n"
        "        handle @outline_sw {\n"
        "            root * /srv\n"
        "            rewrite * /unregister-outline-sw.js\n"
        "            header Service-Worker-Allowed /\n"
        "            header Cache-Control no-cache\n"
        "            file_server\n"
        "        }\n"
        "        @outline_assets path /static/assets/* /images/* /sw.js /s /s/* /share /share/* /documents/* /collections/* /settings /settings/*\n"
        "        handle @outline_assets {\n"
        "            reverse_proxy outline:3000\n"
        "        }\n"
        "        @outline_api path /api/*\n"
        "        handle @outline_api {\n"
        "            reverse_proxy outline:3000\n"
        "        }\n"
        "        handle {\n"
        "            root * /srv\n"
        "            header Cache-Control no-store\n"
        "            file_server\n"
        "        }\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    os.chmod(temporary_caddyfile, 0o644)
    temporary_caddyfile.replace(caddyfile)

    template = (directory / "index.html.template").read_text(encoding="utf-8")
    temporary_index = directory / "index.html.tmp"
    temporary_index.write_text(
        template.replace("{{SERVER_HOST}}", caddy_host),
        encoding="utf-8",
    )
    os.chmod(temporary_index, 0o644)
    temporary_index.replace(directory / "index.html")
    print("Caddy routes and the service index rendered.")


if __name__ == "__main__":
    main()
