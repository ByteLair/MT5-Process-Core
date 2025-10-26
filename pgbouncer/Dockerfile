FROM alpine:3.19

# Install PgBouncer
RUN apk add --no-cache \
    pgbouncer \
    postgresql-client \
    && mkdir -p /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer \
    && chown -R postgres:postgres /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer

# Copy configuration files
COPY pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY userlist.txt /etc/pgbouncer/userlist.txt

# Set permissions
RUN chown postgres:postgres /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/userlist.txt \
    && chmod 600 /etc/pgbouncer/userlist.txt

# Switch to postgres user
USER postgres

# Expose PgBouncer port
EXPOSE 5432

# Start PgBouncer
CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
