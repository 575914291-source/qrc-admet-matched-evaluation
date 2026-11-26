---
title: "固定量子储层特征用于 TDC ADMET 预测的匹配评估"
subtitle: "基于随机实现与强基线的信号校准基准"
lang: zh-CN
---

# 摘要

文献报告的量子储层性能增益难以比较，因为匹配经典对照、多种随机实现、强基线模型与外部迁移检验很少同时出现。本文将模型定位为无状态量子极限学习机（QELM），评价一项覆盖 TDC 全端点的固定五比特幅度编码特征映射，并用 Morgan-ExtraTrees 与 MapLight-CatBoost 比较真实正交二次映射和随机 Fourier 特征。研究使用五个骨架划分，并对每族五个映射取平均以控制随机性。未门控量子特征在 ExtraTrees 的 6 个端点上更好、16 个端点上更差；在 CatBoost 的 3 个端点上更好、19 个端点上更差。Holm 校正后，没有端点显著更好，3 个端点显著更差。门控、联合 QRC-正交残差、低数据缩放、有限测量采样、模拟噪声和有限储层族搜索均未产生跨基线优势。外部迁移具有来源依赖性：在 293 个非重叠 hERG 分子上，门控 CatBoost-QRC 比相同规则门控的正交对照高 0.040 AUROC；但两种基线在 2,317 个 B3DB BBB 分子上均出现退化。hERG 差异还包含正交界分支的性能下降。连续标签排序和骨架不相交的 pIC50 敏感性分析均未通过联合多重校正。已知信号校准能够恢复 QRC 目标和经典目标，零信号假阳性率为 2.0-4.7%。Qiskit/Aer 读出保真度审计显示，误差下特征排序仍被保留，但幅度衰减，且未在误差特征上重新训练下游模型。化学空间分析未显示简单的来源效应。本文的贡献是针对这一特征映射族开展信号校准的 TDC 审计，并提供开放的匹配评价流程。结论受五比特幅度编码、15 个 Pauli 读出、线性残差头和精确态矢量模拟限制，并不否定其他编码、可训练线路、更大储层或物理硬件。

关键词：ADMET；QSAR；化学信息学；TDC；无状态量子特征映射；匹配经典对照；外部迁移

# 1 引言

ADMET 预测包含二分类、连续值和排序端点，不同任务在样本量、测量分辨率和化学空间覆盖方面差异很大。TDC 提供固定测试集、端点专用指标和骨架划分接口，使端点级验证成为可能 \[1,2\]。分子表示、模型族和评价划分中的任一因素都可能改变模型排名 \[3-6\]。仅与单一弱基线模型比较，无法分离量子特征的增量。这些特征使基准证据直接关系到 QSAR 和化学信息学工作流：模型增益必须经受强经典表示、留出化学空间和来源变化的检验。

本文检验一个有边界的问题：在输入、15 个读出和线性残差头都相同的条件下，固定的无状态五比特储层特征映射，是否能在 22 个 TDC 端点、两种经典基线和两个外部迁移队列上，相对真实正交二次映射与随机 Fourier 特征产生增量？图 1 概括研究设计。本文有三项贡献。第一，将与 QRC 相关的残差模型定义为固定量子特征映射的无状态 QELM 极限，将其形式化为受限实二次函数族，并构造在输入维数、名义读出维数、拟合参数数量、随机映射预算和调参预算上匹配的对照。第二，在全部 22 个端点上使用验证门控和多重检验校正进行评价。第三，通过低数据、有限测量采样、模拟噪声、有限特征族搜索、双来源外部迁移、连续标签、独立 pIC50 回归和化学空间分析界定结论范围。

<img src="D:/论文/qrc_admet/outputs/Submission_Variants/JCIM/JCIM_Media_ZH/media/image1.png" title="Study-design schematic from molecular data and two classical bases through matched quantum, orthogonal, and Fourier branches to scaffold-level evidence; the lower band shows that 15 Pauli readouts form constrained real quadratic features." style="width:6.6in;height:4.34375in" alt="Study-design schematic from molecular data and two classical bases through matched quantum, orthogonal, and Fourier branches to scaffold-level evidence; the lower band shows that 15 Pauli readouts form constrained real quadratic features." />

图 1 匹配评价设计。两类数据共享两种经典基线、32 维 PCA 幅度输入、五映射残差集成和相同门控预算。主要比较为固定五比特 QRC/QELM 特征映射与参数匹配的真实正交二次映射。底部说明 15 个 Pauli 读出均构成受限实二次特征 q\_j(a)=a^T A\_j a。

# 2 相关工作

## 2.1 ADMET 基准与经典表示

TDC 的端点定义、固定测试集和评分接口支持结果核查，但公开官方测试集并非前瞻性验证。骨架划分比随机划分更严格，却仍可能保留近邻分子，不能替代时间留出 \[1-5\]。本文使用修正后的 MapLight 特征与 CatBoost 作为强经典参照 \[6,7,25,26\]：1,024 个 Morgan 计数、1,024 个 Avalon 计数、315 个 ErG 维度和 200 个 RDKit 描述符。上游计数转换使用 int8，可能发生溢出；重建特征缓存时改用 int32。近期评价表明，骨架划分仍可能相对温和，结构前沿留出会暴露更大的泛化失败 \[43\]，而有效的验证应明确并核查所模拟的部署分布偏移 \[44\]。

## 2.2 量子分子特征与结构对照

Beaulieu 等研究了固定储层和小样本分子活性学习 \[8\]。Benson 等将 Hamiltonian 导出的读出与经典描述符拼接后输入 CatBoost；Mansour 等报告了 AqSolDB 上量子启发预处理的误差 \[9,10\]。QCS-ADME 关注线路搜索及模拟器到硬件的迁移 \[11\]。Jia 等比较了五比特幅度编码残差与真实正交界分支，但联合训练编码器和预测头，且未覆盖 ADMET \[12\]。近期一项覆盖 48 个任务的效价预测基准未发现量子分类器相对经典对照的全局优势 \[27\]。Floquet-QRC 工作使用序列图事件和受驱储层，其输入与动力学设置不同 \[28\]。表 1 汇总这些研究；其任务、量子组件和训练协议不能支持单一分数排名。

近期精确模拟比较得到相似的边界：两点关联读出相对容量匹配的多项式模型没有增加信息，反馈储层在同调参预算的循环基线下也失去表面优势 \[32\]。另一项匹配复杂度研究在混沌预测中发现储层行为稳定，但其任务类别较窄，基线面板也不完整 \[33\]。中性原子硬件储层已在更大规模上得到演示，但尚未用于 ADMET \[34\]。

模型类别是另一条边界。本文对每个独立分子都从全新寄存器开始，分子之间不传播量子态。因此，这是 QRC/QELM 家族中的无状态 QELM 极限 \[35\]。QELM 的表达力受编码频率、观测量数量和测量局部性限制 \[36\]。Pauli 转移分析将表示与可解码性区分开 \[37\]；优化测量算子或改变读出方向，可能获得固定低阶 Pauli 读出无法访问的信息 \[38,39\]。有限纠缠可以形成有用的嵌入，却不意味着量子计算优势 \[45\]。

表 1 代表性 QML 分子性质研究及其与本文评价的关系。各研究的任务、编码和训练协议不能直接进行数值等同。

|               |                      |                               |                                    |
|---------------|----------------------|-------------------------------|------------------------------------|
| **研究**      | **分子场景**         | **量子/对照重点**             | **与本文基准的关系**               |
| Beaulieu 2025 | 活性；小样本         | 固定 QRC                      | 增加 22 个端点、两种基线和外部检验 |
| Benson 2026   | 10 个 TDC 任务       | Hamiltonian + CatBoost        | 不同混合模型；匹配残差检验         |
| Mansour 2026  | AqSolDB              | 互信息 Hamiltonian + CatBoost | 多项式消融支持匹配二次对照         |
| Zheng 2026    | 8 个分类 + 4 个回归  | 线路搜索                      | 搜索与固定匹配比较                 |
| Jia 2026      | 3 个受体效价任务     | 联合编码器 + 量子残差         | 正交对照表现相近                   |
| Garg 2026     | 10 个靶标；48 个任务 | QSVM 与 VQC                   | 无全局优势；局部稀疏信号           |
| Wang 2026     | 图前缀；能隙         | Floquet QRC                   | 序列输入与硬件；非 ADMET 全端点    |

