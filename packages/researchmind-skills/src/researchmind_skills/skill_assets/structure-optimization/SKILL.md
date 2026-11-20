---
name: structure-optimization
description: 对输入晶体进行单点能量评估，或在用户要求时进行结构弛豫。
---

对输入晶体进行单点能量评估，或在用户要求时进行结构弛豫。

执行流程：校验 CIF → 判断单点/弛豫意图 → 检查 MatterSim 权重 → 计算 → 保存真实结果及新结构。

边界：只算能量时输入结构保持不变，不隐式调用弛豫；未配置模型时明确失败。

先检查本地环境：运行 researchmind-skills doctor --skill structure-optimization --target <技能根目录>。缺依赖、密钥、模型或执行权限时报告缺项，不自行安装或下载。

使用宿主已绑定的等价原生工具；没有原生工具时运行：
python "<本技能绝对目录>/scripts/run.py" run <能力编号> --input-file <UTF-8 JSON 文件> --workspace <授权工作目录> --wait --output-format json

只使用下列能力：
- simulation.validate_cif
- simulation.energy
- simulation.relax

按需读取 [参数说明](references/parameters.md) 和 [结果说明](references/outputs.md)。参数采用能力注册表 Schema；可用 researchmind-skills capabilities describe <能力编号> --output-format json 查询，不猜测工具别名。

检查 status 和 error。accepted 只是已提交，需继续通过 jobs status/result 查询；partial 必须报告逐项失败。优先复用同 workspace/会话内的 artifact_id 和 job_id，避免重新检索或计算。重试使用相同 request_id；不同请求不可复用该 ID。读取技能不自动注册工具或赋予权限。

日志在 stderr，stdout 的一个 JSON 对象才是执行结果；输出路径和第三方凭据来自宿主或本地配置。共享 CIF 校验、CSV 导出、分段读取通过相同运行层执行，无需 MCP。
