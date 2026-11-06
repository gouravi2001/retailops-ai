"""Optional bounded LLM summaries; all numerical evidence comes from the analytics layer."""
import json
from retailops.config import OPENAI_API_KEY, OPENAI_MODEL
from retailops.schemas import AIInsight


def rule_based_insight(report: dict) -> dict:
    rows = report["by_store"]
    if not rows:
        return {"mode": "rules", "headline": "No store records available",
                "summary": "Import a dataset before requesting operational insights.", "recommendations": []}
    largest = max(rows, key=lambda r: r["active_issues"])
    summary = report["summary"]
    headline = f"Highest issue count: {largest['store_name']}"
    message = (f"{largest['store_name']} has {largest['active_issues']} active issues. "
               f"Across the selected stores, {summary['active_issues']} issues are open or under review. "
               "These are rule-derived observations, not a verified root-cause diagnosis.")
    return {
        "mode": "rules", "headline": headline, "summary": message,
        "recommendations": [
            "Inspect unresolved inventory and delivery exceptions in the issue queue.",
            "Assign an owner and require a documented review before closing an issue.",
        ],
    }


def llm_insight(report: dict) -> dict:
    """Only called by an authenticated, explicit POST, never on every page view."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=15.0, max_retries=0)
    # Only aggregated, non-personal records are sent to the external model.
    evidence = {"summary": report["summary"], "by_store": report["by_store"][:30]}
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        max_tokens=450,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                "You analyze fictional retail operations data. Use ONLY provided evidence; "
                "do not invent numbers, causes or claims of actions taken. "
                "Return a JSON object containing headline, summary and recommendations "
                "(1 to 3 short action recommendations). A human must approve business actions."
            )},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    insight = AIInsight.model_validate_json(raw)
    return {"mode": "llm", **insight.model_dump(),
            "caution": "AI-generated interpretation; verify against the data before acting."}