本文的主要对照直接来自模型表示。对于实幅度输入，固定演化后的每个 Z 或 ZZ 期望都是实二次型。真实正交映射产生另一组二次型，输入、读出数量和拟合参数数量相同，因此可检验储层几何的差异，而不仅是“加入非线性特征”本身。随机 Fourier 特征 \[24\] 提供第二个 15 维非线性对照。三种特征族均平均五个独立映射，验证过程没有给任何一族额外候选。

## 2.3 验证门控与端点级报告

折外偏移、由验证集估计的堆叠权重以及端点级报告已有先例 \[14-16\]。Ark-ADMET 在 22 个 TDC 端点上通过内部验证选择表示和融合权重 \[16\]。Robinson 等在 Journal of Computer-Aided Molecular Design 中重新分析了一项大规模生物活性模型比较，表明评价设计能够改变模型结论 \[31\]。本文对 QRC 和两种经典特征族采用相同的五映射平均和标量门控规则。测试标签不参与映射生成、残差拟合或权重选择。重复拟合共享固定外层测试集，因此推断按测试骨架配对 \[17\]。

等价声明需要足够的研究设计，而不能依赖不显著检验。采用 随机种子级 TOST 并明确功效分析，才能使等价主张可检验 \[40\]。近期匹配 QML 基准在量子与经典模型使用相同输入、划分和调参预算时，至多报告持平 \[41\]；分子析因基准则显示表示效应可能大于模型效应 \[42\]。这些结果为本文分别报告 QRC 对正交和 QRC 对基线的比较提供依据。

# 3 数据、划分与统计评价

本文从 Harvard Dataverse 文件 4426004 获取官方 TDC ADMET 归档，SHA-256 为 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1。22 个端点包含 65,430 条官方训练/验证记录和 16,379 条带标签测试记录。13 个分类端点采用 AUROC 或 AUPRC；9 个回归端点采用 MAE 或 Spearman 相关 \[2\]。

对每个端点，使用 PyTDC 骨架流程和种子 1-5，将官方 train\_val 表划分为 87.5% 训练集和 12.5% 验证集。官方测试集成员、标签和行顺序保持不变。全部 SMILES 均成功解析，规范非异构身份和 Bemis-Murcko 骨架在训练、验证和测试集之间均不相交 \[22\]。每个外层训练集内部使用三个骨架折生成折外基线偏移。配置冻结后才生成测试结果。

主要效应由未舍入预测计算：先对每个种子评分，再平均五个种子。对 AUROC、AUPRC 和 Spearman，效应为新方法减参照；对 MAE，效应为参照减新方法；正值始终表示改进。使用 1,000 次配对骨架 bootstrap 重采样得到 95% 区间，使用 1,999 次配对骨架置换开展主要检验，并在每个基线内对 22 个端点进行 Holm 校正 \[18-20\]。

探索性 TOST 对 AUROC、AUPRC 和 Spearman 使用 0.01 的实际边界，对 MAE 使用基线 MAE 的 2%。这些边界是基准解释阈值，不是临床限制。TOST 包含两个单侧检验。仅当 90% 置信区间位于预设边界内，且 Holm 校正后的等价检验显著时，才称结果为实际等价。结果分为三种状态：Holm 显著负差表示显著退化，Holm 显著正差表示改进，显著等价检验表示实际统计等价；其余均为未决。等价不意味着机制相同或逐分子预测相同。

事后随机种子级功效诊断表明，五个划分随机种子不足以在 +/-0.01 的指标边界内为单个端点提供高功效等价证明。TOST 结果仍属探索性，按等价计数报告，不作为确证性主张。

补充表 S1 报告端点样本量、官方指标和标签摘要；表 S2 列出主要、次要、敏感性、外部和探索性分析的层级；表 S9 报告紧、主和宽边界下的 TOST 计数。图 2 展示 TDC、hERG 和 B3DB 队列的化学空间与物理化学背景。

<img src="D:/论文/qrc_admet/outputs/Submission_Variants/JCIM/JCIM_Media_ZH/media/image2.png" title="Chemical-space projection and molecular-weight, cLogP, and TPSA distributions for TDC, external hERG, and B3DB molecules." style="width:6.3in;height:5.51389in" alt="Chemical-space projection and molecular-weight, cLogP, and TPSA distributions for TDC, external hERG, and B3DB molecules." />

图 2 化学空间与适用域背景。(A) 使用 20 分量截断 SVD、标准化和二维 PCA 投影 Morgan 半径 2、1024 位指纹。TDC 和 B3DB 分别随机抽取 3,000 和 500 个唯一分子；全部 293 个 hERG 分子均被使用。(B-D) 全部唯一 TDC、hERG 和 B3DB 分子的分子量、cLogP 和 TPSA 分布。为提高可读性，箱线图省略离群点标记。

# 4 方法

## 4.1 经典基线与折外偏移

Morgan-ExtraTrees \[23\] 使用 512 位半径 2 Morgan 指纹、128 棵树、最小叶节点规模 2 和平方根特征子采样。回归保留原始标签尺度；分类输出类别 1 概率。每个外层划分使用独立种子训练。最终测试基线在完整外层训练集上重新拟合，折外预测仅用于残差拟合。

MapLight-CatBoost 使用修正后的 2,563 维表示，迭代 240 次、深度 6、学习率 0.06。分类使用 Logloss，回归使用 MAE。半衰期、VDss 和两个清除率端点采用 MapLight 协议的目标对数变换；其他回归保持原始尺度。CatBoost 原生处理缺失值。两种基线共享外层划分和内部骨架折 \[25,26\]。

## 4.2 五比特无状态特征映射与匹配经典特征

本文仅用训练集拟合标准器和 32 维 PCA，对每个 PCA 向量归一化后以幅度编码载入五个量子比特。固定 Hamiltonian 包含独立采样的横场、纵场和环形近邻 ZZ 耦合，尺度系数分别为 0.4、0.7 和 0.25，演化时间为 0.5；并显式检查 厄米性。五个单比特 Z 期望和十个 ZZ 期望构成 15 维特征。线路和读出采用精确态矢量模拟；零向量映射到全零计算基态。精确模拟是有意设置的控制条件，用于分离固定线路、编码和读出的表达行为。否则，物理门误差、读出误差、串扰和连接性会混淆结构比较。有限测量采样 和去极化分析是敏感性检验，不是硬件验证；物理设备执行留待后续独立研究。由于每个分子都从全新寄存器开始，该实现是无状态固定量子特征映射，而非用于序列的有记忆 QRC \[35\]。

五个量子比特支持 32 个实幅度，因此 32 维 PCA 是在该规模下无截断、无填充的最小完整幅度输入。15 个读出由五个单比特 Z 期望和全部十个两两 ZZ 期望组成。这不是硬件容量主张，而是一个封闭设计，允许精确态矢量评价、相同维数的经典对照和五个完整映射实现。对于归一化 PCA 向量 v，幅度为 a\_j = v\_j / \|\|v\|\|。Hamiltonian H 和演化 U = exp(-iHt) 固定，不以测试标签训练。PCA 维数和读出集合保持固定，以免在主基准中再引入容量搜索。

对于输入幅度 a、读出算子 D\_j 和固定演化 U，

*q*<sub>*j*</sub>(*a*) = (*U**a*)<sup>†</sup>*D*<sub>*j*</sub>(*U**a*) = *a*<sup>*T*</sup>*R**e*(*U*<sup>†</sup>*D*<sub>*j*</sub>*U*)*a*.

