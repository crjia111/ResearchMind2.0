---
name: phonon-analysis
description: 使用配置好的 MatterSim 与声子依赖计算晶体声子谱及相关工件。
---

使用配置好的 MatterSim 与声子依赖计算晶体声子谱及相关工件。

执行流程：校验结构 → 确认前置弛豫策略 → 检查模型 → 声子计算 → 保存图像和数据。

边界：relax_first 默认 false；尊重用户不弛豫的请求；不自动计算热导率。

先检查本地环境：运行 researchmind-skills doctor --skill phonon-analysis --target <技能根目录>。缺依赖、密钥、模型或执行权限时报告缺项，不自行安装或下载。

使用宿主已绑定的等价原生工具；没有原生工具时运行：
python "<本技能绝对目录>/scripts/run.py" run <能力编号> --input-file <UTF-8 JSON 文件> --workspace <授权工作目录> --wait --output-format json

只使用下列能力：
- simulation.validate_cif
- simulation.relax
- simulation.phonon

按需读取 [参数说明](references/parameters.md) 和 [结果说明](references/outputs.md)。参数采用能力注册表 Schema；可用 researchmind-skills capabilities describe <能力编号> --output-format json 查询，不猜测工具别名。

检查 status 和 error。accepted 只是已提交，需继续通过 jobs status/result 查询；partial 必须报告逐项失败。优先复用同 workspace/会话内的 artifact_id 和 job_id，避免重新检索或计算。重试使用相同 request_id；不同请求不可复用该 ID。读取技能不自动注册工具或赋予权限。

日志在 stderr，stdout 的一个 JSON 对象才是执行结果；输出路径和第三方凭据来自宿主或本地配置。共享 CIF 校验、CSV 导出、分段读取通过相同运行层执行，无需 MCP。
