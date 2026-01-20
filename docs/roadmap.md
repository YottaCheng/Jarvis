# Project Jarvis: Evolution Roadmap

## 📂 Phase 2: Logistics & Navigation (The "Map" Integration)
> "Calculated travel time to destination: 23 minutes. Traffic is light."

### 🎯 目标 (Objective)
集成地理空间感知能力，让 Jarvis 从单纯的“时间管理”进化为“时空管理”。
解决痛点：
1. **通勤计算**：去 UCL 到底需要多久？是否会迟到？
2. **米兰行动**：从机场到 Max Brown Hotel 的最优路线。
3. **路线规划**：根据日程地点，自动建议出发时间。

### 🛠 技术栈 (Tech Stack)
- **API**: Google Maps Platform
    - `Distance Matrix API`: 计算多点之间的通行时间。
    - `Directions API`: 获取具体导航路线。
    - `Places API`: 模糊搜索地点（如 "最近的 Pret" 或 "UCL IOE"）。

### 📝 功能描述 (User Stories)
1. **智能提醒**：
   - *Scenario*: "Sir, 下一节 Crime Science 讲座在 14:00 开始。考虑到 Piccadilly Line 的延误，建议您 13:15 出发。"
   
2. **差旅助手**：
   - *Scenario*: "检测到您周五飞往米兰。已查询到 Linate 机场到酒店的快线时刻表，建议搭乘 16:30 的班次。"

3. **动态日程**：
   - *Logic*: 如果两个会议地点的物理距离超过了 30 分钟路程，Jarvis 应自动在日历中插入 "Commute" 缓冲块，防止背靠背排期。

### 📅 实施计划 (Action Plan)
- [ ] 申请 Google Maps API Key。
- [ ] 编写 `src/geo_ops.py` 模块。
- [ ] 在 `main.py` 中增加 `get_travel_time` 工具函数供 Gemini 调用。

---
*Created by Jarvis System | Date: 2026-01-18*