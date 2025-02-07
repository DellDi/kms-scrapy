# Changelog

## [Unreleased]

### 重构
- 重构树结构提取相关代码 @2025-02-07
  - 创建 TreeExtractor 类专门处理导航树解析逻辑
  - 从 ConfluenceSpider 类中分离树结构处理代码
  - 改善代码组织结构，提高可维护性