# 实验结论摘要

## 数据与设计

- TDC ADMET 官方 22 个端点。
- Harvard Dataverse 文件 4426004，SHA-256
  `bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1`。
- 65,430 条官方 train+valid 记录，16,379 条带标签官方 test 记录。
- 五个 scaffold train/valid seed。
- 两个基座：Morgan-ExtraTrees 与修正后的 MapLight-CatBoost。
- 三个 15 维随机族，每族五个独立映射：
  QRC、real-orthogonal quadratic、random Fourier。
- 共 220 次基座-split 流程、660 个分支族适配点和 3,300 个
  分支-随机映射残差拟合。

## 主结果

未门控 QRC 相对固定 real-orthogonal 二次映射：

| 基座 | QRC 更好 | QRC 更差 | Holm 正向显著 | Holm 负向显著 |
|---|---:|---:|---:|---:|
| ExtraTrees | 6 | 16 | 0 | 2 |
| MapLight-CatBoost | 3 | 19 | 0 | 1 |

Holm 显著负向端点为：

- ExtraTrees / AMES：AUROC 差 `-0.0115`，Holm `p=0.011`。
- ExtraTrees / VDss：Spearman 差 `-0.1127`，Holm `p=0.042`。
- CatBoost / Solubility：MAE 差 `-0.0268`，Holm `p=0.011`。

没有任何端点在 Holm 校正后显示 QRC 正向显著。

## 强基座

MapLight-CatBoost 在 21/22 个端点的五 seed 平均官方指标上优于
Morgan-ExtraTrees。QRC 在更强基座上的相对表现没有改善，反而进一步向负向集中。

## 验证门控

QRC 权重被验证集置零的次数：

- ExtraTrees：47/110。
- MapLight-CatBoost：55/110。

门控后的 QRC 相对同规则门控的 real-orthogonal 映射：

| 基座 | 更好 | 更差 | 持平 | Holm 正向显著 |
|---|---:|---:|---:|---:|
| ExtraTrees | 11 | 11 | 0 | 0 |
| MapLight-CatBoost | 4 | 17 | 1 | 0 |

门控主要减少了不利残差造成的退化，没有形成稳定超越经典对照的量子增量。

## 联合门控

允许 QRC 与 real-orthogonal 分支同时进入模型，并在验证集选择两个标量权重：

| 基座 | 相对门控正交 更好/更差/持平 | Holm 正向显著 |
|---|---:|---:|
| ExtraTrees | 12 / 10 / 0 | 0 |
| MapLight-CatBoost | 6 / 14 / 2 | 0 |

联合门控没有提供稳定的互补信息。

## 有限采样

在 BBB、hERG、Caco2、LD50、PPBR、DILI、CYP2D6 inhibition 和 VDss
八个代表端点上，模拟 1,024、4,096、16,384 shots，并在有限采样特征上重新拟合
残差头。每个 Pauli 期望按独立二项测量抽样。

| 基座 | 1,024 shots | 4,096 shots | 16,384 shots |
|---|---:|---:|---:|
| ExtraTrees，QRC 好/差于门控正交 | 5 / 3 | 5 / 3 | 5 / 3 |
| CatBoost，QRC 好/差于门控正交 | 2 / 6 | 1 / 7 | 1 / 7 |

有限采样没有反转主结论。

## 低数据曲线

八个代表端点使用 5%、10%、20%、40% 和完整训练集。未门控 QRC 相对正交映射的
正向端点数：

| 基座 | 5% | 10% | 20% | 40% | 100% |
|---|---:|---:|---:|---:|---:|
| ExtraTrees | 2/8 | 0/8 | 1/8 | 0/8 | 2/8 |
| MapLight-CatBoost | 1/8 | 0/8 | 1/8 | 0/8 | 1/8 |

验证门控在 ExtraTrees 的 20% 规模达到 6/8，但 CatBoost 同一比例为 4/8，
其他规模也未在两个基座上同步复现。没有证据支持稳定的低数据量子优势。

## 独立外部验证

