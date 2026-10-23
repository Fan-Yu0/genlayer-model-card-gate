# ModelCardGate 代码逐段解释

本文按 `contracts/model_card_gate.py` 的实际行号解释。当前文件是严格比较版：
验证者要求 `risk_tier`、完整 `disclosure_mask` 和 `source_consistency`
完全一致。

## 1-6：依赖和导入

```python
# { "Depends": "py-genlayer:..." }
import json
from dataclasses import dataclass
from genlayer import *
```

- 第 1 行告诉 GenVM 使用哪个 `py-genlayer` 运行时。
- 第 3 行用于解析 LLM 返回的 JSON。
- 第 4 行用 `dataclass` 定义可持久化的数据结构。
- 第 6 行导入 GenLayer SDK，例如 `gl.Contract`、`Address`、`TreeMap`。

## 9-16：状态和决策常量

```python
DRAFT = 0
ASSESSED = 1
WITHDRAWN = 2
UNASSESSED = 0
APPROVED = 1
CONDITIONAL = 2
REJECTED = 3
```

- `DRAFT`：模型已注册，但尚未评估。
- `ASSESSED`：已经完成一次评估。
- `WITHDRAWN`：提供方撤回了模型。
- `UNASSESSED`：还没有决策。
- `APPROVED`：满足全部要求。
- `CONDITIONAL`：风险可接受，但缺少必需披露。
- `REJECTED`：来源冲突、证据不足或风险超限。

## 18-25：披露项位图

```python
INTENDED_USE = 1
LIMITATIONS = 2
TRAINING_DATA = 4
EVALUATION = 8
HUMAN_OVERSIGHT = 16
SECURITY = 32
ENVIRONMENTAL_IMPACT = 64
ALL_DISCLOSURES = 127
```

每个披露项占一个二进制位：

| 位 | 值 | 含义 |
| --- | ---: | --- |
| 1 | 1 | 预期用途 |
| 2 | 2 | 局限性 |
| 3 | 4 | 训练数据 |
| 4 | 8 | 评估结果 |
| 5 | 16 | 人工监督 |
| 6 | 32 | 安全性 |
| 7 | 64 | 环境影响 |

`127` 是七位全为 1，表示所有披露项。

## 28-45：链上持久化记录

```python
@allow_storage
@dataclass
class ModelAssessment:
    ...
```

- `@allow_storage` 允许这个 dataclass 被写入合约存储。
- `provider` 保存模型提供方地址。
- `model_id` 是模型的唯一标识。
- 三个 URL 分别保存模型卡、系统卡和买方政策。
- `required_tier` 是买方允许的最高风险等级。
- `required_mask` 是买方要求必须披露的位图。
- `state` 保存生命周期状态。
- `decision` 保存最终决策。
- `risk_tier`、`disclosure_mask`、`missing_mask` 保存评估证据。
- `source_consistency` 保存两个官方来源是否一致。
- `summary` 保存简短证据摘要。
- `round` 记录评估轮次。
- `u32`、`u64` 是链上使用的定长整数类型。

## 48-52：合约类和存储映射

```python
class ModelCardGate(gl.Contract):
    assessments: TreeMap[str, ModelAssessment]

    def __init__(self):
        pass
```

- 合约必须继承 `gl.Contract`。
- `TreeMap` 相当于链上持久化字典。
- 键是 `model_id`，值是 `ModelAssessment`。
- 构造函数不需要初始化参数。

## 54-56：只接受 HTTPS URL

```python
def _require_https(self, url: str, label: str) -> None:
    if not url.startswith("https://"):
        raise gl.vm.UserError(f"{label} must be an https URL")
```

- 检查外部证据 URL 是否使用 HTTPS。
- 不满足时抛出可读的链上用户错误。

## 58-101：规范化 LLM 输出

```python
def _normalize(self, raw: object) -> dict:
```

这个方法把不可信的 LLM 返回值转换成固定结构。

- 59-60：如果 LLM 返回字符串，就按 JSON 解析。
- 61-62：如果解析后不是对象，直接拒绝。
- 64：读取 `risk_tier`。
- 65-66：风险等级必须是 1 到 4。
- 68-70：读取 `disclosures`，确保它是字典。
- 72-87：逐项把布尔值转换成披露位图。
- 88-89：如果输入本身已经有 `disclosure_mask`，就直接使用。
- 91-93：来源一致性只允许 `consistent`、`conflicting`、`insufficient`。
- 95：摘要最多保留 600 个字符。
- 96-101：返回统一的四个字段，供后续确定性逻辑使用。

