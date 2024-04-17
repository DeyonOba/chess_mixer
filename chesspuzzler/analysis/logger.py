import sys
import logging

# from chesspuzzler.colours import Color
from chesspuzzler.analysis.chess_analysis import symbol_uci_move, BoardInfo
from colorama import Fore, Style



def configure_log(logger_name: str, filename: str, encoding='utf-8', view_on_console=True):
    # create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # create file handler
    file_handler = logging.FileHandler(filename, encoding=encoding)
    file_handler.setLevel(logging.DEBUG)

    # create format and add to handlers
    format = '%(message)s'
    formatter = logging.Formatter(format)
    file_handler.setFormatter(formatter)

    # add the file handler to the logger
    logger.addHandler(file_handler)

    # create console handler and add to logger
    if view_on_console:
        console_handler  = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        console_handler.setFormatter(formatter)

    return logger


def log_board(boardinfo: BoardInfo, node, cp, evaluation):
    message = ""

    if evaluation in ["Blunder", "Mistake", "Inaccuracy"]:
        map_nag = {"Blunder": "??", "Mistake": "?", "Inaccuracy": "?!"}
        map_colour = {"Blunder": Fore.RED, "Mistake": Fore.LIGHTYELLOW_EX, "Inaccuracy": Fore.LIGHTCYAN_EX}
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

