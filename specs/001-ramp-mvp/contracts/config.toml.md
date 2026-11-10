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
api_key_env = "OPENROUTER_API_KEY"   # name of an env var; the key itself is never stored
model      = "REPLACE_ME"           # OpenRouter model id (owner-chosen; unverified placeholder)
max_input_tokens  = 24000
max_output_tokens = 6000
usd_per_mtok_in   = 0.0             # owner fills; used only by the cost meter
usd_per_mtok_out  = 0.0

[roles.writer]                # strong
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
model = "REPLACE_ME"
max_input_tokens = 24000
max_output_tokens = 8000
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0

[roles.reviewer]              # must differ from writer
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
model = "REPLACE_ME_DIFFERENT"
max_input_tokens = 24000
max_output_tokens = 3000
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0

[roles.grader]                # cheap
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
model = "REPLACE_ME_CHEAP"
max_input_tokens = 6000
max_output_tokens = 600
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0
```

**Validation rules**: all four roles present; `roles.reviewer.model != roles.writer.model` (error otherwise); `model` not starting with `REPLACE_ME` when a call is attempted (clear message naming the file and key); `pass_threshold` in 0..5; caps > 0; `base_url` https, or http only for loopback (local endpoints allowed, Art. VIII); unknown keys are errors. A local endpoint (Ollama / LM Studio) is a valid `base_url`; its `api_key_env` may be empty.

**Egress**: `providers` sends brief + diff + test output (submit) and written answers (cards, teach-back); nothing else.