命题 1。对于任意固定的一组 15 个对角 Pauli 可观测量 D\_j 和任意固定酉矩阵 U，归一化 32 维实输入 a 的读出满足 q\_j(a)=a^T A\_j a，其中 A\_j=Re(U^dagger D\_j U)。这些 15 个特征的任意仿射读出均可写成 a^T M a+b，其中截距并入 b。使用线性残差头的固定五比特储层特征映射属于这一模型族，并受至多 15 个实二次型约束。证明可由展开 (Ua)^dagger D\_j (Ua) 得到。该命题并不表示 QRC 与某个特定真实正交映射等价，而是界定当前编码和读出可用的函数类。它只定义名义函数族，不表示可解码性相同。Pauli 转移和读出方向分析表明，相同秩或观测量数量仍可能使不同任务相关信息具有不同的可访问性 \[37-39\]。本文将真实正交族描述为在输入维数、名义读出维数、拟合参数数量、随机映射预算和调参预算上匹配，而不称其具有完全相同的容量。主分析还将读出固定在五个 Z 和全部十个 ZZ 观测量；优化测量算子和相互作用消融不属于主比较。

QRC 衍生特征、真实正交二次特征和随机 Fourier 特征分别使用五个独立映射，种子为 20261101-20261105。真实正交对照将 U 替换为随机实正交矩阵，并保留相同的 15 个读出。随机 Fourier 对照使用 15 个余弦特征。所有特征族共享相同 PCA 输入、训练侧标准化和线性残差头：分类使用 L2=1 的 logistic 偏移回归，回归使用 alpha=10 的岭回归。验证门控和测试评价前先平均五个映射的残差。

## 4.3 验证匹配与端点级门控

对于每个端点、基线、外层种子和候选特征族，设 f\_0(x) 为基线预测，Delta\_m(x) 为特征族 m 的五映射平均残差。门控预测为

*f*<sub>*m*</sub><sup>gate</sup>(*x*) = *f*<sub>0</sub>(*x*) + *α*<sub>*m*</sub>*Δ*<sub>*m*</sub>(*x*), *α**ₘ* ∈ {0, 0.25, 0.5, 0.75, 1}.

验证集在端点指标上从 {0, 0.25, 0.5, 0.75, 1} 选择标量权重，并列时选择较小权重。分类对 logit 施加门控，回归直接作用于预测值。QRC 和每个经典特征族使用相同权重网格和五映射预算。主要比较为未门控 QRC 对真实正交二次映射；Fourier 和门控比较为次要分析。

全部特征变换、折外偏移、残差头和门控权重均在相应训练集或验证集内拟合。配置锁定后，测试集仅用于最终预测和官方指标。主研究包含 22 个端点 × 5 个外层种子 × 2 种基线 = 220 条基线流程；每条流程包含三次折外拟合和一次完整训练拟合。

## 4.4 基准校准与归因

为检验评价能否恢复已知的储层特异信号并拒绝已知经典信号，本文在 hERG、B3DB BBB 和 AqSolDB 溶解度上增加特征阶段校准。真实分子输入投影至 32 维，并经过相同的五个 QRC、正交和 Fourier 映射抽样。生成 QRC 派生、正交派生和无信号目标，在固定训练划分上训练相同的 15 维头，平均五个映射预测，并评价留出恢复情况。该校准隔离特征比较，有意省略经典基线偏移。

本文还将每个 QRC 对基线的端点效应分解为匹配经典非线性项和 QRC 特异项；评价验证集选择的映射以量化选择乐观；对全部 220 个任务-基线-划分组合计算有效秩、条件数和中心核对齐；并按外部分子与 TDC 的最近邻相似度四分位分层。相关结果见补充表 S12-S16 和图 S6-S10。

校准目标用于检验评价的敏感性和特异性。它们不是生物端点，也不用于推断新的 ADMET 机制。

# 5 结果

## 5.1 总体结果

表 2 报告两种基线和未门控分支的五种子平均官方指标。相对固定的真实正交对照，ExtraTrees 的 6 个端点支持 QRC，16 个端点支持匹配对照；CatBoost 的 3 个端点支持 QRC，19 个端点支持匹配对照。修正后的 CatBoost 基线本身在 21/22 个端点上优于 ExtraTrees，例外为 CYP2C9 底物 的 AUPRC。早期试点中方向最一致的四个端点没有稳定复现：ExtraTrees 相对基线仅在 Caco2 和 LD50 为正，CatBoost 仅 hERG 轻微为正。对正交映射，任一基线最多 2/4 个为正，且没有一个通过多重检验校正。

表 2 两种基线和未门控分支的五种子平均官方指标。

|                     |          |        |            |             |        |            |             |
|---------------------|----------|--------|------------|-------------|--------|------------|-------------|
| **端点**            | **指标** | **ET** | **QRC-ET** | **Orth-ET** | **CB** | **QRC-CB** | **Orth-CB** |
| Caco-2              | MAE      | 0.469  | 0.463      | 0.468       | 0.296  | 0.318      | 0.306       |
| 肠道吸收 HIA        | AUROC    | 0.896  | 0.856      | 0.890       | 0.980  | 0.972      | 0.978       |
| P-糖蛋白            | AUROC    | 0.912  | 0.893      | 0.913       | 0.927  | 0.932      | 0.936       |
| 生物利用度          | AUROC    | 0.612  | 0.595      | 0.643       | 0.722  | 0.694      | 0.715       |
| 亲脂性              | MAE      | 0.796  | 0.798      | 0.795       | 0.576  | 0.581      | 0.577       |
| 水溶性              | MAE      | 1.402  | 1.438      | 1.425       | 0.844  | 0.871      | 0.844       |
| 血脑屏障 BBB        | AUROC    | 0.878  | 0.864      | 0.881       | 0.913  | 0.905      | 0.917       |
| 血浆蛋白结合率 PPBR | MAE      | 10.131 | 10.009     | 9.847       | 7.880  | 8.428      | 8.303       |
| 稳态分布容积 VDss   | Spearman | 0.490  | 0.260      | 0.373       | 0.703  | 0.416      | 0.452       |
| CYP2C9 抑制         | AUPRC    | 0.725  | 0.714      | 0.721       | 0.771  | 0.770      | 0.772       |
| CYP2D6 抑制         | AUPRC    | 0.642  | 0.638      | 0.640       | 0.707  | 0.706      | 0.706       |
| CYP3A4 抑制         | AUPRC    | 0.823  | 0.824      | 0.824       | 0.869  | 0.869      | 0.870       |
| CYP2C9 底物         | AUPRC    | 0.381  | 0.382      | 0.384       | 0.355  | 0.348      | 0.345       |
| CYP3A4 底物         | AUROC    | 0.622  | 0.612      | 0.626       | 0.658  | 0.662      | 0.665       |
| CYP2D6 底物         | AUPRC    | 0.634  | 0.658      | 0.643       | 0.714  | 0.684      | 0.721       |
| 半衰期              | Spearman | 0.312  | 0.299      | 0.242       | 0.553  | 0.143      | 0.203       |
| 肝细胞清除率        | Spearman | 0.363  | 0.358      | 0.348       | 0.459  | 0.449      | 0.454       |
| 微粒体清除率        | Spearman | 0.523  | 0.499      | 0.518       | 0.596  | 0.599      | 0.598       |
| LD50                | MAE      | 0.660  | 0.658      | 0.660       | 0.647  | 0.654      | 0.645       |
| hERG                | AUROC    | 0.810  | 0.807      | 0.809       | 0.853  | 0.853      | 0.856       |
| AMES                | AUROC    | 0.835  | 0.822      | 0.834       | 0.855  | 0.850      | 0.854       |
| DILI                | AUROC    | 0.796  | 0.776      | 0.790       | 0.894  | 0.870      | 0.894       |

表 3 经 Holm 校正的 QRC 对匹配真实正交映射的端点效应。

