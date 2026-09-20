from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping


VALID_STATUSES = {
    "pending",
    "running",
    "succeeded",
    "failed",
    "rejected",
}


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    action_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    requires_human_approval: bool = True
    executable: bool = True

    def __post_init__(self) -> None:
        if not self.execution_id.startswith("EXEC-"):
            raise ValueError("execution_id must start with EXEC-")

        if not self.action_id:
            raise ValueError("action_id is required")

        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid execution status: {self.status}")

        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")


@dataclass(frozen=True)
class ExecutionRecord:
    execution_id: str
    action_id: str
    action_type: str
    executor_name: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    requires_human_approval: bool = True


class ActionExecutionGateway:
    """
    Controlled execution boundary for YOMA.

    This gateway never decides whether an action should happen.
    It only executes an action after an already-approved workflow
    has explicitly authorized it.
    """

    def __init__(self) -> None:
        self._executors: dict[str, Callable[..., Mapping[str, Any]]] = {}
        self._records: dict[str, ExecutionRecord] = {}

    @property
    def records(self) -> tuple[ExecutionRecord, ...]:
        return tuple(
            self._records[key]
            for key in sorted(self._records)
        )

    @property
    def executor_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._executors))

    def register_executor(
        self,
        name: str,
        executor: Callable[..., Mapping[str, Any]],
    ) -> None:
        if not name:
            raise ValueError("executor name is required")

        if not callable(executor):
            raise TypeError("executor must be callable")

        if name in self._executors:
            raise ValueError(
                f"executor already registered: {name}"
            )

        self._executors[name] = executor

    def unregister_executor(self, name: str) -> None:
        self._executors.pop(name, None)

    def get_record(
        self,
        execution_id: str,
    ) -> ExecutionRecord | None:
        return self._records.get(execution_id)

    def execute(
        self,
        *,
        action_id: str,
        action_type: str,
        executor_name: str,
        approved: bool,
        created_at: datetime,
        parameters: Mapping[str, Any] | None = None,
    ) -> ExecutionResult:
        if not action_id:
            raise ValueError("action_id is required")

        if not action_type:
            raise ValueError("action_type is required")

        if not approved:
            execution_id = f"EXEC-{action_id}-REJECTED"

            result = ExecutionResult(
                execution_id=execution_id,
                action_id=action_id,
                status="rejected",
                started_at=created_at,
                completed_at=created_at,
                error="human approval is required before execution",
                requires_human_approval=True,
                executable=False,
            )

            self._records[execution_id] = ExecutionRecord(
                execution_id=execution_id,
                action_id=action_id,
                action_type=action_type,
                executor_name=executor_name,
                status="rejected",
                created_at=created_at,
                completed_at=created_at,
                error=result.error,
                requires_human_approval=True,
            )

            return result

        executor = self._executors.get(executor_name)

        if executor is None:
            raise ValueError(
                f"executor is not registered: {executor_name}"
            )

        execution_id = f"EXEC-{action_id}"

        existing = self._records.get(execution_id)

        if existing is not None:
            raise ValueError(
                f"execution already exists: {execution_id}"
            )

        started_at = created_at

        self._records[execution_id] = ExecutionRecord(
            execution_id=execution_id,
            action_id=action_id,
            action_type=action_type,
            executor_name=executor_name,
            status="running",
            created_at=created_at,
            started_at=started_at,
            requires_human_approval=True,
        )

        try:
            output = executor(
                action_id=action_id,
                action_type=action_type,
                parameters=dict(parameters or {}),
            )

            if output is None:
                output = {}

            if not isinstance(output, Mapping):
                raise TypeError(
                    "executor must return a mapping"
                )

            completed_at = created_at

            record = ExecutionRecord(
                execution_id=execution_id,
                action_id=action_id,
                action_type=action_type,
                executor_name=executor_name,
                status="succeeded",
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                output=dict(output),
                requires_human_approval=True,
            )

            self._records[execution_id] = record

            return ExecutionResult(
                execution_id=execution_id,
                action_id=action_id,
                status="succeeded",
                started_at=started_at,
                completed_at=completed_at,
                output=dict(output),
                requires_human_approval=True,
                executable=True,
            )

        except Exception as exc:
            completed_at = created_at
            error = str(exc)

            record = ExecutionRecord(
                execution_id=execution_id,
                action_id=action_id,
                action_type=action_type,
                executor_name=executor_name,
                status="failed",
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                error=error,
                requires_human_approval=True,
            )

            self._records[execution_id] = record

            return ExecutionResult(
                execution_id=execution_id,
                action_id=action_id,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                error=error,
                requires_human_approval=True,
                executable=True,
            )

    def execute_approved(
        self,
        *,
        action_id: str,
        action_type: str,
        executor_name: str,
        created_at: datetime,
        parameters: Mapping[str, Any] | None = None,
    ) -> ExecutionResult:
        return self.execute(
            action_id=action_id,
            action_type=action_type,
            executor_name=executor_name,
            approved=True,
            created_at=created_at,
            parameters=parameters,
        )
