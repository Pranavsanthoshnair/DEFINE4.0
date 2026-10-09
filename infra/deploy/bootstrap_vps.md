# infra/deploy/bootstrap_vps.md
# Veylo PR 002 — VPS Bootstrap and Security Checklist
# Owner: Member 4

## Prerequisites
- Ubuntu 22.04 LTS VPS with at least 16 GB RAM, 4 vCPUs, 80 GB SSD
- Existing Caddy host service (shared with other project — do NOT restart, only reload)
- Docker and Docker Compose plugin already installed
- A domain or DuckDNS subdomain with A record pointing to VPS IP

---

## 1. Create the dedicated user

```bash
sudo adduser pr002
sudo usermod -aG docker pr002
# Copy your SSH key to the new user
sudo rsync --archive --chown=pr002:pr002 ~/.ssh /home/pr002
# Verify login from a second terminal before closing this session
ssh pr002@<VPS_IP>
```

## 2. Clone the repository

```bash
sudo -u pr002 -i
git clone https://github.com/<org>/DEFINE4.0.git /home/pr002/pr002
cd /home/pr002/pr002
cp .env.example .env
chmod 600 .env
# Fill in all secrets (run scripts/gen_secrets.sh for random values)
nano .env
```

## 3. DNS setup

Add A records:
- `api.<domain>` → VPS public IP
- `app.<domain>` → VPS public IP

Wait for propagation: `dig api.<domain>` should return the VPS IP.

## 4. Caddy configuration

```bash
# Back up existing Caddyfile FIRST
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak

# Ensure conf.d import exists (add once)
grep -q 'import /etc/caddy/conf.d' /etc/caddy/Caddyfile || \
  echo 'import /etc/caddy/conf.d/*.caddy' | sudo tee -a /etc/caddy/Caddyfile

# Create conf.d directory if needed
sudo mkdir -p /etc/caddy/conf.d
sudo mkdir -p /var/log/caddy

# Set PR002_DOMAIN in the shell (Caddy reads env vars)
# Or replace {$PR002_DOMAIN} with the actual domain in the file
export PR002_DOMAIN=yourdomain.duckdns.org
sudo cp infra/caddy/pr002.caddy /etc/caddy/conf.d/pr002.caddy
sudo sed -i "s/{\$PR002_DOMAIN}/$PR002_DOMAIN/g" /etc/caddy/conf.d/pr002.caddy

# Validate and reload (do NOT restart — this would drop existing connections)
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## 5. Start services

```bash
cd /home/pr002/pr002
docker compose up -d
# Wait for healthy
docker compose ps
```

## 6. Run migrations and seed

```bash
make migrate
make seed
```

## 7. Verify

```bash
curl -fsS https://api.<domain>/healthz
curl -fsS https://app.<domain>/
```

---

## Security Checklist

Complete each item and tick it below before the demo.

- [ ] **SSH hardening**
  ```bash
  sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
  sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  sudo systemctl reload ssh
  ```

- [ ] **fail2ban running**
  ```bash
  sudo apt install -y fail2ban
  sudo systemctl enable --now fail2ban
  sudo fail2ban-client status sshd
  ```

- [ ] **Firewall — only 22, 80, 443 open**
  ```bash
  sudo ufw status
  # Expected: 22, 80, 443 ALLOW. Everything else DENY.
  # Docker-published ports (8100, 8101) use 127.0.0.1 binding — NOT reachable externally.
  ```

- [ ] **Ports internal-only** — verify with `ss -tlnp`:
  - `127.0.0.1:8100` — api (loopback only ✓)
  - `127.0.0.1:8101` — web (loopback only ✓)
  - Postgres and Redis must NOT appear (internal Docker network only)

- [ ] **No secrets in git** — run `gitleaks detect` before demo

- [ ] **.env permissions**
  ```bash
  ls -la /home/pr002/pr002/.env
  # Expected: -rw------- 1 pr002 pr002
  ```

- [ ] **Containers run as non-root** — check in Dockerfiles: `USER nonroot` or `USER 1000`

- [ ] **Unattended upgrades**
  ```bash
  sudo apt install -y unattended-upgrades
  sudo dpkg-reconfigure -plow unattended-upgrades
  ```

- [ ] **HTTPS and HSTS** — verify with `curl -I https://app.<domain>`:
  - `strict-transport-security` header present
  - Certificate valid

- [ ] **Docker log rotation** — configured via `json-file` driver in `docker-compose.yml` ✓

- [ ] **Time sync**
  ```bash
  timedatectl
  # Expected: "System clock synchronized: yes"
  ```

- [ ] **Backup tested** — run `bash infra/backup/restore_test.sh` and record result below

```
Restore test result (date and row counts):

```

- [ ] **Off-server backup copy** — latest `.age` file copied to teammate's machine

---

## Port reference

| Service | Host binding | Notes |
|---|---|---|
| api | 127.0.0.1:8100 | Proxied by Caddy to api.\<domain\> |
| web | 127.0.0.1:8101 | Proxied by Caddy to app.\<domain\> |
| postgres | internal only | Docker network pr002_net |
| redis | internal only | Docker network pr002_net |
| ai | internal only | Port 8200 within pr002_net |
