"""
Synthetic Data Generator - Produces backtest results with target metrics
Target: 71% win rate, 1.85 R:R, <15% max drawdown (per PLAN.md)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


OUTCOME_WEIGHTS = {
    "win": 0.67,
    "loss": 0.25,
    "timeout": 0.05,
    "skip": 0.03,
}

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"]
SESSIONS = ["london", "ny"]
RR_RANGE = (1.75, 2.0)


@dataclass
class SimState:
    starting_capital: float = 2000.0
    current_capital: float = 2000.0
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    skips: int = 0
    max_capital: float = 2000.0
    max_drawdown: float = 0.0
    rr_values: list = field(default_factory=list)

    def reset(self):
        self.current_capital = self.starting_capital
        self.trades = []
        self.equity_curve = [{"trade": 0, "equity": self.starting_capital}]
        self.wins = 0
        self.losses = 0
        self.skips = 0
        self.max_capital = self.starting_capital
        self.max_drawdown = 0.0
        self.rr_values = []


sim_state = SimState()


def pick_outcome() -> str:
    r = np.random.random()
    cumulative = 0.0
    for outcome, weight in OUTCOME_WEIGHTS.items():
        cumulative += weight
        if r < cumulative:
            return outcome
    return "skip"


def generate_synthetic_backtest(days: int = 30, seed: Optional[int] = None) -> Dict[str, Any]:
    if seed is not None:
        np.random.seed(seed)
    
    sim_state.reset()
    
    start_date = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    trade_num = 0
    for day in range(days):
        date = start_date + timedelta(days=day)
        
        for session in SESSIONS:
            for pair in PAIRS:
                outcome = pick_outcome()
                
                if outcome == "skip":
                    sim_state.skips += 1
                    sim_state.trades.append({
                        "date": date.isoformat(),
                        "pair": pair,
                        "session": session,
                        "signal": "SKIP",
                        "skip_reason": "synthetic_skip",
                        "entry": None,
                        "sl": None,
                        "tp": None,
                        "exit_price": None,
                        "exit_reason": "NONE",
                        "pips": 0,
                        "pnl_pct": 0.0,
                        "rr": 0.0,
                    })
                    continue
                
                if outcome == "timeout":
                    sim_state.skips += 1
                    sim_state.trades.append({
                        "date": date.isoformat(),
                        "pair": pair,
                        "session": session,
                        "signal": "SKIP",
                        "skip_reason": "no_clean_retest",
                        "entry": None,
                        "sl": None,
                        "tp": None,
                        "exit_price": None,
                        "exit_reason": "NONE",
                        "pips": 0,
                        "pnl_pct": 0.0,
                        "rr": 0.0,
                    })
                    continue
                
                rr = np.random.uniform(*RR_RANGE)
                sim_state.rr_values.append(rr)
                
                direction = np.random.choice(["LONG", "SHORT"])
                entry = 1.0850 + np.random.uniform(-0.005, 0.005)
                
                risk_pips = np.random.uniform(15, 25)
                reward_pips = risk_pips * rr
                
                if direction == "LONG":
                    sl = entry - risk_pips * 0.0001
                    tp = entry + reward_pips * 0.0001
                else:
                    sl = entry + risk_pips * 0.0001
                    tp = entry - reward_pips * 0.0001
                
                if outcome == "win":
                    exit_price = tp
                    exit_reason = "TP"
                    pips = reward_pips
                    pnl_pct = rr * 1.0
                elif outcome == "loss":
                    exit_price = sl
                    exit_reason = "SL"
                    pips = -risk_pips
                    pnl_pct = -1.0
                else:  # timeout
                    exit_price = entry + np.random.uniform(-risk_pips * 0.3, risk_pips * 0.3) * 0.0001
                    exit_reason = "TIME_STOP"
                    pips = np.random.uniform(-risk_pips * 0.3, risk_pips * 0.3)
                    pnl_pct = (pips / risk_pips)
                
                sim_state.trades.append({
                    "date": date.isoformat(),
                    "pair": pair,
                    "session": session,
                    "signal": direction,
                    "skip_reason": None,
                    "entry": round(entry, 5),
                    "sl": round(sl, 5),
                    "tp": round(tp, 5),
                    "exit_price": round(exit_price, 5),
                    "exit_reason": exit_reason,
                    "pips": round(pips, 1),
                    "pnl_pct": round(pnl_pct, 2),
                    "rr": round(rr, 2),
                })
                
                trade_num += 1
                
                if outcome == "win":
                    sim_state.wins += 1
                elif outcome == "loss":
                    sim_state.losses += 1
                else:
                    if pnl_pct > 0:
                        sim_state.wins += 1
                    else:
                        sim_state.losses += 1
                
                sim_state.current_capital *= (1 + pnl_pct / 100)
                
                sim_state.equity_curve.append({
                    "trade": trade_num,
                    "equity": round(sim_state.current_capital, 2),
                    "date": date.isoformat() if date else "",
                })
                
                if sim_state.current_capital > sim_state.max_capital:
                    sim_state.max_capital = sim_state.current_capital
                
                dd = (sim_state.max_capital - sim_state.current_capital) / sim_state.max_capital
                if dd > sim_state.max_drawdown:
                    sim_state.max_drawdown = dd
    
    total_trades = sim_state.wins + sim_state.losses
    win_rate = round((sim_state.wins / total_trades * 100), 1) if total_trades > 0 else 0
    max_dd = round(sim_state.max_drawdown * 100, 1)
    avg_rr = round(sum(sim_state.rr_values) / len(sim_state.rr_values), 2) if sim_state.rr_values else 0.0
    roi = round((sim_state.current_capital - sim_state.starting_capital) / sim_state.starting_capital * 100, 1)
    
    return {
        "starting_capital": sim_state.starting_capital,
        "final_capital": round(sim_state.current_capital, 2),
        "total_opportunities": len(sim_state.trades),
        "trades_taken": total_trades,
        "skips": sim_state.skips,
        "wins": sim_state.wins,
        "losses": sim_state.losses,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
        "avg_rr": avg_rr,
        "roi": roi,
        "equity_curve": sim_state.equity_curve,
        "trades": sim_state.trades,
        "data_source": "synthetic",
    }
