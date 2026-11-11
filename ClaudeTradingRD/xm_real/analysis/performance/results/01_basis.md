## Basis: XM GOLD fill minus OANDA XAU_USD quote on the same side (points = USD/oz)

market (MOBILE, non close-by) deals: 271; calm-bar subset used (S5 ask range <= 1.0): 211

| side | n | median | mean | sd | p10 | p90 |
|---|---|---|---|---|---|---|
| ask (BUY deals) | 101.000 | 0.069 | 0.048 | 0.188 | -0.186 | 0.293 |
| bid (SELL deals) | 110.000 | -0.042 | -0.036 | 0.195 | -0.245 | 0.192 |

bootstrap 95% CI of the medians: {"ask (BUY deals)": [0.0016399999999521242, 0.09673599999950966], "bid (SELL deals)": [-0.06946500000003653, -0.014975999999478518]}

### by day
| day | side | n | median | sd |
|---|---|---|---|---|
| 11-04 | ask (BUY deals) | 9.000 | 0.104 | 0.150 |
| 11-04 | bid (SELL deals) | 16.000 | -0.040 | 0.161 |
| 11-05 | ask (BUY deals) | 16.000 | 0.053 | 0.179 |
| 11-05 | bid (SELL deals) | 22.000 | -0.050 | 0.272 |
| 11-06 | ask (BUY deals) | 11.000 | 0.083 | 0.164 |
| 11-06 | bid (SELL deals) | 18.000 | 0.062 | 0.131 |
| 11-09 | ask (BUY deals) | 21.000 | 0.247 | 0.146 |
| 11-09 | bid (SELL deals) | 26.000 | -0.049 | 0.199 |
| 11-10 | ask (BUY deals) | 22.000 | 0.034 | 0.255 |
| 11-10 | bid (SELL deals) | 14.000 | -0.136 | 0.102 |
| 11-11 | ask (BUY deals) | 22.000 | -0.090 | 0.100 |
| 11-11 | bid (SELL deals) | 14.000 | -0.055 | 0.147 |

### all deal kinds (not used for the estimate; TP/SO in news bars are interpolation artefacts)
| reason | entryType | side | n | median | mean | sd |
|---|---|---|---|---|---|---|
| DEAL_REASON_MOBILE | DEAL_ENTRY_IN | ask (BUY deals) | 74.000 | -0.002 | 0.021 | 0.257 |
| DEAL_REASON_MOBILE | DEAL_ENTRY_IN | bid (SELL deals) | 104.000 | -0.033 | -0.037 | 0.305 |
| DEAL_REASON_MOBILE | DEAL_ENTRY_OUT | ask (BUY deals) | 55.000 | 0.097 | 0.075 | 0.183 |
| DEAL_REASON_MOBILE | DEAL_ENTRY_OUT | bid (SELL deals) | 39.000 | -0.090 | -0.028 | 0.222 |
| DEAL_REASON_MOBILE | DEAL_ENTRY_OUT_BY | ask (BUY deals) | 4.000 | 8.752 | 8.677 | 0.908 |
| DEAL_REASON_MOBILE | DEAL_ENTRY_OUT_BY | bid (SELL deals) | 4.000 | -6.556 | -6.435 | 0.999 |
| DEAL_REASON_SO | DEAL_ENTRY_OUT | ask (BUY deals) | 15.000 | -0.071 | -0.103 | 0.551 |
| DEAL_REASON_SO | DEAL_ENTRY_OUT | bid (SELL deals) | 19.000 | -0.802 | -4.418 | 8.658 |
| DEAL_REASON_TP | DEAL_ENTRY_OUT | ask (BUY deals) | 30.000 | -0.119 | -0.941 | 2.264 |
| DEAL_REASON_TP | DEAL_ENTRY_OUT | bid (SELL deals) | 12.000 | 0.223 | 0.313 | 0.265 |

result: {"bid": -0.042, "ask": 0.069, "mid": 0.014, "xm_minus_oanda_spread": 0.111, "oanda_spread_median_at_deals": 0.48, "n_bid": 110, "n_ask": 101, "ci95_bid": [-0.069, -0.015], "ci95_ask": [0.002, 0.097], "n_market_deals": 271, "n_calm": 211}