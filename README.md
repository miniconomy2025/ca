### Generated file structure:
```
certs/
├── root-ca.key                      # Private key of the shared root CA (kept secret, used only during signing)
├── root-ca.crt                      # Public root CA certificate (distributed to all teams for verification)
├── provider-certs/                  # Per‑team client certificates
│   ├── sumsang-company-client.key   # Team’s client private key
│   ├── sumsang-company-client.csr   # Their client certificate signing request
│   └── sumsang-company-client.crt   # The client cert signed by root-ca
├── server-certs/                    # Per‑team server certificates
│   ├── sumsang-company-server.key   # Team’s server private key
│   ├── sumsang-company-server.csr   # Their server certificate signing request
│   └── sumsang-company-server.crt   # The server cert signed by root-ca
└── zips/                            # Zip bundles per team, containing all deployment files
```

---

### File types and roles

- **`*.key` (private key)**
  You must keep this secret.
  - **Client key** (`*-client.key`): used when making outbound connections.
  - **Server key** (`*-server.key`): used when accepting inbound connections.
  - **CA key** (`root-ca.key`): used only for certificate signing—never distributed or deployed.

- **`*.csr` (certificate signing request)**
  Used during certificate creation. Includes public key and identity information.
  These can be deleted after use—they’re not needed in production.

- **`*.crt` (X.509 certificate)**
  Verifiable identity + public key + CA signature.

  * **Root CA cert** (`root-ca.crt`): shared trust anchor, used to verify both server and client certificates.
  * **Client cert** (`*-client.crt`): used when initiating requests to other services.
  * **Server cert** (`*-server.crt`): used when accepting connections.

---

### Wiring into mTLS

1. **Trust stores**
  - Every service must trust `root-ca.crt` to verify incoming *client* and *server* certificates.

2. **Key & cert installation**
  - When *acting* as a client (initiating requests), configure your TLS client to use:

    ```
    --key   path/to/<team>-client.key
    --cert  path/to/<team>-client.crt
    --cacert path/to/root-ca.crt
    ```
  - When *acting* as a server (receiving connections), configure your TLS server to use:

    ```
    ssl_certificate      path/to/<team>-server.crt;
    ssl_certificate_key  path/to/<team>-server.key;
    ssl_client_certificate path/to/root-ca.crt;
    ssl_verify_client    on;
    ```

3. **mTLS handshake**
  - The server presents its server certificate signed by `root-ca.crt`, and the client verifies it.
  - The client presents its client certificate signed by `root-ca.crt`, and the server verifies it.
  - If both certs are valid and trusted, a secure mTLS channel is established.

---

## Example mTLS Interaction: team-a ➝ team-b

1. `team-a` initiates a TLS connection to `team-b.com` using the IP or DNS of `team-b`'s server.
2. `team-b` sends its server certificate (`team-b-server.crt`) to `team-a` as part of the TLS handshake.
3. `team-a` verifies `team-b-server.crt` by checking:
  - It was signed by the shared `root-ca.crt`
  - The CN or SAN matches `team-b.com`
4. `team-a` then presents its own client certificate (`team-a-client.crt`) to `team-b` during the same handshake.
5. `team-b` verifies `team-a-client.crt` by checking:
  - It was signed by the same shared `root-ca.crt`
  - The certificate subject (e.g., CN/OU) matches the expected client identity
6. If all checks pass on both sides, a secure mutual TLS (mTLS) channel is established.