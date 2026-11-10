# godot-dev

[English](README.md) | 简体中文

用于在 Godot 4.7 中做游戏的 Claude Code 插件。

它提供三样东西。一个 skill：在 Godot 项目里工作时 Claude 会加载它，它把每个任务分派到一份简短的参考文件，而不是把整本规则塞进上下文。几个脚本：用你本机实际安装的 Godot 来检查 Claude 的工作。以及 [godot-ai](https://github.com/hi-godot/godot-ai) MCP 服务器的接入：第一次在某个项目里打开 Claude 会话时，自动把它的编辑器插件装进项目。

写 Godot 代码的智能体总会重复同样的错误：Godot 3 语法、没有类型的 GDScript、能加载但一实例化就坏的场景，以及没跑过就说"能用了"。这个插件做的事，大部分是让这些错误在到达你之前就暴露出来。

## 环境要求

- 支持插件的 Claude Code
- Godot 4.7 或更新版本，通过 PATH 上的 `godot`、`GODOT` 环境变量，或 macOS 上的 `/Applications/Godot*.app` 找到
- Python 3.9 或更新版本，或 [uv](https://docs.astral.sh/uv/)（godot-ai 服务器本身需要 uv）
- git，用于变更集检查

## 安装

把本仓库添加为插件市场，再从中安装插件：

```bash
claude plugin marketplace add ItsYUGAMES/godot-dev
```

```bash
claude plugin install godot-dev@godot-dev
```

在 Claude Code 会话里，同样的两步是 `/plugin marketplace add ItsYUGAMES/godot-dev` 和 `/plugin install godot-dev@godot-dev`。之后开一个新会话，skill、hook 和 MCP 服务器才会加载。

不安装、只试用一次：克隆仓库，让 Claude Code 在一个会话里指向它：

```bash
git clone https://github.com/ItsYUGAMES/godot-dev.git
```

```bash
claude --plugin-dir ./godot-dev
```

用 `claude plugin update godot-dev@godot-dev` 更新，用 `claude plugin uninstall godot-dev@godot-dev` 卸载。

### Codex

同一个仓库也可以作为 Codex 的插件市场：

```bash
codex plugin marketplace add ItsYUGAMES/godot-dev
```

```bash
codex plugin add godot-dev@godot-dev
```

Codex 只在你信任插件 hook 之后才运行它们，所以要在新会话里打开 `/hooks`，信任 godot-dev 的 SessionStart hook；在此之前 skill 和 MCP 服务器可用，但不会自动安装任何东西。Codex 不会展开 MCP 命令里的 `${CLAUDE_PLUGIN_ROOT}`，所以 `.codex-mcp.json` 在 `$CODEX_HOME/plugins/cache`（默认 `~/.codex`）下查找启动脚本。重复检查读取的是 `$CODEX_HOME/config.toml` 和项目 `.codex/config.toml` 里的 `[mcp_servers.godot-ai]`，而不是 Claude 的配置。

## 在 Godot 项目里会发生什么

会话开始时，hook 在工作目录及其上级目录中查找 `project.godot`。不在 Godot 项目里时，它什么也不输出，内置 MCP 服务器也只返回零个工具，所以插件在其他仓库里没有任何开销。

在目标为 Godot 4.7 或更新版本、且还没有 `addons/godot_ai/` 的项目里，hook 会下载 godot-ai v4.3.0 发布包。在动你的项目之前，它先用本仓库里固定的 SHA-256 值校验三个发布文件，再运行 godot-ai 自带的校验器检查 RSA 签名和完整文件清单。插件先解压到暂存目录，再一步移动到位。如果没有正在运行的 Godot 编辑器，hook 还会在 `project.godot` 里启用该插件；如果编辑器开着，它不碰这个文件，而是提示你去项目设置里启用，因为编辑器反正会覆盖这次修改。

hook 从不覆盖或降级已有的插件。之后它最多输出三行：引擎版本、插件的处理结果、MCP 状态。

MCP 服务器通过 uvx 运行 `godot-ai attach`，版本固定为 `addons/godot_ai/plugin.cfg` 里的那个。这很重要，因为编辑器会拒绝与插件版本不同的后端。端口和排除的工具域从你的 Godot 编辑器设置里读取，遥测默认关闭，除非你主动开启。如果你已经自己注册过 godot-ai（通过面板的 Configure 按钮、`claude mcp add` 或项目里的 `.mcp.json`），内置服务器保持不启动，免得出现 47 个重复工具。如果那个已有条目固定的版本与插件不同，它会提醒你。

在 Godot 编辑器里打开项目后，godot-ai 工具就能读取和修改正在运行的编辑器。

## 使用

你不需要直接调用 skill。像平常一样提 Godot 需求（"给玩家加土狼时间"、"这个场景为什么一实例化就崩"、"做一个存档系统"），Claude 会加载 `godot` skill，读取任务需要的参考文件，并在汇报前跑完检查。

检查脚本在 `skills/godot/scripts/gd.py`，你也可以在克隆的仓库里自己运行：

```bash
python3 skills/godot/scripts/gd.py check --project /path/to/game --smoke
```

`check` 运行 `--import`，加载每个脚本，实例化每个场景；加上 `--smoke` 时，还会无头运行主场景几百帧。它不用 `--check-only`，因为后者对引用了 autoload 的代码会误报错误。

```bash
python3 skills/godot/scripts/gd.py api CharacterBody2D.move_and_slide Vector3.MODEL_FRONT
```

`api` 在你安装的引擎里查找名称，名称不存在时给出最接近的真实名称。比如 `KinematicBody2D` 会返回不存在，并建议 `StaticBody2D` 和 `AnimatableBody2D`。

```bash
python3 skills/godot/scripts/gd.py hygiene --project /path/to/game
```

`hygiene` 读取你的 git diff 和未跟踪文件，标出调试后常被遗留的东西：`print()` 调用（它们会进发布版本，只有 `assert()` 会被剥离）、没写原因的 `@warning_ignore`、被注释掉的代码、没有负责人的 TODO、有副作用的 assert、丢了断言或被删掉的测试、探测脚本，以及孤立的 `.uid` 文件。

```bash
python3 skills/godot/scripts/gd.py release --project /path/to/game --preset "macOS"
```

`release` 用你的某个导出预设导出 pack，如果测试目录或测试插件混进了 pack 就判失败，然后无头启动这个 pack 捕捉运行时错误。

四个命令最后都输出一行 `RESULT: PASS`、`RESULT: FAIL` 或 `RESULT: NOT ASSESSED`。只有 PASS 才算数，因为 Godot 在脚本出错后经常仍以退出码 0 结束。

## 上下文开销

用 `claude plugin details` 测得：

| 时机 | 开销 |
|---|---|
| 每个会话 | 约 76 token（skill 描述） |
| 调用 skill 时 | 路由约 1.6k token，加上任务需要的参考文件（每份 22 到 94 行） |
| 在 Godot 项目里开始会话 | hook 输出约 120 token |
| godot-ai 工具 | 延迟加载；只有 Claude 搜索时才加载其 schema |

## 设置

在启动 Claude Code 前设置这些环境变量：

| 变量 | 作用 |
|---|---|
| `GODOT_DEV_AUTO_INSTALL=0` | 从不安装或启用插件 |
| `GODOT_DEV_MCP=0` | 保持内置 MCP 服务器不启动 |
| `GODOT_DEV_MCP_FORCE=1` | 即使你有自己的 godot-ai 条目也运行内置服务器 |
| `GODOT_DEV_TELEMETRY=1` | 允许 godot-ai 遥测 |
| `GODOT_DEV_MCP_PORT`、`GODOT_DEV_MCP_WS_PORT`、`GODOT_DEV_EXCLUDE_DOMAINS` | 覆盖从编辑器设置读取的值 |

在项目里运行 `python3 scripts/godot_dev.py status`，会输出插件检测到的情况。

## 仓库内容

```
.claude-plugin/        插件和市场清单
.codex-plugin/         Codex 清单（配合 .codex-mcp.json 和 hooks/codex-hooks.json）
skills/godot/          SKILL.md（路由）、21 份参考文件、gd.py 及其 GDScript 辅助脚本
hooks/, scripts/       SessionStart hook、插件安装器、MCP 启动脚本
scripts/vendor/        godot-ai 的发布校验器（MIT，按哈希固定）
docs/STANDARDS.md      完整规则集，附来源和背后的引擎检查
tests/                 安装器、启动脚本和 gd.py 的测试，以及一个端到端 MCP 测试
evals/                 `claude plugin eval` 的用例
```

参考文件涵盖：工作流、GDScript、交付前清理、架构与模式、项目设置、物理、2D、3D、动画、UI、输入、存档与线程、音频、导航、多人、着色器、性能、手改 `.tscn` 文件、测试与导出、godot-ai，以及编辑器插件。

## 规则从哪来

规则提炼自 Godot 4.7 文档、官方示例项目、《游戏编程模式》、对 star 最多的 Godot 智能体 skill 和 MCP 服务器的调研，以及已发表的工作室在工作流、测试和代码清理方面的实践。来源有分歧时，由 Godot 本身裁决：有争议的默认值或 API，就运行 4.7.stable 实际检查。举个例子，文档说 `move_and_slide` 默认最多碰撞五次；引擎里 `max_slides` 是 4。`docs/STANDARDS.md` 列出了每处冲突及其裁决方式。

这个 skill 也做过对照测试：在一个强模型上，让带和不带它的智能体做同样的任务。不带它时，模型已经能避开明显的 Godot 3 错误。带上它之后，代码更常通过严格的类型检查，运行过程会查引擎 API、先写测试再修 bug、证明回退修复后测试会失败，并留下干净的仓库。代价是大约多用 25% 的 token。小模型还没测过；`evals/` 里的评测集就是为此准备的。

## 测试

```bash
bash tests/gd_tests.sh
```

```bash
bash tests/run_tests.sh /path/to/godot-ai-v4.3.0-release-files
```

```bash
bash tests/integration_godot_ai.sh /path/to/godot-ai-v4.3.0-release-files
```

第二和第三个脚本需要一个存放三个 godot-ai v4.3.0 发布文件（`godot-ai-v4-plugin.zip`、`.manifest.json`、`.manifest.sig`）的目录，这样不必每次运行都联网。端到端测试会用隔离的 home 目录和单独的端口启动一个无头 Godot 编辑器，不会干扰你已经在运行的 godot-ai 后端。

```bash
claude plugin eval . --allow-tools Bash Write Edit --no-publish
```

## 故障排查

如果第一次运行时没有 godot-ai 工具，多半是 uv 还在构建服务器环境。hook 会在后台启动这次构建；一分钟后在 `/mcp` 里重新连接 godot-ai。

如果刚打开编辑器就看到 `PORT_OCCUPIED` 或 HTTP 401，很可能是 Claude 和编辑器同时启动了 godot-ai。在 `/mcp` 里重新连接即可。

如果插件装上了但没有启用，说明安装时编辑器是开着的。到"项目 > 项目设置 > 插件 > Godot AI"里启用。

## 更新固定的 godot-ai 版本

修改 `scripts/godot_dev.py` 里的 `PIN_VERSION`、`PIN_TAG`、`PIN_COMMIT` 和三个 `PIN_ASSETS` 摘要，摘要要自己对下载的发布文件计算，不要照抄发布页。从同一个 tag 复制 `release_verify.py` 到 `scripts/vendor/`，更新 `VERIFIER_SHA256`，然后运行测试脚本。

## 许可证

MIT，见 `LICENSE`。`scripts/vendor/release_verify.py` 来自 [godot-ai](https://github.com/hi-godot/godot-ai)，在 `scripts/vendor/LICENSE-godot-ai` 中保留其自己的 MIT 许可证。
