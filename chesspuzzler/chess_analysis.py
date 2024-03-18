#!/usr/bin/env python3

"""Analyze Chess Games stored in pgn format."""

import os
import sys
import logging
import pandas as pd
from chesspuzzler.utils import FileManager
import chess
import chess.pgn
from chess.pgn import ChildNode
import chess.engine
from chess.engine import Cp, Mate, PovScore, InfoDict, SimpleEngine
from chesspuzzler.constants import Constant
import re
from colorama import Fore, Back, Style
from chesspuzzler.model import TrackEval, BestMovePair, BoardInfo

# Create logging folder if it does not exist
os.makedirs("./data/logging", exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
FORMAT = "%(funcName)s:%(levelname)s:%(message)s"
formater = logging.Formatter(FORMAT)
file_handler = logging.FileHandler(os.path.join(".", "data", "logging", "analysis.logging"))
file_handler.setFormatter(formater)
logger.addHandler(file_handler)


class EvaluationEngine:
    def __init__(
        self, node: ChildNode, engine: SimpleEngine,
        info: InfoDict, prevScore: PovScore, turn: int 
    ) -> None:
        self.node = node
        self.engine = engine
        self.info = info
        self.prevScore = prevScore
        self.turn = turn
        self.comment = " "
        self.best_moves = []
       
    def position_eval(self) -> str:
        prev = TrackEval(self.prevScore, self.turn)
        curr = TrackEval(self.info["score"], self.turn)

        logger.info("--"*20)
        logger.info("SCORE DETAILS: ")
        logger.info("Previous Move Scores:\ncp:  {}\nwdl: {}\nmate = {}".format(prev.cp, prev.wdl, prev.mate))
        logger.info("Current Move Scores:\ncp: {}\nwdl: {}\nmate: {}".format(prev.cp, prev.wdl, prev.mate))
        logger.info("--"*20)
        
        self.current = curr
        # We don't expect majority of players to find mate in 30
        # as this would require a time format like classical for this to 
        # be achieved, and yet it's still rare for top masters to spot this 
        # over the board
        mate_limit = Mate(15)
        advantage = curr.wdl > 0.5
        lostAdvantage = not advantage
        mateCreated = prev.mateCreated or curr.mateCreated
        
        if self.node.board().is_checkmate():
            comment = "Game Ended with Checkmate..."
            self.comment = comment
            self.evaluation = "Best Move"
            logger.info(f"Comment: {self.comment}\nJudgement:{self.evaluation}")
            return "Best Move"
        
        if mateCreated:
            logger.debug("Checking Mating conditions")

            if prev.mateCreated and curr.inCheckMate:
                self.comment = "Lost mate and now in Mate..."
                self.evaluation = "Blunder"
                logger.info(f"Comment: {self.comment}\nJudgement:{self.evaluation}")
                return "Blunder"
            
            # Cp(0) < Cp(20) < Cp(400) < Mate(17) < Mate(3) < MateGiven
            elif prev.mateCreated and curr.noMateFound and Mate(prev.mate) > mate_limit and advantage:
                self.comment = "Missed mating chance created but you still have the advantage."
                logger.info(f"Comment: {self.comment}")

                if curr.wdl < prev.wdl:
                    logger.debug("Previous winning chance is greater the your current winning chance.")
                    return self.evaluate(curr.wdl, prev.wdl)
                else:
                    logger.debug("Still winning but let's find the best move")
                    return self.further_analysis()
            
            elif prev.mateCreated and curr.noMateFound and advantage:
                self.comment = "Lost mate but still has the advantage"
                logger.info(f"Comment: {self.comment}")
                if curr.wdl < prev.wdl:
                    return self.evaluate(curr.wdl, prev.wdl)
                else:
                    return self.further_analysis()

            elif prev.mateCreated and curr.noMateFound and lostAdvantage:
                self.comment = "Lost mate and also the advantage..."
                self.evaluation = "Blunder"
                logger.info(f"Comment: {self.comment}\nJudgement:{self.evaluation}")
                return "Blunder"
            
            elif curr.mateCreated and prev.noMateFound:
                self.comment = "Mating sequence created"
                logger.info(f"Comment: {self.comment}")
                return self.further_analysis()
            
            elif curr.mate >= prev.mate and prev.mateCreated and Mate(prev.mate) > mate_limit:
                self.comment = f"Fewer mating moves in {prev.mate} but now {curr.mate}"
                logger.info(f"{self.comment}")
                return self.further_analysis()
            
            elif curr.mate < prev.mate:
                self.comment = "Making precise mating moves."
                logger.info(f"Comment: {self.comment}")
                return self.further_analysis()
            else:
                self.comment = "Check for candidate moves and best move"
                logger.debug(f"{self.comment}")
                self.further_analysis()

        elif curr.wdl < prev.wdl:
            self.comment = "Previous winning chance is greater than current winning chance"
            logger.info(f"Comment: {self.comment}")
            return self.evaluate(curr.wdl, prev.wdl)

        else:
            self.comment = "Check for candidate moves and best move"
            logger.debug(f"{self.comment}")
            return self.further_analysis()
        
    def further_analysis(self):
        return "Good Move"
    
    def evaluate(self, curr_wdl, prev_wdl):
        delta_wdl = prev_wdl - curr_wdl
#         print("delta_wdl", delta_wdl)
        logger.debug("Delta win draw probability: {}".format(delta_wdl))
        if delta_wdl >= 0.3:
            self.comment = self.comment + "Blunder best move is  ."
            logger.info(f"{self.comment}")
            return "Blunder"
        elif delta_wdl >= 0.2:
            self.comment = self.comment + "Mistake best move is  ."
            logger.info(f"{self.comment}")
            return "Mistake"
        elif delta_wdl >= 0.1:
            self.comment = self.comment + "Made an inaccuracy you can consider moves like  ."
            logger.info(f"{self.comment}")
            return "Inaccuracy"
        else:
            self.comment = self.comment + "Check for best moves"
            return self.further_analysis()
        
def split_uci_moves(move: str) -> str:
    # Pattern to split should be a non digit and a digit
    PATTERN = r'(\D\d)'
    
    output = re.split(PATTERN, move)
    # Remove empty string from the output
    output = [s for s in output if s]
    # The uci (universal chess interface) consists of two concatenated string
    # positions the first is the original position of piece on board, 
    # and the second is the move been made on the board.
    
    # Example
    # d2d4 (Queen's opening)
    # d2 is the original position of the pawn
    # d4 is the move been made
    return output[1]

def symbol_uci_move(node):
    move = split_uci_moves(node.move.uci())
    piece_symbol = node.board().piece_at(chess.parse_square(move)).unicode_symbol()
    return f"{piece_symbol} {move}"

class GameAnalysis(FileManager):

    def __init__(self, game) -> None:
        self.game = game
        self.is_game_processed = False

    def game_analysis(self):
        board = chess.Board()
        engine = SimpleEngine.popen_uci(Constant.ENGINE_PATH)
        # The initial score at the begining of the game for WHITE is Cp 20
        prevScore = PovScore(Cp(20), board.turn)
        game_data = []
        column_labels = ["move_number", "move", "side", "fen", "cp", "wdl", "mate", "evaluation"]

        for node in self.game.mainline():
            if not board.is_legal(node.move):
                print(symbol_uci_move(node))
                print("Move {} is illegal".format(symbol_uci_move(node)))
                print(" ".join(map(lambda x: x.uci(), board.generate_pseudo_legal_moves())))
                break
            board.push(node.move)
            board_info = BoardInfo(node)

            info = engine.analyse(board, chess.engine.Limit(depth=Constant.SCAN_ENGINE_DEPTH))
            evaluate = EvaluationEngine(node, engine, info, prevScore, board_info.turn)

            evaluation = evaluate.position_eval()
            # After evaluating the board position update the `prevScore`
            prevScore = info["score"]
            cp, wdl, mate = evaluate.current.cp, evaluate.current.wdl, evaluate.current.mate
            move_info = board_info.get_info() + [cp, wdl, mate, evaluation]
            game_data.append(move_info)

            GameAnalysis.set_node_details(node, prevScore)
        self.game = node.game()
        engine.quit() 
        df = pd.DataFrame(game_data, columns=column_labels)
        print(df.head())    
        return node.game()
    
    @staticmethod
    def set_node_details(node, prevScore):
        if node.eval() and node.eval_depth():
            if node.eval_depth() < Constant.SCAN_ENGINE_DEPTH:
                node.set_eval(prevScore, Constant.SCAN_ENGINE_DEPTH)
            if node.clock():
                node.set_clock(node.clock())
        else:
            node.set_eval(prevScore, Constant.SCAN_ENGINE_DEPTH)
            if node.clock():
                node.set_clock(node.clock())
        return node