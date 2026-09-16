# v008 Feature Stability Audit (V1a) — v007c R1 features across sources

2026-09-16. Advisory evidence for the PREREGISTERED feature-selection gate in plan
`godspeed-agent-v008-r1-transfer`. Read-only audit; no repo code modified.

## Inputs, methods, reproducibility

Data: `data/settlement_datasets/corpora/v007c-episodes/episodes.jsonl`, R1 rows only
(`point=="R1"`): verified N=37,426 = swegym_openhands 6,987 / nebius_swe_agent 17,642 /
swe_smith 12,797; 0 NaN cells in the 54-feature matrix. Features: all 54 of `v007_r1@1`
(from `scripts/settlement_datasets/v007_recovery.py`: R0 44 = 29 v006 + 10 v005-prefix +
5 episode-positional, plus 10 R1_ADDITIONS); `dataset_id` is identity, excluded from
transfer candidates. Label `recovery_success`, prevalence .101/.141/.378 — the base-rate
shift is the dominant transfer hazard (handled by class_weight="balanced" + per-pool
refit, not by feature choice). `split_group` counts 11/176/1,951. Seeds: random_state=42;
GroupKFold(5) unshuffled (deterministic); quartile bins via rank(method='first').

Per feature: median/IQR/zero%/z(mean)/std-ratio per source (z and std-ratio vs pooled;
scale differences visible via zmean/stdR); within-source AUC(feature, label); pooled AUC
for contrast; sign of (AUC-.5) per source (`dir`); pooled LogisticRegression(C=1.0,
class_weight="balanced", max_iter=1000, lbfgs, standardized) fit on GroupKFold(5) folds
over `split_group`, coefficient sign per fold (`folds`) and majority-sign fraction
(`cons`); mean standardized |coef| (`beta`); one-vs-rest (OVR) AUC predicting SOURCE
(`ovrMn`/`ovrMx` = mean/max); max |point-biserial corr| with source one-hot (`corr`).
Cramer's V was computed on rank-quartile bins but is UNRELIABLE for tied/constant
features (file-ordered artifact, e.g. has_failure V=.823 at AUC .500) — use OVR/corr
there. Source order in every triple: swegym_openhands / nebius_swe_agent / swe_smith.
`const`: `.` varies, `C` constant within that source. `gate` = direction-consistent AND
cons>=0.8 AND OVR-mean<0.85 AND non-constant (advisory application of the prereg wording).

## Master table — all 54 features (distribution, prediction, stability, identifiability)

