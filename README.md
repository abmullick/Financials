# Parity Retirement Planner

A FastAPI-based retirement planning application that models annual corpus growth, retirement withdrawals, tax effects, and stress scenarios. The application logic mirrors a spreadsheet-based planner and provides a comprehensive web dashboard for scenario analysis and visualization.

## Features

- Real-time retirement corpus projection year-by-year
- Pre-retirement and post-retirement investment return modeling
- Inflation-adjusted annual withdrawal calculations
- Ad-hoc expense event handling
- LTCG (Long-Term Capital Gains) tax estimation with exemption logic
- Stress test scenarios (mild and severe market crashes)
- Minimum corpus requirement calculation using present value analysis
- Interactive web dashboard with retirement trajectory visualization
- Comprehensive annual ledger with detailed cash flow breakdowns
- Fully tested with workbook parity validation

## Project structure

```text
financials/
├── README.md
└── retirals/
    ├── assets/
    │   └── logo.png
    ├── src/
    │   ├── main.py              # FastAPI application with retirement calculation engine
    │   └── static/
    │       └── index.html       # Interactive web dashboard
    └── tests/
        └── test_retirement.py   # Unit tests with workbook parity validation
```

## Requirements

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic

## Setup

### Create and activate a virtual environment

```bash
cd /home/abmul/projects/financials
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install fastapi uvicorn pydantic
```

## Run the app

```bash
cd /home/abmul/projects/financials/retirals
# Activate your virtual environment
source ~/spark_venv/bin/activate  # or source ../.venv/bin/activate
python src/main.py
```

The application will start at:

```
http://localhost:20080/
```

Open this URL in your browser to access the interactive dashboard.

## Run tests

```bash
cd /home/abmul/projects/financials/retirals
# Activate your virtual environment
source ~/spark_venv/bin/activate  # or source ../.venv/bin/activate
python -m unittest -v tests/test_retirement.py
```

Tests validate:
- Workbook parity for default scenarios
- Custom ad-hoc expense handling
- Tax calculation accuracy
- Minimum corpus requirement calculations

## Public sharing

To expose the app over the internet temporarily, use ngrok:

```bash
ngrok http 20080
```

This will generate a public URL that forwards to your local app.

## Product owner

- Abhisek Basu Mullick
- abmullick@gmail.com

## Technical Details

### API Endpoints

- **POST /calculate** - Accepts retirement planning parameters and returns full projection
  - Input: `PlannerInputs` model with age, corpus, contribution, expense, and scenario parameters
  - Output: Metrics summary and year-by-year projection table

- **GET /** - Serves the interactive web dashboard

### Calculation Engine

The core calculation logic:
1. Iterates through each year from current age to life expectancy
2. Applies contribution growth during pre-retirement phase
3. Calculates inflation-adjusted expenses during retirement
4. Applies LTCG tax on investment gains with exemption logic
5. Models stress scenarios with market crash simulations
6. Computes minimum corpus requirement using present value analysis

### Dashboard Features

- Real-time calculation results display
- Interactive parameter adjustment
- Multi-chart visualization of retirement trajectory
- Detailed year-by-year ledger table
- Key metrics summary (corpus at retirement, peak age, final corpus)
- Responsive design with light/dark theme support

## Notes

This project implements the complete logic and interface of a spreadsheet-based retirement corpus planner. It provides financial advisors and individuals with an interactive tool for retirement scenario analysis, stress testing, and corpus adequacy validation.
