import sys
import logging

# from chesspuzzler.colours import Color
from chesspuzzler.chess_analysis import symbol_uci_move, BoardInfo
from colorama import Fore, Style


def log_board(boardinfo: BoardInfo, node, cp, evaluation):
    message = ""

    if evaluation in ["Blunder", "Mistake"]:
        map_nag = {"Blunder": "??", "Mistake": "?!"}
        map_colour = {"Blunder": Fore.RED, "Mistake": Fore.LIGHTYELLOW_EX}
        move_symbol = map_colour[evaluation] + symbol_uci_move(node) + map_nag[evaluation] + Fore.RESET
        evaluation = map_colour[evaluation] + evaluation + Fore.RESET
        list_ = [boardinfo.half_move_number, boardinfo.side, move_symbol, cp, evaluation, "\n"+boardinfo.fen]
        list_ = list(map(str, list_))
        message += "\t".join(list_)

    else:
        move_symbol = symbol_uci_move(node)
        evaluation = Fore.GREEN + evaluation + Fore.RESET
        list_ = [boardinfo.half_move_number, boardinfo.side, move_symbol,cp, evaluation]
        list_ = list(map(str, list_))
        message += "\t".join(list_)      
    return(message)

