# 📚 摔倒检测系统 - 完整项目文档

## 🎯 项目概述

**GuardianFall** 是一个基于点云技术的实时摔倒检测系统，使用 Azure Kinect DK 相机和 AI 算法，能够在室内环境中准确检测人员摔倒事件并即时报警。

### 核心特性

- ✅ **隐私保护**: 仅使用点云/深度数据，无可见光图像
- ✅ **实时检测**: < 100ms 延迟，7x24 小时不间断监测
- ✅ **高准确率**: > 95% 检测准确率，< 5% 误报率
- ✅ **易于部署**: 一键 Docker 部署，支持云端和本地
- ✅ **可视化界面**: 实时 3D 点云显示，直观易懂

---

## 📁 文档导航

### 📘 入门指南

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [README.md](../README.md) | 项目介绍和快速开始 | 所有人 |
| [docs/QUICK_START.md](./QUICK_START.md) | 5 分钟快速上手指南 | 新用户 |
| [docs/FEATURES.md](./FEATURES.md) | 功能特性详解 | 评估人员 |

### 🔧 技术文档

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [technical-proposal.md](../technical-proposal.md) | 完整技术方案 | 技术人员 |
| [docs/ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构设计 | 架构师 |
| [docs/API_REFERENCE.md](./API_REFERENCE.md) | API 接口文档 | 开发者 |
| [docs/DATA_FORMAT.md](./DATA_FORMAT.md) | 数据格式说明 | 开发者 |

### 🚀 部署运维

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [docs/DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | 完整部署指南 | 运维人员 |
| [docs/DEPLOYMENT.md](./DEPLOYMENT.md) | 快速部署手册 | 运维人员 |
| [docs/MONITORING.md](./MONITORING.md) | 监控与维护 | 运维人员 |
| [docs/TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 故障排查 | 运维人员 |

### 📱 使用手册

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [docs/USER_GUIDE.md](./USER_GUIDE.md) | 用户操作指南 | 最终用户 |
| [docs/WEB_UI_GUIDE.md](./WEB_UI_GUIDE.md) | Web 界面使用 | 最终用户 |
| [docs/CONFIGURATION.md](./CONFIGURATION.md) | 参数配置说明 | 管理员 |

### 📊 项目管理

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [week-by-week-plan.md](../week-by-week-plan.md) | 12 周执行计划 | 项目经理 |
| [WEEK1_TODO.md](../WEEK1_TODO.md) | Week 1 任务清单 | 执行人员 |
| [docs/CHANGELOG.md](./CHANGELOG.md) | 版本更新日志 | 所有人 |
| [docs/ROADMAP.md](./ROADMAP.md) | 未来规划 | 所有人 |

### 💰 成本分析

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [ai-driven-cost-analysis.md](../ai-driven-cost-analysis.md) | AI 驱动成本分析 | 决策者 |
| [docs/ROI_ANALYSIS.md](./ROI_ANALYSIS.md) | 投资回报分析 | 决策者 |

### 🤖 AI 相关

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [ai-prompts-collection.md](../ai-prompts-collection.md) | AI Prompt 集合 | 开发者 |
| [docs/AI_MODEL_TRAINING.md](./AI_MODEL_TRAINING.md) | AI 模型训练指南 | AI 工程师 |
| [docs/DATA_COLLECTION.md](./DATA_COLLECTION.md) | 数据采集规范 | 数据工程师 |

---

## 🎯 快速链接

### 代码仓库
- **GitHub**: https://github.com/nanfeng2021/fall-detection-system
- **主要分支**: `main` (稳定版), `develop` (开发版)

### 重要文件
- [源代码](../src/) - 核心算法和模块
- [Demo 脚本](../demos/) - 示例和测试
- [配置文件](../configs/) - 系统配置
- [Docker 配置](../Dockerfile) - 容器化部署

### 在线资源
- **问题反馈**: https://github.com/nanfeng2021/fall-detection-system/issues
- **讨论区**: https://github.com/nanfeng2021/fall-detection-system/discussions
- **Wiki**: https://github.com/nanfeng2021/fall-detection-system/wiki

---

## 📖 阅读建议

### 第一次接触项目？

1. 从 [README.md](../README.md) 开始，了解项目概况
2. 阅读 [docs/QUICK_START.md](./QUICK_START.md)，5 分钟快速上手
3. 查看 [docs/FEATURES.md](./FEATURES.md)，了解功能特性
4. 参考 [docs/USER_GUIDE.md](./USER_GUIDE.md)，学习使用方法

### 准备部署项目？

1. 阅读 [docs/DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)，选择部署方式
2. 参考 [docs/CONFIGURATION.md](./CONFIGURATION.md)，配置系统参数
3. 查看 [docs/MONITORING.md](./MONITORING.md)，设置监控告警
4. 保存 [docs/TROUBLESHOOTING.md](./TROUBLESHOOTING.md)，以备不时之需

### 想要贡献代码？

1. 阅读 [technical-proposal.md](../technical-proposal.md)，理解技术方案
2. 查看 [docs/ARCHITECTURE.md](./ARCHITECTURE.md)，了解系统设计
3. 参考 [docs/API_REFERENCE.md](./API_REFERENCE.md)，熟悉接口规范
4. 查看 GitHub Issues，找到可以贡献的内容

---

## 🗂️ 文档结构

```
docs/
├── README.md                 # 本文件（文档导航）
├── QUICK_START.md           # 快速开始
├── FEATURES.md              # 功能特性
├── ARCHITECTURE.md          # 系统架构
├── API_REFERENCE.md         # API 文档
├── DATA_FORMAT.md           # 数据格式
├── DEPLOYMENT_GUIDE.md      # 部署指南（详细）
├── DEPLOYMENT.md            # 部署指南（快速）
├── MONITORING.md            # 监控维护
├── TROUBLESHOOTING.md       # 故障排查
├── USER_GUIDE.md            # 用户指南
├── WEB_UI_GUIDE.md          # Web UI 指南
├── CONFIGURATION.md         # 配置说明
├── CHANGELOG.md             # 更新日志
├── ROADMAP.md               # 未来规划
├── ROI_ANALYSIS.md          # 投资回报
├── AI_MODEL_TRAINING.md     # AI 训练指南
└── DATA_COLLECTION.md       # 数据采集
```

---

## 📝 文档维护

### 文档规范

- 使用 Markdown 格式
- 中文为主，关键术语保留英文
- 包含代码示例和截图
- 定期审查和更新

### 贡献指南

欢迎提交文档改进！

1. Fork 项目
2. 创建文档分支 (`git checkout -b feature/docs-improvement`)
3. 提交更改 (`git commit -m 'docs: improve XXX documentation'`)
4. 推送到分支 (`git push origin feature/docs-improvement`)
5. 创建 Pull Request

---

## 🆘 获取帮助

遇到问题或有问题？

1. **查看文档**: 先在本页面查找相关文档
2. **搜索 Issues**: https://github.com/nanfeng2021/fall-detection-system/issues
3. **创建 Issue**: 如果没找到答案，创建新 Issue
4. **参与讨论**: https://github.com/nanfeng2021/fall-detection-system/discussions

---

## 📞 联系方式

- **项目主页**: https://github.com/nanfeng2021/fall-detection-system
- **作者**: 南风
- **邮箱**: nanfeng@example.com
- **许可证**: MIT License

---

*最后更新：2026-04-12*  
*版本：v1.0*  
*状态：生产就绪 ✅*
