# Codex Token Pool — Home Assistant 集成

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![HA Core ≥ 2024.10](https://img.shields.io/badge/HA-≥2024.10-03a9f4.svg)](https://www.home-assistant.io/)
[![Tests](https://github.com/elvin-li/ha-codex-proxy/actions/workflows/tests.yml/badge.svg)](https://github.com/elvin-li/ha-codex-proxy/actions/workflows/tests.yml)

把 Home Assistant 接入 **Codex 风格的反代号池**（OpenAI Responses API），
让对话代理 / 语音助手、AI Task 用上号池里的 GPT-5 系列模型。

> **目标场景：** 你已经在用 Codex CLI 走反代号池  
> （`base_url = "https://your-codex-pool.example.com"`、`wire_api = "responses"`、`requires_openai_auth = true`），  
> 现在希望 HA 也能用同一个号池。

---

## 设计要点

| 特性 | 说明 |
|---|---|
| **薄壳子** | 直接 subclass 官方 `openai_conversation`，流式 / 工具调用 / reasoning / 结构化输出随 HA Core 升级自动获益 |
| **Codex 请求头** | 每个请求自动带 `User-Agent: codex_cli_rs/...`、`OpenAI-Beta: responses=experimental`、`originator: codex_cli_rs`、`x-codex-installation-id: <稳定 UUID>` |
| **模型自动发现** | 每 6 小时拉一次 `/v1/models`，新模型即时出现在下拉，`update` 实体提示一键切换 |
| **多子代理** | 一个条目下可以挂多个对话 / AI Task 子代理，每个独立配置模型、推理强度、系统 Prompt |
| **retry + 退避** | 5xx / 超时自动重试（最多 3 次，间隔 5s → 30s），连接失败即时上报 |
| **diagnostics** | 开发者工具里可下载诊断报告，API Key 自动打码 |

---

## 安装

### 通过 HACS（推荐）

1. HACS → 自定义存储库 → 添加 `https://github.com/elvin-li/ha-codex-proxy`，类型 `Integration`。
2. 在 HACS 集成列表里安装 **Codex Token Pool**。
3. 重启 Home Assistant。

### 手动

```bash
cp -r custom_components/codex_proxy /path/to/homeassistant/config/custom_components/
```

重启 HA。

---

## 配置

### 方法一：粘贴 config.toml（最快）

如果你已经在用 Codex CLI，直接把 `~/.codex/config.toml` 的内容粘进去，集成会自动提取 `base_url`、`model`、推理强度和存储开关：

```toml
model = "gpt-5.5"
model_reasoning_effort = "xhigh"
disable_response_storage = true

[model_providers.mypool]
base_url = "https://your-codex-pool.example.com"
wire_api = "responses"
```

### 方法二：手动填写

1. 设置 → 设备与服务 → 添加集成 → 搜索 **Codex Token Pool**。
2. 填写：
   - **API Key** — 反代发的 token（如 `sk-...`）
   - **反代基础 URL** — 例如 `https://your-codex-pool.example.com`（不要加 `/v1`）
   - **默认模型** — 默认 `gpt-5.5`

提交后自动创建：
- **Codex 号池对话** — 对话代理子代理
- **Codex 号池 AI Task** — AI Task 数据生成子代理

---

## 子代理配置

每个子代理（对话 / AI Task）都可单独调整：

| 字段 | 说明 |
|---|---|
| **模型** | 下拉显示反代实时支持的列表，也可手填任意 id |
| **推理强度** | `none / medium / high / xhigh`（xhigh 最深但最慢）|
| **在反代保留响应** | 关 ↔ Codex CLI 的 `disable_response_storage = true` |
| **系统提示词** | 可用 HA 模板语法 |

在 设置 → 设备与服务 → Codex Token Pool → `···` → **添加子代理** 可以继续加更多实例。

---

## 重新配置连接

需要换 API Key 或换反代地址时，不用删除整个条目：

设置 → 设备与服务 → Codex Token Pool → `···` → **重新配置**

会弹出和初始安装一样的表单，预填当前值，已有的子代理全部保留。

---

## 模型自动跟随

- 每 6 小时自动拉一次 `/v1/models`，模型下拉实时更新。
- 设备页会出现 **Latest model from proxy** 的 `update` 实体：
  - `已安装版本` = 当前子代理订阅的模型
  - `最新版本` = 反代当前最新的对话模型
  - 点 **安装** 一键切换并自动重载。
- 想立即刷新：开发者工具 → 服务 → `homeassistant.update_entity`，目标选 update 实体。

---

## 诊断信息

设置 → 设备与服务 → Codex Token Pool → 下载诊断信息

报告包含：
- 集成配置（API Key 已打码）
- coordinator 状态（上次成功时间、模型总数、最新模型 ID）
- 所有子代理的类型 / 标题 / 配置

可在提 Bug 时附上，方便定位问题。

---

## 实体一览

### 默认启用

| 实体 | 类型 | 说明 |
|---|---|---|
| `binary_sensor.codex_*_proxy_reachable` | 连通性诊断 | 反代可达时为 `on`，最近一次 `/v1/models` 拉取失败时为 `off`；`extra_state_attributes.last_checked` 记录上次成功检查时间 |
| `button.codex_*_refresh_models` | 操作 | 立即触发一次 `/v1/models` 刷新，无需等待 6 小时周期 |
| `update.codex_*_model_update` | 更新 | 反代出现新模型时显示 "有更新"，点安装即切换子代理模型 |

### 默认禁用（可在实体页手动启用）

| 实体 | 类型 | 说明 |
|---|---|---|
| `sensor.codex_*_chat_model_count` | 传感器 | 反代当前可用对话模型数量 |
| `sensor.codex_*_last_model_refresh` | 传感器 | 上次 `/v1/models` 成功刷新的时间戳 |
| `select.codex_*_model_select` | 选择 | 从下拉直接切换子代理使用的模型（适合仪表盘操作） |

---

## 故障排查

| 现象 | 处理 |
|---|---|
| `invalid_auth` | API Key 错或额度耗尽，先用下面的 curl 自检 |
| `cannot_connect` | 反代 URL 或 HA 出网有问题，`curl -v <base_url>/v1/models` 测试 |
| `unknown_model` | 反代不识别该模型，换 `/v1/models` 里出现的 id |
| `invalid_url_scheme` | URL 必须以 `http://` 或 `https://` 开头 |
| `bad_toml` | 粘贴的 config.toml 格式有误，检查语法 |
| `toml_no_base_url` | TOML 解析成功但没找到 `base_url`，手动填写反代地址 |
| 对话能开始但卡住 | 查 HA 日志 `custom_components.codex_proxy`；5xx 会自动重试 |

### 反代独立 smoke test

```bash
# 测试 Responses API
curl -sS https://your-codex-pool.example.com/v1/responses \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.5","input":"ping","max_output_tokens":16,"store":false}'

# 测试 models 接口
curl -sS https://your-codex-pool.example.com/v1/models \
  -H "Authorization: Bearer sk-..."
```

两条都要返回 200。如果 `/v1/responses` 失败但 `/v1/models` 成功，多半是号池对该 token 关闭了 chat 权限。

---

## 已知限制

- **AI 绘图 / 语音**：`gpt-image-*`、`dall-e-*` 等图像模型自动从对话下拉中过滤；图像生成 / 语音 API 暂不接入。
- **工具调用**：随官方实现，反代需支持对应的 function calling schema。
- **HA Core 版本**：依赖 `homeassistant.components.openai_conversation`（HA 2024.10+ 内置）。

---

## 开发 / 贡献

```bash
# 克隆并安装测试依赖
git clone https://github.com/elvin-li/ha-codex-proxy
pip install -r requirements_test.txt

# 运行测试
pytest tests/ -v
```

CI 在 GitHub Actions 上跑 Python 3.12 + 3.13，每次 push / PR 自动触发。

欢迎提 issue 和 PR，格式参见 `.github/` 下的模板。

---

## 更新日志

完整历史见 [CHANGELOG.md](CHANGELOG.md)。

---

## 协议

[AGPL-3.0](LICENSE)。可以自用、修改、分发；如果 fork 后**重新分发或对外提供服务**，需以 AGPL 回源。