| feature | fam | median | IQR | zero% | zmean | stdR | const | AUC s0/s1/s2 | pool | dir | folds | cons | beta | ovrMn | ovrMx | corr | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n_events | v006 | 26/27/32 | 32/43/40 | 0.0/0.0/0.0 | -0.245/+0.076/+0.029 | 0.567/1.188/0.874 | ... | 0.402/0.327/0.406 | 0.402 | --- | ----- | 1.0 | 0.380 | 0.493 | 0.540 | 0.117 | PASS |
| n_actions | v006 | 13/13/16 | 16/21/20 | 0.0/0.0/0.0 | -0.237/+0.064/+0.042 | 0.566/1.189/0.874 | ... | 0.402/0.327/0.405 | 0.405 | --- | +++++ | 1.0 | 0.993 | 0.494 | 0.551 | 0.114 | PASS |
| n_observations | v006 | 13/14/16 | 16/22/20 | 0.0/0.0/0.0 | -0.252/+0.089/+0.015 | 0.571/1.186/0.873 | ... | 0.403/0.327/0.406 | 0.399 | --- | ----- | 1.0 | 1.750 | 0.492 | 0.530 | 0.121 | PASS |
| unresolved_action_rate | v006 | 0/0/0 | 0/0/0 | 93.6/98.0/98.8 | +0.198/-0.029/-0.069 | 1.469/0.977/0.635 | ... | 0.466/0.488/0.490 | 0.484 | --- | ----- | 1.0 | 0.144 | 0.503 | 0.524 | 0.095 | PASS |
| action_observation_closure_ratio | v006 | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | -0.198/+0.029/+0.069 | 1.469/0.977/0.635 | ... | 0.534/0.511/0.510 | 0.516 | +++ | +++++ | 1.0 | 0.144 | 0.497 | 0.510 | 0.095 | PASS |
| used_family_diversity | v006 | 3/1/3 | 1/0/2 | 0.0/0.0/0.0 | +0.491/-0.832/+0.879 | 0.904/0.000/0.786 | .C. | 0.425/0.500/0.517 | 0.612 | -0+ | +++++ | 1.0 | 0.290 | 0.536 | 0.878 | 0.786 | fail |
| tool_switch_rate | v006 | 0.4444/0/0.5161 | 0.4655/0/0.2843 | 20.3/100.0/3.6 | +0.518/-0.848/+0.886 | 0.937/0.000/0.722 | .C. | 0.448/0.500/0.579 | 0.627 | -0+ | +++++ | 1.0 | 0.152 | 0.536 | 0.875 | 0.801 | fail |
| repeated_action_rate | v006 | 0.2857/0/0 | 0.5162/0/0 | 16.1/98.3/99.7 | +1.528/-0.347/-0.356 | 1.567/0.109/0.017 | ... | 0.445/0.495/0.498 | 0.437 | --- | ---++ | 0.6 | 0.022 | 0.550 | 0.918 | 0.732 | fail |
| max_repeated_action_run | v006 | 3/1/1 | 3/0/0 | 0.0/0.0/0.0 | +1.214/-0.272/-0.288 | 1.860/0.181/0.028 | ... | 0.399/0.495/0.498 | 0.437 | --- | +---- | 0.8 | 0.097 | 0.550 | 0.916 | 0.582 | PASS |
| error_count | v006 | 6/6/7 | 9/10/8 | 0.0/0.0/0.0 | -0.145/+0.073/-0.022 | 0.681/1.177/0.862 | ... | 0.394/0.359/0.418 | 0.409 | --- | ----- | 1.0 | 1.349 | 0.496 | 0.515 | 0.069 | PASS |
| error_rate | v006 | 0.25/0.24/0.2308 | 0.1125/0.1036/0.1333 | 0.0/0.0/0.0 | +0.105/+0.050/-0.126 | 0.893/1.000/1.042 | ... | 0.451/0.567/0.522 | 0.512 | -++ | ----- | 1.0 | 1.269 | 0.504 | 0.545 | 0.091 | fail |
| distinct_error_count | v006 | 6/5/7 | 7/6/8 | 0.0/0.0/0.0 | -0.102/-0.083/+0.171 | 0.809/0.950/1.131 | ... | 0.400/0.401/0.418 | 0.440 | --- | ----- | 1.0 | 0.871 | 0.499 | 0.565 | 0.123 | PASS |
| repeated_error_rate | v006 | 0/0/0 | 0.1111/0.1667/0 | 66.8/64.4/82.4 | -0.022/+0.242/-0.322 | 0.830/1.259/0.424 | ... | 0.431/0.372/0.477 | 0.405 | --- | ----- | 1.0 | 0.424 | 0.499 | 0.580 | 0.232 | PASS |
| recovery_attempt_count | v006 | 6/5/6 | 9/10/9 | 0.0/0.0/0.0 | -0.166/+0.075/-0.012 | 0.671/1.179/0.860 | ... | 0.400/0.356/0.417 | 0.411 | --- | +++++ | 1.0 | 1.275 | 0.495 | 0.523 | 0.080 | PASS |
| recovery_rate | v006 | 0.9677/1/1 | 0.2/0.1667/0.0909 | 0.0/0.0/0.0 | -0.260/+0.016/+0.120 | 1.261/0.891/0.954 | ... | 0.502/0.448/0.485 | 0.495 | +-- | ----- | 1.0 | 0.242 | 0.494 | 0.554 | 0.124 | fail |
| recovery_latency_mean | v006 | 2.667/2.2/2.769 | 1.8/1/2 | 7.1/0.0/4.3 | +0.066/-0.114/+0.121 | 1.124/0.879/1.065 | ... | 0.400/0.415/0.466 | 0.475 | --- | +-+++ | 0.8 | 0.053 | 0.506 | 0.596 | 0.108 | PASS |
| first_recovery_latency | v006 | 2/2/2 | 1/0/2 | 7.1/0.0/4.3 | +0.119/-0.303/+0.353 | 1.329/0.338/1.243 | ... | 0.471/0.491/0.490 | 0.545 | --- | ++++- | 0.8 | 0.024 | 0.506 | 0.673 | 0.286 | PASS |
| strategy_change_after_first_failure | v006 | 0/0/0 | 0/0/1 | 75.1/100.0/55.6 | +0.128/-0.497/+0.616 | 1.085/0.000/1.246 | .C. | 0.524/0.500/0.480 | 0.551 | +0- | ----- | 1.0 | 0.079 | 0.510 | 0.686 | 0.469 | fail |
| verification_action_count | v006 | 0/0/0 | 0/0/0 | 99.7/100.0/87.8 | -0.129/-0.131/+0.252 | 0.049/0.000/1.681 | .C. | 0.498/0.500/0.505 | 0.523 | -0+ | ----- | 1.0 | 1.157 | 0.499 | 0.560 | 0.181 | fail |
| verification_rate | v006 | 0/0/0 | 0/0/0 | 99.7/100.0/87.8 | -0.148/-0.153/+0.292 | 0.109/0.000/1.670 | .C. | 0.498/0.500/0.505 | 0.523 | -0+ | --++- | 0.6 | 0.025 | 0.499 | 0.560 | 0.210 | fail |
| verification_after_edit_count | v006 | 0/0/0 | 0/0/0 | 100.0/100.0/87.9 | -0.131/-0.131/+0.252 | 0.000/0.000/1.682 | CC. | 0.500/0.500/0.505 | 0.523 | 00+ | ---++ | 0.6 | 0.497 | 0.499 | 0.560 | 0.181 | fail |
| verification_after_recovery_count | v006 | 0/0/0 | 0/0/0 | 99.8/100.0/89.1 | -0.123/-0.125/+0.239 | 0.043/0.000/1.684 | .C. | 0.499/0.500/0.513 | 0.525 | -0+ | +++++ | 1.0 | 1.000 | 0.499 | 0.554 | 0.172 | fail |
| observation_novelty_rate | v006 | 0.9231/1/1 | 0.2059/0.1429/0.0541 | 0.0/0.0/0.0 | -0.206/-0.163/+0.337 | 0.910/1.236/0.440 | ... | 0.604/0.656/0.538 | 0.622 | +++ | +++++ | 1.0 | 0.144 | 0.488 | 0.612 | 0.243 | PASS |
| actions_since_last_observation | v006 | 0/0/0 | 0/0/0 | 93.6/98.0/98.8 | +0.244/-0.035/-0.084 | 1.553/0.887/0.695 | ... | 0.466/0.488/0.490 | 0.484 | --- | ----- | 1.0 | 0.263 | 0.503 | 0.523 | 0.117 | PASS |
| actions_without_observation_rate | v006 | 0/0/0 | 0.0455/0/0 | 70.6/83.1/90.2 | +0.543/-0.070/-0.200 | 1.787/0.719/0.511 | ... | 0.424/0.435/0.484 | 0.442 | --- | ----- | 1.0 | 0.123 | 0.510 | 0.588 | 0.260 | PASS |
| stuck_cycle_max | v006 | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | +0.122/-0.006/-0.058 | 1.923/0.782/0.226 | ... | 0.496/0.497/0.499 | 0.497 | --- | -++++ | 0.8 | 0.068 | 0.501 | 0.505 | 0.058 | PASS |
| stuck_loop_indicator | v006 | 0/0/0 | 0/0/0 | 98.5/99.4/99.9 | +0.118/+0.002/-0.067 | 1.591/1.011/0.350 | ... | 0.496/0.497/0.499 | 0.497 | --- | +---- | 0.8 | 0.101 | 0.501 | 0.505 | 0.057 | PASS |
| has_failure | v006 | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | +0.000/+0.000/+0.000 | 0/0/0 | CCC | 0.500/0.500/0.500 | 0.500 | 000 | 00000 | 0.0 | 0.000 | 0.500 | 0.500 | nan | fail |
| has_recovery | v006 | 1/1/1 | 0/0/0 | 7.1/0.0/4.3 | -0.259/+0.170/-0.093 | 1.554/0.000/1.234 | .C. | 0.491/0.500/0.490 | 0.491 | -0- | ----+ | 0.8 | 0.021 | 0.496 | 0.526 | 0.160 | fail |
| payment_predicted_total | v005pre | 28/28/34 | 32/43/40 | 0.0/0.0/0.0 | -0.231/+0.062/+0.040 | 0.569/1.189/0.874 | ... | 0.401/0.327/0.406 | 0.404 | --- | ---++ | 0.6 | 0.256 | 0.495 | 0.550 | 0.111 | fail |
| payment_actual_total | v005pre | 33/33/44 | 41/52/57 | 0.0/0.0/0.0 | -0.272/+0.021/+0.119 | 0.568/1.135/0.957 | ... | 0.399/0.331/0.412 | 0.420 | --- | +++++ | 1.0 | 0.632 | 0.492 | 0.579 | 0.130 | PASS |
| payment_error | v005pre | 4/5/11 | 9/10/16 | 11.7/0.0/3.6 | -0.360/-0.118/+0.359 | 0.516/0.922/1.179 | ... | 0.392/0.359/0.433 | 0.472 | --- | +++++ | 1.0 | 0.761 | 0.487 | 0.662 | 0.259 | PASS |
| horizon_delta | v005pre | 0.825/0.8429/0.8671 | 0.0571/0.0719/0.0714 | 0.0/0.0/0.0 | -0.427/-0.106/+0.379 | 0.799/0.994/0.977 | ... | 0.520/0.406/0.486 | 0.521 | +-- | +++++ | 1.0 | 0.207 | 0.484 | 0.661 | 0.274 | fail |
| risk_estimate | v005pre | 0.2333/0.2333/0.2143 | 0.09983/0.09821/0.1146 | 0.0/0.0/0.0 | +0.020/+0.114/-0.168 | 0.925/0.987/1.034 | ... | 0.432/0.554/0.509 | 0.493 | -++ | +++++ | 1.0 | 1.678 | 0.500 | 0.555 | 0.121 | fail |
| debt_estimate | v005pre | 0/0/0 | 0/0/0 | 100.0/100.0/100.0 | +0.000/+0.000/+0.000 | 0/0/0 | CCC | 0.500/0.500/0.500 | 0.500 | 000 | 00000 | 0.0 | 0.000 | 0.500 | 0.500 | nan | fail |
| tool_diversity_count | v005pre | 3/0/0 | 0/0/0 | 0.0/100.0/100.0 | +2.087/-0.479/-0.479 | 0.000/0.000/0.000 | CCC | 0.500/0.500/0.500 | 0.437 | 000 | ----- | 1.0 | 0.304 | 0.560 | 1.000 | 1.000 | fail |
| error_recovery_ratio | v005pre | 0.9412/1/1 | 0.2857/0.3333/0.1818 | 7.1/0.0/4.3 | -0.151/-0.013/+0.100 | 1.167/0.924/0.990 | ... | 0.518/0.455/0.492 | 0.501 | +-- | ++++- | 0.8 | 0.130 | 0.496 | 0.552 | 0.072 | fail |
| action_observation_ratio | v005pre | 1/0.9286/1 | 0/0.0905/0 | 0.0/0.0/0.0 | +0.478/-0.625/+0.600 | 1.106/0.942/0.107 | ... | 0.491/0.322/0.490 | 0.571 | --- | +++++ | 1.0 | 0.383 | 0.541 | 0.857 | 0.590 | PASS |
| avg_actions_per_step | v005pre | 0.4615/0.4643/0.4706 | 0.0562/0.0453/0.0389 | 0.0/0.0/0.0 | -0.221/-0.015/+0.142 | 1.097/1.008/0.906 | ... | 0.411/0.324/0.401 | 0.406 | --- | ----- | 1.0 | 0.430 | 0.492 | 0.556 | 0.106 | PASS |
| fail_event_index | epi_pos | 23/24/29 | 32/42/40 | 0.0/0.0/0.0 | -0.245/+0.076/+0.028 | 0.568/1.188/0.873 | ... | 0.401/0.327/0.405 | 0.402 | --- | ----- | 1.0 | 0.242 | 0.493 | 0.540 | 0.117 | PASS |
| prior_episode_count | epi_pos | 2/2/2 | 4/5/4 | 21.8/24.2/18.9 | -0.166/+0.127/-0.084 | 0.562/1.283/0.663 | ... | 0.412/0.360/0.412 | 0.408 | --- | +++++ | 1.0 | 0.197 | 0.498 | 0.517 | 0.120 | PASS |
| prior_escape_count | epi_pos | 2/2/2 | 4/5/4 | 21.8/24.2/18.9 | -0.166/+0.127/-0.084 | 0.562/1.283/0.663 | ... | 0.412/0.360/0.412 | 0.408 | --- | +++++ | 1.0 | 0.197 | 0.498 | 0.517 | 0.120 | PASS |
| errors_opening_run_available_at_r0 | epi_pos | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | +0.000/+0.000/+0.000 | 0/0/0 | CCC | 0.500/0.500/0.500 | 0.500 | 000 | 00000 | 0.0 | 0.000 | 0.500 | 0.500 | nan | fail |
| current_streak_prior_nonerror | epi_pos | 1/1/2 | 1/1/2 | 0.0/0.0/0.0 | -0.193/-0.027/+0.143 | 0.549/0.903/1.262 | ... | 0.514/0.483/0.496 | 0.513 | +-- | +++++ | 1.0 | 0.020 | 0.493 | 0.552 | 0.103 | fail |
| recovery_attempt_present | r1att | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | +0.000/+0.000/+0.000 | 0/0/0 | CCC | 0.500/0.500/0.500 | 0.500 | 000 | 00000 | 0.0 | 0.000 | 0.500 | 0.500 | nan | fail |
| attempt_repeats_prior_action | r1att | 0/0/0 | 1/0/0 | 74.1/99.8/100.0 | +0.968/-0.219/-0.227 | 2.021/0.208/0.071 | ... | 0.480/0.499/0.500 | 0.481 | --- | ----- | 1.0 | 0.080 | 0.516 | 0.629 | 0.464 | PASS |
| has_prior_action | r1att | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | +0.000/+0.000/+0.000 | 0/0/0 | CCC | 0.500/0.500/0.500 | 0.500 | 000 | 00000 | 0.0 | 0.000 | 0.500 | 0.500 | nan | fail |
| attempt_family_change | r1att | 1/0/1 | 1/0/1 | 43.9/100.0/39.9 | +0.541/-0.671/+0.629 | 1.073/0.000/1.059 | .C. | 0.471/0.500/0.500 | 0.561 | -0- | ----- | 1.0 | 0.075 | 0.527 | 0.721 | 0.633 | fail |
| has_pre_failure_action | r1att | 1/1/1 | 0/0/0 | 0.0/0.0/0.0 | +0.000/+0.000/+0.000 | 0/0/0 | CCC | 0.500/0.500/0.500 | 0.500 | 000 | 00000 | 0.0 | 0.000 | 0.500 | 0.500 | nan | fail |
| obs_between_failure_and_attempt | r1att | 0/0/0 | 0/0/0 | 98.2/100.0/100.0 | +0.186/-0.043/-0.043 | 2.305/0.000/0.000 | .CC | 0.500/0.500/0.500 | 0.499 | +00 | +++-+ | 0.8 | 0.010 | 0.501 | 0.509 | 0.089 | fail |
| new_obs_between_failure_and_attempt | r1att | 1/1/1 | 0/1/0 | 20.4/25.0/7.8 | +0.042/-0.180/+0.226 | 1.352/1.019/0.630 | ... | 0.559/0.598/0.512 | 0.569 | +++ | +++++ | 1.0 | 0.061 | 0.502 | 0.576 | 0.170 | PASS |
| attempt_result_is_error | r1att | 0/0/0 | 1/1/1 | 55.0/55.7/62.9 | +0.063/+0.047/-0.099 | 1.008/1.007/0.979 | ... | 0.488/0.521/0.502 | 0.495 | -++ | ----- | 1.0 | 0.110 | 0.501 | 0.522 | 0.071 | fail |
| has_attempt_result | r1att | 1/1/1 | 0/0/0 | 6.4/2.0/1.2 | -0.244/+0.035/+0.084 | 1.553/0.887/0.695 | ... | 0.534/0.511/0.510 | 0.516 | +++ | +++++ | 1.0 | 0.263 | 0.497 | 0.510 | 0.117 | PASS |
| attempt_result_same_hash_as_failure | r1att | 0/0/0 | 0/0/0 | 99.0/97.9/99.9 | -0.023/+0.081/-0.099 | 0.892/1.309/0.331 | ... | 0.497/0.494/0.500 | 0.495 | --- | ++-+- | 0.6 | 0.013 | 0.499 | 0.508 | 0.077 | fail |

