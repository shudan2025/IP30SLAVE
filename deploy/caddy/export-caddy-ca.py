#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path


ROOT = Path("/opt/ip30slave")
CADDY_CONTAINER = "ip30-caddy-candidate"
GITLAB_CONTAINER = "ip30-gitlab-candidate"
CA_PATH = "/data/caddy/pki/authorities/local/root.crt"
SYSTEM_CA_PATH = "/etc/ssl/certs/ca-certificates.crt"


def container_file(container, path):
    result = subprocess.run(
        ["docker", "exec", container, "cat", path],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def write_file(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    os.chown(temporary, 0, 0)
    os.chmod(temporary, 0o644)
    temporary.replace(path)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run this script as root.")

    directory = ROOT / "caddy"
    root_ca = container_file(CADDY_CONTAINER, CA_PATH)
    if b"-----BEGIN CERTIFICATE-----" not in root_ca:
        raise SystemExit("Caddy did not return a PEM root certificate.")

    system_bundle_path = directory / "system-ca-bundle.pem"
    if system_bundle_path.exists():
        system_bundle = system_bundle_path.read_bytes()
    else:
        system_bundle = container_file(GITLAB_CONTAINER, SYSTEM_CA_PATH)
        if b"-----BEGIN CERTIFICATE-----" not in system_bundle:
            raise SystemExit("GitLab did not return its system CA bundle.")
        write_file(system_bundle_path, system_bundle)

    write_file(directory / "caddy-root.crt", root_ca)
    ca_bundle = system_bundle.rstrip() + b"\n" + root_ca.strip() + b"\n"
    write_file(directory / "ca-bundle.pem", ca_bundle)
    print("Exported the Caddy root CA and built the GitLab CA bundle.")


if __name__ == "__main__":
    main()
