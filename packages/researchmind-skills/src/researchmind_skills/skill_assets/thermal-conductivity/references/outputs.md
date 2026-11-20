# 返回契约

schema_version=1.0。status 为 completed、partial、failed 或 accepted；accepted 附 job_id，不能作为最终成功。data 是对应能力结果；artifacts 提供 artifact_id、类型和哈希；error 包含 code/message/retryable。usage 记录模型调用和真实计算数量。

CLI 退出码：0 完成/接收，2 参数错，3 部分完成，4 业务/依赖失败，5 内部错误，130 取消。全文过长应分段读取；偏移按 Unicode 字符，total_length 与 next_start 使用同一单位。