## Dead / duplicated features (drop or collapse before any pool)

Constant in ALL sources: `has_failure`(=1), `debt_estimate`(=0),
`errors_opening_run_available_at_r0`(=1, documented constant), `recovery_attempt_present`
(=1 on every R1 row by construction), `has_prior_action`(=1), `has_pre_failure_action`(=1).
Constant in nebius only: `used_family_diversity`, `tool_switch_rate`(0),
`strategy_change_after_first_failure`(0), `attempt_family_change`(0),
`verification_action_count`/`verification_rate`/`verification_after_recovery_count`(0),
`has_recovery`(1); swegym+nebius: `verification_after_edit_count`(0); nebius+smith:
`obs_between_failure_and_attempt`(0). Verified duplicates: `prior_escape_count ==
prior_episode_count` exactly; `corr(fail_event_index, n_events)=1.000`,
`corr(n_events, n_actions)=0.9998` (depth = one signal under five names);
`corr(payment_predicted_total, payment_actual_total)=0.9913`.

## Environment-identifier candidates (high identifiability, weak label relation)

`tool_diversity_count` (OVR max 1.000, constant-per-source 3/0/0, within-source AUC .500
everywhere — a pure source dummy); `repeated_action_rate` (OVR max .918, corr .732, label
edge ~0 outside swegym); `used_family_diversity` (.878, constant in nebius);
`tool_switch_rate` (.875, constant 0 in nebius); `strategy_change_after_first_failure`
(.686, constant 0 in nebius, AUC .524/.500/.480); verification family (near-zero
everywhere, mass only in smith, AUC ~.50). Borderline — real but source-concentrated
label signal: `max_repeated_action_run` (OVR max .916; direction consistent but edge
carried by swegym .399 vs .495/.498) and `action_observation_ratio` (OVR max .857; edge
carried by nebius .322 vs .491/.490).

