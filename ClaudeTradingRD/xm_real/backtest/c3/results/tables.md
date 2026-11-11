### T0. Price basis, XM GOLD minus OANDA XAU_USD (S5 quote at the deal instant)

| what | n | median | mean | sd | p05 | p95 |
|---|---|---|---|---|---|---|
| SELL deals vs OANDA bid | 159 | -0.042 | -0.169 | +1.060 | -0.441 | +0.522 |
| BUY deals vs OANDA ask | 162 | +0.054 | +0.075 | +1.736 | -0.649 | +0.430 |
| stop-out deals (excluded above) | 34 | -0.749 | -2.515 | +6.764 | -23.193 | +0.531 |

### T1. Default cell (TP 1.5 ATR / SL 1.5 ATR / K_FADE 0.6): every window at every cost level

| cost | window | n | win | pf_usd | pf_pts | net_pts | avg_pts | net_usd | usd_004lot | maxdd_usd | worst_day_usd | days | months_pos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spec_base | TRAIN | 1009 | 43.7% | 0.724 | 0.776 | -1018.0 | -1.009 | -4726 | -4072 | 4795 | -127 | 177 | 0/9 |
| spec_base | TEST | 972 | 45.5% | 0.777 | 0.833 | -616.2 | -0.634 | -3693 | -2465 | 3938 | -128 | 154 | 0/8 |
| spec_base | FULL | 1981 | 44.6% | 0.750 | 0.801 | -1634.3 | -0.825 | -8419 | -6537 | 8436 | -128 | 331 | 0/17 |
| spec_base | WEEK | 45 | 48.9% | 1.004 | 1.127 | +19.8 | +0.441 | +3 | +79 | 225 | -50 | 6 | 1/1 |
| spec_stress | TRAIN | 967 | 41.6% | 0.610 | 0.677 | -1514.3 | -1.566 | -7035 | -6057 | 7035 | -134 | 177 | 0/9 |
| spec_stress | TEST | 945 | 44.8% | 0.705 | 0.769 | -888.8 | -0.941 | -5061 | -3555 | 5266 | -122 | 154 | 0/8 |
| spec_stress | FULL | 1912 | 43.1% | 0.656 | 0.719 | -2403.1 | -1.257 | -12096 | -9612 | 12096 | -134 | 331 | 0/17 |
| spec_stress | WEEK | 47 | 51.1% | 1.046 | 1.120 | +19.9 | +0.423 | +31 | +80 | 215 | -58 | 6 | 1/1 |
| flat_0.45 | TRAIN | 1017 | 44.4% | 0.782 | 0.823 | -770.9 | -0.758 | -3580 | -3084 | 3781 | -123 | 177 | 1/9 |
| flat_0.45 | TEST | 990 | 46.2% | 0.829 | 0.885 | -407.7 | -0.412 | -2720 | -1631 | 2996 | -123 | 154 | 1/8 |
| flat_0.45 | FULL | 2007 | 45.3% | 0.805 | 0.851 | -1178.6 | -0.587 | -6300 | -4714 | 6461 | -123 | 331 | 2/17 |
| flat_0.45 | WEEK | 45 | 51.1% | 1.054 | 1.179 | +26.9 | +0.597 | +33 | +108 | 200 | -45 | 6 | 1/1 |
| flat_0.80 | TRAIN | 986 | 42.0% | 0.693 | 0.747 | -1117.2 | -1.133 | -5075 | -4469 | 5075 | -124 | 177 | 0/9 |
| flat_0.80 | TEST | 962 | 45.0% | 0.786 | 0.845 | -553.7 | -0.576 | -3400 | -2215 | 3787 | -126 | 154 | 0/8 |
| flat_0.80 | FULL | 1948 | 43.5% | 0.739 | 0.791 | -1670.9 | -0.858 | -8475 | -6684 | 8475 | -126 | 331 | 0/17 |
| flat_0.80 | WEEK | 47 | 51.1% | 1.140 | 1.214 | +32.8 | +0.698 | +88 | +131 | 172 | -48 | 6 | 1/1 |

### T2. All six pre-registered cells, TRAIN and TEST, spec base and spec stress cost

