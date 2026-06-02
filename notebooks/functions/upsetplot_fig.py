import warnings
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import upsetplot as up


def upsetplot_fig(
    variants_df: pd.DataFrame,
    gene: str,
    muts_dict: dict,
    ids_passed_QC: Optional[pd.DataFrame] = None,
    min_prevalence: Optional[float] = None,
) -> plt.Figure:
    """
    Generate an upset plot in a matplot figure based on the provided DataFrame and values column.
    Args:
        variants_df (pd.DataFrame): DataFrame containing all variant calls
        gene (str): Name of the gene to generate the plot for
        muts_dict (dict): Dictionary of mutations and combinations
        ids_passed_QC (pd.DataFrame): All samples (gene / amplicon level) that have passed QC
        min_prevalence (float): Minimum prevalence threshold under which mutations will be collapsed into a single category.
    Returns:
        plt.Figure: The generated upset plot as a matplotlib fig.
    """

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)

        ############################
        # Extract mutation metadata
        ############################
        target = muts_dict.get(gene, {})
        candidate = list(target.get("candidate", []))
        validated = list(target.get("validated", []))
        combinations = target.get("combinations", {})

        ############################
        # Filter variants
        ############################
        variants_df = variants_df[variants_df["gene"] == gene]
        all_ids = set(variants_df["sample_id"])
        # gt_int values: 0 = WT, 1 = het, 2 = hom mut, -1 = filtered out / no call
        variants_df = variants_df[variants_df["gt_int"] > 0]
        variants_df = variants_df[variants_df["mut_type"] == "missense"]

        ############################
        # Build mutation matrix
        ############################
        mutation_matrix = pd.crosstab(
            variants_df["sample_id"],
            variants_df["aa_change"],
        )
        mutation_matrix = mutation_matrix.astype(bool)

        ############################
        # Add WT samples
        ############################
        ids_nonref = set(variants_df["sample_id"])

        if ids_passed_QC is not None:
            ids_ref = set(
                ids_passed_QC.query("gene in @gene and sample_id not in @ids_nonref")[
                    "sample_id"
                ]
            )
        else:
            ids_ref = all_ids - ids_nonref

        wt_category_name = "WT"

        if len(ids_ref) > 0:
            new_rows_df = pd.DataFrame(
                False,
                index=list(ids_ref),
                columns=mutation_matrix.columns,
            )

            mutation_matrix[wt_category_name] = False
            new_rows_df[wt_category_name] = True
            mutation_matrix = pd.concat([mutation_matrix, new_rows_df])

        ############################
        # Handle empty/single-category
        ############################
        if mutation_matrix.empty or mutation_matrix.shape[1] == 1:
            if mutation_matrix.empty:
                text_msg = f"No data available for {gene}."
            else:
                text_msg = (
                    f"All samples are "
                    f"{list(mutation_matrix.columns)[0]} "
                    f"for {gene} so unable to plot"
                )

            fig = plt.figure(figsize=(4, 3))
            ax = fig.add_subplot(111)
            ax.text(
                0.5,
                0.5,
                text_msg,
                horizontalalignment="center",
                verticalalignment="center",
                transform=ax.transAxes,
            )
            ax.axis("off")
            return fig

        if min_prevalence is not None:
            test_columns = ["_sub-threshold"]
            subthres_name = "*"

            # Mark all samples without validated markers
            validated_present = [c for c in validated if c in mutation_matrix.columns]
            if len(validated) > 0 and len(validated_present) > 0:
                mutation_matrix["_no_validated_markers"] = ~mutation_matrix[
                    validated_present
                ].any(axis=1)
                test_columns.append("_no_validated_markers")

            # Identify min_count that relates to min_prevalence threhold
            min_count = round(len(mutation_matrix) * (min_prevalence / 100), 0)

            # Collapse matrix into a single column of tuples representing the mutation pattern for each sample
            mut_signatures = mutation_matrix.apply(
                lambda row: tuple(row),
                axis=1,
            )

            # Count each mutation combination
            mut_signature_counts = mut_signatures.value_counts()
            # Identify those below threshold and add to matrix
            subthresh_signatures = set(
                mut_signature_counts[mut_signature_counts < min_count].index
            )
            mutation_matrix["_sub-threshold"] = mut_signatures.apply(
                lambda x: True if x in subthresh_signatures else False
            )

            # Keep entries that are above the threshold and don't have validated markers
            mutation_matrix["_to_collapse"] = mutation_matrix[test_columns].all(axis=1)
            matrix_to_plot = mutation_matrix[~mutation_matrix["_to_collapse"]].drop(
                columns=test_columns + ["_to_collapse"],
            )

            # Create single category for all samples below threshold
            if any(mutation_matrix["_to_collapse"]):
                sample_ids = list(
                    mutation_matrix.index[mutation_matrix["_to_collapse"]].astype(str)
                )
                collapsed_rows = pd.DataFrame(
                    {
                        col: False
                        for col in mutation_matrix.columns
                        if col != "_to_collapse" and col not in test_columns
                    },
                    index=[sample_ids],
                )

                collapsed_rows[subthres_name] = True

                if subthres_name not in matrix_to_plot.columns:
                    matrix_to_plot[subthres_name] = False

                matrix_to_plot = pd.concat(
                    [matrix_to_plot, collapsed_rows], axis=0, ignore_index=True
                )

            # Remove WT category if present and if all entries are False
            if (
                wt_category_name in matrix_to_plot.columns
                and ~matrix_to_plot[wt_category_name].any()
            ):
                matrix_to_plot.drop(columns=[wt_category_name], inplace=True)
            mutation_matrix = matrix_to_plot.copy(deep=True)

        ############################
        # Convert to upset format and create upset object
        ############################
        upset_data = up.from_indicators(mutation_matrix)

        up_obj = up.UpSet(
            upset_data,
            subset_size="count",
            sort_by="cardinality",
            show_percentages="{:.0%}",
            show_counts=True,
        )

        ############################
        # WT styling
        ############################
        if wt_category_name in mutation_matrix.columns:
            up_obj.style_subsets(
                present=wt_category_name,
                facecolor="green",
            )

        ############################
        # Candidate styling
        ############################
        for c in candidate:
            if c in mutation_matrix.columns:
                up_obj.style_categories(
                    c,
                    shading_facecolor="lightgrey",
                    shading_linewidth=1,
                )

                up_obj.style_categories(
                    c,
                    bar_facecolor="tab:orange",
                    bar_hatch="xx",
                    bar_edgecolor="black",
                )

        ############################
        # Validated styling
        ############################
        for v in validated:
            if v in mutation_matrix.columns:
                up_obj.style_categories(
                    v,
                    shading_facecolor="darkgrey",
                    shading_linewidth=1,
                )

                up_obj.style_categories(
                    v,
                    bar_facecolor="tab:red",
                    bar_hatch="xx",
                    bar_edgecolor="black",
                )

        ############################
        # Create figure
        ############################
        fig = plt.figure(figsize=(6, 8))
        up_plot = up_obj.plot(fig=fig)

        ############################
        # Matrix axis
        ############################
        ax = up_plot["matrix"]

        ############################
        # Highlight specific nodes
        ############################
        cmap = plt.colormaps.get_cmap("Reds")

        colours = [
            cmap(x)
            for x in np.linspace(
                0.55,
                0.98,
                max(len(combinations), 1),
            )
        ]

        # Identify the intersections names and id in the up_obj
        intersections_idx = list(up_obj.intersections.index)
        intersections_names = list(up_obj.intersections.index.names)

        legend_names = []
        # Loop through each combination of mutations
        for colour_idx, (combo_name, members) in enumerate(combinations.items()):
            # Loop through each intersection (column)
            for col_idx, subset in enumerate(intersections_idx):
                muts_present = [
                    name
                    for name, present in zip(intersections_names, subset)
                    if present
                ]
                if all(x in muts_present for x in members):
                    # Identify appropriate combination nodes
                    for row_idx, mut in enumerate(intersections_names):
                        # Only highlight selected mutations
                        if mut in members:
                            if combo_name in legend_names:
                                ax.scatter(
                                    col_idx,
                                    row_idx,
                                    color=colours[colour_idx],
                                    s=80,
                                    zorder=20,
                                )
                            else:
                                ax.scatter(
                                    col_idx,
                                    row_idx,
                                    color=colours[colour_idx],
                                    s=80,
                                    zorder=20,
                                    label=combo_name,
                                )
                                # Add entry to list
                                legend_names.append(combo_name)
        if len(legend_names) > 0:
            fig.legend(loc="lower right", bbox_to_anchor=(1, 0))

        ############################
        # Formatting
        ############################

        if min_prevalence is not None:
            if subthres_name in mutation_matrix.columns:
                fig.text(
                    0.2,
                    0,
                    f"*combinations with <{min_prevalence}% prevalence collapsed into a single category",
                    ha="center",
                    fontsize=8,
                )

        up_plot["intersections"].set_title(
            f"{gene}",
            fontsize=16,
            pad=20,
        )
        up_plot["intersections"].set_ylabel("Count")
        up_plot["totals"].set_xlabel("Count")

        return fig