|                     |          |                           |               |                           |               |
|---------------------|----------|---------------------------|---------------|---------------------------|---------------|
| **端点**            | **指标** | **ET 效应 \[95% CI\]**    | **ET Holm p** | **CB 效应 \[95% CI\]**    | **CB Holm p** |
| Caco-2              | MAE      | +0.005 \[-0.009, +0.017\] | 1.000         | -0.012 \[-0.025, -0.001\] | 0.646         |
| 肠道吸收 HIA        | AUROC    | -0.034 \[-0.068, -0.004\] | 1.000         | -0.006 \[-0.019, +0.001\] | 1.000         |
| P-糖蛋白            | AUROC    | -0.020 \[-0.046, +0.003\] | 1.000         | -0.004 \[-0.014, +0.004\] | 1.000         |
| 生物利用度          | AUROC    | -0.048 \[-0.093, -0.002\] | 1.000         | -0.021 \[-0.056, +0.006\] | 1.000         |
| 亲脂性              | MAE      | -0.002 \[-0.007, +0.003\] | 1.000         | -0.004 \[-0.007, -0.000\] | 0.503         |
| 水溶性              | MAE      | -0.013 \[-0.035, +0.006\] | 1.000         | -0.027 \[-0.038, -0.016\] | 0.011         |
| 血脑屏障 BBB        | AUROC    | -0.017 \[-0.032, -0.003\] | 0.480         | -0.012 \[-0.024, -0.004\] | 0.230         |
| 血浆蛋白结合率 PPBR | MAE      | -0.162 \[-0.324, -0.005\] | 1.000         | -0.125 \[-0.236, -0.015\] | 0.639         |
| 稳态分布容积 VDss   | Spearman | -0.113 \[-0.168, -0.053\] | 0.042         | -0.037 \[-0.130, +0.060\] | 1.000         |
| CYP2C9 抑制         | AUPRC    | -0.007 \[-0.014, +0.001\] | 1.000         | -0.001 \[-0.003, +0.001\] | 1.000         |
| CYP2D6 抑制         | AUPRC    | -0.002 \[-0.006, +0.004\] | 1.000         | +0.000 \[-0.003, +0.004\] | 1.000         |
| CYP3A4 抑制         | AUPRC    | +0.000 \[-0.002, +0.003\] | 1.000         | -0.000 \[-0.002, +0.001\] | 1.000         |
| CYP2C9 底物         | AUPRC    | -0.002 \[-0.046, +0.033\] | 1.000         | +0.003 \[-0.022, +0.025\] | 1.000         |
| CYP3A4 底物         | AUROC    | -0.015 \[-0.039, +0.008\] | 1.000         | -0.003 \[-0.020, +0.015\] | 1.000         |
| CYP2D6 底物         | AUPRC    | +0.015 \[-0.022, +0.045\] | 1.000         | -0.036 \[-0.063, -0.007\] | 0.052         |
| 半衰期              | Spearman | +0.057 \[-0.016, +0.127\] | 1.000         | -0.060 \[-0.188, +0.071\] | 1.000         |
| 肝细胞清除率        | Spearman | +0.010 \[-0.018, +0.047\] | 1.000         | -0.005 \[-0.072, +0.049\] | 1.000         |
| 微粒体清除率        | Spearman | -0.019 \[-0.047, +0.009\] | 1.000         | +0.001 \[-0.030, +0.040\] | 1.000         |
| LD50                | MAE      | +0.003 \[-0.009, +0.018\] | 1.000         | -0.009 \[-0.021, +0.001\] | 1.000         |
| hERG                | AUROC    | -0.002 \[-0.030, +0.027\] | 1.000         | -0.003 \[-0.024, +0.020\] | 1.000         |
| AMES                | AUROC    | -0.012 \[-0.017, -0.006\] | 0.011         | -0.005 \[-0.010, -0.000\] | 0.784         |
| DILI                | AUROC    | -0.014 \[-0.062, +0.034\] | 1.000         | -0.024 \[-0.052, +0.001\] | 1.000         |

表 3 的效应已作方向统一化，正值支持 QRC；方括号为配对 95% 骨架 bootstrap 区间。Holm 校正在每个基线内覆盖 22 个端点。三个 Holm 显著结果均支持正交映射：ExtraTrees 的 AMES（AUROC 差 -0.0115，Holm p=0.011）、ExtraTrees 的 VDss（Spearman 差 -0.1127，Holm p=0.042）和 CatBoost 的溶解度（MAE 差 -0.0268，Holm p=0.011）。没有任何端点显著为正。

## 5.2 端点级门控

验证门控在 ExtraTrees 的 47/110 次选择中将 QRC 权重设为零，在 CatBoost 中为 55/110 次。门控 QRC 对相同规则门控的正交映射，在 ExtraTrees 上 11 个端点支持 QRC、11 个端点支持正交；CatBoost 上 4 个支持 QRC、17 个支持正交、1 个持平。两种基线均未产生 Holm 显著正向端点。探索性等价分别覆盖 8 和 10 个端点，但其中若干结果源于两个分支都被退回基线模型，不能作为量子贡献证据。

表 4 验证门控的代表性行为。

|          |                     |          |                       |                              |            |
|----------|---------------------|----------|-----------------------|------------------------------|------------|
| **基线** | **端点**            | **指标** | **QRC 门控权重**      | **门控 QRC−正交 \[95% CI\]** | **Holm p** |
| ET       | 半衰期              | Spearman | 0/0.5/1/0.5/1         | +0.062 \[+0.001, +0.117\]    | 0.940      |
| ET       | 血浆蛋白结合率 PPBR | MAE      | 0.75/0.75/0.25/1/0.75 | -0.153 \[-0.260, -0.046\]    | 0.242      |
| ET       | AMES                | AUROC    | 0.5/0/0.25/0/0        | -0.001 \[-0.002, -0.000\]    | 0.940      |
| CB       | 半衰期              | Spearman | 0/0/0/0/0             | +0.000 \[+0.000, +0.000\]    | 1.000      |
| CB       | 血浆蛋白结合率 PPBR | MAE      | 0.25/0/0/0/0          | -0.023 \[-0.045, -0.002\]    | 0.510      |
| CB       | 水溶性              | MAE      | 0.25/0.25/0/0/0.25    | -0.001 \[-0.004, +0.002\]    | 1.000      |

小效应端点表明，门控限制了负迁移，却没有产生新的外推能力。在 ExtraTrees 上，半衰期 门控后改善 0.0616，但 Holm p=0.94；PPBR 仍为 -0.1531。在 CatBoost 上，五个种子均将 半衰期 的 QRC 权重设为零，差异恰为零；溶解度在五划分中的三个划分选择零权重，保留差异为 -0.0010。

## 5.3 其他比较

表 5 各端点上的方向计数和 Holm 显著计数。

|                       |              |              |                   |                   |
|-----------------------|--------------|--------------|-------------------|-------------------|
| **比较**              | **QRC 更好** | **QRC 更差** | **Holm 显著正向** | **Holm 显著负向** |
| ET：QRC − 正交        | 6            | 16           | 0                 | 2                 |
| CB：QRC − 正交        | 3            | 19           | 0                 | 1                 |
| ET：QRC − Fourier     | 3            | 19           | 0                 | 1                 |
| CB：QRC − Fourier     | 3            | 19           | 0                 | 1                 |
| ET：QRC − 基线        | 6            | 16           | 0                 | 2                 |
| CB：QRC − 基线        | 4            | 18           | 0                 | 5                 |
| ET：门控 QRC − 正交   | 11           | 11           | 0                 | 0                 |
| CB：门控 QRC − 正交   | 4            | 17           | 0                 | 0                 |
| ET：QRC + 正交 − 正交 | 12           | 10           | 0                 | 0                 |
| CB：QRC + 正交 − 正交 | 6            | 14           | 0                 | 0                 |

QRC 对随机 Fourier 特征时，两种基线均得到 3 个支持 QRC、19 个支持对照的端点估计。相对无残差基线，ExtraTrees 有 6/16 个端点支持 QRC，CatBoost 有 4/18 个，分别有 2 个和 5 个 Holm 显著负向端点。不同单位的指标未跨端点平均。

将每个 QRC 映射索引与对应的真实正交映射配对后，端点内出现可见变异，但没有形成稳定正向的任务子集。完整逐映射指标和预测见复现包。

允许 QRC 与正交界分支同时进入模型，并在验证集选择两个标量权重时，ExtraTrees 对相同规则门控正交特征的估计为 12 个支持 QRC、10 个支持对照；CatBoost 为 6/14，另有 2 个持平。没有 Holm 显著正向端点。相对无残差基线，联合模型在 ExtraTrees 上为 10 个更好、12 个更差，包含一个显著正向和一个显著负向端点；CatBoost 为 7 个更好、14 个更差、1 个持平，没有显著改善。联合门控未提供可迁移的 QRC 互补信息。

