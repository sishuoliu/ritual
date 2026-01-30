# 通用 RPG 桌游引擎 + LLM 对话式设计 — 可行性分析

> 目标：构建一套引擎，能支持各类复杂 RPG 桌游的开发与测试，并提供 LLM 对话框交互（连接 DeepSeek），将自然语言转化为规则、辅助设计  
> 日期：2026-01-29

---

## 一、经典复杂 RPG 桌游穷举

根据 BGG 排名、机制分类及社区讨论，以下是主要类型及代表作：

### 1. 地下城探索 / Dungeon Crawler

| 游戏 | 复杂度 | 核心机制 | 特点 |
|------|--------|----------|------|
| **Gloomhaven / Frosthaven** | 4.0+ | 卡牌驱动战斗、角色升级、战役、无骰子 | 95+ 剧本、角色退休、解锁 |
| **Descent: Legends of the Dark** | 3.5 | App 辅助、3D 地形、合作 | 现代化设计 |
| **HeroQuest** | 2.0 | 骰子战斗、一对多、DM 角色 | 经典入门 |
| **Mice & Mystics** | 2.5 | 骰子、故事驱动、家庭向 | 叙事性强 |
| **Imperial Assault** | 3.5 | 星战主题、一对多/App 合作 | 战术深度 |
| **Mansions of Madness** | 3.0 | App 辅助、克苏鲁、探索 | 恐怖叙事 |
| **Sword & Sorcery** | 4.0 | 剧本链、角色复活、骰子 | 硬核战术 |
| **Middara** | 4.0 | 动漫风、剧本式、角色成长 | 故事书厚 |

### 2. 半合作 / 叛徒机制

| 游戏 | 复杂度 | 核心机制 | 特点 |
|------|--------|----------|------|
| **Dead of Winter** | 3.0 | 隐藏目标、投票驱逐、资源管理、危机 | 叛徒全程隐藏 |
| **Betrayal at House on the Hill** | 2.5 | 探索→Haunt 阶段转换、叛徒揭示、50+ 剧本 | 随机地图 |
| **Nemesis** | 3.5 | 隐藏目标、外星人、空间站生存 | 恐怖+策略 |
| **Battlestar Galactica** | 3.5 | 赛隆叛徒、技能检定、投票 | 经典叛徒 |
| **Archipelago** | 3.5 | 殖民、隐藏目标、分离主义者 | 经济 + 谈判 |
| **功德轮回（本项目）** | 2.5–3.0 | 半合作、发愿、渡化、劫难 | 佛教主题 |

### 3. Legacy / 战役

| 游戏 | 复杂度 | 核心机制 | 特点 |
|------|--------|----------|------|
| **Pandemic Legacy S1/S2** | 3.0 | 贴纸、永久改变、12 月战役 | 开创 Legacy |
| **Risk Legacy** | 2.5 | 永久改变、贴纸、解锁 | Legacy 鼻祖 |
| **Betrayal Legacy** | 3.0 | 13 章战役、50+ Haunt | 叛徒 + Legacy |
| **Clank! Legacy** | 3.0 | 卡牌构筑 + Legacy | 解锁新内容 |
| **Legacy of Dragonholt** | 2.0 | 叙事冒险、选择分支 | 故事优先 |

### 4. 卡牌驱动 / LCG / 构筑

| 游戏 | 复杂度 | 核心机制 | 特点 |
|------|--------|----------|------|
| **Arkham Horror LCG** | 3.5 | 卡组构筑、战役、调查员 | 克苏鲁 |
| **Marvel Champions** | 3.0 | 英雄 + 套牌、合作 | 漫威主题 |
| **Pathfinder ACG** | 3.0 | 卡牌冒险、角色成长 | 类 TRPG |
| **Aeon's End** | 3.0 | 合作卡构、Boss 战 | 无洗牌 |

### 5. 高策略 / 非对称阵营