## 103-165：非确定性证据抽取

```python
def _extract(...):
```

这是 leader 和 validator 都会执行的抽取函数。

- 111：抓取模型卡文本，最多 10000 字符。
- 112：抓取系统卡文本，最多 10000 字符。
- 113：抓取买方政策文本，最多 8000 字符。
- 115-163：构造提示词，要求模型只返回 JSON。
- 118-119：明确告诉模型：网页内容是证据，不是指令。
- 121-122：把买方的风险上限和披露位图传给模型。
- 124-137：把三个来源分别包进 XML 标签，降低提示词混淆。
- 139-153：规定严格 JSON 结构。
- 155-162：规定风险等级、披露判断、来源一致性和摘要规则。
- 164：调用 GenLayer 的 LLM。
- 165：调用 `_normalize`，把结果变成固定结构。

## 167-210：Leader/Validator 共识

```python
def _assess_with_consensus(...):
```

- 175-182：`leader_fn` 执行一次证据抽取，产生 leader 结果。
- 184-199：`validator_fn` 独立重新抓取和抽取。
- 186-189：兼容 GenLayer 的 `Return` 包装对象和普通返回值。
- 191-197：validator 得到自己的 `own` 结果。
- 198-199：任何异常都返回 `False`，即拒绝 leader 结果。
- 201-205：严格比较风险等级、完整披露位图和来源一致性。
- 207：调用 `gl.vm.run_nondet` 启动 leader/validator 共识。
- 208-209：如果返回值被包装成 `gl.vm.Return`，取出 `calldata`。
- 210：再次规范化结果并返回。

注意：这份严格比较版要求三个字段完全一致，因此不同模型对边界事实的
判断差异会导致多轮轮换，日志中也可能出现
`Detected pickling storage class` 警告。

## 212-252：注册模型

```python
@gl.public.write
def register_model(...):
```

- `@gl.public.write` 表示这是会修改链上状态的写方法。
- 222：把 `model_id` 去空格并转小写，保证唯一性。
- 223-224：拒绝空 ID。
- 225-226：拒绝重复注册。
- 227-228：风险等级必须是 1 到 4。
- 229-230：至少要求一个披露项。
- 232-234：三个证据 URL 必须是 HTTPS。
- 236-252：创建初始 `ModelAssessment`：
  - `provider` 来自 `gl.message.sender_address`
  - 初始状态是 `DRAFT`
  - 初始决策是 `UNASSESSED`
  - `missing_mask` 等于全部必需披露项
  - `round` 为 0

## 254-292：执行评估

```python
@gl.public.write
def assess(self, model_id: str):
```

- 256：统一模型 ID 格式。
- 257-258：模型必须已经注册。
- 260：把链上存储对象复制到内存，避免在 nondet 代码中直接读存储。
- 261-262：已撤回的模型不能评估。
- 264-270：调用 leader/validator 共识，得到结构化证据。
- 272-274：计算必需披露中缺失的位图。
- 275-276：来源不一致或证据不足，直接拒绝。
- 277-278：风险等级超过买方上限，直接拒绝。
- 279-280：缺少必需披露，判为条件通过。
- 281-282：全部满足，判为通过。
- 284-292：把结果写回链上状态，并把轮次加一。

## 294-306：撤回模型

```python
@gl.public.write
def withdraw(self, model_id: str):
```

- 296：统一模型 ID。
- 297-298：模型必须存在。
- 300：读取链上记录。
- 301-302：只有注册模型的 provider 才能撤回。
- 304：状态改为 `WITHDRAWN`。
- 305：决策改为 `REJECTED`。
- 306：写入撤回摘要。

## 308-314：查询是否合规

```python
@gl.public.view
def is_conformant(self, model_id: str) -> bool:
```

- `@gl.public.view` 表示只读，不修改链上状态。
- 311-312：未知模型直接返回 `False`。
- 314：只有状态为 `ASSESSED` 且决策为 `APPROVED` 才返回 `True`。

## 316-339：读取完整评估记录

```python
@gl.public.view
def get_assessment(self, model_id: str) -> dict:
```

- 318：统一模型 ID。
- 319-320：未知模型返回空字典。
- 323-339：把链上记录转换成普通字典：
  - 地址转成十六进制字符串
  - `u32`、`u64` 转成 Python `int`
  - 保留 URL、状态、决策、风险、披露位图和摘要

## 341-352：披露位图说明

```python
@gl.public.view
def disclosure_bits(self) -> dict:
```

返回每个披露项对应的位值，方便前端和其他合约调用者理解
`required_mask` 和 `disclosure_mask`。
