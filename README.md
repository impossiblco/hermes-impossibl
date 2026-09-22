# hermes-impossibl

[Impossibl](https://impossibl.com) as a first-class model provider for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Impossibl is an AI gateway: 100+ models from OpenAI, Anthropic, Google, xAI, DeepSeek, Moonshot, Z.ai, Qwen, MiniMax and more behind one OpenAI-compatible API and one key. This plugin registers the `impossibl` provider profile so `hermes model`, `--provider impossibl`, `hermes doctor` and the auxiliary-model defaults work out of the box. It ships as a standalone plugin because Hermes [does not take third-party provider plugins in-tree](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#third-party-product-integrations-ship-as-a-standalone-plugin).

## Install

```bash
hermes plugins install impossiblco/hermes-impossibl --enable
echo 'IMPOSSIBL_API_KEY=<your key>' >> ~/.hermes/.env   # create one at https://impossibl.com
hermes model                                            # choose "Impossibl", then a model
```

Or set it directly in `~/.hermes/config.yaml`:

```yaml
model:
  provider: impossibl
  default: anthropic/claude-sonnet-5
```

Switch mid-session with `/model impossibl:openai/gpt-5.5`.

## Model ids

Ids are `<creator>/<model>`: `anthropic/claude-sonnet-5`, `openai/gpt-5.5`, `google/gemini-3.8-flash`, `xai/grok-4.7`, `deepseek/deepseek-v4-pro`, `moonshotai/kimi-k3`, `zai/glm-5.3`, `minimaxai/minimax-m3`. The picker fetches the live catalogue from `https://api.impossibl.com/v1/models` and lists only the models Hermes can drive. It leaves out image, speech, transcription, embedding and rerank models, and any chat model that does not support tool calling.

## What the profile sets

| Field | Value |
|---|---|
| `name` / aliases | `impossibl` / `impossibl.com`, `impossibl-ai` |
| `api_mode` | `chat_completions` (streaming, tools, vision) |
| `base_url` | `https://api.impossibl.com/v1` (override with `IMPOSSIBL_BASE_URL`) |
| `env_vars` | `IMPOSSIBL_API_KEY`, `IMPOSSIBL_BASE_URL` |
| `default_aux_model` | `google/gemini-3.1-flash-lite` (compression, titles, vision side tasks) |
| `fallback_models` | tool-calling models shown when the live catalogue is unreachable |

Context windows come from [models.dev](https://models.dev), where `impossibl` is a listed provider.

## Without the plugin

Hermes can already reach Impossibl as a named custom provider. Add this to `~/.hermes/config.yaml` and use `/model custom:impossibl:anthropic/claude-sonnet-5`:

```yaml
providers:
  impossibl:
    api: https://api.impossibl.com/v1
    key_env: IMPOSSIBL_API_KEY
    transport: chat_completions
```

The plugin adds the picker entry, aliases, `hermes doctor` checks, a chat-only model list and aux-model defaults on top of that.

## Development

```bash
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-agent
pip install pytest pyyaml
PYTHONPATH=/tmp/hermes-agent pytest -q
```

The tests copy the plugin into a temporary `$HERMES_HOME/plugins/hermes-impossibl/` and resolve it through Hermes' real discovery path.

## License

MIT
