"""YOMA local API entry point."""

from datetime import datetime, timezone
import hashlib
import json
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path, PureWindowsPath
from urllib.parse import urlencode
import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .audit import record
from .agent import Plan, PlannerError, new_run_id, plan_goal
from .context import ContextError, assemble_context
from .config import Settings, load_settings, validate_settings
from .db import connection_scope, health_check, initialize
from .document_index import record_failed_document, search_documents, upsert_document
from .documents import DocumentError, extract_document, validate_document
from .memory import MemoryError, context_memories, new_memory_id, now_iso, search_memories, validate_category, validate_content, validate_expiration, validate_importance, validate_metadata, validate_source
from .integrations import REGISTRY, get_capability, get_integration, validate_registered_url
from .google_oauth import GoogleOAuthError, exchange_authorization_code
from .credential_vault import CredentialVault, CredentialVaultError
from .google_credentials import GoogleCredentialError, GoogleCredentialStore
from .provider import AIProvider, GenerationPolicy, GenerationResult, NoProvider, ProviderPolicyError, enforce_provider_policy, provider_from_settings
from .retrieval import RetrievalError, RetrievalSource, retrieve
from .runtime import YomaRuntime
from .security import expires_in, hash_password, is_expired, new_session, verify_password
from .tools import TOOL_REGISTRY, authorize
from .tool_execution import ToolExecutionError, ToolLimits, execute_tool
from .workspace import WorkspacePathError, discover_files, validate_child, validate_root


class LoginRequest(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str
    role: str


class WorkspaceRootCreate(BaseModel):
    path: str


class WorkspaceRoot(BaseModel):
    id: int
    path: str
    created_at: str


class WorkspaceFile(BaseModel):
    relative_path: str
    filename: str
    extension: str
    size: int
    modified_at: str
    approved_root_id: int


class DocumentIngestRequest(BaseModel):
    workspace_root_id: int
    relative_path: str


class DocumentMetadata(BaseModel):
    document_id: str
    user_id: int
    workspace_root_id: int
    canonical_path: str
    relative_path: str
    filename: str
    extension: str
    size: int
    modified_at: str
    content_type: str
    extraction_status: str
    extracted_at: str | None
    parser_name: str | None
    parser_version: str | None
    source_locations: list[dict]


class DocumentText(DocumentMetadata):
    extracted_text: str


class DocumentSearchResult(DocumentMetadata):
    excerpt: str


class AssistantQueryRequest(BaseModel):
    query: str
    limit: int = 5


class AssistantSource(BaseModel):
    document_id: str
    filename: str
    relative_path: str
    workspace_root_id: int
    excerpt: str
    rank: int
    source_locations: list[dict]


class AssistantQueryResponse(BaseModel):
    retrieval_status: str
    generation_status: str
    provider: str
    answer: str | None
    citations: list[dict]
    sources: list[AssistantSource]
    context_character_count: int
    reason: str | None = None


class ConversationCreate(BaseModel):
    title: str = ""


class ConversationSummary(BaseModel):
    id: str
    user_id: int
    title: str
    created_at: str
    updated_at: str


class ConversationMessage(BaseModel):
    id: int
    conversation_id: str
    role: str
    content: str
    metadata: dict
    created_at: str


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage]


class ConversationMessageRequest(BaseModel):
    content: str


class ToolInvokeRequest(BaseModel):
    tool: str
    arguments: dict = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    success: bool
    tool: str
    result: dict | list[dict] | None = None
    error: str | None = None


class AgentRunCreateRequest(BaseModel):
    goal: str
    conversation_id: str | None = None
    max_steps: int | None = None


class AgentApprovalResponse(BaseModel):
    id: str
    status: str
    approval_required: bool


class AgentStepResponse(BaseModel):
    id: int
    step_index: int
    action_type: str
    tool_name: str | None
    arguments: dict
    status: str
    result_metadata: dict | None
    created_at: str
    started_at: str | None
    completed_at: str | None
    failure_reason: str | None


class AgentRunResponse(BaseModel):
    id: str
    user_id: int
    conversation_id: str | None
    goal: str
    status: str
    created_at: str
    updated_at: str
    completed_at: str | None
    current_step: int
    max_steps: int
    approval_required: bool
    cancellation_requested: bool
    failure_reason: str | None
    steps: list[AgentStepResponse]


class MemoryCreateRequest(BaseModel):
    category: str
    content: str
    source: str
    importance: int = 3
    expires_at: str | None = None
    metadata: dict | None = None


class MemoryUpdateRequest(BaseModel):
    category: str | None = None
    content: str | None = None
    importance: int | None = None
    expires_at: str | None = None
    metadata: dict | None = None


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 10


class MemoryResponse(BaseModel):
    id: str
    user_id: int
    category: str
    content: str
    source: str
    importance: int
    created_at: str
    updated_at: str
    expires_at: str | None
    metadata: dict


class IntegrationCapabilityResponse(BaseModel):
    capability_id: str
    description: str
    required_scope: str
    is_write: bool
    approval_required: bool
    max_results: int


class IntegrationResponse(BaseModel):
    integration_id: str
    display_name: str
    description: str
    authentication_method: str
    enabled: bool
    capabilities: list[IntegrationCapabilityResponse]


class IntegrationConnectionResponse(BaseModel):
    id: str
    integration_id: str
    status: str
    granted_scopes: list[str]
    created_at: str
    updated_at: str
    last_used_at: str | None
    expires_at: str | None


class IntegrationConnectResponse(BaseModel):
    integration_id: str
    status: str
    authorization_url: str | None = None
    state: str | None = None


class IntegrationCallbackRequest(BaseModel):
    state: str
    code: str


class IntegrationCapabilityRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)


