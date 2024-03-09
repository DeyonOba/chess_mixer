#!/usr/bin/env python3

"""Manages download and storage of lichess games based on game id or user API token"""

import os
import sys
import requests
import logging
# from chesspuzzler.constants import ENGINE_PATH, API_TOKEN_PATH
import chess.pgn

# Create logging folder if it does not exist
os.makedirs("./data/logging", exist_ok=True)
FORMAT = "%(asctime)s:%(funcName)s:%(levelname)s:%(message)s"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("./data/logging/utils.logging")
formater = logging.Formatter(FORMAT)
file_handler.setFormatter(formater)
logger.addHandler(file_handler)

class FileManger:
    __game_id = ""

    @staticmethod
    def save_url_game_content(file_object, game_id):
        # Create a directory to store the downloaded games if it doesn't exist
        parent_dir = os.path.join(".", "data")
        child_dir = os.path.join(parent_dir, "game_data")

        if not os.path.exists(parent_dir) or not os.path.exists(child_dir):
            os.makedirs(parent_dir, exist_ok=True)
            logger.debug("Creating Game data directory...")
        else:
            logger.debug("Game Data directory already created...")

        file_name = f'lichess_{game_id}.pgn'
        logger.debug(f"File Name: {file_name} to be created...")
        file_path = os.path.join(child_dir, file_name)
        logger.debug(f"File to be added to {file_path}...")

        with open(file_path, mode="w") as file:
            logger.debug("File Created...")
            try:
                file.writelines(file_object.content.decode())
                logger.debug(f"Added pgn content from Lichess from game id {game_id} to file...")
            except:
                logger.exception(f"Could not add content to {file_path}...")
        # check if the pgn file contains useful information about games
        try:
            with open(file_path) as file:
                game = chess.pgn.read_game(file)
                logger.debug("Checking if file is empty or not...")
                if game is None:
                    logger.debug(f"File {file_name} is empty, delecting file...")
                    os.remove(file_path)
                    logger.debug(f"{file_name} delected...")
                    sys.exit(1)
                else:
                    logger.debug(f"File: {file_name} has been stored in {child_dir}")
                del game
                FileManger.set_game_id(game_id)

        except FileNotFoundError as e:
            logger.exception("File not found ...")

    @classmethod
    def load_pgn_game(clf, game_id):
        FileManger.set_game_id(game_id)
        file_name = f"lichess_{game_id}.pgn"
        file_path = os.path.join(".", "data", "game_data", file_name)
        logger.debug(f"File path for loading data {file_path}...")
        if os.path.exists(file_path):
            with open(file_path) as file:
                game = chess.pgn.read_game(file)
                if game is None:
                    logger.error("File is empty ...")
                else:
                    logger.info(f"GAME LOADING SUCCESSFUL...\n{game}")
                    return game
        else:
            logger.error(f"{file_path} is not found...")

    @staticmethod
    def get_game_via_token(self):
        pass

    @staticmethod
    def set_game_id(game_id=""):
        if game_id:
            FileManger.__game_id = game_id
        else:
            FileManger.__game_id = input("Enter game id:")


class GameDownloader(FileManger):
    """Download lichess game

    Attributes:
        is_token(bool, optional): How the game is to be downloader
            if true then .json file location should be provided.
            if false then game id is to be provided.
    """

    def __init__(self, is_token=False):
        super().__init__()
        self.is_token = is_token
        self.game_id = ""
    
    def get_game_via_api(self):
        pass

    def get_game_via_gameid(self, game_id="") -> bool:
        if game_id:
            self.game_id = game_id
            LICHESS_SITE = "https://lichess.org/"
            TASK = "game/export/"
            url = LICHESS_SITE + TASK + game_id
            r = requests.get(url)
            
            if r.status_code == 200:
                self.save_url_game_content(r, self.game_id)
            else:
                print("Invalid game id response from Lichess....", file=sys.stderr)
                logger.error("Invalid game id response from Lichess....")
                sys.exit(1)
            return True
        else:
            self.set_game_id()
        return False
    
    def set_game_id(self):
        self.game_id = input("Enter Game id: ")
        if self.game_id:
            self.get_game_via_gameid(self.game_id)
        else:
            print("Enter valid game id from Lichess....", file=sys.stderr)
            logger.error("Entered empty string...")
            sys.exit(1)
        