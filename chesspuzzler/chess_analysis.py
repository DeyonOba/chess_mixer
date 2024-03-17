#!/usr/bin/env python3

"""Analyze Chess Games stored in pgn format."""

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
from chesspuzzler.model import TrackEval, BestMovePair, Continuation

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
       
    def position_eval(self) -> str:
        prev = TrackEval(self.prevScore, self.turn)
        curr = TrackEval(self.info["score"], self.turn)
        # print("POV Scores::....")
        # print("prev: wdl", prev.wdl)
        # print("Function wdl: prev", prev.win_chances())
        # print("Function wdl: prev", prev.wdl_score())
        # print("prev: cp", prev.cp)
        # print("prev: mate", prev.mate)
        # print("curr: wdl", curr.wdl)
        # print("Function wdl: curr", curr.win_chances())
        # print("Function wdl: curr", curr.wdl_score())
        # print("curr: cp", curr.cp)
        # print("curr: mate", curr.mate)
        self.current = curr
        # We don't expect majority of players to find mate in 30
        # as this would require a time format like classical for this to 
        # be achieved, and yet it's still rare for top masters to spot this 
        # over the board
        mate_limit = Mate(15)
        advantage = curr.wdl > 0.5
        lostAdvantage = not advantage
        mateCreated = prev.mateCreated or curr.mateCreated
        
#         print("Is mateCreated: ", mateCreated)
        if self.node.board().is_checkmate():
#             print("Game Ended with Checkmate...")
            return "Best Move"
        
        if mateCreated:
            print("Checking Mating conditions")
            if prev.mateCreated and curr.inCheckMate:
                print("Lost mate and now in Mate")
                return "Blunder"
            
            # Cp(0) < Cp(20) < Cp(400) < Mate(17) < Mate(3) < MateGiven
            elif prev.mateCreated and curr.noMateFound and Mate(prev.mate) > mate_limit and advantage:
                print("Missed mating chance created by opponent.")
                if curr.wdl < prev.wdl:
                    return self.evaluate(curr.wdl, prev.wdl)
                else:
                    return self.further_analysis()
            
            elif prev.mateCreated and curr.noMateFound and advantage:
                print("Lost mate but still has the advantage...")
                if curr.wdl < prev.wdl:
                    return self.evaluate(curr.wdl, prev.wdl)
                else:
                    return self.further_analysis()

            elif prev.mateCreated and curr.noMateFound and lostAdvantage:
                print("Lost mate and also the advantage...")
                return "Blunder"
            
            elif curr.mateCreated and prev.noMateFound:
                print("Mating sequence created....")
                return self.further_analysis()
            
            elif curr.mate >= prev.mate and prev.mateCreated and Mate(prev.mate) > mate_limit:
                print(f"Fewer mating moves in {prev.mate} but now {curr.mate}")
                return self.further_analysis()
            
            elif curr.mate < prev.mate:
                print("Making precise mating moves...")
                return self.further_analysis()
            else:
                self.further_analysis()

        elif curr.wdl < prev.wdl:
            print("previous wdl is greater than current")
            return self.evaluate(curr.wdl, prev.wdl)

        else:
            print("**Evaluating ....")
            return self.further_analysis()
        
    def further_analysis(self):
        return "Good Move"
    
    def evaluate(self, curr_wdl, prev_wdl):
        delta_wdl = prev_wdl - curr_wdl
#         print("delta_wdl", delta_wdl)
        if delta_wdl >= 0.3:
            return "Blunder"
        elif delta_wdl >= 0.2:
            return "Mistake"
        elif delta_wdl >= 0.1:
            return "Inaccuracy"
        else:
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

    def game_analysis(self):
        board = chess.Board()
        engine = SimpleEngine.popen_uci(Constant.ENGINE_PATH)
        # The initial score at the begining of the game for WHITE is Cp 20
        prevScore = PovScore(Cp(20), board.turn)
        game_data = []
        column_labels = ["move_number", "side", "move", "fen", "cp", "wdl", "mate", "evaluation"]

        for node in self.game.mainline():
            side = "White" if board.turn else "Black"
            turn = board.turn
            move_info = [node.ply()]
            if not board.is_legal(node.move):
                print(symbol_uci_move(node))
                print("Move {} is illegal".format(symbol_uci_move(node)))
                print(" ".join(map(lambda x: x.uci(), board.generate_pseudo_legal_moves())))
                break
            board.push(node.move)
            fen = board.fen()    
            # print(board.unicode())  
            # display(board) 
            info = engine.analyse(board, chess.engine.Limit(depth=Constant.SCAN_ENGINE_DEPTH))
            evaluate = EvaluationEngine(node, engine, info, prevScore, turn)
            move_unicode_symbol = symbol_uci_move(node)
    #         print(symbol_uci_move(node))
            evaluation = evaluate.position_eval()
            # After evaluating the board position update the `prevScore`
            prevScore = info["score"]
            report = Fore.RED + f"{move_unicode_symbol} {evaluation}" if evaluation == "Blunder" else Fore.GREEN + f"{move_unicode_symbol} {evaluation}"
            print(report)
            print(Style.RESET_ALL)
            cp, wdl, mate = evaluate.current.cp, evaluate.current.wdl, evaluate.current.mate
            move_info.extend([side, node.move, cp, fen, wdl, mate, evaluation])
            game_data.append(move_info)
            should_investigate_puzzle = True if evaluation in ["Blunder", "Mistake", "Miss"] else False

            if should_investigate_puzzle:
                print("\t".join([side, symbol_uci_move(node), fen, str(cp), evaluation, Fore.CYAN+"INVESTIGATE PUZULLE"]))
                print(Style.RESET_ALL)
                pass
            else:
                print("\t".join([side, symbol_uci_move(node), str(cp), evaluation]))

            if node.eval() and node.eval_depth():
                if node.eval_depth() < Constant.SCAN_ENGINE_DEPTH:
                    node.set_eval(prevScore, Constant.SCAN_ENGINE_DEPTH)
                if node.clock():
                    node.set_clock(node.clock())
            else:
                node.set_eval(prevScore, Constant.SCAN_ENGINE_DEPTH)
                if node.clock():
                    node.set_clock(node.clock())
        self.game = node.game()
        engine.quit()
        board.reset()  
        df = pd.DataFrame(game_data, columns=column_labels)    
        return node.game()