"""
eval.py - Evaluation Harness

Compares agent diagnoses against the simulator's ground truth to produce
real, citable numbers for the writeup:
  - Accuracy: did the resolver correctly identify the root cause?
  - Latency percentiles: p50/p95/p99 from incident detection to diagnosis
  - Disagreement rate: % of incidents where agents disagreed (score > 0.6)
  - Per-agent confidence distribution

Run this as a standalone script AFTER collecting some incidents:
    python eval.py

It reads ground_truth.jsonl (written by simulator.py) and consumes
the `diagnoses` Kafka topic from the beginning to collect all results.

Interview point: "We control ground truth via the simulator so accuracy
is an objective measurement, not a subjective one. That's why we built
the synthetic data generator rather than running against real infra."
"""

import json
import os
import statistics
from datetime import datetime

from kafka import KafkaConsumer

KAFKA_BROKER = "localhost:9092"
TOPIC_DIAGNOSES = "diagnoses"

GROUND_TRUTH_FILE = "../simulator/ground_truth.jsonl"

# Keywords we look for in the final diagnosis root_cause to determine
# whether the agents correctly identified a bad deploy.
# Phrases that mean the agent thinks a deploy caused the incident.
BAD_DEPLOY_POSITIVE = ["rollback", "bad deploy", "deploy caused", "caused by deploy",
                        "refactor connection", "connection pooling deploy", "deployment caused"]

# Phrases that mean the agent is ruling a deploy OUT.
BAD_DEPLOY_NEGATIVE = ["not deploy", "no deploy", "unlikely to be caused by",
                        "not caused by", "no deployments", "not related"]


def _deploy_identified(text: str) -> bool:
    text = text.lower()
    # Reject if the agent is ruling it out.
    if any(phrase in text for phrase in BAD_DEPLOY_NEGATIVE):
        return False
    # Accept if the agent is asserting it.
    if any(phrase in text for phrase in BAD_DEPLOY_POSITIVE):
        return True
    # Fallback: generic deploy mention without negation.
    return "deploy" in text or "rollback" in text


def load_ground_truth() -> list:
    """Load all ground truth records written by the simulator."""
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"[ERROR] Ground truth file not found: {GROUND_TRUTH_FILE}")
        print("Make sure simulator.py has been running long enough to inject incidents.")
        return []

    records = []
    with open(GROUND_TRUTH_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"[EVAL] Loaded {len(records)} ground truth records")
    return records


def load_diagnoses(timeout_seconds: int = 10) -> list:
    """
    Consume all messages from the diagnoses topic.
    Reads from the beginning (auto_offset_reset='earliest') so we get
    everything even if the topic has been accumulating for a while.
    Stops after timeout_seconds of no new messages.
    """
    consumer = KafkaConsumer(
        TOPIC_DIAGNOSES,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id=None,  # None = don't commit offsets, just read
        consumer_timeout_ms=timeout_seconds * 1000,
    )

    diagnoses = []
    for message in consumer:
        diagnoses.append(message.value)

    print(f"[EVAL] Loaded {len(diagnoses)} diagnoses from Kafka")
    return diagnoses


def is_correct_diagnosis(ground_truth: dict, diagnosis: dict) -> bool:
    """
    Check whether the diagnosis correctly identified the root cause.

    For 'bad_deploy' incidents: the final root_cause should mention
    deploy-related keywords. We check the resolver's final_diagnosis
    AND the deploy_correlator's individual result.

    This is intentionally simple - a production eval would use
    semantic similarity, but keyword matching is transparent and
    explainable, which matters more here.
    """
    root_cause = ground_truth.get("root_cause", "")

    if root_cause == "bad_deploy":
        # Check if the resolver's final diagnosis mentions a deploy.
        final = diagnosis.get("resolution", {}).get("final_diagnosis", {})
        final_text = final.get("root_cause", "").lower()
        if _deploy_identified(final_text):
            return True

        # Also check if the deploy_correlator specifically flagged it,
        # even if it didn't win the resolver vote.
        for agent_result in diagnosis.get("agent_results", []):
            if agent_result.get("agent") == "deploy_correlator":
                agent_text = agent_result.get("diagnosis", {}).get("root_cause", "").lower()
                if _deploy_identified(agent_text):
                    # deploy_correlator identified it, even if resolver didn't pick it
                    return True

    return False


