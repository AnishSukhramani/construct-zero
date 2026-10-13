# CZ Certified matrix

Profile: **cz-certified-v1**. Generated from `scripts/ci/certified-matrix.yaml`.

| OS | Python | Hermes pin | Backend | Client | Status |
|----|--------|------------|---------|--------|--------|
| Ubuntu 24.04 | 3.12 | upstream.lock.yaml | mock | none | CI-certified |
| Ubuntu 24.04 | 3.12 | upstream.lock.yaml | cursor | cline | advisory |
| macOS latest | 3.12 | upstream.lock.yaml | cursor | cline | advisory |
| WSL2 Ubuntu | 3.12 | upstream.lock.yaml | cursor | cline | community-reported |

Run locally: `./construct-zero doctor --certify [--json] [--offline]`.