## Source-specific / direction-conflict features

Within-source AUC sign inversions: `error_rate` .451/.567/.522; `horizon_delta`
.520/.406/.486; `risk_estimate` .432/.554/.509; `recovery_rate` .502/.448/.485;
`error_recovery_ratio` .518/.455/.492; weak: `current_streak_prior_nonerror`
.514/.483/.496 and `attempt_result_is_error` .488/.521/.502 (harness error taxonomy).
Single-source presence: `obs_between_failure_and_attempt` varies only in swegym;
verification family varies only in smith; `repeated_action_rate`/`max_repeated_action_run`
signal only in swegym; `action_observation_ratio` only in nebius.

## Semantic-equivalence flags (per-source behavior vs feature intent)

- `tool_diversity_count` constant 3/0/0 — the adapters cannot be measuring a common
  quantity; it is environment identity, not behavior.
- cmd_family-dependent features (`used_family_diversity`, `tool_switch_rate`,
  `strategy_change_after_first_failure`, `attempt_family_change`, verification family)
  are degenerate in nebius — its command taxonomy collapses to one family; verification
  mass exists only in smith. Same formula, different taxonomy per harness: NOT equivalent.
- payment family: `payment_error` and `payment_actual_total` are direction-consistent in
  all three sources — the corrected ctx payment semantics behave equivalently across
  sources; `payment_predicted_total` adds nothing (r=.991 with actual) and is
  fold-unstable (cons .6).
