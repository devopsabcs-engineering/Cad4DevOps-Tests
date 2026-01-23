# Cad4DevOps-Tests

Tools and utilities for working with DevOps Shield SARIF assessments and GitHub Code Scanning integration.

## Overview

This repository contains scripts and sample data for cleaning and transforming DevOps Shield SARIF exports to be compatible with GitHub Code Scanning.

## Project Structure

```
├── docs/
│   └── sarif/
│       ├── devops-shield-assessment.sarif          # Original DevOps Shield export
│       └── devops-shield-assessment-cleaned.sarif  # GitHub-compatible version
├── scripts/
│   └── Clean-SarifForGitHub.py                     # SARIF cleaning utility
└── README.md
```

## Scripts

### Clean-SarifForGitHub.py

Transforms DevOps Shield SARIF exports to strict SARIF 2.1.0 specification compliance for GitHub Code Scanning.

**Problem:** DevOps Shield exports SARIF with non-standard properties that GitHub rejects during upload.

**Solution:** This script:
- Removes non-standard properties (`sarifNodeKind`, `propertyNames`, `tags`, etc.)
- Converts numeric enums to string values (level, kind, baselineState)
- Cleans location objects and removes invalid data
- Ensures strict SARIF 2.1.0 compliance

**Usage:**

```bash
# Output to a new file (recommended for comparison)
python scripts/Clean-SarifForGitHub.py input.sarif output.sarif

# Overwrite the input file
python scripts/Clean-SarifForGitHub.py input.sarif
```

**Example:**

```bash
python scripts/Clean-SarifForGitHub.py docs/sarif/devops-shield-assessment.sarif docs/sarif/devops-shield-assessment-cleaned.sarif
```

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## License

MIT
