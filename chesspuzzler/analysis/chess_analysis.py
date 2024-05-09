#!/usr/bin/env python3

"""Analyze Chess Games stored in pgn format."""

import os
import copy
import sys
import logging
import pandas as pd
from chesspuzzler.analysis.file_util import FileManager
import chess
import chess.pgn
from chess.pgn import ChildNode
import chess.engine
from chess.engine import Cp, Mate, PovScore, InfoDict, SimpleEngine
from chesspuzzler.analysis.constants import Constant
from chesspuzzler.analysis.board_util import symbol_uci_move
from colorama import Fore, Back, Style
from chesspuzzler.analysis.model import TrackEval, BestMovePair, BoardInfo
from chesspuzzler.analysis.logger import configure_log

# Create logging folder if it does not exist
os.makedirs("./data/logging", exist_ok=True)
logger = configure_log(__name__, "analysis.log")
board_logger = configure_log("board", "evaluation.log", view_on_console=True)


class EvaluationEngine:
    def __init__(
        self, node: ChildNode, engine: SimpleEngine,
        info: InfoDict, prevScore: PovScore, 
        prevpovScore: PovScore, turn: int 
    ) -> None:
        self.node = node
        self.engine = engine
        self.info = info
        self.prevScore = prevScore
        self.prevpovScore = prevpovScore
        self.turn = turn
        self.comment = " "
        self.best_moves = []
       
    def position_eval(self) -> str:
        prev = TrackEval(self.prevScore, self.turn)
        prevoppScore = TrackEval(self.prevScore, not self.turn)
        prevpovScore = TrackEval(self.prevpovScore, self.turn)

        try:
            curr = TrackEval(self.info["score"], self.turn)
        except TypeError:
            curr = TrackEval(self.info, self.turn)

        logger.info("--"*20)
        logger.info("SCORE DETAILS: ")
        logger.info("TURN: {}".format("White" if self.turn else "Black"))
        logger.info("Full move number: {}\t Half move number: {}".format(self.node.board().fullmove_number,self.node.ply()))
        logger.info("INDEX\t\t\tCP\tWDL\tMATE\t")
        logger.info("Previous POV score     {}\t{}\t{}".format(prevpovScore.cp, prevpovScore.wdl, prevpovScore.mate))
        logger.info("Previous Move Scores   {}\t{}\t{}".format(prev.cp, prev.wdl, prev.mate))
        logger.info("Current Move Scores    {}\t{}\t{}".format(curr.cp, curr.wdl, curr.mate))

        
        self.current = curr
        # We don't expect majority of players to find mate in 30
        # as this would require a time format like classical for this to 
        # be achieved, and yet it's still rare for top masters to spot this 
        # over the board
        mate_limit = Mate(15)
        advantage = curr.wdl > 0.5
        lostAdvantage = not advantage
        mateSequence = prev.mateCreated or curr.mateCreated
        
        if self.node.board().is_checkmate():
            comment = "Game Ended with Checkmate..."
            self.comment = comment
            self.evaluation = "Best Move"
            logger.info(f"Comment: {self.comment}\nJudgement:{self.evaluation}")
            return "Best Move"
        
        if mateSequence:
            logger.debug("Checking Mating conditions")

            if prev.mateCreated and curr.inCheckMate:
                self.comment = "Lost mate and now in Mate..."
                self.evaluation = "Blunder"
                logger.info(f"Comment: {self.comment}\nJudgement:{self.evaluation}")
                return "Blunder"        
            
            elif prev.mateCreated and curr.noMateFound:
                if curr.cp > 999: return "Inaccuracy"
                elif curr.cp > 700: return "Mistake"
                else: return "Blunder" 
        
            
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

            elif curr.mate >= prev.mate and prev.mateCreated:
                self.comment = f"Fewer mating moves in {prev.mate} but now {curr.mate}"
                logger.info(f"{self.comment}")
                return self.further_analysis()
            
            elif curr.mate < prev.mate and curr.mateCreated and prev.mateCreated:
                self.comment = "Making precise mating moves."
                logger.info(f"Comment: {self.comment}")
                return self.further_analysis()
            
            else:
                self.comment = "Check for candidate moves and best move"
                logger.debug(f"{self.comment}")
                self.further_analysis()

        elif prev.noMateFound and curr.inCheckMate:
            if prev.cp < -999: return "Inaccuracy"
            elif prev.cp < -700: return "Mistake"
            else: return "Blunder"

        # elif 0.3 > (1 - curr.wdl - prevoppScore.wdl) >= 0.05 and curr.wdl >= prevpovScore.wdl:
        elif (1 - curr.wdl - prevoppScore.wdl) >= 0:
            delta_wdl = 1 - curr.wdl - prevoppScore.wdl
            return self.evaluate(delta_wdl)

        # elif curr.wdl < prev.wdl:
        #     self.comment = "Previous winning chance is greater than current winning chance"
        #     logger.info(f"Comment: {self.comment}")
        #     delta_wdl = prevpovScore.wdl - curr.wdl
        #     return self.evaluate(delta_wdl)

        else:
            self.comment = "Check for candidate moves and best move"
            logger.debug(f"{self.comment}")
            return self.further_analysis()
        
    def further_analysis(self):
        return "Good Move"
    
    def evaluate(self, delta_wdl):
        logger.debug("Delta win draw probability: {}".format(delta_wdl))
        if delta_wdl >= 0.2:
            self.comment = self.comment + "Blunder best move is  ."
            logger.info(f"{self.comment}")
            return "Blunder"
        elif delta_wdl >= 0.1:
            self.comment = self.comment + "Mistake best move is  ."
            logger.info(f"{self.comment}")
            return "Mistake"
        elif delta_wdl >= 0.05:
            self.comment = self.comment + "Made an inaccuracy you can consider moves like  ."
            logger.info(f"{self.comment}")
            return "Inaccuracy"
        else:
            self.comment = self.comment + "Check for best moves"
            return self.further_analysis()


