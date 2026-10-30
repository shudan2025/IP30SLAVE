# IP30SLAVE

IP30SLAVE is a project designed to rebuild IP30 Server functionality, enabling enhanced control and communication with the IP30 server platform.

Originally, the IP30 server platform running on IP address 172.23.57.30, provided the core server functionality for the IP30 infrastructure.

The IP30SLAVE server will temporarily running on IP address 172.23.57.29, providing an interim solution for IP30 server functionality.

## Project Objectives
- Rebuilds IP30 Server functionality
- Provides enhanced control over IP30 server platform
- Facilitates communication with IP30 server components
- Supports integration with existing IP30 infrastructure

## Migration Plan
- New homepage
- Authentication system
- Github server
- SVN server
- ERP system
  - Assets/Inventory management
  - Employee management
  - Attendance management
- Company forum/blog system

## Architecture considerations
- docker-based deployment
- Unified link structure
- Modular service architecture
- Scalable and maintainable design
- Caddy as reverse proxy and TLS termination

### Base Services

- LDAP
    Use LLDAP for LDAP authentication
  - lldap
    https://github.com/lldap/lldap

- OIDC
   - Dex
    https://github.com/dexidp/dex

- Mailserver
   - https://github.com/docker-mailserver/docker-mailserver

### Configuration Management Services
- SVN
   - Apache Subversion with mod_dav_svn, LLDAP authentication, and SMTP commit notifications
   Other svn server references:
      https://github.com/talisych/svn-server
      https://github.com/garethflowers/docker-svn-server

- GitLab
   - https://github.com/sameersbn/docker-gitlab
   Other GitLab references:
      https://github.com/gitlabhq/gitlabhq

### Collaboration and Knowledge Management Services

- Outline
   - https://github.com/outline/outline

## Deployment Records

See [service deployment records](docs/services/README.md) for per-service deployment and retirement history.