| cell | cost | window | n | win | pf_usd | pf_pts | net_pts | avg_pts | net_usd | maxdd_usd | worst_day_usd | months_pos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TP1.5/SL1.5/K0.6 | spec_base | TRAIN | 1009 | 43.7% | 0.724 | 0.776 | -1018.0 | -1.009 | -4726 | 4795 | -127 | 0/9 |
| TP1.5/SL1.5/K0.6 | spec_base | TEST | 972 | 45.5% | 0.777 | 0.833 | -616.2 | -0.634 | -3693 | 3938 | -128 | 0/8 |
| TP1.5/SL1.5/K0.6 | spec_stress | TRAIN | 967 | 41.6% | 0.610 | 0.677 | -1514.3 | -1.566 | -7035 | 7035 | -134 | 0/9 |
| TP1.5/SL1.5/K0.6 | spec_stress | TEST | 945 | 44.8% | 0.705 | 0.769 | -888.8 | -0.941 | -5061 | 5266 | -122 | 0/8 |
| TP2.5/SL2.5/K0.6 | spec_base | TRAIN | 1496 | 47.5% | 0.834 | 0.843 | -1141.0 | -0.763 | -2713 | 2713 | -128 | 3/9 |
| TP2.5/SL2.5/K0.6 | spec_base | TEST | 1542 | 46.2% | 0.796 | 0.831 | -1188.4 | -0.771 | -3645 | 3682 | -145 | 0/8 |
| TP2.5/SL2.5/K0.6 | spec_stress | TRAIN | 1447 | 46.3% | 0.743 | 0.732 | -2027.3 | -1.401 | -4377 | 4377 | -133 | 1/9 |
| TP2.5/SL2.5/K0.6 | spec_stress | TEST | 1465 | 44.4% | 0.703 | 0.752 | -1768.5 | -1.207 | -5451 | 5451 | -156 | 0/8 |
| TP1.5/SL2.5/K0.6 | spec_base | TRAIN | 1682 | 52.5% | 0.828 | 0.856 | -1066.7 | -0.634 | -2857 | 2869 | -128 | 3/9 |
| TP1.5/SL2.5/K0.6 | spec_base | TEST | 1593 | 51.7% | 0.738 | 0.779 | -1542.8 | -0.968 | -4637 | 4730 | -142 | 1/8 |
| TP1.5/SL2.5/K0.6 | spec_stress | TRAIN | 1569 | 50.6% | 0.716 | 0.745 | -1930.6 | -1.230 | -4831 | 4831 | -142 | 0/9 |
| TP1.5/SL2.5/K0.6 | spec_stress | TEST | 1525 | 49.4% | 0.644 | 0.684 | -2272.4 | -1.490 | -6523 | 6531 | -147 | 0/8 |
| TP1.5/SL1.5/K1.0 | spec_base | TRAIN | 955 | 44.1% | 0.703 | 0.762 | -1013.2 | -1.061 | -4941 | 5084 | -115 | 1/9 |
| TP1.5/SL1.5/K1.0 | spec_base | TEST | 903 | 44.9% | 0.739 | 0.778 | -789.7 | -0.875 | -4250 | 4489 | -116 | 2/8 |
| TP1.5/SL1.5/K1.0 | spec_stress | TRAIN | 900 | 39.7% | 0.558 | 0.644 | -1589.0 | -1.766 | -7778 | 7778 | -124 | 0/9 |
| TP1.5/SL1.5/K1.0 | spec_stress | TEST | 870 | 43.6% | 0.661 | 0.707 | -1077.9 | -1.239 | -5704 | 5877 | -124 | 1/8 |
| TP2.5/SL2.5/K1.0 | spec_base | TRAIN | 1372 | 47.2% | 0.792 | 0.815 | -1256.6 | -0.916 | -3210 | 3274 | -133 | 2/9 |
| TP2.5/SL2.5/K1.0 | spec_base | TEST | 1435 | 47.5% | 0.822 | 0.867 | -870.2 | -0.606 | -2976 | 3393 | -130 | 2/8 |
| TP2.5/SL2.5/K1.0 | spec_stress | TRAIN | 1328 | 45.6% | 0.720 | 0.761 | -1639.8 | -1.235 | -4449 | 4510 | -137 | 1/9 |
| TP2.5/SL2.5/K1.0 | spec_stress | TEST | 1351 | 44.6% | 0.703 | 0.749 | -1671.1 | -1.237 | -5122 | 5208 | -136 | 0/8 |
| TP1.5/SL2.5/K1.0 | spec_base | TRAIN | 1456 | 52.8% | 0.787 | 0.816 | -1224.9 | -0.841 | -3235 | 3358 | -147 | 2/9 |
| TP1.5/SL2.5/K1.0 | spec_base | TEST | 1560 | 52.9% | 0.789 | 0.841 | -1024.1 | -0.656 | -3502 | 3526 | -130 | 0/8 |
| TP1.5/SL2.5/K1.0 | spec_stress | TRAIN | 1412 | 50.6% | 0.698 | 0.731 | -1846.0 | -1.307 | -4782 | 4828 | -140 | 1/9 |
| TP1.5/SL2.5/K1.0 | spec_stress | TEST | 1441 | 50.2% | 0.661 | 0.711 | -1902.9 | -1.321 | -5832 | 5838 | -134 | 0/8 |

### T3. All six cells at the task's flat round-trip costs (0.45 and 0.80 pts), TRAIN and TEST

