"""Improved Pine Script generator.

Functions:
- generate_pine(feature_weights, as_strategy=False): returns Pine Script v5 source string.
- to_pine_simple_combination kept for backward compatibility (calls generate_pine).

The generated script includes inputs for smoothing and normalization, creates
per-feature expressions, normalizes them with a rolling z-score, combines them
with weights, and emits a plotted combo plus optional buy/sell signals when used
as a strategy.
"""

from typing import List, Tuple


def _feature_mapping(name: str, norm_len_var: str = 'norm_len') -> str:
    """Return a Pine expression (string) for a known feature name.
    The returned expression should be a valid Pine v5 expression using `close` and `volume`.
    """
    m = {
        'SMA_20': "ta.sma(close, 20)",
        'EMA_20': "ta.ema(close, 20)",
        'EMA_50': "ta.ema(close, 50)",
        'RSI_14': "ta.rsi(close, 14)",
        'ROC_10': "ta.roc(close, 10)",
        # MACD handled specially in generate_pine (destructured)
        'MACD': None,
        'MACD_SIG': None,
        'MACD_HIST': None,
        'BBM_20': "ta.bb(close, 20, 2).middle",
        'BBU_20': "ta.bb(close, 20, 2).upper",
        'BBL_20': "ta.bb(close, 20, 2).lower",
        'ATR_14': "ta.atr(14)",
        # OBV handled specially in generate_pine (cumulative implementation)
        'OBV': None,
        # ADX handled via ta.dmi destructuring in generate_pine
        'ADX_14': None,
        'CCI_20': "ta.cci(20)",
        'VWAP': "ta.vwap(hlc3)",
    }
    return m.get(name, None)


def generate_pine(feature_weights: List[Tuple[str, float]], title: str = 'Auto Combo', as_strategy: bool = False, overlay: bool = False) -> str:
    """Generate a Pine Script v5 source combining features.

    - `feature_weights` is a list of (feature_name, weight).
    - `as_strategy` when True will emit `strategy()` and simple entries/exits.
    """
    header = ["// Generated Pine Script v6", "//@version=6"]
    header.append(("strategy('{}', overlay={})".format(title, str(overlay).lower()) if as_strategy
                   else "indicator('{}', overlay={})".format(title, str(overlay).lower())))

    # Inputs
    inputs = [
        "norm_len = input.int(20, 'Normalization Length', minval=1)",
        "smooth_len = input.int(3, 'Combo Smooth Length', minval=1)",
        "threshold = input.float(0.0, 'Signal Threshold', step=0.0001)",
        "show_signals = input.bool(true, 'Show Buy/Sell Signals')",
    ]

    lines = header + inputs + ["\n// Per-feature calculations"]

    used = []
    # If any MACD-related features are requested, destructure ta.macd into variables
    macd_needed = any(name in ('MACD', 'MACD_SIG', 'MACD_HIST') for name, _ in feature_weights)
    if macd_needed:
        # Use destructuring to match v6 style: [MACD, _, _] = ta.macd(...)
        lines.append("[MACD, _, _] = ta.macd(close, 12, 26, 9)")

    # If ADX is requested, destructure ta.dmi to obtain ADX_14 before per-feature processing
    adx_needed = any(name == 'ADX_14' for name, _ in feature_weights)
    if adx_needed:
        # ta.dmi(length, smoothing) returns [pdi, mdi, adx]
        adx_line = "[_, _, ADX_14] = ta.dmi(14, 14)"
        if adx_line not in lines:
            lines.append(adx_line)
    for name, weight in feature_weights:
        # Determine expression or special handling for known features
        if name == 'MACD':
            expr = 'MACD'
        elif name == 'MACD_SIG':
            expr = 'MACD_SIG'
        elif name == 'MACD_HIST':
            expr = 'MACD_HIST'
        elif name == 'OBV':
            # special-case OBV: implement cumulative OBV in Pine before normalization
            # use `var float obv = 0` and `obv := obv[1] + ...` as per v6 idiom
            lines.append("var float obv = 0")
            lines.append("obv := obv[1] + (close > close[1] ? volume : close < close[1] ? -volume : 0)")
            expr = 'obv'
        elif name == 'ADX_14':
            expr = 'ADX_14'
        else:
            expr = _feature_mapping(name)

        if expr is None:
            continue

        # safe variable name
        var = name.replace('-', '_')
        # avoid redundant self-assignment (e.g., MACD = MACD)
        if expr != var:
            lines.append(f"{var} = {expr}")
        # normalization: rolling z-score
        lines.append(f"{var}_m = ta.sma({var}, norm_len)")
        lines.append(f"{var}_s = ta.stdev({var}, norm_len)")
        lines.append(f"{var}_z = {var}_s == 0 ? 0 : ({var} - {var}_m) / {var}_s")
        used.append((var, weight))

    # ADX handling: if ADX requested, destructure via ta.dmi
    adx_needed = any(name == 'ADX_14' for name, _ in feature_weights)
    if adx_needed:
        # ta.dmi(length, smoothing) returns [pdi, mdi, adx]
        lines.append("[_, _, ADX_14] = ta.dmi(14, 14)")

    if not used:
        lines.append("// No known features provided - nothing to plot")
        return '\n'.join(lines)

    lines.append('\n// Combine normalized features using provided weights')
    combo_terms = []
    for var, weight in used:
        combo_terms.append(f"({weight:.6f}) * {var}_z")
    combo_expr = ' + '.join(combo_terms)
    lines.append(f"combo_raw = {combo_expr}")
    lines.append("combo = ta.ema(combo_raw, smooth_len)")
    lines.append("plot(combo, title='Combo', color=color.blue)")

    lines.append("// Optional threshold and signals")
    lines.append("plot(threshold, title='Threshold', color=color.gray, linewidth=1)")
    lines.append("signal_long = combo > threshold")
    lines.append("signal_short = combo < -threshold")
    lines.append("plotshape(show_signals and signal_long, title='Long', location=location.belowbar, color=color.green, style=shape.triangleup, size=size.small)")
    lines.append("plotshape(show_signals and signal_short, title='Short', location=location.abovebar, color=color.red, style=shape.triangledown, size=size.small)")

    if as_strategy:
        # Simple entries and exits with optional stop/limit inputs (placeholders)
        lines.append("stop_pct = input.float(1.0, 'Stop %', step=0.1) / 100.0")
        lines.append("take_pct = input.float(2.0, 'Take Profit %', step=0.1) / 100.0")
        lines.append("if show_signals and signal_long\n    strategy.entry('Long', strategy.long)\n    // optional: strategy.exit('Exit Long', 'Long', stop=close*(1-stop_pct), limit=close*(1+take_pct))")
        lines.append("if show_signals and signal_short\n    strategy.entry('Short', strategy.short)\n    // optional: strategy.exit('Exit Short', 'Short', stop=close*(1+stop_pct), limit=close*(1-take_pct))")

    lines.append("\n// End of generated script")
    return '\n'.join(lines)


def to_pine_simple_combination(feature_weights):
    # Backwards-compatible helper that returns the improved script
    return generate_pine(feature_weights, as_strategy=False)

