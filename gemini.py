"""Gemini API helpers."""

import time
from collections.abc import Generator

from google import genai
from google.genai import errors as genai_errors

GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"

GEMINI_MAX_RETRIES = 3
GEMINI_RETRY_BASE_DELAY = 1.0


class GeminiBusyError(Exception):
    """Raised when Gemini is still overloaded after exhausting retries (and the fallback model, if tried)."""

    def __init__(self, retries: int, tried_fallback: bool = False):
        self.retries = retries
        self.tried_fallback = tried_fallback
        suffix = " and the fallback model" if tried_fallback else ""
        super().__init__(f"Gemini is busy after {retries} retr{'y' if retries == 1 else 'ies'}{suffix}.")


def build_gemini_prompt(genre: str, artists: list[dict]) -> str:
    artist_list = "\n".join(f"{i}. {artist['name']}" for i, artist in enumerate(artists, start=1))
    return (
        f"Here is an ordered list of top artists that I listen to:\n{artist_list}\n\n"
        f"I'd like to explore the {genre} genre. Based on this list, recommend artists "
        f"in that genre that I might enjoy.  At the end of the prose list, please "
        f"provide a JSON array of the recommended artists, where each artist is an "
        f"object with a 'name' field, each recommended album is a sub-object  of the artist "
        f"with a 'title' field, and each recommended track is a sub-object of the album with "
        f"a 'title' field. "
    )


def ask_gemini(prompt: str, api_key: str, model: str = GEMINI_MODEL) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def ask_gemini_with_retry_streaming(
    prompt: str,
    api_key: str,
    max_retries: int = GEMINI_MAX_RETRIES,
    base_delay: float = GEMINI_RETRY_BASE_DELAY,
    fallback_model: str = GEMINI_FALLBACK_MODEL,
) -> Generator[dict, None, None]:
    """Like ask_gemini_with_retry but yields progress dicts instead of blocking.

    Event types: trying | waiting | trying_fallback | done | busy | error
    """
    retries_used = 0
    for attempt in range(max_retries + 1):
        retries_used = attempt
        yield {"type": "trying", "attempt": attempt + 1}
        try:
            reply = ask_gemini(prompt, api_key, GEMINI_MODEL)
            yield {"type": "done", "reply": reply, "retries": attempt, "fallback": False}
            return
        except genai_errors.ClientError as e:
            if e.code == 429:
                break
            raise
        except genai_errors.ServerError:
            if attempt < max_retries:
                wait_secs = max(1, int(base_delay * (2 ** attempt)))
                for remaining in range(wait_secs, 0, -1):
                    yield {"type": "waiting", "total": wait_secs, "remaining": remaining}
                    time.sleep(1)

    if fallback_model:
        yield {"type": "trying_fallback"}
        try:
            reply = ask_gemini(prompt, api_key, fallback_model)
            yield {"type": "done", "reply": reply, "retries": retries_used, "fallback": True}
            return
        except (genai_errors.ServerError, genai_errors.ClientError):
            pass

    yield {"type": "busy", "retries": retries_used, "fallback": bool(fallback_model)}


def ask_gemini_with_retry(
    prompt: str,
    api_key: str,
    max_retries: int = GEMINI_MAX_RETRIES,
    base_delay: float = GEMINI_RETRY_BASE_DELAY,
    fallback_model: str = GEMINI_FALLBACK_MODEL,
) -> tuple[str, int, bool]:
    """Calls ask_gemini on GEMINI_MODEL, retrying with exponential backoff on
    transient server overload (5xx). On a 429 quota error, retrying the same
    model won't help, so it skips straight to fallback_model. Also falls
    back after exhausting retries on a 5xx.

    Returns (reply, retries_used, used_fallback). Raises GeminiBusyError if
    both the primary model and the fallback model fail.
    """
    last_error = None
    retries_used = 0
    for attempt in range(max_retries + 1):
        retries_used = attempt
        try:
            return ask_gemini(prompt, api_key, GEMINI_MODEL), attempt, False
        except genai_errors.ClientError as e:
            last_error = e
            if e.code == 429:
                break
            raise
        except genai_errors.ServerError as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(base_delay * (2**attempt))

    if fallback_model:
        try:
            return ask_gemini(prompt, api_key, fallback_model), retries_used, True
        except (genai_errors.ServerError, genai_errors.ClientError) as e:
            last_error = e
            raise GeminiBusyError(retries_used, tried_fallback=True) from last_error

    raise GeminiBusyError(retries_used) from last_error