| cell | cost | window | n | win | pf_usd | pf_pts | net_pts | avg_pts | net_usd | maxdd_usd | worst_day_usd | months_pos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TP1.5/SL1.5/K0.6 | flat_0.45 | TRAIN | 1017 | 44.4% | 0.782 | 0.823 | -770.9 | -0.758 | -3580 | 3781 | -123 | 1/9 |
| TP1.5/SL1.5/K0.6 | flat_0.45 | TEST | 990 | 46.2% | 0.829 | 0.885 | -407.7 | -0.412 | -2720 | 2996 | -123 | 1/8 |
| TP1.5/SL1.5/K0.6 | flat_0.80 | TRAIN | 986 | 42.0% | 0.693 | 0.747 | -1117.2 | -1.133 | -5075 | 5075 | -124 | 0/9 |
| TP1.5/SL1.5/K0.6 | flat_0.80 | TEST | 962 | 45.0% | 0.786 | 0.845 | -553.7 | -0.576 | -3400 | 3787 | -126 | 0/8 |
| TP2.5/SL2.5/K0.6 | flat_0.45 | TRAIN | 1503 | 47.8% | 0.858 | 0.864 | -972.2 | -0.647 | -2281 | 2281 | -125 | 3/9 |
| TP2.5/SL2.5/K0.6 | flat_0.45 | TEST | 1602 | 48.4% | 0.893 | 0.916 | -576.9 | -0.360 | -1857 | 1895 | -131 | 1/8 |
| TP2.5/SL2.5/K0.6 | flat_0.80 | TRAIN | 1470 | 46.4% | 0.802 | 0.792 | -1520.6 | -1.034 | -3234 | 3234 | -136 | 2/9 |
| TP2.5/SL2.5/K0.6 | flat_0.80 | TEST | 1515 | 45.7% | 0.784 | 0.826 | -1207.8 | -0.797 | -3810 | 3810 | -147 | 0/8 |
| TP1.5/SL2.5/K0.6 | flat_0.45 | TRAIN | 1704 | 52.6% | 0.858 | 0.889 | -808.8 | -0.475 | -2292 | 2376 | -125 | 2/9 |
| TP1.5/SL2.5/K0.6 | flat_0.45 | TEST | 1653 | 52.6% | 0.787 | 0.819 | -1259.8 | -0.762 | -3701 | 3833 | -126 | 1/8 |
| TP1.5/SL2.5/K0.6 | flat_0.80 | TRAIN | 1600 | 51.6% | 0.788 | 0.809 | -1384.4 | -0.865 | -3429 | 3438 | -127 | 2/9 |
| TP1.5/SL2.5/K0.6 | flat_0.80 | TEST | 1537 | 51.0% | 0.710 | 0.758 | -1645.1 | -1.070 | -5011 | 5103 | -141 | 1/8 |
| TP1.5/SL1.5/K1.0 | flat_0.45 | TRAIN | 961 | 44.5% | 0.748 | 0.798 | -829.6 | -0.863 | -4012 | 4316 | -112 | 1/9 |
| TP1.5/SL1.5/K1.0 | flat_0.45 | TEST | 921 | 45.8% | 0.807 | 0.843 | -537.2 | -0.583 | -3000 | 3291 | -110 | 2/8 |
| TP1.5/SL1.5/K1.0 | flat_0.80 | TRAIN | 918 | 41.2% | 0.643 | 0.718 | -1168.8 | -1.273 | -5752 | 5752 | -114 | 0/9 |
| TP1.5/SL1.5/K1.0 | flat_0.80 | TEST | 897 | 45.0% | 0.769 | 0.813 | -635.7 | -0.709 | -3590 | 3891 | -112 | 2/8 |
| TP2.5/SL2.5/K1.0 | flat_0.45 | TRAIN | 1372 | 47.5% | 0.840 | 0.847 | -1013.4 | -0.739 | -2390 | 2460 | -128 | 2/9 |
| TP2.5/SL2.5/K1.0 | flat_0.45 | TEST | 1460 | 48.7% | 0.882 | 0.915 | -541.2 | -0.371 | -1911 | 2571 | -131 | 3/8 |
| TP2.5/SL2.5/K1.0 | flat_0.80 | TRAIN | 1354 | 46.4% | 0.777 | 0.807 | -1291.6 | -0.954 | -3401 | 3464 | -131 | 2/9 |
| TP2.5/SL2.5/K1.0 | flat_0.80 | TEST | 1391 | 46.3% | 0.791 | 0.834 | -1060.5 | -0.762 | -3422 | 3721 | -128 | 2/8 |
| TP1.5/SL2.5/K1.0 | flat_0.45 | TRAIN | 1462 | 53.1% | 0.823 | 0.847 | -995.0 | -0.681 | -2617 | 2761 | -141 | 2/9 |
| TP1.5/SL2.5/K1.0 | flat_0.45 | TEST | 1615 | 54.9% | 0.873 | 0.915 | -540.6 | -0.335 | -2049 | 2206 | -126 | 2/8 |
| TP1.5/SL2.5/K1.0 | flat_0.80 | TRAIN | 1440 | 51.9% | 0.766 | 0.792 | -1380.2 | -0.958 | -3540 | 3643 | -130 | 1/9 |
| TP1.5/SL2.5/K1.0 | flat_0.80 | TEST | 1503 | 52.3% | 0.761 | 0.817 | -1148.8 | -0.764 | -3886 | 3913 | -127 | 0/8 |

