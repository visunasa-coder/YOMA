"""Explicitly allowlisted tool definitions; no shell execution is permitted."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    required_roles: frozenset[str]
    description: str = ""
    permission: str | None = None
    input_schema: dict | None = None


ALLOWLIST = {
    "health.read": ToolDefinition("health.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "audit.read": ToolDefinition("audit.read", frozenset({"admin", "security_admin", "auditor"})),
    "workspace.root.add": ToolDefinition("workspace.root.add", frozenset({"user", "admin", "security_admin", "auditor"})),
    "workspace.root.list": ToolDefinition("workspace.root.list", frozenset({"user", "admin", "security_admin", "auditor"})),
    "workspace.root.remove": ToolDefinition("workspace.root.remove", frozenset({"user", "admin", "security_admin", "auditor"})),
    "workspace.files.list": ToolDefinition("workspace.files.list", frozenset({"user", "admin", "security_admin", "auditor"})),
    "document.ingest": ToolDefinition("document.ingest", frozenset({"user", "admin", "security_admin", "auditor"})),
    "document.metadata.read": ToolDefinition("document.metadata.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "document.search": ToolDefinition("document.search", frozenset({"user", "admin", "security_admin", "auditor"})),
    "document.text.read": ToolDefinition("document.text.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "assistant.query": ToolDefinition("assistant.query", frozenset({"user", "admin", "security_admin", "auditor"})),
    "conversation.create": ToolDefinition("conversation.create", frozenset({"user", "admin", "security_admin", "auditor"})),
    "conversation.read": ToolDefinition("conversation.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "conversation.delete": ToolDefinition("conversation.delete", frozenset({"user", "admin", "security_admin", "auditor"})),
    "conversation.message": ToolDefinition("conversation.message", frozenset({"user", "admin", "security_admin", "auditor"})),
    "workspace.list_files": ToolDefinition(
        "workspace.list_files", frozenset({"user", "admin", "security_admin", "auditor"}),
        "List bounded metadata for files in an owned approved root.", "workspace.list_files", {"type": "object", "required": ["workspace_root_id"]},
    ),
    "workspace.file_info": ToolDefinition(
        "workspace.file_info", frozenset({"user", "admin", "security_admin", "auditor"}),
        "Return metadata for one file in an owned approved root.", "workspace.file_info", {"type": "object", "required": ["workspace_root_id", "relative_path"]},
    ),
    "workspace.read_text": ToolDefinition(
        "workspace.read_text", frozenset({"user", "admin", "security_admin", "auditor"}),
        "Read bounded UTF-8 text from an owned approved text file.", "workspace.read_text", {"type": "object", "required": ["workspace_root_id", "relative_path"]},
    ),
    "workspace.write_text": ToolDefinition(
        "workspace.write_text", frozenset({"user", "admin", "security_admin", "auditor"}),
        "Create a new UTF-8 text file in an owned approved root without overwriting.", "workspace.write_text", {"type": "object", "required": ["workspace_root_id", "relative_path", "content"]},
    ),
    "workspace.create_directory": ToolDefinition(
        "workspace.create_directory", frozenset({"user", "admin", "security_admin", "auditor"}),
        "Create a directory inside an owned approved root.", "workspace.create_directory", {"type": "object", "required": ["workspace_root_id", "relative_path"]},
    ),
    "memory.create": ToolDefinition("memory.create", frozenset({"user", "admin", "security_admin", "auditor"})),
    "memory.read": ToolDefinition("memory.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "memory.update": ToolDefinition("memory.update", frozenset({"user", "admin", "security_admin", "auditor"})),
    "memory.delete": ToolDefinition("memory.delete", frozenset({"user", "admin", "security_admin", "auditor"})),
    "memory.search": ToolDefinition("memory.search", frozenset({"user", "admin", "security_admin", "auditor"})),
    "agent.create": ToolDefinition("agent.create", frozenset({"user", "admin", "security_admin", "auditor"})),
    "agent.read": ToolDefinition("agent.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "agent.approve": ToolDefinition("agent.approve", frozenset({"user", "admin", "security_admin", "auditor"})),
    "agent.cancel": ToolDefinition("agent.cancel", frozenset({"user", "admin", "security_admin", "auditor"})),
    "agent.execute": ToolDefinition("agent.execute", frozenset({"user", "admin", "security_admin", "auditor"})),
    "integration.read": ToolDefinition("integration.read", frozenset({"user", "admin", "security_admin", "auditor"})),
    "integration.write": ToolDefinition("integration.write", frozenset({"user", "admin", "security_admin", "auditor"})),
    "integration.connect": ToolDefinition("integration.connect", frozenset({"user", "admin", "security_admin", "auditor"})),
    "integration.disconnect": ToolDefinition("integration.disconnect", frozenset({"user", "admin", "security_admin", "auditor"})),
}


TOOL_REGISTRY = {name: definition for name, definition in ALLOWLIST.items() if name.startswith("workspace.") and name in {
    "workspace.list_files", "workspace.file_info", "workspace.read_text", "workspace.write_text", "workspace.create_directory"
}}


def authorize(tool_name: str, role: str) -> ToolDefinition:
    tool = ALLOWLIST.get(tool_name)
    if tool is None or role not in tool.required_roles:
        raise PermissionError("tool is not allowlisted for this role")
    return tool