def create_app(settings: Settings | None = None, provider: AIProvider | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    validate_settings(app_settings)
    configured_provider = provider or provider_from_settings(app_settings)
    initialize(app_settings.database_path)

    if not app_settings.credential_vault_key:
        raise RuntimeError("YOMA credential vault key is not configured")

    try:
        credential_vault = CredentialVault(
            app_settings.credential_vault_path,
            app_settings.credential_vault_key.encode("utf-8"),
        )
        google_credentials = GoogleCredentialStore(credential_vault)
    except CredentialVaultError as exc:
        raise RuntimeError("YOMA credential vault could not be initialized") from exc

    if app_settings.bootstrap_username and app_settings.bootstrap_password:
        with connection_scope(app_settings.database_path) as connection:
            existing = connection.execute("SELECT 1 FROM users WHERE username = ?", (app_settings.bootstrap_username,)).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                    (app_settings.bootstrap_username, hash_password(app_settings.bootstrap_password), "admin", datetime.now(timezone.utc).isoformat()),
                )
                connection.commit()

    app = FastAPI(title="YOMA Local API", version="0.1.0")
    logger = logging.getLogger("yoma")
    logger.setLevel(getattr(logging, app_settings.logging_level, logging.INFO))
    pending_agent_arguments: dict[tuple[str, int], dict] = {}
    pending_oauth_states: dict[tuple[int, str], tuple[str, float]] = {}

    runtime = YomaRuntime(
        mode=app_settings.runtime_mode,
        voice_enabled=app_settings.voice_enabled,
        wake_word_enabled=app_settings.wake_word_enabled,
    )

    @app.middleware("http")
    async def operational_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", incoming) else secrets.token_urlsafe(12)
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > app_settings.max_request_body_size:
            response = JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content={"detail": "request body exceeds the configured limit", "request_id": request_id})
        else:
            started = time.monotonic()
            response = await call_next(request)
            logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, int((time.monotonic() - started) * 1000))
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unexpected_exception(request: Request, _exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("request_id=%s method=%s path=%s status=500", request_id, request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal server error", "request_id": request_id}, headers={"X-Request-ID": request_id})

    def current_user(
        authorization: str | None = Header(default=None),
    ) -> User:
        if not authorization:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "auth.missing", None, {})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
        scheme, separator, raw_token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not raw_token or raw_token != raw_token.strip() or " " in raw_token:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "auth.malformed_token", None, {})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session")
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute(
                "SELECT users.id, users.username, users.role, sessions.expires_at FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token_hash = ?",
                (token_hash,),
            ).fetchone()
            if row is None:
                record(connection, "auth.invalid_token", None, {})
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session")
            if is_expired(row["expires_at"]):
                record(connection, "auth.expired_session", row["username"], {})
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session")
            return User(id=row["id"], username=row["username"], role=row["role"])

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "yoma-local-api"}

    @app.get("/readyz")
    def readiness() -> dict:
        database_status = "ok" if health_check(app_settings.database_path) else "unavailable"
        provider_configured = (
            app_settings.ai_provider == "yoma-native"
            or (
                app_settings.ai_provider == "openai-compatible"
                and bool(app_settings.ai_base_url)
                and bool(app_settings.ai_model)
                and bool(app_settings.ai_api_key)
            )
        )
        provider_status = "configured" if provider_configured else "unavailable"
        integrations_status = "configured" if any(
            app_settings.external_integration_egress_enabled and app_settings.google_oauth_client_id and app_settings.google_oauth_client_secret and app_settings.google_oauth_redirect_uri
            for _ in (1,)
        ) else "unavailable"
        overall = "ok" if database_status == "ok" else "degraded"
        return {"status": overall, "service": "yoma-local-api", "components": {"database": database_status, "configuration": "ok", "provider": provider_status, "integrations": integrations_status}}

    @app.get("/version")
    def version() -> dict[str, str]:
        return {"application_version": "0.1.0", "api_version": "1", "build": "local"}

    @app.post("/auth/login")
    def login(request: LoginRequest) -> dict[str, str]:
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute("SELECT id, password_hash FROM users WHERE username = ?", (request.username,)).fetchone()
            if row is None or not verify_password(request.password, row["password_hash"]):
                record(connection, "auth.login_failed", request.username, {})
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
            token, token_hash = new_session()
            connection.execute("INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)", (token_hash, row["id"], expires_in(app_settings.session_ttl_seconds), datetime.now(timezone.utc).isoformat()))
            record(connection, "auth.login_succeeded", request.username, {})
            return {"access_token": token, "token_type": "bearer"}

    @app.get("/auth/me", response_model=User)
    def me(user: User = Depends(current_user)) -> User:
        return user

    @app.get("/admin/audit")
    def audit_events(user: User = Depends(current_user)) -> list[dict]:
        try:
            authorize("audit.read", user.role)
        except PermissionError:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "authz.denied", user.username, {"action": "audit.read", "role": user.role})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permissions")
        with connection_scope(app_settings.database_path) as connection:
            rows = connection.execute(
                "SELECT id, event_type, username, details_json, created_at FROM audit_events ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]

    def require_tool(user: User, tool_name: str) -> None:
        try:
            authorize(tool_name, user.role)
        except PermissionError:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "authz.denied", user.username, {"action": tool_name, "role": user.role})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient permissions")

    def tool_audit(user: User, tool_name: str, success: bool, details: dict) -> None:
        safe_details = {"tool": tool_name, "success": success, **details}
        with connection_scope(app_settings.database_path) as connection:
            record(connection, "tool.invoked", user.username, safe_details)

    @app.post("/tools/invoke", response_model=ToolInvokeResponse)
    def invoke_tool(request: ToolInvokeRequest, user: User = Depends(current_user)) -> ToolInvokeResponse:
        definition = TOOL_REGISTRY.get(request.tool)
        if definition is None:
            tool_audit(user, request.tool, False, {"error": "unknown_tool"})
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown tool")
        try:
            require_tool(user, definition.permission or definition.name)
        except HTTPException:
            tool_audit(user, request.tool, False, {"error": "authorization_denied"})
            raise
        try:
            argument_size = len(json.dumps(request.arguments, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            tool_audit(user, request.tool, False, {"error": "invalid_arguments"})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="arguments are invalid") from exc
        if argument_size > app_settings.max_tool_input_size:
            tool_audit(user, request.tool, False, {"error": "size_limit"})
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="tool input exceeds the configured limit")
        limits = ToolLimits(
            max_read_size=app_settings.max_tool_read_size,
            max_write_size=app_settings.max_tool_write_size,
            max_files=app_settings.max_tool_files,
            max_directory_depth=app_settings.max_tool_directory_depth,
        )
        try:
            with connection_scope(app_settings.database_path) as connection:
                result = execute_tool(request.tool, request.arguments, connection, user.id, limits)
            result_metadata = {"result_count": len(result)} if isinstance(result, list) else {"result_type": "metadata"}
            tool_audit(user, request.tool, True, result_metadata)
            return ToolInvokeResponse(success=True, tool=request.tool, result=result)
        except ToolExecutionError as exc:
            tool_audit(user, request.tool, False, {"error": exc.code})
            status_code = {
                "not_found": status.HTTP_404_NOT_FOUND,
                "root_not_found": status.HTTP_404_NOT_FOUND,
                "root_unavailable": status.HTTP_409_CONFLICT,
                "overwrite_denied": status.HTTP_409_CONFLICT,
                "already_exists": status.HTTP_409_CONFLICT,
                "size_limit": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            }.get(exc.code, status.HTTP_400_BAD_REQUEST)
            raise HTTPException(status_code=status_code, detail=exc.detail) from exc
        except Exception:
            tool_audit(user, request.tool, False, {"error": "execution_failed"})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tool execution failed")

    def integration_audit(user: User, event_type: str, details: dict) -> None:
        with connection_scope(app_settings.database_path) as connection:
            record(connection, event_type, user.username, details)

    def integration_enabled(integration_id: str) -> bool:
        return bool(
            app_settings.external_integration_egress_enabled
            and app_settings.google_oauth_client_id
            and app_settings.google_oauth_client_secret
            and app_settings.google_oauth_redirect_uri
            and integration_id == "google_workspace"
        )

    def integration_response(definition) -> IntegrationResponse:
        return IntegrationResponse(
            integration_id=definition.integration_id,
            display_name=definition.display_name,
            description=definition.description,
            authentication_method=definition.authentication_method,
            enabled=integration_enabled(definition.integration_id),
            capabilities=[IntegrationCapabilityResponse(**capability.__dict__) for capability in definition.capabilities],
        )

    def integration_connection_response(row, status_override: str | None = None) -> IntegrationConnectionResponse:
        try:
            scopes = json.loads(row["granted_scopes_json"])
        except (TypeError, json.JSONDecodeError):
            scopes = []
        return IntegrationConnectionResponse(
            id=row["id"], integration_id=row["integration_id"], status=status_override or row["status"],
            granted_scopes=scopes, created_at=row["created_at"], updated_at=row["updated_at"],
            last_used_at=row["last_used_at"], expires_at=row["expires_at"],
        )

    @app.get("/integrations", response_model=list[IntegrationResponse])
    def list_integrations(user: User = Depends(current_user)) -> list[IntegrationResponse]:
        require_tool(user, "integration.read")
        return [integration_response(definition) for definition in REGISTRY.values()]

    @app.get("/integrations/connections", response_model=list[IntegrationConnectionResponse])
    def list_integration_connections(user: User = Depends(current_user)) -> list[IntegrationConnectionResponse]:
        require_tool(user, "integration.read")
        now = datetime.now(timezone.utc).isoformat()
        with connection_scope(app_settings.database_path) as connection:
            rows = connection.execute("SELECT * FROM integration_connections WHERE user_id = ? ORDER BY integration_id", (user.id,)).fetchall()
            responses = []
            for row in rows:
                state = row["status"]
                if row["expires_at"] and row["expires_at"] <= now and state == "connected":
                    state = "expired"
                    record(connection, "integration.expired", user.username, {"integration_id": row["integration_id"]})
                responses.append(integration_connection_response(row, state))
            return responses

    @app.post("/integrations/{integration_id}/connect", response_model=IntegrationConnectResponse)
    def connect_integration(integration_id: str, user: User = Depends(current_user)) -> IntegrationConnectResponse:
        require_tool(user, "integration.connect")
        definition = get_integration(integration_id)
        if definition is None:
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "reason": "unknown_integration"})
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="integration not found")
        if not integration_enabled(integration_id):
            integration_audit(user, "integration.auth_failed", {"integration_id": integration_id, "status": "unavailable"})
            return IntegrationConnectResponse(integration_id=integration_id, status="unavailable")
        redirect = app_settings.google_oauth_redirect_uri or ""
        if not validate_registered_url("google_workspace", "https://accounts.google.com/o/oauth2/v2/auth") or not redirect.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]", "https://127.0.0.1", "https://localhost")):
            integration_audit(user, "integration.auth_failed", {"integration_id": integration_id, "status": "invalid_redirect"})
            return IntegrationConnectResponse(integration_id=integration_id, status="unavailable")
        state = secrets.token_urlsafe(32)
        pending_oauth_states[(user.id, integration_id)] = (state, time.time() + 600)
        scopes = " ".join(capability.required_scope for capability in definition.capabilities)
        authorization_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({"client_id": app_settings.google_oauth_client_id, "redirect_uri": redirect, "response_type": "code", "scope": scopes, "state": state, "access_type": "offline", "prompt": "consent"})
        integration_audit(user, "integration.auth_started", {"integration_id": integration_id, "status": "authorization_required"})
        return IntegrationConnectResponse(integration_id=integration_id, status="authorization_required", authorization_url=authorization_url, state=state)

    @app.post("/integrations/{integration_id}/callback", response_model=IntegrationConnectResponse)
    def integration_callback(integration_id: str, request: IntegrationCallbackRequest, user: User = Depends(current_user)) -> IntegrationConnectResponse:
        require_tool(user, "integration.connect")
        expected = pending_oauth_states.pop((user.id, integration_id), None)
        if expected is None or expected[0] != request.state or expected[1] < time.time():
            integration_audit(user, "integration.auth_failed", {"integration_id": integration_id, "status": "invalid_state"})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid OAuth state")
        if integration_id != "google_workspace":
            integration_audit(
                user,
                "integration.auth_failed",
                {"integration_id": integration_id, "status": "unsupported_callback"},
            )
            return IntegrationConnectResponse(
                integration_id=integration_id,
                status="unavailable",
            )

        if not app_settings.google_oauth_client_id or not app_settings.google_oauth_client_secret:
            integration_audit(
                user,
                "integration.auth_failed",
                {"integration_id": integration_id, "status": "oauth_not_configured"},
            )
            return IntegrationConnectResponse(
                integration_id=integration_id,
                status="unavailable",
            )

        redirect = app_settings.google_oauth_redirect_uri or ""

        try:
            token = exchange_authorization_code(
                client_id=app_settings.google_oauth_client_id,
                client_secret=app_settings.google_oauth_client_secret,
                redirect_uri=redirect,
                code=request.code,
            )
        except GoogleOAuthError:
            integration_audit(
                user,
                "integration.auth_failed",
                {"integration_id": integration_id, "status": "exchange_failed"},
            )
            return IntegrationConnectResponse(
                integration_id=integration_id,
                status="unavailable",
            )

        integration_audit(
            user,
            "integration.auth_succeeded",
            {
                "integration_id": integration_id,
                "status": "token_received",
                "expires_in": token.expires_in,
                "scope_count": len(token.scope),
                "has_refresh_token": bool(token.refresh_token),
            },
        )

        return IntegrationConnectResponse(
            integration_id=integration_id,
            status="connected",
        )

    @app.post("/integrations/{integration_id}/disconnect", response_model=IntegrationConnectResponse)
    def disconnect_integration(integration_id: str, user: User = Depends(current_user)) -> IntegrationConnectResponse:
        require_tool(user, "integration.disconnect")
        if get_integration(integration_id) is None:
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "reason": "unknown_integration"})
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="integration not found")
        pending_oauth_states.pop((user.id, integration_id), None)
        with connection_scope(app_settings.database_path) as connection:
            connection.execute("DELETE FROM integration_connections WHERE user_id = ? AND integration_id = ?", (user.id, integration_id))
            connection.commit()
            record(connection, "integration.disconnected", user.username, {"integration_id": integration_id})
        return IntegrationConnectResponse(integration_id=integration_id, status="disconnected")

    @app.get("/integrations/{integration_id}/status", response_model=IntegrationConnectResponse)
    def integration_status(integration_id: str, user: User = Depends(current_user)) -> IntegrationConnectResponse:
        require_tool(user, "integration.read")
        if get_integration(integration_id) is None:
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "reason": "unknown_integration"})
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="integration not found")
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute("SELECT status, expires_at FROM integration_connections WHERE user_id = ? AND integration_id = ?", (user.id, integration_id)).fetchone()
            if row is None:
                current_status = "unavailable" if not integration_enabled(integration_id) else "disconnected"
            elif row["expires_at"] and row["expires_at"] <= datetime.now(timezone.utc).isoformat() and row["status"] == "connected":
                current_status = "expired"
                record(connection, "integration.expired", user.username, {"integration_id": integration_id})
            else:
                current_status = row["status"]
        return IntegrationConnectResponse(integration_id=integration_id, status=current_status)

    @app.post("/integrations/{integration_id}/capabilities/{capability_id}")
    def invoke_integration_capability(integration_id: str, capability_id: str, request: IntegrationCapabilityRequest, user: User = Depends(current_user)) -> dict:
        capability = get_capability(integration_id, capability_id)
        if capability is None:
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "capability": capability_id, "reason": "unknown_capability"})
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="capability not found")
        require_tool(user, "integration.write" if capability.is_write else "integration.read")
        serialized = json.dumps(request.arguments, ensure_ascii=False, separators=(",", ":"))
        def has_network_target(value) -> bool:
            if isinstance(value, dict):
                return any(key.casefold() in {"url", "uri", "endpoint", "host"} or has_network_target(item) for key, item in value.items())
            if isinstance(value, list):
                return any(has_network_target(item) for item in value)
            return False
        requested_results = request.arguments.get("max_results")
        if isinstance(requested_results, bool) or (requested_results is not None and (not isinstance(requested_results, int) or requested_results < 1 or requested_results > min(capability.max_results, app_settings.max_integration_results))):
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "capability": capability_id, "reason": "result_limit"})
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="integration result limit exceeded")
        if len(serialized.encode("utf-8")) > app_settings.max_tool_input_size or has_network_target(request.arguments):
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "capability": capability_id, "reason": "invalid_arguments"})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="integration arguments are invalid")
        if not app_settings.external_integration_egress_enabled:
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "capability": capability_id, "reason": "egress_disabled"})
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="integration egress is disabled")
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute("SELECT * FROM integration_connections WHERE user_id = ? AND integration_id = ?", (user.id, integration_id)).fetchone()
            if row is None or row["status"] != "connected":
                record(connection, "integration.denied", user.username, {"integration_id": integration_id, "capability": capability_id, "reason": "not_connected"})
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="integration is not connected")
            try:
                scopes = json.loads(row["granted_scopes_json"])
            except (TypeError, json.JSONDecodeError):
                scopes = []
            if capability.required_scope not in scopes:
                record(connection, "integration.denied", user.username, {"integration_id": integration_id, "capability": capability_id, "reason": "scope_not_granted"})
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="required integration scope is not granted")
        if capability.is_write or capability.approval_required:
            integration_audit(user, "integration.denied", {"integration_id": integration_id, "capability": capability_id, "reason": "approval_required"})
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="integration write capability requires approval")
        integration_audit(user, "integration.denied", {"integration_id": integration_id, "capability": capability_id, "reason": "reference_client_unavailable"})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="integration capability is unavailable")

    def document_metadata(row) -> DocumentMetadata:
        return DocumentMetadata(
            document_id=row["document_id"],
            user_id=row["user_id"],
            workspace_root_id=row["workspace_root_id"],
            canonical_path=row["canonical_path"],
            relative_path=row["relative_path"],
            filename=row["filename"],
            extension=row["extension"],
            size=row["size"],
            modified_at=row["modified_at"],
            content_type=row["content_type"],
            extraction_status=row["extraction_status"],
            extracted_at=row["extracted_at"],
            parser_name=row["parser_name"],
            parser_version=row["parser_version"],
            source_locations=json.loads(row["source_metadata_json"]),
        )

    def authorized_document(connection, user: User, document_id: str):
        row = connection.execute(
            """
            SELECT d.*, r.canonical_path AS approved_root_path
            FROM documents d JOIN workspace_roots r ON r.id = d.workspace_root_id
            WHERE d.document_id = ? AND d.user_id = ? AND r.user_id = ?
            """,
            (document_id, user.id, user.id),
        ).fetchone()
        if row is None:
            return None
        try:
            from .workspace import validate_child, validate_root

            validate_child(row["canonical_path"], validate_root(row["approved_root_path"]))
        except Exception:
            return None
        return row

    def source_response(source: RetrievalSource) -> AssistantSource:
        return AssistantSource(
            document_id=source.document_id,
            filename=source.filename,
            relative_path=source.relative_path,
            workspace_root_id=source.workspace_root_id,
            excerpt=source.excerpt,
            rank=source.rank,
            source_locations=list(source.source_locations),
        )

    def citations_from_sources(sources: list[RetrievalSource]) -> list[dict]:
        return [
            {
                "document_id": source.document_id,
                "filename": source.filename,
                "relative_path": source.relative_path,
                "workspace_root_id": source.workspace_root_id,
                "excerpt": source.excerpt,
                "source_locations": list(source.source_locations),
            }
            for source in sources
        ]

    def safe_citations(generation, sources: list[RetrievalSource]) -> list[dict]:
        if generation.generation_status != "generated":
            return []
        allowed_ids = {source.document_id for source in sources}
        if generation.citations and all(
            isinstance(citation, dict) and citation.get("document_id") in allowed_ids
            for citation in generation.citations
        ):
            return list(generation.citations)
        return citations_from_sources(sources)

    def run_assistant_query(
        user: User,
        query: str,
        limit: int = 5,
        conversation_messages: list[str] | tuple[str, ...] = (),
    ) -> AssistantQueryResponse:
        require_tool(user, "assistant.query")
        try:
            with connection_scope(app_settings.database_path) as connection:
                sources = retrieve(
                    connection,
                    user.id,
                    query,
                    min(limit, app_settings.max_search_results, app_settings.max_context_documents),
                    app_settings.max_query_length,
                )
                record(connection, "document.retrieved", user.username, {"document_ids": [source.document_id for source in sources], "count": len(sources)})
        except RetrievalError as exc:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "document.retrieval_failed", user.username, {"reason": exc.code})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        with connection_scope(app_settings.database_path) as connection:
            try:
                memories = context_memories(
                    connection,
                    user.id,
                    query.strip(),
                    app_settings.max_memory_context,
                    app_settings.max_memory_search_query_length,
                )
                bounded_memories = []
                memory_characters = 0
                for memory in memories:
                    if memory_characters + len(memory.content) > app_settings.max_memory_context_chars:
                        continue
                    bounded_memories.append(memory)
                    memory_characters += len(memory.content)
                memories = bounded_memories
                record(connection, "memory.context_used", user.username, {"memory_ids": [memory.memory_id for memory in memories], "count": len(memories)})
            except MemoryError as exc:
                memories = []
                record(connection, "memory.context_used", user.username, {"memory_ids": [], "count": 0, "reason": exc.code})

        try:
            context = assemble_context(
                query.strip(),
                sources,
                max_documents=app_settings.max_context_documents,
                max_characters=app_settings.max_context_chars,
                conversation_messages=conversation_messages,
                max_conversation_messages=app_settings.max_conversation_history_messages,
                max_conversation_characters=app_settings.max_conversation_history_chars,
                memories=memories,
                max_memories=app_settings.max_memory_context,
                max_memory_characters=app_settings.max_memory_context_chars,
            )
        except ContextError as exc:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "assistant.context_rejected", user.username, {"reason": str(exc), "source_count": len(sources)})
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

        policy = GenerationPolicy(external_egress_enabled=app_settings.external_ai_egress_enabled)
        started_at = datetime.now(timezone.utc)
        try:
            enforce_provider_policy(configured_provider, policy)
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "assistant.provider_attempted", user.username, {"provider": configured_provider.name, "source_count": len(sources)})
            generation = configured_provider.generate_answer(query.strip(), context, policy)
        except ProviderPolicyError as exc:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "assistant.generation_denied", user.username, {"provider": configured_provider.name, "reason": str(exc)})
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider policy denied generation") from exc
        except Exception:
            generation = GenerationResult("failed", configured_provider.name, None, (), "provider request failed")
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

        with connection_scope(app_settings.database_path) as connection:
            provider_event = "assistant.provider_succeeded" if generation.generation_status == "generated" else "assistant.provider_failed"
            record(connection, provider_event, user.username, {"provider": generation.provider, "status": generation.generation_status, "duration_ms": duration_ms})
            record(
                connection,
                "assistant.query",
                user.username,
                {
                    "generation_status": generation.generation_status,
                    "provider": generation.provider,
                    "source_count": len(sources),
                    "document_ids": [source.document_id for source in sources],
                    "policy": "local_only",
                },
            )
        return AssistantQueryResponse(
            retrieval_status="ok",
            generation_status=generation.generation_status,
            provider=generation.provider,
            answer=generation.answer,
            citations=safe_citations(generation, sources),
            sources=[source_response(source) for source in sources],
            context_character_count=context.character_count,
            reason=generation.reason,
        )

    @app.post("/assistant/query", response_model=AssistantQueryResponse)
    def assistant_query(request: AssistantQueryRequest, user: User = Depends(current_user)) -> AssistantQueryResponse:
        return run_assistant_query(user, request.query, request.limit)

    def conversation_summary(row) -> ConversationSummary:
        return ConversationSummary(
            id=row["id"], user_id=row["user_id"], title=row["title"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def conversation_message(row) -> ConversationMessage:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return ConversationMessage(
            id=row["id"], conversation_id=row["conversation_id"], role=row["role"],
            content=row["content"], metadata=metadata, created_at=row["created_at"],
        )

    def conversation_detail(connection, row) -> ConversationDetail:
        messages = connection.execute(
            "SELECT id, conversation_id, role, content, metadata_json, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
            (row["id"],),
        ).fetchall()
        return ConversationDetail(**conversation_summary(row).model_dump(), messages=[conversation_message(message) for message in messages])

    def owned_conversation(connection, user: User, conversation_id: str):
        return connection.execute(
            "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user.id),
        ).fetchone()

    def conversation_denied(connection, user: User, conversation_id: str) -> None:
        record(connection, "conversation.authorization_denied", user.username, {"conversation_id": conversation_id})

    @app.post("/conversations", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
    def create_conversation(request: ConversationCreate | None = None, user: User = Depends(current_user)) -> ConversationSummary:
        require_tool(user, "conversation.create")
        title = request.title.strip() if request is not None else ""
        title = title or "New conversation"
        if len(title) > app_settings.conversation_title_max_length:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation title is too long")
        conversation_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with connection_scope(app_settings.database_path) as connection:
            connection.execute("INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (conversation_id, user.id, title, now, now))
            connection.commit()
            record(connection, "conversation.created", user.username, {"conversation_id": conversation_id})
            row = connection.execute("SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            return conversation_summary(row)

    @app.get("/conversations", response_model=list[ConversationSummary])
    def list_conversations(user: User = Depends(current_user)) -> list[ConversationSummary]:
        require_tool(user, "conversation.read")
        with connection_scope(app_settings.database_path) as connection:
            rows = connection.execute("SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (user.id,)).fetchall()
            return [conversation_summary(row) for row in rows]

    @app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
    def get_conversation(conversation_id: str, user: User = Depends(current_user)) -> ConversationDetail:
        require_tool(user, "conversation.read")
        with connection_scope(app_settings.database_path) as connection:
            row = owned_conversation(connection, user, conversation_id)
            if row is None:
                conversation_denied(connection, user, conversation_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
            return conversation_detail(connection, row)

    @app.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_conversation(conversation_id: str, user: User = Depends(current_user)) -> None:
        require_tool(user, "conversation.delete")
        with connection_scope(app_settings.database_path) as connection:
            row = owned_conversation(connection, user, conversation_id)
            if row is None:
                conversation_denied(connection, user, conversation_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
            connection.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user.id))
            connection.commit()
            record(connection, "conversation.deleted", user.username, {"conversation_id": conversation_id})

    @app.post("/conversations/{conversation_id}/messages", response_model=ConversationDetail)
    def add_conversation_message(conversation_id: str, request: ConversationMessageRequest, user: User = Depends(current_user)) -> ConversationDetail:
        require_tool(user, "conversation.message")
        content = request.content.strip()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message content is required")
        if len(content) > app_settings.max_user_message_length:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="message is too long")
        now = datetime.now(timezone.utc).isoformat()
        with connection_scope(app_settings.database_path) as connection:
            row = owned_conversation(connection, user, conversation_id)
            if row is None:
                conversation_denied(connection, user, conversation_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
            count = connection.execute("SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ?", (conversation_id,)).fetchone()["count"]
            if count >= app_settings.max_messages_per_conversation:
                record(connection, "conversation.limit_rejected", user.username, {"conversation_id": conversation_id, "limit": app_settings.max_messages_per_conversation})
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="conversation message limit reached")
            history_rows = connection.execute(
                "SELECT content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, app_settings.max_conversation_history_messages),
            ).fetchall()
            cursor = connection.execute("INSERT INTO messages (conversation_id, role, content, metadata_json, created_at) VALUES (?, 'user', ?, '{}', ?)", (conversation_id, content, now))
            connection.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            connection.commit()
            record(connection, "conversation.message_added", user.username, {"conversation_id": conversation_id, "message_id": cursor.lastrowid, "role": "user"})
        try:
            result = run_assistant_query(user, content, conversation_messages=tuple(row["content"] for row in reversed(history_rows)))
        except HTTPException:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "conversation.provider_failure", user.username, {"conversation_id": conversation_id, "status": "gateway_error"})
            raise
        assistant_content = result.answer or ""
        metadata = {"generation_status": result.generation_status, "provider": result.provider, "source_count": len(result.sources), "citations": result.citations}
        with connection_scope(app_settings.database_path) as connection:
            current = owned_conversation(connection, user, conversation_id)
            if current is None:
                conversation_denied(connection, user, conversation_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
            count = connection.execute("SELECT COUNT(*) AS count FROM messages WHERE conversation_id = ?", (conversation_id,)).fetchone()["count"]
            if count >= app_settings.max_messages_per_conversation:
                record(connection, "conversation.provider_failure", user.username, {"conversation_id": conversation_id, "status": "message_limit_reached"})
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="conversation message limit reached")
            cursor = connection.execute("INSERT INTO messages (conversation_id, role, content, metadata_json, created_at) VALUES (?, 'assistant', ?, ?, ?)", (conversation_id, assistant_content, json.dumps(metadata, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            connection.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), conversation_id))
            record(connection, "conversation.message_added", user.username, {"conversation_id": conversation_id, "message_id": cursor.lastrowid, "role": "assistant"})
            event = "conversation.provider_success" if result.generation_status == "generated" else "conversation.provider_failure"
            record(connection, event, user.username, {"conversation_id": conversation_id, "provider": result.provider, "status": result.generation_status, "result_count": len(result.sources)})
            connection.commit()
            refreshed = owned_conversation(connection, user, conversation_id)
            return conversation_detail(connection, refreshed)

    def memory_response(row) -> MemoryResponse:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return MemoryResponse(
            id=row["id"], user_id=row["user_id"], category=row["category"], content=row["content"],
            source=row["source"], importance=row["importance"], created_at=row["created_at"],
            updated_at=row["updated_at"], expires_at=row["expires_at"], metadata=metadata,
        )

    def memory_error_response(exc: MemoryError) -> HTTPException:
        code_status = {
            "content_too_long": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "query_too_long": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        }.get(exc.code, status.HTTP_400_BAD_REQUEST)
        return HTTPException(status_code=code_status, detail=exc.detail)

    def memory_denied(connection, user: User, memory_id: str) -> None:
        record(connection, "memory.authorization_denied", user.username, {"memory_id": memory_id})

    @app.post("/memory", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
    def create_memory(request: MemoryCreateRequest, user: User = Depends(current_user)) -> MemoryResponse:
        require_tool(user, "memory.create")
        try:
            category = validate_category(request.category)
            content = validate_content(request.content, app_settings.max_memory_content_length)
            source = validate_source(request.source)
            importance = validate_importance(request.importance)
            expires_at = validate_expiration(request.expires_at)
            metadata_json = validate_metadata(request.metadata)
        except MemoryError as exc:
            raise memory_error_response(exc) from exc
        memory_id = new_memory_id()
        created_at = now_iso()
        with connection_scope(app_settings.database_path) as connection:
            count = connection.execute("SELECT COUNT(*) AS count FROM memories WHERE user_id = ?", (user.id,)).fetchone()["count"]
            if count >= app_settings.max_memories_per_user:
                record(connection, "memory.create_denied", user.username, {"reason": "memory_limit"})
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="memory limit reached")
            connection.execute(
                "INSERT INTO memories (id, user_id, category, content, source, importance, created_at, updated_at, expires_at, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (memory_id, user.id, category, content, source, importance, created_at, created_at, expires_at, metadata_json),
            )
            connection.commit()
            record(connection, "memory.created", user.username, {"memory_id": memory_id, "category": category, "source": source})
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            return memory_response(row)

    @app.get("/memory", response_model=list[MemoryResponse])
    def list_memory(category: str | None = None, limit: int = 10, user: User = Depends(current_user)) -> list[MemoryResponse]:
        require_tool(user, "memory.read")
        if limit < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be positive")
        bounded_limit = min(limit, app_settings.max_memory_list)
        if category is not None:
            try:
                category = validate_category(category)
            except MemoryError as exc:
                raise memory_error_response(exc) from exc
        with connection_scope(app_settings.database_path) as connection:
            if category:
                query = "SELECT * FROM memories WHERE user_id = ? AND category = ? AND (expires_at IS NULL OR expires_at > ?) ORDER BY importance DESC, updated_at DESC, id LIMIT ?"
                parameters = (user.id, category, now_iso(), bounded_limit)
            else:
                query = "SELECT * FROM memories WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?) ORDER BY importance DESC, updated_at DESC, id LIMIT ?"
                parameters = (user.id, now_iso(), bounded_limit)
            rows = connection.execute(query, parameters).fetchall()
            record(connection, "memory.read", user.username, {"count": len(rows)})
            return [memory_response(row) for row in rows]

    @app.post("/memory/search", response_model=list[MemoryResponse])
    def search_memory(request: MemorySearchRequest, user: User = Depends(current_user)) -> list[MemoryResponse]:
        require_tool(user, "memory.search")
        if request.limit < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be positive")
        try:
            normalized = request.query.strip()
            if len(normalized) > app_settings.max_memory_search_query_length:
                raise MemoryError("query_too_long", "memory search query exceeds the configured limit")
            with connection_scope(app_settings.database_path) as connection:
                sources = search_memories(connection, user.id, normalized, min(request.limit, app_settings.max_memory_results), app_settings.max_memory_search_query_length)
                ids = [source.memory_id for source in sources]
                rows = connection.execute("SELECT * FROM memories WHERE user_id = ? AND id IN (%s)" % ",".join("?" for _ in ids), (user.id, *ids)).fetchall() if ids else []
                row_by_id = {row["id"]: row for row in rows}
                rows = [row_by_id[source.memory_id] for source in sources if source.memory_id in row_by_id]
                record(connection, "memory.search", user.username, {"count": len(rows)})
                return [memory_response(row) for row in rows]
        except MemoryError as exc:
            raise memory_error_response(exc) from exc

    @app.get("/memory/{memory_id}", response_model=MemoryResponse)
    def get_memory(memory_id: str, user: User = Depends(current_user)) -> MemoryResponse:
        require_tool(user, "memory.read")
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ? AND user_id = ? AND (expires_at IS NULL OR expires_at > ?)", (memory_id, user.id, now_iso())).fetchone()
            if row is None:
                memory_denied(connection, user, memory_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory not found")
            record(connection, "memory.read", user.username, {"memory_id": memory_id})
            return memory_response(row)

    @app.patch("/memory/{memory_id}", response_model=MemoryResponse)
    def update_memory(memory_id: str, request: MemoryUpdateRequest, user: User = Depends(current_user)) -> MemoryResponse:
        require_tool(user, "memory.update")
        changes = request.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="at least one memory field is required")
        try:
            if "category" in changes:
                changes["category"] = validate_category(changes["category"])
            if "content" in changes:
                changes["content"] = validate_content(changes["content"], app_settings.max_memory_content_length)
            if "importance" in changes:
                changes["importance"] = validate_importance(changes["importance"])
            if "expires_at" in changes:
                changes["expires_at"] = validate_expiration(changes["expires_at"])
            if "metadata" in changes:
                changes["metadata_json"] = validate_metadata(changes.pop("metadata"))
        except MemoryError as exc:
            raise memory_error_response(exc) from exc
        allowed = {"category", "content", "importance", "expires_at", "metadata_json"}
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ? AND user_id = ?", (memory_id, user.id)).fetchone()
            if row is None:
                memory_denied(connection, user, memory_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory not found")
            changes["updated_at"] = now_iso()
            assignments = ", ".join(f"{key} = ?" for key in changes if key in allowed or key == "updated_at")
            connection.execute(f"UPDATE memories SET {assignments} WHERE id = ? AND user_id = ?", (*[changes[key] for key in changes if key in allowed or key == "updated_at"], memory_id, user.id))
            connection.commit()
            record(connection, "memory.updated", user.username, {"memory_id": memory_id})
            return memory_response(connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone())

    @app.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_memory(memory_id: str, user: User = Depends(current_user)) -> None:
        require_tool(user, "memory.delete")
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute("SELECT id FROM memories WHERE id = ? AND user_id = ?", (memory_id, user.id)).fetchone()
            if row is None:
                memory_denied(connection, user, memory_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory not found")
            connection.execute("DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user.id))
            connection.commit()
            record(connection, "memory.deleted", user.username, {"memory_id": memory_id})

    def agent_step_response(row) -> AgentStepResponse:
        try:
            arguments = json.loads(row["arguments_json"])
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        try:
            result_metadata = json.loads(row["result_metadata_json"]) if row["result_metadata_json"] else None
        except (TypeError, json.JSONDecodeError):
            result_metadata = None
        return AgentStepResponse(
            id=row["id"], step_index=row["step_index"], action_type=row["action_type"], tool_name=row["tool_name"],
            arguments=arguments, status=row["status"], result_metadata=result_metadata,
            created_at=row["created_at"], started_at=row["started_at"], completed_at=row["completed_at"], failure_reason=row["failure_reason"],
        )

    def agent_response(connection, row) -> AgentRunResponse:
        steps = connection.execute("SELECT * FROM agent_steps WHERE agent_run_id = ? ORDER BY step_index", (row["id"],)).fetchall()
        return AgentRunResponse(
            id=row["id"], user_id=row["user_id"], conversation_id=row["conversation_id"], goal=row["goal"], status=row["status"],
            created_at=row["created_at"], updated_at=row["updated_at"], completed_at=row["completed_at"], current_step=row["current_step"],
            max_steps=row["max_steps"], approval_required=bool(row["approval_required"]), cancellation_requested=bool(row["cancellation_requested"]),
            failure_reason=row["failure_reason"], steps=[agent_step_response(step) for step in steps],
        )

    def owned_agent(connection, user: User, run_id: str):
        return connection.execute("SELECT * FROM agent_runs WHERE id = ? AND user_id = ?", (run_id, user.id)).fetchone()

    def agent_denied(connection, user: User, run_id: str) -> None:
        record(connection, "agent.authorization_denied", user.username, {"run_id": run_id})

    def agent_error(exc: PlannerError) -> HTTPException:
        code_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if exc.code in {"goal_too_long", "plan_too_large"} else status.HTTP_400_BAD_REQUEST
        return HTTPException(status_code=code_status, detail=exc.detail)

    def sanitized_agent_goal(goal: str) -> str:
        return re.sub(r"(\bcontent\s*[:=])\s*.+$", r"\1 [omitted]", goal, flags=re.IGNORECASE)

    def sanitized_agent_arguments(tool_name: str, arguments: dict) -> dict:
        sanitized = dict(arguments)
        sensitive_keys = {"content", "extracted_text", "document_content", "memory_content", "prompt", "answer"}
        for key in list(sanitized):
            if key.casefold() in sensitive_keys:
                value = sanitized.pop(key)
                sanitized[f"{key}_length"] = len(value.encode("utf-8")) if isinstance(value, str) else 0
                sanitized[f"{key}_omitted"] = True
        return sanitized

    def clear_pending_agent_arguments(run_id: str) -> None:
        for key in [key for key in pending_agent_arguments if key[0] == run_id]:
            pending_agent_arguments.pop(key, None)

    @app.post("/agent/runs", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
    def create_agent_run(request: AgentRunCreateRequest, user: User = Depends(current_user)) -> AgentRunResponse:
        require_tool(user, "agent.create")
        max_steps = app_settings.max_agent_steps if request.max_steps is None else request.max_steps
        if max_steps < 1 or max_steps > app_settings.max_agent_steps:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_steps is outside the configured limit")
        if request.conversation_id:
            with connection_scope(app_settings.database_path) as connection:
                conversation = connection.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?", (request.conversation_id, user.id)).fetchone()
                if conversation is None:
                    record(connection, "agent.authorization_denied", user.username, {"conversation_id": request.conversation_id})
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        try:
            goal, plan = plan_goal(request.goal, max_steps, app_settings.max_agent_goal_length, app_settings.max_agent_plan_size)
        except PlannerError as exc:
            raise agent_error(exc) from exc
        run_id = new_run_id()
        now = datetime.now(timezone.utc).isoformat()
        stored_goal = sanitized_agent_goal(goal)
        serialized_steps = [json.dumps(step.arguments, ensure_ascii=False, separators=(",", ":")) for step in plan.steps]
        if any(len(arguments.encode("utf-8")) > app_settings.max_agent_step_arguments for arguments in serialized_steps):
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="step arguments exceed the configured limit")
        with connection_scope(app_settings.database_path) as connection:
            count = connection.execute("SELECT COUNT(*) AS count FROM agent_runs WHERE user_id = ?", (user.id,)).fetchone()["count"]
            if count >= app_settings.max_agent_runs_per_user:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="agent run limit reached")
            run_status = "awaiting_approval" if plan.approval_required else "planned"
            connection.execute(
                "INSERT INTO agent_runs (id, user_id, conversation_id, goal, status, created_at, updated_at, max_steps, approval_required) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, user.id, request.conversation_id, stored_goal, run_status, now, now, max_steps, int(plan.approval_required)),
            )
            for step in plan.steps:
                pending_agent_arguments[(run_id, step.step_index)] = dict(step.arguments)
                connection.execute(
                    "INSERT INTO agent_steps (agent_run_id, step_index, action_type, tool_name, arguments_json, status, created_at) VALUES (?, ?, ?, ?, ?, 'planned', ?)",
                    (run_id, step.step_index, step.action_type, step.tool_name, json.dumps(sanitized_agent_arguments(step.tool_name, step.arguments), ensure_ascii=False), now),
                )
            connection.commit()
            record(connection, "agent.created", user.username, {"run_id": run_id})
            record(connection, "agent.plan_created", user.username, {"run_id": run_id, "step_count": len(plan.steps)})
            if plan.approval_required:
                record(connection, "agent.approval_required", user.username, {"run_id": run_id})
            return agent_response(connection, connection.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone())

    @app.get("/agent/runs", response_model=list[AgentRunResponse])
    def list_agent_runs(limit: int = 20, user: User = Depends(current_user)) -> list[AgentRunResponse]:
        require_tool(user, "agent.read")
        if limit < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be positive")
        with connection_scope(app_settings.database_path) as connection:
            rows = connection.execute("SELECT * FROM agent_runs WHERE user_id = ? ORDER BY updated_at DESC, id DESC LIMIT ?", (user.id, min(limit, app_settings.max_agent_runs_per_user))).fetchall()
            return [agent_response(connection, row) for row in rows]

    @app.get("/agent/runs/{run_id}", response_model=AgentRunResponse)
    def get_agent_run(run_id: str, user: User = Depends(current_user)) -> AgentRunResponse:
        require_tool(user, "agent.read")
        with connection_scope(app_settings.database_path) as connection:
            row = owned_agent(connection, user, run_id)
            if row is None:
                agent_denied(connection, user, run_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
            return agent_response(connection, row)

    @app.post("/agent/runs/{run_id}/approve", response_model=AgentApprovalResponse)
    def approve_agent_run(run_id: str, user: User = Depends(current_user)) -> AgentApprovalResponse:
        require_tool(user, "agent.approve")
        with connection_scope(app_settings.database_path) as connection:
            row = owned_agent(connection, user, run_id)
            if row is None:
                agent_denied(connection, user, run_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
            if row["status"] != "awaiting_approval" or not row["approval_required"]:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agent run is not awaiting approval")
            connection.execute("UPDATE agent_runs SET approval_required = 0, status = 'planned', updated_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), run_id))
            connection.commit()
            record(connection, "agent.approved", user.username, {"run_id": run_id})
            return AgentApprovalResponse(id=run_id, status="planned", approval_required=False)

    @app.post("/agent/runs/{run_id}/cancel", response_model=AgentApprovalResponse)
    def cancel_agent_run(run_id: str, user: User = Depends(current_user)) -> AgentApprovalResponse:
        require_tool(user, "agent.cancel")
        with connection_scope(app_settings.database_path) as connection:
            row = owned_agent(connection, user, run_id)
            if row is None:
                agent_denied(connection, user, run_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
            if row["status"] in {"completed", "failed", "cancelled"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agent run is already terminal")
            connection.execute("UPDATE agent_runs SET cancellation_requested = 1, status = 'cancelled', completed_at = ?, updated_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), run_id))
            connection.commit()
            clear_pending_agent_arguments(run_id)
            record(connection, "agent.cancelled", user.username, {"run_id": run_id})
            return AgentApprovalResponse(id=run_id, status="cancelled", approval_required=bool(row["approval_required"]))

    def agent_result_metadata(tool_name: str, result, max_size: int) -> dict:
        def redact(value):
            if isinstance(value, dict):
                output = {}
                for key, item in value.items():
                    if key.casefold() in {"content", "extracted_text", "document_content", "memory_content", "prompt", "answer"}:
                        output[f"{key}_omitted"] = True
                        output[f"{key}_length"] = len(item.encode("utf-8")) if isinstance(item, str) else 0
                    else:
                        output[key] = redact(item)
                return output
            if isinstance(value, list):
                return [redact(item) for item in value]
            return value

        if isinstance(result, list):
            metadata = {"result_count": len(result)}
        elif isinstance(result, dict):
            metadata = redact(result)
        else:
            metadata = {"result_type": type(result).__name__}
        serialized = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > max_size:
            return {"result_type": "bounded_metadata", "truncated": True}
        return metadata

    def verify_agent_result(tool_name: str, result, user: User, limits: ToolLimits) -> None:
        if tool_name == "workspace.read_text":
            if not isinstance(result, dict) or not isinstance(result.get("content"), str) or len(result["content"].encode("utf-8")) > limits.max_read_size:
                raise ToolExecutionError("verification_failed", "read result exceeded the configured limit")
            return
        if tool_name not in {"workspace.write_text", "workspace.create_directory"}:
            return
        if not isinstance(result, dict) or not isinstance(result.get("workspace_root_id"), int) or not isinstance(result.get("relative_path"), str):
            raise ToolExecutionError("verification_failed", "tool result could not be verified")
        with connection_scope(app_settings.database_path) as connection:
            root = connection.execute("SELECT canonical_path FROM workspace_roots WHERE id = ? AND user_id = ?", (result["workspace_root_id"], user.id)).fetchone()
        if root is None:
            raise ToolExecutionError("verification_failed", "approved root could not be verified")
        try:
            root_path = validate_root(root["canonical_path"])
            target = validate_child(root_path / result["relative_path"], root_path)
            if tool_name == "workspace.write_text" and not target.is_file():
                raise ToolExecutionError("verification_failed", "created file could not be verified")
            if tool_name == "workspace.create_directory" and not target.is_dir():
                raise ToolExecutionError("verification_failed", "created directory could not be verified")
        except WorkspacePathError as exc:
            raise ToolExecutionError("verification_failed", "created target could not be verified") from exc

    def mark_agent_failure(user: User, run_id: str, step_id: int | None, reason: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with connection_scope(app_settings.database_path) as connection:
            if step_id is not None:
                connection.execute("UPDATE agent_steps SET status = 'failed', failure_reason = ?, completed_at = ? WHERE id = ?", (reason, now, step_id))
            connection.execute("UPDATE agent_runs SET status = 'failed', failure_reason = ?, completed_at = ?, updated_at = ? WHERE id = ? AND user_id = ?", (reason, now, now, run_id, user.id))
            connection.commit()
            if step_id is not None:
                record(connection, "agent.step_failed", user.username, {"run_id": run_id, "step_id": step_id, "failure_category": reason})
            record(connection, "agent.failed", user.username, {"run_id": run_id, "failure_category": reason})
        clear_pending_agent_arguments(run_id)

    def execute_agent(user: User, run_id: str) -> AgentRunResponse:
        with connection_scope(app_settings.database_path) as connection:
            row = owned_agent(connection, user, run_id)
            if row is None:
                agent_denied(connection, user, run_id)
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
            if row["status"] in {"completed", "failed", "cancelled"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agent run is already terminal")
            if row["approval_required"]:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agent run requires approval")
            connection.execute("UPDATE agent_runs SET status = 'running', updated_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), run_id))
            connection.commit()
            record(connection, "agent.started", user.username, {"run_id": run_id})
        start_time = time.monotonic()
        limits = ToolLimits(app_settings.max_tool_read_size, app_settings.max_tool_write_size, app_settings.max_tool_files, app_settings.max_tool_directory_depth)
        with connection_scope(app_settings.database_path) as connection:
            steps = connection.execute("SELECT * FROM agent_steps WHERE agent_run_id = ? ORDER BY step_index", (run_id,)).fetchall()
        for step in steps:
            timed_out = False
            with connection_scope(app_settings.database_path) as connection:
                current = owned_agent(connection, user, run_id)
                if current is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent run not found")
                if current["cancellation_requested"] or current["status"] == "cancelled":
                    connection.execute("UPDATE agent_steps SET status = 'cancelled' WHERE agent_run_id = ? AND status = 'planned'", (run_id,))
                    connection.commit()
                    record(connection, "agent.cancelled", user.username, {"run_id": run_id})
                    break
                if time.monotonic() - start_time > app_settings.max_agent_execution_seconds:
                    timed_out = True
                if timed_out:
                    pass
                else:
                    started = datetime.now(timezone.utc).isoformat()
                    connection.execute("UPDATE agent_steps SET status = 'running', started_at = ? WHERE id = ?", (started, step["id"]))
                    connection.execute("UPDATE agent_runs SET current_step = ?, updated_at = ? WHERE id = ?", (step["step_index"], started, run_id))
                    connection.commit()
                    record(connection, "agent.step_started", user.username, {"run_id": run_id, "step_id": step["id"], "step_index": step["step_index"], "tool_name": step["tool_name"]})
            if timed_out:
                mark_agent_failure(user, run_id, step["id"], "execution_timeout")
                break
            try:
                definition = TOOL_REGISTRY.get(step["tool_name"])
                if definition is None:
                    raise ToolExecutionError("unknown_tool", "tool is not registered")
                require_tool(user, definition.permission or definition.name)
                arguments = pending_agent_arguments.get((run_id, step["step_index"]))
                if arguments is None:
                    stored_arguments = json.loads(step["arguments_json"])
                    if stored_arguments.get("content_omitted"):
                        raise ToolExecutionError("arguments_unavailable", "pending write arguments are unavailable")
                    arguments = stored_arguments
                if len(json.dumps(arguments, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > app_settings.max_agent_step_arguments:
                    raise ToolExecutionError("size_limit", "step arguments exceed the configured limit")
                with connection_scope(app_settings.database_path) as connection:
                    result = execute_tool(step["tool_name"], arguments, connection, user.id, limits)
                verify_agent_result(step["tool_name"], result, user, limits)
                metadata = agent_result_metadata(step["tool_name"], result, app_settings.max_agent_result_metadata_size)
                completed = datetime.now(timezone.utc).isoformat()
                with connection_scope(app_settings.database_path) as connection:
                    connection.execute("UPDATE agent_steps SET status = 'completed', result_metadata_json = ?, completed_at = ? WHERE id = ?", (json.dumps(metadata, ensure_ascii=False), completed, step["id"]))
                    connection.execute("UPDATE agent_runs SET current_step = ?, updated_at = ? WHERE id = ?", (step["step_index"], completed, run_id))
                    connection.commit()
                    record(connection, "agent.step_completed", user.username, {"run_id": run_id, "step_id": step["id"], "step_index": step["step_index"], "tool_name": step["tool_name"], **metadata})
                pending_agent_arguments.pop((run_id, step["step_index"]), None)
                if time.monotonic() - start_time > app_settings.max_agent_execution_seconds:
                    mark_agent_failure(user, run_id, None, "execution_timeout")
                    break
            except HTTPException:
                mark_agent_failure(user, run_id, step["id"], "authorization_denied")
                break
            except ToolExecutionError as exc:
                mark_agent_failure(user, run_id, step["id"], exc.code)
                break
            except Exception:
                mark_agent_failure(user, run_id, step["id"], "execution_failed")
                break
        else:
            completed = datetime.now(timezone.utc).isoformat()
            with connection_scope(app_settings.database_path) as connection:
                current = owned_agent(connection, user, run_id)
                if current and not current["cancellation_requested"]:
                    connection.execute("UPDATE agent_runs SET status = 'completed', completed_at = ?, updated_at = ? WHERE id = ?", (completed, completed, run_id))
                    connection.commit()
                    record(connection, "agent.completed", user.username, {"run_id": run_id})
                    clear_pending_agent_arguments(run_id)
        with connection_scope(app_settings.database_path) as connection:
            return agent_response(connection, owned_agent(connection, user, run_id))

    @app.post("/agent/runs/{run_id}/execute", response_model=AgentRunResponse)
    def execute_agent_run(run_id: str, user: User = Depends(current_user)) -> AgentRunResponse:
        require_tool(user, "agent.execute")
        return execute_agent(user, run_id)

    @app.post("/documents/ingest", response_model=DocumentMetadata, status_code=status.HTTP_201_CREATED)
    def ingest_document(request: DocumentIngestRequest, user: User = Depends(current_user)) -> DocumentMetadata:
        require_tool(user, "document.ingest")
        with connection_scope(app_settings.database_path) as connection:
            root = connection.execute(
                "SELECT id, canonical_path FROM workspace_roots WHERE id = ? AND user_id = ?",
                (request.workspace_root_id, user.id),
            ).fetchone()
            if root is None:
                record(connection, "document.path_denied", user.username, {"workspace_root_id": request.workspace_root_id})
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approved root not found")
            relative = Path(request.relative_path)
            if relative.is_absolute() or PureWindowsPath(request.relative_path).is_absolute():
                error = DocumentError("document path must be relative to the approved root", "path_denied")
            else:
                try:
                    document = validate_document(
                        Path(root["canonical_path"]) / relative,
                        root["canonical_path"],
                        user.id,
                        request.workspace_root_id,
                        app_settings.max_document_size,
                    )
                    error = None
                except DocumentError as exc:
                    document = None
                    error = exc
            if error is not None:
                event_type = "document.unsupported" if error.code == "unsupported_extension" else "document.unsafe_rejected"
                record(connection, event_type, user.username, {"workspace_root_id": request.workspace_root_id, "reason": error.code})
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE if error.code == "unsupported_extension" else status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

        try:
            extraction = extract_document(
                document.canonical_path,
                app_settings.max_extracted_text_size,
                app_settings.max_archive_expansion,
                app_settings.max_archive_members,
            )
        except DocumentError as exc:
            with connection_scope(app_settings.database_path) as connection:
                record_failed_document(connection, document, user.id, request.workspace_root_id, exc.code)
                connection.commit()
                record(connection, "document.extraction_failed", user.username, {"document_id": document.document_id, "reason": exc.code})
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        with connection_scope(app_settings.database_path) as connection:
            upsert_document(connection, document, user.id, request.workspace_root_id, extraction)
            connection.commit()
            record(connection, "document.extracted", user.username, {"document_id": document.document_id})
            record(connection, "document.indexed", user.username, {"document_id": document.document_id})
            row = connection.execute("SELECT * FROM documents WHERE document_id = ?", (document.document_id,)).fetchone()
            return document_metadata(row)

    @app.get("/documents/search", response_model=list[DocumentSearchResult])
    def search_document_index(q: str, limit: int = 10, user: User = Depends(current_user)) -> list[DocumentSearchResult]:
        require_tool(user, "document.search")
        with connection_scope(app_settings.database_path) as connection:
            rows = search_documents(connection, user.id, q, min(limit, app_settings.max_search_results))
            results: list[DocumentSearchResult] = []
            denied = 0
            for row in rows:
                if authorized_document(connection, user, row["document_id"]) is None:
                    denied += 1
                    continue
                metadata = document_metadata(row)
                results.append(DocumentSearchResult(**metadata.model_dump(), excerpt=row["extracted_text"][:1000]))
            record(connection, "document.search", user.username, {"result_count": len(results), "denied_count": denied})
            return results

    @app.get("/documents/{document_id}", response_model=DocumentMetadata)
    def get_document_metadata(document_id: str, user: User = Depends(current_user)) -> DocumentMetadata:
        require_tool(user, "document.metadata.read")
        with connection_scope(app_settings.database_path) as connection:
            row = authorized_document(connection, user, document_id)
            if row is None:
                record(connection, "document.access_denied", user.username, {"document_id": document_id})
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
            record(connection, "document.metadata_read", user.username, {"document_id": document_id})
            return document_metadata(row)

    @app.get("/documents/{document_id}/text", response_model=DocumentText)
    def get_document_text(document_id: str, user: User = Depends(current_user)) -> DocumentText:
        require_tool(user, "document.text.read")
        with connection_scope(app_settings.database_path) as connection:
            row = authorized_document(connection, user, document_id)
            if row is None or row["extraction_status"] != "extracted":
                record(connection, "document.access_denied", user.username, {"document_id": document_id})
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
            metadata = document_metadata(row)
            record(connection, "document.text_read", user.username, {"document_id": document_id})
            return DocumentText(**metadata.model_dump(), extracted_text=row["extracted_text"])

    @app.post("/workspace/roots", response_model=WorkspaceRoot, status_code=status.HTTP_201_CREATED)
    def add_workspace_root(request: WorkspaceRootCreate, user: User = Depends(current_user)) -> WorkspaceRoot:
        require_tool(user, "workspace.root.add")
        try:
            canonical_path = validate_root(request.path)
        except WorkspacePathError as exc:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "workspace.root_add_denied", user.username, {"reason": str(exc)})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        with connection_scope(app_settings.database_path) as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO workspace_roots (user_id, canonical_path, created_at) VALUES (?, ?, datetime('now'))",
                    (user.id, str(canonical_path)),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                record(connection, "workspace.root_duplicate", user.username, {})
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="root is already approved") from exc
            row = connection.execute(
                "SELECT id, canonical_path, created_at FROM workspace_roots WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            record(connection, "workspace.root_added", user.username, {"root_id": row["id"]})
            return WorkspaceRoot(id=row["id"], path=row["canonical_path"], created_at=row["created_at"])

    @app.get("/workspace/roots", response_model=list[WorkspaceRoot])
    def list_workspace_roots(user: User = Depends(current_user)) -> list[WorkspaceRoot]:
        require_tool(user, "workspace.root.list")
        with connection_scope(app_settings.database_path) as connection:
            rows = connection.execute(
                "SELECT id, canonical_path, created_at FROM workspace_roots WHERE user_id = ? ORDER BY id",
                (user.id,),
            ).fetchall()
            record(connection, "workspace.root_listed", user.username, {"count": len(rows)})
            return [WorkspaceRoot(id=row["id"], path=row["canonical_path"], created_at=row["created_at"]) for row in rows]

    @app.delete("/workspace/roots/{root_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_workspace_root(root_id: int, user: User = Depends(current_user)) -> None:
        require_tool(user, "workspace.root.remove")
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute(
                "SELECT id FROM workspace_roots WHERE id = ? AND user_id = ?", (root_id, user.id)
            ).fetchone()
            if row is None:
                record(connection, "workspace.root_remove_denied", user.username, {"root_id": root_id})
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approved root not found")
            connection.execute("DELETE FROM workspace_roots WHERE id = ?", (root_id,))
            connection.commit()
            record(connection, "workspace.root_removed", user.username, {"root_id": root_id})

    @app.get("/workspace/roots/{root_id}/files", response_model=list[WorkspaceFile])
    def list_workspace_files(root_id: int, user: User = Depends(current_user)) -> list[WorkspaceFile]:
        require_tool(user, "workspace.files.list")
        with connection_scope(app_settings.database_path) as connection:
            row = connection.execute(
                "SELECT id, canonical_path FROM workspace_roots WHERE id = ? AND user_id = ?", (root_id, user.id)
            ).fetchone()
            if row is None:
                record(connection, "workspace.path_denied", user.username, {"root_id": root_id})
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approved root not found")
            root_path = row["canonical_path"]

        try:
            files = discover_files(root_path)
        except WorkspacePathError as exc:
            with connection_scope(app_settings.database_path) as connection:
                record(connection, "workspace.path_denied", user.username, {"root_id": root_id, "reason": str(exc)})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        with connection_scope(app_settings.database_path) as connection:
            record(connection, "workspace.files_listed", user.username, {"root_id": root_id, "count": len(files)})
        return [WorkspaceFile(**file.__dict__, approved_root_id=root_id) for file in files]

    return app


app = create_app()