### T4. Default cell: 95% intervals from a bootstrap over UTC days (2000 resamples); MDE = 2.8 x SE of mean points per trade

| cost | window | n | pf_usd | pf_ci95 | net_usd | net_usd_ci95 | avg_pts | avg_pts_ci95 | p_net_le0 | sd_pts | mde_pts_80pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| spec_base | TRAIN | 1009 | 0.724 | 0.641 .. 0.812 | -4726 | -6218 .. -3164 | -1.009 | -1.510 .. -0.540 | 100.0% | 9.72 | 0.856 |
| spec_base | TEST | 972 | 0.777 | 0.684 .. 0.872 | -3693 | -5242 .. -2110 | -0.634 | -1.095 .. -0.183 | 100.0% | 7.49 | 0.673 |
| spec_stress | TRAIN | 967 | 0.610 | 0.527 .. 0.695 | -7035 | -8569 .. -5461 | -1.566 | -2.109 .. -1.065 | 100.0% | 9.79 | 0.882 |
| spec_stress | TEST | 945 | 0.705 | 0.619 .. 0.792 | -5061 | -6547 .. -3560 | -0.941 | -1.419 .. -0.509 | 100.0% | 7.70 | 0.702 |
| flat_0.45 | TRAIN | 1017 | 0.782 | 0.688 .. 0.889 | -3580 | -5171 .. -1835 | -0.758 | -1.280 .. -0.260 | 100.0% | 9.57 | 0.840 |
| flat_0.45 | TEST | 990 | 0.829 | 0.733 .. 0.925 | -2720 | -4255 .. -1194 | -0.412 | -0.855 .. +0.015 | 100.0% | 7.33 | 0.652 |
| flat_0.80 | TRAIN | 986 | 0.693 | 0.608 .. 0.779 | -5075 | -6511 .. -3618 | -1.133 | -1.635 .. -0.668 | 100.0% | 9.57 | 0.853 |
| flat_0.80 | TEST | 962 | 0.786 | 0.693 .. 0.883 | -3400 | -4905 .. -1857 | -0.576 | -1.041 .. -0.116 | 100.0% | 7.40 | 0.668 |

### T5. Default cell at spec base cost: exit mix and sides

| window | subset | n | share | win | avg_pts | net_pts | net_usd |
|---|---|---|---|---|---|---|---|
| TRAIN | all | 1009 | 100.0% | 43.7% | -1.009 | -1018.0 | -4726 |
| TRAIN | exit=tp | 350 | 34.7% | 100.0% | +9.114 | +3189.8 | +11237 |
| TRAIN | exit=stop | 482 | 47.8% | 0.0% | -8.862 | -4271.4 | -16179 |
| TRAIN | exit=time | 157 | 15.6% | 50.3% | +0.433 | +68.0 | +160 |
| TRAIN | exit=eod | 1 | 0.1% | 0.0% | -17.070 | -17.1 | -17 |
| TRAIN | exit=news | 19 | 1.9% | 63.2% | +0.668 | +12.7 | +74 |
| TRAIN | long | 490 | 48.6% | 46.9% | -0.631 | -309.0 | -1328 |
| TRAIN | short | 519 | 51.4% | 40.7% | -1.366 | -709.1 | -3398 |
| TRAIN | target-before-stop among bracket exits | 832 | 82.5% | 42.1% | -1.300 | -1081.6 | -4942 |
| TEST | all | 972 | 100.0% | 45.5% | -0.634 | -616.2 | -3693 |
| TEST | exit=tp | 364 | 37.4% | 100.0% | +7.689 | +2798.8 | +11874 |
| TEST | exit=stop | 462 | 47.5% | 0.0% | -7.561 | -3493.4 | -15802 |
| TEST | exit=time | 145 | 14.9% | 53.1% | +0.513 | +74.4 | +227 |
| TEST | exit=news | 1 | 0.1% | 100.0% | +3.935 | +3.9 | +8 |
| TEST | long | 512 | 52.7% | 41.2% | -1.316 | -673.8 | -3176 |
| TEST | short | 460 | 47.3% | 50.2% | +0.125 | +57.5 | -516 |
| TEST | target-before-stop among bracket exits | 826 | 85.0% | 44.1% | -0.841 | -694.6 | -3928 |

### T6. Default cell, TEST by calendar month (2026-11 holds two trading days, 11-02 and 11-03)