class GameAnalysis(FileManager):

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.is_game_processed = False

    def game_analysis(self):
        from chesspuzzler.analysis.logger import log_board
        board = chess.Board()
        engine = SimpleEngine.popen_uci(Constant.ENGINE_PATH)
        # The initial score at the begining of the game for WHITE is Cp 20
        prevScore = PovScore(Cp(20), board.turn)
        prevpovScore = prevScore

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
            if node.eval():
                info = node.eval()
            else:
                info = engine.analyse(board, chess.engine.Limit(depth=Constant.SCAN_ENGINE_DEPTH))
                GameAnalysis.set_node_details(node, info["score"])

            evaluate = EvaluationEngine(node, engine, info, prevScore, prevpovScore, board_info.turn)
            evaluation = evaluate.position_eval()
    
            # After evaluating the board position update the `prevScore`
            prevpovScore = prevScore
            try:
                prevScore = info["score"]
            except TypeError:
                prevScore = info
            cp, wdl, mate = evaluate.current.cp, evaluate.current.wdl, evaluate.current.mate
            move_info = board_info.get_info() + [cp, wdl, mate, evaluation]
            board_logger.info(log_board(board_info, node, prevScore.pov(node.turn), evaluation))
            logger.debug("--"*20)
            game_data.append(move_info)


        df = pd.DataFrame(game_data, columns=column_labels)
        print(df.groupby(["side", "evaluation"])["move_number"].count())
        self.update_game(node.game(), node.game().headers.get("Site"))
        self.save_dataframe(df, node.game().headers.get("Site"))  
        engine.quit()
        self.is_game_processed = True 
        return node.game()
    
    @staticmethod
    def set_node_details(node: ChildNode, povscore: PovScore) -> ChildNode:
        """
        Sets node comment with evaluation and engine depth.
        """
        if node.eval() and node.eval_depth():
            if node.eval_depth() < Constant.SCAN_ENGINE_DEPTH:
                node.set_eval(povscore, Constant.SCAN_ENGINE_DEPTH)
            if node.clock():
                node.set_clock(node.clock())
        else:
            node.set_eval(povscore, Constant.SCAN_ENGINE_DEPTH)
            if node.clock():
                node.set_clock(node.clock())
        return node
