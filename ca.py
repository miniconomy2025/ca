#!/usr/bin/env python3

# flake8: noqa

"""
mTLS Certificate Automation

This script automates the generation of:
  • A self‑signed "root" CA for client certs
  • Per‑team client keys, CSRs, and signed client certs
  • Per‑team "server" CAs, server keys, CSRs, and signed server certs

Usage:
  1. Customize the constants below (directories, key sizes, validity days, DN fields, extfile path).
  2. Populate the TEAMS dict with your team identifiers and their `commonName` (URL).
  3. Run: python3 generate_certs.py
  4. Find all output under the specified certs/ subdirectories.

Requirements:
  • OpenSSL installed and on your PATH
  • Python 3.7+ (for typing)
"""

import subprocess
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

# ─── Global Configuration ────────────────────────────────────────────────────

KEY_SIZE: int = 2048  # Bits for each RSA key
DAYS_VALID: int = 1000  # Validity of all certs in days

BASE_DIR: Path = Path("certs")
CLIENT_CA_KEY: Path = BASE_DIR / "root-client-ca.key"
CLIENT_CA_CRT: Path = BASE_DIR / "root-client-ca.crt"
PROVIDER_DIR: Path = BASE_DIR / "provider-certs"
SERVER_CA_DIR: Path = BASE_DIR / "server-cas"
SERVER_CERT_DIR: Path = BASE_DIR / "server-certs"

# Optional OpenSSL extension file for server certs (set to None to skip)
EXTFILE: Optional[Path] = Path("bbdgradproject.ext")

# DN fields common to everyone
DN_COMMON: Dict[str, str] = {
    "C":  "ZA",
    "ST": "Gauteng",
    "L":  "Johannesburg",
    "O":  "Miniconomy",
}

# Per-team configuration
TEAMS: Dict[str, Dict[str, str]] = {
    "electronics-supplier": { "commonName": "electronics-supplier-api.projects.bbdgrad.com" },
    "screen-supplier":      { "commonName": "screen-supplier-api.projects.bbdgrad.com" },
    "case-supplier":        { "commonName": "case-supplier-api.projects.bbdgrad.com" },

    "bulk-logistics":       { "commonName": "bulk-logistics-api.projects.bbdgrad.com" },
    "consumer-logistics":   { "commonName": "consumer-logistics-api.projects.bbdgrad.com" },

    "pear-company":         { "commonName": "pear-company-api.projects.bbdgrad.com" },
    "sumsang-company":      { "commonName": "sumsang-phones-api.projects.bbdgrad.com" },

    "commercial-bank":      { "commonName": "commercial-bank-api.projects.bbdgrad.com" },
    "retail-bank":          { "commonName": "retail-bank-api.projects.bbdgrad.com" },

    "thoh":                 { "commonName": "thoh-api.projects.bbdgrad.com" },
    "recycler":             { "commonName": "recycler-api.projects.bbdgrad.com" },
}

# ─── Helper Functions ────────────────────────────────────────────────────────

