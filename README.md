### Generated file structure:
```
certs/
├── root-client-ca.key       # Private key of your “root” CA used to sign client certs
├── root-client-ca.crt       # Public CA certificate for client certs (trust anchor)
├── provider-certs/          # Per‑team client certificates
│   ├── sumsang-company-client.key   # Team’s client private key
│   ├── sumsang-company-client.csr   # Their certificate signing request (can be discarded)
│   └── sumsang-company-client.crt   # The client cert signed by root-client-ca
├── server-cas/               # Per‑team “server CA” keys & certs
│   ├── sumsang-company-server-ca.key  # Team’s private key for signing server certs
│   └── sumsang-company-server-ca.crt  # The public CA cert used to verify server certs
└── server-certs/             # Per‑team server certificates
    ├── sumsang-company-server.key     # Team’s server private key
    ├── sumsang-company-server.csr     # Their server CSR (usually not needed afterward)
    └── sumsang-company-server.crt     # The server cert signed by their server‑CA
```

---

### File types and roles

- **`.key` (private key)**  
  You must keep this secret.  
  - **Client key** (`*-client.key`): installed on each client/server that will *act* as a client when making outgoing connections.  
  - **Server key** (`*-server.key`): installed on each server that will *act* as a TLS server accepting inbound connections.  
  - **CA keys** (`*-ca.key`): used only during cert generation—never install these on your running services.

- **`.csr` (certificate signing request)**  
  Contains the public key + DN info that you send to a CA to get a cert. Once you have the signed `.crt`, you can safely delete or archive these; they’re not needed at runtime.

- **`.crt` (X.509 certificate)**  
  Contains the public key, identity (DN), validity period, and issuer signature.  
  - **Root CA cert** (`root-client-ca.crt`): distributed to *all* servers so they can verify incoming *client* certs.  
  - **Server CA cert** (`*-server-ca.crt`): distributed to *all* clients so they can verify incoming *server* certs.  
  - **Client cert** (`*-client.crt`): each server will present its own client cert when it *initiates* a connection.  
  - **Server cert** (`*-server.crt`): each server will present its server cert when it *accepts* a connection.

---

### Wiring into mTLS

1. **Trust stores**  
   - On every server that will *verify* client identities, import `root-client-ca.crt` into your TLS trust store.  
   - On every client (or server acting as a client) that will *verify* server identities, import each team’s `*-server-ca.crt` into its trust store.

2. **Key & cert installation**  
   - When *acting* as client, configure your TLS client library (curl, Java, Go, etc.) to use:
     ```
     --key   path/to/sumsang-company-client.key
     --cert  path/to/sumsang-company-client.crt
     ```
   - When *acting* as server, configure your TLS server library (nginx, Java, Go, etc.) to use:
     ```
     ssl_certificate      path/to/sumsang-company-server.crt;
     ssl_certificate_key  path/to/sumsang-company-server.key;
     ```

3. **mTLS handshake**  
   - The client presents its client cert; the server checks it against `root-client-ca.crt`.  
   - The server presents its server cert; the client checks it against `*-server-ca.crt`.  
   - Both sides now trust each other’s identity, and the encrypted channel is established.

---

With this layout and file‑type usage, adding new teams is as simple as dropping their `commonName` into the `TEAMS` dict and re‑running `generate_certs.py`.
