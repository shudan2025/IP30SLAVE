# Dex Deployment

## Status

Active OIDC provider at `https://<server-ip>/dex`, using image `ghcr.io/dexidp/dex:v2.46.1`. Caddy preserves the `/dex` issuer path. Its service-specific Compose file is `deploy/dex/compose.yaml`; its configuration renderer is `deploy/dex/render-config.py`.

## LLDAP integration

Dex connects to `lldap:3890` over the private `ip30-lldap-apps` Docker network. LLDAP TLS is disabled for this candidate, so the LDAP hop is unencrypted inside that network. The connector searches `ou=people,dc=agigactu,dc=com`, uses `mail` for username and email, and uses `mail` for the OIDC name claim.

The `nameAttr` was changed from `cn` to `mail` after an LLDAP entry without the optional `cn` attribute caused an authentication error. Users without a display name therefore receive their email as the OIDC name. No directory profiles were modified to work around the issue.

## OIDC clients

The generated Dex config registers:

- GitLab with its `/gitlab/.../callback` redirect URI.
- Outline with `https://<server-ip>/outline/auth/oidc.callback`.

`render-config.py` reads the server-side Dex, LLDAP, GitLab, and Outline `.env` files and writes the LDAP/OIDC config with restrictive permissions. It verifies the OIDC issuer matches the application settings. Caddy routes are generated separately by `deploy/caddy/render-config.py`. Do not copy secrets into repository files or logs.

## Deployment

Set `DEX_OIDC_ISSUER=https://<server-ip>/dex` in the protected Dex, GitLab, and Outline `.env` files, and set each application's redirect URI before rendering. Then run:

```sh
sudo python3 /opt/ip30slave/dex/render-config.py
cd /opt/ip30slave/dex
sudo docker compose --env-file .env -f compose.yaml config -q
sudo docker compose --env-file .env -f compose.yaml up -d dex
sudo python3 /opt/ip30slave/caddy/render-config.py
sudo python3 /opt/ip30slave/caddy/export-caddy-ca.py
```

The renderer validates that the issuer uses HTTPS and the `/dex` path. Dex state is stored in the `dex-data` volume.

## Validation and limits

`https://<server-ip>/dex/.well-known/openid-configuration` reports the `/dex` issuer and path-prefixed endpoints. GitLab and Outline OIDC initiation reach the Dex login form. An Outline browser test reached `/dex/auth/lldap/login` without an internal-server error. No employee credentials were used for a completed login.

Employee browsers must trust the Caddy internal root CA. The former port `18084` redirects to `/dex` for compatibility.
