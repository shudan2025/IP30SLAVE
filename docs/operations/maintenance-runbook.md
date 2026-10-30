# IP30SLAVE Periodic Maintenance Runbook

## Purpose and current readiness

This runbook covers the active IP30SLAVE services: Caddy, Dex, GitLab, LLDAP, Mailserver, Outline, and SVN, including their authoritative data and configuration.

**Backups are not operational yet.** The server currently has no NAS mount at `/mnt/ip30-backups` and Restic is not installed. The commands below assume an approved off-host NAS is mounted there and Restic has been installed from an approved package source. Until both prerequisites are met and a restore drill succeeds, the RPO of 24 hours and RTO of 4 hours are targets, not achieved guarantees. Do not substitute a directory on the same server for the NAS.

The runbook is manual; it does not install software, configure a scheduler, or change server services. The suggested schedule is 02:00 Asia/Shanghai for backups and before 09:00 for the daily check.

## Safety rules

- Run maintenance commands from an authorized administrator session with `sudo` access. Do not print or paste `.env` files, generated Dex configuration, database dumps, mailbox data, private keys, or unredacted logs.
- Restic encrypts repository contents. Retrieve its password from the organization-approved password vault; keep it separate from the NAS and never put it in this document, a command argument, shell history, or repository.
- NAS mount credentials must be held in a root-only credentials file managed by the host. Do not put them in `.env` files or on the command line.
- If the NAS is not mounted, Restic is unavailable, or a required backup fails, stop the backup procedure. Do not fall back to local-only copies, do not prune snapshots, and do not delete staging files.
- If a service was stopped for a backup and any following command fails, start that service before troubleshooting or continuing.
- Never use `docker compose down -v`, `docker volume rm`, `docker volume prune`, or `--remove-orphans` for routine maintenance. Several service-specific Compose files intentionally share project names.
- Restore to an isolated host or empty test volumes first. Never overwrite production data as part of a routine maintenance check.

## Backup policy

| Item | Policy |
|---|---|
| Daily restore points | Keep 7 |
| Weekly restore points | Keep 12 |
| Target RPO | 24 hours |
| Target RTO | 4 hours; confirm with quarterly timed restore drills |
| Backup window | 02:00 Asia/Shanghai |
| Encryption-key custody | Organization password vault, separate from the NAS |
| Failure response | Start any stopped service, retain staging and prior snapshots, pause pruning, and escalate to the IT duty operator |

Use the approved NAS mount at `/mnt/ip30-backups`; the repository path is `/mnt/ip30-backups/ip30slave`. This is a placeholder until the NAS protocol, export/share, and mount are configured.

### One-time prerequisites

1. Configure and test the NAS mount at `/mnt/ip30-backups`. Confirm it mounts after a host reboot and is writable only by authorized administrators. Use the organization's approved NFS or SMB/CIFS configuration; do not place mount credentials in this runbook.
2. Install and pin an approved Restic version. The current server does not have Restic, Borg, or Rclone installed.
3. Retrieve a new Restic repository password through the organization's vault process. Initialize the repository once:

   ```sh
   export RESTIC_REPOSITORY=/mnt/ip30-backups/ip30slave
   read -r -s -p 'Restic repository password: ' RESTIC_PASSWORD
   printf '\n'
   export RESTIC_PASSWORD
   mountpoint -q /mnt/ip30-backups
   restic init
   unset RESTIC_PASSWORD
   ```

   Do not run `restic init` again for an existing repository. A lost repository password makes the encrypted backups unrecoverable.
4. Test one backup and restore on an isolated location before declaring the RPO/RTO operational.

At the start of each maintenance session, run as root and enter the Restic password interactively:

```sh
sudo -i
export RESTIC_REPOSITORY=/mnt/ip30-backups/ip30slave
read -r -s -p 'Restic repository password: ' RESTIC_PASSWORD
printf '\n'
export RESTIC_PASSWORD
mountpoint -q /mnt/ip30-backups || { echo 'NAS is not mounted; aborting.' >&2; exit 1; }
restic snapshots
```

The host-side staging directory contains temporary plaintext dumps. Create it with restrictive permissions, confirm adequate local free space before use, and remove only the completed run directory after the Restic snapshot has been verified. If host policy does not permit temporary plaintext staging, configure encrypted staging before using these commands.

## What to back up

Back up service configuration directories as encrypted Restic data. This includes root-only `.env` files, generated Dex configuration, Caddy routes and exported CA files, GitLab and Mailserver password files, and service-specific configuration such as SVN authorization policy.