hERG 使用 ToxTree 外部测试集，按 `PIC50 >= 4.5` 二分类，并在删除 TDC 重叠后
保留 293 个分子。BBB 使用 B3DB 分类集，删除 TDC 重叠后保留 2,317 个分子。

门控 QRC 相对同规则门控正交映射（外部分子上的 AUROC 差）：

| 基座 | hERG | B3DB BBB |
|---|---:|---:|
| ExtraTrees | +0.0112，Holm p=0.200 | −0.0046，Holm p=0.002 |
| MapLight-CatBoost | +0.0402，Holm p=0.002 | −0.0034，Holm p=0.016 |

hERG 的 CatBoost 正向信号与 BBB 的跨基座负迁移同时存在，因此外部验证支持
“来源依赖的候选信号”，不支持普遍可迁移优势。

## 连续标签排序迁移（探索性）

在不重新训练分类模型的情况下，将已有外部预测分别与 hERG `PIC50` 和
B3DB `logBB` 连续标签计算 Spearman 排序。hERG 连续标签覆盖全部 293 个
非重叠分子；B3DB 仅覆盖 613/2,317 个分子，其中 86.8% 为 BBB 阳性，因此
该子集具有明显选择偏差。

| 端点 | 基座 | 门控 QRC − 门控正交 | 95% CI | 未校正 p | Holm p（12 项） |
|---|---|---:|---:|---:|---:|
| hERG pIC50 | ExtraTrees | +0.004 | [−0.019, 0.027] | 0.757 | 1.000 |
| hERG pIC50 | MapLight-CatBoost | +0.043 | [0.012, 0.072] | 0.020 | 0.234 |
| B3DB logBB | ExtraTrees | −0.002 | [−0.014, 0.011] | 0.724 | 1.000 |
| B3DB logBB | MapLight-CatBoost | +0.001 | [−0.016, 0.015] | 0.896 | 1.000 |

CatBoost/hERG 的连续标签方向与二分类 AUROC 候选信号一致，但在统一多重校正
后不显著，且未在 BBB 复现。该分析属于二分类输出的排序迁移，不是独立训练
连续值模型的回归外部验证。

## 模拟退相干

在八个代表端点上加入 p=0.001、0.005 和 0.010 的局部单比特 depolarizing
并叠加 4,096 shots，在含噪特征上重新拟合残差头。QRC 相对门控正交映射的
更好/更差端点数在三档噪声下保持不变：

- ExtraTrees：5/3。
- MapLight-CatBoost：1/7。

没有出现噪声水平依赖的方向反转。

## 有限储层族搜索

五组预设 QRC 参数族与五组同等预算的实正交候选均由 TDC valid 选择。
QRC 对正交界的好/差端点数：

- ExtraTrees：4/4。
- MapLight-CatBoost：2/5/1 平。

没有 Holm 正向显著端点。baseline 仍是最常选择的参数配置，说明扩展参数族
没有产生新的稳定优势。

## 解释边界

- 当前结果针对五比特幅度编码、固定 Ising 演化、15 个 Pauli-Z/ZZ 读出和精确
  state-vector 模拟。
- 有限 shots 仅采用独立二项读出模型，不覆盖硬件退相干、门错误、读出串扰、
  真实测量调度、可训练线路、不同编码或不同 PCA 维度。
- 探索性 TOST 使用 AUROC/AUPRC/Spearman 的 0.01 绝对边界和基座 MAE 的 2%
  相对边界；这些边界用于基准解释，不是临床阈值。
- 在若干端点，门控后的两个分支都回退到基座，因此“接近零差异”不能解释为
  量子分支有效。

## 文件

- 论文：`outputs/论文修订稿_v2_TDC完整实验.docx`
- PDF：`outputs/论文修订稿_v2_TDC完整实验.pdf`
- 主结果表：`results/report/endpoint_summary.csv`
- 端点推断：`results/report/comparisons.csv`
- 连续标签迁移：`results/external_continuous/comparisons.csv`
- 逐 split 预测：`results/runs/`
- 可复现附件：`outputs/补充材料_qrc_admet_代码与结果_最终.zip`