| month | cost | n | win | net_pts | net_usd | pf_usd |
|---|---|---|---|---|---|---|
| 2026-04 | spec_base | 147 | 46.9% | -19.6 | -381 | 0.836 |
| 2026-05 | spec_base | 144 | 52.1% | +17.4 | -42 | 0.981 |
| 2026-06 | spec_base | 147 | 46.3% | -106.6 | -283 | 0.878 |
| 2026-07 | spec_base | 131 | 38.2% | -240.5 | -1153 | 0.542 |
| 2026-08 | spec_base | 134 | 48.5% | -7.0 | -273 | 0.876 |
| 2026-09 | spec_base | 135 | 43.7% | -124.2 | -646 | 0.731 |
| 2026-10 | spec_base | 123 | 41.5% | -124.7 | -859 | 0.639 |
| 2026-11 | spec_base | 11 | 45.5% | -11.1 | -55 | 0.723 |
| 2026-04 | spec_stress | 142 | 47.9% | -52.1 | -466 | 0.799 |
| 2026-05 | spec_stress | 148 | 52.7% | +7.3 | -100 | 0.957 |
| 2026-06 | spec_stress | 135 | 45.2% | -157.9 | -550 | 0.763 |
| 2026-07 | spec_stress | 132 | 39.4% | -261.9 | -1160 | 0.550 |
| 2026-08 | spec_stress | 136 | 49.3% | -15.5 | -370 | 0.840 |
| 2026-09 | spec_stress | 131 | 41.2% | -162.5 | -908 | 0.647 |
| 2026-10 | spec_stress | 112 | 35.7% | -221.1 | -1384 | 0.453 |
| 2026-11 | spec_stress | 9 | 33.3% | -25.1 | -123 | 0.394 |
| 2026-04 | flat_0.80 | 145 | 48.3% | +25.8 | -172 | 0.921 |
| 2026-05 | flat_0.80 | 142 | 51.4% | +8.7 | -80 | 0.963 |
| 2026-06 | flat_0.80 | 145 | 45.5% | -91.0 | -241 | 0.892 |
| 2026-07 | flat_0.80 | 128 | 36.7% | -251.5 | -1139 | 0.528 |
| 2026-08 | flat_0.80 | 135 | 48.9% | +18.2 | -164 | 0.922 |
| 2026-09 | flat_0.80 | 138 | 44.2% | -99.9 | -570 | 0.757 |
| 2026-10 | flat_0.80 | 120 | 39.2% | -142.5 | -929 | 0.597 |
| 2026-11 | flat_0.80 | 9 | 33.3% | -21.5 | -106 | 0.432 |

### T7. Default cell vs 200 random-signal controls at spec base cost (same firing rate per UTC hour x calendar month x side; identical exits, sizing, brakes). The gate reads TEST net_pts only

| window | metric | real | ctrl_mean | ctrl_p05 | ctrl_median | ctrl_p95 | real_percentile |
|---|---|---|---|---|---|---|---|
| TRAIN | n | 1009.000 | 1066.420 | 1007.000 | 1069.000 | 1121.000 | 6.5 |
| TRAIN | win | 0.437 | 0.451 | 0.422 | 0.451 | 0.476 | 19.5 |
| TRAIN | pf_usd | 0.724 | 0.777 | 0.690 | 0.774 | 0.854 | 17.0 |
| TRAIN | net_pts | -1018.023 | -867.084 | -1373.348 | -832.383 | -383.446 | 30.5 |
| TRAIN | avg_pts | -1.009 | -0.821 | -1.338 | -0.772 | -0.353 | 25.5 |
| TRAIN | net_usd | -4726.155 | -3854.327 | -5377.529 | -3933.646 | -2475.692 | 17.5 |
| TEST | n | 972.000 | 974.195 | 925.850 | 973.000 | 1031.100 | 49.0 |
| TEST | win | 0.455 | 0.452 | 0.428 | 0.452 | 0.478 | 58.0 |
| TEST | pf_usd | 0.777 | 0.780 | 0.696 | 0.778 | 0.876 | 48.0 |
| TEST | net_pts | -616.239 | -798.902 | -1155.352 | -798.334 | -415.560 | 83.0 |
| TEST | avg_pts | -0.634 | -0.827 | -1.248 | -0.822 | -0.403 | 81.5 |
| TEST | net_usd | -3692.650 | -3632.750 | -4974.983 | -3671.946 | -2068.973 | 47.5 |

### T8. Dose-response at TP 1.5 / SL 1.5, spec base cost: K_FADE 1.0 against 0.6 (SE is binomial, trades treated as independent)

| window | n_K06 | win_K06 | avg_pts_K06 | n_K10 | win_K10 | avg_pts_K10 | win_diff_pp | se_pp | higher |
|---|---|---|---|---|---|---|---|---|---|
| TRAIN | 1009 | 43.7% | -1.009 | 955 | 44.1% | -1.061 | +0.38 | 2.24 | True |
| TEST | 972 | 45.5% | -0.634 | 903 | 44.9% | -0.875 | -0.62 | 2.30 | False |

