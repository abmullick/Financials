# Parity Retirement Planner
# With Deterministic Model
A sophisticated, FastAPI-based retirement planning application designed to model and visualize long-term financial trajectories. It meticulously simulates annual corpus growth, inflation-adjusted retirement withdrawals, complex tax implications, and market stress scenarios. The application's core logic is engineered for parity with detailed spreadsheet-based financial models, offering users a powerful and intuitive web dashboard for comprehensive scenario analysis. This tool is ideal for financial advisors and individuals seeking a clear, data-driven understanding of their retirement readiness.

## Key Features at a Glance

| Category | Feature | Description |
| :--- | :--- | :--- |
| **Core Projection** | **Year-by-Year Simulation** | Generates a detailed annual projection of wealth from current age to life expectancy, forming the foundation of the plan. |
| | **Inflation & Growth** | Automatically models inflation on expenses and growth on pre-retirement contributions to reflect real-world changes. |
| | **Ad-Hoc Life Events** | Plan for one-time major expenses (e.g., wedding, home purchase) at specific ages, entered in today's money and correctly inflated. |
| **Advanced Modeling** | **Sophisticated Tax Engine** | Accurately calculates a blended effective tax rate based on portfolio allocation and applies the annual LTCG exemption correctly. |
| | **Market Stress Testing** | Simulates the impact of a "Mild" (-10%) or "Severe" (-20%) market crash on the portfolio during the first two years of retirement. |
| | **Minimum Corpus Goal** | Determines the precise corpus needed at retirement using a reverse present value analysis, providing a clear target for your savings. |
| **Advisory & Goal-Seek** | **Retirement Readiness Score** | Instantly shows readiness as a percentage (Projected Corpus vs. Minimum Required), with color-coded feedback. |
| | **Target Contribution Solver** | If there's a gap, the engine calculates the exact new annual contribution needed to achieve 100% readiness. |
| | **Required Return Solver** | Alternatively, it solves for the pre- or post-retirement return rates required to close any retirement gap. |
| **Visualization** | **Interactive Dashboard** | A sleek, modern UI with real-time updates, conditional coloring for key metrics, and light/dark modes. |
| | **Multi-Chart Visualization** | Includes dynamic charts for wealth trajectory, annual cash flow, and portfolio allocation over time. |
| | **Detailed Financial Ledger** | A comprehensive, scrollable table presenting the year-by-year financial breakdown for in-depth analysis. |

## How It Works

The application is built with a clean, API-driven architecture.

1.  **Frontend**: A single, dynamic `index.html` file provides an interactive user interface for inputting financial parameters.
2.  **Backend**: A FastAPI server exposes a `/calculate` endpoint.
4.  **Data Flow**: When the user runs a simulation, the frontend sends a JSON payload to the backend. The backend validates this data using Pydantic models (including `AdHocExpense` for ad-hoc expenses) and passes it to the `retirement_engine`.
4.  **Calculation Engine**: The engine performs a year-by-year simulation, calculates all metrics, and returns the complete projection and analysis back to the frontend.
5.  **Visualization**: The frontend uses Chart.js to render the received data into a rich, multi-chart dashboard and a detailed ledger table.

## Project Structure

```text
financials/
├── README.md
├── render.yaml
├── requirements.txt
├── start.sh
└── retirals/
    ├── src/
    │   ├── __init__.py
    │   ├── main.py              # FastAPI application entrypoint
    │   ├── models.py            # Pydantic data models and validation
    │   ├── retirement_engine.py # Core projection, gap, and goal-seek logic
    │   ├── stress_engine.py     # Logic for applying market stress scenarios
    │   ├── tax_engine.py        # Blended tax rate calculation logic
    │   └── static/
    │       └── index.html       # Single-page interactive web dashboard
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

To run the application, navigate to the `retirals` directory and use `uvicorn`. This is the standard method for running ASGI applications like FastAPI and correctly handles Python's package structure.

```bash
cd /home/abmul/projects/financials/retirals
# Activate your virtual environment
source ~/spark_venv/bin/activate  # or source ../.venv/bin/activate
uvicorn src.main:app --reload --port 20080
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
- Custom ad-hoc expense handling and inflation
- Market stress scenarios (mild and severe crashes)
- Zero return and zero inflation edge cases
- Tax calculation accuracy
- LTCG exemption logic
- Minimum corpus requirement calculations
- Peak asset age and final corpus calculations
- Invalid planner inputs are rejected before the projection engine runs
- Correctness of retirement duration and projection points

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
   - **Start Command:** `bash start.sh`
   - **Environment:** Python 3.11+
   - **Plan:** Free or Paid (Free tier has limitations)

Make sure your `start.sh` script is executable (`chmod +x start.sh`) before pushing to GitHub.
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
3.  **Annual Loop (Post-Retirement)**: The engine models withdrawals to cover living expenses.
    -   **Calculate Net Withdrawal**: Determines the required after-tax amount for the year by applying the inflation rate to base expenses.
    -   **Factor in Ad-Hoc Expenses**: Adds any inflation-adjusted ad-hoc expenses planned for the current year.
    -   **Calculate Gross Withdrawal**: "Grosses up" the net withdrawal to find the pre-tax amount needed. This uses a sophisticated piecewise function that correctly applies the annual LTCG exemption only when the LTCG portion of the withdrawal exceeds the threshold.
    -   **Apply Market Returns**: Applies the post-retirement return rate (or a stress-test rate) to the corpus balance *after* all withdrawals for the year.
4.  **Closing Balance**: The closing corpus for one year becomes the opening corpus for the next, continuing until life expectancy.
5.  **Minimum Corpus & Goal-Seek**: After the main projection, the engine performs a reverse calculation (from life expectancy backward) to find the minimum corpus required at retirement. It then uses this target to perform the "goal-seek" analysis for contributions and returns.

### Dashboard Features

- Real-time calculation results display
- Interactive parameter adjustment, with clear labels for ad-hoc expenses (in today's money).
- Multi-chart visualization of retirement trajectory
- Detailed year-by-year ledger table
- Key metrics summary (corpus at retirement, peak asset age, retirement span, final corpus) with conditional green/amber/red coloring for goal-oriented feedback.
- Fully responsive design with light/dark theme support (defaulting to light mode).

## Notes

This project implements the complete logic and interface of a spreadsheet-based retirement corpus planner. It provides financial advisors and individuals with an interactive tool for retirement scenario analysis, stress testing, and corpus adequacy validation.
