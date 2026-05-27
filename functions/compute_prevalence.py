from typing import Optional

import pandas as pd
from statsmodels.stats.proportion import proportion_confint

# These columns are used to define unique variants
VARIANTS_GROUP_COLUMNS = [
    "gene",
    "chrom",
    "aa_pos",
]

# These groups are used to define a unique mutation, e.g. A127E
VARIANTS_MUTATION_COLUMNS = [
    "aa_change",
    "mut_type",
    "mutation",
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
    print(f"Additional groups: {additional_groups}")
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

    agg_aa_change_df = (
        variants_df.loc[variants_df["type"].isin(["mixed_mut", "mut"])]
        .groupby(
            VARIANTS_GROUP_COLUMNS + VARIANTS_MUTATION_COLUMNS + additional_groups,
        )
        .agg(
            n_mixed=pd.NamedAgg("type", lambda x: (x == "mixed_mut").sum()),
            n_mut=pd.NamedAgg("type", lambda x: (x == "mut").sum()),
        )
    )

    groups = (
        variants_df[VARIANTS_GROUP_COLUMNS + additional_groups]
        .drop_duplicates()
        .dropna()
    )
    muts = (
        variants_df[VARIANTS_GROUP_COLUMNS + VARIANTS_MUTATION_COLUMNS]
        .query("mut_type == 'missense'")
        .drop_duplicates()
        .dropna()
    )

    # Build full index so we see also values for groups that have no mutation
    full_index = (
        groups.merge(muts, how="inner", on=VARIANTS_GROUP_COLUMNS)
        .set_index(
            VARIANTS_GROUP_COLUMNS + VARIANTS_MUTATION_COLUMNS + additional_groups
        )
        .index
    )
    # Ensure all n_mut, n_mixed are filled with zeros
    agg_aa_change_df = agg_aa_change_df.reindex(full_index).reset_index().fillna(0)

    agg_aa_pos_df = variants_df.groupby(
        VARIANTS_GROUP_COLUMNS + additional_groups,
        as_index=False,
    ).agg(
        n_samples=pd.NamedAgg("type", "size"),
        n_passed=pd.NamedAgg("type", lambda x: sum(x != "filtered")),
        n_wt=pd.NamedAgg("type", lambda x: sum(x == "wt")),
    )

    prev_df = agg_aa_change_df.merge(
        agg_aa_pos_df,
        on=VARIANTS_GROUP_COLUMNS + additional_groups,
        how="left",
        validate="m:1",
    )

    # Compute frequencies
    prev_df["per_wt"] = 100 * prev_df["n_wt"] / prev_df["n_passed"]
    prev_df["per_mixed"] = 100 * prev_df["n_mixed"] / prev_df["n_passed"]
    prev_df["per_mut"] = 100 * prev_df["n_mut"] / prev_df["n_passed"]

    # Compute prevalence
    prev_df["prevalence"] = prev_df["per_mixed"] + prev_df["per_mut"]

    # Compute prevalence 95% confidence intervals
    low, high = proportion_confint(
        prev_df["n_mut"] + prev_df["n_mixed"],
        prev_df["n_passed"],
        alpha=0.05,
        method="beta",
    )
    prev_df["prevalence_lowci"] = 100 * low
    prev_df["prevalence_highci"] = 100 * high

    return prev_df