### T9. Pre-registered pass marks (spec 9.3), default cell

| gate | requirement (spec 9.3, default cell) | measured | pass |
|---|---|---|---|
| 1 | PF >= 1.15 base and >= 1.00 stress, TRAIN and TEST (USD PF) | TRAIN 0.724 / 0.610; TEST 0.777 / 0.705 | FAIL |
| 2 | TEST total points above the 95th percentile of 200 random controls | real -616.2 vs control p95 -415.6 (real at percentile 83.0) | FAIL |
| 3 | >= 60% of TEST months net positive and no month > 40% of TEST net | 0 of 8 months positive; TEST net -3693 USD (not positive, so the share test cannot be met) | FAIL |
| 4 | At least half of the 5 neighbouring cells with TEST PF > 1.00 at base cost | 0 of 5 (PFs 0.796, 0.738, 0.739, 0.822, 0.789) | FAIL |
| 5 | K_FADE 1.0 win rate above K_FADE 0.6 on TRAIN and on TEST | TRAIN 44.1% vs 43.7%; TEST 44.9% vs 45.5% | FAIL |
| 6 | At least 300 trades in TEST | 972 | PASS |

### T10. The task brief's generic bars, default cell

| bar (task brief, flat 0.80 pts round trip) | measured | pass |
|---|---|---|
| TEST PF >= 1.15 at 0.80 cost | 0.786 | FAIL |
| Positive in both halves of TEST | -1103 / -2297 USD | FAIL |
| >= 60% positive TEST months | 0 of 8 | FAIL |
| No single month above half of net | TEST net -3400 USD (not positive) | FAIL |
| n >= 200 TEST trades | 962 | PASS |

### T11. Small-account survival, default cell, every UTC trading day of TRAIN+TEST as a start date. Ruin = closed-trade equity below 38 USD (cannot fund the next trade's risk). Start dates near the end have little time left to fail (censored).

| cost | start_equity | start_dates | ruined_before_data_end | median_calendar_days_to_ruin | starts_with_60d_ahead | ruined_within_60_trading_days |
|---|---|---|---|---|---|---|
| spec_base | 200 | 331 | 98.5% | 6 | 271 | 100.0% |
| spec_base | 1000 | 331 | 92.7% | 48 | 271 | 95.9% |
| spec_stress | 200 | 331 | 99.4% | 5 | 271 | 100.0% |
| spec_stress | 1000 | 331 | 95.5% | 36 | 271 | 100.0% |

### T12. Trade-week replication, default cell at spec base cost. Strategy entries inside the trader's active span (11-04 10:08 .. 11-11 06:26 UTC): 37; raw K=0.6 trigger bars in session: 1435; random-control strategies: 200 draws, mean 35 entries each

| measure | n | strategy_trades | random_control_mean | control_p95 | percentile_vs_control | raw_trigger_bars | raw_trigger_chance |
|---|---|---|---|---|---|---|---|
| strategy entries with a real same-side position opened within +-5 min (hit rate) | 37 | 10.8% | 9.5% | 16.2% | 62 | 17.1% |  |
| same, but opposite side (placebo) | 37 | 8.1% | 8.8% | 16.1% | 46 | 5.5% |  |
| real positions (178) with a same-side strategy entry within +-5 min | 178 | 2.8% | 3.9% | 11.2% | 42 | 51.7% | 48.0% |
| real decisions (124) explained | 124 | 3.2% | 3.3% | 6.5% | 42 | 60.5% | 48.0% |
| real fresh entries (27) explained | 27 | 0.0% | 1.9% | 7.4% | 0 | 59.3% | 48.0% |

### T13. Trade week 2026-11-04 .. 11-11 13:43 UTC, side by side (parity only; 6 trading days)

| who | n | win | net_pts | net_usd | pf_usd |
|---|---|---|---|---|---|
| trader, real (trades.csv; pts counts both legs of the 4 close-by pairs) | 178 | 75.8% | +339.8 | +491 | 1.130 |
| XMR-3 default, spec_base | 45 | 48.9% | +19.8 | +3 | 1.004 |
| XMR-3 default, spec_stress | 47 | 51.1% | +19.9 | +31 | 1.046 |
| XMR-3 default, flat_0.45 | 45 | 51.1% | +26.9 | +33 | 1.054 |
| XMR-3 default, flat_0.80 | 47 | 51.1% | +32.8 | +88 | 1.140 |

### T14. Exit resolution on S5 bid/ask against M1 bid/ask, same entries (2026-11-03 .. 11-11; S5 exists for this stretch only)

