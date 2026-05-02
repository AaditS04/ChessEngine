from pathlib import Path
import math

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path(__file__).resolve().parent
DATA_DIR = REPORT_DIR / "data"


def load_results() -> pd.DataFrame:
    frames = []
    for csv_path in sorted((ROOT / "logs").glob("persona_evaluation_results*.csv")):
        frame = pd.read_csv(csv_path)
        frame["Run"] = "Run 1" if csv_path.name == "persona_evaluation_results.csv" else "Run 2"
        frames.append(frame)
    if not frames:
        raise FileNotFoundError("No persona_evaluation_results*.csv files found in logs/")
    df = pd.concat(frames, ignore_index=True)
    df["ScoreDiff"] = pd.to_numeric(df["Score Diff"], errors="coerce")
    df["Legal"] = df["Is Legal"].astype(str).str.lower().eq("true")
    df["Good"] = df["Quality"].eq("Best/Good")
    df["Mistake"] = df["Quality"].eq("Mistake")
    df["Blunder"] = df["Quality"].astype(str).str.lower().eq("blunder")
    df["Invalid"] = ~df["Legal"]
    df["BestMatch"] = df["LLM Move"].astype(str).eq(df["Best Move"].astype(str)) & df["Legal"]
    return df


def short_name(persona: str) -> str:
    return {
        "Neutral Baseline": "Neutral",
        "Aggressive": "Aggressive",
        "Defensive": "Defensive",
        "Beginner Materialist": "Materialist",
    }[persona]


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half_width = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return center - half_width, center + half_width


