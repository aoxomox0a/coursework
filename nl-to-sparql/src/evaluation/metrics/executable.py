"""Funnel stage 2 — does the endpoint actually accept and execute the query?"""
from dataclasses import dataclass
from enum import Enum

from src.sparql.execution import execute_query


class ExecutableStatus(str, Enum):
    OK = "ok"
    ENDPOINT_ERROR = "endpoint_error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ExecutableResult:
    status: ExecutableStatus
    bindings: list[dict] | None
    error: str


def _classify_error(message: str) -> ExecutableStatus:
    msg = message.lower()
    if "timeout" in msg or "timed out" in msg:
        return ExecutableStatus.TIMEOUT
    return ExecutableStatus.ENDPOINT_ERROR


async def evaluate_executable(query: str, endpoint: str) -> ExecutableResult:
    """Execute ``query`` against ``endpoint`` and classify the response."""
    response = await execute_query(query, endpoint_url=endpoint)

    if "error" in response:
        message = str(response["error"])
        return ExecutableResult(
            status=_classify_error(message),
            bindings=None,
            error=message,
        )

    bindings = response.get("results", {}).get("bindings", [])
    return ExecutableResult(
        status=ExecutableStatus.OK,
        bindings=bindings,
        error="",
    )
