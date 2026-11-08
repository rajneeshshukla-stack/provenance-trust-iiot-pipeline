## hand

| Case | Expected by hand (selected fields) | Oracle/temporal result (same fields) | Match repo (n/N) | Match reference (n/N) |
|---|---|---|---|---|
| A_forged_and_genuine_share_identity | O1=0; O2=1; NLX=0; WH=27.7; W=9.233; AV1=1.0; AV5=1.0; never=0; wdr=1; KM50=0.1; zero=0; winInc=1; winCorr=0 | O1=0; O2=1; NLX=0; WH=27.7; W=9.233; AV1=1.0; AV5=1.0; never=0; wdr=1; KM50=0.1; zero=0; winInc=1; winCorr=0 | 22/22 | 14/14 |
| B_front_running_same_ms_zero_flip_of_forgery | O1=0; O2=1; NLX=0; zero=1; WH=28.2; W=9.4; AV5=0.667; never=1; wdr=0; KM50=0.1; KM90=None | O1=0; O2=1; NLX=0; zero=1; WH=28.2; W=9.4; AV5=0.667; never=1; wdr=0; KM50=0.1; KM90=None | 14/14 | 13/13 |
| C_brief_forgery_withdrawn_by_successor | O1=0; O2=1; NLX=3.0; WH=28.2; W=9.4; AV5=0.667; never=1; wdr=0; quar=0 | O1=0; O2=1; NLX=3.0; WH=28.2; W=9.4; AV5=0.667; never=1; wdr=0; quar=0 | 16/16 | 10/10 |
| D_quarantine_then_release | O1=0; O2=0; quar=0; WH=14.1; W=7.05; AV1=0.5; AV5=0.5; AV30=1.0; never=0; wdr=0; KM50=0.1; KM90=14.0; winInc=0; winCorr=0 | O1=0; O2=0; quar=0; WH=14.1; W=7.05; AV1=0.5; AV5=0.5; AV30=1.0; never=0; wdr=0; KM50=0.1; KM90=14.0; winInc=0; winCorr=0 | 21/21 | 13/13 |
| E_b5_hold_then_release | O1=0; O2=1; NLX=0; WH=40.6; W=10.15; AV1=0.5; AV5=0.5; AV30=1.0; wdr=1; never=0; KM50=0.1; KM90=7.0; quar=0; holds=3; heldDist=3 | O1=0; O2=1; NLX=0; WH=40.6; W=10.15; AV1=0.5; AV5=0.5; AV30=1.0; wdr=1; never=0; KM50=0.1; KM90=7.0; quar=0; holds=4 **≠**; heldDist=2 **≠** | 18/20 | 14/14 |
| E2_b5_rehold_after_release | O1=0; O2=3; NLX=0; WH=76.6; W=19.15; wdr=3; never=0; AV5=0.5; AV30=1.0; quar=1; holds=5 | O1=0; O2=3; NLX=0; WH=76.6; W=19.15; wdr=3; never=0; AV5=0.5; AV30=1.0; quar=2 **≠**; holds=6 **≠** | 12/15 | 11/11 |
| F_never_released_censoring | O2=2; quar=2; WH=55.1; W=18.367; AV5=0.333; never=2; KM50=None; KM90=None; O1=0; NLX=0 | O2=2; quar=2; WH=55.1; W=18.367; AV5=0.333; never=2; KM50=None; KM90=None; O1=0; NLX=0 | 13/13 | 10/10 |
| G_duplicate_and_replay | O1=0; O2=0; dup=0; WH=0.2; W=0.1; AV1=1.0; NLX=0; zero=0 | O1=0; O2=0; dup=0; WH=0.2; W=0.1; AV1=1.0; NLX=0; zero=0 | 10/10 | 8/8 |
| H_suppressed_message | O2=1; quar=0; WH=28.2; W=9.4; never=1; AV5=0.667; KM50=0.1; KM90=None; NLX=0; O1=0 | O2=1; quar=0; WH=28.2; W=9.4; never=1; AV5=0.667; KM50=0.1; KM90=None; NLX=0; O1=0 | 12/12 | 9/9 |
| I_taint_after_revocation | O1=0; O2=2; taint=3; WH=44.3; W=14.767; NLX=3.9; AV1=1.0; never=0; wdr=2 | O1=0; O2=2; taint=3; WH=44.3; W=14.767; NLX=3.9; AV1=1.0; never=0; wdr=2 | 17/17 | 12/12 |
| J_deadline_boundaries | AV1=0.25; AV5=0.75; AV30=1.0; WH=12.002; W=3.001; KM50=1.001; KM90=5.001; ALM=1 | AV1=0.25; AV5=0.75; AV30=1.0; WH=12.002; W=3.001; KM50=1.001; KM90=5.001; ALM=1 | 12/12 | 9/9 |
| K_genuine_zero_duration | zero=1; never=1; wdr=0; AV5=0.667; WH=28.2; W=9.4; O2=1; NLX=0 | zero=1; never=1; wdr=0; AV5=0.667; WH=28.2; W=9.4; O2=1; NLX=0 | 9/9 | 8/8 |
| L_drain_phase | O1=1; O2=1; NLX=2.0; WH=26.8; W=6.7; AV5=0.25; AV30=0.5; never=2; zero=1; KM50=6.0; KM90=None; winCorr=1; winInc=0 | O1=1; O2=1; NLX=2.0; WH=26.8; W=6.7; AV5=0.25; AV30=0.5; never=2; zero=1; KM50=6.0; KM90=None; winCorr=1; winInc=0 | 18/18 | 12/12 |
| M_forgery_under_genuine_identity_retained | O1=1; O2=1; NLX=27.9; WH=28.1; W=14.05; never=1; AV5=0.5; winCorr=1 | O1=1; O2=1; NLX=27.9; WH=28.1; W=14.05; never=1; AV5=0.5; winCorr=1 | 13/13 | 8/8 |
| N_relabelled_genuine_content | O1=0; dup=1; O2=0; NLX=26.9 | O1=0; dup=1; O2=0; NLX=26.9 | 6/6 | 4/4 |
| O_pbti_sh_provisional_to_end | O1=0; O2=2; WH=54.6; W=18.2; never=1; wdr=1; quar=1 | O1=0; O2=2; WH=54.6; W=18.2; never=1; wdr=1; quar=0 **≠** | 7/9 | 6/6 |
| **Total** | | | **220/227** | **161/161** |

