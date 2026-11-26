---
title: "论文中英文终稿修订报告"
subtitle: "七项检查、双语合并与代表性前后对照"
date: "2026-11-26"
lang: zh-CN
---

## 修改范围

本次修改覆盖英文 JCAMD 投稿全文和逐段对应的中文参考稿。原有 1-31 号文献、研究问题、模型、数据集、全部数值和实验判断均保留；在另一对话框的检索结果基础上新增 32-45 号文献，并逐条核对题名、年份、摘要与引用语境。除双语对应、文献适用范围和表述边界外，没有新增实验。

## 总体改善

- 将统计计算与 TOST 解释拆成独立段落。
- 将连续 pIC50 回归与 Qiskit/Aer 电路审计拆成独立 Results 章节，并相应重排编号。
- 把扩大后的容量诊断与外部相似度四分位结果写入讨论，避免把读出矩阵满秩写成样本特征容量相等。
- 将局限重写为评估、量子执行和辅助分析三个主题，说明每项限制影响哪一类推断。
- 将结论拆为经验结果与方法贡献，避免在摘要、讨论、局限和结论中重复同一段防御性表述。
- 统一英美拼写，并清除英文参考文献中的全角标点。

## 七项检查结果

| 检查项 | 发现的问题 | 已采取的处理 |
|---|---|---|
| 段落功能 | 统计计算与 TOST 解释同段；连续回归与电路审计同节；部分研究过程缺少定义 | 拆分统计、TOST、回归和电路章节；补充 exploratory pilot 的四个具体端点，并说明其不进入确证推断 |
| 标点与套话 | 英文参考文献中存在 7 处全角逗号；少量压缩标签信息不足 | 统一英文标点；将压缩标签改为可核对的说明 |
| 衔接 | therefore 等连接词在部分句子中重复，但未发现连续冒号滥用 | 仅删除可由论据直接表达的连接词；保留 TOST 分类和命题推导所需的逻辑标记 |
| 文献 | 部分近邻研究只写“做了什么”，未说明其结果和适用范围 | 对 Beaulieu、Benson、Mansour、Zheng、Jia、Garg、Wang 的结果方向、控制方式和任务范围作了更明确的区分 |
| 句式 | 结果段落有重复的主语—动词序列 | 重写为“对象—比较—结果”顺序，不改变数值 |
| 分析 | 容量讨论把读出矩阵满秩与样本特征有效秩混在一起 | 区分矩阵秩、条件数、held-out effective rank 和 CKA |
| 防御表达 | 摘要、讨论、局限和结论重复说明“不能外推” | 将限制按评估、执行和辅助分析三类集中陈述，各保留一次 |

## 文献适用范围核对

- Beaulieu 等工作支持小样本固定储层与嵌入可分性的讨论，不支持对其它编码或真实硬件的普遍推断。
- Benson 等报告的是 Hamiltonian 衍生特征与完整经典表示拼接后的 10 任务结果，不等同于本研究的同容量固定残差控制。
- Mansour 等的二次多项式消融说明量子启发特征可能被经典交互项解释，直接支持本文加入显式二次控制。
- Zheng 等研究线路搜索与 sim-to-real，Garg 等研究跨靶点量子分类基准；两者与本研究的固定线路匹配评估对象不同。
- Jia 等同样使用幅度编码残差和实正交控制，但其编码器与量子头联合训练，且任务是受体效价而非 ADMET。
- Wang 等研究序列图事件、Floquet 驱动和硬件执行，支持“输入和动力学改变结论”的边界说明，不进入本文主比较。

## 代表性上下文前后对照

本节列出 11 个代表性修改；其余修改保留在完整 JSON 日志中。

### 1. Abstract, paragraph 1

**原文**

