# CyberPanel deploy setup: cancer hub

Target dir: `/home/pharmeasy.in/public_html/cancer`
Served at:  `https://pharmeasy.in/cancer/` (once CloudFront routes it, see step 0)
Source:     a `--production` build of this repo, staged into `dist/` and rsynced by
            `.github/workflows/deploy.yml` on every push to `main` (or Run workflow).

Same pattern as the GLP-1 hub (`pharmeasyMarketing/GLP-1`, `deploy/CYBERPANEL.md`), with one
difference: **this repo is public, so the private deploy key is never committed.** It lives at
`~/.ssh/cancer_deploy` on the machine that generated it and only goes into the GitHub secret.

The deploy key is locked to that one directory with `rrsync`: write-only, no shell, nothing else
on the box.

## Status (14 Nov 2026)

- Steps 1 to 5 are done: `cancer/` exists on the box (owner `pharm9528`), the deploy key is
  authorised with `/usr/local/bin/rrsync -wo /home/pharmeasy.in/public_html/cancer` (line 10 of
  `/home/pharmeasy.in/.ssh/authorized_keys`, backup `authorized_keys.bak-20261114021407`) and the
  five `DEPLOY_*` secrets are set. The key cannot open a shell (tested).
- **Step 0 (CloudFront) is still open.** Files deploy to the server, but the public URL serves the
  app's 404 until `/cancer*` is routed to the CyberPanel origin.
- The "Latest on cancer in India" section is left off production until an editor approves real
  items (`review_updates.py approve`); items approved by the end-to-end test do not count.

## Two warnings

1. **`--delete` is on.** Anything in `cancer/` that is not in the build is removed on every
   deploy. Keep only the generated site there.
2. **Production is indexable.** The GitHub Pages copy carries `noindex`; the deploy build drops it
   (`--production`) and the workflow fails if any page still has it. Pushing to `main` publishes
   to Google once the secrets are set, so only push reviewed content.

## Step 0: CloudFront routing (infra team)

As of 14 Nov 2026 `https://pharmeasy.in/cancer/` is answered by the main app (`server: pe`), not
CyberPanel. `/glp-1/` and `/medicines/` reach CyberPanel (`server: LiteSpeed`,
`x-powered-by: CyberPanel-OLS`). CloudFront needs a behaviour for `/cancer` and `/cancer/*`
pointing at the CyberPanel origin, copied from the `/glp-1*` behaviour. Until then files land on
the server but the public URL keeps returning the app's 404.

Check after the change:

```bash
curl -sI https://pharmeasy.in/cancer/ | grep -i -E '^HTTP|^server|x-powered-by'
```

## Step 1: find the site user (on the server, as root)

```bash
stat -c 'owner=%U group=%G' /home/pharmeasy.in/public_html
getent passwd <owner>        # needs a real shell; usermod -s /bin/bash <owner> if not
```

## Step 2: locate rrsync

```bash
ls -1 /usr/bin/rrsync /usr/share/rsync/rrsync /usr/share/doc/rsync*/support/rrsync 2>/dev/null
```

## Step 3: create the directory and authorise the key

```bash
U=<owner from step 1>
RRSYNC=<path from step 2>
DIR=/home/pharmeasy.in/public_html/cancer
HOME_DIR=$(getent passwd "$U" | cut -d: -f6)
mkdir -p "$DIR" && chown "$U": "$DIR"
mkdir -p "$HOME_DIR/.ssh" && chmod 700 "$HOME_DIR/.ssh"
cat >> "$HOME_DIR/.ssh/authorized_keys" <<EOF
command="$RRSYNC -wo $DIR",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINBBbgcBjgqUV+utqDdfU7Se0AzJlpRdb5Vp9A2NWR+O github-actions@cancer
EOF
chmod 600 "$HOME_DIR/.ssh/authorized_keys" && chown -R "$U": "$HOME_DIR/.ssh"
```

## Step 4: host key (locally)

```bash
ssh-keyscan -t ed25519 <server-ip-or-hostname>
```

## Step 5: GitHub secrets (pharmeasyMarketing/cancer)

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | server IP or hostname (same box as GLP-1) |
| `DEPLOY_USER` | owner from step 1 |
| `DEPLOY_PATH` | `.` exactly (rrsync already roots the session at `cancer/`) |
| `DEPLOY_SSH_KEY` | `gh secret set DEPLOY_SSH_KEY < ~/.ssh/cancer_deploy --repo pharmeasyMarketing/cancer` |
| `DEPLOY_KNOWN_HOSTS` | the `ssh-keyscan` line from step 4 |
| `DEPLOY_PORT` | only if SSH is not on 22 |

## Step 6: deploy and verify

Actions > **Deploy cancer hub to CyberPanel** > Run workflow (or push to `main`).

```bash
curl -sI https://pharmeasy.in/cancer/ | head -1
curl -s https://pharmeasy.in/cancer/treatment/ | grep -o '<title>[^<]*'
curl -s https://pharmeasy.in/cancer/ | grep -c 'name="robots" content="noindex'   # must be 0
```
