"""
FastAPI Server - Dashboard API + WebSocket streaming
"""

import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backtest import run_backtest, get_status
from mode_b import STRATEGY_PRESETS

app = FastAPI(title="Openclaw Mode B")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"name": "Openclaw Mode B", "status": "running"}


@app.get("/status")
def status():
    return get_status()


@app.post("/reset")
def reset():
    return {"status": "reset", "capital": 2000.0}


@app.get("/strategies")
def list_strategies():
    return {
        name: {
            "label": cfg["label"],
            "description": cfg["description"],
        }
        for name, cfg in STRATEGY_PRESETS.items()
    }


@app.get("/backtest")
def backtest(period_days: int = 0, strategy: str = "base", starting_capital: float = 2000.0, risk_pct: float = 0.01):
    if strategy not in STRATEGY_PRESETS:
        return {"error": f"Unknown strategy: {strategy}. Available: {list(STRATEGY_PRESETS.keys())}"}
    result = run_backtest(period_days, strategy, starting_capital, risk_pct)
    return result


@app.websocket("/ws/backtest/stream")
async def backtest_stream(websocket: WebSocket):
    await websocket.accept()
    
    try:
        msg = await websocket.receive_json()
        period_days = msg.get("period_days", 0)
        strategy = msg.get("strategy", "base")
        starting_capital = msg.get("starting_capital", 2000.0)
        risk_pct = msg.get("risk_pct", 0.01)
        
        if strategy not in STRATEGY_PRESETS:
            await websocket.send_json({"type": "error", "message": f"Unknown strategy: {strategy}"})
            return
        
        await websocket.send_json({
            "type": "start",
            "starting_capital": starting_capital,
            "strategy": strategy,
            "strategy_label": STRATEGY_PRESETS[strategy]["label"],
        })
        
        result = run_backtest(period_days, strategy, starting_capital, risk_pct)
        
        for i, trade in enumerate(result["trades"]):
            trade_data = {
                "type": "trade",
                "index": i + 1,
                "total": len(result["trades"]),
                **trade
            }
            await websocket.send_json(trade_data)
            await asyncio.sleep(0.4)
        
        summary = {
            "type": "complete",
            "starting_capital": result["starting_capital"],
            "final_capital": result["final_capital"],
            "total_opportunities": result["total_opportunities"],
            "trades_taken": result["trades_taken"],
            "skips": result["skips"],
            "wins": result["wins"],
            "losses": result["losses"],
            "win_rate": result["win_rate"],
            "max_drawdown": result["max_drawdown"],
            "roi": result["roi"],
            "equity_curve": result["equity_curve"],
        }
        await websocket.send_json(summary)
        
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
