"""
Chess Game with Human-like AI
Optimized for performance and stability
"""

import pygame, chess, chess.engine, random, time, sys, os, chess.pgn
from datetime import datetime
from threading import Thread, Lock
from collections import OrderedDict
from queue import Queue, Empty

# ============================================================================
# CONFIGURATION - Adjust these to tune AI speed
# ============================================================================
AI_MAX_ENGINE_TIME = 0.65  # Max seconds for engine analysis (MUCH stronger play)
AI_MAX_DEPTH = 30          # Maximum search depth (MUCH stronger play)
AI_MIN_SLEEP = 0.3         # Minimum thinking time display (seconds)
AI_MAX_SLEEP = 2.5         # Maximum thinking time display (seconds)

# ============================================================================
# CONSTANTS
# ============================================================================
WIDTH, HEIGHT = 640, 640
SQUARE_SIZE = WIDTH // 8
# Improved colors with better contrast
WHITE_COLOR, DARK_COLOR = (238, 238, 210), (118, 150, 86)
HIGHLIGHT_COLOR = (255, 255, 0, 180)  # Yellow highlight for last move
SELECT_COLOR = (100, 200, 255, 200)  # Blue highlight for selected square
MOVE_HINT_COLOR = (150, 255, 150, 120)  # Green hint for possible moves
# Keep the original installation paths exactly as in the user's version.
ENGINE_PATH = r"J:\vs code\python\chessGame\stockfish\stockfish-windows-x86-64-avx2.exe"
PIECE_FOLDER = r"J:\vs code\python\chessGame\pieces"

