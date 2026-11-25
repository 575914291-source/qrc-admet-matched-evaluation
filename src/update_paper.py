from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt

from src.config import PROJECT_ROOT, RESULTS_ROOT, TASKS


SOURCE = PROJECT_ROOT / "templates" / "source_manuscript.docx"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
OUTPUT = OUTPUT_ROOT / "论文修订稿_v2_TDC完整实验.docx"
ASSET_ROOT = RESULTS_ROOT / "manuscript"


DISPLAY = {
    "caco2_wang": "Caco-2",
    "hia_hou": "HIA",
    "pgp_broccatelli": "P-gp",
    "bioavailability_ma": "Bioavailability",
    "lipophilicity_astrazeneca": "Lipophilicity",
    "solubility_aqsoldb": "Solubility",
    "bbb_martins": "BBB",
    "ppbr_az": "PPBR",
    "vdss_lombardo": "VDss",
    "cyp2c9_veith": "CYP2C9 inhibition",
    "cyp2d6_veith": "CYP2D6 inhibition",
    "cyp3a4_veith": "CYP3A4 inhibition",
    "cyp2c9_substrate_carbonmangels": "CYP2C9 substrate",
    "cyp3a4_substrate_carbonmangels": "CYP3A4 substrate",
    "cyp2d6_substrate_carbonmangels": "CYP2D6 substrate",
    "half_life_obach": "Half-life",
    "clearance_hepatocyte_az": "Hepatocyte clearance",
    "clearance_microsome_az": "Microsome clearance",
    "ld50_zhu": "LD50",
    "herg": "hERG",
    "ames": "AMES",
    "dili": "DILI",
}


def set_paragraph(paragraph, text: str) -> None:
    paragraph.text = text


def set_run_font(run, size: float, bold: bool = False) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.bold = bold
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


def repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        tr_pr.append(header)