| Service | Authoritative data and backup method |
|---|---|
| Caddy | Stop Caddy briefly, then back up `ip30-dex-caddy-data` and `ip30-dex-caddy-config`. The data volume contains the internal CA and private keys; preserve it with the exported CA files. |
| Dex | Stop Dex briefly, then back up `ip30-dex-candidate_dex-data` (SQLite state). Also back up `/opt/ip30slave/dex/` configuration. |
| GitLab | Run the image's native `gitlab:backup:create` task and copy its resulting archive to staging. Back up `/opt/ip30slave/gitlab/`, including its protected configuration. Do not use the Redis cache volume as a data backup. |
| LLDAP | Stop only the LLDAP service, then back up `ip30-base-services_lldap-data`. The path-proxy may remain running. Back up `/opt/ip30slave/lldap/` configuration. |
| Mailserver | Stop Mailserver briefly, then back up `ip30-base-services_mail-data`, `ip30-base-services_mail-state`, `ip30-base-services_mail-logs`, and `ip30-base-services_mail-config`. The configuration volume contains TLS private keys and certificates. |
| Outline | Stop Outline while taking the PostgreSQL dump and copying `ip30-outline-candidate_outline-file-data`. Back up `/opt/ip30slave/outline/`. The PostgreSQL dump is authoritative; Redis is rebuildable cache/queue state. |
| SVN | Use `svnadmin hotcopy` for the live `main` repository. Back up `/opt/ip30slave/svn/`, including `authz` and its protected `.env`. |

The GitLab and Outline PostgreSQL volumes are not to be copied as live filesystem trees. Use the native GitLab backup and an Outline `pg_dump` instead. Redis volumes are excluded as rebuildable state; reassess if a service later stores authoritative data there.

## Daily backup procedure

Run the backup at the agreed window. Do one service at a time when a service must be stopped. A short outage is expected for Caddy, Dex, LLDAP, Mailserver, and Outline; SVN hotcopy and GitLab's native backup run online.

### Prepare and resolve volume paths

```sh
set -euo pipefail
umask 077
STAGE_ROOT=/var/backups/ip30slave/staging
RUN_ID="$(date +%Y%m%dT%H%M%S%z)"
RUN_DIR="$STAGE_ROOT/$RUN_ID"
install -d -m 0700 "$RUN_DIR/gitlab" "$RUN_DIR/outline" "$RUN_DIR/svn"
df -h / "$STAGE_ROOT" /mnt/ip30-backups

volume_path() {
  docker volume inspect --format '{{.Mountpoint}}' "$1"
}

backup_volume() {
  local volume="$1"
  local source
  source="$(volume_path "$volume")"
  test -d "$source" || { printf 'Missing volume path for %s\n' "$volume" >&2; return 1; }
  restic backup --tag daily --tag "volume:$volume" "$source"
}
```

Do not continue if a volume is missing or the NAS/staging filesystem is full.

### Back up stopped-service volumes

Stop only the named service, back up its volume(s), then start it again. If Restic fails, start the service immediately and retain all staging files.

```sh
# Caddy: brief reverse-proxy/TLS interruption
docker compose --env-file /opt/ip30slave/caddy/.env -f /opt/ip30slave/caddy/compose.yaml stop caddy
backup_volume ip30-dex-caddy-data
backup_volume ip30-dex-caddy-config
docker compose --env-file /opt/ip30slave/caddy/.env -f /opt/ip30slave/caddy/compose.yaml start caddy

# Dex: OIDC sign-in is unavailable while stopped
docker compose --env-file /opt/ip30slave/dex/.env -f /opt/ip30slave/dex/compose.yaml stop dex
backup_volume ip30-dex-candidate_dex-data
docker compose --env-file /opt/ip30slave/dex/.env -f /opt/ip30slave/dex/compose.yaml start dex

# LLDAP: directory writes and authentication are unavailable while stopped
docker compose --env-file /opt/ip30slave/lldap/.env -f /opt/ip30slave/lldap/compose.yaml stop lldap
backup_volume ip30-base-services_lldap-data
docker compose --env-file /opt/ip30slave/lldap/.env -f /opt/ip30slave/lldap/compose.yaml start lldap

# Mailserver: mail delivery and access are unavailable while stopped
docker compose -f /opt/ip30slave/mailserver/compose.yaml stop mailserver
backup_volume ip30-base-services_mail-data
backup_volume ip30-base-services_mail-state
backup_volume ip30-base-services_mail-logs
backup_volume ip30-base-services_mail-config
docker compose -f /opt/ip30slave/mailserver/compose.yaml start mailserver
```

### GitLab native backup

The GitLab image supports its Rake backup task. Keep GitLab running, copy the new archive out of its data volume, and let Restic encrypt it:

```sh
docker compose --env-file /opt/ip30slave/gitlab/.env \
  -f /opt/ip30slave/gitlab/compose.yaml \
  run --rm --no-deps gitlab app:rake gitlab:backup:create

GITLAB_ARCHIVE="$(docker exec ip30-gitlab-candidate sh -c \
  'ls -1t /home/git/data/backups/*_gitlab_backup.tar | head -n 1')"
test -n "$GITLAB_ARCHIVE"
docker cp "ip30-gitlab-candidate:$GITLAB_ARCHIVE" "$RUN_DIR/gitlab/"
```

If the native task or copy fails, do not remove the archive or prune older snapshots. The task is documented by the [sameersbn GitLab image](https://github.com/sameersbn/docker-gitlab#creating-backups).

### Outline database and file data

Stop only the Outline application while taking both its logical database dump and local file-storage volume. PostgreSQL and Redis remain running.

```sh
docker compose --env-file /opt/ip30slave/outline/.env \
  -f /opt/ip30slave/outline/compose.yaml stop outline

docker exec ip30-outline-postgresql-candidate \
  pg_dump -U outline -Fc outline > "$RUN_DIR/outline/outline.pgdump"
backup_volume ip30-outline-candidate_outline-file-data

docker compose --env-file /opt/ip30slave/outline/.env \
  -f /opt/ip30slave/outline/compose.yaml start outline
```

If either backup command fails, start Outline before investigating. Keep the dump until it has been included in a verified Restic snapshot.

### SVN repository hotcopy

`svnadmin hotcopy` is designed to copy a repository while it is in use. Copy the hotcopy from the container to staging before removing the temporary container copy.

```sh
SVN_TMP="/tmp/ip30-svn-hotcopy-$RUN_ID"
docker exec ip30-svn-candidate mkdir -p "$SVN_TMP"
docker exec ip30-svn-candidate svnadmin hotcopy /var/svn/main "$SVN_TMP/main"
docker cp "ip30-svn-candidate:$SVN_TMP/main" "$RUN_DIR/svn/"
docker exec ip30-svn-candidate rm -r -- "$SVN_TMP"
```

### Store configuration and staged archives

The following captures protected environment files and service configuration. The staged directory path is stable so Restic can apply retention consistently.

```sh
restic backup --tag daily --tag configuration \
  /opt/ip30slave/caddy /opt/ip30slave/dex /opt/ip30slave/gitlab \
  /opt/ip30slave/lldap /opt/ip30slave/mailserver \
  /opt/ip30slave/outline /opt/ip30slave/svn

restic backup --tag daily --tag staged "$STAGE_ROOT"
restic snapshots --tag daily
```

Verify that this run produced snapshots for configuration, staging, every stopped-service volume, and the SVN/GitLab/Outline data. The staging files are plaintext until uploaded; remove only this run's staging directory after verifying the snapshots. On any failure, keep it for investigation and do not run retention cleanup.

After confirming the Restic snapshot contains the new GitLab archive, remove only that archive from the GitLab container; retain it there if verification failed:

```sh
docker exec ip30-gitlab-candidate rm -- "$GITLAB_ARCHIVE"
```

## Weekly review and retention

At the weekly review:

1. Confirm the latest daily snapshots exist for every required service source and that no backup failed.
2. Review the NAS mount, free space, and Restic repository status:

   ```sh
   mountpoint -q /mnt/ip30-backups
   df -h /mnt/ip30-backups
   restic snapshots --tag daily
   restic check
   ```

3. Preview the retention policy. Only after confirming the latest complete backup and expected snapshots, apply it:

   ```sh
   restic forget --tag daily --keep-daily 7 --keep-weekly 12 --dry-run
   restic forget --tag daily --keep-daily 7 --keep-weekly 12 --prune
   restic check
   ```

Pruning locks the Restic repository and may take time. Do not overlap pruning with backups. If any daily source failed, the NAS is unavailable, or the snapshot set is incomplete, do not prune.

After the maintenance session, clear the interactive repository password from the shell:

```sh
unset RESTIC_PASSWORD
```

## Daily system-status check

Complete this check before 09:00 Asia/Shanghai and record pass/fail, time, and the operator role in the approved maintenance log. Do not copy secret values or raw authentication logs into the log.

### Containers and Compose configuration

```sh
docker ps -a --filter name=ip30- --format 'table {{.Names}}\t{{.Status}}'
```

Confirm the active containers are running: Caddy, Dex, GitLab and its PostgreSQL/Redis, LLDAP and its path proxy, Mailserver, Outline and its PostgreSQL/Redis, and SVN. Investigate any stopped, restarting, unhealthy, or unexpectedly recreated container. GitLab, Caddy, Dex, SVN, and the LLDAP path proxy do not have Docker healthchecks; use the endpoint checks below for them.

Validate Compose configuration without printing expanded configuration or secrets:

```sh
for service in caddy dex gitlab lldap outline svn; do
  docker compose --env-file "/opt/ip30slave/$service/.env" \
    -f "/opt/ip30slave/$service/compose.yaml" config -q
done
docker compose -f /opt/ip30slave/mailserver/compose.yaml config -q
```

`config -q` validates configuration only; it is not a service healthcheck. Do not add `--remove-orphans`.

### Routed endpoints

Use the current server IP; `172.23.57.29` is the address recorded for this deployment. `-k` is needed for this candidate's internal Caddy CA and does not verify certificate trust.

```sh
SERVER_IP=172.23.57.29
for path in / /dex/.well-known/openid-configuration /gitlab /outline/ /ldap/ /svn/main/; do
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' "https://$SERVER_IP$path")"
  printf '%s %s\n' "$code" "$path"
done
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' "http://$SERVER_IP/dex"
```

Expected results: `/`, Dex discovery, `/outline/`, and `/ldap/` return `200`; `/gitlab` redirects to its sign-in flow (`302`); anonymous `/svn/main/` returns `401`; HTTP `/dex` redirects to HTTPS (`308`). A different status, TLS failure, or timeout requires investigation. These checks do not prove an employee can complete an OIDC login.

Check Mailserver's published TCP ports and Caddy's certificate dates:

```sh
ss -lnt
openssl s_client -connect "$SERVER_IP:443" -servername "$SERVER_IP" </dev/null 2>/dev/null \
  | openssl x509 -noout -dates -issuer
openssl x509 -in /opt/ip30slave/caddy/caddy-root.crt -noout -dates -issuer
```

Expected Mailserver host ports are `2525`, `1143`, `1465`, `1587`, and `1993`. The server uses an internal CA; verify that employee clients trust it separately.

### Storage, logs, and backup freshness

```sh
df -hT /
df -i /
mountpoint -q /mnt/ip30-backups
df -hT /mnt/ip30-backups
restic snapshots --tag daily
```

Review service logs locally when a check fails, for example:

```sh
docker logs --since 24h --tail 200 ip30-gitlab-candidate
```

Look for repeated startup failures, database connection errors, disk errors, failed mail delivery, or certificate problems. Logs may contain usernames or other sensitive data; redact before sharing. Escalate repeated errors, low disk/inodes, missing snapshots, or an unavailable NAS to the IT duty operator.

## Quarterly restore drill

Run a restore drill on a separate host or isolated test volumes, never against the production Compose project or production volumes.

1. Retrieve the Restic password from the organization vault and select a recent daily snapshot:

   ```sh
   restic snapshots --tag daily
   restic restore <snapshot-id> --target /var/tmp/ip30slave-restore-drill
   ```

2. Confirm the restored tree contains the selected service data and protected configuration. Validate PostgreSQL dumps with `pg_restore --list`, the GitLab archive with `tar -tf`, and the SVN hotcopy with `svnadmin verify`.
3. Restore the selected service in an isolated environment, verify its health and expected endpoint behavior, and measure elapsed recovery time.
4. Record the result, missing prerequisites, and measured RPO/RTO. Remove only the exact isolated drill directory after review; never use a production volume for cleanup tests.

For a production incident, take a fresh backup of the current state if possible and get an approved recovery plan before replacing data. Restore configuration and volumes while the affected services are stopped; restore the Caddy CA files with the Caddy data. Then bring the stack up in dependency order: LLDAP and Mailserver, Dex, GitLab with PostgreSQL/Redis, Outline with PostgreSQL/Redis, SVN, and Caddy last. Confirm GitLab is restored with the matching `sameersbn/gitlab:19.5.1` image and original encryption secrets. Use the service-specific restoration procedure for GitLab and PostgreSQL; do not improvise destructive database or volume replacement commands.

## References

- Repository deployment records: [services index](../services/README.md), [Caddy](../services/caddy.md), [Dex](../services/dex.md), [GitLab](../services/gitlab.md), [LLDAP](../services/lldap.md), [Mailserver](../services/mailserver.md), [Outline](../services/outline.md), [SVN](../services/svn.md).
- [Restic backup](https://restic.readthedocs.io/en/stable/040_backup.html), [restore](https://restic.readthedocs.io/en/stable/050_restore.html), [retention and pruning](https://restic.readthedocs.io/en/stable/060_forget.html).
- [sameersbn GitLab image backup and restore](https://github.com/sameersbn/docker-gitlab#creating-backups).
- [PostgreSQL 17 `pg_dump`](https://www.postgresql.org/docs/17/app-pgdump.html).
- [LLDAP project README](https://github.com/lldap/lldap), [Dex storage](https://dexidp.io/docs/configuration/storage/), [Caddy data directory](https://caddyserver.com/docs/conventions#data-directory), and [Subversion `svnadmin hotcopy`](https://svnbook.red-bean.com/en/1.8/svn.ref.svnadmin.c.hotcopy.html).
