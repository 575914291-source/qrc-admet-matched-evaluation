from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
OFFICIAL_DATA_ROOT = DATA_ROOT / "tdc_official" / "admet_group"
CACHE_ROOT = DATA_ROOT / "cache"
RESULTS_ROOT = PROJECT_ROOT / "results"


@dataclass(frozen=True)
class TaskSpec:
    name: str
    metric: str
    kind: str

    @property
    def binary(self) -> bool:
        return self.kind == "classification"

    @property
    def higher_is_better(self) -> bool:
        return self.metric != "MAE"


TASKS = (
    TaskSpec("caco2_wang", "MAE", "regression"),
    TaskSpec("hia_hou", "AUROC", "classification"),
    TaskSpec("pgp_broccatelli", "AUROC", "classification"),
    TaskSpec("bioavailability_ma", "AUROC", "classification"),
    TaskSpec("lipophilicity_astrazeneca", "MAE", "regression"),
    TaskSpec("solubility_aqsoldb", "MAE", "regression"),
    TaskSpec("bbb_martins", "AUROC", "classification"),
    TaskSpec("ppbr_az", "MAE", "regression"),
    TaskSpec("vdss_lombardo", "Spearman", "regression"),
    TaskSpec("cyp2c9_veith", "AUPRC", "classification"),
    TaskSpec("cyp2d6_veith", "AUPRC", "classification"),
    TaskSpec("cyp3a4_veith", "AUPRC", "classification"),
    TaskSpec("cyp2c9_substrate_carbonmangels", "AUPRC", "classification"),
    TaskSpec("cyp3a4_substrate_carbonmangels", "AUROC", "classification"),
    TaskSpec("cyp2d6_substrate_carbonmangels", "AUPRC", "classification"),
    TaskSpec("half_life_obach", "Spearman", "regression"),
    TaskSpec("clearance_hepatocyte_az", "Spearman", "regression"),
    TaskSpec("clearance_microsome_az", "Spearman", "regression"),
    TaskSpec("ld50_zhu", "MAE", "regression"),
    TaskSpec("herg", "AUROC", "classification"),
    TaskSpec("ames", "AUROC", "classification"),
    TaskSpec("dili", "AUROC", "classification"),
)

TASK_BY_NAME = {task.name: task for task in TASKS}

SPLIT_SEEDS = (1, 2, 3, 4, 5)
MAP_SEEDS = (20261101, 20261102, 20261103, 20261104, 20261105)
GATE_WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)
BASES = ("extra_trees", "catboost")
FAMILIES = ("qrc", "real_orthogonal", "random_fourier")
CIRCUIT_TASKS = (
    "bbb_martins",
    "herg",
    "caco2_wang",
    "ld50_zhu",
    "ppbr_az",
    "dili",
    "cyp2d6_veith",
    "vdss_lombardo",
)
PRIMARY_FAMILY = "qrc"
PRIMARY_MATCHED = "real_orthogonal"
BOOTSTRAP_REPLICATES = 1000
PERMUTATION_REPLICATES = 1999
LOG_TARGET_TASKS = {
    "vdss_lombardo",
    "half_life_obach",
    "clearance_hepatocyte_az",
    "clearance_microsome_az",
}

# Practical smallest effects used only for the exploratory TOST analysis.
# Classification and rank metrics use absolute units; MAE uses a relative
# threshold against the base-model MAE.
EQUIVALENCE_ABSOLUTE = {
    "AUROC": 0.01,
    "AUPRC": 0.01,
    "Spearman": 0.01,
}
EQUIVALENCE_MAE_RELATIVE = 0.02

