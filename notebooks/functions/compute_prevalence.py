from typing import Optional

import pandas as pd
from statsmodels.stats.proportion import proportion_confint

# These columns are used to define unique variants
GENE_COL = "gene"
AA_CHANGE_COL = "aa_change"
AA_POS_COL = "aa_pos"
AA_CALL_COL = "aa_call"

REF_POS_COL = "ref_pos"

AA_GROUP_COLUMNS = [
    "chrom",
    GENE_COL,
    AA_POS_COL,
    AA_CHANGE_COL,
]

# Taken verbatim from nomadic
def compute_variant_prevalence(
    variants_df: pd.DataFrame,
    master_df: Optional[pd.DataFrame] = None,
    additional_groups: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Compute the prevalence of each mutation in `variants_df`
    """
    if additional_groups is None:
        additional_groups = []

    if additional_groups:
        assert master_df is not None, (
            "master_df must be provided if additional_groups are used"
        )
        assert all(group in master_df.columns for group in additional_groups), (
            "all additional_groups must be columns in master_df"
        )
        variants_df = variants_df.merge(
            master_df[["sample_id", *additional_groups]],
            on="sample_id",
            how="left",
            validate="m:1",
        )

    passed_types = {"mixed", "mutant", "absent", "wt"}

    # Precompute so we can use fast sum aggregation
    variants_df = variants_df.assign(
        _passed=variants_df[AA_CALL_COL].isin(passed_types),
        _wt=variants_df[AA_CALL_COL].eq("wt"),
        _mixed=variants_df[AA_CALL_COL].eq("mixed"),
        _mut=variants_df[AA_CALL_COL].eq("mutant"),
    )

    prev_df = variants_df.groupby(
        AA_GROUP_COLUMNS + additional_groups, as_index=False
    ).agg(
        n_samples=(AA_CALL_COL, "size"),
        n_passed=("_passed", "sum"),
        n_wt=("_wt", "sum"),
        n_mixed=("_mixed", "sum"),
        n_mut=("_mut", "sum"),
    )
    has_passing_samples = prev_df["n_passed"].ne(0)
    # Compute frequencies
    prev_df.loc[has_passing_samples, "per_wt"] = (
        100
        * prev_df.loc[has_passing_samples, "n_wt"]
        / prev_df.loc[has_passing_samples, "n_passed"]
    )
    prev_df.loc[has_passing_samples, "per_mixed"] = (
        100
        * prev_df.loc[has_passing_samples, "n_mixed"]
        / prev_df.loc[has_passing_samples, "n_passed"]
    )
    prev_df.loc[has_passing_samples, "per_mut"] = (
        100
        * prev_df.loc[has_passing_samples, "n_mut"]
        / prev_df.loc[has_passing_samples, "n_passed"]
    )

    # Compute prevalence
    prev_df.loc[has_passing_samples, "prevalence"] = (
        prev_df.loc[has_passing_samples, "per_mixed"]
        + prev_df.loc[has_passing_samples, "per_mut"]
    )

    # Compute prevalence 95% confidence intervals
    low, high = proportion_confint(
        prev_df.loc[has_passing_samples, "n_mut"]
        + prev_df.loc[has_passing_samples, "n_mixed"],
        prev_df.loc[has_passing_samples, "n_passed"],
        alpha=0.05,
        method="beta",
    )
    prev_df.loc[has_passing_samples, "prevalence_lowci"] = 100 * low
    prev_df.loc[has_passing_samples, "prevalence_highci"] = 100 * high

    return prev_df