## runs

| Run (campaign / arm / scenario or cell / seed) | Fidelity: stored fields reproduced | O1 | O2 | NLX (rec-s) | Withheld (rec-s) | W (s/obs) | AV5 | KM p50 (s) | KM p90 (s) | Never | Withdrawn | Zero flips | Transitions | Poller = Tracer (pairs) | 21 metrics: ref = re-run = stored |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0_core / B5-hist / S05_stolen_key / 1 | 106/106 | 150 | 215 | 38208.373 | 106119.449 | 14.7388 | 0.8708 | 0.028 | 63.027 | 214 | 1 | 1 | 7141 | 7137/7137 | 21/21 |
| A0_core / B5-hist / S14_revocation / 1 | 100/100 | 0 | 270 | 8022.600 | 82117.599 | 11.4052 | 0.9736 | 0.027 | 0.045 | 190 | 80 | 0 | 7488 | 7209/7209 | 21/21 |
| A0_core / PBTI-R-hist / S99_mixed / 2 | 134/134 | 7 | 270 | 4181.761 | 150700.404 | 20.9452 | 0.8503 | 0.03 | 52.785 | 224 | 46 | 17 | 7230 | 7064/7064 | 21/21 |
| A0_core / PBTI / S05_stolen_key / 1 | 90/90 | 150 | 215 | 38231.328 | 59426.674 | 8.2537 | 0.9729 | 0.027 | 0.045 | 195 | 20 | 21 | 7265 | 7179/7179 | 21/21 |
| A0_core / PBTI / S14_revocation / 1 | 89/89 | 0 | 270 | 8022.600 | 82117.599 | 11.4052 | 0.9736 | 0.027 | 0.045 | 190 | 80 | 0 | 7488 | 7209/7209 | 21/21 |
| A1_review / B5-event / S05_stolen_key / 22 | 106/106 | 150 | 222 | 38252.843 | 62359.922 | 8.6611 | 0.9724 | 0.027 | 0.047 | 199 | 23 | 20 | 7252 | 7170/7170 | 21/21 |
| A1_review / B5-hist / S05_stolen_key / 21 | 106/106 | 150 | 221 | 38309.860 | 110100.608 | 15.2918 | 0.8682 | 0.028 | 63.589 | 220 | 1 | 1 | 7135 | 7131/7131 | 21/21 |
| A1_review / B5-hist / S08_seq_reuse_bug / 21 | 99/99 | 0 | 12 | 0.000 | 29521.352 | 4.1002 | 0.9447 | 0.027 | 0.05 | 8 | 4 | 0 | 7196 | 7192/7192 | 21/21 |
| A1_review / B5-hist / S12_beyond_horizon / 21 | 96/96 | 0 | 0 | 0.000 | 87505.197 | 12.1535 | 0.8667 | 0.028 | 40.898 | 0 | 0 | 0 | 7200 | 7200/7200 | 21/21 |
| A1_review / B5-hist / S99_mixed / 21 | 145/145 | 7 | 296 | 2627.207 | 212753.310 | 29.5696 | 0.7325 | 0.034 | 69.664 | 293 | 3 | 1 | 6934 | 6917/6917 | 21/21 |
| A1_review / PBTI-R-hist / S05_stolen_key / 21 | 97/97 | 150 | 221 | 38333.852 | 62583.887 | 8.6922 | 0.9718 | 0.027 | 0.046 | 203 | 18 | 28 | 7271 | 7172/7172 | 21/21 |
| A1_review / PBTI-R-hist / S08_seq_reuse_bug / 21 | 92/92 | 0 | 12 | 0.000 | 4067.918 | 0.5650 | 0.9994 | 0.026 | 0.043 | 4 | 8 | 0 | 7204 | 7196/7196 | 21/21 |
| A1_review / PBTI-R-hist / S12_beyond_horizon / 21 | 92/92 | 0 | 0 | 0.000 | 87505.197 | 12.1535 | 0.8667 | 0.028 | 40.898 | 0 | 0 | 0 | 7200 | 7200/7200 | 21/21 |
| A1_review / PBTI-R-hist / S99_mixed / 21 | 135/135 | 7 | 294 | 4308.293 | 161338.711 | 22.4237 | 0.8438 | 0.031 | 59.465 | 266 | 28 | 25 | 7184 | 7021/7021 | 21/21 |
| A1_review / PBTI / S05_stolen_key / 21 | 90/90 | 150 | 221 | 38333.852 | 62583.887 | 8.6922 | 0.9718 | 0.027 | 0.046 | 203 | 18 | 28 | 7271 | 7172/7172 | 21/21 |
| A1_review / PBTI / S08_seq_reuse_bug / 21 | 85/85 | 0 | 12 | 0.000 | 4067.918 | 0.5650 | 0.9994 | 0.026 | 0.043 | 4 | 8 | 0 | 7204 | 7196/7196 | 21/21 |
| A1_review / PBTI / S12_beyond_horizon / 21 | 85/85 | 0 | 193 | 0.000 | 126105.197 | 17.5146 | 0.8667 | 0.028 | 40.898 | 193 | 0 | 0 | 7007 | 7007/7007 | 21/21 |
| A1_review / PBTI / S99_mixed / 21 | 125/125 | 7 | 346 | 4308.293 | 172778.711 | 24.0137 | 0.8438 | 0.031 | 59.465 | 318 | 28 | 25 | 7132 | 6969/6969 | 21/21 |
| A3_factorial / PBTI-SH-T30 / run3 / 21 | 102/102 | 2 | 264 | 434.000 | 65502.532 | 22.7439 | 0.9007 | 0.032 | 4.041 | 262 | 4 | 1 | 2628 | 2620/2620 | 21/21 |
| A3_factorial / PBTI-SH / run3 / 21 | 102/102 | 0 | 282 | 0.000 | 68814.532 | 23.8939 | 0.9007 | 0.032 | 4.041 | 280 | 4 | 1 | 2608 | 2600/2600 | 21/21 |

