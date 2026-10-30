# LLDAP Deployment

## Status

LLDAP is the only active directory service in the candidate stack. The OpenLDAP container was retired; its data/config volumes remain on the host but are no longer mounted. LLDAP uses `lldap/lldap:stable` in `deploy/lldap/compose.yaml`; pin a tested image digest before production.

## Deployment

Copy the `deploy/lldap/` directory to the LLDAP deployment directory. Create its server `.env` from `.env.example`, set unique secrets and `LLDAP_HTTP_URL=https://<server-ip>/ldap`, and keep the file root-owned with mode `0600`.

```sh
cd /opt/ip30slave/lldap
sudo docker compose --env-file .env -f compose.yaml config -q
sudo docker compose --env-file .env -f compose.yaml up -d
```

Start Mailserver after LLDAP has created the shared mail network. Its TLS files and test mailbox setup are documented in [mailserver.md](mailserver.md).

## Endpoints and path routing

The server publishes LDAP on host port `13890` (container port `3890`) and the web UI on host port `17170`. The public web URL is `https://<server-ip>/ldap/`; set `LLDAP_HTTP_URL=https://<server-ip>/ldap` in the protected LLDAP `.env`.

Caddy routes `/ldap/` through `lldap-path-proxy`. The Nginx adapter injects `<base href="/ldap/">` and rewrites root-relative static asset URLs. `/ldap` redirects to `/ldap/`. The LLDAP UI also remains directly reachable over plain HTTP at `http://<server-ip>:17170/`; restrict this port to trusted networks.

Raw LDAP is TCP, not an HTTP path. Applications connect to `lldap:3890` on the private `ip30-lldap-apps` network.

## Mail and integrations

LLDAP password-reset email is enabled and uses `mailserver:25` on the private `ip30-lldap-mail` network. This candidate relay is unauthenticated and unencrypted; do not expose it to untrusted networks. Reset links use `LLDAP_HTTP_URL`.

GitLab uses `mail` for LDAP login. Dex also searches by `mail`; Outline uses Dex OIDC rather than LDAP directly. SVN authenticates by email and maps the authenticated identity back to `uid` for repository authorization. LLDAP is a candidate directory, not yet a production identity service; account recovery, backups, TLS, and all required integrations need production validation.

The built-in `admin` account currently has no `mail` attribute. It works as a directory bind account but cannot log into email-only applications until its profile is completed.

## Validation

The container reported healthy. Through Caddy, `/ldap` redirects to `/ldap/`, the page advertises `/ldap/` as its base path, `/ldap/static/main.js` returns HTTP 200, and a fresh browser reaches `/ldap/login`. Email password-reset configuration is present; a complete employee password-reset flow was not tested.
