#!/usr/bin/env python3
import os
import smtplib
import subprocess
import sys
from email.header import Header
from email.message import EmailMessage


def svnlook(command, revision, repository):
    result = subprocess.run(
        ["svnlook", command, "-r", revision, repository],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: svn-post-commit-email.py <repository> <revision>")

    repository, revision = sys.argv[1:]
    recipients = [
        address.strip()
        for address in os.environ["SVN_NOTIFICATION_TO"].split(",")
        if address.strip()
    ]
    if not recipients:
        raise ValueError("SVN_NOTIFICATION_TO must contain at least one recipient.")

    repository_name = os.path.basename(repository.rstrip("/"))
    author = svnlook("author", revision, repository)
    date = svnlook("date", revision, repository)
    message = svnlook("log", revision, repository)
    changed = svnlook("changed", revision, repository)

    email = EmailMessage()
    email["From"] = os.environ["SVN_NOTIFICATION_FROM"]
    email["To"] = ", ".join(recipients)
    email["Subject"] = str(
        Header(f"[SVN] {repository_name} r{revision}", "utf-8")
    )
    email.set_content(
        "\n".join(
            [
                f"Repository: {repository_name}",
                f"Revision: {revision}",
                f"Author: {author}",
                f"Date: {date}",
                "",
                "Commit message:",
                message or "(no commit message)",
                "",
                "Changed paths:",
                changed or "(none)",
                "",
            ]
        )
    )

    with smtplib.SMTP(
        os.environ["SVN_SMTP_HOST"],
        int(os.environ.get("SVN_SMTP_PORT", "25")),
        timeout=10,
    ) as server:
        refused = server.send_message(
            email,
            from_addr=email["From"],
            to_addrs=recipients,
        )
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


if __name__ == "__main__":
    main()