Reported QRC gains are difficult to interpret because matched classical controls, multiple random realizations, strong base models, and cross-source validation are rarely combined. We establish a calibrated reproducible matched evaluation workflow on all 22 Therapeutics Data Commons (TDC) ADMET endpoints. We compare exactly simulated five-qubit amplitude-encoded reservoirs with real-orthogonal quadratic maps and random Fourier features, using Morgan-ExtraTrees and MapLight-CatBoost. Five scaffold splits and five averaged maps per family control randomness. Ungated QRC is better on 6 and worse on 16 ExtraTrees endpoints, and better on 3 and worse on 19 CatBoost endpoints. After Holm correction, no endpoint is significantly better and three are significantly worse. Gating, joint correction, low-data scaling, finite shots, simulated noise, and a bounded reservoir-family search do not produce a cross-base advantage. External validation is source-dependent: CatBoost improves by 0.040 AUROC on 293 non-overlapping hERG molecules but both bases degrade on 2,317 B3DB BBB molecules. The hERG difference combines a QRC gain and an orthogonal-branch decrement relative to the base. Continuous-label ranking and an independent pIC50 regression do not survive joint multiplicity correction. Known-signal calibration recovered QRC and classical targets, with null false-positive rates of 2.0-4.7%. A Qiskit/Aer audit preserved rank under errors but attenuated amplitudes. Chemical-space analyses show no simple source effect. The main contribution is a calibrated evaluation workflow. The conclusion is bounded by five-qubit amplitude encoding, 15 Pauli readouts, a linear residual head, and exact state-vector simulation; it is not a general claim against other encodings, trainable circuits, larger reservoirs, or physical hardware.

**修改后**

Reported QRC gains are difficult to compare because studies often differ in classical controls, random realizations, base-model strength, and external validation. We evaluated this question under a common, calibrated protocol across all 22 Therapeutics Data Commons (TDC) ADMET endpoints. We compared exact simulations of five-qubit amplitude-encoded reservoirs with real-orthogonal quadratic maps and random Fourier features, using Morgan-ExtraTrees and MapLight-CatBoost. Five scaffold splits and five averaged maps per family quantified randomness. Ungated QRC was better on 6 and worse on 16 ExtraTrees endpoints, and better on 3 and worse on 19 CatBoost endpoints. After Holm correction, no endpoint was significantly better and three were significantly worse. Validation gating, joint QRC-orthogonal residuals, low-data scaling, finite shots, simulated noise, and a bounded reservoir-family search did not produce a cross-base advantage. External validation was source-dependent: CatBoost improved by 0.040 AUROC on 293 non-overlapping hERG molecules, whereas both bases degraded on 2,317 B3DB BBB molecules. The hERG difference combined a QRC gain with an orthogonal-branch decrement relative to the base. Continuous-label ranking and an independent pIC50 regression did not survive joint multiplicity correction. Known-signal calibration recovered QRC and classical targets, with null false-positive rates of 2.0-4.7%. Circuit-level simulation preserved rank under error but attenuated amplitudes. Chemical-space analyses showed no simple source effect. The main contribution is a calibrated evaluation workflow; its scope is limited to five-qubit amplitude encoding, 15 Pauli readouts, a linear residual head, and exact state-vector simulation, not to other encodings, trainable circuits, larger reservoirs, or physical hardware.

**具体改善**

Sharpened the comparison problem, removed compressed nominal phrases, and grouped each result with its evidential role while retaining all values.

### 2. 1 Introduction, paragraph 2

**原文**

We ask a bounded question. Under the same input, the same 15 readouts, and the same linear residual head, does a fixed five-qubit reservoir provide an increment relative to real-orthogonal quadratic maps and random Fourier features across the 22 TDC endpoints, two classical bases, and independent external sources? Figure 1 summarizes the design. The study makes three contributions. First, it formalizes the current QRC and linear residual head as a constrained real quadratic feature family and constructs an equal-input, equal-capacity, equal-map-budget quadratic control. Second, it evaluates the family across all 22 endpoints with validation gating and multiple-testing correction. Third, it uses low-data, finite-shot, simulated-noise, bounded-family, two-source external, continuous-label, independent pIC50 regression, and chemical-space analyses to delimit the conclusion.

