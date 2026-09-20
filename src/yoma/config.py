"""Environment-backed configuration with safe local defaults."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    approved_roots: tuple[Path, ...]
    host: str
    port: int
    session_ttl_seconds: int
    bootstrap_username: str | None
    bootstrap_password: str | None
    max_document_size: int = 25 * 1024 * 1024
    max_extracted_text_size: int = 5 * 1024 * 1024
    max_archive_expansion: int = 50 * 1024 * 1024
    max_archive_members: int = 2000
    max_search_results: int = 50
    max_query_length: int = 1000
    max_context_documents: int = 5
    max_context_chars: int = 12000
    ai_provider: str = "none"
    ai_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_timeout_seconds: float = 20.0
    external_ai_egress_enabled: bool = False
    conversation_title_max_length: int = 120
    max_user_message_length: int = 12000
    max_messages_per_conversation: int = 100
    max_conversation_history_messages: int = 12
    max_conversation_history_chars: int = 12000
    max_tool_input_size: int = 32 * 1024
    max_tool_read_size: int = 256 * 1024
    max_tool_write_size: int = 256 * 1024
    max_tool_files: int = 1000
    max_tool_directory_depth: int = 20
    max_memory_content_length: int = 4000
    max_memory_search_query_length: int = 1000
    max_memory_results: int = 20
    max_memory_list: int = 50
    max_memories_per_user: int = 100
    max_memory_context: int = 5
    max_memory_context_chars: int = 6000
    max_agent_steps: int = 10
    max_agent_goal_length: int = 1000
    max_agent_plan_size: int = 32 * 1024
    max_agent_step_arguments: int = 32 * 1024
    max_agent_execution_seconds: int = 30
    max_agent_runs_per_user: int = 100
    max_agent_result_metadata_size: int = 8 * 1024
    external_integration_egress_enabled: bool = False
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None
    credential_vault_path: Path | None = None
    credential_vault_key: str | None = None
    max_integration_results: int = 50
    max_integration_response_chars: int = 256 * 1024
    logging_level: str = "INFO"
    max_request_body_size: int = 2 * 1024 * 1024
    runtime_mode: str = "embedded"
    voice_enabled: bool = False
    stt_provider: str = "none"
    tts_provider: str = "none"
    voice_max_seconds: int = 30
    voice_max_audio_bytes: int = 5 * 1024 * 1024
    voice_max_transcript_chars: int = 4000
    wake_word_enabled: bool = False

def load_settings() -> Settings:
    data_dir = Path(os.getenv("YOMA_DATA_DIR", "./data")).resolve()
    roots = os.getenv("YOMA_APPROVED_ROOTS", "").split(";")
    approved_roots = tuple(Path(root).expanduser().resolve() for root in roots if root.strip())
    return Settings(
        database_path=Path(os.getenv("YOMA_DATABASE_PATH", str(data_dir / "yoma.sqlite3"))).expanduser().resolve(),
        approved_roots=approved_roots,
        host=os.getenv("YOMA_HOST", "127.0.0.1"),
        port=int(os.getenv("YOMA_PORT", "8765")),
        session_ttl_seconds=int(os.getenv("YOMA_SESSION_TTL_SECONDS", "28800")),
        bootstrap_username=os.getenv("YOMA_BOOTSTRAP_USERNAME") or None,
        bootstrap_password=os.getenv("YOMA_BOOTSTRAP_PASSWORD") or None,
        max_document_size=int(os.getenv("YOMA_MAX_DOCUMENT_SIZE", str(25 * 1024 * 1024))),
        max_extracted_text_size=int(os.getenv("YOMA_MAX_EXTRACTED_TEXT_SIZE", str(5 * 1024 * 1024))),
        max_archive_expansion=int(os.getenv("YOMA_MAX_ARCHIVE_EXPANSION", str(50 * 1024 * 1024))),
        max_archive_members=int(os.getenv("YOMA_MAX_ARCHIVE_MEMBERS", "2000")),
        max_search_results=int(os.getenv("YOMA_MAX_SEARCH_RESULTS", "50")),
        max_query_length=int(os.getenv("YOMA_MAX_QUERY_LENGTH", "1000")),
        max_context_documents=int(os.getenv("YOMA_MAX_CONTEXT_DOCUMENTS", "5")),
        max_context_chars=int(os.getenv("YOMA_MAX_CONTEXT_CHARS", "12000")),
        ai_provider=os.getenv("YOMA_AI_PROVIDER", "none").strip().lower(),
        ai_base_url=os.getenv("YOMA_AI_BASE_URL") or None,
        ai_model=os.getenv("YOMA_AI_MODEL") or None,
        ai_api_key=os.getenv("YOMA_AI_API_KEY") or None,
        ai_timeout_seconds=float(os.getenv("YOMA_AI_TIMEOUT_SECONDS", "20")),
        external_ai_egress_enabled=os.getenv("YOMA_EXTERNAL_AI_EGRESS_ENABLED", "false").strip().lower() == "true",
        conversation_title_max_length=int(os.getenv("YOMA_CONVERSATION_TITLE_MAX_LENGTH", "120")),
        max_user_message_length=int(os.getenv("YOMA_MAX_USER_MESSAGE_LENGTH", "12000")),
        max_messages_per_conversation=int(os.getenv("YOMA_MAX_MESSAGES_PER_CONVERSATION", "100")),
        max_conversation_history_messages=int(os.getenv("YOMA_MAX_CONVERSATION_HISTORY_MESSAGES", "12")),
        max_conversation_history_chars=int(os.getenv("YOMA_MAX_CONVERSATION_HISTORY_CHARS", "12000")),
        max_tool_input_size=int(os.getenv("YOMA_MAX_TOOL_INPUT_SIZE", str(32 * 1024))),
        max_tool_read_size=int(os.getenv("YOMA_MAX_TOOL_READ_SIZE", str(256 * 1024))),
        max_tool_write_size=int(os.getenv("YOMA_MAX_TOOL_WRITE_SIZE", str(256 * 1024))),
        max_tool_files=int(os.getenv("YOMA_MAX_TOOL_FILES", "1000")),
        max_tool_directory_depth=int(os.getenv("YOMA_MAX_TOOL_DIRECTORY_DEPTH", "20")),
        max_memory_content_length=int(os.getenv("YOMA_MAX_MEMORY_CONTENT_LENGTH", "4000")),
        max_memory_search_query_length=int(os.getenv("YOMA_MAX_MEMORY_SEARCH_QUERY_LENGTH", "1000")),
        max_memory_results=int(os.getenv("YOMA_MAX_MEMORY_RESULTS", "20")),
        max_memory_list=int(os.getenv("YOMA_MAX_MEMORY_LIST", "50")),
        max_memories_per_user=int(os.getenv("YOMA_MAX_MEMORIES_PER_USER", "100")),
        max_memory_context=int(os.getenv("YOMA_MAX_MEMORY_CONTEXT", "5")),
        max_memory_context_chars=int(os.getenv("YOMA_MAX_MEMORY_CONTEXT_CHARS", "6000")),
        max_agent_steps=int(os.getenv("YOMA_MAX_AGENT_STEPS", "10")),
        max_agent_goal_length=int(os.getenv("YOMA_MAX_AGENT_GOAL_LENGTH", "1000")),
        max_agent_plan_size=int(os.getenv("YOMA_MAX_AGENT_PLAN_SIZE", str(32 * 1024))),
        max_agent_step_arguments=int(os.getenv("YOMA_MAX_AGENT_STEP_ARGUMENTS", str(32 * 1024))),
        max_agent_execution_seconds=int(os.getenv("YOMA_MAX_AGENT_EXECUTION_SECONDS", "30")),
        max_agent_runs_per_user=int(os.getenv("YOMA_MAX_AGENT_RUNS_PER_USER", "100")),
        max_agent_result_metadata_size=int(os.getenv("YOMA_MAX_AGENT_RESULT_METADATA_SIZE", str(8 * 1024))),
        external_integration_egress_enabled=os.getenv("YOMA_EXTERNAL_INTEGRATION_EGRESS_ENABLED", "false").strip().lower() == "true",
        google_oauth_client_id=os.getenv("YOMA_GOOGLE_OAUTH_CLIENT_ID") or None,
        google_oauth_client_secret=os.getenv("YOMA_GOOGLE_OAUTH_CLIENT_SECRET") or None,
        google_oauth_redirect_uri=os.getenv("YOMA_GOOGLE_OAUTH_REDIRECT_URI") or None,
        credential_vault_path=Path(os.getenv("YOMA_CREDENTIAL_VAULT_PATH", str(data_dir / "credentials.vault"))).expanduser().resolve(),
        credential_vault_key=os.getenv("YOMA_CREDENTIAL_VAULT_KEY") or None,
        max_integration_results=int(os.getenv("YOMA_MAX_INTEGRATION_RESULTS", "50")),
        max_integration_response_chars=int(os.getenv("YOMA_MAX_INTEGRATION_RESPONSE_CHARS", str(256 * 1024))),
        logging_level=os.getenv("YOMA_LOGGING_LEVEL", "INFO").strip().upper(),
        max_request_body_size=int(os.getenv("YOMA_MAX_REQUEST_BODY_SIZE", str(2 * 1024 * 1024))),
    )


def validate_settings(settings: Settings) -> None:
    """Reject structurally unsafe local configuration before serving requests."""
    if not settings.host.strip() or not 1 <= settings.port <= 65535:
        raise ValueError("host or port configuration is invalid")
    if settings.session_ttl_seconds <= 0:
        raise ValueError("session TTL must be positive")
    if settings.ai_provider not in {"none", "yoma-native", "openai-compatible"}:
        raise ValueError("AI provider is not registered")
    if settings.ai_timeout_seconds <= 0:
        raise ValueError("AI provider timeout must be positive")
    if bool(settings.bootstrap_username) != bool(settings.bootstrap_password):
        raise ValueError("bootstrap username and password must be configured together")
    if settings.max_request_body_size < 1024:
        raise ValueError("request body limit is too small")
    if settings.logging_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        raise ValueError("logging level is invalid")
    if settings.external_integration_egress_enabled and (settings.google_oauth_client_id or settings.google_oauth_client_secret) and not settings.google_oauth_redirect_uri:
        raise ValueError("integration egress requires an OAuth redirect URI")
