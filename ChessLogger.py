import json
import time
import os

class ChessLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.current_game_id = int(time.time())
        self.log_file = os.path.join(log_dir, f"game_{self.current_game_id}.json")
        self.data = {
            "game_id": self.current_game_id,
            "moves": [],
            "stats": {
                "total_ai_requests": 0,
                "illegal_moves": 0,
                "legal_moves": 0,
                "illegal_move_rate": 0.0,
                "total_good_moves": 0,
                "total_mistakes": 0,
                "total_blunders": 0
            },
            "agent /model": None,
            "prompt / persona": None
        }
        self._save()

    def set_persona(self, name, prompt):
        """Sets the persona name and prompt for the game (logged only once)."""
        if self.data["prompt / persona"] is None:
            self.data["agent /model"] = name
            self.data["prompt / persona"] = prompt
            self._save()

    def log_move_attempt(self, agent_name, raw_response, parsed_move, is_legal, best_move=None, best_score=None, ai_score=None, score_diff=None):
        """
        Logs a single move attempt by an AI agent.
        """
        # Only update stats if it's a real AI attempt (not human, not fallback)
        if agent_name not in ["Human", "Engine (Fallback)"]:
            self.data["stats"]["total_ai_requests"] += 1
            if is_legal:
                self.data["stats"]["legal_moves"] += 1
            else:
                self.data["stats"]["illegal_moves"] += 1

            # Calculate rate
            if self.data["stats"]["total_ai_requests"] > 0:
                rate = self.data["stats"]["illegal_moves"] / self.data["stats"]["total_ai_requests"]
                self.data["stats"]["illegal_move_rate"] = round(rate, 4)

        # Determine move quality
        quality = self.classify_move(score_diff) if score_diff is not None else "N/A"
        
        # Increment quality counters
        if quality == "Best/Good":
            self.data["stats"]["total_good_moves"] += 1
        elif quality == "Mistake":
            self.data["stats"]["total_mistakes"] += 1
        elif quality == "Blunder":
            self.data["stats"]["total_blunders"] += 1

        entry = {
            "timestamp": time.time(),
            "agent": agent_name,
            "raw_response": str(raw_response),
            "parsed_move": parsed_move,
            "is_legal": is_legal,
            "current_illegal_rate": self.data["stats"]["illegal_move_rate"],
            "ai_score": ai_score,
            "best_score": best_score,
            "best_move": best_move,
            "score_diff": score_diff,
            "move_quality": quality
        }
        self.data["moves"].append(entry)
        self._save()

    def classify_move(self, score_diff):
        """
        Classifies the move based on user-defined thresholds.
        """
        if score_diff < 0: 
            return "Brilliant" 
        if score_diff <= 2:
            return "Best/Good"
        elif score_diff <= 8:
            return "Mistake" 
        else:
            return "Blunder"

    def _save(self):
        if os.environ.get("CHESS_NO_LOG") == "1":
            return
        with open(self.log_file, "w") as f:
            json.dump(self.data, f, indent=4)
