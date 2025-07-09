#!/usr/bin/env python3

# flake8: noqa

"""
mTLS Certificate Automation

This script automates the generation of:
  • A single self‑signed Root CA for signing both client and server certificates
  • Per‑team client keys, CSRs, and signed client certs
  • Per‑team server keys, CSRs, and signed server certs
  • Per‑team zip packages containing the required credentials

Usage:
  1. Customize the constants below (directories, key sizes, validity days, DN fields, extfile path).
  2. Populate the TEAMS dict with your team identifiers and their `commonName` (URL).
  3. Run: python3 ca.py
  4. Find all output under `certs/` and zipped bundles under `certs/zips/`

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
ROOT_CA_KEY: Path = BASE_DIR / "root-ca.key"
ROOT_CA_CRT: Path = BASE_DIR / "root-ca.crt"
CLIENT_DIR: Path = BASE_DIR / "provider-certs"
SERVER_DIR: Path = BASE_DIR / "server-certs"
ZIPS_DIR: Path = BASE_DIR / "zips"

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
    print(f"→ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def make_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def format_subj(dn: Dict[str, str], ou: Optional[str] = None, cn: Optional[str] = None) -> str:
    parts = [f"/{k}={v}" for k, v in dn.items()]
    if ou:
        parts.append(f"/OU={ou}")
    if cn:
        parts.append(f"/CN={cn}")
    return "".join(parts)

def generate_private_key(path: Path, size: int = KEY_SIZE) -> None:
    run_cmd(["openssl", "genrsa", "-out", str(path), str(size)])

def create_self_signed_ca(key: Path, crt: Path, subj: str, days: int = DAYS_VALID) -> None:
    run_cmd(["openssl", "req", "-new", "-x509", "-nodes", "-days", str(days), "-key", str(key), "-out", str(crt), "-subj", subj])

def create_csr(key: Path, csr: Path, subj: str) -> None:
    run_cmd(["openssl", "req", "-new", "-key", str(key), "-out", str(csr), "-subj", subj])

def sign_csr(csr: Path, ca_crt: Path, ca_key: Path, out_crt: Path, serial: int, days: int = DAYS_VALID, extfile: Optional[Path] = None) -> None:
    cmd = ["openssl", "x509", "-req", "-in", str(csr), "-days", str(days), "-CA", str(ca_crt), "-CAkey", str(ca_key), "-set_serial", f"{serial:02d}", "-out", str(out_crt)]
    if extfile and extfile.exists():
        cmd += ["-extfile", str(extfile)]
    run_cmd(cmd)

def create_zips() -> None:
    make_dir(ZIPS_DIR)
    readme = """# mTLS Certificate Bundle

This archive includes all credentials required for mutual TLS:

- <team>-client.key    :: Private key for your client authentication
- <team>-client.crt    :: Client certificate signed by root-ca.crt
- <team>-server.key    :: Private key for your server TLS endpoint
- <team>-server.crt    :: Server certificate signed by root-ca.crt
- root-ca.crt          :: Shared root certificate used to validate all other teams' certs
"""

    for team in TEAMS:
        zip_path = ZIPS_DIR / f"{team}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(CLIENT_DIR / f"{team}-client.key", arcname=f"{team}-client.key")
            zipf.write(CLIENT_DIR / f"{team}-client.crt", arcname=f"{team}-client.crt")
            zipf.write(SERVER_DIR / f"{team}-server.key", arcname=f"{team}-server.key")
            zipf.write(SERVER_DIR / f"{team}-server.crt", arcname=f"{team}-server.crt")
            zipf.write(ROOT_CA_CRT, arcname="root-ca.crt")
            zipf.writestr("README.md", readme.replace("<team>", team))
        print(f"✅ Created: {zip_path}")

# ─── Main Execution ───

def main() -> None:
    make_dir(BASE_DIR)
    make_dir(CLIENT_DIR)
    make_dir(SERVER_DIR)

    # Root CA generation
    if not ROOT_CA_KEY.exists():
        generate_private_key(ROOT_CA_KEY)
        subj = format_subj(DN_COMMON, ou="RootCA", cn="RootCA")
        create_self_signed_ca(ROOT_CA_KEY, ROOT_CA_CRT, subj)
    else:
        print(f"Root CA already exists at {ROOT_CA_CRT}")

    for idx, (team, cfg) in enumerate(TEAMS.items(), start=1):
        print(f"\n\033[94m----- Generating certs for {team} -----\033[0m")
        cn = cfg["commonName"]

        # Client cert
        client_key = CLIENT_DIR / f"{team}-client.key"
        client_csr = CLIENT_DIR / f"{team}-client.csr"
        client_crt = CLIENT_DIR / f"{team}-client.crt"

        generate_private_key(client_key)
        subj = format_subj(DN_COMMON, ou=team, cn=cn)
        create_csr(client_key, client_csr, subj)
        sign_csr(client_csr, ROOT_CA_CRT, ROOT_CA_KEY, client_crt, serial=idx)

        # Server cert
        server_key = SERVER_DIR / f"{team}-server.key"
        server_csr = SERVER_DIR / f"{team}-server.csr"
        server_crt = SERVER_DIR / f"{team}-server.crt"

        generate_private_key(server_key)
        subj_srv = format_subj(DN_COMMON, ou=team, cn=cn)
        create_csr(server_key, server_csr, subj_srv)
        sign_csr(server_csr, ROOT_CA_CRT, ROOT_CA_KEY, server_crt, serial=idx, extfile=EXTFILE)

    print("\n\033[92mAll certificates generated successfully.\033[0m")
    create_zips()
    print("\nAll team bundles zipped in:", ZIPS_DIR)

if __name__ == "__main__":
    main()