有限测量采样 面板覆盖 BBB、hERG、Caco2、LD50、PPBR、DILI、CYP2D6 抑制 和 VDss。每个 Pauli 读出分别在 1,024、4,096 和 16,384 次测量采样下独立模拟，并在采样特征上重新训练残差头。QRC 对门控正交特征，在 ExtraTrees 的三个 测量采样预算下均为 5/3；CatBoost 依次为 2/6、1/7 和 1/7。增加 测量采样 使 CatBoost 的方向计数趋近精确模拟结果，而没有出现光照预算依赖性收益。

## 5.4 低数据缩放

为检验 QRC 理论动机最明显的数据条件，本文在外层训练集的 5%、10%、20%、40% 和 100% 上使用相同的八个代表端点。每个子集至少包含 96 条记录，使三个内部骨架折仍可估计；每个结果均记录实际样本数。子集仅从外层训练数据抽取，验证集和测试集成员保持固定。

未门控 QRC 优于正交映射的端点数，在 ExtraTrees 上依次为 2/8、0/8、1/8、0/8 和 2/8；CatBoost 上依次为 1/8、0/8、1/8、0/8 和 1/8。20% 训练数据时，验证门控使 ExtraTrees 达到 6/8 正向端点，但 CatBoost 相应为 4/8；其他数据规模未在两种基线之间产生同步正向变化。门控结果表示风险控制，而非低数据量子优势。端点曲线见补充图 S1。

## 5.5 独立外部迁移队列

外部迁移检验使用 ToxTree hERG 测试集和 B3DB BBB 分类集 \[29,30\]；两者均非前瞻性队列。hERG 使用原二分类阈值 pIC50 &gt;= 4.5；删除 TDC hERG 训练或测试中已有的规范分子身份后，保留 293 个分子。B3DB 使用提供方的 BBB+/BBB- 标签；删除与 TDC BBB 重叠的规范分子后，保留 2,317 个分子。DeepChem ESOL 与 TDC AqSolDB 几乎共享全部规范分子，仅剩 18 条非重叠记录，被排除。

在外部 hERG 上，门控 QRC 减门控正交的 AUROC 为 ExtraTrees +0.0112（95% CI \[-0.0029, 0.0246\]，Holm p=0.200），CatBoost 为 +0.0402（\[0.0221, 0.0591\]，Holm p=0.002）。在 B3DB BBB 上，同一效应为 ExtraTrees -0.0046（\[-0.0076, -0.0019\]，Holm p=0.002），CatBoost -0.0034（\[-0.0065, -0.0006\]，Holm p=0.016）。联合门控呈相同分化：CatBoost 在 hERG 为 +0.0298，而两种基线在 BBB 上均为 Holm 显著负向。hERG 信号与 BBB 负迁移并存，表明来源依赖，而非普遍可迁移优势。完整外部区间见补充图 S2。

图 3 利用已有预测分离 QRC 增益与正交界分支退化。对 CatBoost/hERG，门控 QRC 减无残差基线为 +0.0285 AUROC（95% CI \[0.0137, 0.0437\]），而门控正交减基线为 -0.0117（\[-0.0216, -0.0011\]）；+0.0402 的主差异同时包含 QRC 增益和正交分支下降。hERG 的 QRC 减正交 AUPRC 差为 +0.0304，Brier 分数和对数损失改善分别为 +0.0038 和 +0.0363。两个 hERG 分支的校准均较差，校准斜率为约 0.15-0.26。B3DB 中，QRC 减正交 AUPRC 在 ExtraTrees 和 CatBoost 上分别为 -0.0047 和 -0.0061，Brier 分数与对数损失差异不支持 QRC。完整分解和校准值见补充表 S7、S8。连续标签排序迁移的 CatBoost/hERG pIC50 Spearman 差为未校正的 +0.043，未通过 12 项比较的 Holm 校正，也未在 BBB logBB 中复现。它并非独立训练的回归评价，且 B3DB 连续值子集有 86.8% 为阳性。

<img src="D:/论文/qrc_admet/outputs/Submission_Variants/JCIM/JCIM_Media_ZH/media/image3.png" title="External hERG and B3DB effect decomposition and CatBoost calibration curves." style="width:6.25in;height:5.22431in" alt="External hERG and B3DB effect decomposition and CatBoost calibration curves." />

图 3 外部分类的效应分解与校准。(A-B) 门控 QRC 对基线、门控正交对基线以及门控 QRC 对门控正交的 AUROC 差；正值支持前者。(C-D) 按预测五分位计算五个种子平均的 CatBoost 校准曲线；虚线对角表示完美校准。分解用于解释主比较，不能替代预设的外部 AUROC 检验。

## 5.6 模拟退相干

作为受控噪声压力测试，本文在相同八个端点上加入概率为 0.001、0.005 和 0.010 的局域单比特去极化噪声，并固定 4,096 次测量采样。对称去极化将 Z 期望乘以 lambda=1-4p/3，将 ZZ 期望乘以 lambda^2；残差头在含噪特征上重新训练。模型不包含门专用误差、泄漏、串扰和硬件连接性，仅检验对受控读出幅度衰减的敏感性。

三个噪声水平下，QRC 对门控正交特征在 ExtraTrees 上始终为 5/3，在 CatBoost 上始终为 1/7。相对无残差基线，ExtraTrees 为 3/5，CatBoost 为 2/6。去极化概率从 0.001 增至 0.010 未导致方向反转。敏感性结果见补充图 S3。

## 5.7 有限储层族搜索

为回应“仅测试了一个储层”的可能，本文预设五组固定参数族：baseline、weak、strong、short 和 long。每族包含五个独立量子映射。并构造五组真实正交候选，每组同样含五个独立映射。每个候选形成五映射残差集成，TDC 验证集选择门控权重。QRC 和正交族在测试前具有相同候选预算和映射预算。

在八个代表端点上，ExtraTrees 有 4 个端点选择 QRC 搜索、4 个端点选择匹配正交搜索；CatBoost 有 2 个端点选择 QRC 搜索、5 个端点选择正交搜索、1 个端点持平。没有 Holm 显著正向端点。baseline（基线）配置仍是最常被选择的 QRC 设置（ExtraTrees 15/40，CatBoost 25/40），说明扩大特征族没有揭示新的稳定信号。相对无残差基线，相应计数仍为 ExtraTrees 4/4、CatBoost 2/5/1；VDss 在两种基线上均显著更差。这降低了“调参不足导致零结果”的可能。

<img src="D:/论文/qrc_admet/outputs/Submission_Variants/JCIM/JCIM_Media_ZH/media/image4.png" title="Endpoint-level paired differences of ungated QRC versus matched orthogonal quadratic features across all 22 TDC ADMET endpoints." style="width:6.22014in;height:6.65347in" alt="Endpoint-level paired differences of ungated QRC versus matched orthogonal quadratic features across all 22 TDC ADMET endpoints." />

图 4 未门控 QRC 对匹配真实正交映射的端点级差异。分类指标采用绝对单位，MAE 采用参照 MAE 的相对百分比，Spearman 采用绝对单位。区间为 95% 骨架簇 bootstrap 区间；红色表示 Holm 显著。

## 5.8 独立连续 hERG 回归

为避免将二分类器的排序保留误作连续值预测，本文增加固定的 ToxTree hERG pIC50 回归。删除 TDC 重叠后，将来源开发集（Dev）按 Bemis-Murcko 骨架划分为 6,895 个训练分子和 985 个验证分子。过滤来源测试集以删除 TDC 重叠及与外部 开发集（Dev）共享的骨架，保留 214 个测试分子和 155 个骨架。QRC、正交二次、随机 Fourier 与线性残差头遵循 TDC 协议。外部测试标签不用于选择映射种子、PCA 维数、正则化或超参数。

五个模型种子均未显示经确认的 QRC 增量。QRC 减正交的 Spearman 差，ExtraTrees 为 +0.0229（95% CI \[-0.0121, 0.0608\]），CatBoost 为 +0.0093（\[-0.0168, 0.0325\]）；QRC 减 CatBoost 基线为 +0.0292（\[-0.0034, 0.0604\]）。MAE 差异接近零。对全部 12 个指标、基线和对照比较进行 Holm 校正后，没有显著结果。该队列独立于 TDC 标签，但仅有 214 个分子，不能单独提供高功效验证。完整结果见补充图 S4 和补充表 S10。

