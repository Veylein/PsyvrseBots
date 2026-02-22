import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import time
import io
from PIL import Image, ImageDraw, ImageFont

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}
try:
    from utils.stat_hooks import us_inc as _arc_inc, us_mg as _arc_mg
except Exception:
    _arc_inc = _arc_mg = None

class PacManGame:
    """Turn-based procedural PacMan game logic"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.width = 15
        self.height = 15
        self.block_size = 32
        
        # 0: Wall, 1: Pellet, 2: Empty, 3: Power Pellet
        self.grid = {}
        self.score = 0
        self.lives = 3
        self.state = "playing" # playing, game_over, win
        
        self.pacman = {"x": 1, "y": 1, "dir": "right", "mouth_open": True}
        self.ghosts = []
        
        self.generate_maze()
        self.spawn_ghosts()
        
    def generate_maze(self):
        """Generate a proper maze using Recursive Backtracker"""
        # Initialize full walls
        for x in range(self.width):
            for y in range(self.height):
                self.grid[(x, y)] = 0 # Wall
        
        # Recursive Backtracker
        # Start at (1, 1)
        stack = [(1, 1)]
        self.grid[(1, 1)] = 1 # Path (with pellet)
        
        while stack:
            cx, cy = stack[-1]
            # Find neighbors (distance 2)
            neighbors = []
            for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
                nx, ny = cx + dx, cy + dy
                if 1 <= nx < self.width - 1 and 1 <= ny < self.height - 1:
                    if self.grid[(nx, ny)] == 0:
                        neighbors.append((nx, ny, dx, dy))
            
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                # Carve path to neighbor (remove wall between)
                self.grid[(cx + dx//2, cy + dy//2)] = 1
                self.grid[(nx, ny)] = 1
                stack.append((nx, ny))
            else:
                stack.pop()
        
        # Add some random loops (remove random walls) to make it more PacMan-like
        # PacMan maps aren't perfect mazes
        for _ in range(self.width * 2):
            rx = random.randint(1, self.width - 2)
            ry = random.randint(1, self.height - 2)
            if self.grid[(rx, ry)] == 0:
                # Check if it connects two paths
                horizontal_connect = self.grid.get((rx-1, ry)) != 0 and self.grid.get((rx+1, ry)) != 0
                vertical_connect = self.grid.get((rx, ry-1)) != 0 and self.grid.get((rx, ry+1)) != 0
                
                if horizontal_connect or vertical_connect:
                    self.grid[(rx, ry)] = 1
        
        # Ensure PacMan start is clear
        self.grid[(1, 1)] = 2 # Empty start
        self.pacman["x"], self.pacman["y"] = 1, 1
        
        # Center ghost house
        center_x, center_y = self.width // 2, self.height // 2
        for x in range(center_x - 1, center_x + 2):
            for y in range(center_y - 1, center_y + 2):
                self.grid[(x, y)] = 2 # Empty box
        
        # Place Power Pellets in corners
        corners = [(1, self.height-2), (self.width-2, 1), (self.width-2, self.height-2)]
        for cx, cy in corners:
            if (cx, cy) in self.grid and self.grid[(cx, cy)] != 0:
                self.grid[(cx, cy)] = 3

    def spawn_ghosts(self):
        colors = [(255, 0, 0), (255, 184, 255), (0, 255, 255), (255, 184, 82)] # Blinky, Pinky, Inky, Clyde
        center_x, center_y = self.width // 2, self.height // 2
        
        for i, color in enumerate(colors):
            self.ghosts.append({
                "x": center_x, 
                "y": center_y, 
                "color": color, 
                "scared": 0, # Scared timer
                "respawn_timer": i * 2 # Staggered release
            })

    def move_player(self, direction):
        if self.state != "playing":
            return
            
        dx, dy = 0, 0
        if direction == "up": dy = -1
        elif direction == "down": dy = 1
        elif direction == "left": dx = -1
        elif direction == "right": dx = 1
        
        nx, ny = self.pacman["x"] + dx, self.pacman["y"] + dy
        
        # Check wall collision
        if self.grid.get((nx, ny), 0) == 0:
            return # Blocked
        
        # Move
        self.pacman["x"], self.pacman["y"] = nx, ny
        self.pacman["dir"] = direction
        self.pacman["mouth_open"] = not self.pacman["mouth_open"]
        
        # Collect items
        cell = self.grid.get((nx, ny))
        if cell == 1: # Pellet
            self.score += 10
            self.grid[(nx, ny)] = 2 # Empty
        elif cell == 3: # Power Pellet
            self.score += 50
            self.grid[(nx, ny)] = 2
            # Scare ghosts
            for ghost in self.ghosts:
                ghost["scared"] = 15 # 15 turns
        
        # Move Ghosts (AI)
        self.move_ghosts()
        
        # Check Collisions
        self.check_collisions()
        
        # Check Win
        if not any(v in [1, 3] for v in self.grid.values()):
            self.state = "win"

    def move_ghosts(self):
        px, py = self.pacman["x"], self.pacman["y"]
        
        for ghost in self.ghosts:
            if ghost["respawn_timer"] > 0:
                ghost["respawn_timer"] -= 1
                continue
            
            gx, gy = ghost["x"], ghost["y"]
            possible_moves = []
            
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = gx + dx, gy + dy
                if self.grid.get((nx, ny), 0) != 0: # Not a wall
                    possible_moves.append((nx, ny))
            
            if not possible_moves:
                continue
                
            # AI Logic
            best_move = None
            
            if ghost["scared"] > 0:
                # Run away from PacMan
                # Maximize distance
                best_move = max(possible_moves, key=lambda m: abs(m[0]-px) + abs(m[1]-py))
                ghost["scared"] -= 1
            else:
                # Chase PacMan (simple)
                # Minimize distance
                # Add randomness to prevent stacking (20% random move)
                if random.random() < 0.2:
                    best_move = random.choice(possible_moves)
                else:
                    best_move = min(possible_moves, key=lambda m: abs(m[0]-px) + abs(m[1]-py))
            
            ghost["x"], ghost["y"] = best_move

    def check_collisions(self):
        px, py = self.pacman["x"], self.pacman["y"]
        for ghost in self.ghosts:
            if ghost["x"] == px and ghost["y"] == py:
                if ghost["scared"] > 0:
                    # Eat Ghost
                    self.score += 200
                    ghost["x"] = self.width // 2
                    ghost["y"] = self.height // 2
                    ghost["scared"] = 0
                    ghost["respawn_timer"] = 3
                else:
                    # Die
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = "game_over"
                    else:
                        # Reset positions
                        self.pacman["x"], self.pacman["y"] = 1, 1
                        self.pacman["dir"] = "right" # Reset direction too
                        # Reset ghosts
                        self.ghosts = []
                        self.spawn_ghosts()

    def render(self):
        w, h = self.width * self.block_size, self.height * self.block_size
        img = Image.new('RGB', (w, h), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw Walls
        for (x, y), cell in self.grid.items():
            rect = [x * self.block_size, y * self.block_size, (x+1) * self.block_size, (y+1) * self.block_size]
            if cell == 0:
                # Blue hollow walls like retro PacMan
                draw.rectangle(rect, outline=(33, 33, 255), width=2)
                # Optional: Fill slightly
                # draw.rectangle(rect, fill=(0, 0, 50))
            elif cell == 1:
                # Pellet
                cx, cy = (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2
                r = 3
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 184, 174))
            elif cell == 3:
                # Power Pellet
                cx, cy = (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2
                r = 8
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 184, 174))
        
        # Draw Ghosts with improved graphics
        for ghost in self.ghosts:
            gx, gy = ghost["x"] * self.block_size, ghost["y"] * self.block_size
            color = (0, 0, 255) if ghost["scared"] > 0 else ghost["color"]
            
            # Body (Round top)
            draw.chord([gx+2, gy+2, gx+30, gy+30], 180, 0, fill=color) 
            draw.rectangle([gx+2, gy+16, gx+30, gy+26], fill=color)
            
            # Wavy feet (3 triangles)
            foot_size = 28 // 3
            for i in range(3):
                fx = gx + 2 + (i * foot_size)
                # Simple jagged bottom
                draw.polygon([
                    (fx, gy+26), 
                    (fx + foot_size//2, gy+30), 
                    (fx + foot_size, gy+26)
                ], fill=color)

            # Eyes (White sclera)
            eye_y = gy + 10
            # Scared ghosts have different eyes (wavy mouth or small eyes)
            if ghost["scared"] > 0:
                 # Small scared eyes
                 draw.rectangle([gx+8, gy+12, gx+12, gy+14], fill=(255, 200, 200)) 
                 draw.rectangle([gx+20, gy+12, gx+24, gy+14], fill=(255, 200, 200))
                 # Wavy scared mouth
                 draw.line([(gx+6, gy+20), (gx+10, gy+18), (gx+14, gy+20), (gx+18, gy+18), (gx+22, gy+20), (gx+26, gy+18)], fill=(255, 200, 200), width=1)
            else:
                # Normal eyes looking in direction of movement (simulated randomness for now or center)
                draw.ellipse([gx+6, gy+8, gx+14, gy+18], fill=(255, 255, 255))
                draw.ellipse([gx+18, gy+8, gx+26, gy+18], fill=(255, 255, 255))
                # Pupils (Blue)
                # Look towards PacMan simply
                look_x = 0
                if self.pacman["x"] > ghost["x"]: look_x = 2
                elif self.pacman["x"] < ghost["x"]: look_x = -2
                
                look_y = 0
                if self.pacman["y"] > ghost["y"]: look_y = 2
                elif self.pacman["y"] < ghost["y"]: look_y = -2
                
                draw.ellipse([gx+8+look_x, gy+11+look_y, gx+12+look_x, gy+15+look_y], fill=(0, 0, 255))
                draw.ellipse([gx+20+look_x, gy+11+look_y, gx+24+look_x, gy+15+look_y], fill=(0, 0, 255))


        
        # Draw PacMan (High Quality)
        px, py = self.pacman["x"] * self.block_size, self.pacman["y"] * self.block_size
        mouth_angle = 45 if self.pacman["mouth_open"] else 5
        start_angle = 0
        direction = self.pacman["dir"]
        
        # Determine angle
        if direction == "right": start_angle = 0
        elif direction == "down": start_angle = 90
        elif direction == "left": start_angle = 180
        elif direction == "up": start_angle = 270
        
        # Shadow/3D effect
        # draw.pieslice([px+4, py+4, px+32, py+32], start_angle + mouth_angle, start_angle + 360 - mouth_angle, fill=(180, 180, 0))
        
        # Main Body
        draw.pieslice([px+2, py+2, px+30, py+30], start_angle + mouth_angle, start_angle + 360 - mouth_angle, fill=(255, 255, 0))
        
        # Eye (if mouth is open wide, maybe hide it, but classic pacman has no eye often, let's add a small black dot for personality)
        # Position depends on rotation
        eye_rad = 2
        eye_offset_x = 0
        eye_offset_y = 0
        
        if direction == "right": eye_offset_x, eye_offset_y = 16, 8
        elif direction == "left": eye_offset_x, eye_offset_y = 16, 8
        elif direction == "up": eye_offset_x, eye_offset_y = 8, 16 
        elif direction == "down": eye_offset_x, eye_offset_y = 24, 16 
        
        if direction in ["right", "up"]: # Top/Right side eye
             draw.ellipse([px+eye_offset_x-eye_rad, py+eye_offset_y-eye_rad, px+eye_offset_x+eye_rad, py+eye_offset_y+eye_rad], fill=(0, 0, 0))
        elif direction == "left": # Need to mirror
             draw.ellipse([px+(32-eye_offset_x)-eye_rad, py+eye_offset_y-eye_rad, px+(32-eye_offset_x)+eye_rad, py+eye_offset_y+eye_rad], fill=(0, 0, 0))
        elif direction == "down":
             draw.ellipse([px+eye_offset_x-eye_rad, py+(32-eye_offset_y)-eye_rad, px+eye_offset_x+eye_rad, py+(32-eye_offset_y)+eye_rad], fill=(0, 0, 0))


        # Game Over Overlay
        if self.state in ["game_over", "win"]:
            # Darkened overlay
            overlay = Image.new('RGBA', (w, h), (0, 0, 0, 180))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Text
            text = "GAME OVER" if self.state == "game_over" else "YOU WIN!"
            color = (255, 50, 50) if self.state == "game_over" else (50, 255, 50)
            
            # Simple centering (not perfect without font metrics but works)
            draw.text((w//2 - 30, h//2 - 10), text, fill=color)
            draw.text((w//2 - 40, h//2 + 10), f"Final Score: {self.score}", fill=(255, 255, 255))

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class BombDefuseGame:
    """Arcade Bomb Defuse Visual Logic"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.state = "playing" # playing, win, game_over
        self.wires = [] # List of {"color": "red", "cut": False}
        self.serial = ""
        self.batteries = 0
        self.correct_index = -1 
        self.logic_text = ""
        
        self.generate_puzzle()

    def generate_puzzle(self):
        # 1. Generate Environment
        colors_pool = ["red", "blue", "white", "yellow", "black"]
        num_wires = random.randint(3, 6)
        self.wires = [{"color": random.choice(colors_pool), "cut": False} for _ in range(num_wires)]
        
        self.serial = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
        # Ensure last digit is a number for Odd/Even logic sometimes, or handle it
        if not self.serial[-1].isdigit():
             self.serial = self.serial[:-1] + str(random.randint(0, 9))
             
        self.batteries = random.randint(0, 5)
        
        # 2. Determine Solution (Simple Wires Logic)
        colors = [w["color"] for w in self.wires]
        last_digit_odd = int(self.serial[-1]) % 2 != 0
        
        rule_desc = "Unknown"
        target = -1
        
        if num_wires == 3:
            if "red" not in colors:
                target = 1 # Second wire
                rule_desc = "No red wires -> Cut second wire"
            elif colors[-1] == "white":
                target = 2 # Last wire
                rule_desc = "Last wire is white -> Cut last wire"
            elif colors.count("blue") > 1:
                # Last blue wire
                idx = -1
                for i in range(2, -1, -1):
                    if colors[i] == "blue": idx = i; break
                target = idx
                rule_desc = ">1 blue wires -> Cut last blue wire"
            else:
                target = 2 # Last wire
                rule_desc = "Otherwise -> Cut last wire"

        elif num_wires == 4:
            if colors.count("red") > 1 and last_digit_odd:
                # Last red wire
                idx = -1
                for i in range(3, -1, -1):
                    if colors[i] == "red": idx = i; break
                target = idx
                rule_desc = ">1 red wires & odd serial -> Cut last red wire"
            elif colors[-1] == "yellow" and "red" not in colors:
                target = 0 # First wire
                rule_desc = "Last wire yellow & no red -> Cut first wire"
            elif colors.count("blue") == 1:
                target = 0 # First wire
                rule_desc = "Exactly 1 blue wire -> Cut first wire"
            elif colors.count("yellow") > 1:
                target = 3 # Last wire
                rule_desc = ">1 yellow wires -> Cut last wire"
            else:
                target = 1 # Second wire
                rule_desc = "Otherwise -> Cut second wire"

        elif num_wires == 5:
            if colors[-1] == "black" and last_digit_odd:
                target = 3 # Fourth wire
                rule_desc = "Last wire black & odd serial -> Cut fourth wire"
            elif colors.count("red") == 1 and colors.count("yellow") > 1:
                target = 0 # First wire
                rule_desc = "1 red wire & >1 yellow -> Cut first wire"
            elif "black" not in colors:
                target = 1 # Second wire
                rule_desc = "No black wires -> Cut second wire"
            else:
                target = 0 # First wire
                rule_desc = "Otherwise -> Cut first wire"
                
        elif num_wires == 6:
            if "yellow" not in colors and last_digit_odd:
                target = 2 # Third wire
                rule_desc = "No yellow & odd serial -> Cut third wire"
            elif colors.count("yellow") == 1 and colors.count("white") > 1:
                target = 3 # Fourth wire
                rule_desc = "1 yellow & >1 white -> Cut fourth wire"
            elif "red" not in colors:
                target = 5 # Last wire
                rule_desc = "No red wires -> Cut last wire"
            else:
                target = 3 # Fourth wire
                rule_desc = "Otherwise -> Cut fourth wire"
        
        self.correct_index = target
        self.logic_text = rule_desc # Store for debug or post-game

    def cut(self, index):
        if self.state != "playing": return
        if self.wires[index]["cut"]: return # Already cut
        
        self.wires[index]["cut"] = True
        
        if index == self.correct_index:
            self.state = "win"
        else:
            self.state = "game_over"

    def render(self):
        w, h = 600, 400
        img = Image.new('RGB', (w, h), color=(40, 40, 45))
        draw = ImageDraw.Draw(img)
        
        # Panel Bevel
        draw.rectangle([5, 5, w-5, h-5], outline=(100, 100, 100), width=3)
        draw.rectangle([15, 15, w-15, h-15], fill=(30, 30, 30))
        
        # --- Top Section: Indicators ---
        
        # Serial Number (Sticker)
        draw.rectangle([40, 40, 190, 90], fill=(230, 230, 230))
        draw.text((50, 45), "SERIAL #", fill=(0,0,0))
        draw.text((50, 60), f"{self.serial}", fill=(0,0,0)) # Simulating bold by printing twice? No, plain is fine
        
        # Batteries
        bat_x = 220
        for i in range(min(self.batteries, 4)):
            draw.rectangle([bat_x, 50, bat_x+20, 80], fill=(10, 10, 10), outline=(200, 200, 200)) # Body
            draw.rectangle([bat_x+5, 45, bat_x+15, 50], fill=(150, 150, 150)) # Hub
            bat_x += 30
        if self.batteries > 4:
            draw.text((bat_x, 60), f"+{self.batteries-4}", fill=(255, 255, 255))
            
        # Timer Display
        draw.rectangle([430, 40, 560, 90], fill=(0, 0, 0), outline=(60, 60, 60), width=2)
        status_text = "00:45"
        text_col = (255, 0, 0)
        
        if self.state == "game_over": 
            status_text = "BOOM"
        elif self.state == "win":
            status_text = "SAFE"
            text_col = (0, 255, 0)
            
        # Draw "Segments" (roughly center)
        draw.text((455, 55), status_text, fill=text_col)
        
        # Status Light
        led_col = (50, 0, 0) # Off red
        if self.state == "game_over": led_col = (255, 0, 0) # Bright Red
        elif self.state == "win": led_col = (0, 255, 0) # Bright Green
        
        draw.ellipse([530, 50, 550, 70], fill=led_col, outline=(100, 100, 100))
        
        # --- Middle Section: Wires ---
        # Draw "sockets" on left and right
        num_w = len(self.wires)
        
        y_start = 130
        y_end = 350
        spacing = (y_end - y_start) // (num_w)
        
        c_map = {
            "red": (200, 20, 20),
            "blue": (20, 20, 200),
            "yellow": (200, 200, 20),
            "white": (240, 240, 240),
            "black": (10, 10, 10)
        }
        
        for i, wire in enumerate(self.wires):
            y = y_start + (i * spacing) + (spacing//2)
            col = c_map.get(wire["color"], (128, 128, 128))
            
            # Left Socket
            draw.rectangle([50, y-10, 80, y+10], fill=(20, 20, 20), outline=(100, 100, 100))
            draw.text((30, y-8), f"{i+1}", fill=(255, 255, 255))
            
            # Right Socket
            draw.rectangle([520, y-10, 550, y+10], fill=(20, 20, 20), outline=(100, 100, 100))
            
            # Wire
            if wire["cut"]:
                # Cut wire - two loose ends
                draw.line([(80, y), (250, y)], fill=col, width=10)
                draw.ellipse([245, y-5, 255, y+5], fill=(184, 115, 51)) # Copper
                
                draw.line([(350, y), (520, y)], fill=col, width=10)
                draw.ellipse([345, y-5, 355, y+5], fill=(184, 115, 51)) # Copper
                
                # Scorch marks?
            else:
                # Full Wire (Arc slightly?)
                # Just straight for now for clean look, maybe slight bezier if I had time
                draw.line([(80, y), (520, y)], fill=col, width=10)
                # Highlight
                draw.line([(80, y-2), (520, y-2)], fill=(255, 255, 255, 80), width=2)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class BombDefuseView(discord.ui.View):
    def __init__(self, game, interaction, cog):
        super().__init__(timeout=180)
        self.game = game
        self.original_interaction = interaction
        self.cog = cog
        self.message = None
        
        # Add wire buttons dynamically
        for i in range(len(game.wires)):
             # Create button for each wire
             btn = discord.ui.Button(label=f"✂️ {i+1}", style=discord.ButtonStyle.secondary, custom_id=f"cut_{i}", row=0 if i < 3 else 1)
             btn.callback = self.make_callback(i)
             self.add_item(btn)

    def make_callback(self, index):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.game.user_id:
                return
            
            self.game.cut(index)
            await self.update_board(interaction)
        return callback

    @discord.ui.button(label="🔄 Restart", style=discord.ButtonStyle.primary, row=2)
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.user_id: return
        await self.cog.start_bomb(interaction)

    @discord.ui.button(label="🏠 Menu", style=discord.ButtonStyle.secondary, row=2)
    async def menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_arcade_menu(interaction)

    async def update_board(self, interaction=None):
        file = discord.File(self.game.render(), filename="bomb.png")
        
        if self.game.state == "win":
            reward = 300
            desc = f"✅ **BOMB DEFUSED!**\n\nThe correct wire was cut. Good job!\n**+{reward} PsyCoins** 🪙"
            color = discord.Color.green()
            
            # Disable buttons
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id and item.custom_id.startswith("cut_"):
                    item.disabled = True
            
            if _arc_mg:
                 try:
                     _arc_mg(self.game.user_id, 'bombdefuse', 'win', reward)
                     _arc_inc(self.game.user_id, 'arcade_wins')
                 except Exception: pass
            
        elif self.game.state == "game_over":
            desc = f"💥 **BOOM!**\n\nYou cut the wrong wire! The bomb exploded.\n\n**Solution Logic:**\n{self.game.logic_text}"
            color = discord.Color.dark_red()
            
            # Disable buttons
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id and item.custom_id.startswith("cut_"):
                    item.disabled = True
                    if item.custom_id == f"cut_{self.game.correct_index}":
                        item.style = discord.ButtonStyle.success # Highlight correct one
            
            if _arc_mg:
                 try:
                     _arc_mg(self.game.user_id, 'bombdefuse', 'loss', 0)
                 except Exception: pass
        else:
            desc = (
                "**LOGIC PUZZLE - MANUAL**\n"
                "Follow these rules based on the bomb configuration:\n\n"
            )
            # Add rules manual
            desc += "**3 Wires:**\n- No Red: Cut 2nd\n- Last is White: Cut Last\n- >1 Blue: Cut Last Blue\n- Else: Cut Last\n\n"
            desc += "**4 Wires:**\n- >1 Red & Odd Serial: Cut Last Red\n- Last Yellow & No Red: Cut 1st\n- 1 Blue: Cut 1st\n- >1 Yellow: Cut Last\n- Else: Cut 2nd\n\n"
            desc += "**5 Wires:**\n- Last Black & Odd Serial: Cut 4th\n- 1 Red & >1 Yellow: Cut 1st\n- No Black: Cut 2nd\n- Else: Cut 1st\n\n"
            desc += "**6 Wires:**\n- No Yellow & Odd Serial: Cut 3rd\n- 1 Yellow & >1 White: Cut 4th\n- No Red: Cut Last\n- Else: Cut 4th"
            
            color = discord.Color.gold()

        embed = discord.Embed(title="💣 Bomb Defusal", description=desc, color=color)
        embed.set_image(url="attachment://bomb.png")
        
        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        else:
            await self.original_interaction.response.send_message(embed=embed, file=file, view=self)
            self.message = await self.original_interaction.original_response()

class MainArcadeMenu(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="👻 PacMan", style=discord.ButtonStyle.primary, row=0)
    async def pacman(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.start_pacman(interaction)

    @discord.ui.button(label="💣 Bomb Defuse", style=discord.ButtonStyle.danger, row=0)
    async def bomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.start_bomb(interaction)

    @discord.ui.button(label="🐍 Snake", style=discord.ButtonStyle.success, row=1)
    async def snake(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🐍 Snake is coming soon!", ephemeral=True)

    @discord.ui.button(label="🧱 Tetris", style=discord.ButtonStyle.primary, row=1)
    async def tetris(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🧱 Tetris is coming soon!", ephemeral=True)

    @discord.ui.button(label="👾 Space Invaders", style=discord.ButtonStyle.secondary, row=2)
    async def space(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👾 Space Invaders is coming soon!", ephemeral=True)
        
    @discord.ui.button(label="🏓 Pong", style=discord.ButtonStyle.secondary, row=2)
    async def pong(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🏓 Pong is coming soon!", ephemeral=True)


class PacManView(discord.ui.View):
    def __init__(self, game, interaction, cog):
        super().__init__(timeout=120)
        self.game = game
        self.original_interaction = interaction
        self.cog = cog
        self.message = None
    
    async def update_board(self, interaction=None):
        file = discord.File(self.game.render(), filename="pacman.png")
        desc = f"Score: {self.game.score} | Lives: {'❤️'*self.game.lives}"
        
        if self.game.state == "win":
            desc += "\n\n🎉 **WINNER!**"
        elif self.game.state == "game_over":
            desc += "\n\n💀 **GAME OVER**"
            
        embed = discord.Embed(title="🕹️ PacMan Arcade", description=desc, color=discord.Color.yellow())
        embed.set_image(url="attachment://pacman.png")
        embed.set_footer(text="Use the buttons below to play!")
        
        if self.game.state != "playing":
            # Update buttons for game over state
            self.clear_items()
            self.add_item(discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.success, custom_id="restart"))
            self.add_item(discord.ui.Button(label="🏠 Menu", style=discord.ButtonStyle.secondary, custom_id="menu"))
            
            # handle rewards logic (omitted for brevity, copied from previous)
            if self.game.state == "win":
                reward = self.game.score * 2
                if _arc_mg:
                    try:
                        _arc_mg(self.game.user_id, 'pacman', 'win', reward)
                        _arc_inc(self.game.user_id, 'arcade_wins')
                    except Exception:
                        pass
                embed.description += f"\n**+{reward} PsyCoins!** 🪙"
            
        
        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        else: # Initial send
            await self.original_interaction.response.send_message(embed=embed, file=file, view=self)
            self.message = await self.original_interaction.original_response()

    # Row 0: Restart, Up, Menu
    @discord.ui.button(label="🔄 Restart", style=discord.ButtonStyle.secondary, row=0)
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restart game with same user
        await self.cog.start_pacman(interaction, is_retry=True)

    @discord.ui.button(label="⬆️", style=discord.ButtonStyle.primary, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.move_player("up")
        await self.update_board(interaction)

    @discord.ui.button(label="🏠 Menu", style=discord.ButtonStyle.secondary, row=0)
    async def menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_arcade_menu(interaction)

    # Row 1: Left, Down, Right
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, row=1)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.move_player("left")
        await self.update_board(interaction)

    @discord.ui.button(label="⬇️", style=discord.ButtonStyle.primary, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.move_player("down")
        await self.update_board(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, row=1)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.move_player("right")
        await self.update_board(interaction)
    
    # Custom handler for dynamic buttons added in game over
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return False
            
        custom_id = interaction.data.get("custom_id")
        if custom_id == "restart":
            await self.cog.start_pacman(interaction, is_retry=True)
            return False # Stop processing
        elif custom_id == "menu":
            await self.cog.show_arcade_menu(interaction)
            return False
            
        return True

class ArcadeGames(commands.Cog):
    """Arcade-style games"""

    @app_commands.command(name="arcadehelp", description="View all arcade game commands and info (paginated)")
    async def arcadehelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Arcade Games"
        category_desc = "Play fast-paced arcade games! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
    
    @app_commands.command(name="arcade", description="Arcade games menu")
    async def arcade_command(self, interaction: discord.Interaction):
        """Unified arcade command"""
        await self.show_arcade_menu(interaction)
        
    async def show_arcade_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🕹️ LUDUS ARCADE",
            description="Welcome to the arcade! Insert coin to play.",
            color=discord.Color.from_rgb(255, 0, 255)
        )
        embed.set_image(url="https://media.discordapp.net/attachments/900000000000000000/111111111111111111/arcade_banner_placeholder.png?width=800&height=200") # Placeholder or remove if no image
        # Actually let's just use a nice text art or nothing for now to avoid broken links
        embed.set_image(url=None) 
        embed.add_field(name="Available Games", value="""
👻 **PacMan** - Classic arcade action
💣 **Bomb Defuse** - Cut the right wire!
🐍 **Snake** - Grow your snake (Soon)
🧱 **Tetris** - Stack blocks (Soon)
👾 **Space Invaders** - Defend Earth (Soon)
🏓 **Pong** - Retro tennis (Soon)
""", inline=False)
        
        view = MainArcadeMenu(self)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    async def start_pacman(self, interaction: discord.Interaction, is_retry=False):
        """PacMan game - Procedurally Generated"""
        game = PacManGame(interaction.user.id)
        view = PacManView(game, interaction, self)
        
        # If it's a retry/restart/menu navigation, we might need to edit or send new
        # But PacManView handles its own initial send/update logic mostly
        # We just need to trigger the initial update_board
        if is_retry:
             # For restart, we likely want to edit the existing message if possible or send new
             # PacManView.update_board handles interaction logic
             await view.update_board(interaction)
        else:
             # Fresh start from menu
             await view.update_board(interaction)
        
        # Track statistics if available
        if _arc_inc:
            try:
                _arc_inc(interaction.user.id, 'arcade_played')
            except Exception:
                pass

    async def start_  (self, interaction: discord.Interaction):
        """Bomb defuser game - New Visual Version"""
        game = BombDefuseGame(interaction.user.id)
        view = BombDefuseView(game, interaction, self)
        
        # Initial render/send
        await view.update_board(interaction)
        
        # Track statistics if available
        if _arc_inc:
            try:
                _arc_inc(interaction.user.id, 'arcade_played')
            except Exception:
                pass


    async def arcade_snake_action(self, interaction: discord.Interaction):
        """Snake game (Placeholder)"""
        embed = discord.Embed(
            title="🐍 Snake (Coming Soon!)",
            description="This game is currently under development. Check back later!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def arcade_tetris_action(self, interaction: discord.Interaction):
        """Tetris game (Placeholder)"""
        embed = discord.Embed(
            title="🧱 Tetris (Coming Soon!)",
            description="This game is currently under development. Check back later!",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def arcade_space_invaders_action(self, interaction: discord.Interaction):
        """Space Invaders game (Placeholder)"""
        embed = discord.Embed(
            title="👾 Space Invaders (Coming Soon!)",
            description="This game is currently under development. Check back later!",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def arcade_pong_action(self, interaction: discord.Interaction):
        """Pong game (Placeholder)"""
        embed = discord.Embed(
            title="🏓 Pong (Coming Soon!)",
            description="This game is currently under development. Check back later!",
            color=discord.Color.dark_grey()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ArcadeGames(bot))
