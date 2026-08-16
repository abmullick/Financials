# Parity Retirement Planner

A sophisticated, FastAPI-based retirement planning application designed to model and visualize long-term financial trajectories. It meticulously simulates annual corpus growth, inflation-adjusted retirement withdrawals, complex tax implications, and market stress scenarios. The application's core logic is engineered for parity with detailed spreadsheet-based financial models, offering users a powerful and intuitive web dashboard for comprehensive scenario analysis.

## Features

The planner is packed with features to provide a holistic view of your financial future:

### Core Planning & Projection
- **Year-by-Year Trajectory**: Generates a detailed annual projection of your wealth from your current age to life expectancy.
- **Accumulation & Depletion Phases**: Models distinct financial behaviors for pre-retirement (accumulation) and post-retirement (depletion) periods.
- **Inflation-Adjusted Expenses**: Automatically calculates the future cost of your current lifestyle by adjusting annual expenses for inflation.
- **Dynamic Contributions**: Supports modeling for annual increases in contributions during the accumulation phase.
- **Ad-Hoc Life Events**: Allows for planning one-time major expenses (e.g., a wedding, home purchase) at specific ages, adjusted for inflation.

### Advanced Financial Modeling
- **Sophisticated Tax Engine**: Calculates a blended effective tax rate based on a detailed portfolio allocation (Equity, Debt, Arbitrage) and equity sub-types (LTCG/STCG). It then computes the required **gross (pre-tax) withdrawal** to meet your **net (after-tax)** lifestyle expenses.
- **Stress Testing**: Simulates the impact of market downturns on your portfolio with "Mild Crash" (-10% returns) and "Severe Crash" (-20% returns) scenarios applied for the first two years of retirement.
- **Minimum Corpus Requirement**: Calculates the precise corpus needed at retirement to sustain your lifestyle until life expectancy, using a reverse present value analysis that accounts for all withdrawals, taxes, and market returns.

### Interactive Dashboard & Visualization
- **Intuitive UI**: A sleek, modern interface with light and dark modes for comfortable viewing.
- **Real-Time Simulation**: Instantly recalculates and updates all metrics and charts as you adjust input parameters.
- **Key Performance Indicators (KPIs)**: At-a-glance view of critical metrics like *Corpus at Retirement*, *Final Terminal Corpus*, *Peak Asset Age*, and *Minimum Corpus Required*.
- **Multi-Chart Visualization**: A rich dashboard with multiple charts to analyze:
    - **Wealth Growth & Depletion**: The complete trajectory of your net worth.
    - **Cash Flow Breakdown**: Annual contributions, withdrawals, and taxes.
    - **Portfolio & Tax Allocation**: Doughnut charts visualizing your asset mix and its contribution to the effective tax rate.
    - **Returns & Expenses**: Detailed line and bar charts for annual returns and expenses over time.
- **Detailed Ledger**: A comprehensive, scrollable table presenting the year-by-year financial breakdown, including opening/closing balances, contributions, withdrawals, and returns.

### Technical Excellence
- **API-Driven**: Built on a robust FastAPI backend that handles all complex calculations.
- **Pydantic Validation**: Ensures all user inputs are valid and logical before running a simulation, providing clear error feedback.
- **Workbook Parity Tested**: The calculation engine is rigorously tested against an equivalent spreadsheet model to ensure accuracy and reliability.

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
source ~/spark_venv/bin/activate
PYTHONPATH=. python3 -m unittest -v tests/test_retirement.py
```

Tests validate:
- Workbook parity for default scenarios
- Custom ad-hoc expense handling
- Tax calculation accuracy
- Minimum corpus requirement calculations
- Invalid planner inputs are rejected before the projection engine runs

## Example use case

A typical planning scenario:

```text
Current age: 23
Retirement age: 58
Life expectancy: 85
Current corpus: ₹100,000
Annual contribution: ₹200,000
Expense inflation: 6%
Return pre-retirement: 9%
Return post-retirement: 8%
```

This produces a yearly trajectory showing when the retirement corpus peaks, how much is required to sustain the lifestyle, and how stress scenarios affect long-term outcomes.

## Deployment

### Deploy on Render.com

1. Push your repository to GitHub
2. Connect your GitHub account to [Render.com](https://render.com)
3. Create a new Web Service and select your GitHub repository
4. Use the following settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd retirals && uvicorn src.main:app --host 0.0.0.0 --port 8080`
   - **Environment:** Python 3.11+
   - **Plan:** Free or Paid (Free tier has limitations)

Alternatively, use the `render.yaml` file in the repository for Infrastructure as Code deployment.

The application will be available at: `https://<your-render-app-name>.onrender.com`

### Temporary public sharing with ngrok

To expose the app over the internet temporarily:

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

The core calculation logic is a year-by-year simulation from the current age to life expectancy:

1.  **Initialization**: Starts with the current corpus and a map of all future ad-hoc expenses.
2.  **Annual Loop (Pre-Retirement)**:
    -   Calculates the annual contribution, factoring in the specified growth rate.
    -   Applies the pre-retirement return rate to the corpus after adding the contribution.
3.  **Annual Loop (Post-Retirement)**:
    -   **Calculate Net Withdrawal**: Determines the required after-tax withdrawal for the year by applying the inflation rate to the base annual expenses.
    -   **Calculate Blended Tax Rate**: Computes a single effective tax rate based on the defined portfolio allocation (Equity, Debt, Arbitrage) and their respective tax rates.
    -   **Calculate Gross Withdrawal**: "Grosses up" the net withdrawal amount to determine the pre-tax amount that must be withdrawn from the corpus to cover both the expenses and the taxes.
        -   `Gross Withdrawal = Net Withdrawal / (1 - Blended Tax Rate)`
    -   **Factor in Ad-Hoc Expenses**: Adds any inflation-adjusted ad-hoc expenses planned for the current year to the total outflow.
    -   **Apply Market Returns**:
        -   Applies the post-retirement return rate (or a negative stress-test rate for the first two years of retirement, if selected).
        -   The return is calculated on the corpus balance *after* all contributions and withdrawals for the year.
4.  **Closing Balance**: The closing corpus for one year becomes the opening corpus for the next.
5.  **Minimum Corpus Calculation**: After the main projection, the engine performs a reverse calculation. It starts from zero at life expectancy and works backward to the retirement age, determining the present value of all future outflows (grossed-up expenses and ad-hoc costs) to find the minimum corpus required at the start of retirement.

### Dashboard Features

- Real-time calculation results display
- Interactive parameter adjustment
- Multi-chart visualization of retirement trajectory
- Detailed year-by-year ledger table
- Key metrics summary (corpus at retirement, peak age, final corpus)
- Fully responsive design with light/dark theme support.

## Notes

This project implements the complete logic and interface of a spreadsheet-based retirement corpus planner. It provides financial advisors and individuals with an interactive tool for retirement scenario analysis, stress testing, and corpus adequacy validation.