| 游戏 | 复杂度 | 核心机制 | 特点 |
|------|--------|----------|------|
| **Twilight Imperium 4** | 4.5 | 30 阵营、银河争霸、外交 | 超长时间 |
| **Scythe** | 3.5 | 非对称阵营、区域控制、引擎构建 | 视觉精美 |
| **Root** | 3.5 | 非对称阵营、区域控制 | 可爱风格 |
| **Spirit Island** | 4.0 | 合作、非对称精灵、恐惧 | 反殖民 |
| **Mage Knight** | 4.5 | 卡牌 + 探索 + 战斗 | 极高复杂度 |

### 6. 经典冒险 / 角色发展

| 游戏 | 复杂度 | 核心机制 | 特点 |
|------|--------|----------|------|
| **Talisman** | 2.5 | 骰子移动、遭遇、升级 | 老牌经典 |
| **Runebound** | 3.0 | 冒险卡、技能、装备 | 自由探索 |
| **Eldritch Horror** | 3.5 | 全球探索、神话事件、调查员 | 克苏鲁 |

---

## 二、核心机制抽象：引擎需要支持什么？

将上述游戏的机制归纳为**可配置的引擎组件**：

### 2.1 回合与阶段结构

| 机制 | 示例游戏 | 引擎抽象 |
|------|----------|----------|
| 固定阶段顺序 | 大多数 | `phases: [event, action, settlement]` |
| 玩家轮流行动 | 大多数 | `turn_order: clockwise / initiative` |
| 同时行动 | 部分 | `simultaneous: true` |
| 阶段内多次行动 | 功德轮回（2 次） | `actions_per_turn: 2` |
| 阶段转换触发 | Betrayal（Haunt） | `phase_transition_trigger: condition` |

### 2.2 玩家与角色

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 非对称角色 | 几乎所有 | `roles: [farmer, merchant, ...]` + 初始属性 |
| 角色成长（升级） | Gloomhaven | `level_up: { xp_threshold, new_abilities }` |
| 角色退休/解锁 | Gloomhaven | `retirement: { condition, unlock }` |
| 隐藏身份/叛徒 | Dead of Winter | `hidden_role: true` |
| 职业转职/分支 | 功德轮回（皈依/大乘/密宗） | `choice_tree: [ { id, condition, effects } ]` |

### 2.3 资源系统

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 多资源 | 几乎所有 | `resources: [wealth, merit, wisdom, ...]` |
| 全局资源 | 功德轮回（劫难） | `global_resources: [calamity]` |
| 资源转换 | 部分 | `conversion: { from, to, rate }` |
| 资源上限/下限 | 部分 | `min, max, cap` |

### 2.4 行动系统

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 行动列表 | 几乎所有 | `actions: [ { id, cost, effect, requires } ]` |
| 骰子判定 | 大多数 | `dice: "2d6"`, `effect_table: {...}` |
| 卡牌驱动行动 | Gloomhaven | `action_source: hand_cards` |
| 位置相关行动 | Descent | `location_actions: [...]` |

### 2.5 牌堆与卡牌

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 事件牌堆 | 功德轮回、Dead of Winter | `decks: [events, sentients, ...]` |
| 抽牌/弃牌 | 几乎所有 | `draw, discard, shuffle` |
| 卡牌效果 | 所有 | `card: { id, effect, trigger }` |
| 手牌管理 | Gloomhaven | `hand_size, hand_limit` |
| 卡组构筑 | Arkham LCG | `deck_building: true` |

### 2.6 胜负条件

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 团队胜利 | 合作类 | `win_conditions.team: [...]` |
| 团队失败 | 合作类 | `lose_conditions.team: [...]` |
| 个人胜利 | 半合作 | `win_conditions.individual: score_formula` |
| 叛徒胜利 | 叛徒类 | `win_conditions.traitor: [...]` |
| 剧本/Haunt 胜利 | Betrayal | `scenario_win: {...}` |

### 2.7 战役与 Legacy

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 剧本链 | Gloomhaven | `scenarios: [ { id, unlock_condition, next } ]` |
| 永久改变 | Legacy 系列 | `permanent_changes: [ { trigger, effect } ]` |
| 解锁内容 | 多数战役 | `unlocks: [ { condition, content } ]` |
| 存档/读档 | 战役类 | `save_state, load_state` |

