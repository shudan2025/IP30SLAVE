# Caddy Deployment

## Status

Active reverse proxy and TLS terminator on `IP30SLAVE`. Its service-specific Compose file is `deploy/caddy/compose.yaml`; `deploy/caddy/render-config.py` generates the Caddyfile and service index from the Dex issuer.

## Deployment

Caddy uses the `caddy:2` image and joins the `ip30-lldap-apps` Docker network so it can reach GitLab, Dex, LLDAP's path adapter, SVN, and Outline. Host ports `80` and `443` bind to all interfaces. The former Dex compatibility port `18084` redirects to `/dex`.

The service-specific deployment is active at `/opt/ip30slave/caddy/`. Render and apply the configuration after syncing the service directories; the former grouped directories remain available for rollback.

```sh
sudo python3 /opt/ip30slave/dex/render-config.py
sudo python3 /opt/ip30slave/caddy/render-config.py
cd /opt/ip30slave/dex
sudo docker compose --env-file .env -f compose.yaml config -q
sudo docker compose --env-file .env -f compose.yaml up -d dex
cd /opt/ip30slave/caddy
sudo docker compose --env-file .env -f compose.yaml config -q
sudo docker compose --env-file .env -f compose.yaml up -d caddy
sudo python3 /opt/ip30slave/caddy/export-caddy-ca.py
```

The index at `https://<server-ip>/` is static and does not proxy to Outline. Caddy redirects HTTP requests on port `80` to HTTPS.

## Routes

| Public path | Upstream behavior |
|---|---|
| `/gitlab` | GitLab; prefix preserved for `GITLAB_RELATIVE_URL_ROOT=/gitlab` |
| `/svn/` | Apache `mod_dav_svn`; prefix preserved |
| `/outline/` | Outline; `/outline` is redirected to `/outline/`, then the prefix is stripped upstream |
| `/auth/oidc` | Exact alias to Outline's upstream OIDC initiation endpoint |
| `/dex` | Dex; issuer prefix preserved |
| `/ldap/` | LLDAP through the Nginx path adapter, which adds the HTML base path and rewrites root-relative assets |

LDAP remains a TCP protocol at `ldap://<server-ip>:13890`; it is not served through an HTTP path.

## TLS and validation

Caddy uses its internal CA. `export-caddy-ca.py` exports the public root certificate to `/opt/ip30slave/caddy/caddy-root.crt` and creates a GitLab CA bundle. Outline and SVN also use the exported root where required. Employee browsers and command-line clients must trust this root certificate; replace the internal CA with an organization-trusted certificate when available.

The service index and routed services were checked over HTTPS. Bare `/svn`, `/outline`, and `/ldap` paths redirect to their slash-terminated forms. See the individual service records for protocol-specific validation and client certificate requirements.
