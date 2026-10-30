# Employee Authentication Architecture

**Status:** Proposed
**Date:** 2026-10-28

Service-specific deployment records are indexed in [`docs/services/README.md`](services/README.md).

## Goals

- Let employees use their corporate email address as the login name for GitLab, SVN, Samba file services, Outline, and employee Wi-Fi.
- Keep one authoritative employee account and password store.
- Provide self-service password recovery using the employee's company mailbox.
- Self-host the identity and authentication components.
- Use the current LLDAP deployment as the sole candidate directory; do not create a second independently writable identity store.

## Recommendation

Use **LLDAP as the single candidate user directory**. Use direct LDAP authentication where supported, Dex OIDC for browser-based single sign-on, and **FreeRADIUS** for Wi-Fi authentication with the H3C AC's built-in Portal/Web function or a compatible external Portal service.

This provides a shared identity source, but not every protocol necessarily supports the same sign-in experience. Outline uses Dex OIDC; GitLab can use direct LDAP and Dex. Samba and FreeRADIUS compatibility with LLDAP must be proven in a pilot, including account attributes and password updates. Do not introduce OpenLDAP or another writable directory as a parallel source.

## Logical Architecture

```text
                         +----------------------+
                         | LLDAP                |
                         | Candidate users,     |
                         | groups, passwords    |
                         +----------+-----------+
                                    |
             +----------------------+----------------------+
             |                      |                      |
       +-----v------+          +----v-------+         +----v-------+
       | GitLab /   |          | FreeRADIUS |         | Password   |
       | Outline /  |          | Wi-Fi auth |         | recovery   |
       +------------+          +-----+------+         +------+-----+
                                    |                       |
                             H3C AC / Portal                 |
                                    |                       |
                             Employee Wi-Fi          Updates directory
                                                            |
        SVN (Apache LDAP auth)      Samba file service (LDAP backend)
```

## Directory and Login Identity

- Use the employee's **company-controlled email address** as the user-facing login name where each service supports it. Keep a stable LDAP identifier such as `uid` as the internal account-linking key; do not use a mutable email address as the sole authorization key.
- Keep each employee's `mail` value unique. Retain a stable LDAP username for clients or integrations that require a non-email login.
- Verify email login behavior with the actual SMB clients, SVN clients, and application versions. Some clients expect `DOMAIN\\username` or a short account name even when web applications accept an email address.
- Use directory groups as the source for application and network access policy.

## Service Integrations

| Service | Integration | Notes |
|---|---|---|
| GitLab | Direct LDAP authentication | Map the unique corporate email to the login name and retain a stable LDAP identifier for account linking. |
| Outline | Dex OIDC | Outline does not use LDAP directly; Dex authenticates against LLDAP. |
| SVN | Apache in front of SVN using LDAP authentication against the directory | Centralizes credentials, but SVN command-line clients generally do not get browser-style SSO. Keep repository authorization separate and group-based. |
| Samba file service | Samba LDAP passdb integration, if supported by the deployed Samba version | Requires Samba-specific LDAP attributes/schema and compatible password handling. Validate email login and password changes with the actual SMB clients. |
| Employee Wi-Fi | H3C AC Portal/Web authentication backed by FreeRADIUS and the directory | The AC controls network access; FreeRADIUS validates credentials; the Portal page collects them. FreeRADIUS is not the login-page service. |
| Password recovery | LLDAP email-based self-service reset | Keep reset delivery tied to a verified company mailbox and validate the deployed mail path. |

## Wi-Fi Portal Authentication Flow

1. The employee joins the employee SSID and receives network configuration.
2. The H3C AC restricts unauthenticated traffic and redirects the client to a Portal/Web login page.
3. The employee enters their corporate email and password over HTTPS.
4. The Portal service submits the authentication request to FreeRADIUS.
5. FreeRADIUS validates the credentials against the authoritative directory over a protected LDAP connection.
6. On success, the AC authorizes the client and applies the configured network policy.

The supplied H3C 300AP manual includes Web-authentication material. Before deployment, verify the exact AC/AP model and software release, supported Portal mode and protocol, external Portal compatibility, and RADIUS settings. Client operating systems do not always open captive-portal windows automatically, so provide a documented fallback login URL.

The Portal password flow is distinct from WPA2/WPA3-Enterprise 802.1X. If password-based Portal authentication is used, confirm that the selected RADIUS-to-directory method works with the directory's password storage and the H3C request format. Do not assume a salted LDAP password hash can validate every EAP method. EAP-TLS is a stronger future option, but it does not provide the requested web login page after association.

## Password Recovery