**修改后**

The study addresses one question: with molecular input, 15 readouts, and the linear residual head held constant, does a fixed five-qubit reservoir add predictive value beyond real-orthogonal quadratic maps and random Fourier features across 22 TDC endpoints, two classical bases, and independent external sources? Figure 1 summarizes the design. The study makes three contributions. First, it treats the current QRC residual as a constrained real quadratic feature family and constructs a control with the same input, readout dimension, fitted-parameter budget, and map budget. Second, it evaluates the family across all 22 endpoints with validation gating and multiple-testing correction. Third, it uses low-data, finite-shot, simulated-noise, bounded-family, two-source external, continuous-label, independent pIC50 regression, and chemical-space analyses to define the limits of the conclusion.

**具体改善**

Converted a broad statement of scope into one research question and three explicit, non-overlapping contributions.

### 3. 2.2 Quantum Molecular Features and Structural Controls, paragraph 1

**原文**

Beaulieu et al. studied fixed reservoirs and small-sample molecular activity learning [8]. Benson et al. concatenated Hamiltonian-derived readouts with classical descriptors before CatBoost, and Mansour et al. reported errors from quantum-inspired preprocessing on AqSolDB [9,10]. QCS-ADME focused on circuit search and simulator-to-hardware variation [11]. Jia et al. compared five-qubit amplitude-encoded residuals with real-orthogonal branches, but jointly trained the encoder and prediction head and did not address ADMET [12]. A recent 48-task potency benchmark found no global advantage for quantum classifiers over their classical comparators [27]. Floquet-QRC work has also used sequential graph events and driven reservoirs under a different input and dynamics setting [28]. Table 1 summarizes these studies and their relation to the present benchmark; their tasks, quantum components, and training protocols do not support a single-score ranking.

**修改后**

Beaulieu et al. reported more stable fixed-reservoir performance in smaller molecular-activity datasets and analyzed embedding separation [8]. Benson et al. concatenated Hamiltonian-derived readouts with classical descriptors before CatBoost and reported improvement on 8/10 TDC tasks; this hybrid feature design does not isolate a capacity-matched residual [9]. Mansour et al. found that compact quantum-inspired Hamiltonian features performed comparably to a second-degree polynomial interaction control on AqSolDB, making an explicit quadratic comparator central to the present design [10]. QCS-ADME addressed quantum-circuit search and simulator-to-hardware variation rather than one fixed circuit family [11]. Jia et al. compared five-qubit amplitude-encoded residuals with real-orthogonal controls, but jointly trained the encoder and residual head and evaluated receptor-potency tasks rather than ADMET [12]. A 48-task potency benchmark found no global advantage for quantum classifiers [27], and Floquet-QRC tested sequential graph events and driven reservoirs under a different input regime [28]. These studies differ in task, control, and training protocol; Table 1 accordingly compares design choices rather than model scores.

**具体改善**

State the reported scope of each source, distinguish positive, negative, and mechanistic findings, and explain why the table is not a numerical ranking.

### 4. 4.2 Five-Qubit Reservoir and Matched Classical Features, Proposition 1

**原文**

Proposition 1. For any fixed set of 15 diagonal Pauli observables D_j and any fixed unitary U, the readouts of a normalized 32-dimensional real input a satisfy q_j(a)=a^T A_j a, where A_j=Re(U^dagger D_j U). Therefore any intercept-free linear readout is a real quadratic form a^T M a+b: fixed five-qubit QRC with a linear residual head belongs to a model family constrained by at most 15 real quadratic forms. The proof follows by expanding (Ua)^dagger D_j (Ua). This does not make QRC equivalent to a particular real-orthogonal map; it defines the function class available under the current encoding and readout.

**修改后**

