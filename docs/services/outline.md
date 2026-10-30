# Outline Deployment

## Status

Outline runs as `ip30-outline-path:1.12.0-r1` with PostgreSQL and Redis. The custom image is built from upstream Outline `v1.12.0` and verifies commit `09f11188b87b0220fa318dfa6fdd0fa9772195dd`. Its patch derives the browser history basename from the public `URL` path; the runtime image retains the upstream `LICENSE`.

The public URL is `https://<server-ip>/outline` through Caddy. Caddy strips the `/outline` prefix for the upstream application and routes required root-relative assets/API requests. The direct host port `18082` remains published; restrict it to trusted networks.

## Deployment

The Outline Compose project and custom image build files are under `deploy/outline/`. Configure `OUTLINE_URL=https://<server-ip>/outline`, the Dex client settings, and the Caddy CA bind source in the protected server `.env`. Build and start the application with:

```sh
cd /opt/ip30slave/outline
sudo docker compose --env-file .env -f compose.yaml config -q
sudo docker compose --env-file .env -f compose.yaml build outline
sudo docker compose --env-file .env -f compose.yaml up -d --no-deps outline
```

## Identity and mail

Outline has no native LDAP integration, so it uses Dex OIDC. The registered callback is `https://<server-ip>/outline/auth/oidc.callback`. Outline's login button requests the upstream root path `/auth/oidc`; Caddy aliases that exact path to Outline, which redirects to Dex. The Node.js container trusts the Caddy root through `NODE_EXTRA_CA_CERTS`. Dex maps LLDAP `mail` to OIDC email.

SMTP uses `mailserver:25` without TLS or authentication on the private candidate network. A test message was delivered to the postmaster mailbox and removed.

## Validation and limits

The container is healthy. `/outline` redirects to `/outline/`; a fresh browser following the index link remained under `/outline/` and displayed the login page. Clicking “Continue with Dex (LLDAP)” reached `/dex/auth/lldap/login` without an internal-server error.

No employee credentials were used for an interactive login. Employee browsers must trust the Caddy internal root CA. The old origin-wide Outline service worker is retired by a Caddy unregister script at `/static/sw.js`; existing browsers may need a hard reload or site-data clear.