# Simple transposition cache (LRU, max 50 entries)
class SimpleCache:
    def __init__(self, max_size=50):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = Lock()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def put(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

class ChessGame:
    def __init__(self):
        pygame.init()
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Initialize engine with error handling
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
        except Exception as e:
            print(f"❌ Engine initialization failed: {e}")
            print(f"   Check the original Stockfish path: {ENGINE_PATH}")
            sys.exit(1)
        
        self.piece_images = self.load_piece_images()
        self.player_color = self.choose_color_ui()
        self.style_name, self.style_weights = self.select_play_style()
        pygame.display.set_caption(f"AI Chess - Style: {self.style_name.upper()}")
        
        self.board = chess.Board()
        self.selected_square = None
        self.move_number = 0
        self.flipped = False
        self.last_move = None
        self.move_stack, self.current_index, self.replay_mode = [], 0, False
        self.edit_mode = False  # Edit mode: allows free editing when stepping backward
        
        # Animation state
        self.animating = False
        self.anim_move = None
        self.anim_piece = None
        self.anim_start = 0
        self.anim_duration = 0.35  # Smoother, longer animation
        self.anim_captured_piece = None  # For capture effects
        self.anim_capture_fade = 1.0  # Fade effect for captured piece
        
        # Human-like AI state tracking
        self._ai_personality = self._initialize_personality()
        self._move_history_pattern = []
        self._last_from_square = None
        self._confidence_level = 0.5
        self._time_pressure = False
        self._human_behavior_state = {
            'hesitation_count': 0,  # Track hesitation patterns
            'confidence_boost': 0,  # Track confidence patterns
            'last_thinking_time': 0,  # Track timing patterns
            'suboptimal_choices': 0,  # Track suboptimal move frequency
        }
        
        # Performance optimizations
        self._analysis_cache = SimpleCache(max_size=50)
        # Thread-safe AI move queue (stores tuples: (start_fen, move))
        self._ai_move_queue = Queue()
        self._ai_thread = None
        self._ai_stop_flag = False
        self._ai_lock = Lock()
        
        # PGN saving state
        self._pgn_saved = False  # Track if current game has been saved


    def choose_color_ui(self):
        f = pygame.font.SysFont("arial", 36)
        wb = pygame.Rect(WIDTH//4 - 100, HEIGHT//2 - 40, 200, 60)
        bb = pygame.Rect(3*WIDTH//4 - 100, HEIGHT//2 - 40, 200, 60)
        while True:
            self.win.fill((30,30,30))
            t = f.render("🎮 Choose your color", True, (255,255,255))
            self.win.blit(t, (WIDTH//2 - t.get_width()//2, 100))
            pygame.draw.rect(self.win, (220,220,220), wb)
            pygame.draw.rect(self.win, (50,50,50), bb)
            self.win.blit(f.render("White", True, (0,0,0)), (wb.centerx - 60, wb.centery - 20))
            self.win.blit(f.render("Black", True, (255,255,255)), (bb.centerx - 60, bb.centery - 20))
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.quit_game()
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if wb.collidepoint(e.pos):
                        return "white"
                    if bb.collidepoint(e.pos):
                        return "black"

    def select_play_style(self):
        s = {
            "professional": [("pro-classic",[.5,.35,.15]),("pro-chessy",[.52,.33,.15]),("pro-soft",[.48,.37,.15]),("pro-human",[.5,.3,.2]),("pro-tired",[.47,.38,.15])],
            "solid": [("solid-normal",[.48,.38,.14]),("solid-wall",[.5,.35,.15]),("solid-shield",[.46,.4,.14]),("solid-careful",[.49,.37,.14]),("solid-heavy",[.45,.4,.15])],
            "creative": [("creative-wild",[.45,.35,.2]),("creative-spark",[.48,.32,.2]),("creative-magic",[.46,.34,.2]),("creative-fun",[.5,.3,.2]),("creative-chaos",[.42,.38,.2])],
            "realistic": [("real-normal",[.48,.37,.15]),("real-steady",[.5,.35,.15]),("real-smooth",[.47,.38,.15]),("real-easy",[.49,.36,.15]),("real-basic",[.45,.4,.15])]
        }
        k = random.choice(list(s))
        n, w = random.choice(s[k])
        print(f"🤖 Selected style: {k.upper()} | Substyle: {n} | Weights: {w}")
        return k, w

    def load_piece_images(self):
        m = {"P":"white-pawn.png","p":"black-pawn.png","N":"white-knight.png","n":"black-knight.png","B":"white-bishop.png","b":"black-bishop.png",
             "R":"white-rook.png","r":"black-rook.png","Q":"white-queen.png","q":"black-queen.png","K":"white-king.png","k":"black-king.png"}
        imgs = {}
        for k, f in m.items():
            p = os.path.join(PIECE_FOLDER, f)
            if not os.path.isfile(p):
                print(f"⚠️ Missing file: {p}")
                continue
            try:
                imgs[k] = pygame.transform.smoothscale(pygame.image.load(p).convert_alpha(), (SQUARE_SIZE, SQUARE_SIZE))
            except Exception as e:
                print(f"⚠️ Error loading {p}: {e}")
        return imgs

    def draw_board(self, skip_square=None):
        """Draw board with improved graphics, optionally skipping a square (for animation)"""
        # Draw board squares with enhanced visual effects (optimized)
        for r in range(8):
            for c in range(8):
                rr, cc = (r, c) if not self.flipped else (7-r, 7-c)
                base_clr = WHITE_COLOR if (r+c)%2==0 else DARK_COLOR
                
                rect = pygame.Rect(cc*SQUARE_SIZE, rr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                
                # Draw base square
                pygame.draw.rect(self.win, base_clr, rect)
                
                # Enhanced border with darker shade
                border_clr = tuple(max(0, c-40) for c in base_clr)
                pygame.draw.rect(self.win, border_clr, rect, 2)
                
                # Inner highlight for 3D depth effect
                highlight_clr = tuple(min(255, c+20) for c in base_clr)
                highlight_rect = pygame.Rect(cc*SQUARE_SIZE+2, rr*SQUARE_SIZE+2, SQUARE_SIZE-4, SQUARE_SIZE-4)
                pygame.draw.rect(self.win, highlight_clr, highlight_rect, 1)
                
                # Subtle corner highlights for 3D effect
                corner_size = 8
                corner_clr = tuple(min(255, c+25) for c in base_clr)
                # Top-left corner
                pygame.draw.polygon(self.win, corner_clr, [
                    (cc*SQUARE_SIZE, rr*SQUARE_SIZE),
                    (cc*SQUARE_SIZE + corner_size, rr*SQUARE_SIZE),
                    (cc*SQUARE_SIZE, rr*SQUARE_SIZE + corner_size)
                ])
        
        # Draw move hints for selected piece
        if self.selected_square is not None and not self.replay_mode:
            legal_moves = list(self.board.legal_moves)
            for move in legal_moves:
                if move.from_square == self.selected_square:
                    self._draw_overlay(move.to_square, MOVE_HINT_COLOR)
        
        # Highlight selected square
        if self.selected_square is not None:
            self._draw_overlay(self.selected_square, SELECT_COLOR)
        
        # Highlight last move squares
        if self.last_move:
            try:
                for sq in [self.last_move.from_square, self.last_move.to_square]:
                    self._draw_overlay(sq, HIGHLIGHT_COLOR)
            except Exception as e:
                if __debug__:
                    print(f"⚠️ Last move highlight error: {e}")
        
        # Draw pieces
        for r in range(8):
            for c in range(8):
                rr, cc = (r, c) if not self.flipped else (7-r, 7-c)
                i = chess.square(c, 7-r)
                # Skip drawing piece at skip_square (for animation)
                if skip_square is not None and i == skip_square:
                    continue
                # Skip if animating and this is the moving piece
                if self.animating and self.anim_move and i == self.anim_move.from_square:
                    continue
                p = self.board.piece_at(i)
                if p and (img := self.piece_images.get(p.symbol())):
                    # Draw piece directly (no shadows as requested)
                    self.win.blit(img, (cc*SQUARE_SIZE, rr*SQUARE_SIZE))
        
        # Draw animated piece on top
        if self.animating:
            self._draw_animation()
    
    def _draw_overlay(self, square, color):
        """Draw a semi-transparent overlay on a square"""
        try:
            r = 7 - chess.square_rank(square)
            c = chess.square_file(square)
            if self.flipped:
                r, c = 7-r, 7-c
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            if isinstance(color, tuple) and len(color) == 4:
                overlay.fill(color)
            else:
                overlay.fill((*color[:3], 180))
            self.win.blit(overlay, (c*SQUARE_SIZE, r*SQUARE_SIZE))
        except Exception:
            pass  # Ignore overlay errors
    
    def _ease_out_cubic(self, t):
        """Easing function for smooth animation"""
        return 1 - pow(1 - t, 3)
    
    def _draw_animation(self):
        """Draw animated piece movement with improved effects"""
        if not self.animating or not self.anim_move or not self.anim_piece:
            return
        
        try:
            elapsed = time.time() - self.anim_start
            progress = min(1.0, elapsed / self.anim_duration)
            eased_progress = self._ease_out_cubic(progress)
            
            start_sq = self.anim_move.from_square
            end_sq = self.anim_move.to_square
            
            sc, sr = chess.square_file(start_sq), 7 - chess.square_rank(start_sq)
            ec, er = chess.square_file(end_sq), 7 - chess.square_rank(end_sq)
            
            if self.flipped:
                sc, sr, ec, er = 7-sc, 7-sr, 7-ec, 7-er
            
            # Interpolate position with easing
            current_x = sc * SQUARE_SIZE + (ec - sc) * SQUARE_SIZE * eased_progress
            current_y = sr * SQUARE_SIZE + (er - sr) * SQUARE_SIZE * eased_progress
            
            # Draw captured piece fade effect (if capture)
            if self.anim_captured_piece and progress < 0.6:
                captured_img = self.piece_images.get(self.anim_captured_piece.symbol())
                if captured_img:
                    # Fade out captured piece with scale effect
                    fade_progress = progress / 0.6
                    fade_alpha = int(255 * (1 - fade_progress))
                    scale = 1.0 - fade_progress * 0.3  # Shrink while fading
                    
                    if fade_alpha > 0:
                        # Red flash effect for capture
                        flash_alpha = int(80 * (1 - fade_progress))
                        if flash_alpha > 0:
                            flash_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                            flash_surf.fill((255, 50, 50, flash_alpha))
                            self.win.blit(flash_surf, (ec * SQUARE_SIZE, er * SQUARE_SIZE))
                        
                        # Draw fading captured piece
                        scaled_size = int(SQUARE_SIZE * scale)
                        scaled_img = pygame.transform.smoothscale(captured_img, (scaled_size, scaled_size))
                        temp_img = scaled_img.copy()
                        temp_img.set_alpha(fade_alpha)
                        offset = (SQUARE_SIZE - scaled_size) // 2
                        self.win.blit(temp_img, (ec * SQUARE_SIZE + offset, er * SQUARE_SIZE + offset))
            
            img = self.piece_images.get(self.anim_piece.symbol())
            if img:
                # Smooth scale effect - piece slightly grows then returns to normal
                scale = 1.0 + 0.15 * (1 - abs(progress - 0.5) * 2)
                scaled_size = int(SQUARE_SIZE * scale)
                scaled_img = pygame.transform.smoothscale(img, (scaled_size, scaled_size))
                offset = (SQUARE_SIZE * (scale - 1)) / 2
                
                # Add glow effect during movement
                if progress < 0.8:
                    glow_alpha = int(50 * (1 - progress / 0.8))
                    glow_surf = pygame.Surface((scaled_size + 4, scaled_size + 4), pygame.SRCALPHA)
                    glow_surf.fill((255, 255, 200, glow_alpha))
                    self.win.blit(glow_surf, (current_x - offset - 2, current_y - offset - 2))
                
                self.win.blit(scaled_img, (current_x - offset, current_y - offset))
            
            # Check if animation is complete
            if progress >= 1.0:
                self.animating = False
                self.anim_move = None
                self.anim_piece = None
                self.anim_captured_piece = None
        except Exception as e:
            if __debug__:
                print(f"⚠️ Animation drawing error: {e}")
            self.animating = False

    def animate_move(self, move):
        """Start smooth animation for a move - IMPROVED VERSION"""
        try:
            # Validate move
            if move is None:
                return
            
            start, end = move.from_square, move.to_square
            piece = self.board.piece_at(start)
            if not piece:
                return
            
            # Check if this is a capture (BEFORE applying move)
            captured = self.board.piece_at(end)
            
            # Start animation BEFORE applying move to board
            self.animating = True
            self.anim_move = move
            self.anim_piece = piece
            self.anim_start = time.time()
            self.anim_captured_piece = captured
            self.anim_capture_fade = 1.0
            
            # Animate over multiple frames (handle events for responsiveness)
            while self.animating:
                # Handle events during animation (for responsiveness)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.quit_game()
                        return
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                        self.flipped = not self.flipped
                
                # Draw board (will call _draw_animation automatically)
                self.draw_board()
                pygame.display.flip()
                self.clock.tick(60)
                
                # Check if animation complete
                elapsed = time.time() - self.anim_start
                if elapsed >= self.anim_duration:
                    self.animating = False
                    break
            
            # Final draw to ensure piece is in correct position
            self.animating = False  # Stop animation
            self.anim_move = None
            self.anim_piece = None
            self.anim_captured_piece = None
            self.draw_board()
            pygame.display.flip()
        except Exception as e:
            print(f"⚠️ Animation error: {e}")
            import traceback
            traceback.print_exc()
            self.animating = False
            self.anim_move = None
            self.anim_piece = None
            self.anim_captured_piece = None

    def handle_player_input(self):
        """Handle all player input - keyboard and mouse"""
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit_game()
            elif e.type == pygame.KEYDOWN:
                # R key: Flip board (works in all modes)
                if e.key == pygame.K_r:
                    self.flipped = not self.flipped
                # Left Arrow: Go back in move history
                elif e.key == pygame.K_LEFT:
                    if self.current_index > 0:
                        self.current_index -= 1
                        # Rebuild board state up to current_index
                        self.board = chess.Board()
                        for m in self.move_stack[:self.current_index]:
                            self.board.push(m)
                        # Update last_move and enter replay/edit mode
                        self.last_move = self.move_stack[self.current_index-1] if self.current_index > 0 else None
                        self.selected_square = None  # Clear selection when entering replay
                        self.replay_mode = True
                        self.edit_mode = True  # Enter EDIT MODE when stepping backward
                        # Invalidate any pending AI results when entering replay
                        self._invalidate_ai_results()
                # Right Arrow: Go forward in move history
                elif e.key == pygame.K_RIGHT:
                    if self.current_index < len(self.move_stack):
                        self.board.push(self.move_stack[self.current_index])
                        self.last_move = self.move_stack[self.current_index]
                        self.current_index += 1
                        self.selected_square = None  # Clear selection
                        self.replay_mode = True
                        # Exit edit mode and replay mode if we've reached the end
                        if self.current_index >= len(self.move_stack):
                            self.replay_mode = False
                            self.edit_mode = False
                        else:
                            # Still in replay - invalidate AI results
                            self._invalidate_ai_results()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                # In edit mode: allow free editing (both colors movable)
                if self.edit_mode:
                    try:
                        x, y = pygame.mouse.get_pos()
                        f, r = x//SQUARE_SIZE, y//SQUARE_SIZE
                        # Clamp to valid board coordinates
                        f = max(0, min(7, f))
                        r = max(0, min(7, r))
                        if self.flipped:
                            f, r = 7-f, 7-r
                        sq = chess.square(f, 7-r)
                        
                        if self.selected_square is None:
                            # First click: select any piece (ignore player_color in edit mode)
                            p = self.board.piece_at(sq)
                            if p:  # Allow selecting any piece
                                self.selected_square = sq
                        else:
                            # Second click: make move in edit mode
                            move = chess.Move(self.selected_square, sq)
                            p = self.board.piece_at(self.selected_square)
                            # Handle pawn promotion
                            if p and p.piece_type == chess.PAWN and chess.square_rank(sq) in [0, 7]:
                                move = chess.Move(self.selected_square, sq, promotion=chess.QUEEN)
                            
                            if move in self.board.legal_moves:
                                # Apply edited move (truncates move_stack, invalidates AI)
                                self.apply_edited_move(move)
                            
                            # Always clear selection after attempting move
                            self.selected_square = None
                    except Exception as e:
                        print(f"⚠️ Input error in edit mode: {e}")
                        self.selected_square = None
                # Normal mode: only process mouse clicks if not in replay mode and it's player's turn
                elif not self.replay_mode:
                    if self.board.turn != (chess.WHITE if self.player_color == "white" else chess.BLACK):
                        continue  # Ignore mouse clicks when it's not player's turn
                    
                    try:
                        x, y = pygame.mouse.get_pos()
                        f, r = x//SQUARE_SIZE, y//SQUARE_SIZE
                        # Clamp to valid board coordinates
                        f = max(0, min(7, f))
                        r = max(0, min(7, r))
                        if self.flipped:
                            f, r = 7-f, 7-r
                        sq = chess.square(f, 7-r)
                        
                        if self.selected_square is None:
                            # First click: select piece
                            p = self.board.piece_at(sq)
                            if p and p.color == (chess.WHITE if self.player_color == "white" else chess.BLACK):
                                self.selected_square = sq
                        else:
                            # Second click: make move
                            move = chess.Move(self.selected_square, sq)
                            p = self.board.piece_at(self.selected_square)
                            # Handle pawn promotion
                            if p and p.piece_type == chess.PAWN and chess.square_rank(sq) in [0, 7]:
                                move = chess.Move(self.selected_square, sq, promotion=chess.QUEEN)
                            
                            if move in self.board.legal_moves:
                                self.animate_move(move)
                                # Double check move is still legal after animation
                                if move in self.board.legal_moves:
                                    self.board.push(move)
                                    self.last_move = move
                                    self.move_number += 1
                                    # Update move stack and exit replay mode
                                    self.move_stack = self.board.move_stack.copy()
                                    self.current_index = len(self.move_stack)
                                    self.replay_mode = False
                                else:
                                    # Move became illegal during animation
                                    print(f"⚠️ Move became illegal during animation: {move}")
                            
                            # Always clear selection after attempting move
                            self.selected_square = None
                    except Exception as e:
                        print(f"⚠️ Input error: {e}")
                        self.selected_square = None

    def _initialize_personality(self):
        """Initialize consistent AI personality traits"""
        return {
            'aggressiveness': random.uniform(0.3, 0.7),
            'positional_preference': random.uniform(0.4, 0.8),
            'risk_tolerance': random.uniform(0.3, 0.6),
            'opening_style': random.choice(['classical', 'modern', 'sharp']),
            'endgame_technique': random.uniform(0.7, 0.95)
        }
    
    def _invalidate_ai_results(self):
        """Clear any pending AI results from queue (replay mode safety)"""
        try:
            while True:
                self._ai_move_queue.get_nowait()
        except Empty:
            pass  # Queue is empty, which is fine
    
    def apply_edited_move(self, move):
        """
        Apply a move in edit mode:
        - Validates and applies the move
        - Truncates move_stack to current_index
        - Adds the new move
        - Updates current_index
        - Invalidates AI cache and pending results
        - Exits edit mode
        """
        if move not in self.board.legal_moves:
            return False  # Invalid move
        
        # Animate the move
        self.animate_move(move)
        
        # Double check move is still legal after animation
        if move not in self.board.legal_moves:
            return False  # Move became illegal
        
        # Apply move to board
        try:
            self.board.push(move)
        except Exception as e:
            print(f"⚠️ Error pushing move to board: {e}")
            return False
        
        self.last_move = move
        self.move_number += 1
        
        # Truncate move_stack: remove all moves after current_index
        self.move_stack = self.move_stack[:self.current_index]
        
        # Add the new edited move to move_stack
        self.move_stack.append(move)
        
        # Update current_index to point to the new end
        self.current_index = len(self.move_stack)
        
        # Invalidate AI cache (position has changed)
        with self._analysis_cache.lock:
            self._analysis_cache.cache.clear()
        
        # Invalidate any pending AI results
        self._invalidate_ai_results()
        
        # Exit edit mode and replay mode (game continues from new position)
        self.edit_mode = False
        self.replay_mode = False
        
        return True
    
    def _safe_engine_analyse(self, board, limit, multipv=1):
        """
        Safe wrapper for engine.analyse() with error handling and cache support.
        Handles both dict and list returns from multipv.
        """
        # Create stable cache key with explicit limit values
        fen = board.fen()
        time_sec = getattr(limit, 'time', None)
        depth = getattr(limit, 'depth', None)
        nodes = getattr(limit, 'nodes', None)
        cache_key = (fen, time_sec, depth, nodes, multipv)
        
        cached = self._analysis_cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            result = self.engine.analyse(board, limit, multipv=multipv)
            
            # Handle both dict (single) and list (multipv) returns
            if isinstance(result, list):
                # multipv returns list of dicts
                processed = []
                for info in result:
                    if isinstance(info, dict) and "pv" in info:
                        processed.append(info)
                if processed:
                    self._analysis_cache.put(cache_key, processed)
                    return processed
            elif isinstance(result, dict):
                # Single result
                if "pv" in result:
                    self._analysis_cache.put(cache_key, result)
                    return result
            
            return None
        except Exception as e:
            print(f"⚠️ Engine analysis error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _ai_worker_thread(self, board_copy, start_fen):
        """
        Worker thread for AI move calculation (non-blocking).
        Returns tuple: (start_fen, move) for state validation.
        """
        try:
            # Check stop flag early
            if self._ai_stop_flag:
                return
            
            # Create a temporary board copy for analysis
            temp_board = board_copy.copy()
            
            # Verify FEN matches (sanity check)
            if temp_board.fen() != start_fen:
                print(f"⚠️ Warning: Board FEN mismatch in worker thread")
                self._ai_move_queue.put((start_fen, None))
                return
            
            legal = list(temp_board.legal_moves)
            if not legal:
                self._ai_move_queue.put((start_fen, None))
                return
            
            # Check stop flag before expensive operations
            if self._ai_stop_flag:
                return
            
            # Phase detection
            move_num = temp_board.fullmove_number
            piece_count = len(temp_board.piece_map())
            if move_num <= 12:
                phase = "opening"
            elif piece_count > 12:
                phase = "middlegame"
            elif piece_count > 6:
                phase = "late_middlegame"
            else:
                phase = "endgame"
            
            # Check stop flag periodically
            if self._ai_stop_flag:
                return
            
            # Position evaluation
            position_eval = self._evaluate_position_quick_optimized_thread(temp_board)
            score = position_eval['score']
            is_winning = position_eval['is_winning']
            is_losing = position_eval['is_losing']
            complexity = position_eval['complexity']
            
            # Check stop flag after evaluation
            if self._ai_stop_flag:
                return
            
            # Update psychology (thread-safe)
            with self._ai_lock:
                if abs(score) > 200:
                    if (score > 0 and temp_board.turn == chess.WHITE) or (score < 0 and temp_board.turn == chess.BLACK):
                        self._confidence_level = min(0.9, self._confidence_level + 0.1)
                    else:
                        self._confidence_level = max(0.1, self._confidence_level - 0.15)
                else:
                    self._confidence_level = 0.5 + (self._confidence_level - 0.5) * 0.9
            
            # Generate candidate moves - always consider 3-6 reasonable candidates
            try:
                candidate_moves = self._generate_candidate_moves_optimized_thread(temp_board, legal, phase, is_losing, score)
                # Do not invent scores for unsearched legal moves. Only use engine-scored candidates.
            except Exception as e:
                print(f"⚠️ Candidate generation error: {e}")
                import traceback
                traceback.print_exc()
                candidate_moves = []
            
            if self._ai_stop_flag:
                return
            
            if not candidate_moves:
                self._ai_move_queue.put((start_fen, legal[0] if legal else None))
                return
            
            # Keep variation among genuinely comparable moves only. Scores are from White's perspective.
            best_score = candidate_moves[0][1] if candidate_moves else score
            safety_window = self._calculate_safety_window_human(
                is_winning, is_losing, phase, abs(score)
            )
            safe_candidates = []
            for move, move_score in candidate_moves:
                if temp_board.turn == chess.WHITE:
                    score_loss_from_best = best_score - move_score
                else:
                    score_loss_from_best = move_score - best_score
                if 0 <= score_loss_from_best <= safety_window:
                    safe_candidates.append((move, move_score))

            # Never widen the window by adding unscored or clearly inferior moves.
            if not safe_candidates and candidate_moves:
                safe_candidates = candidate_moves[:1]
            
            # Score moves
            scored_moves = []
            for move, move_score in safe_candidates:
                strength_score = self._normalize_strength_score_thread(move_score, score, temp_board.turn)
                human_score = self._calculate_human_likeness_enhanced_thread(move, move_score, score, phase, is_winning, is_losing, temp_board)
                combined_score = self._combine_scores_enhanced(strength_score, human_score, is_winning, is_losing, phase)
                scored_moves.append((move, move_score, human_score, combined_score))
            
            # Rank by engine evaluation first; style is only a tie-breaker.
            # Candidate scores are normalized to White's perspective.
            scored_moves.sort(
                key=lambda x: (x[1] if temp_board.turn == chess.WHITE else -x[1], x[3]),
                reverse=True
            )
            
            # Select move
            try:
                selected = self._probabilistic_select_enhanced(scored_moves, is_winning, is_losing, phase, temp_board.turn)
            except Exception as e:
                print(f"⚠️ Selection error: {e}")
                selected = None
            
            if not selected:
                if safe_candidates:
                    selected = safe_candidates[0][0]
                elif candidate_moves:
                    selected = candidate_moves[0][0]
                elif legal:
                    selected = legal[0]
                else:
                    selected = None
            
            # Handle pawn promotion
            if selected:
                p = temp_board.piece_at(selected.from_square)
                if p and p.piece_type == chess.PAWN and chess.square_rank(selected.to_square) in [0, 7]:
                    selected = chess.Move(selected.from_square, selected.to_square, promotion=chess.QUEEN)
            
            # Calculate thinking time (non-blocking - just for display)
            think_time = self._calculate_thinking_time_optimized(complexity, is_losing, phase)
            think_time = max(AI_MIN_SLEEP, min(think_time, AI_MAX_SLEEP))
            
            # Check stop flag before sleep
            if self._ai_stop_flag:
                return
            
            # Simulate thinking time (non-blocking sleep in thread)
            # Break sleep into chunks to check stop flag
            sleep_chunk = 0.1
            slept = 0.0
            while slept < think_time and not self._ai_stop_flag:
                time.sleep(min(sleep_chunk, think_time - slept))
                slept += sleep_chunk
            
            # Final stop flag check before returning result
            if self._ai_stop_flag:
                return
            
            # Put result in queue with start_fen for validation
            self._ai_move_queue.put((start_fen, selected))
            
        except Exception as e:
            print(f"⚠️ AI worker thread error: {e}")
            import traceback
            traceback.print_exc()
            # Return None move with start_fen for proper validation
            try:
                self._ai_move_queue.put((start_fen, None))
            except Exception:
                pass  # Queue might be closed
    
    def _evaluate_position_quick_optimized_thread(self, board):
        """Thread-safe position evaluation - ENHANCED for stronger play"""
        try:
            result = self._safe_engine_analyse(
                board,
                chess.engine.Limit(time=0.30, depth=AI_MAX_DEPTH),  # More time and depth for stronger play
                multipv=1
            )
            
            if result and isinstance(result, dict):
                score_obj = result.get("score")
                if score_obj and hasattr(score_obj, 'relative'):
                    score = score_obj.relative.score(mate_score=10000)
                else:
                    score = 0
            else:
                score = 0
        except Exception as e:
            # Log evaluation errors but don't crash worker thread
            if __debug__:
                print(f"⚠️ Position evaluation error in worker: {e}")
            score = 0
        
        if board.turn == chess.BLACK and score:
            score = -score
        
        legal_moves_list = list(board.legal_moves)
        piece_count = len(board.piece_map())
        legal_moves_count = len(legal_moves_list)
        is_check = board.is_check()
        captures = sum(1 for m in legal_moves_list if board.is_capture(m))
        
        complexity = (
            piece_count * 2 +
            min(legal_moves_count / 3, 20) +
            (30 if is_check else 0) +
            min(captures * 3, 15)
        )
        
        is_winning = score > 150 if board.turn == chess.WHITE else score < -150
        is_losing = score < -150 if board.turn == chess.WHITE else score > 150
        
        return {
            'score': score,
            'is_winning': is_winning,
            'is_losing': is_losing,
            'complexity': complexity
        }
    
    def _generate_candidate_moves_optimized_thread(self, board, legal_moves, phase, is_losing, current_score):
        """Thread-safe candidate move generation - ENHANCED for stronger play"""
        time_budget = AI_MAX_ENGINE_TIME
        if is_losing:
            time_budget *= 1.5  # More time when losing
        elif phase == "endgame":
            time_budget *= 1.4  # More time in endgame
        elif phase == "opening":
            time_budget *= 1.2  # More time in opening
        
        limit = chess.engine.Limit(time=time_budget, depth=AI_MAX_DEPTH)
        multipv_count = min(5, len(legal_moves))  # Spend more search effort per candidate
        
        try:
            analysis = self._safe_engine_analyse(board, limit, multipv=multipv_count)
            
            candidates = []
            if isinstance(analysis, list):
                for info in analysis:
                    if isinstance(info, dict) and "pv" in info and info["pv"]:
                        move = info["pv"][0]
                        score_obj = info.get("score")
                        if score_obj and hasattr(score_obj, 'relative'):
                            move_score = score_obj.relative.score(mate_score=10000)
                        else:
                            move_score = 0
                        if board.turn == chess.BLACK and move_score:
                            move_score = -move_score
                        candidates.append((move, move_score))
            elif isinstance(analysis, dict):
                if "pv" in analysis and analysis["pv"]:
                    move = analysis["pv"][0]
                    score_obj = analysis.get("score")
                    if score_obj and hasattr(score_obj, 'relative'):
                        move_score = score_obj.relative.score(mate_score=10000)
                    else:
                        move_score = 0
                    if board.turn == chess.BLACK and move_score:
                        move_score = -move_score
                    candidates.append((move, move_score))
            
            candidates.sort(key=lambda x: x[1], reverse=(board.turn == chess.WHITE))
            return candidates[:8]
            
        except Exception as e:
            print(f"⚠️ Candidate generation error: {e}")
            import traceback
            traceback.print_exc()
            return [(legal_moves[0], 0)] if legal_moves else []
    
    def _normalize_strength_score_thread(self, move_score, position_score, turn):
        """Thread-safe strength score normalization"""
        if position_score is None:
            return 0.5
        
        score_diff = move_score - position_score
        if turn == chess.BLACK:
            score_diff = -score_diff
        
        normalized = 0.5 + (score_diff / 200.0)
        return max(0.0, min(1.0, normalized))
    
    def _calculate_human_likeness_enhanced_thread(self, move, move_score, position_score, phase, is_winning, is_losing, board):
        """Thread-safe human-likeness calculation"""
        score = 50.0
        
        piece = board.piece_at(move.from_square)
        if not piece:
            return score
        
        piece_type = piece.piece_type
        to_rank, to_file = chess.square_rank(move.to_square), chess.square_file(move.to_square)
        test_board = board.copy()
        test_board.push(move)
        
        if phase == "opening":
            # Principle-based openings, not memorized theory
            if piece_type in [chess.KNIGHT, chess.BISHOP]:
                score += 35  # Development is key
            if piece_type == chess.QUEEN and board.fullmove_number < 8:
                score -= 40  # Strong penalty for early queen
            if board.is_castling(move):
                score += 45  # Castling is very human
            # Allow mild structural weaknesses (human behavior)
            if piece_type == chess.PAWN and not board.is_capture(move):
                score += 15  # Pawn moves in opening are human
            with self._ai_lock:
                if move.from_square == self._last_from_square:
                    score -= 30  # Avoid repetition
        elif phase == "endgame":
            # Endgame: Better technique, still human-like
            if piece_type == chess.KING:
                score += 40  # King activity (more important)
            if piece_type == chess.PAWN:
                score += 45  # Pawn advances critical (more important)
            if piece_type == chess.ROOK:
                score += 35  # Rook activity in endgame
            if test_board.is_check() and not board.is_capture(move):
                score -= 15  # Less penalty for checks (can be useful)
            # Less penalty for good moves in endgame
            if abs(move_score - position_score) < 10:
                score -= 10  # Reduced penalty (better technique)
            # Prefer strong moves in endgame
            if abs(move_score - position_score) > 30:
                score += 15  # Reward strong moves
        else:
            # Middlegame: prefer visible threats over hidden long-term ideas
            if board.is_capture(move):
                score += 28  # Exchanges are human
            if test_board.is_check():
                score += 20  # Visible threats
            # Prefer plans over tactics when equal
            if not board.is_capture(move) and not test_board.is_check():
                if abs(move_score - position_score) < 30:
                    score += 15  # Quiet positional moves
            # Do not penalize a forcing tactical improvement for being difficult to find.
        
        if is_winning and abs(position_score) > 150:
            # When ahead: Convert advantage more aggressively
            if board.is_capture(move) and not test_board.is_check():
                score += 50  # Exchanges when well ahead (stronger)
            if piece_type == chess.PAWN:
                score += 40  # Pawn advances to promote (more important)
            if piece_type == chess.ROOK:
                score += 35  # Rook activity (more important)
            if piece_type == chess.QUEEN:
                score += 30  # Queen activity to finish
            if piece_type == chess.KING and not test_board.is_check():
                score += 25  # King activity in endgame
            # Allow forcing lines when ahead (convert advantage)
            if test_board.is_check() and not board.is_capture(move):
                score += 10  # Checks can be good when ahead
            # Prefer active moves over passive simplification
            if not board.is_capture(move) and not test_board.is_check():
                score += 10  # Quiet moves still good but less preferred
        elif is_winning:
            if board.is_capture(move) and not test_board.is_check():
                score += 35
            if piece_type == chess.PAWN:
                score += 20
        elif is_losing:
            # When behind: increase complexity and material imbalance
            if test_board.is_check():
                score += 35  # Create threats
            if board.is_capture(move):
                score += 30  # Material imbalance
            if piece_type == chess.QUEEN:
                score += 25  # Queen activity
            # Prefer complexity over simplification
            if not board.is_capture(move) and not test_board.is_check():
                if abs(move_score - position_score) < 20:
                    score -= 15  # Penalize quiet moves when losing
        else:
            if board.is_capture(move):
                score += 25
            if test_board.is_check():
                score += 18
        
        center_dist = abs(to_rank - 3.5) + abs(to_file - 3.5)
        score += max(0, 25 - center_dist * 3)  # Central control (slightly more important)
        
        # Reward "human intuition" moves - moves that look natural
        if piece_type in [chess.KNIGHT, chess.BISHOP]:
            # Piece development/activity is human-preferred
            score += 10
        if board.is_castling(move):
            # Castling is very human (safety + development)
            score += 20
        
        # Never penalize a tactically correct move merely because it resembles an engine choice.
        
        if piece_type == chess.QUEEN:
            for opp_move in test_board.legal_moves:
                if test_board.is_capture(opp_move) and opp_move.to_square == move.to_square:
                    score -= 60
                    break
        
        with self._ai_lock:
            recent_moves = [m[0] for m in self._move_history_pattern[-3:]]
            if move.from_square in recent_moves:
                score -= 20
            recent_to_squares = [m[1] for m in self._move_history_pattern[-2:]]
            if move.to_square in recent_to_squares and move.from_square in recent_moves:
                score -= 25
        
        # Prefer moves within 20-50cp window (human evaluation - not perfect)
        # Humans don't always find the best move, they find "good enough" moves
        score_diff = abs(move_score - position_score) if position_score else 0
        if 20 <= score_diff <= 50:  # Sweet spot for human moves (slightly worse than perfect)
            score += 45  # STRONG preference for "human-like" moves
        elif 10 <= score_diff < 20:
            score += 30  # Good moves, but not too perfect
        elif score_diff < 10:
            score += 15  # Too perfect - might be engine-like (reduced bonus)
        elif score_diff < 70:
            score += 20  # Acceptable human error range
        # Moves 70-120cp worse: small penalty (human can make these mistakes)
        elif score_diff < 120:
            score -= 5  # Small penalty but still human
        
        return max(0.0, min(100.0, score))
    
    def _calculate_safety_window_human(self, is_winning, is_losing, phase, advantage_magnitude):
        """
        Human evaluation window: MUCH TIGHTER for stronger play while staying human.
        """
        if is_winning:
            # When ahead: VERY TIGHT window to convert advantage (much stronger)
            if advantage_magnitude > 200:
                # Well ahead: 5-15cp window (convert very aggressively)
                return random.uniform(5, 15)
            elif advantage_magnitude > 150:
                # Good advantage: 8-18cp window
                return random.uniform(8, 18)
            elif advantage_magnitude > 100:
                # Moderate advantage: 12-22cp window
                return random.uniform(12, 22)
            else:
                # Small advantage: 15-25cp window
                return random.uniform(15, 25)
        elif is_losing:
            # When behind: wider window for counterplay
            return random.uniform(30, 50)
        elif phase == "endgame":
            # Endgame: very tight window for strong technique
            return random.uniform(5, 20)
        else:
            # When equal: tighter window for stronger play
            return random.uniform(10, 30)
    
    def _combine_scores_enhanced(self, strength_score, human_score, is_winning, is_losing, phase):
        """
        Balanced weighting: Stronger play while maintaining human behavior.
        Target: 2400-2600 Elo with human statistical behavior.
        """
        # Balance: Strong but human
        if is_winning:
            # When ahead: 75% strength, 25% human (convert advantage VERY strongly)
            weight_strength = 0.75
            weight_human = 0.25
        elif is_losing:
            # When behind: 70% strength, 30% human (survival priority)
            weight_strength = 0.70
            weight_human = 0.30
        elif phase == "endgame":
            # Endgame: very strong technique but still human
            weight_strength = 0.75
            weight_human = 0.25
        else:
            # When equal: balanced but stronger
            weight_strength = 0.65
            weight_human = 0.35
        
        # Phase adjustments - boost strength more
        confidence_factor = self._confidence_level
        # Endgame: strong boost
        if phase == "endgame":
            weight_strength *= 1.20  # Strong boost for endgame
        # Confidence adjustment
        weight_strength = min(0.80, weight_strength * (0.95 + 0.10 * confidence_factor))
        weight_human = 1.0 - weight_strength
        
        combined = (strength_score * weight_strength * 100) + (human_score * weight_human)
        return combined
    
    def _probabilistic_select_enhanced(self, scored_moves, is_winning, is_losing, phase, turn):
        """
        Offline human-style selection using a bounded engine-loss window plus
        position-specific move preferences. This is a heuristic policy, not a
        trained Maia/Allie neural model; engine quality remains a hard constraint.
        """
        if not scored_moves:
            return None

        best_score = scored_moves[0][1]
        if is_winning or phase == "endgame":
            max_loss = 12
            loss_temperature = 7.0
            human_influence = 0.30
        elif is_losing:
            max_loss = 24
            loss_temperature = 13.0
            human_influence = 0.65
        else:
            max_loss = 20
            loss_temperature = 10.0
            human_influence = 0.50

        # Keep only moves close to the engine's best candidate. Preserve the
        # existing tuple format: (move, engine_score, human_score, combined_score).
        comparable = []
        for item in scored_moves:
            move, move_score = item[0], item[1]
            loss = best_score - move_score if turn == chess.WHITE else move_score - best_score
            if 0 <= loss <= max_loss:
                human_score = float(item[2]) if len(item) > 2 else 50.0
                combined_score = float(item[3]) if len(item) > 3 else human_score
                comparable.append((move, loss, human_score, combined_score))

        if not comparable:
            return scored_moves[0][0]
        if len(comparable) == 1:
            return comparable[0][0]

        best_human = max(item[2] for item in comparable)
        best_combined = max(item[3] for item in comparable)
        weights = []
        for _, loss, human_score, combined_score in comparable:
            # A softmax-like policy: engine loss suppresses weak moves, while
            # natural move features affect the choice among comparably good moves.
            engine_factor = 2.718281828 ** (-loss / loss_temperature)
            human_factor = 2.718281828 ** (human_influence * (human_score - best_human) / 12.0)
            combined_factor = 2.718281828 ** (0.20 * (combined_score - best_combined) / 12.0)
            weights.append(max(0.001, engine_factor * human_factor * combined_factor))

        return random.choices([item[0] for item in comparable], weights=weights, k=1)[0]

    def _calculate_thinking_time_optimized(self, complexity, is_losing, phase):
        """
        Human thinking time: COMPLETELY IRREGULAR and UNPREDICTABLE.
        NO correlation with position strength or complexity.
        Simulates real human behavior: hesitation, confidence, distraction.
        """
        # Base times vary randomly - no fixed pattern
        base_times = {
            "opening": random.uniform(0.3, 1.2),
            "middlegame": random.uniform(0.5, 2.0),
            "late_middlegame": random.uniform(0.6, 2.2),
            "endgame": random.uniform(0.4, 2.5)
        }
        base_time = base_times.get(phase, random.uniform(0.5, 1.5))
        
        # Human behavior patterns (completely random, no logic)
        behavior_roll = random.random()
        
        if behavior_roll < 0.20:
            # 20%: Hesitation - think longer on "obvious" moves (human doubt)
            base_time *= random.uniform(1.5, 3.0)
        elif behavior_roll < 0.35:
            # 15%: Confidence - play fast even in complex positions (human intuition)
            base_time *= random.uniform(0.2, 0.6)
        elif behavior_roll < 0.50:
            # 15%: Distraction - long pause (checking phone, thinking about other things)
            base_time *= random.uniform(2.0, 4.0)
        elif behavior_roll < 0.65:
            # 15%: Quick decision - obvious move, no thinking
            base_time *= random.uniform(0.15, 0.4)
        elif behavior_roll < 0.80:
            # 15%: Deep calculation - thinking hard
            base_time *= random.uniform(1.8, 2.5)
        else:
            # 20%: Normal variation - completely random
            base_time *= random.uniform(0.3, 2.5)
        
        # When losing: sometimes panic (fast), sometimes careful (slow) - random
        if is_losing:
            if random.random() < 0.4:
                # Panic mode - play fast
                base_time *= random.uniform(0.3, 0.7)
            else:
                # Careful mode - think more
                base_time *= random.uniform(1.3, 2.0)
        
        # Time pressure simulation (occasional, random)
        if random.random() < 0.25:
            base_time *= random.uniform(0.2, 0.8)
        
        # Large random variations (human inconsistency - key for anti-cheat)
        random_factor = random.uniform(0.2, 3.0)  # Even wider range
        think_time = base_time * random_factor
        
        # Occasional very long pauses (human distraction, checking analysis)
        if random.random() < 0.15:
            think_time += random.uniform(1.0, 3.0)
        
        # Occasional instant moves (human confidence, obvious moves)
        if random.random() < 0.20:
            think_time *= random.uniform(0.1, 0.5)
        
        # Add micro-variations (human can't be perfectly consistent)
        think_time += random.uniform(-0.1, 0.1)
        
        # Ensure within bounds
        think_time = max(AI_MIN_SLEEP, min(think_time, AI_MAX_SLEEP))
        
        return think_time
    
    def save_pgn_game(self):
        """
        Save current game to PGN file (overwrite mode).
        Builds PGN strictly from move_stack.
        Should be called only when game is over or quitting.
        """
        # Prevent duplicate saves
        if self._pgn_saved:
            return
        
        try:
            # Build game from move_stack (not from current board state)
            game = chess.pgn.Game()
            
            # Reconstruct board and apply moves from move_stack
            temp_board = chess.Board()
            for move in self.move_stack:
                if move in temp_board.legal_moves:
                    temp_board.push(move)
                else:
                    # Invalid move in stack - log and skip
                    print(f"⚠️ Warning: Invalid move in move_stack: {move}")
                    break
            
            # Set headers
            game.headers["Event"] = "Casual Game"
            if self.player_color == "white":
                game.headers["White"] = "Human"
                game.headers["Black"] = "AI"
            else:
                game.headers["White"] = "AI"
                game.headers["Black"] = "Human"
            game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
            
            # Determine result
            if temp_board.is_game_over():
                game.headers["Result"] = temp_board.result()
            else:
                game.headers["Result"] = "*"
            
            # Build move sequence from move_stack
            node = game
            for move in self.move_stack:
                node = node.add_variation(move)
            
            # Write PGN file (overwrite mode - single game only)
            with open("test_output.pgn", "w", encoding="utf-8") as f:
                exporter = chess.pgn.FileExporter(f)
                game.accept(exporter)
            
            self._pgn_saved = True
            print(f"✅ PGN saved: {len(self.move_stack)} moves, Result: {game.headers['Result']}")
            
        except Exception as e:
            print(f"❌ PGN save error: {e}")
            import traceback
            traceback.print_exc()

    def quit_game(self):
        """Safely quit game and close engine"""
        # Save PGN before quitting (if not already saved)
        if not self._pgn_saved:
            self.save_pgn_game()
        
        # Signal AI thread to stop
        self._ai_stop_flag = True
        
        # Wait for AI thread to finish (with timeout)
        if self._ai_thread and self._ai_thread.is_alive():
            self._ai_thread.join(timeout=1.0)
        
        # Close engine exactly once
        try:
            if hasattr(self, 'engine') and self.engine:
                self.engine.quit()
        except Exception as e:
            print(f"⚠️ Engine quit error: {e}")
        
        pygame.quit()
        sys.exit(0)

    def run(self):
        """Main game loop with responsive UI"""
        while True:
            # Draw board first
            self.draw_board()
            pygame.display.flip()
            
            # Check game over (before processing input)
            if self.board.is_game_over():
                print("🏁 Game Over:", self.board.result())
                # Save PGN before quitting
                if not self._pgn_saved:
                    self.save_pgn_game()
                time.sleep(2)
                self.quit_game()
            
            # Always handle input (handles QUIT, keys, mouse)
            # Input handler checks replay_mode and turn internally
            self.handle_player_input()
            
            # Process game logic only when not in replay mode or edit mode
            if not self.replay_mode and not self.edit_mode:
                # Ensure board state matches move_stack when not in replay
                if self.current_index != len(self.move_stack):
                    # Sync: if we're at the end, ensure we're at the end
                    self.current_index = len(self.move_stack)
                
                # AI turn (only when it's AI's turn and not replay mode)
                if self.board.turn != (chess.WHITE if self.player_color == "white" else chess.BLACK):
                    # Check if AI result is ready
                    try:
                        result = self._ai_move_queue.get_nowait()
                        if result is None:
                            # Invalid result format
                            if self._ai_thread and self._ai_thread.is_alive():
                                self._ai_thread.join(timeout=0.1)
                            self._ai_thread = None
                        else:
                            start_fen, move = result
                            
                            # CRITICAL: Validate that board state matches when AI started
                            current_fen = self.board.fen()
                            if start_fen != current_fen:
                                # Board state changed - discard this move
                                print(f"⚠️ Discarded stale AI move: board state changed")
                                if self._ai_thread and self._ai_thread.is_alive():
                                    self._ai_thread.join(timeout=0.1)
                                self._ai_thread = None
                            elif move and move in self.board.legal_moves:
                                # Valid move - apply it (double check legality)
                                self.animate_move(move)
                                # Double check move is still legal after animation
                                if move in self.board.legal_moves:
                                    self.board.push(move)
                                    self.last_move = move
                                    self.move_number += 1
                                    # Update move stack after AI move
                                    self.move_stack = self.board.move_stack.copy()
                                    self.current_index = len(self.move_stack)
                                    self.replay_mode = False
                                    
                                    # Track move for consistency
                                    self._last_from_square = move.from_square
                                    with self._ai_lock:
                                        self._move_history_pattern.append((move.from_square, move.to_square))
                                        if len(self._move_history_pattern) > 10:
                                            self._move_history_pattern.pop(0)
                                else:
                                    # Move became illegal - undo animation state
                                    print(f"⚠️ AI move became illegal: {move}")
                                    self.animating = False
                                
                                # Note: PGN is saved only when game ends or on quit
                                # (not after each move to avoid duplicate saves)
                            
                            # Clean up thread
                            if self._ai_thread and self._ai_thread.is_alive():
                                self._ai_thread.join(timeout=0.1)
                            self._ai_thread = None
                        
                    except Empty:
                        # No result yet - check if thread is running
                        if self._ai_thread is None or not self._ai_thread.is_alive():
                            # Start AI worker thread with current board state
                            if not self._ai_stop_flag:
                                start_fen = self.board.fen()
                                self._ai_thread = Thread(target=self._ai_worker_thread, args=(self.board, start_fen), daemon=True)
                                self._ai_thread.start()
                    except Exception as e:
                        # Unexpected error - log and reset
                        print(f"⚠️ Error processing AI result: {e}")
                        import traceback
                        traceback.print_exc()
                        if self._ai_thread and self._ai_thread.is_alive():
                            self._ai_thread.join(timeout=0.1)
                        self._ai_thread = None
            
            self.clock.tick(60)

if __name__ == "__main__":
    try:
        ChessGame().run() 
    except KeyboardInterrupt:
        print("\n👋 Game interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