Proposition 1. For any fixed set of 15 diagonal Pauli observables D_j and any fixed unitary U, the readouts of a normalized 32-dimensional real input a satisfy q_j(a)=a^T A_j a, where A_j=Re(U^dagger D_j U). An intercept can be absorbed into b, so any linear readout of these features has the form a^T M a+b. Thus fixed five-qubit QRC with a linear residual head belongs to a model family constrained by at most 15 real quadratic forms. The proof follows by expanding (Ua)^dagger D_j(Ua). This class description does not equate QRC with a particular real-orthogonal map; it identifies the function family and motivates the matched control.

**具体改善**

Removed the contradiction between 'intercept-free' and the intercept-containing expression, and stated the role of the proposition directly.

### 5. 5.1 Overall Results, paragraph 1

**原文**

Table 2 reports five-seed mean official metrics for both bases and ungated branches. Relative to the fixed real-orthogonal control, point estimates favoured QRC on 6 and the matched control on 16 ExtraTrees endpoints, and favoured QRC on 3 and the matched control on 19 CatBoost endpoints. The corrected CatBoost base itself outperformed ExtraTrees on 21/22 endpoints; the exception was AUPRC on CYP2C9 substrate. The four endpoints with the most consistent directional signals in the earlier pilot did not reproduce consistently: only Caco2 and LD50 were positive against the base on ExtraTrees and only hERG was marginally positive on CatBoost. Against the orthogonal map, at most 2/4 were positive on either base, and none survived multiple-testing correction.

**修改后**

Table 2 reports five-seed mean official metrics for both bases and ungated branches. Relative to the fixed real-orthogonal control, point estimates favored QRC on 6 and the matched control on 16 ExtraTrees endpoints; on CatBoost, they favored QRC on 3 and the matched control on 19 endpoints. The corrected MapLight-CatBoost base outperformed ExtraTrees on 21/22 endpoints; the exception was AUPRC on CYP2C9 substrate. An earlier exploratory pilot selected BBB, hERG, Caco2, and LD50 as candidate endpoints. Their directions did not reproduce consistently: only Caco2 and LD50 were positive against the base on ExtraTrees and only hERG was marginally positive on CatBoost; against the matched orthogonal control, at most 2/4 were positive on either base, and none survived multiple-testing correction. These four endpoints are reported as exploratory and are not used for confirmatory inference.

**具体改善**

Named the four endpoints from the exploratory pilot, preserved their direction counts, and explicitly separated them from confirmatory inference.

### 6. 5.10 Benchmark Calibration and Source Diagnostics, paragraph 1

**原文**

The known-signal calibration recovered the intended geometry. For a QRC-derived target, QRC minus orthogonal test performance was +0.302 on ExtraTrees and +0.190 on CatBoost, and the correct source family ranked first in 100.0% and 100.0% of simulations. For an orthogonal-derived target, the same contrast reversed to -0.332 and -0.238; the correct classical family ranked first in 99.3% and 99.3% of simulations. Null false-positive rates were 4.7% and 2.0%, respectively.

**修改后**

The known-signal calibration separated the three feature families. For QRC-derived targets, QRC minus orthogonal test performance was +0.302 on ExtraTrees and +0.190 on CatBoost, and the expected QRC family ranked first in 150/150 simulations (100.0%) for both bases. For orthogonal-derived targets, the same contrast reversed to -0.332 and -0.238, and the expected orthogonal family ranked first in 149/150 simulations (99.3%) for ExtraTrees and 149/150 (99.3%) for CatBoost. For null targets, two-sided paired permutation tests were significant in 7/150 simulations (4.7%) on ExtraTrees and 3/150 (2.0%) on CatBoost.

**具体改善**

Replaced generic 'recovered' language with the number and direction of recovered cases, and clarified what the null rate measures.

### 7. 6.1 What the Constrained Quadratic Map Explains, paragraph 1

**原文**