## 5.9 电路级 Aer 审计

电路级审计在显式生成的 Qiskit 线路上考察读出保真度：32 维幅度制备、八步 Lie-Trotter 固定 Hamiltonian 演化和全量子比特 Z 基测量。面板覆盖八个代表端点、每端点 32 个分层测试态和五个储层映射；转译后的线路深度为 81，约 136 个操作。Aer 密度矩阵模拟包含单双比特门去极化误差及独立读出翻转。相对精确矩阵读出，低、中、高误差下归一化 RMSE 分别为 0.189-0.199、0.337-0.351 和 0.551-0.569。信号斜率约为 0.81、0.66 和 0.45，而 Spearman 相关分别为 0.9974-0.9986、0.9916-0.9958 和 0.9742-0.9866。无噪 Trotter 化 RMSE 为 0.0058-0.0070。线路误差主要收缩读出幅度，同时保留较强相对排序。这是读出保真度审计，不是在含噪特征上端到端重新训练的实验。完整结果见补充图 S5 和补充表 S11。

## 5.10 基准校准与来源诊断

已知信号校准区分了三类特征来源。对 QRC 派生目标，QRC 减正交的测试表现中，ExtraTrees 为 +0.302、CatBoost 为 +0.190；两个基线中，预期 QRC 族均在 150/150 次模拟中排名第一（100.0%）。对正交派生目标，同一比较反转为 -0.332 和 -0.238，预期正交族在 ExtraTrees 和 CatBoost 上均为 149/150 次模拟排名第一（99.3%）。对零信号目标，双侧配对置换检验在 ExtraTrees 的 7/150 次模拟（4.7%）和 CatBoost 的 3/150 次模拟（2.0%）中显著。

效应分解说明了匹配对照为何改变解释。在 ExtraTrees 的 6 个 QRC 相对基线点估计为正的端点中，有 2 个在扣除匹配正交贡献后 QRC 特异效应不再为正；CatBoost 的 4 个此类端点中有 3 个被中和。验证集选择的 QRC 在 ExtraTrees 13/22、CatBoost 12/22 个端点上优于同样由验证集选择的正交特征，呈接近平衡的模式，而非跨基线优势。

容量诊断显示，固定 QRC 映射没有被人为设置为低参数化：在 15 维特征上，ExtraTrees 的平均测试有效秩为 14.10 对 14.62，CatBoost 为 12.82 对 14.25。外部来源分层在中部相似度四分位保留了 hERG 局部方向，但未在相邻四分位或 B3DB BBB 中一致出现。综合来看，这些对照支持有边界的评价结论，而不是模型排名主张。

# 6 讨论

## 6.1 受限二次映射解释了什么

对于实幅度输入，固定演化后的每个 Z 或 ZZ 期望都是实对称二次型。训练侧标准化是仿射特征变换，因此线性读出只组合这些二次型并加入固定偏移。给定拟合参数后，量子残差可由归一化 32 维潜变量输入上的一个实二次型和常数复现。该结构作用于潜变量空间，而不作用于原始分子图。五个 QRC 读出矩阵的秩均为 15，条件数中位数为 1.210；真实正交读出矩阵的秩为 15，条件数为 1.000。在留出分子特征上，有效秩在 ExtraTrees 上为 14.10 对 14.62，在 CatBoost 上为 12.82 对 14.25；线性中心核对齐分别为 0.20 和 0.30。两类分支具有相同的输出维数和拟合参数数量、不同的几何，以及相近但不完全相同的有效特征容量。

真实正交二次映射在 ExtraTrees 16/22、CatBoost 19/22 个端点上具有更低的点估计误差。对五个随机实现取平均后，结果不支持固定 Ising 储层几何比一般二次映射更适合 ADMET 的假设。这与近期一项跨靶标 QML 基准一致：局部候选信号没有形成全局优势 \[27\]。结论仅适用于当前五比特幅度编码、读出和精确模拟 \[12,13,28\]。该结果也与匹配 QRC 比较一致：关联读出相对容量匹配多项式和同调参循环对照的优势消失 \[32\]；而正向缩放结果仍仅局限于混沌预测任务和较窄的基线面板 \[33\]。

## 6.2 门控何时减少退化

门控的主要收益来自阻止有害残差，而非发现可迁移的量子修正。CatBoost 在所有端点-划分决策中有一半将 QRC 权重设为零，且 17 个端点估计仍低于同规则门控的正交界分支。若干端点的差异接近零并落入探索性等价边界，但这与量子分支被抑制一致，不能替代正向优势检验。门控是风险控制规则，不是分子级置信度估计。

## 6.3 强基线与外部队列揭示了什么

强基线比较提供了直接压力测试。MapLight-CatBoost 在 21/22 个端点上优于 Morgan-ExtraTrees，但 QRC 的相对优势没有在更强基线上保留。联合门控、有限测量采样、低数据缩放和模拟噪声均未揭示可迁移的量子修正。电路级审计同样显示读出幅度衰减，未增加优势证据。

外部结果仅支持 hERG 上的来源特异候选。同一方向也出现在 pIC50 排序迁移和独立回归中，但两者均未通过联合多重校正。B3DB logBB 迁移接近零，B3DB BBB 分类又出现显著退化，因此 hERG 结果不能跨来源推广。未来量子编码应在强基线上测试，并匹配输入维数、名义读出维数、拟合参数数量和候选预算；现有结果不支持将其视为通用 ADMET 描述符。两个队列用于考察不同化学空间与标签机制，并不对应单一部署场景 \[44\]。

## 6.4 化学空间与来源依赖

描述性化学空间审计用于判断队列差异是否反映来源邻近性。两个队列均已删除各自 TDC 归档中的精确规范身份。hERG 的 293 个分子中有 23 个（7.8%）保留了出现在 TDC 训练/验证集中的 Bemis-Murcko 骨架；到 TDC 训练/验证分子的最近 Morgan Tanimoto 相似度（半径 2，2048 位）中位数为 0.234，第 90 百分位为 0.423。B3DB BBB 的 2,317 个分子中有 562 个（24.3%）共享 TDC 训练/验证骨架，最近相似度中位数为 0.346，第 90 百分位为 0.722。B3DB 阳性率为 48.9%，完整 TDC BBB 归档为 76.4%；hERG 阳性率为 76.4%，TDC 为 68.9%。两个队列在化学邻近性和标签组成上都不同于其 TDC 来源。

按化学分层重新评分现有留出预测，未支持用简单骨架重叠或相似度解释 hERG 信号。对 CatBoost，在 23 个共享训练/验证骨架的分子中，hERG 门控 QRC 减门控正交的 AUROC 效应为 -0.0026；在 270 个新骨架分子中为 +0.0452。早期按最高相似度四分位分组时，最高组为 +0.0196，其余三组为 +0.0494。更细的四分位分析并不单调：CatBoost 和 ExtraTrees 在 Q3 均为正，但该方向未在每个相邻分组中保持。BBB 效应在共享骨架、新骨架和多数相似度分组中均为负。完整来源审计见补充表 S5、S6 和 S16。这些描述性分层只定位效应出现的位置，不能控制来源、实验批次或标签定义，也不能建立因果化学机制。

## 6.5 分子性质建模中的解释与复用

低维固定量子储层最清晰的理论动机，是处理训练数据有限、局部非线性强，且经典核不能充分覆盖化学分布的任务。全局 TDC ADMET 端点通常包含更大、更异构的标签集合，当前设计在该情境中没有显示稳定增益。低数据曲线也未在两种基线间出现同步正向变化。该观察并不排除角度编码、任务条件幅度编码、可训练线路、更大储层或不同读出策略；这些方案仍需在强基线和独立来源队列上重新评价。

