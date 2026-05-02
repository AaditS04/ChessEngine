# Persona Prompting in LLM Chess Decision Making

This repository contains a chess-based experimental framework for studying whether persona prompts influence the concrete decisions made by large language models, rather than only changing their explanations.

The core research question is:

> Can strategic personas imposed through prompting meaningfully change an LLM's move selection in a structured decision environment?

Chess is used because board states can be represented exactly with FEN strings, legal actions are enumerable, and selected moves can be evaluated against a search baseline.

## Overview

The project evolved from full LLM-vs-LLM chess games to a more controlled position-based evaluation. Full games are difficult to compare because an early mistake changes the entire future trajectory. The final evaluation instead samples fixed FEN positions and asks each persona to choose a move from the same legal move list.

The evaluated personas are:

- **Neutral Baseline**: choose the strongest move without adopting a style.
- **Aggressive**: prefer threats, initiative, checks, captures, and king pressure.
- **Defensive**: prefer low-risk play, piece safety, king safety, and avoiding blunders.
- **Beginner Materialist**: prioritize capturing material over positional considerations.

For each position-persona pair, the system records:

- raw LLM response,
- parsed move,
- legality,
- best move from the search baseline,
- score difference from the best move,
- quality label,
- attack metric,
- defensive metric.

## Repository Structure

```text
.
├── ChessAI.py                  # LLM prompting, move parsing, move evaluation
├── ChessEngine.py              # Custom chess engine and legal move generation
├── ChessLogger.py              # JSON logging utilities
├── ChessMain.py                # Pygame chess UI/helpers
├── EvaluatePersona.py          # Position-based persona evaluation pipeline
├── ExperimentRunner.py         # Game experiment runner
├── PersonaCatalogue.py         # Persona prompt definitions
├── PersonaTests.py             # Persona testing utilities
├── ReplayGame.py               # Replay logged games
├── fen_analysis.csv            # Source pool of FEN positions
├── images/                     # Chess piece sprites
├── logs/                       # Game logs and persona evaluation results
└── end_sem_report/
    ├── main.tex                # Conference-style LaTeX manuscript
    ├── references.bib          # Bibliography
    ├── analyze_persona_results.py
    └── data/                   # Derived tables used by the LaTeX figures
```

## Experimental Pipeline

1. Load FEN positions from `fen_analysis.csv`.
2. Randomly sample up to 100 positions per run.
3. For each position, generate the legal move list.
4. Query the LLM once under each persona prompt.
5. Ask the model for a short rationale and a final move inside `<MOVE>...</MOVE>` tags.
6. Parse the tagged move, with SAN/UCI regex fallbacks.
7. Validate the parsed move against the legal move list.
8. Evaluate legal moves using a depth-4 negamax alpha-beta search baseline.
9. Compute attack and defensive heuristic metrics.
10. Save results to CSV and JSON logs.

## Metrics

### Accuracy / Move Quality

The evaluator compares the LLM move against the best move found by a depth-4 negamax alpha-beta search with material-only leaf evaluation.

The score difference is:

```text
score_diff = best_score - ai_score
```

Lower is better.

Quality labels:

- `Best/Good`: score difference <= 2
- `Mistake`: score difference > 2 and <= 8
- `BLUNDER`: score difference > 8
- Invalid/unparseable moves are tracked separately.

### Attack Metric

The attack score rewards moves that:

- approach the enemy king,
- enter enemy territory,
- capture safely,
- give safe checks,
- create safe threats against enemy pieces.

This metric is used to compare the **Aggressive** persona against the **Neutral Baseline**.

### Defensive Metric

The defensive score rewards:

- defenders near the king,
- pawn shielding,
- compact placement,
- rescuing attacked pieces.

It penalizes hanging friendly pieces.

This metric is used to compare the **Defensive** persona against the **Neutral Baseline**.

### Materialist Accuracy Comparison

The **Beginner Materialist** persona is compared to the Neutral Baseline using score difference rather than a separate style metric, because material gain is already represented in the search evaluation.

## Results and Report

The conference-style manuscript is in:

```text
end_sem_report/main.tex
```

It includes:

- motivation and related work,
- full methodology,
- metric formulas,
- aggregate results,
- paired persona-vs-neutral comparisons,
- confidence intervals,
- sign-test summaries,
- limitations,
- appendix with prompts and reference code.

To regenerate the report data tables:

```powershell
python end_sem_report/analyze_persona_results.py
```

If your system does not have `python` on PATH, use the Python interpreter from your environment.

To compile the paper locally, install a LaTeX distribution such as MiKTeX or TeX Live, then run:

```powershell
cd end_sem_report
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The output will be:

```text
end_sem_report/main.pdf
```

You can also upload the `end_sem_report/` folder to Overleaf and compile `main.tex`.

## Running Persona Evaluation

Install the required Python packages first. The code uses packages including:

- `pygame`
- `openai`
- `google-genai`
- `ollama`
- `pandas`

Then run:

```powershell
python EvaluatePersona.py
```

Important notes:

- The evaluation calls hosted or local LLM APIs depending on which function is enabled in `EvaluatePersona.py`.
- API keys and model names should be configured before running.
- The final reported experiments used OpenRouter models.
- The current evaluator samples positions randomly from `fen_analysis.csv`, so runs are not deterministic unless you set a random seed.

## Current Limitations

This repository is a research prototype. The paper explicitly discusses these limitations:

- The chess evaluator uses a shallow depth-4 material-only negamax baseline.
- A stronger engine such as Stockfish would give more reliable centipawn-loss evaluation.
- The two final runs use different model backends and different sampled FEN sets.
- There is one sample per `(position, persona)` condition.
- The defensive heuristic is imperfect and does not fully capture human notions of safe play.
- Future work should use a fixed benchmark set, repeated samples, one model at a time, stronger engine evaluation, and phase/theme stratification.

## Suggested Future Work

- Replace the search baseline with Stockfish/NNUE.
- Add deterministic benchmark FEN splits by opening, middlegame, endgame, tactical, and quiet positions.
- Run multiple samples per persona and position.
- Add constrained decoding or function calling to reduce invalid outputs.
- Improve the defensive metric using king-safety deltas, opponent checking moves, simplification incentives, and risk under best replies.
- Compare prompt-only persona control with activation or inference-time steering methods.

