#!/usr/bin/env python3
import os
import shlex
import subprocess
from pathlib import Path


def apache_escape(value):
    if "\n" in value or "\r" in value or "\0" in value:
        raise ValueError("LDAP bind settings must not contain control characters.")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_apache_config():
    template = Path("/etc/apache2/sites-available/svn.conf.template").read_text(
        encoding="utf-8"
    )
    replacements = {
        "@@SVN_LDAP_BIND_DN@@": apache_escape(os.environ["SVN_LDAP_BIND_DN"]),
        "@@SVN_LDAP_BIND_PASSWORD@@": apache_escape(
            os.environ["SVN_LDAP_BIND_PASSWORD"]
        ),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)

    if "@@" in template:
        raise ValueError("Unexpanded Apache configuration placeholder.")

    destination = Path("/etc/apache2/sites-available/svn.conf")
    temporary = destination.with_suffix(".conf.tmp")
    temporary.write_text(template, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)


def write_notification_config():
    values = {
        "SVN_NOTIFICATION_TO": os.environ.get(
            "SVN_NOTIFICATION_TO",
            "postmaster@agigactu.com",
        ),
        "SVN_NOTIFICATION_FROM": os.environ.get(
            "SVN_NOTIFICATION_FROM",
            "postmaster@agigactu.com",
        ),
        "SVN_SMTP_HOST": os.environ.get("SVN_SMTP_HOST", "mailserver"),
        "SVN_SMTP_PORT": os.environ.get("SVN_SMTP_PORT", "25"),
    }
    for name, value in values.items():
        if not value or "\n" in value or "\r" in value or "\0" in value:
            raise ValueError(f"{name} must be a non-empty single-line value.")

    port = int(values["SVN_SMTP_PORT"])
    if not 1 <= port <= 65535:
        raise ValueError("SVN_SMTP_PORT must be between 1 and 65535.")

    destination = Path("/etc/subversion/svn-notification.env")
    temporary = destination.with_suffix(".env.tmp")
    temporary.write_text(
        "".join(
            f"export {name}={shlex.quote(value)}\n"
            for name, value in values.items()
        ),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(destination)


def initialize_repository():
    repository = Path("/var/svn/main")
    repository.parent.mkdir(parents=True, exist_ok=True)

    if not (repository / "format").exists():
        subprocess.run(["svnadmin", "create", str(repository)], check=True)
        subprocess.run(
            ["chown", "-R", "www-data:www-data", str(repository)],
            check=True,
        )

    hook = repository / "hooks" / "post-commit"
    hook_source = Path("/usr/local/share/svn-hooks/post-commit").read_bytes()
    legacy_hook = (
        b'#!/bin/sh\n'
        b'set -eu\n'
        b'exec /usr/local/bin/svn-post-commit-email.py "$1" "$2"\n'
    )
    if not hook.exists():
        hook.write_bytes(hook_source)
    else:
        previous_hook = hook.read_bytes()
        hook_contents = previous_hook.replace(b"\r\n", b"\n")
        if hook_contents == legacy_hook:
            hook.write_bytes(hook_source)
        elif hook_contents != previous_hook:
            hook.write_bytes(hook_contents)
    os.chmod(hook, 0o755)


def main():
    write_apache_config()
    write_notification_config()
    initialize_repository()
    subprocess.run(["apache2ctl", "-t"], check=True)
    os.execvp("apache2ctl", ["apache2ctl", "-D", "FOREGROUND"])


if __name__ == "__main__":
    main()