With real amplitude inputs, every Z or ZZ expectation after fixed evolution can be computed exactly as a real symmetric quadratic form. Training-side standardization is an affine feature transform, so the linear readout only combines these quadratic forms and adds a fixed offset. Given the fitted parameters, the QRC residual can be reproduced by a real quadratic form and a constant. This structure applies to the normalized 32-dimensional latent input, not to the raw molecular graph. All five QRC maps had rank 15 and a median condition number of 1.210; the real-orthogonal maps had condition number 1.000. The nominal capacities are equal, while the geometries of the quadratic matrices differ.

**修改后**

With real amplitude inputs, every Z or ZZ expectation after fixed evolution is a real symmetric quadratic form. Training-side standardization is affine, so the linear readout combines these forms and adds a fixed offset. Given the fitted parameters, the QRC residual can be reproduced by a real quadratic form and a constant on the normalized 32-dimensional latent input. This statement applies to that latent space, not to the raw molecular graph. All five QRC readout matrices had rank 15 and a median condition number of 1.210; the real-orthogonal readout matrices had rank 15 and condition number 1.000. On held-out molecular features, effective rank was 14.10 versus 14.62 on ExtraTrees and 12.82 versus 14.25 on CatBoost, with linear centered-kernel alignments of 0.20 and 0.30. The branches had equal output and fitted-parameter budgets, different geometry, and comparable but not identical effective feature capacity.

**具体改善**

Distinguished full-rank readout matrices from held-out feature effective rank and removed the unsupported phrase that nominal capacities were equal.

### 8. 6.4 Chemical-Space and Source Dependence, paragraph 2

**原文**

Re-scoring the existing held-out predictions by these chemical strata did not support a simple scaffold-overlap explanation for the hERG signal. For CatBoost, the hERG gated-QRC minus gated-orthogonal effect was -0.0026 AUROC among the 23 molecules with a shared train/validation scaffold and +0.0452 among the 270 molecules with a novel scaffold. The effect was +0.0196 in the highest nearest-similarity quartile and +0.0494 in the remaining three quartiles. In contrast, the BBB effect was negative across shared-scaffold, novel-scaffold, and similarity strata. Full source audits and hERG strata are reported in Supplementary Tables S5 and S6. These descriptive strata locate where an effect appears; they do not control source, assay batch, or label definition and cannot establish a causal chemical mechanism.

**修改后**

Stratifying the held-out predictions did not support a simple scaffold-overlap or similarity explanation for the hERG signal. For CatBoost, the hERG gated-QRC minus gated-orthogonal effect was -0.0026 AUROC among the 23 molecules with a shared train/validation scaffold and +0.0452 among the 270 molecules with a novel scaffold. The earlier top-quartile split gave +0.0196 in the highest-similarity group and +0.0494 in the other three quartiles. The finer quartile analysis was non-monotonic: CatBoost and ExtraTrees were positive in Q3 but not in every adjacent quartile. B3DB effects were negative across shared-scaffold, novel-scaffold, and most similarity strata. Full source audits are reported in Supplementary Tables S5, S6, and S16. These descriptive strata locate where an effect appears; they do not control source, assay batch, or label definition and cannot establish a causal chemical mechanism.

**具体改善**

Aligned the discussion with the expanded quartile analysis and removed wording that suggested a monotonic source gradient.

### 9. 7 Limitations, paragraph 1

**原文**

The fixed official test set supports reproducible comparisons but may have been reused by earlier public leaderboards and is not a prospective cohort. Similar molecules may remain under different Murcko scaffolds, so extrapolation across laboratories, time, and chemical series requires separate evaluation. The exact state-vector calculation is a controlled choice for isolating circuit expressivity and does not replace evaluation of physical gate error, readout crosstalk, connectivity, or scheduling. The equivalence margins are exploratory and are not clinical or regulatory thresholds [3-5,21].

**修改后**

