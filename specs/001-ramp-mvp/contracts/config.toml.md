# Contract: `~/.ramp/config.toml`

Created by `ramp init` (defaults, secrets never written). Loaded by `providers` and `gate`. Validation errors stop the command before any network call.

```toml
schema_version = 1

[gate]
pass_threshold = 3            # int 0..5; Art. IV / OD-7

[caps]
max_cost_usd_per_command = 0.50
max_cost_usd_per_day     = 3.00
max_regenerations        = 2        # lint + generation-time check
max_retries              = 2        # provider retries, backoff 1s then 3s

[roles.planner]               # strong
base_url   = "https://openrouter.ai/api/v1"
base_url_env = "OPENROUTER_API_URL"   # optional: name of an env var; when set and non-empty it replaces base_url
api_key_env = "API_KEY"   # name of an env var; the key itself is never stored
model      = "claude-opus-5-5"      # default; any model id the endpoint accepts
max_input_tokens  = 24000
max_output_tokens = 6000
usd_per_mtok_in   = 0.0             # owner fills; used only by the cost meter
usd_per_mtok_out  = 0.0

[roles.writer]                # strong
base_url = "https://openrouter.ai/api/v1"
api_key_env = "API_KEY"
model = "claude-sonnet-5-5"
max_input_tokens = 24000
max_output_tokens = 8000
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0

[roles.reviewer]              # must differ from writer
base_url = "https://openrouter.ai/api/v1"
api_key_env = "API_KEY"
model = "claude-haiku-5-5"
max_input_tokens = 24000
max_output_tokens = 3000
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0

[roles.grader]                # cheap
base_url = "https://openrouter.ai/api/v1"
api_key_env = "API_KEY"
model = "claude-haiku-5-5"
max_input_tokens = 6000
max_output_tokens = 600
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0
```

**Validation rules**: all four roles present; `roles.reviewer.model != roles.writer.model` (error otherwise); `model` not starting with `REPLACE_ME` when a call is attempted (clear message naming the file and key; the generated defaults are working models, so a fresh `init` does not stop on this); `pass_threshold` in 0..5; caps > 0; `base_url` https, or http only for loopback (local endpoints allowed, Art. VIII); unknown keys are errors. If `base_url_env` names a set, non-empty environment variable, its value replaces `base_url` at call time and must pass the same https/loopback rule (error otherwise). A local endpoint (Ollama / LM Studio) is a valid `base_url`; its `api_key_env` may be empty.

**Optional `thinking`** (per role, bool, default unset): `thinking = false` asks the provider not to spend output tokens on hidden reasoning. It is applied only on the native Anthropic endpoint (`base_url` host ends with `anthropic.com`, sent as `thinking: {type: disabled}`) and ignored elsewhere. The generated default sets it to `false` for `reviewer` and `grader`, whose replies are short structured data.

**Egress**: `providers` sends brief + diff + test output (submit) and written answers (cards, teach-back); nothing else.