def exact_sign_test_p(better: int, worse: int) -> float:
    n = better + worse
    if n == 0:
        return 1.0
    tail = min(better, worse)
    prob = sum(math.comb(n, i) * (0.5 ** n) for i in range(tail + 1))
    return min(1.0, 2 * prob)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = load_results()
    order = ["Neutral Baseline", "Aggressive", "Defensive", "Beginner Materialist"]

    quality_rows = []
    metric_rows = []
    for persona in order:
        group = df[df["Persona"] == persona]
        quality_rows.append(
            {
                "persona": short_name(persona),
                "good": round(group["Good"].mean() * 100, 1),
                "mistake": round(group["Mistake"].mean() * 100, 1),
                "blunder": round(group["Blunder"].mean() * 100, 1),
                "invalid": round(group["Invalid"].mean() * 100, 1),
            }
        )
        metric_rows.append(
            {
                "persona": short_name(persona),
                "attack": round(group["Attack Metric"].mean(), 2),
                "defense": round(group["Defensive Metric"].mean(), 2),
                "median_diff": round(group["ScoreDiff"].median(), 2),
                "best_match": round(group["BestMatch"].mean() * 100, 1),
            }
        )

    ci_rows = []
    for persona in order:
        group = df[df["Persona"] == persona]
        n = len(group)
        legal_k = int(group["Legal"].sum())
        good_k = int(group["Good"].sum())
        legal_low, legal_high = wilson_interval(legal_k, n)
        good_low, good_high = wilson_interval(good_k, n)
        ci_rows.append(
            {
                "persona": short_name(persona),
                "legal": round(legal_k / n * 100, 1),
                "legal_low": round(legal_low * 100, 1),
                "legal_high": round(legal_high * 100, 1),
                "good": round(good_k / n * 100, 1),
                "good_low": round(good_low * 100, 1),
                "good_high": round(good_high * 100, 1),
            }
        )

    pd.DataFrame(quality_rows).to_csv(DATA_DIR / "quality_stack.csv", index=False)
    pd.DataFrame(metric_rows).to_csv(DATA_DIR / "metric_summary.csv", index=False)
    pd.DataFrame(ci_rows).to_csv(DATA_DIR / "quality_ci.csv", index=False)

    wide = df.pivot_table(
        index=["Run", "FEN"],
        columns="Persona",
        values=["LLM Move", "Attack Metric", "Defensive Metric", "ScoreDiff", "Good"],
        aggfunc="first",
    )

    agreement_rows = []
    delta_rows = []
    for persona in ["Aggressive", "Defensive", "Beginner Materialist"]:
        valid = wide[("LLM Move", persona)].notna() & wide[("LLM Move", "Neutral Baseline")].notna()
        same = (wide[("LLM Move", persona)] == wide[("LLM Move", "Neutral Baseline")]) & valid
        agreement_rows.append(
            {
                "persona": short_name(persona),
                "same": round(same.mean() * 100, 1),
                "different": round((~same & valid).mean() * 100, 1),
            }
        )
        delta_rows.append(
            {
                "persona": short_name(persona),
                "attack_delta": round((wide[("Attack Metric", persona)] - wide[("Attack Metric", "Neutral Baseline")]).mean(), 2),
                "defense_delta": round((wide[("Defensive Metric", persona)] - wide[("Defensive Metric", "Neutral Baseline")]).mean(), 2),
                "median_diff_delta": round((wide[("ScoreDiff", persona)] - wide[("ScoreDiff", "Neutral Baseline")]).median(), 2),
            }
        )

    pd.DataFrame(agreement_rows).to_csv(DATA_DIR / "agreement.csv", index=False)
    pd.DataFrame(delta_rows).to_csv(DATA_DIR / "deltas.csv", index=False)

    comparison_rows = []
    comparison_specs = [
        ("Aggressive", "Attack Metric", "higher"),
        ("Defensive", "Defensive Metric", "higher"),
        ("Beginner Materialist", "ScoreDiff", "lower"),
    ]
    for persona, metric, direction in comparison_specs:
        valid = wide[(metric, persona)].notna() & wide[(metric, "Neutral Baseline")].notna()
        if direction == "higher":
            better = wide[(metric, persona)] > wide[(metric, "Neutral Baseline")]
            equal = wide[(metric, persona)] == wide[(metric, "Neutral Baseline")]
            worse = wide[(metric, persona)] < wide[(metric, "Neutral Baseline")]
        else:
            better = wide[(metric, persona)] < wide[(metric, "Neutral Baseline")]
            equal = wide[(metric, persona)] == wide[(metric, "Neutral Baseline")]
            worse = wide[(metric, persona)] > wide[(metric, "Neutral Baseline")]
        same_move = wide[("LLM Move", persona)] == wide[("LLM Move", "Neutral Baseline")]
        different_valid = (~same_move) & valid
        better_valid = better & valid
        comparison_rows.append(
            {
                "persona": short_name(persona),
                "better": round(better_valid.sum() / valid.sum() * 100, 1),
                "equal": round((equal & valid).sum() / valid.sum() * 100, 1),
                "worse": round((worse & valid).sum() / valid.sum() * 100, 1),
                "better_different": round((better & different_valid).sum() / different_valid.sum() * 100, 1),
                "good_when_better": round(wide.loc[better_valid, ("Good", persona)].mean() * 100, 1),
                "neutral_good_when_better": round(wide.loc[better_valid, ("Good", "Neutral Baseline")].mean() * 100, 1),
            }
        )
    pd.DataFrame(comparison_rows).to_csv(DATA_DIR / "persona_baseline_comparison.csv", index=False)

    sign_test_specs = [
        ("Aggressive attack vs neutral", "Aggressive", "Attack Metric", "higher"),
        ("Defensive defense vs neutral", "Defensive", "Defensive Metric", "higher"),
        ("Materialist accuracy vs neutral", "Beginner Materialist", "ScoreDiff", "lower"),
        ("Aggressive accuracy vs neutral", "Aggressive", "ScoreDiff", "lower"),
        ("Defensive accuracy vs neutral", "Defensive", "ScoreDiff", "lower"),
    ]
    sign_rows = []
    for label, persona, metric, direction in sign_test_specs:
        valid = wide[(metric, persona)].notna() & wide[(metric, "Neutral Baseline")].notna()
        if direction == "higher":
            better = wide[(metric, persona)] > wide[(metric, "Neutral Baseline")]
            equal = wide[(metric, persona)] == wide[(metric, "Neutral Baseline")]
            worse = wide[(metric, persona)] < wide[(metric, "Neutral Baseline")]
        else:
            better = wide[(metric, persona)] < wide[(metric, "Neutral Baseline")]
            equal = wide[(metric, persona)] == wide[(metric, "Neutral Baseline")]
            worse = wide[(metric, persona)] > wide[(metric, "Neutral Baseline")]
        better_count = int((better & valid).sum())
        equal_count = int((equal & valid).sum())
        worse_count = int((worse & valid).sum())
        sign_rows.append(
            {
                "comparison": label,
                "better": better_count,
                "equal": equal_count,
                "worse": worse_count,
                "p_value": round(exact_sign_test_p(better_count, worse_count), 3),
            }
        )
    pd.DataFrame(sign_rows).to_csv(DATA_DIR / "sign_tests.csv", index=False)

    run_rows = []
    for run in ["Run 1", "Run 2"]:
        row = {"run": run}
        for persona in order:
            group = df[(df["Run"] == run) & (df["Persona"] == persona)]
            row[short_name(persona).lower()] = round(group["Good"].mean() * 100, 1)
        pd.Series(row)
        run_rows.append(row)
    pd.DataFrame(run_rows).to_csv(DATA_DIR / "run_good_rates.csv", index=False)

    print("Wrote report data tables to", DATA_DIR)


if __name__ == "__main__":
    main()
