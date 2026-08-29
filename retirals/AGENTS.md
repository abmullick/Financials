# AGENTS.md — Development Rules for Retirement Corpus Planner

This document establishes strict guardrails for all AI-assisted and human development
on this project. It exists because this is a **production financial application** with
deterministic calculation logic, regulatory-sensitive tax mathematics, and a large
frontend surface area. Unintended changes to core logic or API contracts can cause
silent financial miscalculations for users.

---

## 1. MINIMAL CHANGES

- Modify the smallest possible number of files to accomplish the requested task.
- Do not refactor unrelated code.
- Do not rewrite working code merely to make it "cleaner" or "more maintainable."
- Do not change architecture, directory structure, or module organization unless
  explicitly requested by the user.
- Prefer adding new files over modifying existing ones when the change is additive.

## 2. SCOPE FIRST

Before making any changes:

- Identify the exact feature or bug being addressed.
- Identify the files and functions responsible for that feature.
- State which files will be modified and why.
- Do not modify files outside that stated scope.
- If the scope is ambiguous, default to the smallest possible change.

## 3. PROTECTED CORE

The following are **protected by default**. Do not modify them unless the user
explicitly requests a change to that specific area:

- `src/models.py` — data contracts, Pydantic validators, enums
- `src/retirement_engine.py` — all deterministic projection, tax, and Monte Carlo logic
- `src/ai_insights.py` — AI insight service layer and numerical validation
- All existing test files — `test_engine.py`, `tests/test_retirement.py`,
  `test_ai_insights.py`, `test_api.py`, `validate_export.py`

A UI request must **never** result in modifications to financial calculation code.
A backend request must **never** result in modifications to frontend UI code unless
explicitly requested.

## 4. FINANCIAL CORRECTNESS

- Never move financial calculations into frontend JavaScript.
- All retirement projections, tax calculations, corpus exhaustion logic, gap analysis,
  and goal-seek calculations must remain in `retirement_engine.py`.
- Financial calculations must remain deterministic and testable.
- Do not change return formulas, tax formulas, or contribution/inflation logic
  without explicit user approval and a full test run.
- Never "simplify" tax or projection math to make frontend code easier.

## 5. AI INSIGHTS

- AI Insights interpret deterministic financial results. They are not the source of truth.
- Do not allow AI-generated content to influence or modify financial calculations.
- The numerical validation layer in `ai_insights.py` exists to prevent hallucinated
  numbers from reaching users. Do not weaken or bypass it.
- Changes to AI prompts, prompt builders, or response validators must preserve the
  existing JSON schema contract (`AIInsightResponse`).

## 6. API CONTRACTS

- Do not change API request/response structures unless explicitly requested.
- The JSON shapes returned by `/calculate`, `/calculate-mc`, and `/api/ai-insight`
  are consumed by the frontend and tests. Changing field names, types, or nesting
  breaks both.
- If an API change is necessary, explain the impact on the frontend and tests
  before implementing it.
- Do not add required fields to request payloads without updating the frontend
  payload builder and tests.

## 7. FRONTEND

- Avoid adding more JavaScript to `src/static/index.html`.
- Feature-specific JavaScript should live in feature-specific modules (e.g., `js/`).
- Do not rename DOM element IDs, CSS class names, or `localStorage` keys that are
  referenced by existing JavaScript or CSS.
- Do not change the `id` attributes of Chart.js canvases without updating every
  corresponding `makeLineChart` / `makeBarChart` / `makeDoughnutChart` call.
- CSS changes must preserve the `theme-light` class behavior and all CSS custom
  properties (`--bg-1`, `--text-1`, etc.).
- The landing screen (`#landingScreen`), planner app (`#plannerApp`), and
  `#launchPlannerBtn` click handler are part of the core user flow. Do not remove
  or rename them without explicit approval.

## 8. TESTS

- Never delete or weaken existing tests to make them pass.
- Add regression tests for bug fixes.
- Run relevant tests after any change to calculation or API code.
- If a test fails, investigate the actual cause. Do not modify the test to match
  broken behavior.
- Exact decimal assertions in tests (e.g., `assertAlmostEqual(metrics["corpus_at_retirement"], 42131033.64)`)
  are intentional. Do not change them unless the underlying calculation intentionally changes.

## 9. GIT SAFETY

Before finishing any change:

- Inspect `git diff`.
- Confirm only intended files were changed.
- Summarize every modified file and why it was modified.
- Do not leave debug code, console logs, or commented-out code in committed changes.
- Do not commit secrets, API keys, or environment variables.

## 10. STOP CONDITION

Once the requested change is implemented and tested, **stop**.
- Do not perform unrelated cleanup or refactoring.
- Do not "fix" things that were not part of the request.
- Do not reformat code unless explicitly asked.
- If you notice an unrelated issue, note it and report it, but do not fix it.

---

## AMBIGUOUS REQUESTS

When a request is ambiguous, the safest interpretation is to make the **smallest
possible change** that satisfies the literal request without side effects.

Examples:
- "Fix the retirement planner" → Ask for clarification. Do not guess.
- "Clean up the codebase" → Do nothing unless given a specific target.
- "Make the UI better" → Make the smallest visual change that addresses the
  specific complaint. Do not restructure the HTML or rewrite the CSS.
- "Optimize performance" → Identify the specific bottleneck. Do not rewrite
  the calculation engine or replace Chart.js without explicit approval.
- "Add a test" → Add the minimal test for the specific bug or feature. Do not
  refactor existing tests.

When in doubt, stop and ask. Do not solve scope problems by modifying unrelated
parts of the application.
