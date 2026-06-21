# Simple Release

## First Setup

```bash
cp ops/deploy.config.example ops/deploy.config
```

Fill in the four server IPs in `ops/deploy.config`.

Each server keeps its own backend `.env` file locally. Do not commit real
secrets.

## Release

Deploy test servers first:

```bash
bash scripts/release.sh staging
```

After testing passes, deploy production:

```bash
CONFIRM_PRODUCTION=production bash scripts/release.sh production
```

Check health:

```bash
bash scripts/release.sh health staging
bash scripts/release.sh health production
```

The script syncs code to the server, builds Docker images on the server, runs
Alembic once on the external server, starts containers, and checks `/api/health`.
