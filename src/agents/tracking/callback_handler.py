"""
Custom LangChain/LangGraph callback handler for DiaCareFlow pipeline tracking.

Instruments every node (chain), LLM call, and tool execution to produce
structured JSON logs via JsonTrackingLogger.

Tracked metrics per event:
  - latency_ms   : wall-clock duration of the call
  - token_usage  : prompt/completion/total token counts (LLM events only)
  - ram_usage    : process RSS memory before and after the call (MB)
  - metadata.input  : truncated input sent to the LLM or tool (T013)
  - metadata.output : truncated output returned by the LLM or tool (T013)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Union
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.agents.tracking.logger import JsonTrackingLogger
from src.agents.tracking.models import LogEvent

# psutil is an optional dependency; degrade gracefully if missing
try:
    import psutil as _psutil
    _PROCESS = _psutil.Process()
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PSUTIL_AVAILABLE = False


def _rss_mb() -> float:
    """Return the current process RSS in megabytes, or 0.0 if psutil is unavailable."""
    if _PSUTIL_AVAILABLE:
        return _PROCESS.memory_info().rss / (1024 * 1024)
    return 0.0


class DiaCareFlowCallbackHandler(BaseCallbackHandler):
    """
    Structured JSON logging callback handler for the LangGraph pipeline.

    Attach this handler at invocation time via:
        graph.invoke(state, config={"callbacks": [handler]})

    All public methods are guaranteed to never raise — errors are silently
    swallowed to avoid disrupting the pipeline execution.
    """

    def __init__(self, session_id: str = "") -> None:
        super().__init__()
        self._session_id = session_id
        self._logger = JsonTrackingLogger()
        # Pending event state keyed by LangChain run_id (UUID)
        self._pending: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start(self, run_id: UUID, extra: dict[str, Any] | None = None) -> None:
        """Record start timestamp, RAM, and optional extra context for a given run_id."""
        entry: dict[str, Any] = {
            "start_time": time.time(),
            "ram_start_mb": _rss_mb(),
        }
        if extra:
            entry.update(extra)
        self._pending[str(run_id)] = entry

    def _finish(
        self,
        run_id: UUID,
        event_type: str,
        name: str,
        token_usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Compute latency + RAM delta, build a LogEvent and emit it.
        Removes the pending entry regardless of success.
        """
        try:
            end_time = time.time()
            ram_end_mb = _rss_mb()

            key = str(run_id)
            pending = self._pending.pop(key, {})
            start_time = pending.get("start_time", end_time)
            ram_start_mb = pending.get("ram_start_mb", ram_end_mb)

            event = LogEvent(
                session_id=self._session_id,
                event_type=event_type,
                name=name,
                start_time=start_time,
                end_time=end_time,
                latency_ms=round((end_time - start_time) * 1000, 3),
                token_usage=token_usage or {},
                ram_usage={
                    "start_mb": round(ram_start_mb, 3),
                    "end_mb": round(ram_end_mb, 3),
                    "diff_mb": round(ram_end_mb - ram_start_mb, 3),
                },
                metadata=metadata or {},
            )
            self._logger.emit(event)
        except Exception:
            # Never crash the pipeline due to logging errors
            pass

    # ------------------------------------------------------------------
    # Chain (node) callbacks
    # ------------------------------------------------------------------

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            self._start(run_id)
        except Exception:
            pass

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        name = kwargs.get("name", "") or str(run_id)
        self._finish(run_id, "chain_end", name)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        name = kwargs.get("name", "") or str(run_id)
        self._finish(
            run_id,
            "chain_error",
            name,
            metadata={"error": str(error)},
        )

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            # T013: store prompts for later use in on_llm_end
            truncated = [p[:2000] for p in prompts] if prompts else []
            self._start(run_id, extra={"input": truncated})
        except Exception:
            pass

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            # Extract token usage from the LLM output dict
            llm_output = response.llm_output or {}
            token_usage = llm_output.get("token_usage", {})
            # Some providers nest it differently
            if not token_usage and response.generations:
                for gen_list in response.generations:
                    for gen in gen_list:
                        gen_info = getattr(gen, "generation_info", {}) or {}
                        token_usage = gen_info.get("token_usage", {})
                        if token_usage:
                            break

            model_name = llm_output.get("model_name", "")
            name = kwargs.get("name", model_name) or model_name or "llm"

            # T013: extract generated text output (first candidate, truncated)
            llm_output_text: str = ""
            if response.generations:
                for gen_list in response.generations:
                    for gen in gen_list:
                        text = getattr(gen, "text", "") or ""
                        if text:
                            llm_output_text = text[:2000]
                            break
                    if llm_output_text:
                        break

            # Retrieve stored input prompts from _pending (set in on_llm_start)
            stored_input = self._pending.get(str(run_id), {}).get("input", [])

            self._finish(
                run_id,
                "llm_end",
                name,
                token_usage=token_usage,
                metadata={
                    "model_name": model_name,
                    "input": stored_input,
                    "output": llm_output_text,
                },
            )
        except Exception:
            pass

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self._finish(
            run_id,
            "llm_error",
            kwargs.get("name", "llm"),
            metadata={"error": str(error)},
        )

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            # T013: store tool input for later use in on_tool_end
            self._start(run_id, extra={"input": input_str[:2000] if input_str else ""})
        except Exception:
            pass

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        name = kwargs.get("name", "") or str(run_id)
        # T013: capture tool output and retrieve stored input
        stored_input = self._pending.get(str(run_id), {}).get("input", "")
        output_str = str(output)[:2000] if output is not None else ""
        self._finish(
            run_id,
            "tool_end",
            name,
            metadata={"input": stored_input, "output": output_str},
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        name = kwargs.get("name", "") or str(run_id)
        self._finish(
            run_id,
            "tool_error",
            name,
            metadata={"error": str(error)},
        )
