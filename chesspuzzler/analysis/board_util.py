import chess
import math
from chess import Board, Square, Move
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

def material_count(board: chess.Board, turn: chess.Color) -> int:
    piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9
    }
    sum = 0
    for piece_type, piece_value in piece_values.items():
        sum += len(board.pieces(piece_type, turn)) * piece_value
    return sum

def material_diff(board: chess.Board, turn: chess.Color) -> int:
    return material_count(board, turn) - material_count(board, not turn)

def up_in_material(board: chess.Board, turn: chess.Color) -> bool:
    return material_diff(board, turn) > 0

def is_piece_hanging(board: Board, square: Square):
    piece = board.piece_at(square)

    if not piece:
        return False # There is no piece on this Square
    
    color = piece.color
    opp_color = not color

    attacked = board.is_attacked_by(opp_color, square)
    if not attacked:
        return False # Piece is not attacked, therefore it's not hanging
    
    defended = board.is_attacked_by(color, square)

    return attacked and not defended

def win_chances(cp: int) -> float:
    """
    winning chances from -1 to 1 """
    MULTIPLIER = -0.00368208 # https://github.com/lichess-org/lila/pull/11148
    cp = cp if cp else 10_000
    return 2 / (1 + math.exp(MULTIPLIER * cp)) - 1

def wdl_score(winningChance):
    return (50 + 50 * winningChance) * 0.01

def is_capture(previous_board: Board, square: Square, color: chess.Color):
    piece = previous_board.piece_at(square)

    if not piece:
        return False
    if piece.color == color:
        return False
    return True

def threaten_attack(current_board: Board, square: Square, color: chess.Color):
    # tmp_board = current_board.copy()

    for attacked_square in current_board.attacks(square):
        piece_attacked = current_board.piece_at(attacked_square)
        if piece_attacked and piece_attacked.color != color:
            return True
    return False

def advanced_pawn(current_board: Board, square: Square, color: chess.Color):
    piece_type = current_board.piece_type_at(square)

    if piece_type != chess.PAWN:
        return False
    board_rank = chess.square_rank(square)
    return board_rank > 4 if not color else board_rank < 3

def slient_move(current_board: Board, previous_board: Board, color: chess.Color, move: Move):
    if (
        # if the previous board player was in check
        # or player gives check in the next move
        (previous_board.is_check() or previous_board.gives_check(move)) and
        # if previously the opponent had a piece on the square of the current move and was capture
        # or on the current board players current move threatens a piece capture
        (previous_board.is_capture(move) and threaten_attack(current_board, move.to_square, color)) and 
        # if current move is a king move
        current_board.piece_type_at(move.to_square) != chess.KING and
        # if current move is an advancing pawn
        not advanced_pawn(current_board, move.to_square, color)):
        return True
    return False
