import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------
# MCMC Components
#
# --------------------------------------------------------------------------------

def calc_dirmult_logprob(alphas: np.ndarray, xs: np.ndarray):
    """
    Compute the log-probability from a Dirichlet-Multinomial distribution
    
    """
    
    assert xs.shape[0] == alphas.shape[0]
    
    n = xs.sum()
    alpha_sum = alphas.sum()
    
    C = math.lgamma(alpha_sum) + math.lgamma(n + 1) - math.lgamma(n + alpha_sum)
    
    R = 0
    for alpha, x in zip(alphas, xs):
        try:
            R += math.lgamma(x + alpha) - math.lgamma(alpha) - math.lgamma(x + 1)
        except ValueError:
            print("x:", x, "alpha: ", alpha, "R: ", R)
            raise ValueError
        
    return R + C


def calc_logprior(copies: int, prior_del: float = 0.05):
    prior = (1 - copies) * prior_del + copies * (1 - prior_del)
    return np.log(prior).sum()


def propose_copies(current_copies):
    """
    Propose a new copy number vector based on the current copies
    
    This procedure i symetric so hastings ratio is 1

    NB:
    - For more mixing, I could try a procedure where MORE than just
    one strain flips at a time
    - E.g. sample number to flip from binomial distribution
    - Sample them randomly without replacement
    - Flip them all
    - This allows for bigger jumps and maybe better mixing...
    
    """
    
    n = current_copies.shape[0]
    ix = np.random.choice(n, size=1)[0]
    propose_copies = np.copy(current_copies)
    propose_copies[ix] = 1 - propose_copies[ix]
    
    return propose_copies


def get_alphas(copies, sample_ests, error_rate, scale):
    """
    Get dirichlet alpha values
    
    """
    
    abundances = copies * sample_ests
    props = abundances / abundances.sum()
    adj_props = props * (1 - error_rate) + (1 - props) * error_rate
    
    return adj_props * scale


# --------------------------------------------------------------------------------
# MCMC Class
#
# --------------------------------------------------------------------------------


class DeletionMCMC:
    def __init__(self, 
                 read_counts_df: pd.DataFrame, 
                 target_gene: str,
                 sample_qualities: np.ndarray,
                 sample_dispersion: float,
                 error_rate: float,
                 prior_del: float=0.5  # is it OKAY to put such a prior on deletions?
                ):
        """
        Initialise the data
        
        """
        
        self.data = read_counts_df[target_gene].to_numpy()
        self.n_samples = self.data.shape[0]
        self.target_gene = target_gene
        
        self.sample_qualities = sample_qualities
        self.sample_dispersion = sample_dispersion
        self.error_rate = error_rate
        self.prior_del = prior_del
        
    def run(self, n_iters=50_000):
        """
        Run the MCMC
        
        """
        
        # Prepare storage
        # parameters
        self.n_iters = n_iters
        self.copy_array = np.ones((self.n_iters, self.n_samples))
        
        # posterior
        self.loglike = np.zeros(n_iters)
        a = 1
        self.acceptance_rate = np.ones(n_iters)
        
        # Initialise
        print("Initialising...")
        i = 0
        current_copies = self.copy_array[i]  # initialised as all ones
        alphas = get_alphas(
            current_copies,
            self.sample_qualities,
            self.error_rate,
            self.sample_dispersion
        )
        current_loglike = (
            calc_dirmult_logprob(alphas, self.data) 
            + calc_logprior(current_copies, self.prior_del)
        )
        self.loglike[i] = current_loglike
        
        # Iterate
        print(f"Iterating... {n_iters}")
        for i in np.arange(1, self.n_iters):
            proposal = propose_copies(current_copies)
            alphas = get_alphas(
                proposal, 
                self.sample_qualities,
                self.error_rate,
                self.sample_dispersion                   
            )
            proposed_loglike = (
                calc_dirmult_logprob(alphas, xs=self.data)
                + calc_logprior(proposal, self.prior_del)
            )
            A = proposed_loglike - current_loglike
            u = random.random()
            if np.log(u) < A:
                current_copies = proposal
                current_loglike = proposed_loglike
                a += 1
            self.copy_array[i] = current_copies
            self.loglike[i] = current_loglike
            self.acceptance_rate[i] = a / i
        print("Done.")
        print(f"Final acceptance rate: {self.acceptance_rate[i]}")
        
    def compute_posterior(self, n_burn=1_000):
        """
        Compute the posterior probabilities
        
        """
        self.posterior_deleted = (1 - self.copy_array[n_burn:].mean(0))
        return self.posterior_deleted


