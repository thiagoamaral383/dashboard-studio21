# Studio21 Data Extractor

Automated tool to extract reports from the Avec platform and organize them for Power BI analysis.

## Project Structure

- **src/**: Contains the main Python script (`main.py`).
- **config/**: Configuration files (`reports.json`, `.env`).
- **assets/**: Static assets like styles and Power BI themes.
- **reports/**: Output directory for downloaded Excel reports (ignored by Git).
- **.gitignore**: Specifies files to be ignored by version control.

## Setup

1. **Prerequisites**
   - Python 3.8+
   - Git

2. **Installation**
   ```bash
   # Clone the repository (if applicable)
   git clone <repository-url>
   cd Studio21

   # Create a virtual environment (optional but recommended)
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configuration**
   - Define environment variables in `config/.env`.
   - Protocol configuration for reports is in `config/reports.json`.

## Usage

Run the extraction script from the repository root:

```bash
python src/main.py
```

## Features

- **Backfill Capability**: Automatically downloads missing months for historical data.
- **Incremental Updates**: Checks what is already downloaded to avoid re-downloading existing data.
- **Secure**: Uses environment variables for credentials.
- **Configurable**: Reports are defined in `reports.json`, making it easy to add/remove reports without changing code.
