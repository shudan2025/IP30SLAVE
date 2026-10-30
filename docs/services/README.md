# Service Deployment Records

Each active service has its own deployment directory and Compose file, with an environment template where needed. Database and cache containers stay with the application that owns their lifecycle. Dex and Caddy have separate renderers: Dex configuration consumes the service environment files, while Caddy generates its routes and service index from the Dex issuer.

The service-specific Compose files were deployed to `/opt/ip30slave/<service>/` on IP30SLAVE on 2026-10-30. Existing named volumes were reused; no volumes were removed. The former grouped directories remain on the server for rollback, and a root-only configuration archive is stored at `/opt/ip30slave/.deployment-backups/pre-service-layout-20261030-160629.tar.gz`. The GitLab initial-password and test-mailbox password files now reside in their respective service directories. Do not use `--remove-orphans` with a single service-specific file because several files intentionally share their former Compose project name.

For recurring backups, restore drills, and health checks, see the [system maintenance runbook](../operations/maintenance-runbook.md). Its NAS and Restic prerequisites are not yet configured on the server.

## Active services

| Service | Compose file | Deployment record |
|---|---|---|
| Caddy | `deploy/caddy/compose.yaml` | [caddy.md](caddy.md) |
| Dex | `deploy/dex/compose.yaml` | [dex.md](dex.md) |
| GitLab | `deploy/gitlab/compose.yaml` | [gitlab.md](gitlab.md) |
| LLDAP | `deploy/lldap/compose.yaml` | [lldap.md](lldap.md) |
| Mailserver | `deploy/mailserver/compose.yaml` | [mailserver.md](mailserver.md) |
| Outline | `deploy/outline/compose.yaml` | [outline.md](outline.md) |
| SVN | `deploy/svn/compose.yaml` | [svn.md](svn.md) |

## Retired or not deployed

| Service | Status | Record |
|---|---|---|
| OpenLDAP | Container removed; data/config volumes retained | [openldap.md](openldap.md) |
| Wiki.js | Containers removed; PostgreSQL volume retained | [wiki-js.md](wiki-js.md) |
| Plane | Deployment attempt blocked; never started | [plane.md](plane.md) |
