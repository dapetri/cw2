import os

import cma
import dill
import numpy as np
from cma.bbobbenchmarks import nfreefunclasses

import foreman
import workload.job


class CWCMA(workload.job.AbstractJob):
    def __init__(self):
        super().__init__()
        self.problem = None
        self.optimizer = None

    def initialize(self, config: dict, rep: int) -> None:
        dim = config.problem.dim
        x_start = config.optim_params.x_init * np.random.randn(dim)
        init_sigma = config.optim_params.init_sigma
        self.problem = nfreefunclasses[7](iinstance=rep)
        self.problem.initwithsize(curshape=(1, dim), dim=dim)
        self.optimizer = es = cma.CMAEvolutionStrategy(
            x0=x_start,
            sigma0=init_sigma,
            inopts={
                'popsize': config.optim_params.n_samples
            }
        )
        es.f_obj = self.problem

        def entropy(self):
            cov = self.sigma ** 2 * self.sm.covariance_matrix
            chol = np.linalg.cholesky(cov)
            ent = np.sum(np.log(np.diag(chol))) + \
                self.N / 2 * np.log(2 * np.pi) + self.N / 2
            return ent

        self.optimizer.entropy = entropy.__get__(
            self.optimizer, cma.CMAEvolutionStrategy)

        self.optimizer.adapt_sigma.initialize(self.optimizer)
        if config.optim_params.c_c is not None:
            self.optimizer.sp.cc = config.optim_params.c_c
        if config.optim_params.c_1 is not None:
            self.optimizer.sm._parameters['c1'] = config.optim_params.c_1
        if config.optim_params.c_mu is not None:
            self.optimizer.sm._parameters['cmu'] = config.optim_params.c_mu
        if config.optim_params.d_sigma is not None:
            self.optimizer.adapt_sigma.damps = config.optim_params.d_sigma
        if config.optim_params.c_sigma is not None:
            config.adapt_sigma.cs = config.optim_params.c_sigma

    def iterate(self, config: dict, rep: int, n: int) -> dict:
        # do one iteration of cma es
        solutions = self.optimizer.ask()
        f = self.problem(solutions)
        self.optimizer.tell(solutions, f)

        # collect some results from this iteration
        mean_opt = np.mean(self.optimizer.fit.fit) - self.problem.getfopt()
        median_opt = np.median(self.optimizer.fit.fit) - self.problem.getfopt()

        f0_at_mean = float(self.problem(
            self.optimizer.mean.flatten()) - self.problem.getfopt())

        results_dict = {"f_id": self.problem.funId,
                        "current_opt": f0_at_mean,
                        "mean_opt": mean_opt,
                        "median_opt": median_opt,
                        "entropy": self.optimizer.entropy(),
                        "total_samples": (n + 1) * config.optim_params.n_samples
                        }

        return results_dict

    def save_state(self, config: dict, rep: int, n: int) -> None:
        if n % 50 == 0:
            f_name = os.path.join(
                config.log_path, 'rep_{:02d}'.format(rep), 'optimizer.pkl')
            with open(f_name, 'wb') as f:
                dill.dump(self.optimizer, f)

    def finalize(self):
        pass

    def restore_state(self):
        pass


if __name__ == "__main__":
    yaml = "./cma_config.yml"

    c = foreman.Foreman(yaml, CWCMA)