### 2.8 隐藏信息

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 隐藏手牌 | 大多数 | `hidden: hand` |
| 隐藏目标 | Dead of Winter | `hidden: objective` |
| 隐藏身份 | 叛徒类 | `hidden: role` |
| 部分可见 | Hanabi | `visible_to: others_only` |

### 2.9 叙事与分支

| 机制 | 示例 | 引擎抽象 |
|------|------|----------|
| 分支选择 | Legacy of Dragonholt | `choice: { id, options, outcomes }` |
| 故事书 | Middara | `storybook: [ { id, text, triggers } ]` |
| 条件文本 | 多数 | `conditional_text: { condition, text }` |

---

## 三、引擎可行性分析：能否支持所有这类 RPG 桌游？

### 3.1 可行性评估

| 维度 | 评估 | 说明 |
|------|------|------|
| **机制覆盖** | ✅ 高 | 上述机制可归纳为有限的抽象组件（阶段、行动、资源、牌堆、胜负、分支），用 YAML/JSON 配置即可表达 |
| **复杂度跨度** | ✅ 中高 | 从简单（Talisman）到极复杂（Twilight Imperium）都可建模，但极复杂游戏配置量大 |
| **隐藏信息** | ⚠️ 中 | 需引擎支持「视角」（哪些信息对哪些玩家可见）；模拟时需决定是「全知」还是「有限信息」 |
| **叙事分支** | ✅ 高 | 可借鉴 Ink/Twine 的分支叙事语法，嵌入引擎 |
| **Legacy 永久改变** | ⚠️ 中 | 需引擎支持「状态持久化」和「解锁」；数字化比实体更容易 |
| **AI 模拟** | ⚠️ 中 | 隐藏信息 + 多人合作/叛徒的策略模拟难度高；可先做「完全信息」版本 |

### 3.2 核心结论

> **可以做出一套通用引擎，支持绝大多数 RPG 桌游的开发与测试。**

但需要**分层设计**：

1. **核心层**：阶段、行动、资源、牌堆、胜负条件、分支选择 —— 足以覆盖 80%+ 游戏。
2. **扩展层**：隐藏信息、叛徒、Legacy 永久改变、App 辅助 —— 按需加入。
3. **叙事层**：Ink 式分支文本、故事书 —— 独立模块，可选。

---

## 四、LLM 对话式设计：用 DeepSeek 把自然语言转化为规则

### 4.1 用户场景示例

#### 场景 A：模糊需求

**用户**："在功德轮回里，我想加一些选择，让玩家可以走不同的修行路线。"

**LLM（DeepSeek）**：
> 理解你的需求。我建议加入「修行路线」选择系统，在游戏开始或特定回合让玩家选择：
> 
> 1. **是否皈依**：皈依者 +1 福 +1 慧，不皈依者 +3 财富
> 2. **是否发愿大乘**：发愿者渡化奖励 ×1.5，但需满足更高的渡化门槛
> 3. **是否修行密宗**：密宗修行者解锁特殊行动「灌顶」（消耗 5 慧，+3 福），但初始慧 -2
> 
> 这些选择会形成一棵「分支树」，我可以帮你生成对应的 YAML 配置。需要我继续吗？

#### 场景 B：精确需求

**用户**："在第 3 回合开始时，皈依者可以选择是否'发愿大乘'。如果选是，后续每次渡化额外 +1 福，但游戏结束时若渡化 <4 则扣 5 分。"

**LLM（DeepSeek）**：
> 收到。我将生成以下 YAML 配置：
> 
> ```yaml
> choice_events:
>   - id: vow_mahayana
>     trigger: { round: 3, phase: start, player: "role.refuge == true" }
>     prompt: "是否发愿大乘？"
>     options:
>       - id: yes
>         effect:
>           - set_flag: { player: mahayana_vow, value: true }
>           - modify_action: { action: liberate, bonus: { merit: 1 } }
>           - add_end_condition: { if: "player.liberated_count < 4", penalty: { score: -5 } }
>       - id: no
>         effect: []
> ```
> 
> 需要我解释或调整吗？

### 4.2 技术实现