all-match runs: 20/20

## sens

| Campaign / scenario / seed | Arm − base | ΔW end of production | ΔW +60 s drain | ΔW +120 s | ΔW full drain (published) | ΔW delay part | ΔW loss part | ΔAV5 (published) | ΔAV5_stable | ΔNLX (rec-s) |
|---|---|---|---|---|---|---|---|---|---|---|
| A0_core / S05_stolen_key / 1 | B5-hist − PBTI | +5.632 | +6.485 | +6.485 | +6.485 | +6.485 | +0.000 | -0.1021 | -0.0994 | -23.0 |
| A0_core / S14_revocation / 1 | B5-hist − PBTI | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.0000 | +0.0000 | +0.0 |
| A1_review / S05_stolen_key / 21 | B5-hist − PBTI | +5.741 | +6.598 | +6.600 | +6.600 | +6.599 | +0.000 | -0.1036 | -0.1012 | -24.0 |
| A1_review / S05_stolen_key / 21 | PBTI-R-hist − PBTI | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.0000 | +0.0000 | +0.0 |
| A1_review / S08_seq_reuse_bug / 21 | B5-hist − PBTI | +2.952 | +3.535 | +3.535 | +3.535 | +3.534 | +0.001 | -0.0547 | -0.0542 | +0.0 |
| A1_review / S08_seq_reuse_bug / 21 | PBTI-R-hist − PBTI | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 | +0.0000 | +0.0000 | +0.0 |
| A1_review / S12_beyond_horizon / 21 | B5-hist − PBTI | -0.536 | -2.144 | -3.753 | -5.361 | +5.463 | -10.824 | +0.0000 | +0.0000 | +0.0 |
| A1_review / S12_beyond_horizon / 21 | PBTI-R-hist − PBTI | -0.536 | -2.144 | -3.753 | -5.361 | +5.463 | -10.824 | +0.0000 | +0.0000 | +0.0 |
| A1_review / S99_mixed / 21 | B5-hist − PBTI | +5.662 | +6.387 | +5.973 | +5.556 | +8.495 | -2.940 | -0.1113 | -0.1079 | -1681.1 |
| A1_review / S99_mixed / 21 | PBTI-R-hist − PBTI | -0.289 | -0.723 | -1.156 | -1.590 | +1.410 | -3.000 | +0.0000 | +0.0000 | +0.0 |
| A3_factorial / run3 / 21 | PBTI-SH-T30 − PBTI-SH | -0.095 | -0.400 | -0.775 | -1.150 | +0.193 | -1.343 | +0.0000 | +0.0000 | +434.0 |

