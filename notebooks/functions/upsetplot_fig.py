import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import upsetplot as up


def upsetplot_fig(
    variants_df: pd.DataFrame,
    genes: str | list[str],
    muts_dict: dict,
    ids_passed_QC: pd.DataFrame | None = None,
    min_prevalence: float | None = None,
    combinations_only: bool = False,
) -> plt.Figure:
    """
    Generate an upset plot in a matplot figure based on the provided DataFrame and values column.
    Args:
        variants_df (pd.DataFrame): DataFrame containing all variant calls
        genes (str | list(str)): Name of the gene(s) to generate the plot for
        muts_dict (dict): Dictionary of mutations and combinations
        ids_passed_QC (pd.DataFrame): All samples (gene / amplicon level) that have passed QC
        min_prevalence (float): Minimum prevalence threshold under which mutations will be collapsed into a single category.
        combinations_only (bool): Removes all data except for samples carrying a combination of defined mutations.
    Returns:
        plt.Figure: The generated upset plot as a matplotlib fig.
    """

    assert not (min_prevalence is not None and combinations_only), \
        "Specify either min_prevalence or combinations_only, not both."

    def filter_row(row):
        """
        Identifes the largest combination of mutations that match a sample
        """
        mutated = set(row.index[row])
        matched = [combo for combo in combo_sets if combo.issubset(mutated)]

        if not matched:
            return pd.Series(False, index=row.index)
        
        best_combo = max(matched, key=len)
        return pd.Series(row.index.isin(best_combo), index=row.index)
    
    if isinstance(genes, str):
        genes = [genes]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)

        ############################
        # Extract mutation metadata
        ############################
        candidate = []
        validated = []
        combinations = {}
        unique_combo_muts = []
        for gene in genes:
            target = muts_dict.get(gene, {})
            prefix = f"{gene}-" if len(genes)>1 else ""
            candidate += [f"{prefix}{c}" for c in target.get("candidate", [])]
            validated += [f"{prefix}{v}" for v in target.get("validated", [])]
            combos = target.get("combinations", {})
            for key, value in combos.items():
                mutations = [f"{prefix}{a}" for a in value]
                combinations[key] = mutations
                unique_combo_muts += [ m for m in mutations if m not in unique_combo_muts]

        ############################
        # Add in multigene combinations
        ############################
        if len(genes) > 1:
            multitarget = muts_dict.get("multigene", {})
            for gene_grp, values in multitarget.items():
                gs = gene_grp.split("-")
                if set(gs).issubset(genes):
                    combinations = combinations | values

        ############################
        # Filter variants
        ############################
        variants_df = variants_df[variants_df["gene"].isin(genes)]
        all_ids = set(variants_df["sample_id"])
        # gt_int values: 0 = WT, 1 = het, 2 = hom mut, -1 = filtered out / no call
        variants_df = variants_df[variants_df["gt_int"] > 0]
        variants_df = variants_df[variants_df["mut_type"] == "missense"]
        
        ############################
        # Build mutation matrix
        ############################
        mutation_matrix = pd.crosstab(
            variants_df["sample_id"],
            variants_df["mutation" if len(genes)>1 else "aa_change"],
        )
        mutation_matrix = mutation_matrix.astype(bool)
        
        ############################
        # Add WT samples
        ############################
        ids_nonref = set(variants_df["sample_id"])

        if ids_passed_QC is not None:
            ids_ref = set(
                ids_passed_QC.query("gene in @genes and sample_id not in @ids_nonref")[
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
                text_msg = f"No data available for {genes}."
            else:
                first_col = next(iter(mutation_matrix.columns))
                text_msg = (
                    f"All samples are "
                    f"{first_col} "
                    f"for {genes} so unable to plot"
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

        if combinations_only:
            drop_noncombo_cols = [f for f in mutation_matrix.columns if f not in unique_combo_muts ]
            mutation_matrix.drop(columns=drop_noncombo_cols, inplace=True)
            combo_sets = [set(c) for c in combinations.values()]
            mutation_matrix = mutation_matrix.apply(filter_row, axis=1)

        elif min_prevalence is not None:
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
                lambda x: x in subthresh_signatures
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
            totals_plot_elements=0 if combinations_only else 1,
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
        cmap = plt.colormaps.get_cmap("viridis")

        colours = [
            cmap(x)
            for x in np.linspace(
                0.1,
                1,
                max(len(combinations), 1),
            )
        ]

        # Identify the intersections names and id in the up_obj
        intersections_idx = list(up_obj.intersections.index)
        intersections_names = list(up_obj.intersections.index.names)

        legend_names = []
        combo_keys = list(combinations.keys())

        # Loop through each intersection (column) first
        for col_idx, subset in enumerate(intersections_idx):
            muts_present = [name for name, present in zip(intersections_names, subset) if present]

            # Find every combo fully contained in this intersection
            matching_combos = [
                (combo_name, members)
                for combo_name, members in combinations.items()
                if all(x in muts_present for x in members)
            ]

            if not matching_combos:
                continue

            # Keep only the most specific (largest) matching combo for this column
            combo_name, members = max(matching_combos, key=lambda item: len(item[1]))
            colour_idx = combo_keys.index(combo_name)

            for row_idx, mut in enumerate(intersections_names):
                if mut in members:
                    if combo_name in legend_names:
                        ax.scatter(col_idx, row_idx, color=colours[colour_idx], s=80, zorder=20)
                    else:
                        ax.scatter(
                            col_idx, row_idx,
                            color=colours[colour_idx], s=80, zorder=20,
                            label=combo_name,
                        )
                        legend_names.append(combo_name)

        if len(legend_names) > 0:
            handles, labels = ax.get_legend_handles_labels()
            order = [labels.index(name) for name in combinations.keys() if name in labels]
            handles = [handles[i] for i in order]
            labels = [labels[i] for i in order]
            fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(1, 0.1))

        ############################
        # Formatting
        ############################
        if min_prevalence is not None and subthres_name in mutation_matrix.columns:
            fig.text(
                0,
                -0.1,
                f"* all samples <{min_prevalence}% prevalence without any validated markers",
                ha="left",
                fontsize=8,
            )

        up_plot["intersections"].set_title(
            f"{" & ".join(genes)}, (n={len(mutation_matrix)})",
            fontsize=16,
            pad=20,
        )
        up_plot["intersections"].set_ylabel("Count")
        if not combinations_only:
            up_plot["totals"].set_xlabel("Count")

        if combinations_only:
            fig.text(0,
                     -0.1,
                     "NOTE: All mutation combinations other than the ones listed have been removed from this plot!",
                     ha="left",
                     fontsize=8,
                    )

        return fig
