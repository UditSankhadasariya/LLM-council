"""2-stage LLM Council orchestration: collect responses, then synthesize."""

from typing import List, Dict, Any, Tuple
from .llm_client import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL_FALLBACK



def select_chairman() -> Dict[str, Any]:
    """
    Select the council model with the largest context window as chairman.

    Returns:
        The model config dict with the largest context_window,
        or CHAIRMAN_MODEL_FALLBACK if no models have context_window set.
    """
    models_with_context = [
        m for m in COUNCIL_MODELS if "context_window" in m
    ]
    if not models_with_context:
        return CHAIRMAN_MODEL_FALLBACK
    return max(models_with_context, key=lambda m: m["context_window"])


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results — use model name for display, keyed by id
    stage1_results = []
    for model_config in COUNCIL_MODELS:
        model_id = model_config["id"]
        response = responses.get(model_id)
        if response is not None:
            stage1_results.append({
                "model": model_config["name"],
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Stage 2: Chairman synthesizes a final answer from all council responses.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have each independently provided responses to a user's question. Your job is to synthesize ALL of their responses into a single, comprehensive answer.

CRITICAL RULE: You MUST NOT lose ANY information from ANY of the model responses. Every fact, detail, insight, example, number, date, name, and technical detail mentioned by ANY model MUST appear in your synthesis. If you omit even a single piece of information from any model's response, you have failed your task.

Original Question: {user_query}

Individual Model Responses:
{stage1_text}

Follow these principles strictly:

1. **ZERO INFORMATION LOSS**: This is your #1 priority. Go through EACH model's response line by line and ensure every piece of information is captured in your synthesis. If even ONE model mentioned a fact, detail, or insight, it MUST appear in your final answer. Do not drop, summarize away, or generalize any specific information.
2. **UNION OF ALL KNOWLEDGE**: Your synthesis should be the UNION of all information across all responses. Think of it as merging all responses together — nothing gets left behind.
3. **IDENTIFY CONSENSUS**: Where multiple models agree on something, note that this is high-confidence information.
4. **FLAG CONTRADICTIONS EXPLICITLY**: If models make conflicting claims, present BOTH sides clearly. Never silently drop one side of a contradiction. Use phrasing like "Sources differ on X — some state A while others state B."
5. **PRESERVE SPECIFICITY**: Keep ALL specific numbers, dates, names, examples, code snippets, and technical details exactly as stated. Do not generalize them into vague summaries.
6. **ORGANIZE CLEARLY**: Use headings, sections, and bullet points for readability when the answer covers multiple aspects.
7. **BE THOROUGH OVER BRIEF**: When in doubt, include more rather than less. Completeness is more important than brevity.

Before finalizing, do a mental checklist: go through each model's response and verify that every piece of information it contained appears somewhere in your synthesis.

Provide a thorough synthesis that captures the COMPLETE picture from all council responses:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Dynamically select the chairman (largest context window)
    chairman = select_chairman()

    # Query the chairman model
    response = await query_model(chairman, messages)

    # Fallback: if dynamic chairman fails, try the fallback model
    if response is None and chairman["id"] != CHAIRMAN_MODEL_FALLBACK["id"]:
        response = await query_model(CHAIRMAN_MODEL_FALLBACK, messages)
        chairman = CHAIRMAN_MODEL_FALLBACK

    if response is None:
        return {
            "model": chairman["name"],
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": chairman["name"],
        "response": response.get('content', '')
    }


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use fallback model for title generation (lightweight task, no need for largest context)
    response = await query_model(CHAIRMAN_MODEL_FALLBACK, messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, Dict]:
    """
    Run the 2-stage council process: collect responses, then synthesize.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_result)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }

    # Stage 2: Synthesize final answer from all responses
    stage2_result = await stage2_synthesize_final(user_query, stage1_results)

    return stage1_results, stage2_result