| cell | cost | n | exit_kind_changed | m1_net_pts | s5_net_pts | diff_pts_per_trade | m1_win | s5_win | m1_net_usd | s5_net_usd |
|---|---|---|---|---|---|---|---|---|---|---|
| TP1.5/SL1.5/K0.6 | spec_base | 48 | 0 | -2.3 | -2.3 | -0.000 | 45.8% | 45.8% | -92 | -93 |
| TP1.5/SL1.5/K0.6 | spec_stress | 50 | 0 | -3.2 | -3.2 | +0.000 | 48.0% | 48.0% | -68 | -68 |
| TP2.5/SL2.5/K0.6 | spec_base | 93 | 0 | +80.3 | +80.3 | +0.000 | 51.6% | 51.6% | +206 | +206 |
| TP2.5/SL2.5/K0.6 | spec_stress | 86 | 0 | +59.3 | +59.3 | +0.000 | 53.5% | 53.5% | +127 | +127 |
| TP1.5/SL2.5/K0.6 | spec_base | 78 | 0 | -105.9 | -105.9 | +0.000 | 47.4% | 47.4% | -315 | -315 |
| TP1.5/SL2.5/K0.6 | spec_stress | 72 | 0 | -105.8 | -105.8 | +0.000 | 48.6% | 48.6% | -284 | -284 |
| TP1.5/SL1.5/K1.0 | spec_base | 45 | 0 | -29.0 | -29.0 | +0.000 | 46.7% | 46.7% | -187 | -187 |
| TP1.5/SL1.5/K1.0 | spec_stress | 45 | 0 | -38.5 | -38.5 | +0.000 | 44.4% | 44.4% | -230 | -230 |
| TP2.5/SL2.5/K1.0 | spec_base | 92 | 0 | +199.0 | +199.0 | +0.000 | 60.9% | 60.9% | +441 | +441 |
| TP2.5/SL2.5/K1.0 | spec_stress | 88 | 0 | +162.5 | +162.5 | +0.000 | 59.1% | 59.1% | +318 | +318 |
| TP1.5/SL2.5/K1.0 | spec_base | 87 | 0 | +13.3 | +13.3 | +0.000 | 58.6% | 58.6% | +8 | +8 |
| TP1.5/SL2.5/K1.0 | spec_stress | 86 | 0 | -9.1 | -9.1 | +0.000 | 57.0% | 57.0% | -56 | -56 |

### T15. Secondary, report only: 2019-01-01 .. 2025-07-15 on `m3_scalper/xau_m1_full.parquet` (mid; never part of pass/fail)

| cell | cost | n | win | pf_usd | pf_pts | net_pts | avg_pts | net_usd | maxdd_usd | worst_day_usd | months_pos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TP1.5/SL1.5/K0.6 | 1.5bp spread, slip 0.30 | 1984 | 46.8% | 0.808 | 0.814 | -970.8 | -0.489 | -6090 | 6823 | -118 | 28/68 |
| TP2.5/SL2.5/K0.6 | 1.5bp spread, slip 0.30 | 1995 | 47.6% | 0.804 | 0.815 | -1163.5 | -0.583 | -4254 | 4728 | -135 | 25/68 |
| TP1.5/SL2.5/K0.6 | 1.5bp spread, slip 0.30 | 2199 | 52.0% | 0.803 | 0.813 | -1208.9 | -0.550 | -4373 | 4639 | -135 | 27/68 |
| TP1.5/SL1.5/K1.0 | 1.5bp spread, slip 0.30 | 1715 | 47.9% | 0.843 | 0.866 | -600.2 | -0.350 | -4295 | 4802 | -119 | 28/68 |
| TP2.5/SL2.5/K1.0 | 1.5bp spread, slip 0.30 | 1675 | 47.4% | 0.813 | 0.828 | -940.3 | -0.561 | -3496 | 3620 | -154 | 27/68 |
| TP1.5/SL2.5/K1.0 | 1.5bp spread, slip 0.30 | 1831 | 52.5% | 0.826 | 0.844 | -845.0 | -0.461 | -3214 | 3381 | -143 | 28/68 |
| TP1.5/SL1.5/K0.6 | 2.5bp spread, slip 0.60 | 1963 | 44.6% | 0.697 | 0.708 | -1648.9 | -0.840 | -10436 | 11004 | -127 | 22/68 |
| TP2.5/SL2.5/K0.6 | 2.5bp spread, slip 0.60 | 1994 | 45.6% | 0.724 | 0.740 | -1733.1 | -0.869 | -6350 | 6773 | -140 | 20/68 |
| TP1.5/SL2.5/K0.6 | 2.5bp spread, slip 0.60 | 2189 | 50.8% | 0.738 | 0.751 | -1679.4 | -0.767 | -6087 | 6378 | -140 | 21/68 |
| TP1.5/SL1.5/K1.0 | 2.5bp spread, slip 0.60 | 1663 | 44.5% | 0.706 | 0.725 | -1321.1 | -0.794 | -8685 | 8777 | -126 | 22/68 |
| TP2.5/SL2.5/K1.0 | 2.5bp spread, slip 0.60 | 1670 | 45.4% | 0.739 | 0.762 | -1365.6 | -0.818 | -5145 | 5245 | -164 | 22/68 |
| TP1.5/SL2.5/K1.0 | 2.5bp spread, slip 0.60 | 1816 | 50.5% | 0.744 | 0.765 | -1341.8 | -0.739 | -5010 | 5044 | -139 | 24/68 |

