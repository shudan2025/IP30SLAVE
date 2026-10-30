# Mailserver Deployment

## Status

The active candidate uses `ghcr.io/docker-mailserver/docker-mailserver:latest` in `deploy/mailserver/compose.yaml`. The image tag is mutable; pin a tested digest before production.

## Deployment

The Mailserver shares the former Base Services Compose project with LLDAP. After installing the certificates listed below, validate and start it with:

```sh
cd /opt/ip30slave/mailserver
sudo docker compose -f compose.yaml config -q
sudo docker compose -f compose.yaml up -d mailserver
```

The active service-specific Compose file is under `/opt/ip30slave/mailserver/`. Start LLDAP first when bringing up a stopped stack; it creates the shared `ip30-lldap-mail` network.

## Network and ports

The container is named `ip30-mailserver-candidate` and publishes these host ports on all interfaces:

| Host port | Container port | Service |
|---:|---:|---|
| 2525 | 25 | SMTP |
| 1143 | 143 | IMAP |
| 1465 | 465 | SMTPS |
| 1587 | 587 | Submission |
| 1993 | 993 | IMAPS |

Restrict these ports with host/network firewall rules. DNS/MX records and external delivery are not configured.

For the isolated candidate, LLDAP, SVN, and application containers use the `mailserver:25` relay over the private `ip30-lldap-mail` Docker network. SMTP authentication and encryption are disabled on that internal network. Do not reuse this relay policy on an untrusted or public network.

## TLS and test mailbox

The mailserver uses `SSL_TYPE=self-signed`. The three certificate files required by docker-mailserver v16 are stored in the `mail-config` volume:

- `ssl/mail.agigactu.com-key.pem`
- `ssl/mail.agigactu.com-cert.pem`
- `ssl/demoCA/cacert.pem`

The test leaf certificate was signed by a temporary local CA and is not publicly trusted. `SSL_TYPE=self-signed` does not generate these files automatically.

Only the `postmaster@agigactu.com` test mailbox is provisioned. Its generated password is stored on the current server in `/opt/ip30slave/mailserver/test-mailbox-password`, mode `0600`, owner `root:root`. Never copy it into repository files or logs.

Provision the test mailbox and restart the service with:

```sh
sudo docker exec ip30-mailserver-candidate setup email add postmaster@agigactu.com '<random-test-password>'
sudo docker restart ip30-mailserver-candidate
```

## Validation and limits

The container is healthy, and published SMTP/IMAP ports accepted TCP connections from a separate client. Test messages from LLDAP, GitLab, and the SVN post-commit hook were delivered to the local postmaster mailbox and removed. SMTP authentication, TLS between containers, DNS/MX, and external delivery remain unverified.
