import math
import numpy as np


def compute_descriptive_stats(values):
    """Calculates descriptive statistics for a list or numpy array of numeric values.

    Returns a dict with mean, median, std_dev, min, max, and 95% confidence interval.
    """
    if not values or len(values) == 0:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "ci_95_lower": 0.0,
            "ci_95_upper": 0.0,
            "count": 0,
        }

    arr = np.array(values, dtype=float)
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std_dev = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    val_min = float(np.min(arr))
    val_max = float(np.max(arr))
    count = len(arr)

    # 95% confidence interval using standard normal approximation
    margin_of_error = 0.0
    if count > 1 and std_dev > 0:
        # z-score for 95% is approximately 1.96
        margin_of_error = 1.96 * (std_dev / math.sqrt(count))

    return {
        "mean": mean,
        "median": median,
        "std_dev": std_dev,
        "min": val_min,
        "max": val_max,
        "ci_95_lower": max(0.0, mean - margin_of_error),
        "ci_95_upper": mean + margin_of_error,
        "count": count,
    }


def compute_cliffs_delta(x, y):
    """Computes Cliff's Delta effect size between two independent/paired groups x and y.

    Cliff's Delta ranges from -1 to 1.
    Values near 0 imply no difference, positive implies x tends to be larger,
    negative implies y tends to be larger.
    """
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    n1 = len(x)
    n2 = len(y)
    if n1 == 0 or n2 == 0:
        return 0.0

    # Count how many times x_i > y_j, x_i < y_j, and x_i == y_j
    # We can do this efficiently using numpy broadcasting
    diff = x[:, None] - y[None, :]
    greater = np.sum(diff > 0)
    less = np.sum(diff < 0)

    delta = (greater - less) / (n1 * n2)
    return float(delta)


def compute_wilcoxon_signed_rank(x, y):
    """Computes Wilcoxon signed-rank test for paired samples.

    Returns the Wilcoxon statistic and an approximate p-value (using normal approximation).
    """
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    if len(x) != len(y) or len(x) == 0:
        raise ValueError("Samples must have the same length and be non-empty.")

    diffs = x - y
    # Remove zero differences
    nonzero_diffs = diffs[diffs != 0]
    n = len(nonzero_diffs)

    if n < 5:
        # Too few non-zero differences for normal approximation
        # Return statistics but mark p-value as non-computable (1.0 or None)
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "comment": "Too few non-zero differences for reliable Wilcoxon p-value.",
        }

    abs_diffs = np.abs(nonzero_diffs)
    # Get ranks
    # To handle ties properly, we use fractional ranking
    temp = abs_diffs.argsort()
    ranks = np.empty_like(temp, dtype=float)
    # Sort the indices, but we need average ranks for ties
    sorted_abs = abs_diffs[temp]

    # Find groups of ties
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_abs[j] == sorted_abs[i]:
            j += 1
        # Indices are i to j-1. Average rank is sum(i+1 to j)/count
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[temp[k]] = avg_rank
        i = j

    # Signs
    signs = np.sign(nonzero_diffs)
    w_pos = np.sum(ranks[signs > 0])
    w_neg = np.sum(ranks[signs < 0])

    statistic = min(w_pos, w_neg)

    # Normal approximation
    # Expected mean: E = n * (n + 1) / 4
    # Expected variance: Var = n * (n + 1) * (2n + 1) / 24
    # Adjust for ties if necessary, but standard formula is usually sufficient
    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2.0 * n + 1) / 24.0

    # Handle ties in variance calculation
    # Var_adj = Var - sum(t^3 - t)/48
    unique, counts = np.unique(abs_diffs, return_counts=True)
    tie_adjustment = np.sum(counts**3 - counts) / 48.0
    var_w -= tie_adjustment
    if var_w <= 0:
        var_w = 1e-9

    z = (statistic - mean_w) / math.sqrt(var_w)
    # Two-sided p-value from standard normal
    # p = 2 * Phi(z) where z is negative
    p_value = 2.0 * 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "w_positive": float(w_pos),
        "w_negative": float(w_neg),
        "n_nonzero": n,
    }