- Send recovery links or one-time codes only to a verified, company-controlled mailbox.
- Update the password in the authoritative directory so all integrated services use the new credential.
- Protect the recovery flow against account enumeration, repeated attempts, and mailbox compromise; provide an administrator-assisted recovery path.
- Do not add a separate application-local password reset that leaves the LDAP password unchanged.
- Confirm that the chosen recovery tool can safely change passwords in the final directory while enforcing its password policy.

## Current LLDAP Candidate

LLDAP is the only active directory candidate in the current stack. It provides LDAP for services that support directory authentication and works with Dex for browser-based OIDC. Use a least-privilege bind account for lookups, protect LDAP traffic with TLS before production, and keep direct LDAP authentication distinct from browser SSO.

OpenLDAP is retired and out of scope. Samba's LDAP passdb integration with LLDAP remains unverified and may require attributes or password handling that LLDAP does not provide. Sharing an LDAP database does not by itself guarantee that the same password works for SMB, Wi-Fi, and web applications. Pilot Samba authentication and password reset end to end before production use.

Avoid bidirectional synchronization or multiple writable directories. Choose one authoritative directory, define a migration/cutover plan, and make all other components consume that identity source.

## Deployment Components and Container Plan

Containers are a packaging choice; not every component should run in one. Keep stateful identity data, network reachability, and recovery requirements in view.

| Component | Deployment recommendation | Purpose and constraints |
|---|---|---|
| LLDAP | Continue the existing candidate deployment | Validate account recovery, TLS, backups, and every required consumer before production cutover. |
| FreeRADIUS | Docker container on a Linux host | Handles RADIUS authentication/accounting for the H3C AC. Publish the required UDP ports (normally 1812 for authentication and 1813 for accounting), and ensure the AC's source IP reaches FreeRADIUS as expected. Mount configuration and certificates securely; do not bake secrets into the image. |
| H3C Portal service | Use the AC's built-in Portal/Web function if it meets requirements; otherwise deploy a separate compatible Portal service | Provides the login page and H3C Portal interaction. FreeRADIUS does not provide this web page. A separate service must be compatible with the exact AC model, firmware, and Portal protocol. |
| Password recovery service | Optional Docker container | Provides email-based self-service recovery and updates the authoritative directory over TLS. Select and test a product that supports the final directory and password policy. |
| Reverse proxy | Reuse an existing proxy or run one in a container | Provides HTTPS ingress for the Portal page and password recovery. Do not expose LDAP or RADIUS through a general-purpose web proxy. |
| H3C AC/AP and SMTP service | Existing network hardware and mail infrastructure | The AC/AP is not a Docker service. Use the organization's SMTP relay for recovery emails where available. |
| GitLab, SVN, Outline, Samba file service | Existing application/file-service deployments | These are consumers of the identity service, not required containers in the authentication stack. |

A minimal additional application-container stack is therefore **FreeRADIUS**, with **a Portal service only if the H3C AC does not provide the required function**. LLDAP is already deployed; AC/AP and SMTP are separate dependencies. Keep LDAP and RADIUS reachable only on trusted networks, and verify persistent-data backup and restore before production use.

## Security and Operations

- Use TLS for LDAP connections and Portal pages; validate certificates rather than disabling verification.
- Restrict LDAP bind accounts to the minimum read/write permissions required. Keep password-reset permissions separate from ordinary lookup accounts.
- Use strong, unique shared secrets between the H3C AC and RADIUS, restrict RADIUS network access, and monitor authentication failures.
- Apply access policy through directory groups and revoke access by disabling the central account.
- Back up the directory and its configuration, test restoration, and audit account creation, group changes, password resets, and administrative access.

## Rollout and Acceptance Checks

1. Inventory LLDAP user identifiers, groups, password-reset behavior, and dependent services.
2. Confirm that GitLab, Outline/Dex, and Apache/SVN can authenticate with the intended email mapping.
3. Join the Samba service to LLDAP in a lab; test SMB login, group authorization, and password changes/reset with representative clients.
4. Test SVN authentication with both the intended browser and command-line clients.
5. Join a Samba file server to the chosen directory and test access from the actual Windows, Linux, and macOS clients in use.
6. Verify H3C Portal redirection, email-based login, RADIUS success/failure handling, HTTPS, fallback behavior, and session expiry on representative phones and laptops.
7. Cut over only after account disablement, password recovery, group-based authorization, and rollback procedures have been demonstrated.

## Decisions to Confirm

- Whether the deployed Samba version and SMB clients can reliably use LLDAP as the password and account source.
- The exact H3C AC/AP model, firmware, Portal mode, and supported external Portal/RADIUS protocol.
- The GitLab edition and Outline/Dex configuration, which determine the available authentication integrations.
- Required SMB clients and whether they must log in using the full email address or may use a mapped short username.
- Whether LLDAP's built-in email password recovery meets operational and security requirements.