### T16. Secondary, default cell by year (MIN_ATR5 = 3.0 pts removes most bars before 2024, when gold's M5 ATR was below 3)

| year | cost | n | win | net_pts | net_usd | pf_usd |
|---|---|---|---|---|---|---|
| 2019 | 1.5bp spread, slip 0.30 | 17 | 76.5% | +35.4 | +207 | 2.474 |
| 2020 | 1.5bp spread, slip 0.30 | 425 | 50.8% | -40.0 | -355 | 0.943 |
| 2021 | 1.5bp spread, slip 0.30 | 154 | 48.7% | -53.8 | -373 | 0.845 |
| 2022 | 1.5bp spread, slip 0.30 | 192 | 47.4% | -51.8 | -348 | 0.876 |
| 2023 | 1.5bp spread, slip 0.30 | 127 | 50.4% | -44.9 | -209 | 0.891 |
| 2024 | 1.5bp spread, slip 0.30 | 488 | 44.1% | -351.5 | -2106 | 0.740 |
| 2025 | 1.5bp spread, slip 0.30 | 581 | 43.9% | -464.3 | -2905 | 0.711 |
| 2019 | 2.5bp spread, slip 0.60 | 18 | 66.7% | +27.7 | +153 | 1.823 |
| 2020 | 2.5bp spread, slip 0.60 | 414 | 48.8% | -191.7 | -1314 | 0.805 |
| 2021 | 2.5bp spread, slip 0.60 | 153 | 47.1% | -89.5 | -611 | 0.764 |
| 2022 | 2.5bp spread, slip 0.60 | 194 | 45.4% | -110.6 | -733 | 0.764 |
| 2023 | 2.5bp spread, slip 0.60 | 127 | 46.5% | -92.6 | -545 | 0.745 |
| 2024 | 2.5bp spread, slip 0.60 | 490 | 42.7% | -488.7 | -3017 | 0.657 |
| 2025 | 2.5bp spread, slip 0.60 | 567 | 41.1% | -703.5 | -4367 | 0.597 |

### T17. Diagnostic, NOT pre-registered and not a pass mark: default cell with the daily brakes switched off (no 3-stop halt, no kill switch), spec base cost, against 100 random-signal controls run the same way. Shows the entry at all hours, since the 3-stop brake confines the pre-registered run to the first hours of the day

| window | entry_hour_utc | n_brakes_on | avg_pts_brakes_on | n_brakes_off | win_off | avg_pts_off | pf_usd_off | ctrl_win | ctrl_avg_pts | ctrl_p05 | ctrl_p95 | real_percentile |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TRAIN | all 01-21 | 1009 | -1.009 | 3098 | 46.5% | -0.494 | 0.815 | 45.5% | -0.818 | -1.117 | -0.536 | 98 |
| TRAIN | 01-07 | 747 | -0.911 | 941 | 44.7% | -0.894 | 0.774 | 45.0% | -0.896 | -1.393 | -0.372 | 53 |
| TRAIN | 07-12 | 106 | -1.618 | 710 | 48.0% | -0.123 | 0.856 | 45.9% | -0.734 | -1.287 | -0.232 | 97 |
| TRAIN | 12-16 | 135 | -0.695 | 812 | 46.4% | -0.507 | 0.827 | 45.9% | -0.787 | -1.440 | -0.118 | 76 |
| TRAIN | 16-21 | 21 | -3.425 | 635 | 47.7% | -0.297 | 0.816 | 45.2% | -0.832 | -1.306 | -0.188 | 91 |
| TEST | all 01-21 | 972 | -0.634 | 3403 | 44.8% | -0.798 | 0.775 | 45.0% | -0.847 | -1.063 | -0.680 | 61 |
| TEST | 01-07 | 879 | -0.546 | 1160 | 45.8% | -0.654 | 0.780 | 45.0% | -0.854 | -1.198 | -0.534 | 85 |
| TEST | 07-12 | 89 | -1.670 | 825 | 44.7% | -0.737 | 0.784 | 45.0% | -0.798 | -1.160 | -0.442 | 58 |
| TEST | 12-16 | 4 | +3.008 | 773 | 44.8% | -1.097 | 0.770 | 45.2% | -0.893 | -1.401 | -0.432 | 22 |
| TEST | 16-21 | 0 |  | 645 | 43.4% | -0.779 | 0.756 | 44.5% | -0.840 | -1.251 | -0.425 | 58 |