def compute_friedman_test(matrix):
    """Computes Friedman test for multiple paired groups.

    matrix: 2D numpy array of shape (n_tasks, n_models).
            Each row represents a task, each column a model's score/metric.
    Returns:
        - statistic (Friedman Q statistic)
        - p_value (from Chi-Square distribution with k-1 df)
        - mean_ranks: dict mapping column index (model) to its mean rank
        - kendalls_w: Kendall's W effect size
    """
    matrix = np.array(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 2:
        raise ValueError("Matrix must be 2D with at least 2 tasks and 2 models.")

    n_tasks, n_models = matrix.shape

    # Rank each row (task)
    # High score should get better rank. Usually in Friedman, we rank from 1 to k.
    # Let's say higher score gets better (lower rank number, e.g., 1 is best) OR
    # standard Friedman: ranks are 1 (lowest) to k (highest). Let's rank standard 1 to k.
    # To rank standard: rank = 1 for worst, k for best.
    ranks = np.empty_like(matrix)
    for i in range(n_tasks):
        row = matrix[i]
        # Fractional rank (handles ties)
        temp = row.argsort()
        row_ranks = np.empty_like(temp, dtype=float)
        sorted_row = row[temp]
        p = 0
        while p < n_models:
            q = p + 1
            while q < n_models and sorted_row[q] == sorted_row[p]:
                q += 1
            avg_rank = (p + 1 + q) / 2.0
            for k in range(p, q):
                row_ranks[temp[k]] = avg_rank
            p = q
        ranks[i] = row_ranks

    # Sum of ranks for each model (each column)
    rank_sums = np.sum(ranks, axis=0)
    mean_ranks = rank_sums / n_tasks

    # Friedman statistic Q:
    # Q = [12 / (n * k * (k + 1))] * sum(R_j^2) - 3 * n * (k + 1)
    sum_sq_ranks = np.sum(rank_sums**2)
    q_stat = (12.0 / (n_tasks * n_models * (n_models + 1.0))) * sum_sq_ranks - 3.0 * n_tasks * (n_models + 1.0)

    # Degrees of freedom = k - 1
    df = n_models - 1

    # p-value using Chi-Square distribution approximation
    # Chi-Square survival function (CDF: survival = 1 - CDF)
    # We can approximate p-value with high precision or use standard approximation.
    p_value = chi2_survival(q_stat, df)

    # Kendall's W = Q / (n * (k - 1))
    kendalls_w = q_stat / (n_tasks * (n_models - 1.0)) if n_models > 1 else 0.0

    return {
        "statistic": float(q_stat),
        "p_value": float(p_value),
        "df": int(df),
        "mean_ranks": {idx: float(mean_ranks[idx]) for idx in range(n_models)},
        "kendalls_w": float(kendalls_w),
    }


def chi2_survival(chi2, df):
    """Computes the survival function (1 - CDF) of a Chi-Square distribution.

    Uses pure python calculation with high precision approximation.
    """
    if chi2 <= 0:
        return 1.0
    # Survival function is regularized upper incomplete gamma function Q(df/2, chi2/2)
    a = df / 2.0
    x = chi2 / 2.0

    # Using standard series or continued fraction approximation for incomplete gamma
    return igf_upper(a, x)


def igf_upper(a, x):
    """Upper regularized incomplete gamma function Q(a, x)."""
    # For very small x or a, handle limits
    if x <= 0:
        return 1.0
    if a <= 0:
        return 0.0

    # We use Pearson's or continued fraction approximation
    # For continued fraction:
    # f = x^a * e^-x / Gamma(a) * (1 / (x + 1 - a + 1 / (x + 3 - a + ...)))
    gamma_a = math.gamma(a) if a < 100 else Stirling_gamma(a)
    factor = (x**a) * math.exp(-x) / gamma_a

    # Continued fraction for incomplete gamma (Lentz's method)
    # b_0 = 0, a_1 = 1, b_1 = x + 1 - a, etc.
    # Better yet, standard series for lower incomplete gamma P(a, x) and Q = 1 - P:
    # P(a, x) = (x^a * e^-x / Gamma(a)) * sum_{n=0}^\infty [x^n / (a * (a+1) * ... * (a+n))]
    if x < a + 1.0:
        # Use series for lower incomplete gamma P(a, x)
        sum_val = 1.0 / a
        term = 1.0 / a
        for n in range(1, 100):
            term = term * x / (a + n)
            sum_val += term
            if abs(term) < 1e-15 * abs(sum_val):
                break
        p_val = factor * sum_val
        return max(0.0, min(1.0, 1.0 - p_val))
    else:
        # Use continued fraction for upper incomplete gamma Q(a, x)
        # Lentz's method
        tiny = 1e-30
        f = tiny
        c = f
        d = 0.0

        # We evaluate the fraction:
        # 1 / (x + (1-a) / (1 + 1 / (x + (2-a) / (1 + 2 / ...))))
        # which can be converted to standard form
        # We use a standard expansion for upper incomplete gamma:
        # Q(a,x) = factor * continued_fraction
        # a_i, b_i coefficients
        # Here we use the continued fraction of complete incomplete gamma:
        # b_0 = 0, b_1 = x + 1 - a, etc.
        # Let's use a simpler continued fraction:
        # d_j = b_j + a_j * d_{j-1}
        # For incomple gamma:
        # a_2n = n - a, a_2n+1 = n
        # b_n = 1
        # Let's use Lentz's method for complete incomplete gamma:
        # b_1 = x + 1.0 - a
        # a_i:
        # a_2 = a - 1, b_2 = b_1 + 2
        # For simplicity, standard continued fraction:
        # Q(a, x) = factor * continued fraction
        # Let's run a robust expansion:
        d = x + 1.0 - a
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d
        c = x + 1.0 - a
        if abs(c) < tiny:
            c = tiny
        f = c

        for i in range(1, 200):
            an = -i * (i - a)
            bn = x + 2.0 * i + 1.0 - a
            d = bn + an * d
            if abs(d) < tiny:
                d = tiny
            d = 1.0 / d
            c = bn + an / c
            if abs(c) < tiny:
                c = tiny
            delta = c * d
            f *= delta
            if abs(delta - 1.0) < 1e-15:
                break
        return factor * f


def Stirling_gamma(z):
    """Stirling's approximation for Gamma function for larger z."""
    return math.sqrt(2.0 * math.pi / z) * ((z / math.e) ** z)


def compute_nemenyi_critical_difference(n_models, n_tasks, alpha=0.05):
    """Computes critical difference (CD) for Nemenyi post-hoc test.

    CD = q_alpha * sqrt( k * (k + 1) / (6 * n) )
    where k is the number of models, n is the number of tasks,
    and q_alpha is the studentized range statistic divided by sqrt(2).
    """
    # Standard q_alpha critical values (for alpha=0.05) divided by sqrt(2).
    # Source: Demšar, J. (2006). Statistical comparisons of classifiers over multiple data sets.
    # Table of critical values for two-tailed Nemenyi test (q_alpha values / sqrt(2)):
    # Number of models (k): 2,    3,    4,    5,    6,    7,    8,    9,    10
    nemenyi_q_alphas = {
        2: 1.960,  # Actually Wilcoxon is better, but defined here
        3: 2.343,
        4: 2.569,
        5: 2.728,
        6: 2.850,
        7: 2.949,
        8: 3.031,
        9: 3.102,
        10: 3.164,
    }

    # Fallback to standard approximation if k > 10
    q_val = nemenyi_q_alphas.get(n_models, 3.2 + 0.1 * (n_models - 10))

    cd = q_val * math.sqrt((n_models * (n_models + 1.0)) / (6.0 * n_tasks))
    return cd