## wdecomp

| Run | W (s/obs) | delay part | permanent-loss part | loss share | AV5 | AV5_stable | relabelled NL pairs |
|---|---|---|---|---|---|---|---|
| A0_core / B5-hist / S05_stolen_key / 1 | 14.739 | 6.514 | 8.225 | 55.8% | 0.8708 | 0.8707 | 0 |
| A0_core / B5-hist / S14_revocation / 1 | 11.405 | 0.028 | 11.377 | 99.8% | 0.9736 | 0.9625 | 0 |
| A0_core / PBTI-R-hist / S99_mixed / 2 | 20.945 | 8.380 | 12.566 | 60.0% | 0.8503 | 0.8441 | 0 |
| A0_core / PBTI / S05_stolen_key / 1 | 8.254 | 0.029 | 8.225 | 99.7% | 0.9729 | 0.9701 | 0 |
| A0_core / PBTI / S14_revocation / 1 | 11.405 | 0.028 | 11.377 | 99.8% | 0.9736 | 0.9625 | 0 |
| A1_review / B5-event / S05_stolen_key / 22 | 8.661 | 0.037 | 8.624 | 99.6% | 0.9724 | 0.9692 | 0 |
| A1_review / B5-hist / S05_stolen_key / 21 | 15.292 | 6.628 | 8.664 | 56.7% | 0.8682 | 0.8681 | 0 |
| A1_review / B5-hist / S08_seq_reuse_bug / 21 | 4.100 | 3.564 | 0.536 | 13.1% | 0.9447 | 0.9442 | 0 |
| A1_review / B5-hist / S12_beyond_horizon / 21 | 12.153 | 12.153 | 0.000 | 0.0% | 0.8667 | 0.8667 | 0 |
| A1_review / B5-hist / S99_mixed / 21 | 29.570 | 15.520 | 14.049 | 47.5% | 0.7325 | 0.7323 | 0 |
| A1_review / PBTI-R-hist / S05_stolen_key / 21 | 8.692 | 0.029 | 8.664 | 99.7% | 0.9718 | 0.9693 | 0 |
| A1_review / PBTI-R-hist / S08_seq_reuse_bug / 21 | 0.565 | 0.029 | 0.536 | 94.8% | 0.9994 | 0.9983 | 0 |
| A1_review / PBTI-R-hist / S12_beyond_horizon / 21 | 12.153 | 12.153 | 0.000 | 0.0% | 0.8667 | 0.8667 | 0 |
| A1_review / PBTI-R-hist / S99_mixed / 21 | 22.424 | 8.435 | 13.988 | 62.4% | 0.8438 | 0.8402 | 0 |
| A1_review / PBTI / S05_stolen_key / 21 | 8.692 | 0.029 | 8.664 | 99.7% | 0.9718 | 0.9693 | 0 |
| A1_review / PBTI / S08_seq_reuse_bug / 21 | 0.565 | 0.029 | 0.536 | 94.8% | 0.9994 | 0.9983 | 0 |
| A1_review / PBTI / S12_beyond_horizon / 21 | 17.515 | 6.690 | 10.824 | 61.8% | 0.8667 | 0.8667 | 0 |
| A1_review / PBTI / S99_mixed / 21 | 24.014 | 7.025 | 16.989 | 70.7% | 0.8438 | 0.8402 | 0 |
| A3_factorial / PBTI-SH-T30 / run3 / 21 | 22.744 | 0.574 | 22.170 | 97.5% | 0.9007 | 0.9000 | 0 |
| A3_factorial / PBTI-SH / run3 / 21 | 23.894 | 0.381 | 23.513 | 98.4% | 0.9007 | 0.9000 | 0 |