| 组件 | 实现方式 |
|------|----------|
| **对话框 UI** | Streamlit `st.chat_input` / `st.chat_message` |
| **LLM API** | DeepSeek API（兼容 OpenAI SDK） |
| **Prompt 模板** | 系统 prompt 包含：引擎 YAML schema、当前游戏配置摘要、用户历史对话 |
| **输出解析** | LLM 输出 JSON/YAML 片段 → 引擎校验 → 若失败则 LLM 自动修正 |
| **上下文管理** | 保存对话历史 + 当前配置，支持多轮迭代 |

### 4.3 Prompt 工程要点

```
你是一个桌游设计助手，帮助用户设计和修改 RPG 桌游规则。

当前游戏：功德轮回 v3.6
引擎支持的 YAML 结构：
- resources: 资源定义
- roles: 角色定义
- phases: 阶段定义
- actions: 行动定义
- choice_events: 选择事件（分支）
- win_conditions / lose_conditions: 胜负条件

用户可能给出模糊或精确的需求。你的任务：
1. 理解用户意图
2. 若模糊，提出 2-3 个具体方案供选择
3. 若精确，直接生成对应 YAML
4. 解释设计的影响（平衡性、复杂度）
5. 输出 YAML 时用 ```yaml 代码块

当前配置摘要：
- 4 角色：农夫、商人、学者、僧侣
- 6 回合
- 团队胜利：劫难≤12 且 渡化≥6
- 已有选择：皈依（开局）

用户输入：
```

### 4.4 DeepSeek API 集成示例

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_DEEPSEEK_API_KEY",
    base_url="https://api.deepseek.com"
)

def chat_with_designer(user_message: str, history: list, game_config: dict) -> str:
    system_prompt = build_system_prompt(game_config)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    return response.choices[0].message.content
```

---

## 五、功德轮回「修行路线」扩展设计示例

### 5.1 分支选择树

```
游戏开始
    └─ 是否皈依？
        ├─ 是 → 皈依者（福+1, 慧+1）
        │     └─ 第3回合：是否发愿大乘？
        │           ├─ 是 → 大乘行者（渡化奖励+1福，结束时渡化<4扣5分）
        │           │     └─ 第5回合：是否修行密宗？
        │           │           ├─ 是 → 密宗行者（解锁「灌顶」行动）
        │           │           └─ 否 → 显宗行者
        │           └─ 否 → 小乘行者
        └─ 否 → 世俗修行（财富+3）
              └─ 第3回合：是否行善积德？
                    ├─ 是 → 善信（每回合+1福，但财富-1）
                    └─ 否 → 普通信众
```

### 5.2 对应 YAML 配置

```yaml
choice_events:
  # 开局选择：皈依
  - id: refuge_choice
    trigger: { round: 0, phase: setup }
    prompt: "是否皈依三宝？"
    options:
      - id: yes
        effect:
          - set_flag: { player: refuge, value: true }
          - gain: { merit: 1, wisdom: 1 }
      - id: no
        effect:
          - set_flag: { player: refuge, value: false }
          - gain: { wealth: 3 }

  # 第3回合：大乘发愿（仅皈依者）
  - id: mahayana_vow
    trigger: { round: 3, phase: start, condition: "player.refuge == true" }
    prompt: "是否发愿大乘？"
    options:
      - id: yes
        effect:
          - set_flag: { player: mahayana, value: true }
          - modify_action: { action: liberate, bonus: { merit: 1 } }
          - add_scoring_rule: { if: "player.liberated_count < 4", penalty: -5 }
      - id: no
        effect:
          - set_flag: { player: mahayana, value: false }

  # 第5回合：密宗修行（仅大乘者）
  - id: vajrayana_choice
    trigger: { round: 5, phase: start, condition: "player.mahayana == true" }
    prompt: "是否修行密宗？"
    options:
      - id: yes
        effect:
          - set_flag: { player: vajrayana, value: true }
          - unlock_action: { action: initiation }
      - id: no
        effect: []

  # 第3回合：行善积德（仅非皈依者）
  - id: charity_choice
    trigger: { round: 3, phase: start, condition: "player.refuge == false" }
    prompt: "是否行善积德？"
    options:
      - id: yes
        effect:
          - set_flag: { player: devotee, value: true }
          - add_per_round_effect: { gain: { merit: 1 }, cost: { wealth: 1 } }
      - id: no
        effect: []

# 新行动：灌顶（密宗专属）
actions:
  - id: initiation
    name: "灌顶"
    requires: { player.vajrayana: true, wisdom: ">=5" }
    cost: { wisdom: 5 }
    effect:
      - gain: { merit: 3 }
    description: "密宗加持，消耗 5 慧获得 3 福"
```