def style_table(table, widths_inches: list[float], header_fill: str = "D9E2F3") -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for row_index, row in enumerate(table.rows):
        prevent_row_split(row)
        for column_index, cell in enumerate(row.cells):
            cell.width = Inches(widths_inches[column_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    set_run_font(run, 7.5, bold=row_index == 0)
            if row_index == 0:
                shade_cell(cell, header_fill)
            elif row_index % 2 == 0:
                shade_cell(cell, "F5F7FA")
    repeat_header(table.rows[0])


def fill_table(table, rows: list[list[str]], widths: list[float]) -> None:
    if len(rows) != len(table.rows):
        raise ValueError(f"Expected {len(table.rows)} rows, got {len(rows)}")
    for row_index, values in enumerate(rows):
        if len(values) != len(table.columns):
            raise ValueError(
                f"Row {row_index}: expected {len(table.columns)} cells, got {len(values)}"
            )
        for column_index, value in enumerate(values):
            cell = table.rows[row_index].cells[column_index]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(str(value))
            set_run_font(run, 7.5, bold=row_index == 0)
    style_table(table, widths)


def format_ci(effect: float, low: float, high: float, digits: int = 3) -> str:
    return f"{effect:+.{digits}f} [{low:+.{digits}f}, {high:+.{digits}f}]"


def display_score(value: float) -> str:
    return f"{value:.3f}"


def add_references(document: Document, appendix_heading) -> None:
    entries = [
        "25. maplightrx. MapLight-TDC: reference implementation, commit c249378. GitHub, accessed 2026-11-25. https://github.com/maplightrx/MapLight-TDC",
        "26. Prokhorenkova L, Gusev G, Vorobev A, Dorogush A V, Gulin A. CatBoost: unbiased boosting with categorical features. NeurIPS, 2018. https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html",
        "27. Garg S, Garg S. Benchmarking Classical and Quantum Machine Learning for Potency Prediction across Ten Therapeutically Relevant Targets. ACS Medicinal Chemistry Letters, 2026. https://doi.org/10.1021/acsmedchemlett.5c00724",
        "28. Wang L, Zhang D, Wang C, et al. Coherent Floquet quantum reservoirs for molecular property prediction. arXiv:2609.11071, 2026. https://arxiv.org/abs/2609.11071",
        "29. Arab I, Barakat K. ToxTree: descriptor-based machine learning models for both hERG and Nav1.5 cardiotoxicity liability predictions. arXiv:2112.13467, 2021. https://arxiv.org/abs/2112.13467; dataset: https://doi.org/10.5281/zenodo.5807719",
        "30. Meng F, Xi Y, Huang J, Ayers P W. A curated diverse molecular database of blood-brain barrier permeability with chemical descriptors. Scientific Data, 2021. https://doi.org/10.1038/s41597-021-01069-5",
        "31. Robinson M C, Glen R C, Lee A A. Validating the validation: reanalyzing a large-scale comparison of deep learning and machine learning models for bioactivity prediction. Journal of Computer-Aided Molecular Design, 2020. https://doi.org/10.1007/s10822-019-00274-0",
    ]
    for text in entries:
        paragraph = appendix_heading.insert_paragraph_before(text)
        paragraph.style = document.styles["Normal"]
        for run in paragraph.runs:
            set_run_font(run, 9.5)


def replace_main_figure(document: Document) -> None:
    if not document.inline_shapes:
        raise RuntimeError("The source document has no inline figure")
    shape = document.inline_shapes[0]
    relationship_id = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
    image_part = document.part.related_parts[relationship_id]
    image_part._blob = (
        ASSET_ROOT / "figures" / "figure4_primary_effects.png"
    ).read_bytes()
    shape.width = Mm(158)
    shape.height = Mm(169)


def find_paragraph(document: Document, prefix: str):
    for paragraph in document.paragraphs:
        if " ".join(paragraph.text.split()).startswith(prefix):
            return paragraph
    raise KeyError(f"Paragraph not found: {prefix}")


def add_picture_before(
    anchor,
    image_path: Path,
    width_inches: float,
    alt_text: str,
):
    paragraph = anchor.insert_paragraph_before()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    shape = paragraph.add_run().add_picture(
        str(image_path),
        width=Inches(width_inches),
    )
    shape._inline.docPr.set("descr", alt_text)
    shape._inline.docPr.set("title", alt_text)
    return paragraph


def add_caption_before(anchor, text: str):
    paragraph = anchor.insert_paragraph_before(text)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(8)
    for run in paragraph.runs:
        set_run_font(run, 9.5, bold=False)
    return paragraph


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, OUTPUT)
    document = Document(OUTPUT)
    replace_main_figure(document)
    paragraphs = document.paragraphs

    endpoint = pd.read_csv(ASSET_ROOT / "tables" / "endpoint_results.csv")
    effects = pd.read_csv(ASSET_ROOT / "tables" / "effects.csv")
    counts = pd.read_csv(ASSET_ROOT / "tables" / "direction_counts.csv")
    numbers = json.loads(
        (ASSET_ROOT / "manuscript_numbers.json").read_text(encoding="utf-8")
    )

    set_paragraph(
        paragraphs[0],
        "固定量子储层残差在 TDC ADMET 上的随机实现与强基线对照评估",
    )
    set_paragraph(
        paragraphs[1],
        "A Matched Evaluation of Fixed Quantum Reservoir Residuals on TDC ADMET with Random Realizations and Strong Baselines",
    )
    set_paragraph(
        paragraphs[3],
        "量子分子特征的已报告增益常因缺少同容量经典对照、多随机实现、强基座和跨来源验证而难以解释。我们在 TDC ADMET 的 22 个官方端点上建立一套经校准、可复现的匹配评估流程，以 Morgan-ExtraTrees 和 MapLight-CatBoost 为基座，比较精确模拟的五比特幅度编码储层、实正交二次映射和随机傅里叶特征。五个骨架划分和每族五个平均映射用于控制随机性。未门控 QRC 相对正交对照在 ExtraTrees 上为 6 个端点更好、16 个更差，在 CatBoost 上为 3 个更好、19 个更差；Holm 校正后没有正向显著端点，而有三个负向显著端点。门控、联合校正、低数据、有限 shots、模拟噪声和有限参数族搜索均未产生跨基座稳定增量。外部验证呈来源依赖：CatBoost 在 293 个非重叠 hERG 分子上比门控正交对照高 0.040 AUROC，但 2,317 个 B3DB BBB 分子在两个基座上均显著更差。hERG 增益同时包含 QRC 相对基座的提升和正交分支相对基座的下降；连续标签排序与独立 pIC50 回归均未通过统一多重校正。已知信号校准能够恢复 QRC 和经典二次目标，无信号对照错误阳性率为 2.0% 至 4.7%；八阶 Trotter 化 Qiskit/Aer 审计显示读出秩在错误下保持较高，但幅度显著收缩。骨架、最近邻和理化性质分析不支持简单化学空间解释。本文的主要贡献是一套经校准的量子分子特征评估流程；结论仅适用于当前五比特固定储层、15 维 Pauli 读出、线性残差头和精确状态向量仿真，不能推广为对其它编码、可训练线路、更大储层或真实硬件的一般否定。",
    )
    set_paragraph(
        paragraphs[4],
        "关键词　ADMET；TDC；量子储层；匹配经典对照；随机实现；验证集门控",
    )
    set_paragraph(
        paragraphs[6],
        "ADMET 预测覆盖二分类、连续值和排序端点，不同任务的样本规模、测量分辨率和化学空间差异很大。TDC 提供固定测试集、任务专属指标和骨架划分接口，使方法能够按端点复核。[1,2] 分子表示、模型家族和测试划分本身足以改变模型排序，[3–6] 因此，量子特征的价值不能通过与单一弱基座比较来推断。",
    )
    set_paragraph(
        paragraphs[7],
        "本文固定一个范围明确的问题：在相同输入、相同 15 维读出和相同线性残差头下，固定五比特储层是否比实正交二次映射和随机傅里叶特征提供增量？这一增量是否同时出现在 Morgan-ExtraTrees 与 MapLight-CatBoost 两个基座、22 个 TDC 端点和独立外部来源上？研究设计见 Figure 1。本文有三项贡献。第一，将当前 QRC 及其线性残差头形式化为受约束的实二次特征族，并构造同输入、同容量、同映射预算的正交二次对照。第二，在 22 个官方端点上联合检验经典基座、验证门控和多重统计校正。第三，用低数据、有限 shots、模拟噪声、有限参数族搜索、双外部队列、连续标签、独立 pIC50 回归和化学空间审计划定结论边界。",
    )
    add_picture_before(
        paragraphs[8],
        ASSET_ROOT / "figures" / "figure1_design.png",
        6.6,
        "研究流程：TDC 和外部数据经两套经典基座、PCA 幅度编码、QRC、实正交二次和随机傅里叶分支进入匹配残差和验证门控；底部说明15个Pauli读出属于受限实二次型。",
    )
    add_caption_before(
        paragraphs[8],
        "Figure 1　匹配评估流程。两类数据来源共享两套经典基座、32 维 PCA 幅度输入、五个映射的残差集成和相同门控预算；底部给出15个Pauli读出所对应的实二次型 qⱼ(a)=aᵀAⱼa，并说明实正交分支提供同维二次对照。",
    )
    set_paragraph(
        paragraphs[10],
        "TDC 的端点定义、固定测试集和评分接口支持复核，但公开官方测试并不等同于前瞻验证。骨架划分通常比随机划分更能反映结构变化，但仍可能保留近邻分子，也不能替代时间留出。[1–5] 本文使用修正的 MapLight 特征集与 CatBoost 作为强经典参照：[6,7,25,26] 1,024 位 Morgan count、1,024 位 Avalon count、315 维 ErG 和 200 个 RDKit 描述符。原实现的 count 指纹使用 int8，存在计数溢出；本文在生成特征时改为 int32。",
    )
    set_paragraph(
        paragraphs[12],
        "Beaulieu 等在分子活性数据上研究了固定储层和小样本学习。[8] Benson 等将 Hamiltonian 读数拼接到经典描述符后训练 CatBoost；Mansour 等报告了量子启发预处理在 AqSolDB 上的预测误差。[9,10] QCS-ADME 侧重线路搜索和仿真至硬件变化。[11] Jia 等比较了五比特幅度编码残差与参数匹配的实正交分支，但其编码器和预测头联合训练，任务也不是 ADMET。[12] 在 10 个靶点、48 个有效阈值任务上的近期基准没有发现量子分类器全局占优，只报告了稀疏或结构双峰靶点上的局部候选信号。[27] 2026 年的 Floquet-QRC 工作进一步把序列图事件和驱动储层用于分子预测，但研究的是不同输入与动力学设定。[28] 更广泛的量子机器学习基准研究同样表明，量子实现、非线性结构与经典对照条件必须分开检验。[13] Table 1汇总了这些研究与本文的关系；它们采用不同任务、量子组件和训练协议，不能用单一分数直接排序。",
    )
    set_paragraph(
        paragraphs[13],
        "本文据此固定主对照：在实幅度输入下，固定演化后的 Z/ZZ 期望可由一个实二次型表示；实正交映射产生相同数量、相同输入和相同读出的另一组二次型，因此能够检验储层结构本身是否具有预测价值。随机傅里叶特征作为第二类同维非线性对照。五个独立映射的集成同时用于三族，验证集不再为某一族提供额外候选。",
    )
    set_paragraph(
        paragraphs[15],
        "折外偏移、在验证数据上估计组合权重和分端点报告均已有明确先例。[14–16] Ark-ADMET 在 TDC 22 个端点上用内部验证选择表示与融合权重。[16] Robinson 等在 Journal of Computer-Aided Molecular Design 上重分析大规模生物活性模型比较，说明验证设计本身能够改变模型结论。[31] 本文对 QRC 和两个经典族使用完全相同的五映射平均与标量门控，测试标签不参与映射生成、残差拟合或权重选择。重复训练共享固定测试集，因此统计推断按测试骨架配对处理。[17]",
    )
    set_paragraph(
        paragraphs[17],
        "实验从 Harvard Dataverse 文件 4426004 获取 TDC ADMET 官方归档，SHA-256 为 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1。22 个端点合计包含 65,430 条官方训练/验证记录和 16,379 条带标签测试记录。13 个分类端点采用 AUROC 或 AUPRC，9 个回归端点采用 MAE 或 Spearman 相关系数。[2]",
    )
    set_paragraph(
        paragraphs[18],
        "对每个端点，将官方 train_val 表按 PyTDC 的 scaffold 逻辑使用种子 1–5 重切为 87.5% 训练和 12.5% 验证；外层官方 test 成员、标签和行序保持不变。逐端点检查确认 SMILES 均可解析，训练、验证、测试之间的规范化分子标识和 Bemis–Murcko 骨架均不重叠。[22] 每次外层训练内部再用三层分组折外预测生成基座偏移。所有测试结果均在配置锁定后生成。",
    )
    set_paragraph(
        paragraphs[19],
        "主比较使用未舍入预测，先逐 seed 计算官方指标，再取五个 seed 的均值。AUROC、AUPRC 和 Spearman 的差值定义为新方法减参照，MAE 的差值定义为参照减新方法，使正值统一表示改善。以测试骨架为单位进行 1,000 次配对自助重抽样，给出逐端点 95% 区间；以 1,999 次配对骨架置换计算主比较 p 值，并对 22 个端点使用 Holm 校正。[18–20] 另外报告预设小效应容差下的探索性 TOST：AUROC、AUPRC、Spearman 为 0.01 绝对单位，MAE 为基座 MAE 的 2%。TOST 由两个单侧检验构成；只有其90%置信区间完全落在预设等价边界内且等价检验经 Holm 校正后显著，才解释为“在实际容差下未观察到有意义差异”。结果按三类状态报告：Holm 显著的负差表示显著变差，Holm 显著的正差表示显著改善，等价检验显著表示统计等价，其余为未定；等价不表示两种模型具有相同机制或逐分子相同预测。这些容差是基准可解释性边界，不是临床阈值。",
    )
    add_caption_before(
        paragraphs[20],
        "Supplementary Table S1 给出每个端点的样本数、官方指标和标签摘要；Supplementary Table S2 给出主分析、次级分析、敏感性分析和外部验证的多重校正层级。TOST 在较紧、主分析和较宽容差下的端点计数列于 Supplementary Table S9。Figure 2 进一步给出 TDC、hERG 和 B3DB 的化学空间与基础理化性质分布。",
    )
    add_picture_before(
        paragraphs[20],
        ASSET_ROOT / "figures" / "figure2_chemical_space.png",
        6.3,
        "化学空间图：TDC、外部 hERG 和 B3DB 的 Morgan 指纹投影以及分子量、cLogP、TPSA 分布。",
    )
    add_caption_before(
        paragraphs[20],
        "Figure 2　化学空间与适用域背景。A，Morgan 半径 2、1,024 位指纹经 20 维 TruncatedSVD、标准化和二维 PCA 的投影；TDC 随机抽取 3,000 个唯一分子，B3DB 随机抽取 500 个唯一分子，hERG 使用全部 293 个分子。B–D，全部唯一 TDC、hERG 和 B3DB 分子的分子量、cLogP 与 TPSA 箱线图。箱线不显示离群点，以保持分布可读。",
    )
    set_paragraph(
        paragraphs[22],
        "Morgan-ExtraTrees 使用半径 2、512 位 Morgan 指纹，128 棵树、最小叶节点样本数 2 和平方根特征子集预算。回归不改变标签尺度，分类输出类别 1 的概率。每次外层验证使用对应 seed 独立训练；最终测试基座在完整外层训练集上重拟合，训练侧折外预测只用于拟合残差头。",
    )
    set_paragraph(
        paragraphs[23],
        "MapLight-CatBoost 使用修正后的 2,563 维特征缓存，固定 240 轮、深度 6、学习率 0.06；分类采用 Logloss，回归采用 MAE。半衰期、VDss 和两类清除率按原 MapLight 协议使用目标对数变换，其余回归使用原尺度。CatBoost 接受原生缺失值；缺失的 RDKit 描述符不填补为 0。两套基座使用相同外层 split 和内部 scaffold 折，避免比较差异来自数据划分。[25,26]",
    )
    set_paragraph(
        paragraphs[25],
        "对训练特征拟合标准化和 32 维 PCA，将 PCA 向量归一化后幅度编码到五个量子比特。固定哈密顿量由标准正态抽样的横场、纵场和环形近邻 ZZ 耦合组成，缩放因子分别为 0.4、0.7 和 0.25，演化时间为 0.5；构造后显式验证 Hermitian 性。读取五个单比特 Z 和十个两两 ZZ 期望，形成 15 维特征。线路演化和读出使用精确状态向量模拟；零向量映射到全零计算基态。精确仿真是本阶段刻意采用的受控实验设计：它隔离固定线路、编码和读出的函数表达能力，避免门误差、读出错误、串扰和比特连通性把“储层结构本身的表现”与“硬件缺陷造成的损失”混在一起。有限 shots 和 depolarizing 分析只用于压力测试，不替代真实硬件验证；硬件执行留作后续独立研究。",
    )
    design_rationale = paragraphs[26].insert_paragraph_before(
        "5 qubits 对应 32 个实幅度，因此 32 维 PCA 是本规模下唯一不截断或补零的完整幅度输入；15 个读出由 5 个单比特 Z 和 10 个两两 ZZ 期望构成，与每一对量子比特都保留二阶关联。该设置不是量子硬件容量声明，而是在5 qubits可实现精确状态向量、同维经典对照和完整五映射预算的最小闭合设计。令归一化 PCA 向量为 v，则输入幅度 aⱼ=vⱼ/‖v‖；哈密顿量 H 和演化 U=exp(−iHt) 固定，映射参数不通过测试标签训练。本文不调节 PCA 维度或读出集合，以避免在单一主基准中引入额外的容量搜索。",
        style=paragraphs[25].style,
    )
    for run in design_rationale.runs:
        set_run_font(run, 10.6)
    set_paragraph(
        paragraphs[28],
        "命题 1　对任一组固定的 15 个对角 Pauli 可观测 Dⱼ 和任意固定酉演化 U，归一化 32 维实输入 a 的读出满足 qⱼ(a)=aᵀAⱼa，其中 Aⱼ=Re(U†DⱼU)。因此，任一无截距线性读出组合都可写成 aᵀMa+b，即固定五比特 QRC 加线性残差头属于由至多 15 个实二次型约束的模型族。证明直接由 (Ua)†Dⱼ(Ua) 展开得到。该命题不表示 QRC 与任一实正交映射等价；它限定了在当前编码和读出下，量子结构能够提供的函数类。",
    )
    mapping_paragraph = paragraphs[29].insert_paragraph_before(
        "QRC、实正交二次和随机傅里叶三族各使用五个独立映射，映射种子固定为 20261101–20261105。实正交对照把 U 替换为随机实正交矩阵并沿用同一组 15 个对角读出，因此具有相同输入、读出数和拟合参数数，但不同的二次矩阵几何结构；随机傅里叶对照使用 15 维余弦特征。三族共享 PCA 输入、训练侧标准化和线性残差头，分类使用 L2 为 1 的 logistic 偏移模型，回归使用 alpha 为 10 的岭回归。五映射残差先取平均，再进入验证门控和测试评估。",
        style=paragraphs[28].style,
    )
    for run in mapping_paragraph.runs:
        set_run_font(run, 10.6)
    set_paragraph(
        paragraphs[30],
        "对每个端点、基座、外层 seed 和候选族，令 f₀(x) 为基座输出，Δₘ(x) 为第 m 族五映射平均残差，门控预测为",
    )
    set_paragraph(
        paragraphs[32],
        "验证集按端点主指标从 {0, 0.25, 0.5, 0.75, 1} 选择标量权重，同分优先较小权重。分类门控作用于 logit，回归门控作用于预测值。QRC 与每个经典族使用相同权重网格和相同五映射预算。主比较固定使用未门控 QRC 对实正交二次映射；随机傅里叶与门控比较作为次级分析。",
    )
    set_paragraph(
        paragraphs[33],
        "所有特征变换、折外偏移、残差头和门控权重均在对应训练或验证范围内确定。测试集只用于配置锁定后的最终预测与官方指标；主实验共包含 22 个端点 × 5 个外层 seed × 2 个基座 = 220 次基座拟合流程，每次基座流程内部含三次折外拟合和一次全训练拟合。",
    )

    summary_for_base = (
        endpoint.set_index(["base", "task", "metric"])
        .sort_index()
        .reset_index()
    )
    set_paragraph(
        paragraphs[36],
        "表 2 给出两套基座及未门控分支的五 seed 平均官方指标，Figure 4 同时展示端点级差异和区间。QRC 相对固定实正交二次对照，在 ExtraTrees 上为 6 个端点更好、16 个更差；在 CatBoost 上为 3 个更好、19 个更差。修正后的 CatBoost 基座本身在 21/22 个端点上优于 ExtraTrees，唯一例外是 CYP2C9 substrate 的 AUPRC。先前 pilot 中方向较一致的 BBB、hERG、Caco2 和 LD50 没有复现同样的信号：相对无残差基座，ExtraTrees 上仅 Caco2 与 LD50 为正，CatBoost 上仅 hERG 的点估计微正；相对实正交映射，两个基座均至多有 2/4 个端点为正，均无经多重校正的显著改善。",
    )
    set_paragraph(paragraphs[37], "表 2　两个基座及未门控分支的五 seed 平均官方指标")
    set_paragraph(paragraphs[39], "表 3　QRC 相对实正交二次映射的端点级效应与 Holm 校正")
    set_paragraph(
        paragraphs[41],
        "表 3 的效应已统一为正值表示 QRC 改善，括号内为以测试骨架聚类的 95% 配对自助区间。Holm 校正覆盖每个基座内的 22 个端点。三个 Holm 显著结果均为 QRC 较差：ExtraTrees 的 AMES（AUROC 差 −0.0115，Holm p=0.011）与 VDss（Spearman 差 −0.1127，Holm p=0.042），以及 CatBoost 的 Solubility（MAE 差 −0.0268，Holm p=0.011）。没有正向显著端点。",
    )
    set_paragraph(
        paragraphs[43],
        "门控把 QRC 权重在 ExtraTrees 的 47/110 次选择、CatBoost 的 55/110 次选择置零。门控后的 QRC 相对同规则门控的实正交映射，在 ExtraTrees 上为 11 好/11 差，在 CatBoost 上为 4 好/17 差/1 平。两者均无 Holm 显著正向端点；等价性分析中分别有 8 和 10 个端点落在预设小效应范围内，但其中不少是两种方法都被验证门控压回基座，因此不能解释为量子分支贡献。",
    )
    set_paragraph(paragraphs[44], "表 4　验证门控的代表性行为")
    set_paragraph(
        paragraphs[46],
        "小效应端点说明门控可以限制负迁移，但没有产生新的外推信息。ExtraTrees 的 Half-life 在门控后点估计改善 0.0616，Holm p 仍为 0.94；PPBR 的门控后差值仍为 −0.1531。CatBoost 的 Half-life 五个 seed 均将 QRC 权重置零，门控差异严格为零；Solubility 有三次选择将权重置零，残余差值为 −0.0010。",
    )
    set_paragraph(paragraphs[48], "表 5　跨端点点估计方向与 Holm 显著计数")
    set_paragraph(
        paragraphs[50],
        "QRC 相对随机傅里叶特征同样在 ExtraTrees 与 CatBoost 上各为 3 好/19 差。相对无残差基座，QRC 在 ExtraTrees 上为 6 好/16 差，在 CatBoost 上为 4 好/18 差，并分别出现 2 个和 5 个 Holm 显著负向端点。不同端点的指标单位不可直接相加，因此本文不报告跨 AUROC、AUPRC、MAE 和 Spearman 的原始差值均值。",
    )
    set_paragraph(
        paragraphs[51],
        "五个 QRC 映射按同一映射序号与实正交映射配对后，在同一端点内存在明显波动，但没有形成稳定的正向任务子集。完整逐映射指标和预测数组随复现包提供。",
    )
    joint_paragraph = paragraphs[52].insert_paragraph_before(
        "进一步允许 QRC 与正交分支联合进入残差模型，并在验证集上选择两个标量权重后，ExtraTrees 和 CatBoost 相对同规则门控正交映射分别为 12 好/10 差和 6 好/14 差/2 平；没有端点通过 Holm 正向校正。相对各自的无残差基座，ExtraTrees 有 10 好/12 差，其中包含 1 个正向和 1 个负向显著端点；CatBoost 为 7 好/14 差/1 平且没有显著改善。联合门控没有提供可迁移的 QRC 增量。",
        style=paragraphs[51].style,
    )
    for run in joint_paragraph.runs:
        set_run_font(run, 10.6)
    finite_paragraph = paragraphs[52].insert_paragraph_before(
        "有限采样敏感性面板覆盖 BBB、hERG、Caco2、LD50、PPBR、DILI、CYP2D6 inhibition 和 VDss。对每个 Pauli 读出独立模拟 1,024、4,096 和 16,384 shots，并在有限采样特征上重新拟合残差头。ExtraTrees 在三档预算下均为 QRC 对门控正交 5/3；CatBoost 分别为 2/6、1/7、1/7。增加 shot 数只使 CatBoost 的方向计数更接近精确模拟，没有出现随采样收敛而显现的量子增量。",
        style=paragraphs[51].style,
    )
    for run in finite_paragraph.runs:
        set_run_font(run, 10.6)
    low_data_heading = paragraphs[52].insert_paragraph_before(
        "5.4 低数据规模", style=document.styles["Heading 2"]
    )
    low_data_paragraph = paragraphs[52].insert_paragraph_before(
        "为检验 QRC 最有理论机会的小样本区间，我们在与有限采样相同的八个代表端点上使用 5%、10%、20%、40% 和完整训练集。为保持分类和回归的内层 scaffold 折可估计，单个子集至少使用 96 条记录，因此最小端点的实际比例高于名义比例；逐结果文件同时记录实际训练数。所有子集只从外层训练数据抽取，验证和测试成员保持不变。",
        style=paragraphs[51].style,
    )
    for run in low_data_paragraph.runs:
        set_run_font(run, 10.6)
    low_data_result_paragraph = paragraphs[52].insert_paragraph_before(
        "未门控 QRC 相对实正交映射在五档规模上的正向端点数为：ExtraTrees 2/8、0/8、1/8、0/8、2/8，CatBoost 1/8、0/8、1/8、0/8、1/8。验证门控可以显著减少退化，ExtraTrees 的 20% 规模达到 6/8 个正向端点，但同一比例下 CatBoost 仅为 4/8；其他规模也没有两个基座同步的正向集中。门控后的结果应解释为风险控制，而不是低数据量子优势。逐端点曲线见补充图 S1 与结果文件。",
        style=paragraphs[51].style,
    )
    for run in low_data_result_paragraph.runs:
        set_run_font(run, 10.6)
    external_heading = paragraphs[52].insert_paragraph_before(
        "5.5 独立外部端点", style=document.styles["Heading 2"]
    )
    external_paragraph = paragraphs[52].insert_paragraph_before(
        "外部验证使用 ToxTree hERG 测试集和 B3DB BBB 分类集。[29,30] hERG 按原作者二分类规则将 PIC50≥4.5 记为 blocker；去除与 TDC hERG 训练集和测试集重叠的规范分子后保留 293 个。B3DB 使用提供方的 BBB+/BBB− 标签，去除与 TDC BBB 重叠的规范分子后保留 2,317 个。DeepChem ESOL 与 TDC AqSolDB 的规范分子几乎完全重合，去重后仅剩 18 个非重叠样本，因此不纳入结果。",
        style=paragraphs[51].style,
    )
    for run in external_paragraph.runs:
        set_run_font(run, 10.6)
    external_result_paragraph = paragraphs[52].insert_paragraph_before(
        "在 hERG 外部集上，门控 QRC 相对同规则门控正交界在 ExtraTrees 上高 0.0112 AUROC（95% CI [−0.0029, 0.0246]，Holm p=0.200），在 CatBoost 上高 0.0402（[0.0221, 0.0591]，Holm p=0.002）。在 B3DB BBB 上，同一比较在 ExtraTrees 上为 −0.0046（[−0.0076, −0.0019]，Holm p=0.002），在 CatBoost 上为 −0.0034（[−0.0065, −0.0006]，Holm p=0.016）。联合门控也重复了这一分化：hERG 的 CatBoost 正向差值为 0.0298，而 B3DB 在两个基座均为负且 Holm 显著。hERG 信号与 BBB 负迁移同时存在，说明固定 QRC 的表现依赖外部来源，不能支持普遍可迁移优势。外部效应的完整区间见 Supplementary Figure S2。",
        style=paragraphs[51].style,
    )
    for run in external_result_paragraph.runs:
        set_run_font(run, 10.6)
    external_diagnostics_paragraph = paragraphs[52].insert_paragraph_before(
        "为区分 QRC 的增益与正交分支的退化，我们进一步分解已有预测，结果见 Figure 3。CatBoost/hERG 中，门控 QRC 相对无残差基座为 +0.0285 AUROC（95% CI [0.0137, 0.0437]），门控正交相对基座为 −0.0117（[−0.0216, −0.0011]）；因此 +0.0402 的主比较差值同时包含 QRC 提升和正交分支下降。hERG 的 QRC 对正交 AUPRC 差为 +0.0304，Brier 与 log-loss 改善分别为 +0.0038 与 +0.0363；但两分支的校准斜率仅约 0.15–0.26，概率仍明显失校准。B3DB 中 QRC 对正交 AUPRC 在 ExtraTrees 与 CatBoost 上分别为 −0.0047 和 −0.0061，Brier 与 log-loss 亦不支持 QRC。完整分解与校准数值见 Supplementary Table S7 和 S8。连续排序迁移分析显示，CatBoost 的 hERG pIC50 Spearman 差为 +0.043（未校正 p=0.020），但在 12 个比较的 Holm 校正后消失；BBB logBB 未复现。该排序迁移不是独立训练的连续值回归，且 B3DB 子集阳性率为 86.8%。",
        style=paragraphs[51].style,
    )
    for run in external_diagnostics_paragraph.runs:
        set_run_font(run, 10.6)
    add_picture_before(
        paragraphs[52],
        ASSET_ROOT / "figures" / "figure3_external_diagnostics.png",
        6.25,
        "外部验证分解与校准：hERG 和 B3DB 中 QRC、正交分支相对基座的 AUROC 差，以及 CatBoost 五种子平均概率的校准曲线。",
    )
    add_caption_before(
        paragraphs[52],
        "Figure 3　外部分类的效应分解与校准。A–B，门控 QRC、门控正交相对基座，以及 QRC 相对正交的 AUROC 差；正值表示前者更好。C–D，CatBoost 五种子平均预测概率的五分位校准曲线；虚线为完美校准。分解用于解释主比较，不替代预先规定的外部 AUROC 检验。",
    )
    noise_heading = paragraphs[52].insert_paragraph_before(
        "5.6 模拟退相干", style=document.styles["Heading 2"]
    )
    noise_paragraph = paragraphs[52].insert_paragraph_before(
        "作为受控噪声压力测试，我们在同一八个端点上加入局部单比特 depolarizing 模型，概率分别为 0.001、0.005 和 0.010，并固定 4,096 shots。对称 depolarizing 将 Z 期望乘以 λ=1−4p/3，将 ZZ 期望乘以 λ²；残差头在含噪特征上重新拟合。该模型不包含门特异误差、泄漏、串扰或真实硬件连通性，因此只用于判断结论对可控读出衰减是否敏感。",
        style=paragraphs[51].style,
    )
    for run in noise_paragraph.runs:
        set_run_font(run, 10.6)
    noise_result_paragraph = paragraphs[52].insert_paragraph_before(
        "三档噪声下，QRC 相对门控正交映射的更好/更差端点计数保持不变：ExtraTrees 为 5/3，CatBoost 为 1/7。相对各自基座，ExtraTrees 为 3/5，CatBoost 为 2/6。噪声没有解锁新的稳定收益，且随概率从 0.001 增至 0.010，结果没有出现方向性转变。补充图 S3 给出噪声敏感性的补充记录；完整逐 split 结果随复现包提供。",
        style=paragraphs[51].style,
    )
    for run in noise_result_paragraph.runs:
        set_run_font(run, 10.6)
    tuning_heading = paragraphs[52].insert_paragraph_before(
        "5.7 有限储层族搜索", style=document.styles["Heading 2"]
    )
    tuning_paragraph = paragraphs[52].insert_paragraph_before(
        "为避免“只测试了一个随机储层”的批评，我们预注册了五组固定参数族：baseline、weak、strong、short 和 long，每组包含五个独立量子映射；同时构造五组各含五个独立映射的实正交候选。每个候选先做五映射残差集成，再用 TDC valid 选择门控权重；QRC和正交界在 test 前拥有相同的候选数量和映射预算。",
        style=paragraphs[51].style,
    )
    for run in tuning_paragraph.runs:
        set_run_font(run, 10.6)
    tuning_result_paragraph = paragraphs[52].insert_paragraph_before(
        "在八个代表端点上，验证集选择后的 QRC 相对正交界为好/差计数：ExtraTrees 4/4，CatBoost 2/5/1 平。没有任何端点通过 Holm 正向校正。baseline 参数仍是最常被选择的配置（ExtraTrees 15/40，CatBoost 25/40），说明候选搜索有效但扩展参数族没有产生新的稳定信号。相对各自无残差基座，ExtraTrees 为 4/4，CatBoost 为 2/5/1；VDss 在两个基座上都显示了显著负向差异。该搜索进一步缩小了“调参不足”能解释当前未观测到稳定增量的空间。",
        style=paragraphs[51].style,
    )
    for run in tuning_result_paragraph.runs:
        set_run_font(run, 10.6)
    set_paragraph(
        paragraphs[53],
        "Figure 4　未门控 QRC 相对实正交二次映射的端点级差异。分类指标按绝对单位，MAE 按参照 MAE 的相对百分比，Spearman 按绝对单位分面展示；线段为 95% 骨架聚类自助区间，红色表示 Holm 校正后显著。",
    )
    discussion_heading = find_paragraph(document, "6 讨论")
    discussion_heading.insert_paragraph_before(
        "5.8 独立连续 pIC50 回归与电路级错误审计",
        style=document.styles["Heading 2"],
    )
    regression_paragraph_1 = discussion_heading.insert_paragraph_before(
        "为避免把二分类概率的连续排序等同于真正的连续值预测，我们补充了固定的 ToxTree hERG pIC50 外部回归。来源 Dev-set 在去除 TDC 重叠后按 Bemis–Murcko 骨架切分为6,895条训练和985条验证记录；来源 Test-set 再去除与 TDC 以及外部训练骨架重叠的分子，保留214条测试记录、155个测试骨架。QRC、正交二次、随机傅里叶和线性残差头沿用TDC主协议，未使用外部测试标签选择映射种子、PCA维度、正则化或超参数。",
        style=paragraphs[53].style,
    )
    regression_paragraph_2 = discussion_heading.insert_paragraph_before(
        "五个模型种子的连续回归未显示可确认的 QRC 增量。QRC 对正交制的 Spearman 差在ExtraTrees上为+0.0229（95% CI [−0.0121, 0.0608]），在CatBoost上为+0.0093（[−0.0168, 0.0325]）；QRC对CatBoost基座为+0.0292（[−0.0034, 0.0604]）。MAE差异接近零。对12个指标、基座和对照比较统一作Holm校正后，没有任何比较显著。该外部队列独立于TDC标签，但只有214个分子，不能单独提供高功效验证；完整结果见 Supplementary Figure S4 和 Supplementary Table S10。为检查实际线路噪声下的读出保真度，我们将 32 维幅度制备、八阶 Lie–Trotter 固定 Hamiltonian 演化和全比特 Z 基测量实现为 Qiskit 线路。面板覆盖 8 个代表端点、每个端点 32 个分层测试态和五个储层映射；转译线路深度 81，平均约 136 个操作。Aer 密度矩阵模拟同时加入单比特门、双比特门 depolarizing 错误和独立读出翻转。低、中、高三档错误下，相对精确矩阵读出的归一化 RMSE 分别为 0.189–0.199、0.337–0.351 和 0.551–0.569，信号斜率分别约为 0.81、0.66 和 0.45，而 Spearman 秩相关仍分别为 0.9974–0.9986、0.9916–0.9958 和 0.9742–0.9866。八阶线路在没有噪声时的 RMSE 为 0.0058–0.0070。该结果说明电路级错误主要造成读出幅度收缩，同时保持较强的相对排序；它是读出保真度审计，不是对噪声特征重新训练预测器的端到端实验。完整结果见 Supplementary Figure S5 和 Supplementary Table S11。",
        style=paragraphs[53].style,
    )
    for run in regression_paragraph_1.runs:
        set_run_font(run, 10.6)
    for run in regression_paragraph_2.runs:
        set_run_font(run, 10.6)

    set_paragraph(
        paragraphs[56],
        "在实幅度输入下，固定演化的每个 Z 或 ZZ 期望都可由一个实对称矩阵的二次型精确计算。训练侧标准化是逐特征仿射变换，因此线性读头只是在组合这些二次型并加上固定偏移。给定训练后的参数，QRC 残差可由一个实二次型和一个常数复现；该结构针对归一化的 32 维潜在输入，而不是原始分子图。五个 QRC 映射的读出矩阵秩均为 15，条件数中位数为 1.210；实正交映射的条件数为 1.000。两者名义容量相同，差异来自二次矩阵的几何结构。",
    )
    set_paragraph(
        paragraphs[57],
        "在本基准中，实正交二次映射在 ExtraTrees 上于 16/22、在 CatBoost 上于 19/22 个端点的点估计优于 QRC。结合五个随机实现的平均，结果没有支持“固定 Ising 储层结构比一般二次映射更适合 ADMET”的假设。这一结果与近期跨靶点 QML 基准中“局部候选信号存在、但无全局优势”的结论方向一致。[27] 该结论只覆盖当前五比特幅度编码、读出和精确模拟，不涉及不同编码、可训练线路或硬件噪声下的优势。[12,13,28]",
    )
    set_paragraph(
        paragraphs[59],
        "门控的收益主要来自停止不利残差，而不是发现可迁移的量子校正。在 CatBoost 上，一半的端点-split 选择把 QRC 权重置零；门控后仍有 17 个端点差于同规则正交分支。等价性分析显示若干端点接近零差异，但这与“量子分支被抑制”一致，不能替代正向优越性检验。门控可作为风险控制规则，本文不把它解释为分子级预测置信度。",
    )
    set_paragraph(
        paragraphs[61],
        "强基座实验是本文与先前初步 pilot 的关键差异。多指纹 CatBoost 在 21/22 个端点优于 Morgan-ExtraTrees，但 QRC 在该基座上的相对表现进一步下降。联合门控允许 QRC 与正交分支一起使用，仍未得到跨端点稳定增量；有限采样、低数据曲线、模拟退相干和电路级 Aer 错误审计也没有改变该结论。外部 hERG 的 CatBoost 正向结果说明量子分支可能在特定来源上保留候选信号，pIC50 的排序迁移和独立连续回归都呈现同一弱方向，但前者未通过12项 Holm 校正，后者的95%区间跨零且无任何校正后显著比较。B3DB 的 logBB 迁移接近零，且 BBB 分类的显著负迁移排除了“跨来源稳健”解释。对计算药物设计实践而言，固定幅度编码 QRC 目前不应作为通用 ADMET 描述符；后续若提出新的量子编码，应直接在这类强基座上报告，并保留同输入、同容量、同候选预算的经典对照、真正独立的回归队列和外部来源验证。",
    )
    chemical_heading = paragraphs[62].insert_paragraph_before(
        "6.4 化学空间与数据集来源对信号的影响",
        style=document.styles["Heading 2"],
    )
    chemical_space_paragraph = paragraphs[62].insert_paragraph_before(
        "为检验外部差异是否可由化学来源解释，我们补充了描述性化学空间审计。将规范非手性 SMILES 与同端点 TDC 全归档比较，两个外部集在准备阶段均无精确重复。hERG 的293个分子中，23个（7.8%）保留一个出现在TDC训练/验证集中的Bemis–Murcko骨架；到TDC训练/验证集最近Morgan（半径2，2048位）Tanimoto相似度的中位数为0.234，90分位为0.423。B3DB BBB的2,317个分子中，562个（24.3%）与训练/验证集共享骨架，对应中位数为0.346，90分位为0.722。B3DB阳性率为48.9%，低于TDC BBB全归档的76.4%；hERG外部阳性率为76.4%，TDC为68.9%。这些数字说明两个外部集与各自TDC来源的接近程度和标签构成本身不同。",
        style=paragraphs[61].style,
    )
    chemical_result_paragraph = paragraphs[62].insert_paragraph_before(
        "在按上述骨架分组重算已有预测时，CatBoost的hERG门控QRC减正交界在共享骨架子组为−0.0026 AUROC（23个分子），在未见骨架子组为+0.0452（270个）；最近邻相似度最高四分之一子组为+0.0196，其余三个四分位为+0.0494。也就是说，hERG的正向点估计并未集中在与TDC共享骨架的分子上，现有数据不支持“骨架重叠导致hERG增益”的简单解释。BBB的负效应在共享骨架、未见骨架和近邻相似度分层中均存在。完整来源审计与hERG分层见Supplementary Table S5和S6。上述分层只定位信号出现的化学子集，没有控制来源、测定批次或标签定义，不能据此推断因果化学机理。",
        style=paragraphs[61].style,
    )
    chemical_scope_paragraph = paragraphs[62].insert_paragraph_before(
        "从任务性质看，低维固定量子储层理论上更可能受益于训练样本少、局部非线性相互作用强、且经典核表示不能充分覆盖的任务。TDC ADMET的全局端点通常样本较多且标签来源异质，这正是本套设置难以出现稳定增量的区域；低数据曲线也没有在两个基座上同步出现正向集中。该观察不排除角度编码、任务条件幅度编码、可训练量子线路、更大比特数或不同读出策略在其它任务上的可能性，但这些方案必须在同类强基座和独立来源上重新检验。",
        style=paragraphs[61].style,
    )
    chemical_interpretation_paragraph = paragraphs[62].insert_paragraph_before(
        "hERG的点估计改善只能作为待验证的候选信号，不能等价为量子特征学到了心脏毒性机理；B3DB的显著负迁移也不能解释为量子方法在ADMET中普遍无效。本文直接回顾的QML-ADMET研究分别采用固定储层、Hamiltonian衍生特征、量子启发预处理、线路搜索或联合训练残差，任务数量、对照和外部验证设置不同，不能作等价比判；正文Table 1给出主要对照，扩展表见Supplementary Table S4。本文提供的是一套可复用的最低评估流程：预先固定主对照、匹配候选与映射预算、按骨架聚类推断、进行多重检验和等价性解释，并报告跨基座及跨来源结果。",
        style=paragraphs[61].style,
    )
    computational_scope_paragraph = paragraphs[62].insert_paragraph_before(
        "计算资源方面，五个量子比特的精确状态向量仿真本身不是量子加速演示，也不提供硬件运行时间估计。本文选择该规模是为了精确构造同输入、同读出数的二次型对照，并避免噪声把线路表达能力与硬件缺陷混杂。当前结果既不支持量子运行优势，也不能用于推断更大量子储层、容错量子计算或特定硬件拓扑的可行性；这些属于不同实验问题。",
        style=paragraphs[61].style,
    )
    for paragraph in (
        chemical_space_paragraph,
        chemical_result_paragraph,
        chemical_scope_paragraph,
        chemical_interpretation_paragraph,
        computational_scope_paragraph,
    ):
        for run in paragraph.runs:
            set_run_font(run, 10.6)
    benchmark_standard_paragraph = paragraphs[62].insert_paragraph_before(
        "为使本研究结论可被后续工作直接复核，Table 6将上述对照原则整理为一套最低报告要求。该表不是对其它量子架构的预设结论，而是用于判断任何固定线路QML分子特征研究是否具备可比较、可迁移证据的检查清单。",
        style=paragraphs[61].style,
    )
    for run in benchmark_standard_paragraph.runs:
        set_run_font(run, 10.6)
    standard_rows = [
        ["Requirement and implementation", "Primary evidence"],
        [
            "Same 32D input, 15 Pauli readouts, and linear residual head",
            "Figure 1; Proposition 1; Table 3",
        ],
        [
            "Matched randomness: five independent maps per family and five scaffold splits",
            "Methods 4.2; Table 3",
        ],
        [
            "Two strong classical bases: Morgan-ExtraTrees and MapLight-CatBoost",
            "Table 2; Table 3",
        ],
        [
            "Scaffold-clustered inference with Holm and TOST",
            "Methods 3; Figure 4; Table 5",
        ],
        [
            "Independent sources: ToxTree hERG and B3DB BBB, including continuous-label checks",
            "Figure 3; Tables S7-S10",
        ],
        [
            "Report all endpoint effects, gate choices, low-data, shots, noise, and family search",
            "Tables 3-5; Figures S1-S5",
        ],
        [
            "Claim boundaries: exact simulation, circuit-level noise, and hardware are reported separately",
            "Methods 4.2; Limitations; Figure S5",
        ],
    ]
    standard_table = document.add_table(rows=len(standard_rows), cols=2)
    fill_table(standard_table, standard_rows, [4.7, 1.8])
    for row in standard_table.rows[1:]:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    standard_caption = paragraphs[62].insert_paragraph_before(
        "Table 6　固定线路QML分子特征研究的最低匹配评估要求。"
    )
    standard_caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
    standard_caption.paragraph_format.keep_with_next = True
    standard_caption.paragraph_format.space_after = Pt(4)
    for run in standard_caption.runs:
        set_run_font(run, 9.5)
    paragraphs[62]._p.addprevious(standard_table._tbl)
    set_paragraph(
        paragraphs[63],
        "公开官方固定测试集支持可复现对照，但可能与历史公共排行榜反复接触，不能作为独立前瞻验证。不同 Murcko 骨架之间仍可能相似，跨实验室、时间和化学系列的外推需要另行评估。精确状态向量仿真是为了隔离线路表达能力而采用的受控设计，不能替代真实硬件上的门误差、读出串扰、连通性和调度验证。预设等价边界用于探索性解释，不代表临床或监管可接受的最小效应。[3–5,21]",
    )
    set_paragraph(
        paragraphs[64],
        "本研究只评估每分子独立输入和一次固定五比特演化。主噪声敏感性采用简化局域 depolarizing 模型；补充的 Qiskit/Aer 审计加入转译后门级 depolarizing 和独立读出翻转，但仍使用固定线路与合成错误参数，没有模拟泄漏、串扰、漂移、硬件连通性或真实测量调度，也没有在电路噪声特征上重新训练完整预测器。低数据分析只覆盖八个代表端点，较小端点受96条最小训练集约束，不能代表所有ADMET任务的比例曲线。外部验证的主分析仍只包含两个分类端点；hERG与TDC二分类阈值虽已按来源说明对齐，但仍存在测定来源和标签生成差异。补充的连续标签排序只是把二分类输出用于连续标签，不是独立训练评估；独立pIC50回归使用214条测试记录和155个骨架，虽采用固定协议且无显著泄漏，但统计功效有限。B3DB的logBB仅在613/2,317个非重叠分子上可用，且阳性高度富集，不能代表完整BBB化学空间。化学空间图使用Morgan指纹的线性降维和三个基础描述符，不等于完整适用域模型；TOST计数也依赖预设容差。随机映射仅扩展到每个族五个实现；真实量子硬件上的执行成本、退相干和比特连通性未纳入推断。因此，本文的比较只适用于五比特、幅度编码、固定哈密顿储层、15维Pauli读出、线性残差头和精确仿真组成的当前模型族；不能由此推断其它量子表示或真实硬件同样缺少价值。TDC官方测试集的重复使用也可能压低对未见化学系列的泛化能力。",
    )
    set_paragraph(
        paragraphs[66],
        "在TDC ADMET的22个官方端点上，固定五比特储层残差没有表现出相对同容量实正交二次映射的稳定增量；这一结果在Morgan-ExtraTrees和更强的MapLight-CatBoost基座上均成立。验证门控可以把部分不利残差压回经典基座，但没有产生稳定超越门控经典的证据。外部hERG与B3DB BBB的分歧，以及骨架、近邻相似度和理化性质分层的结果，将现有证据限定为来源依赖的局部信号，而不是可识别的通用化学规律。连续标签排序和独立pIC50回归都只在CatBoost/hERG上显示未校正的弱正向方向，统一Holm校正后没有显著比较，不能支持稳定回归增量。八阶 Trotter 化电路级错误审计显示，低至中等噪声主要收缩读出幅度而保持较高排序相关，未提供额外优势证据。本文的主要贡献是给出一套可复核的QML分子预测评估流程，并把结论限定于五比特幅度编码、固定哈密顿储层、15维Pauli读出、线性残差头和精确仿真的当前设置；其它编码、可训练线路、更大比特数和真实硬件仍需独立评价。",
    )
    set_paragraph(
        paragraphs[68],
        "TDC官方归档可通过Harvard Dataverse文件4426004获取，SHA-256为bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1。外部hERG数据来自Zenodo 5807719，BBB数据来自B3DB；两者的来源、标签规约、去重、精确结构重叠、Bemis–Murcko骨架重叠、最近邻相似度和理化性质审计随复现包提供。复现代码与结果索引公开于 https://github.com/575914291-source/qrc-admet-matched-evaluation，冻结版本为v1.5.1，提交归档另附完整逐split预测和补充材料。复现包还包含五seed scaffold划分、五个随机映射、基座配置、联合门控、有限shots、低数据曲线、外部端点分解与校准、连续标签、独立pIC50回归、简化与电路级噪声、有限参数族、TOST敏感性、统计脚本、环境锁定和图形生成代码。MapLight参考实现及其MIT许可证一并保留。官方测试标签仅用于锁定配置后的评分，不参与训练、地图生成、联合权重或门控选择。",
    )

    table_1 = document.tables[0]
    table_1.add_column(Inches(0.78))
    rows_1 = [["Endpoint", "Metric", "ET", "QRC-ET", "Orth-ET", "CB", "QRC-CB", "Orth-CB"]]
    endpoint_index = endpoint.set_index(["base", "task", "metric"])
    for spec in TASKS:
        et = endpoint_index.loc[("extra_trees", spec.name, spec.metric)]
        cb = endpoint_index.loc[("catboost", spec.name, spec.metric)]
        rows_1.append(
            [
                DISPLAY[spec.name],
                spec.metric,
                display_score(et.classical_base),
                display_score(et.qrc_ungated),
                display_score(et.real_orthogonal_ungated),
                display_score(cb.classical_base),
                display_score(cb.qrc_ungated),
                display_score(cb.real_orthogonal_ungated),
            ]
        )
    fill_table(table_1, rows_1, [1.15, 0.50, 0.62, 0.70, 0.73, 0.62, 0.70, 0.73])

    table_2 = document.tables[1]
    primary = effects[effects.comparison == "qrc_vs_matched"]
    primary_index = primary.set_index(["base", "task"])
    rows_2 = [["Endpoint", "Metric", "ET effect [95% CI]", "ET Holm p", "CB effect [95% CI]", "CB Holm p"]]
    for spec in TASKS:
        et = primary_index.loc[("extra_trees", spec.name)]
        cb = primary_index.loc[("catboost", spec.name)]
        rows_2.append(
            [
                DISPLAY[spec.name],
                spec.metric,
                format_ci(et.effect_better_positive, et.ci_low, et.ci_high),
                f"{et.holm_p:.3f}",
                format_ci(cb.effect_better_positive, cb.ci_low, cb.ci_high),
                f"{cb.holm_p:.3f}",
            ]
        )
    fill_table(table_2, rows_2, [1.08, 0.52, 1.58, 0.62, 1.58, 0.62])

    table_3 = document.tables[2]
    table_3.add_column(Inches(0.72))
    gates = pd.read_csv(RESULTS_ROOT / "report" / "gate_weights.csv")
    representative = [
        ("extra_trees", "half_life_obach"),
        ("extra_trees", "ppbr_az"),
        ("extra_trees", "ames"),
        ("catboost", "half_life_obach"),
        ("catboost", "ppbr_az"),
        ("catboost", "solubility_aqsoldb"),
    ]
    rows_3 = [["Base", "Endpoint", "Metric", "QRC gate weights", "Gated QRC−Orth [95% CI]", "Holm p"]]
    for base, task in representative:
        metric = next(spec.metric for spec in TASKS if spec.name == task)
        weights = gates[
            (gates.base == base) & (gates.task == task) & (gates.family == "qrc")
        ].sort_values("split_seed").weight
        effect = effects[
            (effects.base == base)
            & (effects.task == task)
            & (effects.comparison == "gated_qrc_vs_matched")
        ].iloc[0]
        rows_3.append(
            [
                "ET" if base == "extra_trees" else "CB",
                DISPLAY[task],
                metric,
                "/".join(f"{value:g}" for value in weights),
                format_ci(effect.effect_better_positive, effect.ci_low, effect.ci_high),
                f"{effect.holm_p:.3f}",
            ]
        )
    fill_table(table_3, rows_3, [0.45, 0.90, 0.55, 1.05, 1.65, 0.55])

    table_4 = document.tables[3]
    table_4.add_column(Inches(0.75))
    table_4.add_row()
    table_4.add_row()
    desired_counts = [
        ("extra_trees", "qrc_vs_matched", "ET: QRC − orth"),
        ("catboost", "qrc_vs_matched", "CB: QRC − orth"),
        ("extra_trees", "qrc_vs_fourier", "ET: QRC − Fourier"),
        ("catboost", "qrc_vs_fourier", "CB: QRC − Fourier"),
        ("extra_trees", "qrc_vs_base", "ET: QRC − base"),
        ("catboost", "qrc_vs_base", "CB: QRC − base"),
        ("extra_trees", "gated_qrc_vs_matched", "ET: gated QRC − orth"),
        ("catboost", "gated_qrc_vs_matched", "CB: gated QRC − orth"),
        ("extra_trees", "augmented_qrc_vs_matched", "ET: QRC + orth − orth"),
        ("catboost", "augmented_qrc_vs_matched", "CB: QRC + orth − orth"),
    ]
    count_index = counts.set_index(["base", "comparison"])
    rows_4 = [["Contrast", "QRC better", "QRC worse", "Holm positive", "Holm negative"]]
    for base, comparison, label in desired_counts:
        row = count_index.loc[(base, comparison)]
        rows_4.append(
            [
                label,
                str(int(row.positive)),
                str(int(row.negative)),
                str(int(row.holm_significant_positive)),
                str(int(row.holm_significant_negative)),
            ]
        )
    fill_table(table_4, rows_4, [2.15, 0.82, 0.82, 0.92, 0.92])

    appendix_table = next(
        table
        for table in document.tables
        if table.rows[0].cells[0].text.strip() == "端点"
    )
    appendix_table._element.getparent().remove(appendix_table._element)
    add_references(document, paragraphs[94])

    prior_studies = pd.read_csv(
        ASSET_ROOT / "tables" / "prior_qml_comparison.csv",
        encoding="utf-8-sig",
    )
    prior_rows = [
        ["Study", "Molecular setting", "Quantum/control focus", "Relation to this benchmark"],
        [
            "Beaulieu 2025",
            "Activity; small N",
            "Fixed QRC",
            "Adds 22 endpoints, two bases, and external tests",
        ],
        [
            "Benson 2026",
            "10 TDC tasks",
            "Hamiltonian + CatBoost",
            "Different hybrid model; matched residual test",
        ],
        [
            "Mansour 2026",
            "AqSolDB",
            "MI Hamiltonian + CatBoost",
            "Polynomial ablation motivates matched quadratic control",
        ],
        [
            "Zheng 2026",
            "8 class + 4 regression",
            "Circuit search",
            "Search versus fixed matched comparison",
        ],
        [
            "Jia 2026",
            "3 receptor-potency tasks",
            "Joint encoder + quantum residual",
            "Orthogonal control showed similar performance",
        ],
        [
            "Garg 2026",
            "10 targets; 48 tasks",
            "QSVM and VQC",
            "No global advantage; local sparse signals",
        ],
        [
            "Wang 2026",
            "Graph prefixes; gap",
            "Floquet QRC",
            "Sequence input and hardware; not ADMET-wide",
        ],
    ]
    prior_table = document.add_table(rows=len(prior_rows), cols=4)
    fill_table(prior_table, prior_rows, [0.9, 1.4, 1.8, 2.4])
    for row in prior_table.rows[1:]:
        for cell in row.cells[1:]:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    prior_caption = paragraphs[13].insert_paragraph_before(
        "表 1　代表性 QML 分子性质预测研究与本文评估范围的对照。不同研究在任务、编码和训练协议上不可直接数值等价。"
    )
    prior_caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
    prior_caption.paragraph_format.keep_with_next = True
    prior_caption.paragraph_format.space_after = Pt(4)
    for run in prior_caption.runs:
        set_run_font(run, 9.5)
    paragraphs[13]._p.addprevious(prior_table._tbl)

    for trailing in (paragraphs[94], paragraphs[95]):
        trailing._element.getparent().remove(trailing._element)
    document.save(OUTPUT)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

