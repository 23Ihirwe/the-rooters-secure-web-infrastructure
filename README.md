# The Rooters --- Secure Web Infrastructure

> **Securing and Scaling a Production-Style Web Infrastructure**

A production-style Linux infrastructure project demonstrating **NGINX
reverse proxying and load balancing, HTTPS/TLS, UFW firewalling, two
isolated backend services, and evidence-led troubleshooting**.

![Linux](https://img.shields.io/badge/Linux-Ubuntu-E95420?style=flat-square&logo=ubuntu&logoColor=white)
![NGINX](https://img.shields.io/badge/NGINX-Reverse%20Proxy%20%26%20Load%20Balancer-009639?style=flat-square&logo=nginx&logoColor=white)
![HTTPS](https://img.shields.io/badge/HTTPS-TLS-2EA44F?style=flat-square)
![UFW](https://img.shields.io/badge/Firewall-UFW-6F42C1?style=flat-square)
![Python](https://img.shields.io/badge/Backends-Python-3776AB?style=flat-square&logo=python&logoColor=white)

------------------------------------------------------------------------

## Project Overview

**The Rooters** built a small production-style web infrastructure on one
Ubuntu Linux machine.

Two lightweight Python HTTP backends run locally on separate ports.
**NGINX** is the single web entry point and acts as a **reverse proxy
and load balancer**. The web entry point is protected with **HTTPS using
a locally generated self-signed TLS certificate**, while **UFW** applies
a least-exposure firewall policy.

The project also demonstrates evidence-led troubleshooting by
deliberately stopping Backend 2, observing the failure, investigating
the infrastructure, identifying the root cause, restoring the service,
and verifying recovery.

The focus is **infrastructure configuration, security reasoning,
testing, availability and diagnostic reasoning**, rather than
application complexity.

------------------------------------------------------------------------

## Architecture

``` text
                         CLIENT
                            |
                 HTTP :80  |  redirect to HTTPS
                            v
                     +-------------+
                     | FIREWALL    |
                     |    UFW      |
                     +-------------+
                            |
                  HTTPS :443
                            v
                 +--------------------+
                 |       NGINX        |
                 | Reverse Proxy      |
                 | Load Balancer      |
                 +--------------------+
                     /            \
                    v              v
        +------------------+   +------------------+
        |    Backend 1     |   |    Backend 2     |
        | 127.0.0.1:3001   |   | 127.0.0.1:3002   |
        |    Server 1      |   |    Server 2      |
        +------------------+   +------------------+
```

### Request Flow

1.  HTTP requests arrive on **port 80** and are redirected to HTTPS.
2.  **UFW** permits only required administration and web entry ports.
3.  Secure traffic reaches **NGINX on port 443**.
4.  NGINX terminates TLS and forwards requests to the backend pool.
5.  Requests are distributed between `127.0.0.1:3001` and
    `127.0.0.1:3002`.
6.  Backend ports remain local targets rather than public entry points.

> **README image slot:** add the final Canva/PowerPoint export as
> `Architecture/architecture_diagram.png`.

------------------------------------------------------------------------

## Infrastructure Components

  Component   Role                                           Address / Port
  ----------- ---------------------------------------------- --------------------------
  SSH         Administration                                 `22/tcp`
  HTTP        Redirect to HTTPS                              `80/tcp`
  HTTPS       Secure web entry point                         `443/tcp`
  NGINX       Reverse proxy + load balancer + TLS endpoint   `80`, `443`
  Backend 1   Local Python service                           `127.0.0.1:3001`
  Backend 2   Local Python service                           `127.0.0.1:3002`
  UFW         Host firewall                                  Allows `22`, `80`, `443`

------------------------------------------------------------------------

## Backend Environment

The two Python services return distinguishable responses so that load
balancing can be proven.

``` bash
curl http://127.0.0.1:3001; echo
curl http://127.0.0.1:3002; echo
ss -ltnp | grep -E '3001|3002'
```

Both services bind to `127.0.0.1`, keeping them on the local loopback
interface.

------------------------------------------------------------------------

## NGINX Reverse Proxy & Load Balancing

``` nginx
upstream backend_pool {
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}
```

The HTTPS server block forwards requests to the pool:

``` nginx
location / {
    proxy_pass http://backend_pool;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Configuration is validated before reload:

``` bash
sudo nginx -t
sudo systemctl reload nginx
```

Load balancing is verified using:

``` bash
for i in {1..10}; do curl -sk https://localhost; echo; done
```

Responses from both Server 1 and Server 2 demonstrate that NGINX reached
both backend instances.

------------------------------------------------------------------------

## HTTPS & TLS

The project uses a locally generated **self-signed X.509 certificate**.

``` text
Public certificate: /etc/ssl/certs/the_rooters.crt
Private key:        /etc/ssl/private/the_rooters.key
```

NGINX references:

``` nginx
ssl_certificate /etc/ssl/certs/the_rooters.crt;
ssl_certificate_key /etc/ssl/private/the_rooters.key;
```

Certificate details are inspected with:

``` bash
openssl x509 -in /etc/ssl/certs/the_rooters.crt -noout -subject -issuer -dates
```

HTTPS is tested with:

``` bash
curl -k https://localhost
```

### HTTP → HTTPS Redirect

``` nginx
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

Verification:

``` bash
curl -I http://localhost
```

Expected evidence includes `HTTP/1.1 301 Moved Permanently` and
`Location: https://localhost/`.

------------------------------------------------------------------------

## Firewall --- UFW

The firewall follows the **principle of least exposure**.

``` bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status numbered
```

  Port     Purpose              Exposure Decision
  -------- -------------------- ---------------------------
  `22`     SSH administration   Allowed
  `80`     HTTP redirect        Allowed
  `443`    HTTPS                Allowed
  `3001`   Backend 1            Not intentionally exposed
  `3002`   Backend 2            Not intentionally exposed

Ports 3001 and 3002 are absent from the public UFW allow rules and the
services bind to `127.0.0.1`.

------------------------------------------------------------------------

## Troubleshooting & Diagnostic Reasoning

The deliberate fault is **Backend 2 becoming unavailable**.

### 1 --- Problem and Symptom

Backend 2 is deliberately stopped. Repeated HTTPS requests then return
only Server 1.

``` bash
for i in {1..6}; do curl -sk https://localhost; echo; done
```

### 2 --- Evidence

``` bash
ss -ltnp | grep -E '3001|3002'
curl http://127.0.0.1:3001; echo
curl http://127.0.0.1:3002; echo
```

Backend 1 remains reachable while port 3002 refuses the connection.

### 3 --- Investigation

``` bash
sudo systemctl status nginx
sudo nginx -t
ss -ltnp | grep -E '3001|3002'
```

NGINX remains active and its configuration validates successfully, while
no process is listening on port 3002. This narrows the failure to
Backend 2.

### 4 --- Root Cause

Backend 2's process was stopped, leaving no service listening on
`127.0.0.1:3002`.

### 5 --- Fix & Verification

Backend 2 is restarted:

``` bash
python3 backend2.py
```

Recovery is verified:

``` bash
ss -ltnp | grep -E '3001|3002'
for i in {1..8}; do curl -sk https://localhost; echo; done
```

Both backend ports appear again and repeated HTTPS requests return both
Server 1 and Server 2.

------------------------------------------------------------------------

## Evidence

``` text
Evidence/
├── Backend/
├── Load_Balancing/
├── HTTPS/
├── Firewall/
└── Troubleshooting/
```

Screenshots should be readable, captioned, and accompanied by an
explanation of **what each result proves**.

------------------------------------------------------------------------

------------------------------------------------------------------------

## Practical Evidence

The screenshots below were captured from the group's Ubuntu environment.
Each preview is also a link: click the image on GitHub to open the
full-size evidence file.

### Backend Services

Both backend services respond independently and listen on the local
loopback interface on ports `3001` and `3002`.

[![Backend services
running](images/01_backend_services.png)](images/01_backend_services.png)

### NGINX Load Balancing

Repeated HTTPS requests through NGINX return responses from both Server
1 and Server 2, demonstrating that requests are being distributed across
the backend pool.

[![NGINX load balancing
evidence](images/02_load_balancing.png)](images/02_load_balancing.png)

### HTTPS and HTTP Redirect

HTTPS successfully returns a backend response, while an HTTP request
receives `301 Moved Permanently` and is redirected to
`https://localhost/`.

[![HTTPS and HTTP redirect
evidence](images/03_https_redirect.png)](images/03_https_redirect.png)

### UFW Firewall Rules

UFW is active and permits the required entry ports `22`, `80`, and
`443`. Backend ports `3001` and `3002` are not present in the public
allow rules.

[![UFW firewall
rules](images/04_firewall_rules.png)](images/04_firewall_rules.png)

### Troubleshooting Recovery

After Backend 2 is restored, both backend ports are listening again and
the infrastructure can return responses from both servers.

[![Troubleshooting recovery
evidence](images/05_troubleshooting_recovery.png)](images/05_troubleshooting_recovery.png)

## Repository Structure

``` text
the-rooters-secure-web-infrastructure/
│
├── README.md
├── .gitignore
├── Technical_Report/
│   └── Technical_Report.pdf
├── Architecture/
│   ├── architecture_diagram.png
│   └── architecture_diagram.pdf
├── Backend/
│   ├── backend1/
│   │   └── backend1.py
│   └── backend2/
│       └── backend2.py
├── NGINX/
│   └── nginx_site_configuration.txt
├── TLS/
│   ├── certificate_information.txt
│   ├── the_rooters.crt
│   └── NEVER_INCLUDE_PRIVATE_KEY.txt
├── Firewall/
│   └── firewall_rules.txt
├── Evidence/
│   ├── Backend/
│   ├── Load_Balancing/
│   ├── HTTPS/
│   ├── Firewall/
│   └── Troubleshooting/
└── Demo/
    └── demo_link.txt
```

------------------------------------------------------------------------

## Security Note

 The TLS private key (`the_rooters.key`) is intentionally excluded from this repository and must never be committed or submitted.
 
### Recommended `.gitignore`

```gitignore
# TLS private keys
*.key
*.pem

# Python generated files
__pycache__/
*.pyc

# VS Code
.vscode/

# macOS system files
.DS_Store

The public certificate `the_rooters.crt` is different from the secret
private key.

------------------------------------------------------------------------

## Group Collaboration

  Group Member   Main Responsibility          Demo Responsibility
  -------------- ---------------------------- ---------------------------------
  Ange       Backend 1 + Backend 2        Backends and listening ports
  Lovella      NGINX + Load Balancing       Proxy and balancing
  Elvire       SSL/TLS + HTTPS              Certificate, HTTPS and redirect
  Hildegardine       Firewall + Troubleshooting   UFW and diagnosis/recovery

Every member should understand the complete architecture even when
leading a specific section.

------------------------------------------------------------------------

## Technical Report & Demo

The repository supports the final **technical report**, **architecture
diagram**, **actual Linux evidence**, NGINX/TLS/firewall configuration
records, and the **recorded practical demonstration**.

The recording should show the actual Linux environment and command
execution rather than replacing the practical demonstration with slides.

------------------------------------------------------------------------

## AI Transparency

ChatGPT and Claude were used as supplementary learning and troubleshooting aids. All configurations, testing, and evidence were completed and verified by the group.

------------------------------------------------------------------------

# The Rooters

**BSc(Hons) Software Engineering --- Web Infrastructure**\
**Summative Group Practical Assignment**\
**Assessment:** *Securing and Scaling a Production-Style Web
Infrastructure*

**Repository:** `the-rooters-secure-web-infrastructure`


