# OCHA MOU CBPF Data Pipeline

A reproducible Python workflow for downloading, filtering, and organizing official United Nations Office for the Coordination of Humanitarian Affairs (OCHA) Country-Based Pooled Fund (CBPF) data in support of analysis related to the December 2025 U.S.–UN humanitarian funding agreement.

---

## Overview

This repository downloads the latest available data directly from the official OCHA Country-Based Pooled Funds (CBPF) API and automatically builds an Excel workbook for analysis.

The workflow was developed to answer questions such as:

* Which OCHA Country-Based Pooled Funds (CBPFs) received U.S. Government (USG) contributions?
* What projects were broadly funded through those pooled funds?
* Which organizations are implementing projects within those pooled funds?
* What humanitarian activities are being supported across U.S.-supported CBPFs?

The workbook is regenerated each time the script is run, ensuring the analysis reflects the latest data available from OCHA.

<img width="1972" height="1718" alt="usg_cbpf_contributions_by_country" src="https://github.com/user-attachments/assets/a6c4892a-fa38-4370-af94-969ac3fe2e68" />


---

## Data Sources

This repository uses two official UN OCHA CBPF API endpoints.

### 1. Project Summary

Provides the master list of approved CBPF projects.

API endpoint:

```
https://cbpfapi.unocha.org/vo1/odata/ProjectSummary?$format=csv
```

This endpoint includes:

* Project title
* Implementing organization
* Allocation year
* Budget
* Project status
* Project summary
* Pooled Fund
* Sector / Cluster
* Geographic information
* Beneficiary information

Removing the `poolfundAbbrv` parameter returns projects from **all** Country-Based Pooled Funds.

---

### 2. Contribution

Provides donor contributions to CBPFs.

API endpoint:

```
https://cbpfapi.unocha.org/vo1/odata/Contribution?$format=csv&includeTransfer=1
```

This endpoint includes:

* Donor
* Fiscal year
* Contribution amount
* Paid amount
* Pooled Fund
* Contribution code

Removing the `poolfundAbbrv` parameter returns contribution records for **all** Country-Based Pooled Funds.

---

## Methodology

The script performs the following steps:

1. Downloads the latest Project Summary dataset.
2. Downloads the latest Contribution dataset.
3. Filters the Contribution dataset where:

```
DonorName == "United States"
FiscalYear == 2026
```

4. Identifies the CBPFs that received U.S. Government contributions.
5. Creates a funding summary.
6. Creates one worksheet for each CBPF receiving U.S. funding.
7. Writes a complete Excel workbook.

---

## Workbook Structure

The generated workbook contains:

| Worksheet               | Description                                                          |
| ----------------------- | -------------------------------------------------------------------- |
| README_Methodology      | Data sources and methodology                                         |
| Funding                 | Summary of FY2026 U.S. Government CBPF contributions                 |
| RAW_CBPF_ProjectSummary | Complete Project Summary dataset from OCHA                           |
| RAW_CBPF_Contribution   | Complete Contribution dataset from OCHA                              |
| USG_CBPF_Contrib_2026   | Filtered U.S. Government contribution records                        |
| CBPF_*                  | One worksheet for each CBPF receiving FY2026 U.S. Government funding |

Example worksheets:

* CBPF_Sudan
* CBPF_Ukraine
* CBPF_Syria
* CBPF_South Sudan
* CBPF_Myanmar
* CBPF_Nigeria
* CBPF_Ethiopia

---

## Important Interpretation

Country-Based Pooled Funds (CBPFs) are pooled financing mechanisms.

This repository **does not** identify direct U.S. funding to individual projects.

Instead, it identifies:

> Projects implemented through pooled funds that received U.S. Government contributions.

The resulting workbook should therefore be interpreted as showing activities financed through U.S.-supported pooled funds rather than direct bilateral project awards.

---

## Updating the Workbook

Clone the repository:

```bash
git clone https://github.com/stoic9-observ/ocha-mou-cbpf-cerf-data.git
cd ocha-mou-cbpf-cerf-data
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the pipeline:

```bash
python3 scripts/build_usg_workbook.py
```

The script automatically downloads the latest CBPF data and creates:

```
output/UNOCHA_USG_Pooled_Funds_2026.xlsx
```

No manual data cleaning is required.

---

## Repository Structure

```
ocha-mou-cbpf-cerf-data/

├── README.md
├── requirements.txt
├── scripts/
│   └── build_usg_workbook.py
└── output/
    └── UNOCHA_USG_Pooled_Funds_2026.xlsx
```

---
## 🚀 Quick Start

Clone the repository:

```bash
git clone https://github.com/stoic9-observ/ocha-mou-cbpf-cerf-data.git
cd ocha-mou-cbpf-cerf-data
```

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the workbook update script:

```bash
python scripts/update_unocha_workbook.py
```

The updated workbook will be saved to:

```text
output/UNOCHA_USG_Pooled_Funds_2026.xlsx
```
---

## Future 

Need to add:

* Integration of the OCHA Central Emergency Response Fund (CERF) data.
* Time-series analysis of U.S. Government contributions.
* Geographic mapping of USG pooled fund activities.

---

## License

The source data are provided by the United Nations Office for the Coordination of Humanitarian Affairs (OCHA). Users should consult OCHA's applicable terms of use for the underlying datasets.

This repository contains code to automate retrieval, organization, and analysis of publicly available OCHA data.