def run_cmd(cmd: List[str]) -> None:
    """Run a subprocess command, raising on failure."""
    print(f"→ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def make_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def format_subj(dn: Dict[str, str], ou: Optional[str] = None, cn: Optional[str] = None) -> str:
    """
    Build an OpenSSL subject string from DN_COMMON plus optional OU and CN.
    E.g.: /C=ZA/ST=Gauteng/L=Johannesburg/O=Miniconomy/OU=team/CN=team.com
    """
    parts = [f"/{k}={v}" for k, v in DN_COMMON.items()]
    if ou:
        parts.append(f"/OU={ou}")
    if cn:
        parts.append(f"/CN={cn}")
    return "".join(parts)


def generate_private_key(path: Path, size: int = KEY_SIZE) -> None:
    run_cmd(["openssl", "genrsa", "-out", str(path), str(size)])


def create_self_signed_ca(key: Path, crt: Path, subj: str, days: int = DAYS_VALID) -> None:
    run_cmd([
        "openssl", "req", "-new", "-x509", "-nodes",
        "-days", str(days),
        "-key", str(key),
        "-out", str(crt),
        "-subj", subj
    ])


def create_csr(key: Path, csr: Path, subj: str) -> None:
    run_cmd([
        "openssl", "req", "-new",
        "-key", str(key),
        "-out", str(csr),
        "-subj", subj
    ])


def sign_csr(
    csr: Path,
    ca_crt: Path,
    ca_key: Path,
    out_crt: Path,
    serial: int,
    days: int = DAYS_VALID,
    extfile: Optional[Path] = None
) -> None:
    cmd = [
        "openssl", "x509", "-req",
        "-in", str(csr),
        "-days", str(days),
        "-CA", str(ca_crt),
        "-CAkey", str(ca_key),
        "-set_serial", f"{serial:02d}",
        "-out", str(out_crt)
    ]
    # Only add extfile if provided and exists
    if extfile and extfile.exists():
        cmd += ["-extfile", str(extfile)]
    run_cmd(cmd)

ZIPS_DIR: Path = BASE_DIR / "zips"


def create_zips() -> None:
    """Package all required certs/keys into per-team zip files for deployment."""
    make_dir(ZIPS_DIR)
    readme_content = """# mTLS Deployment Certificate Package

This archive contains all credentials and verification files required to run your mTLS-enabled service:

- `<team>-client.key`    :: Your private client key
- `<team>-client.crt`    :: Your signed client certificate
- `<team>-server.key`    :: Your private server key
- `<team>-server.crt`    :: Your signed server certificate
- `<team>-server-ca.crt` :: Your local CA certificate
- `root-client-ca.crt`   :: Shared root CA for validating other teams' certificates
"""

    for team in TEAMS:
        zip_path = ZIPS_DIR / f"{team}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            # Client key, CSR, signed cert
            zipf.write(PROVIDER_DIR / f"{team}-client.key", arcname=f"{team}-client.key")
            zipf.write(PROVIDER_DIR / f"{team}-client.crt", arcname=f"{team}-client.crt")
            zipf.write(CLIENT_CA_CRT, arcname="root-client-ca.crt")

            # Server key, signed cert, and CA
            zipf.write(SERVER_CERT_DIR / f"{team}-server.key", arcname=f"{team}-server.key")
            zipf.write(SERVER_CERT_DIR / f"{team}-server.crt", arcname=f"{team}-server.crt")
            zipf.write(SERVER_CA_DIR / f"{team}-server-ca.crt", arcname=f"{team}-server-ca.crt")
            zipf.writestr("README.txt", readme_content.replace("<team>", team))

        print(f"✅ Created: {zip_path}")

def main() -> None:
    # Prepare directories
    make_dir(BASE_DIR)
    make_dir(PROVIDER_DIR)
    make_dir(SERVER_CA_DIR)
    make_dir(SERVER_CERT_DIR)

    # Generate Root CA for client certs (once)
    if not CLIENT_CA_KEY.exists():
        generate_private_key(CLIENT_CA_KEY)
        subj = format_subj(DN_COMMON, ou="RootClientCA", cn="RootClientCA")
        create_self_signed_ca(CLIENT_CA_KEY, CLIENT_CA_CRT, subj)
    else:
        print(f"Root client CA already exists at {CLIENT_CA_CRT}")

    # Loop over each team
    for idx, (team, cfg) in enumerate(TEAMS.items(), start=1):
        print(f"\n\033[94m----- Generating {team} certificates -----\033[0m")
        cn = cfg["commonName"]

        # Client certificate
        client_key = PROVIDER_DIR / f"{team}-client.key"
        client_csr = PROVIDER_DIR / f"{team}-client.csr"
        client_crt = PROVIDER_DIR / f"{team}-client.crt"

        generate_private_key(client_key)
        subj = format_subj(DN_COMMON, ou=team, cn=cn)
        create_csr(client_key, client_csr, subj)
        sign_csr(client_csr, CLIENT_CA_CRT, CLIENT_CA_KEY, client_crt, serial=idx)

        # Server CA
        server_ca_key = SERVER_CA_DIR / f"{team}-server-ca.key"
        server_ca_crt = SERVER_CA_DIR / f"{team}-server-ca.crt"
        if not server_ca_key.exists():
            generate_private_key(server_ca_key)
            subj_ca = format_subj(DN_COMMON, ou=team, cn=f"{team}-ServerCA")
            create_self_signed_ca(server_ca_key, server_ca_crt, subj_ca)

        # Server certificate
        server_key = SERVER_CERT_DIR / f"{team}-server.key"
        server_csr = SERVER_CERT_DIR / f"{team}-server.csr"
        server_crt = SERVER_CERT_DIR / f"{team}-server.crt"

        generate_private_key(server_key)
        subj_srv = format_subj(DN_COMMON, ou=team, cn=cn)
        create_csr(server_key, server_csr, subj_srv)
        sign_csr(server_csr, server_ca_crt, server_ca_key, server_crt, serial=idx, extfile=EXTFILE)

    print("\n\033[92mAll certificates generated successfully.\033[0m")


    create_zips()
    print("All team files zipped under:", ZIPS_DIR)


if __name__ == "__main__":
    main()
