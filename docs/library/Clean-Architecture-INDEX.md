# Clean Architecture — Robert C. Martin (2018)
# 目录索引 + FounderOS 关联标注

## PART I — Introduction
- Ch 1: What Is Design and Architecture?
- Ch 2: A Tale of Two Values (Behavior vs Architecture)

## PART II — Programming Paradigms
- Ch 3: Paradigm Overview (Structured / OO / Functional)
- Ch 4: Structured Programming
- Ch 5: Object-Oriented Programming (Encapsulation / Inheritance / Polymorphism)
- Ch 6: Functional Programming (Immutability / Event Sourcing) ← **Event Sourcing 跟 FPMS 的 events.jsonl 相关**

## PART III — Design Principles (SOLID)
- Ch 7: SRP — Single Responsibility Principle ← **Module Spec "显式排除"的理论基础**
- Ch 8: OCP — Open-Closed Principle ← **Plugin 架构，Office 扩展**
- Ch 9: LSP — Liskov Substitution Principle
- Ch 10: ISP — Interface Segregation Principle ← **接口契约设计**
- Ch 11: DIP — Dependency Inversion Principle ← **依赖方向：内层不依赖外层**

## PART IV — Component Principles ← **⭐ 支付系统模块拆分必读**
- Ch 12: Components (History / Relocatability)
- Ch 13: Component Cohesion ← **怎么决定哪些代码放一起**
  - Reuse/Release Equivalence Principle
  - Common Closure Principle
  - Common Reuse Principle
  - Tension Diagram
- Ch 14: Component Coupling ← **⭐ 怎么管理模块间依赖**
  - Acyclic Dependencies Principle ← **FPMS DAG 无环约束的理论来源**
  - Stable Dependencies Principle
  - Stable Abstractions Principle

## PART V — Architecture ← **⭐ 核心，支付系统架构设计必读**
- Ch 15: What Is Architecture? (Development / Deployment / Operation / Maintenance)
- Ch 16: Independence ← **⭐ 解耦策略：层/用例/模式**
  - Decoupling Layers
  - Decoupling Use Cases
  - Independent Develop-ability / Deployability
- Ch 17: Boundaries: Drawing Lines ← **⭐ 支付系统边界怎么画**
  - Plugin Architecture
- Ch 18: Boundary Anatomy (Monolith / Components / Services)
- Ch 19: Policy and Level
- Ch 20: Business Rules ← **⭐ Entities vs Use Cases，支付核心实体定义**
  - Entities
  - Use Cases
  - Request and Response Models
- Ch 21: Screaming Architecture (架构应该"喊出"业务意图)
- Ch 22: The Clean Architecture ← **⭐ 经典四层环形图，依赖规则**
  - The Dependency Rule
- Ch 23: Presenters and Humble Objects ← **测试边界设计**
- Ch 24: Partial Boundaries (什么时候可以简化边界)
- Ch 25: Layers and Boundaries
- Ch 26: The Main Component
- Ch 27: Services: Great and Small ← **微服务不等于好架构**
- Ch 28: The Test Boundary ← **铁律测试的设计原则**
  - Tests as System Components
  - Design for Testability
  - The Testing API
- Ch 29: Clean Embedded Architecture

## PART VI — Details
- Ch 30: The Database Is a Detail ← **SQLite 是实现细节，不是架构**
- Ch 31: The Web Is a Detail
- Ch 32: Frameworks Are Details ← **不要被框架绑架**
- Ch 33: Case Study: Video Sales ← **完整案例，可参考拆解方法**
- Ch 34: The Missing Chapter ← **Package by Component 实战**
  - Package by Layer / Feature / Ports and Adapters / Component

## PART VII — Appendix
- Appendix A: Architecture Archaeology

---

## 查阅优先级（做支付系统时）

1. Ch 22 Clean Architecture — 依赖规则
2. Ch 17 Boundaries — 边界划分
3. Ch 20 Business Rules — 实体 vs 用例
4. Ch 14 Component Coupling — 模块依赖管理
5. Ch 16 Independence — 解耦策略
6. Ch 28 Test Boundary — 测试架构
7. Ch 13 Component Cohesion — 模块内聚