# --------------------------------------------------------------------------------
# Deletion Finder using Bayesian MCMC
#
# --------------------------------------------------------------------------------


@dataclass
class ModelHyperParameters:
    sample_qualities: np.ndarray
    sample_dispersion: float
    error_rate: float


class DeletionFinder:
    """
    Find deletions in amplicon sequecing data using Bayesian MCMC

    """

    AMPLICONS_DEL_MVP = [
        #Original
        # "hrp2-exon2-complete",
        # "hrp3-exon2-complete",
        # New nomenclature
        "hrp2-p14-306", 
        "hrp3-p14-276"
    ]
    AMPLICONS_CONTROL_MVP = [
        #Original
        # "ama1-d2-18-ck",
        # "crt-k76",
        # "csp-rtss-repeat",
        # "dhfr-p51-p164",
        # "dhps-p436-p613",
        # "kelch13-cterm",
        # "mdr1-p1034-p1246",
        # "mdr1-p86-p184",
        # New nomenclature
        "ama1-p74-384", 
        "crt-p14-125", 
        "csp-p19-398", 
        "dhfr-p1-410",
        "dhps-p317-707",
        "kelch13-p383-727",
        "mdr1-p46-245", 
        "mdr1-p968-1278"
        ]

    def __init__(self, df_bedcov: pd.DataFrame) -> None:
        """
        Initialise the deletion finder and preprocess for MCMC
        """

        # Store
        self.df_bedcov = df_bedcov.query("barcode != 'unclassified'")

        # Mean coverage dataframe
        self.df_mean_cov = self._create_mean_cov_dataframe()
        self.df_norm_cov = self._normalise_mean_cov_dataframe()

        # Parameters
        self.hyperparams = None

        # Store MCMC results
        self.mcmcs = []
        self.df_summary = None

    def _create_mean_cov_dataframe(self) -> pd.DataFrame:
        """
        Reshape BED coverage such that barcodes are rows, amplicons are columns,
        and each element indicates the mean coverage
        """

        return pd.pivot_table(
            index="barcode", columns="name", values="mean_cov", data=self.df_bedcov
        )

    def _normalise_mean_cov_dataframe(self) -> pd.DataFrame:
        """
        Normalise each amplicon by it's total coverage
        across all included barcodes
        """

        amp_totals = self.df_mean_cov.sum(axis=0)
        return self.df_mean_cov / amp_totals

    @staticmethod
    def scale_estimator(p_mean: np.array, p_var: np.array) -> float:
        n = p_mean.shape[0]
        lterms = p_mean * (1 - p_mean) / p_var - 1
        return np.exp(np.log(lterms)[:-1].sum() / (n - 1))

    def estimate_hyperparameters(
        self, negative_barcodes: list[str], control_amplicons: list[str] | None = None
    ):
        """
        Estimate the MCMC hyperparameters
        """
        if control_amplicons is None:
            control_amplicons = self.AMPLICONS_CONTROL_MVP
        
        # Estimate misclassification rate
        error_rate = self.df_norm_cov.loc[negative_barcodes].to_numpy().flatten().mean()

        # Estimate sample qualities
        sample_qual_mean = self.df_norm_cov[control_amplicons].to_numpy().mean(1)
        sample_qual_var = self.df_norm_cov[control_amplicons].to_numpy().var(1)

        # Estimate overdispersion in sample quality
        scale = self.scale_estimator(sample_qual_mean, sample_qual_var)

        # Store and return
        self.hyperparams = ModelHyperParameters(
            error_rate=error_rate,
            sample_qualities=sample_qual_mean,
            sample_dispersion=scale,
        )

        return self.hyperparams

    def run_mcmc(self, target_gene: str, prior_del: float = 0.5) -> None:
        """
        Run a deletion MCMC and store the results
        """

        mcmc = DeletionMCMC(
            self.df_mean_cov,
            target_gene=target_gene,
            prior_del=prior_del,
            **self.hyperparams.__dict__,
        )
        mcmc.run()
        mcmc.compute_posterior()
        self.mcmcs.append(mcmc)

    def summarise_mcmc_outputs(self) -> pd.DataFrame:
        """
        Summarise MCMC outputs
        """

        dt = {}
        dt["barcode"] = self.df_mean_cov.index
        for mcmc in self.mcmcs:
            short_name = mcmc.target_gene.split("-")[0]
            dt[f"{short_name}_del_posterior"] = mcmc.posterior_deleted
            dt[f"{short_name}_del_prediction"] = mcmc.posterior_deleted > 0.5
        dt["sample_qual_estimate"] = self.hyperparams.sample_qualities

        self.df_summary = pd.DataFrame(dt)

        return self.df_summary