Three evaluation limits constrain generalization. The public TDC test sets may have been reused by earlier studies and are not prospective cohorts; scaffold splits reduce, but do not eliminate, near analogues across laboratories, time, and chemical series. The low-data analysis covers eight endpoints, and its 96-record minimum changes the effective fraction for the smallest endpoints. The primary external comparison contains two classification cohorts that differ in assay source and label construction [3-5].

**具体改善**

Grouped related evaluation limitations and placed the non-clinical equivalence caveat with the statistical scope.

### 10. 8 Conclusion, paragraph 1

**原文**

Across 22 official TDC ADMET endpoints, fixed five-qubit reservoir residuals showed no stable increment over equal-capacity real-orthogonal quadratic maps. This result held on both Morgan-ExtraTrees and the stronger MapLight-CatBoost base. Validation gating pushed some harmful residuals back to the classical base but did not produce a stable advantage over the gated classical control. Joint gating, low-data scaling, finite shots, and simulated decoherence did not reverse this conclusion. External hERG provided a CatBoost-specific candidate signal, whereas B3DB BBB showed significant negative transfer. Continuous-label rank transfer and independent pIC50 regression both showed only uncorrected weak CatBoost/hERG directions, with no Holm-significant comparison and no corresponding BBB signal. The circuit-level audit showed high rank preservation under low and medium errors but marked readout attenuation and no new advantage evidence. Chemical-space and physicochemical strata support a source-dependent local signal rather than an identifiable general chemical rule. The main contribution is a reproducible QML evaluation workflow. The result is bounded by the tested five-qubit amplitude-encoded, fixed-Hamiltonian reservoir with 15 Pauli readouts, a linear residual head, and exact simulation; other encodings, trainable circuits, larger reservoirs, and physical hardware require independent evaluation.

**修改后**

Across 22 official TDC ADMET endpoints, fixed five-qubit reservoir residuals showed no stable increment over real-orthogonal quadratic maps with the same readout dimension, fitted-parameter budget, and map budget. This result held on both Morgan-ExtraTrees and the stronger MapLight-CatBoost base. Validation gating reduced harmful residuals but did not produce a stable advantage over gated classical controls. Joint gating, low-data scaling, finite shots, and simulated decoherence did not reverse the result. External hERG produced a CatBoost-specific candidate signal, whereas B3DB BBB showed significant negative transfer. Continuous-label transfer and independent pIC50 regression showed only uncorrected weak CatBoost/hERG directions, and neither had a corresponding BBB signal. Known-signal calibration recovered the synthetic QRC and classical targets, and null false-positive rates remained at or below 5%.

**具体改善**

Converted a single dense paragraph into an evidence summary that does not repeat the full limitations list.

### 11. Data and Code Availability, paragraph 1

**原文**

The official TDC archive is available as Harvard Dataverse file 4426004 with SHA-256 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. External hERG data are from Zenodo 5807719 and BBB data from B3DB; source, label rules, deduplication, and overlap audits are included in the reproduction package. The package also contains processing scripts, five scaffold splits, five random maps per family, base configurations, all split-level predictions, joint gating, finite-shot, low-data, external-endpoint decomposition and calibration, continuous-label transfer, independent pIC50 regression, simplified and circuit-level noise, bounded-family, TOST-sensitivity, and chemical-space audit results, statistical scripts, figure-generation code, and environment locks. The versioned code and result index are available at https://github.com/575914291-source/qrc-admet-matched-evaluation; the submission archive contains complete split-level predictions and supplementary materials. The MapLight reference and MIT license are retained. Official test labels were used only for scoring after configuration lock and were not used for training, map generation, joint weights, or gating.

**修改后**

The official TDC archive is available as Harvard Dataverse file 4426004 with SHA-256 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. External hERG data are from Zenodo 5807719 and BBB data from B3DB. Source, label rules, deduplication, and overlap audits are included in the reproduction package. The MapLight reference and MIT license are retained, and upstream data licenses are listed with the archived materials.

**具体改善**

Made the availability statement easier to audit and kept the same identifiers.

## 新增与重排段落

