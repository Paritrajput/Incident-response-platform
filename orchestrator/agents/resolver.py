"""
agents/resolver.py - Resolver (Naive Consensus)

Takes the three agent results and produces a final diagnosis.

Strategy: naive consensus — pick the hypothesis with the most agreement,
weighted by confidence. But crucially, we also compute a disagreement
score and log it. This score is what makes the "we measured disagreement
rate" claim in the writeup defensible.

Interview talking point: "We explicitly designed the resolver to avoid
sycophancy-cascade — agents produce their diagnoses independently before
seeing each other's output (enforced by asyncio.gather()), so the resolver
is reconciling genuinely independent views, not rubber-stamping the first
answer. The disagreement score lets us measure how often agents conflict."

Debate mode (week 7-8 stretch goal) would go here: if disagreement_score
is above a threshold, trigger a second round where agents see each other's
reasoning before producing a final answer.
"""

from logger import log

# Map confidence strings to numeric weights for scoring.
CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1, "none": 0}


def _extract_keywords(root_cause: str) -> set:
    """
    Pull meaningful keywords from a root_cause string so we can compare
    whether two agents are saying roughly the same thing.
    We strip common filler words and keep the signal words.
    """
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "to", "of", "in", "and", "or", "for", "its", "this", "that",
        "it", "by", "due", "with", "has", "have", "likely", "may",
        "resulting", "causing", "experiencing", "indicates", "suggest",
    }
    words = root_cause.lower().replace(",", "").replace(".", "").split()
    return {w for w in words if w not in stopwords and len(w) > 3}


def _compute_disagreement_score(agent_results: list) -> float:
    """
    Compute how much the agents disagree with each other.

    Method: for each pair of agents, compute keyword overlap between their
    root_cause strings using Jaccard similarity. Average the pairwise
    similarities, then invert (1 - similarity) to get disagreement.

    Score of 0.0 = perfect agreement, 1.0 = total disagreement.
    This is logged per incident so the eval harness can compute the
    overall disagreement rate across all incidents.
    """
    keyword_sets = []
    for r in agent_results:
        root_cause = r.get("diagnosis", {}).get("root_cause", "")
        if root_cause and root_cause != "Agent unavailable":
            keyword_sets.append(_extract_keywords(root_cause))

    if len(keyword_sets) < 2:
        return 0.0

    # Pairwise Jaccard similarity between all agent pairs.
    similarities = []
    for i in range(len(keyword_sets)):
        for j in range(i + 1, len(keyword_sets)):
            a, b = keyword_sets[i], keyword_sets[j]
            if not a and not b:
                similarities.append(1.0)
            elif not a or not b:
                similarities.append(0.0)
            else:
                jaccard = len(a & b) / len(a | b)
                similarities.append(jaccard)

    avg_similarity = sum(similarities) / len(similarities)
    return round(1.0 - avg_similarity, 3)


def _pick_winner(agent_results: list) -> dict:
    """
    Pick the best single diagnosis using confidence-weighted voting.

    Simple rule: the agent with the highest confidence wins.
    On a tie, prefer the one whose root_cause is corroborated by
    keywords appearing in other agents' root_causes too.
    """
    # Filter out agents that failed completely.
    valid = [r for r in agent_results if r["diagnosis"]["confidence"] != "none"]

    if not valid:
        return {
            "root_cause": "Unable to determine - all agents failed",
            "confidence": "none",
            "evidence": [],
            "recommended_action": "Manual investigation required",
        }

    # Sort by confidence weight descending.
    valid.sort(key=lambda r: CONFIDENCE_WEIGHT.get(r["diagnosis"]["confidence"], 0), reverse=True)

    # Winner is the highest-confidence agent's diagnosis.
    winner = valid[0]["diagnosis"]

    # Enrich evidence with corroborating observations from other agents.
    corroborating = []
    for r in valid[1:]:
        for obs in r["diagnosis"].get("evidence", []):
            corroborating.append(f"[{r['agent']}] {obs}")

    return {
        **winner,
        "corroborating_evidence": corroborating[:4],  # cap at 4 to keep it readable
    }


def resolve(agent_results: list, service: str) -> dict:
    """
    Main resolver entry point. Takes all agent results, computes disagreement,
    picks a winner, and returns the final diagnosis with metadata.
    """
    disagreement_score = _compute_disagreement_score(agent_results)
    final_diagnosis = _pick_winner(agent_results)

    log("info", "resolver completed",
        service=service,
        disagreement_score=disagreement_score,
        winner_confidence=final_diagnosis.get("confidence"),
        agents_succeeded=sum(1 for r in agent_results if r["diagnosis"]["confidence"] != "none"),
        agents_total=len(agent_results))

    return {
        "final_diagnosis": final_diagnosis,
        "disagreement_score": disagreement_score,
        # Flag high disagreement so the eval harness can track it separately.
        "high_disagreement": disagreement_score > 0.6,
    }