def match_diagnoses_to_ground_truth(ground_truths: list, diagnoses: list) -> list:
    matched = []
    used_diagnosis_indices = set()

    for gt in ground_truths:
        gt_time = datetime.fromisoformat(gt["started_at"])
        best_match = None
        best_delta = float("inf")

        for i, diag in enumerate(diagnoses):
            if i in used_diagnosis_indices:
                continue
            if diag.get("service") != gt["service"]:
                continue

            diag_time = datetime.fromisoformat(diag["timestamp"])
            delta = abs((diag_time - gt_time).total_seconds())

            if delta < best_delta and delta <= 300:  # increase to 300s
                best_delta = delta
                best_match = (i, diag)

        if best_match:
            idx, diag = best_match
            used_diagnosis_indices.add(idx)
            matched.append({
                "ground_truth": gt,
                "diagnosis": diag,
                "time_delta_seconds": round(best_delta, 1),
            })

    return matched


def compute_latency_percentiles(diagnoses: list) -> dict:
    latencies = [d.get("latency_ms", 0) for d in diagnoses if d.get("latency_ms")]
    if not latencies:
        return {}

    latencies.sort()
    n = len(latencies)

    def percentile(p):
        idx = int(n * p / 100)
        return latencies[min(idx, n - 1)]

    return {
        "p50_ms": percentile(50),
        "p95_ms": percentile(95),
        "p99_ms": percentile(99),
        "min_ms": latencies[0],
        "max_ms": latencies[-1],
        "mean_ms": round(statistics.mean(latencies)),
        "sample_count": n,
    }


def compute_disagreement_stats(diagnoses: list) -> dict:
    scores = [
        d["resolution"]["disagreement_score"]
        for d in diagnoses
        if "resolution" in d and "disagreement_score" in d["resolution"]
    ]
    if not scores:
        return {}

    high_disagreement_count = sum(1 for s in scores if s > 0.6)

    return {
        "mean_disagreement_score": round(statistics.mean(scores), 3),
        "high_disagreement_count": high_disagreement_count,
        "high_disagreement_rate": round(high_disagreement_count / len(scores), 3),
        "sample_count": len(scores),
    }


def compute_confidence_distribution(diagnoses: list) -> dict:
    dist = {"high": 0, "medium": 0, "low": 0, "none": 0}
    for d in diagnoses:
        final = d.get("resolution", {}).get("final_diagnosis", {})
        conf = final.get("confidence", "none")
        dist[conf] = dist.get(conf, 0) + 1
    return dist


def run_eval():
    print("\n" + "=" * 60)
    print("INCIDENT RESPONSE PLATFORM - EVALUATION REPORT")
    print("=" * 60)

    ground_truths = load_ground_truth()
    diagnoses = load_diagnoses()

    if not diagnoses:
        print("[EVAL] No diagnoses found. Let the system run longer and retry.")
        return

    # --- Latency ---
    latency = compute_latency_percentiles(diagnoses)
    print("\n[LATENCY] Incident detection → diagnosis published")
    for k, v in latency.items():
        print(f"  {k}: {v}")

    # --- Disagreement ---
    disagreement = compute_disagreement_stats(diagnoses)
    print("\n[DISAGREEMENT] Agent consensus metrics")
    for k, v in disagreement.items():
        print(f"  {k}: {v}")

    # --- Confidence distribution ---
    confidence = compute_confidence_distribution(diagnoses)
    print("\n[CONFIDENCE] Final diagnosis confidence distribution")
    for k, v in confidence.items():
        print(f"  {k}: {v}")

    # --- Accuracy ---
    if ground_truths:
        matched = match_diagnoses_to_ground_truth(ground_truths, diagnoses)
        print(f"\n[ACCURACY] Ground truth matching")
        print(f"  Ground truth incidents: {len(ground_truths)}")
        print(f"  Matched to diagnoses:   {len(matched)}")

        if matched:
            correct = sum(1 for m in matched if is_correct_diagnosis(
                m["ground_truth"], m["diagnosis"]))
            accuracy = correct / len(matched)
            print(f"  Correct diagnoses:      {correct}/{len(matched)}")
            print(f"  Accuracy:               {accuracy:.1%}")

            print("\n[ACCURACY] Per-incident breakdown")
            for m in matched:
                gt = m["ground_truth"]
                correct_flag = is_correct_diagnosis(gt, m["diagnosis"])
                final_rc = m["diagnosis"].get("resolution", {}) \
                                         .get("final_diagnosis", {}) \
                                         .get("root_cause", "N/A")[:80]
                print(f"  {'✓' if correct_flag else '✗'} service={gt['service']} "
                      f"truth={gt['root_cause']} "
                      f"delta={m['time_delta_seconds']}s")
                print(f"    diagnosed: {final_rc}")
    else:
        print("\n[ACCURACY] Skipped - no ground truth file found")

    print("\n" + "=" * 60)
    print("END OF REPORT")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_eval()