import chess
import re
"""Board tools."""

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