---

## 六、综合可行性结论

### 6.1 核心问题回答

| 问题 | 回答 |
|------|------|
| **能否做一套引擎支持所有 RPG 桌游？** | ✅ 可以。通过分层抽象（阶段/行动/资源/牌堆/分支/胜负），用 YAML 配置即可表达绝大多数 RPG 桌游机制。极复杂游戏（如 Twilight Imperium）配置量大但仍可建模。 |
| **LLM 对话式设计可行吗？** | ✅ 可行。DeepSeek API 已支持代码生成和 JSON 结构化输出；通过 Prompt 工程 + 校验循环，可实现「自然语言 → YAML 规则」的可靠转换。 |
| **模糊/精确需求都能处理吗？** | ✅ 可以。模糊需求 → LLM 提出方案供选择；精确需求 → LLM 直接生成配置；两者都可通过多轮对话迭代。 |
| **功德轮回的分支选择能实现吗？** | ✅ 完全可以。用 `choice_events` 配置分支选择树，引擎在指定回合触发选择，记录玩家 flag，后续行动/效果基于 flag 条件生效。 |

### 6.2 风险与缓解

| 风险 | 缓解 |
|------|------|
| LLM 生成的 YAML 可能有语法错误 | 引擎校验 + LLM 自动修正循环 |
| LLM 可能误解用户意图 | 多轮对话 + 确认步骤 + 预览生成结果 |
| 复杂游戏配置量大 | 提供模块化模板（事件.yaml, 角色.yaml）；LLM 可按模块生成 |
| 隐藏信息模拟难度高 | 先做「完全信息」版本；隐藏信息作为高级模块 |

### 6.3 推荐实施路径

1. **Phase 1**：核心引擎 + 功德轮回 v3.6 配置化 + 随机模拟
2. **Phase 2**：回测管道 + 报告 + 版本对比
3. **Phase 3**：分支选择（`choice_events`）+ 功德轮回路线扩展
4. **Phase 4**：LLM 对话框（DeepSeek）+ 自然语言 → YAML
5. **Phase 5**：第二款游戏验证通用性 + 高级 AI

---

## 七、附录：更多 RPG 桌游参考

### 完整游戏列表（按类型）

**地下城探索**：Gloomhaven, Frosthaven, Descent, HeroQuest, Mice & Mystics, Imperial Assault, Mansions of Madness, Sword & Sorcery, Middara, Journeys in Middle-earth, Bloodborne, TMNT: Shadows of the Past

**半合作/叛徒**：Dead of Winter, Betrayal at House on the Hill, Nemesis, Battlestar Galactica, Archipelago, The Thing, Dark Moon, Shadows over Camelot

**Legacy/战役**：Pandemic Legacy S1/S2/S0, Risk Legacy, Betrayal Legacy, Clank! Legacy, Aeon's End Legacy, Charterstone, SeaFall, Legacy of Dragonholt

**卡牌驱动**：Arkham Horror LCG, Marvel Champions, Pathfinder ACG, Aeon's End, Legendary Encounters, Lord of the Rings LCG

**非对称阵营**：Twilight Imperium, Scythe, Root, Spirit Island, Vast, Oath

**经典冒险**：Talisman, Runebound, Eldritch Horror, Arkham Horror 3E, Mage Knight, Robinson Crusoe

### 分支叙事引擎参考

- **Ink** (inkle)：开源叙事语言，支持深度分支
- **Twine**：可视化分支编辑器，输出 HTML
- **Yarn Spinner**：Unity 集成叙事工具