- **3 Data, Splits, and Statistical Evaluation, paragraph 3**：Separated hypothesis testing from TOST interpretation.

  Exploratory TOST used margins of 0.01 for AUROC, AUPRC, and Spearman and 2% of base MAE for MAE. These thresholds define practical benchmark equivalence, not clinical limits. Practical equivalence was reported only when the 90% confidence interval lay inside the prespecified margin and the equivalence test remained significant after Holm correction. Results are classified as significant degradation, significant improvement, practical equivalence, or unresolved. Equivalence does not imply identical mechanisms or identical per-molecule predictions.

- **5.5 Independent External Endpoints, paragraphs 3-4**：Separated external effect decomposition from continuous-label transfer.

  The continuous-label rank transfer produced an unadjusted CatBoost/hERG pIC50 Spearman difference of +0.043. This difference did not survive Holm correction across 12 comparisons and did not replicate for BBB logBB. Because it ranks predictions from binary-trained models, it is not an independently trained regression evaluation; the B3DB continuous subset is 86.8% positive.

- **5.9 Circuit-Level Aer Audit**：Separated an unrelated audit from continuous regression.

  5.9 Circuit-Level Aer Audit

- **5.9 Circuit-Level Aer Audit, paragraph 1**：Placed circuit design before its results.

  We also examined circuit-specific readout degradation with explicit Qiskit circuits: 32-dimensional amplitude preparation, an eight-step Lie-Trotter fixed-Hamiltonian evolution, and all-qubit Z-basis measurement. The panel covered eight representative endpoints, 32 stratified test states per endpoint, and five reservoir maps; transpiled circuits had depth 81 and about 136 operations. Aer density-matrix simulation included one- and two-qubit gate depolarizing errors plus independent readout flips.

- **5.9 Circuit-Level Aer Audit, paragraph 2**：Made circuit evidence and its interpretation contiguous.

  Relative to exact matrix readouts, normalized RMSE was 0.189-0.199, 0.337-0.351, and 0.551-0.569 at low, medium, and high error, respectively. Signal slopes were approximately 0.81, 0.66, and 0.45, whereas Spearman correlations remained 0.9974-0.9986, 0.9916-0.9958, and 0.9742-0.9866. The noiseless Trotterized RMSE was 0.0058-0.0070. Circuit errors mainly contracted readout amplitude while retaining substantial relative ordering; they did not add new advantage evidence. This is a readout-fidelity audit, not end-to-end retraining on noisy features. Full results are reported in Supplementary Figure S5 and Supplementary Table S11.

- **5.10 Benchmark Calibration and Source Diagnostics, paragraph 4**：Connected the source-dependence claim to non-monotonic quartile evidence.

  External stratification did not follow a monotonic similarity gradient. For CatBoost/hERG, QRC-specific AUROC changed from +0.003 in Q1 to +0.037, +0.070, and +0.013 across Q2-Q4; the Q3 interval [+0.011, +0.128] excluded zero. ExtraTrees showed a different pattern, with QRC-specific effects of -0.064, -0.059, +0.055, and -0.006 across Q1-Q4; the Q3 interval was [+0.018, +0.092]. B3DB showed no consistently positive quartile. The hERG signal was localized and source-specific rather than a simple function of nearest-TDC similarity.

- **6.3 What the Strong Base and External Cohorts Reveal, paragraph 2**：Separated the evidence summary from the design implication and removed repeated scope language.

  The external results support only a source-specific candidate on hERG. The same direction appeared in pIC50 rank transfer and independent regression, but neither survived the joint multiplicity correction. B3DB logBB was near zero and B3DB BBB classification degraded significantly, so the hERG result cannot be generalized across sources. These findings support testing future quantum encodings on a strong classical base with matched input, capacity, and candidate budgets; they do not establish a general ADMET descriptor.

- **6.5 Interpretation and Reuse**：Separated interpretation boundaries from the chemical-space description.

  6.5 Interpretation and Reuse

