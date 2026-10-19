# ufcpro.in — MCP Server

> Ek real MCP (Model Context Protocol) server jo **ufcpro.in** ke job-finder engine ko
> tools/resources/prompts ke roop me kisi bhi MCP-compatible AI host (Claude, Cursor, Bedrock)
> ke saamne khol deta hai.
>
> Ye project `../web/app.py` ke existing job-finder logic ko **reuse** karta hai — usे todd ke nahi.

---

## Chapter 01 — MCP kya hai aur yahan kyun? (Fundamentals)

### Problem (N×M)
Aapka `web/app.py` jobs laata hai, JD match karta hai, portal link resolve karta hai.
Abhi ye sirf aapke **browser UI** (`index.html`) se chalti hai. Agar aap chaho ki
**Claude**, **Cursor**, ya ek **Bedrock agent** bhi aapke job-finder ko use kare, to har ek
ke liye alag integration likhna padega — ye **N×M problem** hai.

```
          Claude   Cursor   Bedrock-agent
job-finder   ✏️       ✏️        ✏️       <- har jodi alag integration (N×M)
```

### Solution (MCP = USB-C of AI)
MCP server **ek baar** banao — phir koi bhi MCP host usse baat kar lega. Ek standard "port".

```
Claude  ─┐
Cursor  ─┼──►  [ufcpro.in MCP server]  ──►  web/app.py ka job engine
Bedrock ─┘        (tools/resources/prompts)
```

Ab job-finder ek **standardized capability** ban gaya — N+M, N×M nahi.

### Ye project kis guide topic ko implement karta hai

| File | Guide chapter | Topic |
|---|---|---|
| `README.md` (ye) | 01 | Fundamentals, N×M, USB-C |
| `mcp_server.py` | 02, 03, 05, 06 | Host/Client/Server, Tools/Resources/Prompts, JSON-RPC errors, server build |
| `mcp_server.py` (transport switch) | 04 | stdio + Streamable HTTP |
| `mcp_client.py` | 07 | Client + tool-use loop (Bedrock + mock) |
| `auth.py` | 08 | JWT + per-tool RBAC (+ tool-poisoning/rug-pull/EMA explained) |
| `deploy/` | 09 | Dockerfile, Helm, ArgoCD, CI/CD (config-as-code) |

---

## Chapter-by-chapter padhai

Har file ke upar ek `# ===== CHAPTER XX =====` comment hai jo batata hai wo guide ke
kis topic ko implement kar raha hai. Order:

1. `mcp_server.py`  — Ch 02,03,04,05,06
2. `mcp_client.py`  — Ch 07
3. `auth.py`        — Ch 08
4. `deploy/`        — Ch 09

Guides khud: `../../../DevOps/Lab/mcp-complete/` (00 se 10).

---

## Quick start

```bash
cd ufcpro-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Server test (MCP Inspector)
npx @modelcontextprotocol/inspector python mcp_server.py

# 2) Client (mock LLM mode — bina AWS ke chalta hai)
python mcp_client.py --mock "Delhi me devops jobs dhoondo"

# 3) Client (real Bedrock — AWS creds + Bedrock access chahiye)
python mcp_client.py "Delhi me devops jobs dhoondo"
```

> 🔒 Security note: default transport stdio (local). HTTP/remote ke liye auth zaroori — `auth.py` dekho.
