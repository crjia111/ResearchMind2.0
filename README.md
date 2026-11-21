> **0.2 migration:** portable scientific Skills with optional AgentScope 2.0.12. Default local startup no longer starts MCP servers. See [installation, configuration and validation](docs/portable-skills.md). Python 3.11–3.12; use the updated uv.lock. The older architecture descriptions below are retained as historical context.

<div align="center">

# ResearchMind · 智能科研助手
**Your AI Partner in Materials Science**

</div>

---

**[English](#english-version) | [中文版](#中文版)**

---

## 📖 概述 (Overview)

**ResearchMind** 是一款基于**多智能体架构**的AI研究助手，专为材料科学研究领域深度定制。应用集成了四大核心功能模块，为研究人员提供从文献调研、数据查询、仿真计算到实验规划的**一站式科研解决方案**。

**ResearchMind** is an AI research assistant built on a **multi-agent architecture**, specifically tailored for the field of materials science. It integrates four core functional modules to provide researchers with a **one-stop solution** for everything from literature review and data queries to simulation and experimental planning.

---

## ✨ 核心优势 (Core Advantages)

- 🧠 **深度智能 (Deep Intelligence)**: 结合深度学习与大型语言模型，能够理解复杂的科研问题，并提供精准的分析与解答。
- 🧩 **模块化设计 (Modular Design)**: 灵活的多智能体架构，可根据研究需求调用最合适的智能体，精准满足不同研究场景。
- ⚡ **高效执行 (Efficient Execution)**: 自动规划并并行执行复杂的科研任务，从文献检索到数据分析，大幅提升科研效率。
- 🌐 **多源整合 (Multi-Source Integration)**: 无缝对接多个权威学术数据库和计算平台，打破信息孤岛，提供全面的数据支持。

---

- 🧠 **Deep Intelligence**: Combines deep learning and large language models to understand complex scientific problems, providing precise analysis and answers.
- 🧩 **Modular Design**: A flexible multi-agent architecture that invokes the most suitable agent for your research needs, perfectly fitting various scenarios.
- ⚡ **Efficient Execution**: Automatically plans and executes complex research tasks in parallel, from literature searches to data analysis, dramatically boosting your research efficiency.
- 🌐 **Multi-Source Integration**: Seamlessly connects with multiple authoritative academic databases and computing platforms, breaking down information silos to provide comprehensive data support.

---

## 🚀 系统架构 (System Architecture)

> ResearchMind2.0 adopts a runtime boundary inspired by Open Science. Agent
> execution is selected through `RESEARCHMIND_AGENT_RUNTIME`, while materials
> science capabilities remain in portable skills and MCP services. See
> [agent-runtime-migration.md](docs/agent-runtime-migration.md).

### 核心功能模块 (Core Functional Modules)

| 智能体 (Agent)                               | 功能特色 (Key Features)                                                                                                                            | 数据源 / 能力 (Data Sources / Capabilities)                                                                                             |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 📚 **文献研究 (Literature Research)**        | 智能论文搜索、多源信息整合、深度内容分析、生成综合报告。                                                                                             | **数据源**: ArXiv, Tavily, Semantic Scholar, etc.                                                                                        |
| 📊 **数据库查询 (Database Query)**           | 跨库智能检索、结构与性质查询、数据比对分析。                                                                                                       | **数据库**: Materials Project, OQMD, COD, AFLOW                                                                                          |
| 🔬 **仿真计算 (Simulation & Calculation)** | 上传结构文件进行计算、支持多种物理性质分析、提供专业的可视化。                                                                                       | **计算能力**: 热导率 (Thermal Conductivity), 能量属性 (Energy Properties), 声子谱 (Phonon Spectrum)                                        |
| 🧪 **实验规划 (Experiment Planning)**        | 综合多源信息，制定科学严谨的实验方案与验证路径。                                                                                                     | **能力**: 方案生成, 风险评估, 多智能体协同 (Plan Generation, Risk Assessment, Synergy)                                                    |

<br>

| Agent                                        | Key Features                                                                                                                                       | Data Sources / Capabilities                                                                                                              |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 📚 **Literature Research**                   | Smart paper search, multi-source information integration, deep content analysis, and comprehensive report generation.                                | **Data Sources**: ArXiv, Tavily, Semantic Scholar, etc.                                                                                  |
| 📊 **Database Query**                        | Cross-database smart retrieval, structure and property queries, and comparative data analysis.                                                     | **Databases**: Materials Project, OQMD, COD, AFLOW                                                                                       |
| 🔬 **Simulation & Calculation**              | Upload structure files for calculation, supports various physical property analyses, and provides professional visualizations.                       | **Capabilities**: Thermal Conductivity, Energy Properties, Phonon Spectrum                                                               |
| 🧪 **Experiment Planning**                   | Synthesizes multi-source info to create rigorous experimental plans and verification paths.                                                          | **Capabilities**: Plan Generation, Risk Assessment, Multi-Agent Collaboration                                                            |

---

## 📖 最佳实践指南 (Best Practices Guide)

#### 🔬 **示例1：材料热导率研究 (Example 1: Researching Thermal Conductivity)**

- **选择功能**: **仿真计算助手 (Simulation & Calculation Agent)**
- **操作流程**:
  1. 在左侧功能区选择“仿真计算助手”。
  2. 上传您的 `CIF` 晶体结构文件。
  3. 在输入框中输入指令:
    > "计算这个结构的热导率和声子谱"
- **预期输出**:
  - ✅ **精确计算**: 获得材料的热导率精确计算结果。
  - ✅ **专业图像**: 生成声子谱图像，并附带专业分析。
  - ✅ **实时可视化**: 在右侧展示区实时查看晶体结构与生成的声子谱图。

---

- **Select Agent**: **Simulation & Calculation Agent**
- **Workflow**:
  1. Choose "Simulation & Calculation Agent" from the left-hand function panel.
  2. Upload your `CIF` crystal structure file.
  3. Enter the command in the input box:
    > "Calculate the thermal conductivity and phonon spectrum for this structure"
- **Expected Output**:
  - ✅ **Precise Calculation**: Get accurate thermal conductivity results for your material.
  - ✅ **Professional Graphics**: Generate a phonon spectrum image with expert analysis.
  - ✅ **Live Visualization**: View the crystal structure and the generated phonon spectrum in real-time in the right-side display area.

---

#### ⚗️ **示例2：晶体结构查询 (Example 2: Querying Crystal Structures)**

- **选择功能**: **数据库查询助手 (Database Query Agent)**
- **操作流程**:
  1. 选择“数据库查询助手”。
  2. 输入您想查询的材料，例如:
    > "查询NaCl的晶体结构"
- **预期输出**:
  - ✅ **智能检索**: 智能体将自动轮询所有可用数据库 (Materials Project, OQMD, COD, AFLOW)。
  - ✅ **快速响应**: 返回首个成功命中的查询结果，并展示其详细信息和3D结构。

---

- **Select Agent**: **Database Query Agent**
- **Workflow**:
  1. Choose "Database Query Agent".
  2. Enter the material you want to query, for example:
    > "Find the crystal structure of NaCl"
- **Expected Output**:
  - ✅ **Smart Retrieval**: The agent will automatically query all available databases (Materials Project, OQMD, COD, AFLOW).
  - ✅ **Fast Response**: It will return the first successful match, displaying its detailed information and 3D structure.

---

#### 📜 **示例3：学术论文调研 (Example 3: Conducting a Literature Review)**

- **选择功能**: **文献研究助手 (Literature Research Agent)**
- **操作流程**:
  1. 选择“文献研究助手”。
  2. 输入您的研究主题，例如:
    > "生成一份关于大语言模型在材料科学中应用的详细报告"
- **预期输出**:
  - ✅ **并行检索**: 同时从 ArXiv, Tavily 等多个来源检索相关文献。
  - ✅ **深度分析**: 对每篇关键论文进行深度剖析，提取核心观点和方法。
  - ✅ **综合报告**: 生成一份结构清晰、内容详实的综合报告。
  - ✅ **数据文件**: 提供一个包含所有引用文献、摘要和链接的 `CSV` 文件，方便您进一步分析。

---

- **Select Agent**: **Literature Research Agent**
- **Workflow**:
  1. Choose "Literature Research Agent".
  2. Enter your research topic, for example:
    > "Generate a detailed report on the application of large language models in materials science"
- **Expected Output**:
  - ✅ **Parallel Search**: Simultaneously retrieves literature from multiple sources like ArXiv and Tavily.
  - ✅ **In-depth Analysis**: Conducts a deep analysis of each key paper, extracting core ideas and methodologies.
  - ✅ **Comprehensive Report**: Generates a well-structured and detailed summary report.
  - ✅ **Data File**: Provides a `CSV` file containing all cited literature, abstracts, and links for your further analysis.

---

#### 🧪 **示例4：实验方案规划 (Example 4: Experimental Plan Planning)**

- **选择功能**: **实验规划智能体 (Experiment Plan Agent)**
- **操作流程**:
  1. 选择“实验规划智能体”。
  2. 输入您的研究目标，例如:
    > "设计一个提高石墨烯/环氧树脂复合材料热导率的实验方案"
- **预期输出**:
  1. ✅ **综合调研**: 自动调用文献和数据库智能体获取背景信息。
  2. ✅ **方案生成**: 输出包含材料制备、表征测试、数据记录的完整实验流程。
  3. ✅ **风险评估**: 提示潜在的实验风险并给出应对策略。

---

- **Select Agent**: **Experiment Plan Agent**
- **Workflow**:
  1. Choose "Experiment Plan Agent".
  2. Enter your research goal, for example:
    > "Design an experimental plan to improve the thermal conductivity of graphene/epoxy composites"
- **Expected Output**:
  1. ✅ **Comprehensive Survey**: Automatically calls literature and database agents for background info.
  2. ✅ **Plan Generation**: Outputs a complete experimental flow covering preparation, characterization, and data recording.
  3. ✅ **Risk Assessment**: Highlights potential risks and suggests mitigation strategies.

---

## 🏠 本地运行 (Local Operation)

项目采用本地单用户模式，打开网页即可使用，无需平台账号、Cookie、AccessKey 或登录认证。平台扣费、光子配额和邀请奖励功能已移除；模型与科研数据库的第三方 API 仍需按所用功能配置，费用由相应服务商决定。

ResearchMind runs locally without a platform account or login. Configure your model and research API providers as needed; their own usage fees still apply.

---

## 🎓 学术引用 (Academic Citation)

如果您在研究中使用了本应用的热导率计算功能，请引用以下论文。

If you use the thermal conductivity calculation feature of this application in your research, please cite the following paper.

**BibTeX 格式:**
```bibtex
@article{Liu2025PINK,
  author  = {Liu, Yujie and Wang, Xiaoying and Gao, Zhibin},
  title   = {{PINK: physical-informed machine learning for lattice thermal conductivity}},
  journal = {Journal of Materials Informatics},
  year    = {2025},
  volume  = {5},
  pages   = {12},
  doi     = {10.20517/jmi.2024.86}
}
```

**BibTeX 格式:**
```bibtex
@article{Liu2025PINK,
  author  = {Liu, Yujie and Wang, Xiaoying and Gao, Zhibin},
  title   = {{PINK: physical-informed machine learning for lattice thermal conductivity}},
  journal = {Journal of Materials Informatics},
  year    = {2025},
  volume  = {5},
  pages   = {12},
  doi     = {10.20517/jmi.2024.86}
}
```

---
---

# <a name="developer-guide"></a> 👨‍💻 开发者指南 (Developer Guide)

## 🚀 本地启动 (Local Quick Start)

运行环境：Python 3.10–3.12（推荐 3.11）、Node.js 18+、uv。仿真依赖较大，首次安装需要下载 PyTorch 和材料计算库。当前 PyTorch 依赖采用 CUDA 12.4 构建，推荐使用 Linux / WSL2；macOS 不支持当前 CUDA 依赖组合。

### Linux / WSL2

```bash
cd /home/jcr/projects/ResearchMind-master
# 首次配置；已有 .env 时请编辑现有文件。
cp -n .env.example .env
uv sync --python 3.11
bash start_linux.sh
```

本项目位于 WSL Ubuntu 中，请在 Ubuntu 终端运行以上命令。也可以从 Windows PowerShell 启动：

```powershell
wsl -d Ubuntu -- bash -lc 'cd /home/jcr/projects/ResearchMind-master && bash start_linux.sh'
```

### Windows 原生目录

在 Windows 本地目录中安装 Python、Node.js 和 uv 后运行：

```powershell
.\start_windows.ps1
```

也可双击 `start_windows.bat`。WSL 中的 Linux 虚拟环境与 Windows 虚拟环境不能共用。

### 配置模型及科研 API

在项目根目录 `.env` 中配置你的 OpenAI 兼容服务：

```dotenv
MODEL_USE=openai/your-model-name
OPENAI_API_KEY=your-provider-api-key
OPENAI_BASE_URL=https://your-provider.example/v1
```

`MODEL_USE` 使用 LiteLLM 的模型标识；如果使用其他服务商，请按其要求调整模型前缀。`TAVILY_API_KEY`、`MP_API_KEY` 等只在对应检索功能中需要。未配置模型 API 时可以打开界面、管理本地会话，发送 AI 请求前需完成配置。

### 本地访问与数据

| 服务 | 默认地址 |
| --- | --- |
| 前端 | http://localhost:50010 |
| 后端 API | http://127.0.0.1:50002/api |
| API 文档 | http://127.0.0.1:50002/docs |
| WebSocket | ws://127.0.0.1:50003/ws |
| 文献 MCP | http://127.0.0.1:50004/sse |
| 仿真 MCP | http://127.0.0.1:50005/sse |
| 数据库 MCP | http://127.0.0.1:50006/sse |

前端通过 Vite 将 `/api` 和 `/ws` 转发到本地后端，无需 Nginx。保持 `VITE_API_URL=/api`、`VITE_WS_URL=/ws`，并清空旧的 `VITE_API_PORT` / `VITE_WS_PORT` 代理端口配置。服务默认绑定 `127.0.0.1`。

会话、上传文件与计算结果存储于 `.env` 指定的本地路径，默认位于项目 `data/`。Redis 是可选缓存，不可用时自动使用文件存储。Token 统计接口为只读的 `/api/usage/*`；没有认证、扣费或充值接口。旧数据库表和历史文件不会被自动删除。

### 停止、检查与日志

在启动终端按 `Ctrl+C` 停止所有托管服务；Linux / WSL 也可运行 `bash stop_linux.sh`。如果仍在使用旧启动器，请先在原启动终端停止旧服务，再运行新启动器。

```bash
bash start_linux.sh --check
# 可选：使用另一份本地配置（例如不同的端口和数据目录）
bash start_linux.sh --env-file /path/to/local.env
```

端口被占用时启动器会退出并提示修改配置。日志位于 `data/logs/`，包括 `backend.log`、`database.log`、`paper_search.log`、`simulation.log`、`frontend.log`。子服务退出时启动器会报告错误并停止其余托管服务。

### 开发验证

```bash
.venv/bin/python -m pytest tests/test_local_runtime.py -o addopts=''
cd ui && npm run build
```