- attempt-side R1 features: `obs_between_failure_and_attempt` structurally 0 outside
  swegym; `attempt_repeats_prior_action` ~100% zero in nebius/smith vs 74.1% in swegym;
  `attempt_result_same_hash_as_failure` ~99% zero everywhere (no headroom) — attempt
  structure differs per harness.
- `has_recovery` constant 1.0 in nebius (recovery_attempt_count always >= 1 there):
  episode-cut depth semantics differ by source.

## Advisory top transfer features (ranked by mean |AUC-.5| across sources)

Gate: direction-consistent in all 3 sources, fold cons>=0.8, non-degenerate (OVR applied
at mean level here; see recommendation to switch to max).

| # | feature | dir edge | AUC s0/s1/s2 | cons | OVR max | note |
|---|---|---|---|---|---|---|
| 1 | fail_event_index | .122 | .401/.327/.405 | 1.0 | .540 | = n_events; negative direction |
| 2 | n_actions | .122 | .402/.327/.405 | 1.0 | .551 | depth |
| 3 | n_events | .122 | .402/.327/.406 | 1.0 | .540 | depth |
| 4 | n_observations | .121 | .403/.327/.406 | 1.0 | .530 | depth |
| 5 | avg_actions_per_step | .121 | .411/.324/.401 | 1.0 | .556 | depth-derived |
| 6 | payment_actual_total | .120 | .399/.331/.412 | 1.0 | .579 | negative |
| 7 | error_count | .110 | .394/.359/.418 | 1.0 | .515 | negative |
| 8 | recovery_attempt_count | .109 | .400/.356/.417 | 1.0 | .523 | negative |
| 9 | payment_error | .106 | .392/.359/.433 | 1.0 | .662 | negative |
| 10 | prior_episode_count | .105 | .412/.360/.412 | 1.0 | .517 | == prior_escape_count |
| 11 | prior_escape_count | .105 | .412/.360/.412 | 1.0 | .517 | duplicate of #10 |
| 12 | observation_novelty_rate | .099 | .604/.656/.538 | 1.0 | .612 | POSITIVE; strongest non-depth |
| 13 | distinct_error_count | .094 | .400/.401/.418 | 1.0 | .565 | negative |
| 14 | repeated_error_rate | .073 | .431/.372/.477 | 1.0 | .580 | negative |
| 15 | recovery_latency_mean | .073 | .400/.415/.466 | 0.8 | .596 | negative; cons exactly 0.8 |

