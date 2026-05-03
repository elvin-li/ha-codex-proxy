# Codex Token Pool — Home Assistant 集成

把 Home Assistant 接入 **Codex 风格的反代号池**（OpenAI Responses API），
让对话代理 / 语音助手用上号池里的 GPT-5 系列模型。

> 目标场景：你已经在用 Codex CLI 走反代号池（`base_url = "https://your-codex-pool.example.com"`、`wire_api = "responses"`、`requires_openai_auth = true`），现在希望 HA 也能用同一个号池。

## 设计要点

- **薄壳子**：直接 subclass 官方 `homeassistant.components.openai_conversation.OpenAIConversationEntity`，所有对话 / 流式 / 工具调用 / reasoning / 结构化输出的逻辑都跟随官方升级，**HA Core 升级时本集成自动获益**，无需手动同步代码。
- **Codex 字段**：默认在每个请求上挂 `User-Agent: codex_cli_rs/...`、`OpenAI-Beta: responses=experimental`、`originator: codex_cli_rs`、`x-codex-installation-id: <稳定 UUID>`，避开反代针对非 Codex 客户端的限流/拒绝。
- **模型自动发现**：每 6 小时拉一次 `GET /v1/models`，新模型自动出现在下拉列表，并通过 HA `update` 实体提示一键切换（号池上 `gpt-5.6` 一上线，HA 这边就能看到 "update available"）。
- **多代理**：一个反代条目下可以挂多个 conversation 子代理，例如一个 `xhigh` 用作严肃助手，一个 `medium` 用作快问快答。

## 安装

### 通过 HACS（推荐）
1. HACS → 自定义存储库 → 添加 `https://github.com/<your-username>/codex_proxy`，类型 `Integration`。
2. 在 HACS 的集成列表里安装 **Codex Token Pool**。
3. 重启 Home Assistant。

升级走 HACS 推送，新版本自动出现在 HACS 更新列表。

### 手动
```bash
cp -r custom_components/codex_proxy /path/to/homeassistant/config/custom_components/
```
重启 HA。

## 配置

1. 设置 → 设备与服务 → 添加集成 → 搜索 **Codex Token Pool**。
2. 填：
   - **API Key** —— 反代发的 token（如 `sk-...`）。
   - **反代基础 URL** —— 例如 `https://your-codex-pool.example.com`。
   - **默认模型** —— 默认 `gpt-5.5`。
3. 提交后会自动建一个 "Codex 号池对话" 子代理，可在它的 *配置* 里改：
   - 模型（下拉显示反代实时支持的列表）
   - 推理强度：`none / medium / high / xhigh`
   - 是否在反代保留响应（关 = `disable_response_storage = true`）
   - 系统提示词
4. 设置 → 语音助手 → 选 `Codex 号池对话` 作为对话代理即可使用。

## 模型自动跟随

- 集成内置 6 小时一次的 `/v1/models` 轮询，结果直接驱动模型下拉。
- 设备页会出现一个 **Latest model from proxy** 的 update 实体：
  - `已安装版本` = 当前订阅的模型 id
  - `最新版本` = 反代当前最新的对话模型 id
  - 点 *安装* 直接把订阅模型切到最新，并自动重载条目。
- 想立刻刷新可在 *开发者工具 → 服务* 里调用 `homeassistant.update_entity`，目标选 update 实体。

## 故障排查

| 现象 | 怎么办 |
|---|---|
| 添加集成时报 `invalid_auth` | API Key 错或额度耗尽。先用下面的 curl 自检。 |
| 报 `cannot_connect` | 反代 URL 或 HA 出网有问题。试 `curl -v <base_url>/v1/models`。 |
| 报 `unknown_model` | 反代不识别填的模型。改用 `/v1/models` 里出现过的 id。 |
| 对话能开始但卡住 | 看 HA 日志里 `custom_components.codex_proxy` 的输出；流式里 5xx 我们会自动重试一次。 |

### 反代独立 smoke test
```bash
curl -sS https://your-codex-pool.example.com/v1/responses \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.5","input":"ping","max_output_tokens":16,"store":false,"reasoning":{"effort":"xhigh"}}'

curl -sS https://your-codex-pool.example.com/v1/models \
  -H "Authorization: Bearer sk-..."
```
两条都要 200。如果 `/v1/responses` 失败但 `/v1/models` 成功，多半是号池对该 token 关闭了 chat 权限。

## 已知限制

- **平台**：v1 只暴露 `conversation` + `update`。号池上的图像 / 语音模型暂不接入。
- **工具调用**：随官方实现，反代要支持相应的 tool call 才有效。
- **HA Core 版本**：依赖官方 `openai_conversation` 模块（HA 2024.10+ 内置）。如果某个未来版本重命名了 `OpenAIConversationEntity`，集成会在加载时报错；届时升级本集成即可。

## 协议

MIT.