- **7 Limitations, paragraph 3**：Consolidated auxiliary-analysis limits and stated the final scope once.

  The auxiliary analyses have narrower scope. Continuous-label transfer ranks outputs from binary-trained models and is not an independently trained regression. The separate pIC50 regression uses 214 test molecules in 155 scaffolds under a fixed protocol and has limited statistical power. B3DB logBB was available for only 613/2,317 non-overlapping molecules and was strongly class-enriched. The chemical-space figure uses a linear fingerprint projection and three basic descriptors, not a complete applicability-domain model, and TOST margins are exploratory benchmark thresholds rather than clinical or regulatory limits [21]. Random-map sensitivity covers five realizations per family. The known-signal calibration uses synthetic targets drawn from the tested feature families; it establishes detectability for those designs, not coverage of every possible nonlinear signal. The reported comparison applies to five-qubit amplitude encoding, a fixed Hamiltonian reservoir, 15 Pauli readouts, a linear residual head, and exact simulation; other encodings, trainable circuits, larger reservoirs, and physical hardware require independent evaluation.

- **8 Conclusion, paragraph 2**：Separated the methodological contribution and final scope from the result summary.

  The study's main contribution is a calibrated matched-evaluation workflow that distinguishes ordinary quadratic effects, reservoir-specific candidate effects, and source dependence. The hERG signal is a bounded candidate, not a demonstrated mechanism of cardiotoxicity, and the B3DB result does not show that quantum methods are universally ineffective. The conclusion applies to the tested five-qubit amplitude-encoded, fixed-Hamiltonian reservoir with 15 Pauli readouts, a linear residual head, and exact simulation; other encodings, trainable circuits, larger reservoirs, and physical hardware require independent evaluation.

- **Data and Code Availability, paragraph 2**：Separated the software inventory and test-label handling from source-data provenance.

  The reproduction package contains processing scripts, five scaffold splits, five random maps per family, base configurations, all split-level predictions, gating, finite-shot, low-data, external decomposition and calibration, continuous-label transfer, independent pIC50 regression, simplified and circuit-level noise, bounded-family, TOST-sensitivity, effect-decomposition, capacity, and source-gradient results, statistical scripts, figure-generation code, and environment locks. The versioned code and result index are at https://github.com/575914291-source/qrc-admet-matched-evaluation. Official test labels were used only for scoring after configuration lock and were not used for training, map generation, joint weights, or gating.

- **Table 6**：Updated evidence cross-references.

  Methods 3; Figure 4; Table 5 -> Section 3; Figure 4; Table 5

- **Table 6**：Updated evidence cross-references.

  Figure 3; Tables S7-S10 -> Figure 3; Tables S7-S10, S16

- **Table 6**：Updated evidence cross-references.

  Tables 3-5; Figures S1-S5 -> Tables 3-5, S12-S16; Figures S1-S10

- **Table 6**：Updated evidence cross-references.

  Methods 4.2; Limitations; Figure S5 -> Methods 4.2, 4.4; Limitations; Figures S5-S10

## 未发现的问题

- 未发现需要删除的虚假引用，也未改动任何研究数字、指标方向或实验判断。
- 未把句式变化当作作者身份证据，也未对作者身份作任何推断。
- 未发现连续冒号堆叠或成组的空泛排比；不存在的风格问题没有为了“改得多”而强行添加。
- 对已有引用，保留了原编号和基本立场。近距离 QML 分子预测工作继续按固定储层、Hamiltonian 特征、线路搜索、可训练残差和序列储层的适用范围分别表述。

## 逐项交付对照

本次共记录 31 处段落级修改和 15 处新增或重排。完整修改日志见 `Manuscript_Revision_Changes.json`；本报告保留具有代表性的上下文对照，没有把所有改动机械展开。

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

本轮与另一对话框合并后共记录 36 处中英文段落级、
章节级或表项级修改。完整逐项记录见 `Bilingual_Revision_Changes.json`。

