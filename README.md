# Dynamic Retirement Corpus Planner

A FastAPI-based retirement planning dashboard that models annual corpus growth, retirement withdrawals, tax effects, and stress scenarios. The application is aligned to the workbook logic and presents a multi-chart dashboard for planning and scenario analysis.

## Features

- Retirement corpus projection by age
- Pre-retirement and post-retirement return modeling
- Inflation-adjusted annual withdrawals
- Ad-hoc expense events
- LTCG tax estimation and exemption logic
- Stress test scenarios
- Multi-chart dashboard with trajectory and cash-flow views
- Ledger table for annual projection details

## Project structure

```text
financials/
├── README.md
├── .gitignore
└── retirals/
    ├── src/
    │   ├── main.py
    │   └── static/
    │       └── index.html
    └── tests/
        └── test_retirement.py
```

## Requirements

- Python 3.10+
- Virtual environment recommended
- FastAPI
- Pydantic
- Uvicorn

## Setup

Create and activate a virtual environment:

```bash
cd /home/abmul/projects/financials
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install fastapi uvicorn pydantic
```

## Run the app

```bash
cd /home/abmul/projects/financials/retirals
source ~/spark_venv/bin/activate
python src/main.py
```

Then open:

```text
http://localhost:20080/
```

## Run tests

```bash
cd /home/abmul/projects/financials/retirals
source ~/spark_venv/bin/activate
python -m unittest -v tests/test_retirement.py
```

## Public sharing

To expose the app over the internet temporarily, use ngrok:

```bash
ngrok http 20080
```

This will generate a public URL that forwards to your local app.

## Product owner

- Abhisek Basu Mullick
- abmullick@gmail.com

## Notes

This project is designed to mirror the logic and output structure of the spreadsheet-based retirement corpus planner and provides a web interface for simulation and visual review.
