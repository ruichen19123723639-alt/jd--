# JD Agent

一个基于 Python、FastAPI 和大模型 API 的职位分析助手。

## 当前功能

- 分析职位描述
- 输出结构化岗位信息
- 使用 Pydantic 校验模型输出
- 使用 Function Calling 调用技能匹配工具
- 计算候选人与岗位的技能匹配度
- 使用候选人资料进行关键词检索
- 处理模型超时、连接错误和自动重试

## 技术栈

- Python
- FastAPI
- Pydantic
- OpenAI 兼容 API
- Function Calling
- RAG 基础流程

## Docker 运行

构建镜像：

```powershell
docker build -t jd-agent .