from __future__ import annotations

import json
from pathlib import Path

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
BASE_REPORT = OUTPUT_ROOT / "Manuscript_Revision_Before_After.md"
CHANGES = OUTPUT_ROOT / "Bilingual_Revision_Changes.json"
FINAL_REPORT = OUTPUT_ROOT / "Final_Revision_Report.md"


def build_report() -> Path:
    text = BASE_REPORT.read_text(encoding="utf-8")
    payload = json.loads(CHANGES.read_text(encoding="utf-8"))

    old_scope = (
        "本次修改针对英文 JCAMD 投稿全文。研究问题、模型、数据集、"
        "全部数值、实验判断和引文编号保持不变；未新增文献立场或"
        "未做实验。修改集中在段落功能、衔接、句法、范围界定、"
        "结果分组和重复防御表达。"
    )
    new_scope = (
        "本次修改覆盖英文 JCAMD 投稿全文和逐段对应的中文参考稿。"
        "原有 1-31 号文献、研究问题、模型、数据集、全部数值和实验判断"
        "均保留；在另一对话框的检索结果基础上新增 32-45 号文献，并"
        "逐条核对题名、年份、摘要与引用语境。除双语对应、文献适用范围"
        "和表述边界外，没有新增实验。"
    )
    text = text.replace(old_scope, new_scope)
    text = text.replace(
        'title: "论文全文修改报告"',
        'title: "论文中英文终稿修订报告"',
        1,
    )
    text = text.replace(
        'subtitle: "代表性前后对照与具体改善"',
        'subtitle: "七项检查、双语合并与代表性前后对照"',
        1,
    )

    appendix = f"""

## 与另一对话框内容的合并

另一个对话框提供的工作重点包括：把每分子独立重置的模型准确表述为
QRC/QELM 家族的无状态 QELM 极限；不再使用 equal-capacity 作为核心
主张；补充近期 QRC、QELM、等价检验与 ADMET 验证文献；生成中文逐段稿。
这些内容全部并入最终英文稿和中文稿，但按本次七项检查重新核对了段落、
术语、数字和引用。

具体处理如下：

- 主标题保留“随机实现与强基线”，副标题收束为
  “A Signal-Calibrated Benchmark of Stateless Quantum Reservoir Features
  on TDC ADMET”。
- 摘要、4.2 节、讨论和结论均明确：模型是无状态固定量子特征映射，
  不是跨分子传播量子态的有记忆 QRC。
- 将“完全相同容量”的旧表述改为输入维数、名义读出维数、拟合参数数量、
  随机映射预算和调参预算匹配；正文分别报告读出矩阵秩、留出特征有效秩、
  条件数和中心核对齐。
- 把 hERG 与 B3DB 的结果改称 external transfer，避免将回顾性外部数据
  表述为前瞻性验证。
- 将连续 hERG 回归、Qiskit/Aer 电路审计、已知信号校准与来源诊断拆成
  5.8、5.9、5.10 三节。
- 将局限拆为评价、执行和辅助分析三类，将结论拆为经验结果与方法贡献，
  避免在摘要、讨论、局限和结论重复同一防御句。
- 中文稿统一“基线模型”“测量采样”“量子极限学习”“正交界分支”
  等术语；保留 ADMET、TDC、QRC、QELM、Hamiltonian、Pauli、AUROC
  等专业缩写和数据集名称。
- 另一个对话框曾加入的 0.0205 和约 72 个划分种子并非本仓库归档分析
  的直接输出，因此最终稿删去这两个常数，只保留“五个划分不足以提供
  高功效等价证明”的限定，并引用等价检验设计文献 [40]。

## 新增文献与适用范围核验

新增文献均于 2026-11-26 通过 arXiv API 或 Crossref 核对。

| 编号 | 文献与核验结果 | 在本稿中的用途 |
|---|---|---|
| 32 | Pandey, *When Classical Baselines Are Tuned as Carefully as the Quantum Model...* | 支持“匹配调参后关联读出优势消失”的解释；任务为预测而非 ADMET。 |
| 33 | Pandey, *A Quantum Reservoir Architecture for Chaotic Forecasting...* | 作为反例限定结论范围；结果只涉及混沌预测和较窄基线面板。 |
| 34 | Kornjaca et al., *Large-scale quantum reservoir learning with an analog quantum computer* | 说明更大规模硬件储层的可行性，不构成本文五比特仿真证据。 |
| 35 | Ramon-Escandell et al., *From quantum reservoirs to quantum extreme learning machines...* | 支持 QRC 记忆与 QELM 重置的界线。 |
| 36 | Xiong et al., *On fundamental aspects of quantum extreme learning machines* | 支持编码频率、观测量数量和测量局部性限制表达力。 |
| 37 | Gross and Rieser, Pauli transfer matrix theory | 区分表示、可解码性和读出秩。 |
| 38 | Gross and Rieser, measurement-operator optimization | 说明固定读出可能遗漏可访问信息。 |
| 39 | Ait Haddou, readout orientation | 说明相同秩和预算不等于相同任务信息。 |
| 40 | Knopov and Shvai, equivalence-testing run design | 支持 TOST 五划分功效有限的说明。 |
| 41 | Siraj et al., matched QML equivalence benchmark | 支持“公平匹配后接近但未超过经典模型”的背景。 |
| 42 | Talkhan et al., representation and model contributions | 支持分别解释表示效应和模型效应。 |
| 43 | Zheng et al., structural-frontier ADMET evaluation | 支持公开固定测试集不是部署验证。 |
| 44 | Seal et al., model validation protocols | 支持 external transfer、分布偏移和失败模式的分析。 |
| 45 | De Lorenzis et al., entanglement and classical simulability | 说明有限纠缠可改善嵌入但不自动构成量子优势。 |

这些新增文献没有改变原有 1-31 号引用，也没有被用来替代本文实验证据。

## 中文终稿专项前后对照

### 1. 模型定位

**原文**

> 本文在无状态量子极端学习机（QELM）极限下，对固定的五比特幅度编码特征
> 映射开展覆盖 TDC 全端点的信号校准评价。

**修改后**

> 本文将模型定位为无状态量子极限学习机（QELM），评价一项覆盖 TDC 全端点
> 的固定五比特幅度编码特征映射。

**具体改善**

原句把“极限学习机”和“极限下”叠在一起，术语也不统一。修改后先明确模型
类别，再说明研究对象，同时保留五比特、幅度编码和 TDC 全端点范围。

### 2. TOST 功效说明

**原文**

> 五个 QRC 减对照 seed 效应的样本标准差中位数为 0.0205。……约需 72 个
> 独立划分种子。因此，主分析的五划分足以估计平均效应，但不能为单个端点
> 提供高功效的等价证明。

**修改后**

> 事后随机种子级功效诊断表明，五个划分随机种子不足以在 +/-0.01 的指标
> 边界内为单个端点提供高功效等价证明。TOST 结果仍属探索性，按等价计数
> 报告，不作为确证性主张。

**具体改善**

删除未在归档结果中形成可追溯输出的两个常数，保留可核查的有限功效判断。
同时把“估计平均效应”和“证明等价”分开，避免将不显著误写成等价。

### 3. 命题 1

**原文**

> 因此，任意无截距线性读出均为实二次型 a^T M a+b。

**修改后**

> 这些 15 个特征的任意仿射读出均可写成 a^T M a+b，其中截距并入 b。

**具体改善**

原句同时写“无截距”和“+b”，数学含义自相矛盾。修改后明确截距被吸收进 b，
命题、线性残差头和结论随之一致。

### 4. 结果章节

**原文**

> 5.8 独立连续 pIC50 回归与电路级审计

**修改后**

> 5.8 独立连续 hERG 回归
>
> 5.9 电路级 Aer 审计
>
> 5.10 基准校准与来源诊断

**具体改善**

回归结果、电路保真度审计和基准校准回答不同问题，拆分后标题能直接对应
各自证据，避免一个长节混合三类推断。

### 5. 局限

**原文**

> 两个长段同时列出评价、量子执行、连续回归和化学空间的限制。

**修改后**

> 按评价限制、执行边界、辅助分析适用范围分成三段。

**具体改善**

每项限制现在说明它约束哪一类推断；必要的适用边界集中出现，不再在不同
段落反复声明。

### 6. 结论

**原文**

> 一段同时报告经验结果、方法贡献和适用范围。

**修改后**

> 第一段报告 22 个端点、双基线、门控、外部迁移、连续回归、电路审计和
> 信号校准结果；第二段区分经验贡献、方法贡献和适用边界。

**具体改善**

读者能区分“观察到了什么”和“本文提供了什么方法”，不必在同一长句中
反复辨认哪些是结果、哪些是解释。

## 最终一致性与版式检查

- 英文稿与中文稿均为 171 个段落、6 张表、4 幅图、4 个 Word 公式和
  45 条参考文献。
- 英文摘要 250 词；英文和中文正文中的数值逐段核对；6 张表逐单元格
  核对数字，未发现差异。
- 两稿引用 1-45 均有对应参考文献，无缺失或未引用条目。
- 英文稿无 therefore、thus、hence 的机械重复；中文稿保留 6 处语义明确的
  “因此”，未发现连续冒号堆叠。
- 英文 `equal-capacity` 已清除；中文术语已统一。
- 两稿均为 US Letter 单栏；English 渲染 21 页，中文渲染 19 页。
- 页级 QA 未发现空白页、越界字符、边缘挤压、缺字替换符或标题孤行；
  4 幅图均与题注位于同一页，6 张表均设置重复表头。
- 未发现需要删除的虚假引用，未改动研究数值、指标方向或实验结论。
- 未把句长、句式或排版特征当作作者身份证据，也未作作者身份推断。

## 最终双语增补记录

本轮与另一对话框合并后共记录 {len(payload['changes'])} 处中英文段落级、
章节级或表项级修改。完整逐项记录见 `Bilingual_Revision_Changes.json`。
"""

    FINAL_REPORT.write_text(text.rstrip() + appendix + "\n", encoding="utf-8")
    return FINAL_REPORT


if __name__ == "__main__":
    print(build_report())
