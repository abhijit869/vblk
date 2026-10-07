import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

new_gateway = """
class AIGateway:
    \"\"\"Routes requests to the primary provider with retry, then to a fallback.\"\"\"

    def __init__(
        self,
        primary: AIProvider | None = None,
        fallback: AIProvider | None = None,
        max_retries: int = 2,
        backoff_s: float = 0.5,
        max_backoff_s: float = 8.0,
        sleep: Callable[[float], None] = time.sleep,
        failure_threshold: int = 2,
        recovery_threshold: int = 3,
    ) -> None:
        self._primary = primary or MockAIProvider()
        self._fallback = fallback
        self._max_retries = max(0, max_retries)
        self._backoff_s = backoff_s
        self._max_backoff_s = max_backoff_s
        self._sleep = sleep
        
        self._failure_threshold = failure_threshold
        self._recovery_threshold = recovery_threshold
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._circuit_open = False

    @property
    def primary(self) -> AIProvider:
        return self._primary

    @property
    def fallback(self) -> AIProvider | None:
        return self._fallback

    def health(self) -> ProviderHealth:
        # Check circuit state
        if self._circuit_open:
            h = self._primary.health()
            if h.status == ProviderStatus.HEALTHY:
                self._consecutive_successes += 1
                if self._consecutive_successes >= self._recovery_threshold:
                    self._circuit_open = False
                    self._consecutive_failures = 0
                    self._consecutive_successes = 0
            else:
                self._consecutive_successes = 0
            
            if self._circuit_open and self._fallback:
                return self._fallback.health()

        h = self._primary.health()
        if h.status == ProviderStatus.UNAVAILABLE and self._fallback:
            return self._fallback.health()
        return h

    def complete(self, request: AIRequest) -> AIResponse:
        return self._route(request, lambda provider: provider.complete(request))

    def respond(
        self, request: AIRequest, outputs: Sequence[AIToolOutput]
    ) -> AIResponse:
        return self._route(request, lambda provider: provider.respond(request, outputs))

    def _route(
        self, request: AIRequest, call: Callable[[AIProvider], AIResponse]
    ) -> AIResponse:
        self.health() # trigger health checks and circuit breaker logic
        
        if self._circuit_open:
            return self._use_fallback(request, call, "Circuit breaker open")

        health = self._primary.health()
        if health.status == ProviderStatus.UNAVAILABLE:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._circuit_open = True
            reason = health.message or "AI provider unavailable"
            return self._use_fallback(request, call, reason)

        try:
            res = self._with_retry(self._primary, call)
            self._consecutive_failures = 0
            return res
        except ProviderError as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._circuit_open = True
            return self._use_fallback(request, call, str(exc))

    def _with_retry(
        self, provider: AIProvider, call: Callable[[AIProvider], AIResponse]
    ) -> AIResponse:
        attempt = 0
        while True:
            try:
                return call(provider)
            except ProviderError as exc:
                if not exc.retryable or attempt >= self._max_retries:
                    raise
                delay = (
                    exc.retry_after_s
                    if exc.retry_after_s is not None
                    else self._backoff_s * (2**attempt)
                )
                self._sleep(min(delay, self._max_backoff_s))
                attempt += 1

    def _use_fallback(
        self, request: AIRequest, call: Callable[[AIProvider], AIResponse], reason: str
    ) -> AIResponse:
        if self._fallback is None:
            return AIResponse(
                request_id=request.request_id,
                provider=self._primary.name,
                model=request.model or "unknown",
                content=f"AI provider unavailable: {reason}",
                tool_calls=[],
                error=reason,
            )
        try:
            response = call(self._fallback)
        except ProviderError as exc:
            return AIResponse(
                request_id=request.request_id,
                provider=self._fallback.name,
                model=request.model or "unknown",
                content=f"AI provider unavailable: {reason}; fallback failed: {exc}",
                tool_calls=[],
                error=f"{reason}; fallback failed: {exc}",
            )
        return AIResponse(
            request_id=response.request_id,
            provider=response.provider,
            model=response.model,
            content=response.content,
            tool_calls=response.tool_calls,
            usage=response.usage,
            fallback_from=self._primary.name,
            error=reason,
        )
"""

pattern = re.compile(r"class AIGateway:.*?def _use_fallback\(.*?error=reason,\n        \)", re.DOTALL)
content = pattern.sub(new_gateway.strip(), content)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)
