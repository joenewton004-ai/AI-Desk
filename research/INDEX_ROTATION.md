# Index rotation: should the 30% SPY sleeve compare other indices?

_October 2026. Code: `IndexRotation` in `ai_desk/portfolio/methods.py`. Tables:
[`output/index_rotation.md`](output/index_rotation.md) from
`python research/index_rotation.py`. Educational research, not financial advice._

## The idea

The live sleeve holds SPY while its 12-month return is positive, otherwise
cash. The alternative compares six major indices every month, holds the
strongest one (or two, or three), and still steps into cash when the leaders'
own 12-month return turns negative. This is often called "dual momentum".

| fund | index |
|---|---|
| SPY | S&P 500 |
| QQQ | Nasdaq-100 |
| IWM | Russell 2000 (small caps) |
| DIA | Dow Jones Industrials |
| EFA | Developed markets outside the US |
| EEM | Emerging markets |

The test runs from June 2004 (the first month all six have a year of history)
to October 2026. Fills are at the next open, with 3bps costs; cash earns
T-bills, and Sharpe is measured above them.

## Results

| | Return/yr | Volatility | Sharpe | Worst drop |
|---|---|---|---|---|
| **Live sleeve: SPY + 12-month switch** | 9.4% | 14% | 0.58 | −34% |
| Rotation, all 6, top 1 | 12.0% | 21% | 0.56 | −29% |
| Rotation, all 6, top 2 | 11.6% | 18% | 0.60 | −31% |
| Rotation, US only, top 2 | 10.8% | 17% | 0.60 | −31% |
| Rotation without QQQ, top 2 | 8.9% | 17% | 0.48 | −38% |
| SPY buy & hold | 11.0% | 19% | 0.56 | −55% |

At first glance rotation earns 2-3% a year more. Look closer and the case falls apart:

1. **Same return per unit of risk.** Its Sharpe is 0.56-0.60, against 0.58 for
   the live sleeve. The extra return comes from taking more risk (volatility
   18-21% vs 14%), not from a better signal.
2. **All the gain is from one era.** In 2004-2012, emerging markets boomed and
   rotation made 13%/yr against 6% for the live sleeve. In 2013-2019 it
   *lagged*: 9% against 12%. In 2020-2026 it was about level.
3. **It leans on QQQ.** Remove QQQ and top-2 rotation drops to 8.9%/yr with
   a −38% worst drop. Top-1 rotation held QQQ in 38% of months. We know
   with hindsight that the Nasdaq was the place to be. That's the same bias
   noted in `FINDINGS.md` §6.
4. **It's fragile to the lookback.** With 6- or 9-month returns instead of
   12-month, every variant falls to 8-10%/yr with a Sharpe of 0.44-0.50,
   below the live sleeve. A real edge shouldn't vanish when one setting moves a little.
5. **Walk-forward fails.** Each January from 2010, it picked the best setting
   using only past data and traded it for the year. That earned 8.3%/yr (Sharpe 0.45), against the live
   sleeve's 10.2% (0.61) over the same years. This is the honest
   out-of-sample test, and rotation lost.
6. **It doesn't help the desk.** Swapping it into the 50/20/30 desk
   (2014-2026) gives 16.2-16.7%/yr with a Sharpe of 0.86, against 16.3% and 0.89
   with the live sleeve. Rotation correlates just as much with the quality
   screen (0.71-0.77), so it adds no diversification.

It also trades far more: 140-200 trades against 17 over 22 years, with
the top-1 version switching holdings 76 times. Costs at 3x barely change the
results, so costs aren't the problem. The signal is.

## Verdict

**Keep the SPY sleeve.** Rotation is not a better crash-insurance sleeve.
It takes more risk for the same reward, and its out-of-sample
test was worse. The live sleeve's job in the desk is to be the steady, low-turnover
part next to two concentrated stock sleeves, and plain SPY does that job
better.

Not tested and worth knowing: data before 2003 (the international funds
didn't exist), other universes (bonds and gold were tested in
`FINDINGS.md` §6, with the same conclusion), and blends of 3-, 6- and 12-month returns
across these six indices.