hERG 候选信号和 B3DB 负迁移都不能单独建立机制性或普遍的量子效应。本文综述的 QML-ADMET 研究使用不同的固定储层、Hamiltonian 派生特征、量子启发预处理、线路搜索或联合训练残差；其任务数、对照和外部迁移设置不支持同类等效比较。表 1 汇总设计差异，补充表 S4 给出扩展比较。本文的经验贡献是对一个固定无状态量子特征映射族开展信号校准的 TDC 全端点审计；方法贡献是提供可复用的最低评价流程：预设主要对照，匹配候选与映射预算，按骨架簇推断，跨端点校正，分别解释等价与优越性，并同时报告跨基线与跨来源结果。

从计算背景看，五比特精确态矢量模拟不是量子加速演示，也不能提供硬件运行时间估计。该规模用于构造精确、相同读出的二次对照，并避免将线路表达力与物理噪声混淆。结果不支持量子运行时间优势，也不能用来推断更大储层、容错量子计算或特定硬件拓扑的可行性；这些是独立的实验问题。

为使结论可直接复用，表 6 将上述匹配对照原则转化为最低报告要求。该表是评价证据可比性和迁移性的检查清单，不是对其他量子架构的预设结论。

表 6 固定线路 QML 分子性质研究的最低匹配评价要求。

|                                                                |                                      |
|----------------------------------------------------------------|--------------------------------------|
| **要求与实施**                                                 | **主要证据**                         |
| 相同 32 维输入、15 个 Pauli 读出和线性残差头                   | 图 1；命题 1；表 3                   |
| 匹配随机性：每族五个独立映射和五个骨架划分                     | 方法 4.2；表 3                       |
| 两种强经典基线：Morgan-ExtraTrees 与 MapLight-CatBoost         | 表 2；表 3                           |
| 使用 Holm 和 TOST 的骨架簇推断                                 | 第 3 节；图 4；表 5                  |
| 独立来源：ToxTree hERG 与 B3DB BBB，并含连续标签检验           | 图 3；补充表 S7-S10、S16             |
| 报告全部端点效应、门控选择、低数据、测量采样、噪声和特征族搜索 | 表 3-5、S12-S16；补充图 S1-S10       |
| 主张边界：精确模拟、电路级噪声和硬件分别报告                   | 方法 4.2、4.4；局限性；补充图 S5-S10 |

# 7 局限性

三类评价限制界定了结果的泛化范围。公开 TDC 测试集可能已被早期研究重复使用，并非前瞻性队列；骨架划分减少了实验室、时间和化学系列之间的近邻泄漏，但不能将其完全消除。低数据分析覆盖八个端点，96 条记录下限会改变最小端点的有效比例。主要外部比较包含两个分类队列，其来源和标签构造不同 \[3-5\]。

执行边界同样明确。精确态矢量计算用于隔离固定线路的表达行为，但不评价物理门误差、读出串扰、连接性或调度。有限测量采样分析对每个 Pauli 期望独立采样；简化去极化模型省略门专用误差、泄漏、串扰和物理调度。Qiskit/Aer 审计增加了转译门去极化和读出翻转，但仍使用固定合成误差参数，且未在电路含噪特征上重新训练完整预测器。本文未测试可训练线路、任务条件幅度编码或其他 PCA 维数。

辅助分析的适用范围更窄。连续标签迁移对二分类模型输出排序，不是独立训练的回归评价。单独 pIC50 回归在固定协议下使用 214 个测试分子和 155 个骨架，统计功效有限。B3DB logBB 仅有 613/2,317 个非重叠分子可用，且类别比例高度不平衡。化学空间图使用线性指纹投影和三个基本描述符，不是完整适用域模型；TOST 边界是探索性基准阈值，而非临床或监管限值 \[21\]。随机映射敏感性为每族五个实现。已知信号校准使用由受测特征族生成的合成目标，只能说明这些设计的可检测性，并不覆盖所有可能的非线性信号。当前比较适用于五比特幅度编码、固定 Hamiltonian 储层、15 个 Pauli 读出、线性残差头和精确模拟；其他编码、可训练线路、更大储层和物理硬件需要独立评价。

# 8 结论

在 22 个官方 TDC ADMET 端点上，固定五比特无状态储层残差相对在输入维数、名义读出维数、拟合参数数量、随机映射预算和调参预算上匹配的真实正交二次映射，没有显示稳定增量。该结果在 Morgan-ExtraTrees 和更强的 MapLight-CatBoost 基线上均成立。验证门控把部分有害残差退回经典基线，却未产生相对门控经典对照的稳定优势。联合门控、低数据缩放、有限测量采样和模拟退相干均未推翻该结论。外部 hERG 迁移提供了 CatBoost 特异候选信号，而 B3DB BBB 显示显著负迁移。连续标签排序迁移和骨架不相交的 pIC50 敏感性分析只显示未校正的弱 CatBoost/hERG 方向，既无 Holm 显著比较，也没有相应 BBB 信号。电路级审计在低、中误差下保持较高秩，但读出幅度明显衰减，且未增加优势证据。已知信号校准恢复了合成的 QRC 与经典目标，零信号假阳性率不超过 5%。

本文的经验贡献是对一个固定无状态量子特征映射族开展信号校准的 TDC 全端点审计；方法贡献是提供开放的匹配评价流程。hERG 信号是有边界的候选，而不是已建立的心脏毒性机制；B3DB 结果也不表示量子方法在 ADMET 中普遍无效。结论适用于所测试的五比特幅度编码、固定 Hamiltonian 储层、15 个 Pauli 读出、线性残差头和精确模拟；其他编码、可训练线路、更大储层和物理硬件需要独立评价。

# 数据与代码可用性

官方 TDC 归档可由 Harvard Dataverse 文件 4426004 获取，SHA-256 为 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1。外部 hERG 数据来自 Zenodo 5807719，BBB 数据来自 B3DB。数据来源、标签规则、去重和重叠审计包含在复现包中。MapLight 参照实现和 MIT 许可证被保留，上游数据许可证随归档材料一并列出。

复现包包含处理脚本、五个骨架划分、每族五个随机映射、基线配置、全部逐划分预测、门控、有限测量采样、低数据、外部效应分解与校准、连续标签迁移、独立 pIC50 回归、简化和电路级噪声、有限特征族、TOST 敏感性、效应分解、容量和来源梯度结果，以及统计脚本、绘图代码和环境锁文件。版本化代码和结果索引见 https://github.com/575914291-source/qrc-admet-matched-evaluation。官方测试标签仅在配置锁定后用于评分，未用于训练、映射生成、联合权重或门控。

# 参考文献

1\. Huang K, Fu T, Gao W, et al. Therapeutics Data Commons: Machine Learning Datasets and Tasks for Drug Discovery and Development. NeurIPS Datasets and Benchmarks, 2021. https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/4c56ff4ce4aaf9573aa5dff913df997a-Abstract-round1.html

2\. Therapeutics Data Commons. ADMET Benchmark Group. https://tdcommons.ai/benchmark/admet\_group/overview/

3\. Yang K, Swanson K, Jin W, et al. Analyzing Learned Molecular Representations for Property Prediction. Journal of Chemical Information and Modeling, 2019. https://doi.org/10.1021/acs.jcim.9b00237

4\. Sheridan R P. Time-Split Cross-Validation as a Method for Estimating the Goodness of Prospective Prediction. Journal of Chemical Information and Modeling, 2013. https://doi.org/10.1021/ci400084k

5\. Koleiev I, Stratiichuk R, Shevchuk N, et al. An End-User Audit of Reproducibility, Data Leakage, and Overfitting of the Top-Ranked ADMET Prediction Models in TDC Leaderboards. Journal of Chemical Information and Modeling, 2026. https://doi.org/10.1021/acs.jcim.6c00819

6\. Notwell J H, Wood M W. ADMET property prediction through combinations of molecular fingerprints. arXiv preprint, 2023. https://arxiv.org/abs/2310.00174

7\. Kamuntavičius G, Paquet T, Bastas O, et al. Benchmarking ML in ADMET predictions: the practical impact of feature representations in ligand-based models. Journal of Cheminformatics, 2025. https://doi.org/10.1186/s13321-025-01041-0

8\. Beaulieu D, Kornjača M, Krunic Z, et al. Robust Quantum Reservoir Learning for Molecular Property Prediction. Journal of Chemical Information and Modeling, 2025. https://doi.org/10.1021/acs.jcim.5c00958

