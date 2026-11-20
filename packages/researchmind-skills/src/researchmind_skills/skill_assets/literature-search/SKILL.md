---
name: literature-search
description: 按主题或作者检索、导入和筛选论文，生成供后续分析使用的文献集合。
---

按主题或作者检索、导入和筛选论文，生成供后续分析使用的文献集合。

执行流程：理解主题 → 选择 arXiv/Tavily/Semantic Scholar → 检索与去重 → 保存集合与 CSV。

边界：只要求找论文时不自动分析或写报告；已有集合满足要求时优先复用。

先检查本地环境：运行 researchmind-skills doctor --skill literature-search --target <技能根目录>。缺依赖、密钥、模型或执行权限时报告缺项，不自行安装或下载。

使用宿主已绑定的等价原生工具；没有原生工具时运行：
python "<本技能绝对目录>/scripts/run.py" run <能力编号> --input-file <UTF-8 JSON 文件> --workspace <授权工作目录> --wait --output-format json

只使用下列能力：
- papers.list
- papers.topics
- papers.filter
- papers.selection.update
- papers.selection.get
- papers.selection.clear
- papers.plan
- papers.search
- papers.search_by_author
- papers.import_uploads
- papers.info
- papers.web_search
- papers.news_search
- papers.export_csv

按需读取 [参数说明](references/parameters.md) 和 [结果说明](references/outputs.md)。参数采用能力注册表 Schema；可用 researchmind-skills capabilities describe <能力编号> --output-format json 查询，不猜测工具别名。

检查 status 和 error。accepted 只是已提交，需继续通过 jobs status/result 查询；partial 必须报告逐项失败。优先复用同 workspace/会话内的 artifact_id 和 job_id，避免重新检索或计算。重试使用相同 request_id；不同请求不可复用该 ID。读取技能不自动注册工具或赋予权限。

日志在 stderr，stdout 的一个 JSON 对象才是执行结果；输出路径和第三方凭据来自宿主或本地配置。共享 CIF 校验、CSV 导出、分段读取通过相同运行层执行，无需 MCP。