Next-in-line: `action_observation_ratio` (.065; fails max-OVR<0.85 at .857),
`new_obs_between_failure_and_attempt` (.056, POSITIVE, .559/.598/.512, cons 1.0),
`actions_without_observation_rate` (.052). Effective distinct signals in the top 15: ~11
(depth block, payment block, prior-episode pair, error block, novelty). Direction story:
shallower failure contexts and fresher observation content predict recovery everywhere;
pooled AUCs show no pooling inflation vs within-source (n_events .402 pooled vs
.327-.406 within).

## Gate recommendation (BEFORE freezing)

1. Direction consistency across sources: KEEP — the only rule catching real sign conflicts
   (error_rate, horizon_delta, risk_estimate, recovery_rate, error_recovery_ratio,
   current_streak_prior_nonerror, attempt_result_is_error).
2. Fold-sign consistency >= 0.8: KEEP. Measured cons values are {0.0, 0.6, 0.8, 1.0}; the
   only non-degenerate features below 0.8 are collinearity artifacts (payment_predicted_total,
   repeated_action_rate, attempt_result_same_hash_as_failure, all 0.6). Any threshold in
   (0.6, 0.8] behaves identically on this corpus.
3. Identifiability: SWITCH the statistic from mean-OVR to WORST-CASE (max) OVR AUC, keep
   threshold < 0.85. Among non-degenerate features mean-OVR never exceeds .560, so a
   mean-gate at .85 excludes nothing the other rules miss; max-OVR has a clean break:
   1.000/.918/.916/.878/.875/.857 (tool_diversity_count, repeated_action_rate,
   max_repeated_action_run, used_family_diversity, tool_switch_rate,
   action_observation_ratio) vs next .673 (first_recovery_latency). Mean dilutes
   single-source identification (tool_diversity_count mean .560 despite AUC 1.000 vs
   swegym). Counts: mean-gate 27 eligible; max-gate 25 (drops action_observation_ratio,
   max_repeated_action_run).
4. ADD a degeneracy rule: drop any feature with zero within-source variance in ANY source
   of the training pool — per-source-constant features re-encode the per-source label
   base-rate under pooling (tool_diversity_count 3/0/0; six features constant everywhere).
5. Per-pool application: on a single-source pool the OVR target is single-class and the
   identifiability gate is UNDEFINED; the prereg should state the gate is skipped or
   evaluated only on multi-source pools, recorded in HARNESS.md as implementation-defined.
6. Effect size should stay OUT of the gate (it is an exclusion rule, not a ranking), but
   note 9 of the 27 mean-gate passers have mean direction edge < 0.02 (stuck_*,
   has_attempt_result, action_observation_closure_ratio, unresolved_action_rate,
   actions_since_last_observation, first_recovery_latency, attempt_repeats_prior_action) —
   eligible, not interpretable as signal.

UNDETERMINED: none — all planned computations were feasible; the only undefined quantity
is the identifiability gate on single-source pools (item 5, a prereg decision).