9\. Benson B M, Byler K, Petroff A, Keinan S, Shipman W J. Quantum-Inspired Hamiltonian Feature Extraction for ADMET Prediction: A Simulation Study. arXiv preprint, 2026. https://arxiv.org/abs/2603.03109

10\. Mansour B, Takahashi D K, Rafaelyan G. ADMET Property Prediction with Quantum-Inspired Preprocessing. bioRxiv preprint, 2026. https://doi.org/10.64898/2026.06.30.735582

11\. Zheng K, Fu T, Liang Z. QCS-ADME: Quantum Circuit Search for Drug Property Prediction with Imbalanced Data and Regression Adaptation. Quantum Machine Intelligence, 2026. https://doi.org/10.1007/s42484-026-00369-6

12\. Jia C, Ma Y, Wang Y, Guo C. Quantum-Circuit Residuals for Receptor Functional Potency Prediction: Predictive Gains and Quadratic Structure. arXiv preprint, 2026. https://arxiv.org/abs/2610.13037

13\. Bowles J, Ahmed S, Schuld M. Better than classical? The subtle art of benchmarking quantum machine learning models. arXiv preprint, 2024. https://arxiv.org/abs/2403.07059

14\. Wolpert D H. Stacked Generalization. Neural Networks, 1992. https://doi.org/10.1016/S0893-6080(05)80023-1

15\. van der Laan M J, Polley E C, Hubbard A E. Super Learner. Statistical Applications in Genetics and Molecular Biology, 2007. https://doi.org/10.2202/1544-6115.1309

16\. Shi Y, Luo H, Liu F, Zhao S. Ark-ADMET: endpoint-specific selection of molecular representations and hyperparameters for gradient-boosted ADMET models under the Therapeutics Data Commons benchmark protocol. bioRxiv preprint, 2026. https://doi.org/10.64898/2026.10.28.762420

17\. Fredsgaard L, Andersen M R, Schmidt M N. Calibrated Uncertainty Quantification on TDC ADMET: What Can Be Resolved Across 22 Datasets? arXiv preprint, 2026. https://arxiv.org/abs/2611.09373

18\. Field C A, Welsh A H. Bootstrapping Clustered Data. Journal of the Royal Statistical Society: Series B, 2007. https://doi.org/10.1111/j.1467-9868.2007.00593.x

19\. Winkler A M, Webster M A, Vidaurre D, Nichols T E, Smith S M. Multi-level block permutation. NeuroImage, 2015. https://doi.org/10.1016/j.neuroimage.2015.05.092

20\. Holm S. A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics, 1979. https://www.jstor.org/stable/4615733

21\. Lakens D. Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses. Social Psychological and Personality Science, 2017. https://doi.org/10.1177/1948550617697177

22\. Bemis G W, Murcko M A. The Properties of Known Drugs. 1. Molecular Frameworks. Journal of Medicinal Chemistry, 1996. https://doi.org/10.1021/jm9602928

23\. Geurts P, Ernst D, Wehenkel L. Extremely randomized trees. Machine Learning, 2006. https://doi.org/10.1007/s10994-006-6226-1

24\. Rahimi A, Recht B. Random Features for Large-Scale Kernel Machines. NeurIPS, 2007. https://papers.nips.cc/paper\_files/paper/2007/hash/013a006f03dbc5392effeb8f18fda755-Abstract.html

25\. maplightrx. MapLight-TDC: reference implementation, commit c249378. GitHub, accessed 2026-11-25. https://github.com/maplightrx/MapLight-TDC

26\. Prokhorenkova L, Gusev G, Vorobev A, Dorogush A V, Gulin A. CatBoost: unbiased boosting with categorical features. NeurIPS, 2018. https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html

27\. Garg S, Garg S. Benchmarking Classical and Quantum Machine Learning for Potency Prediction across Ten Therapeutically Relevant Targets. ACS Medicinal Chemistry Letters, 2026. https://doi.org/10.1021/acsmedchemlett.5c00724

28\. Wang L, Zhang D, Wang C, et al. Coherent Floquet quantum reservoirs for molecular property prediction. arXiv:2609.11071, 2026. https://arxiv.org/abs/2609.11071

29\. Arab I, Barakat K. ToxTree: descriptor-based machine learning models for both hERG and Nav1.5 cardiotoxicity liability predictions. arXiv:2112.13467, 2021. https://arxiv.org/abs/2112.13467; dataset: https://doi.org/10.5281/zenodo.5807719

30\. Meng F, Xi Y, Huang J, Ayers P W. A curated diverse molecular database of blood-brain barrier permeability with chemical descriptors. Scientific Data, 2021. https://doi.org/10.1038/s41597-021-01069-5

31\. Robinson M C, Glen R C, Lee A A. Validating the validation: reanalyzing a large-scale comparison of deep learning and machine learning models for bioactivity prediction. Journal of Computer-Aided Molecular Design, 2020. https://doi.org/10.1007/s10822-019-00274-0

32\. Pandey T. When Classical Baselines Are Tuned as Carefully as the Quantum Model, Does Quantum Reservoir Computing Still Win? arXiv:2607.09905, 2026. https://arxiv.org/abs/2607.09905

33\. Pandey T. A Quantum Reservoir Architecture for Chaotic Forecasting and a Test of Whether Its High Dimension Helps. arXiv:2607.07978, 2026. https://arxiv.org/abs/2607.07978

34\. Kornjaca M, Hu H Y, Zhao C, et al. Large-scale quantum reservoir learning with an analog quantum computer. arXiv:2407.02553, 2024. https://arxiv.org/abs/2407.02553

35\. Ramon-Escandell C, Riera A, Plodzien M. From quantum reservoirs to quantum extreme learning machines through a nearest-neighbor spin chain with tunable quantum memory. arXiv:2608.28440, 2026. https://arxiv.org/abs/2608.28440

36\. Xiong W, Facelli G, Sahebi M, et al. On fundamental aspects of quantum extreme learning machines. arXiv:2312.15124, 2023. https://arxiv.org/abs/2312.15124

37\. Gross M, Rieser H M. Theory and interpretability of Quantum Extreme Learning Machines: a Pauli transfer matrix approach. arXiv:2602.18377, 2026. https://doi.org/10.1103/6tm7-3tn4

38\. Gross M, Rieser H M. Kernel-based optimization of measurement operators for quantum reservoir computers. arXiv:2602.14677, 2026. https://arxiv.org/abs/2602.14677

39\. Ait Haddou M. Readout Orientation Controls Measurement-Accessible Quantum Tangent Geometry. arXiv:2608.17085, 2026. https://arxiv.org/abs/2608.17085

40\. Knopov D, Shvai N. Equivalence testing and run-count design for stochastic machine-learning experiments. arXiv:2610.23700, 2026. https://arxiv.org/abs/2610.23700

41\. Siraj B M, Habib G, Ruban S. Matched but Not Better: An Equivalence-Tested Benchmark of Quantum Machine Learning on Six Clinical Datasets and the QML-Health-READY Reporting Framework. arXiv:2611.05442, 2026. https://arxiv.org/abs/2611.05442

42\. Talkhan N A M A, Abdelbaky I, Omara F A. Representation and Model Contributions on Small Molecular Benchmarks: Controlled Comparisons and External Evaluation. arXiv:2611.32568, 2026. https://arxiv.org/abs/2611.32568

43\. Zheng J, Guo C, Wang Z, Liu X, Chen H. Beyond Scaffold Splits: Structural-Frontier Evaluation Reveals Hidden Failures in ADMET Models. arXiv:2607.10729, 2026. https://arxiv.org/abs/2607.10729

44\. Seal S, Zalte A S, Araripe D A, et al. Model Validation Protocols for Machine Learning in Small Molecule Drug Discovery. bioRxiv preprint, 2026. https://doi.org/10.64898/2026.08.19.745868

45\. De Lorenzis A, Casado M P, Lo Gullo N, Lux T, Plastina F, Riera A. Entanglement and Classical Simulability in Quantum Extreme Learning Machines. arXiv:2509.06873, 2025. https://arxiv.org/abs/2509.06873
