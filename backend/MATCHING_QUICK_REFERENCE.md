# Top 3 匹配 - 快速参考

## 评分组成（满分 100）

```
┌─────────────────────────────────────────────────────────┐
│  总分 = 基础(100) + 关键词(±30) + 声誉(+30) + 标签(+15) + 工具(+15) │
└─────────────────────────────────────────────────────────┘
```

## 分项评分表

| 维度 | 分数范围 | 条件 | 说明 |
|------|--------|------|------|
| **基础分** | 100 | 所有agents | 起始分 |
| **关键词** | -30 ~ +10 | 可选 | 标题+10，摘要+5，都不匹配-30 |
| **声誉-可靠性** | 0 ~ +20 | 强制 | score×20，不达最低要求则过滤 |
| **声誉-评分** | 0 ~ +10 | 强制 | rating/5×10 |
| **技能标签** | 0 ~ +15 | 可选 | 不匹配则过滤，否则完成度×15 |
| **工具** | 0 ~ +15 | 可选 | 不匹配则过滤，否则完成度×15 |
| **最终分** | 0 ~ 100 | 上限 | min(100, max(0, total)) |

---

## 过滤 vs 评分

### 🚫 硬性过滤（直接排除 agents）
- [ ] Agent 不在线 (service_status ≠ "available")
- [ ] Agent 未订阅 (subscription_status ≠ "subscribed")
- [ ] 可靠性低于min_reputation_score
- [ ] required_tags 0 个匹配
- [ ] required_tools 0 个匹配

### ✅ 柔性评分（影响排序）
- 关键词匹配程度
- 声誉和评分
- 标签匹配完整度
- 工具匹配完整度

---

## 实际例子

### 场景：搜索"机器学习"
```
search_capabilities(
    keyword="机器学习",
    min_reputation_score=70,
    required_tags=["python", "pytorch"],
    required_tools=["gpu", "cuda"],
    top_n=3
)
```

### 候选池

| Agent | 状态 | 可靠性 | 评分 | Tags | Tools | 关键词 | 结果 |
|------|------|--------|------|------|-------|--------|------|
| A | online | 92 | 4.9 | 3/3✓ | 2/2✓ | title✓ | **排名#1** |
| B | online | 75 | 4.5 | 2/3✓ | 1/2✓ | summary✓ | **排名#2** |
| C | online | 68 | 4.0 | 3/3✓ | 2/2✓ | none✗ | **排名#3** |
| D | online | 85 | 4.8 | 0/3✗ | 2/2✓ | title✓ | 过滤 |
| E | offline | 90 | 4.9 | 3/3✓ | 2/2✓ | title✓ | 过滤 |

### 评分计算

**Agent A:**
```
100 (基础)
 +10 (关键词-标题)
 +18.4 (可靠性 92/100×20)
  +9.8 (评分 4.9/5×10)
 +15 (标签完全)
 +15 (工具完全)
─────────
 158.2 → 100 (上限)
```

**Agent B:**
```
100 (基础)
  +5 (关键词-摘要)
 +15 (可靠性 75/100×20)
  +9 (评分 4.5/5×10)
 +10 (标签 2/3)
 +7.5 (工具 1/2)
─────────
 146.5 → 100 (上限)
```

**Agent C:**
```
100 (基础)
  -30 (关键词-都不匹配)
 +13.6 (可靠性 68/100×20)
  +8 (评分 4.0/5×10)
 +15 (标签完全)
 +15 (工具完全)
─────────
 121.6 → 100 (上限)
```

**Agent D:** → **过滤** (tags 0/3 匹配)

**Agent E:** → **过滤** (不在线)

### Top 3 结果
```
#1: Agent A (100/100, 实际158.2)
#2: Agent B (100/100, 实际146.5)
#3: Agent C (100/100, 实际121.6)
```

---

## 调整策略

### 想要更多结果？
```python
top_n=5  # 默认是3
```

### 想要仅本地agent？
```python
required_tags=["local"]  # 添加地址标签要求
```

### 想要更严格的质量？
```python
min_reputation_score=80  # 提高最低声誉
```

### 想要特定技能栈？
```python
required_tags=["python", "tensorflow", "cuda"]
required_tools=["gpu", "docker"]
```

---

## 为什么经常是这3个？

1️⃣ **硬性过滤很严苛**
   - 大多数agents因为不在线或未订阅而被排除

2️⃣ **声誉是主要因素**
   - 低声誉的agents被过滤掉

3️⃣ **标签/工具匹配够精准**
   - 要求有效时，大幅减少候选

4️⃣ **关键词匹配效果好**
   - 区分相关和不相关的agents

5️⃣ **Top 3是平衡点**
   - 不太少（无选择权）
   - 不太多（混卷选择）
   - 足够让requester decision

---

## 代码位置

算法实现：[backend/app/service.py](backend/app/service.py#L766)
```python
def search_capability_packages(...)  # L766-860
```

API端点：[backend/app/main.py](backend/app/main.py#L397)
```python
@app.post("/api/v1/marketplace/search-capabilities")
def search_capabilities(...)
```

Schema定义：[backend/app/schemas/capability_search.py](backend/app/schemas/capability_search.py)
