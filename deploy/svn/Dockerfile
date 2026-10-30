FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        apache2 \
        ca-certificates \
        libapache2-mod-svn \
        libaprutil1-ldap \
        python3 \
        subversion \
    && rm -rf /var/lib/apt/lists/*

RUN a2enmod authnz_ldap dav dav_svn ldap authz_svn \
    && a2dissite 000-default \
    && ln -s ../sites-available/svn.conf /etc/apache2/sites-enabled/svn.conf

COPY apache-svn.conf.template /etc/apache2/sites-available/svn.conf.template
COPY authz /etc/subversion/authz
COPY svn-entrypoint.py /usr/local/bin/svn-entrypoint.py
COPY svn-post-commit /usr/local/share/svn-hooks/post-commit
COPY svn-post-commit-email.py /usr/local/bin/svn-post-commit-email.py

RUN sed -i 's/\r$//' \
        /usr/local/bin/svn-entrypoint.py \
        /usr/local/bin/svn-post-commit-email.py \
        /usr/local/share/svn-hooks/post-commit \
    && chmod 0755 /usr/local/bin/svn-entrypoint.py \
        /usr/local/bin/svn-post-commit-email.py \
        /usr/local/share/svn-hooks/post-commit \
    && chmod 0644 /etc/subversion/authz

EXPOSE 80

ENTRYPOINT ["python3", "/usr/local/bin/svn-entrypoint.py"]
