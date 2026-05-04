"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from datasets import Dataset
    import pandas as pd
    import numpy as np

    # 1. Prepare dataset
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
    dataset = Dataset.from_dict(data)

    # 2. Run evaluation
    # Note: Explicitly setting LLM and Embeddings to avoid AttributeError in some environments
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
    )

    # 3. Process results
    df = result.to_pandas()
    per_question = []
    for _, row in df.iterrows():
        # Ragas v0.2+ uses new column names: user_input, response, retrieved_contexts, reference
        per_question.append(EvalResult(
            question=row.get("user_input", row.get("question", "")),
            answer=row.get("response", row.get("answer", "")),
            contexts=row.get("retrieved_contexts", row.get("contexts", [])),
            ground_truth=row.get("reference", row.get("ground_truth", "")),
            faithfulness=float(np.nan_to_num(row.get("faithfulness", 0.0))),
            answer_relevancy=float(np.nan_to_num(row.get("answer_relevancy", 0.0))),
            context_precision=float(np.nan_to_num(row.get("context_precision", 0.0))),
            context_recall=float(np.nan_to_num(row.get("context_recall", 0.0)))
        ))

    # 4. Final output - Ensure we return floats, not lists or series
    # EvaluationResult object doesn't always support .get(), so we check keys directly
    def get_score(res, metric):
        try:
            # Try direct access
            val = res[metric]
            # Handle if it's a list/series/array
            if isinstance(val, (list, np.ndarray, pd.Series)):
                val = val[0] if len(val) > 0 else 0.0
            return float(np.nan_to_num(val))
        except (KeyError, AttributeError, TypeError, IndexError):
            return 0.0

    return {
        "faithfulness": get_score(result, "faithfulness"),
        "answer_relevancy": get_score(result, "answer_relevancy"),
        "context_precision": get_score(result, "context_precision"),
        "context_recall": get_score(result, "context_recall"),
        "per_question": per_question
    }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    import numpy as np

    # 1. Calculate average score for each result
    scored_results = []
    for res in eval_results:
        avg_score = np.mean([
            res.faithfulness,
            res.answer_relevancy,
            res.context_precision,
            res.context_recall
        ])
        scored_results.append((avg_score, res))

    # 2. Sort and take bottom N
    scored_results.sort(key=lambda x: x[0])
    bottom_results = scored_results[:bottom_n]

    # 3. Diagnose
    failures = []
    for avg_score, res in bottom_results:
        # Find the worst metric
        metrics = {
            "faithfulness": res.faithfulness,
            "answer_relevancy": res.answer_relevancy,
            "context_precision": res.context_precision,
            "context_recall": res.context_recall
        }
        worst_metric = min(metrics, key=metrics.get)
        score = metrics[worst_metric]

        # Diagnostic Tree Mapping
        diagnosis = "Unknown error"
        suggested_fix = "Check logs"

        if worst_metric == "faithfulness" and score < 0.85:
            diagnosis = "LLM hallucinating (answer contains info not in context)"
            suggested_fix = "Tighten system prompt, lower temperature, or improve chunk relevance."
        elif worst_metric == "context_recall" and score < 0.75:
            diagnosis = "Missing relevant information in retrieved chunks"
            suggested_fix = "Improve chunking strategy (e.g., Hierarchical) or add BM25 keyword search."
        elif worst_metric == "context_precision" and score < 0.75:
            diagnosis = "Retrieved chunks contain too much noise/irrelevant info"
            suggested_fix = "Add Reranking (M3) or use smaller child chunks with parent context."
        elif worst_metric == "answer_relevancy" and score < 0.80:
            diagnosis = "Answer is correct but doesn't directly address the user query"
            suggested_fix = "Improve prompt template to focus on the specific question."

        failures.append({
            "question": res.question,
            "worst_metric": worst_metric,
            "score": round(score, 4),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix
        })

    return failures


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
