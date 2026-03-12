# State Schema

_给AI看的：系统状态数据的精确定义_

---

## State 定义

State 是公司当前的客观状态。所有 State 必须满足两个条件：
1. **可量化**
2. **可长期跟踪**

每个模块只保留 2-3 个核心指标。

---

## Schema

```yaml
State:
  updated_at: datetime  # 最近一次更新时间
  modules:
    uniweb:
      label: "Uniweb（现金流文明）"
      objective: string
      metrics:
        merchant_count:
          type: integer
          unit: "个"
          description: "活跃商户数量"
        monthly_gmv:
          type: number
          unit: "USD"
          description: "月交易总额"
        net_profit:
          type: number
          unit: "USD"
          description: "月净利润"
      key_results:
        - id: string  # format: KR-UW-NNN
          description: string
          target: string  # 量化目标
          current: string  # 当前值
          status: enum [on_track, at_risk, blocked, done]
          updated_at: date
    
    onta:
      label: "Onta（未来网络）"
      objective: string
      metrics:
        active_nodes:
          type: integer
          unit: "个"
          description: "活跃节点数"
        daily_transactions:
          type: integer
          unit: "笔"
          description: "日交易量"
        sdk_integrations:
          type: integer
          unit: "个"
          description: "SDK集成数量"
      key_results:
        - id: string
          description: string
          target: string
          current: string
          status: enum [on_track, at_risk, blocked, done]
          updated_at: date

    license:
      label: "License（合规护城河）"
      objective: string
      metrics:
        license_count:
          type: integer
          unit: "个"
          description: "已获得牌照数"
        application_status:
          type: string
          description: "当前申请状态概要"
        compliance_progress:
          type: number
          unit: "%"
          description: "合规完成度"
      key_results:
        - id: string
          description: string
          target: string
          current: string
          status: enum [on_track, at_risk, blocked, done]
          updated_at: date

    vibecash:
      label: "Vibecash（消费者入口）"
      objective: string
      metrics:
        active_users:
          type: integer
          unit: "人"
          description: "活跃用户数"
        transaction_volume:
          type: number
          unit: "USD"
          description: "交易额"
        retention_rate:
          type: number
          unit: "%"
          description: "用户留存率"
      key_results:
        - id: string
          description: string
          target: string
          current: string
          status: enum [on_track, at_risk, blocked, done]
          updated_at: date
```

## 更新规则

- State 数据每周至少更新一次（周度 Review）
- 重大变化实时更新
- 每次更新必须更新 `updated_at` 时间戳
- 历史数据保留在 `state-history/` 目录

## 显式排除

- **不包含** Mission/Task 级别的数据（属于 Mission Schema）
- **不包含** Signal 数据（属于 Signal Schema）
- **不包含** 预测或计划数据（State 只记录事实）
- **不自动计算** 派生指标（保持数据源清晰）
