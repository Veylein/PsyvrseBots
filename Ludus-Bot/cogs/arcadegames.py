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

class SnakeGame:
    """Classic Snake Game"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.width = 15
        self.height = 15
        self.block_size = 32
        
        # Start in middle
        self.snake = [(7, 7), (7, 8), (7, 9)] # Head, Body, Tail
        self.direction = "up" # up, down, left, right
        self.food = (5, 5) # Temp init
        self.spawn_food()
        self.score = 0
        self.state = "playing" # playing, game_over, win

    def spawn_food(self):
        while True:
            x, y = random.randint(0, self.width-1), random.randint(0, self.height-1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break

    def move(self, direction):
        if self.state != "playing": return
        
        # Prevent 180 turns
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        if opposites.get(direction) == self.direction:
             # Ignore 180 turn, keep current direction? 
             # Or just ignore input. Let's effectively ignore input but we must advance?
             # Actually classic snake advances automatically. Here user forces advance.
             # So if user presses Down while going Up, we should probably ignore it OR Game Over?
             # Standard is ignore. So we use self.direction
             pass
        else:
            self.direction = direction
        
        # Calculate new head
        head_x, head_y = self.snake[0]
        dx, dy = 0, 0
        if self.direction == "up": dy = -1
        elif self.direction == "down": dy = 1
        elif self.direction == "left": dx = -1
        elif self.direction == "right": dx = 1
        
        new_head = (head_x + dx, head_y + dy)
        
        # Check collisions logic
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.state = "game_over"
            return
            
        if new_head in self.snake[:-1]: 
            self.state = "game_over"
            return
            
        self.snake.insert(0, new_head)
        
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
            if len(self.snake) >= self.width * self.height:
                self.state = "win"
        else:
            self.snake.pop()

    def render(self):
        w, h = self.width * self.block_size, self.height * self.block_size
        img = Image.new('RGB', (w, h), color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
        
        # Draw Border
        draw.rectangle([0, 0, w-1, h-1], outline=(50, 50, 50), width=1)

        # Draw Food
        fx, fy = self.food[0] * self.block_size, self.food[1] * self.block_size
        draw.ellipse([fx+4, fy+4, fx+28, fy+28], fill=(255, 50, 50))
        
        # Draw Snake
        for idx, (x, y) in enumerate(self.snake):
            sx, sy = x * self.block_size, y * self.block_size
            rect = [sx+1, sy+1, sx+31, sy+31]
            color = (50, 255, 50) if idx == 0 else (0, 200, 0) # Head brighter
            draw.rectangle(rect, fill=color)
            
            # Eyes on head
            if idx == 0:
                eye_color = (0, 0, 0)
                if self.direction == "up":
                    draw.rectangle([sx+6, sy+6, sx+10, sy+10], fill=eye_color)
                    draw.rectangle([sx+22, sy+6, sx+26, sy+10], fill=eye_color)
                elif self.direction == "down":
                    draw.rectangle([sx+6, sy+22, sx+10, sy+26], fill=eye_color)
                    draw.rectangle([sx+22, sy+22, sx+26, sy+26], fill=eye_color)
                elif self.direction == "left":
                    draw.rectangle([sx+6, sy+6, sx+10, sy+10], fill=eye_color)
                    draw.rectangle([sx+6, sy+22, sx+10, sy+26], fill=eye_color)
                elif self.direction == "right":
                    draw.rectangle([sx+22, sy+6, sx+26, sy+10], fill=eye_color)
                    draw.rectangle([sx+22, sy+22, sx+26, sy+26], fill=eye_color)

        # Game Over Overlay
        if self.state != "playing":
            overlay = Image.new('RGBA', (w, h), (0, 0, 0, 180))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")
            draw = ImageDraw.Draw(img)
            text = "GAME OVER" if self.state == "game_over" else "YOU WIN!"
            color = (255, 50, 50) if self.state == "game_over" else (50, 255, 50)
            # Centering roughly
            draw.text((w//2 - 40, h//2 - 10), text, fill=color)
            draw.text((w//2 - 50, h//2 + 10), f"Score: {self.score}", fill=(255, 255, 255))
            
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class SnakeView(discord.ui.View):
    def __init__(self, game, interaction, cog):
        super().__init__(timeout=120)
        self.game = game
        self.original_interaction = interaction
        self.cog = cog
        self.message = None

    async def update_board(self, interaction=None):
        file = discord.File(self.game.render(), filename="snake.png")
        desc = f"Score: {self.game.score} | Length: {len(self.game.snake)}"
        color = discord.Color.green()
        
        if self.game.state != "playing":
             if self.game.state == "win":
                 desc += "\n**YOU WON!**"
                 reward = 500
             else:
                 desc += "\n**GAME OVER**"
                 reward = self.game.score // 2 
                 color = discord.Color.red()
             
             # Stats
             if _arc_mg:
                 try:
                     _arc_mg(self.game.user_id, 'snake', 'win' if self.game.state == 'win' else 'loss', reward)
                     if self.game.state == 'win': _arc_inc(self.game.user_id, 'arcade_wins')
                 except Exception: pass
            
             self.clear_items()
             b_restart = discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.success, custom_id="restart")
             b_restart.callback = self.restart_callback
             self.add_item(b_restart)
             
             b_menu = discord.ui.Button(label="🏠 Menu", style=discord.ButtonStyle.secondary, custom_id="menu")
             b_menu.callback = self.menu_callback
             self.add_item(b_menu)

             desc += f"\n**+{reward} PsyCoins** 🪙"

        embed = discord.Embed(title="🐍 Snake Arcade", description=desc, color=color)
        embed.set_image(url="attachment://snake.png")
        
        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        else:
            await self.original_interaction.response.send_message(embed=embed, file=file, view=self)
            self.message = await self.original_interaction.original_response()

    async def check_auth(self, interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return False
        return True

    async def restart_callback(self, interaction):
        if not await self.check_auth(interaction): return
        await self.cog.start_snake(interaction)

    async def menu_callback(self, interaction):
        if not await self.check_auth(interaction): return
        await self.cog.show_arcade_menu(interaction)

    @discord.ui.button(label="⬆️", style=discord.ButtonStyle.primary, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move("up")
        await self.update_board(interaction)

    @discord.ui.button(label="⬇️", style=discord.ButtonStyle.primary, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move("down")
        await self.update_board(interaction)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, row=1)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move("left")
        await self.update_board(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, row=1)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move("right")
        await self.update_board(interaction)

class TetrisGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.width = 10
        self.height = 20
        self.block_size = 24
        self.grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.score = 0
        self.state = "playing"
        
        self.shapes = [
            [[1, 1, 1, 1]], # I
            [[1, 1], [1, 1]], # O
            [[0, 1, 0], [1, 1, 1]], # T
            [[1, 0, 0], [1, 1, 1]], # L
            [[0, 0, 1], [1, 1, 1]], # J
            [[0, 1, 1], [1, 1, 0]], # S
            [[1, 1, 0], [0, 1, 1]]  # Z
        ]
        self.colors = [
            (0, 255, 255), (255, 255, 0), (128, 0, 128), 
            (255, 165, 0), (0, 0, 255), (0, 255, 0), (255, 0, 0)
        ]
        
        self.current_piece = self.new_piece()
        self.piece_x = 3
        self.piece_y = 0

    def new_piece(self):
        shape = random.choice(self.shapes)
        color = self.colors[self.shapes.index(shape)]
        return {"shape": shape, "color": color}

    def check_collision(self, dx=0, dy=0, shape=None):
        if shape is None: shape = self.current_piece["shape"]
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    nx, ny = self.piece_x + x + dx, self.piece_y + y + dy
                    if nx < 0 or nx >= self.width or ny >= self.height:
                        return True
                    if ny >= 0 and self.grid[ny][nx]:
                        return True
        return False

    def merge_piece(self):
        for y, row in enumerate(self.current_piece["shape"]):
            for x, cell in enumerate(row):
                if cell:
                    if self.piece_y + y >= 0:
                        self.grid[self.piece_y + y][self.piece_x + x] = self.current_piece["color"]
        self.clear_lines()
        self.current_piece = self.new_piece()
        self.piece_x = 3
        self.piece_y = 0
        if self.check_collision():
            self.state = "game_over"

    def clear_lines(self):
        lines_to_clear = [i for i, row in enumerate(self.grid) if all(row)]
        for i in lines_to_clear:
            del self.grid[i]
            self.grid.insert(0, [0 for _ in range(self.width)])
            self.score += 100 * len(lines_to_clear) # Standard scoring is better but simple for now

    def rotate_piece(self):
        shape = self.current_piece["shape"]
        # Rotate matrix
        new_shape = [list(row) for row in zip(*shape[::-1])]
        if not self.check_collision(shape=new_shape):
            self.current_piece["shape"] = new_shape

    def move(self, dx, dy):
        if not self.check_collision(dx, dy):
            self.piece_x += dx
            self.piece_y += dy
            return True
        elif dy > 0: # Hit bottom or stack
            self.merge_piece()
            return False
        return False

    def drop(self):
        while self.move(0, 1): pass

    def render(self):
        w, h = self.width * self.block_size, self.height * self.block_size
        img = Image.new('RGB', (w + 100, h), color=(20, 20, 30)) # Extra width for UI
        draw = ImageDraw.Draw(img)
        
        # Grid area
        draw.rectangle([0, 0, w, h], fill=(0, 0, 0))
        
        # Draw Stack
        for y, row in enumerate(self.grid):
            for x, val in enumerate(row):
                if val:
                    rx, ry = x * self.block_size, y * self.block_size
                    draw.rectangle([rx+1, ry+1, rx+self.block_size-1, ry+self.block_size-1], fill=val)
        
        # Draw Current Piece
        if self.state == "playing":
            for y, row in enumerate(self.current_piece["shape"]):
                for x, val in enumerate(row):
                    if val:
                        rx, ry = (self.piece_x + x) * self.block_size, (self.piece_y + y) * self.block_size
                        if ry >= 0:
                            draw.rectangle([rx+1, ry+1, rx+self.block_size-1, ry+self.block_size-1], fill=self.current_piece["color"])
        
        # UI
        draw.text((w + 10, 20), "SCORE", fill=(200, 200, 200))
        draw.text((w + 10, 40), str(self.score), fill=(255, 255, 255))
        
        if self.state == "game_over":
             draw.text((w + 10, 100), "GAME", fill=(255, 50, 50))
             draw.text((w + 10, 120), "OVER", fill=(255, 50, 50))

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class TetrisView(discord.ui.View):
    def __init__(self, game, interaction, cog):
        super().__init__(timeout=180)
        self.game = game
        self.original_interaction = interaction
        self.cog = cog
        self.message = None

    async def update_board(self, interaction=None):
        file = discord.File(self.game.render(), filename="tetris.png")
        desc = f"Score: {self.game.score}"
        
        if self.game.state == "game_over":
             desc += "\n**GAME OVER**"
             self.clear_items()
             b_restart = discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.success, custom_id="restart")
             b_restart.callback = self.restart_callback
             self.add_item(b_restart)
             b_menu = discord.ui.Button(label="🏠 Menu", style=discord.ButtonStyle.secondary, custom_id="menu")
             b_menu.callback = self.menu_callback
             self.add_item(b_menu)
             
             if _arc_mg:
                 try:
                     _arc_mg(self.game.user_id, 'tetris', 'loss', self.game.score)
                 except Exception: pass

        embed = discord.Embed(title="🧱 Tetris Arcade", description=desc, color=discord.Color.blue())
        embed.set_image(url="attachment://tetris.png")
        
        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        else:
            await self.original_interaction.response.send_message(embed=embed, file=file, view=self)
            self.message = await self.original_interaction.original_response()

    async def check_auth(self, interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return False
        return True

    async def restart_callback(self, interaction):
        if not await self.check_auth(interaction): return
        await self.cog.start_tetris(interaction)

    async def menu_callback(self, interaction):
        if not await self.check_auth(interaction): return
        await self.cog.show_arcade_menu(interaction)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, row=0)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move(-1, 0)
        # Auto fall 1 step per move? Maybe not, allow positioning
        # But games need progress. Let's make Down the progress.
        await self.update_board(interaction)

    @discord.ui.button(label="⬇️", style=discord.ButtonStyle.primary, row=0)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move(0, 1)
        await self.update_board(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, row=0)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move(1, 0)
        await self.update_board(interaction)

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def rotate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.rotate_piece()
        await self.update_board(interaction)

    @discord.ui.button(label="⏬", style=discord.ButtonStyle.danger, row=1)
    async def drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.drop()
        await self.update_board(interaction)

class SpaceInvadersGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.width = 15
        self.height = 12
        self.block_size = 24
        
        self.player_x = self.width // 2
        self.bullets = [] # List of {"x": x, "y": y, "dir": -1 (up) or 1 (down)}
        self.aliens = [] # List of {"x": x, "y": y}
        
        self.score = 0
        self.state = "playing"
        self.level = 1
        self.alien_direction = 1 # 1 for right, -1 for left
        
        self.spawn_aliens()

    def spawn_aliens(self):
        self.aliens = []
        rows = 3
        cols = 8
        start_x = (self.width - cols) // 2
        for r in range(rows):
            for c in range(cols):
                self.aliens.append({"x": start_x + c, "y": r + 1})

    def move_player(self, dx):
        self.player_x = max(0, min(self.width - 1, self.player_x + dx))
        self.update_game_state() # Advance game on player move? Or just move player?
        # Turn based: Player moves, Aliens move?
        # Let's say: Player action -> Aliens Move -> Resolve
        
    def shoot(self):
        # Only 1 bullet at a time? Or multiple?
        # Let's say max 2 player bullets
        p_bullets = [b for b in self.bullets if b["dir"] == -1]
        if len(p_bullets) < 2:
            self.bullets.append({"x": self.player_x, "y": self.height - 2, "dir": -1})
        self.update_game_state()

    def update_game_state(self):
        # 1. Move Bullets
        for b in self.bullets[:]:
            b["y"] += b["dir"]
            # Out of bounds
            if b["y"] < 0 or b["y"] >= self.height:
                self.bullets.remove(b)
        
        # 2. Check Bullet Collisions
        for b in self.bullets[:]:
            if b["dir"] == -1: # Player bullet
                # Check hit alien
                hit = False
                for alien in self.aliens[:]:
                    if b["x"] == alien["x"] and b["y"] == alien["y"]:
                        self.aliens.remove(alien)
                        self.score += 50
                        hit = True
                        break
                if hit and b in self.bullets: self.bullets.remove(b)
            
            # TODO: Alien bullets hitting player
        
        # 3. Move Aliens
        # Move periodically based on level speed
        if random.random() < 0.4 + (self.level * 0.05):
            should_move_down = False
            next_dir = self.alien_direction
            
            # Check edge collision
            for a in self.aliens:
                next_x = a["x"] + self.alien_direction
                if next_x < 0 or next_x >= self.width:
                    should_move_down = True
                    next_dir = -self.alien_direction
                    break
            
            if should_move_down:
                for a in self.aliens:
                    a["y"] += 1
                    if a["y"] >= self.height - 1:
                        self.state = "game_over"
                self.alien_direction = next_dir
            else:
                for a in self.aliens:
                    a["x"] += self.alien_direction
        
        # 4. Alien Shoot
        # Random alien shoots
        if random.random() < 0.2:
             # Pick random bottom alien
             if self.aliens:
                 shooter = random.choice(self.aliens)
                 self.bullets.append({"x": shooter["x"], "y": shooter["y"] + 1, "dir": 1})
        
        # 5. Check Player Hit
        for b in self.bullets:
            if b["dir"] == 1:
                if b["x"] == self.player_x and b["y"] == self.height - 1:
                    self.state = "game_over"

        # 6. Check Win (No aliens)
        if not self.aliens:
            self.level += 1
            self.score += 1000
            self.spawn_aliens()

    def render(self):
        w, h = self.width * self.block_size, self.height * self.block_size
        img = Image.new('RGB', (w, h), color=(10, 10, 20))
        draw = ImageDraw.Draw(img)
        
        # Draw Player
        px, py = self.player_x * self.block_size, (self.height - 1) * self.block_size
        draw.polygon([(px+12, py), (px+4, py+20), (px+20, py+20)], fill=(50, 255, 50))
        
        # Draw Aliens
        for a in self.aliens:
            ax, ay = a["x"] * self.block_size, a["y"] * self.block_size
            draw.rectangle([ax+4, ay+4, ax+20, ay+20], fill=(255, 50, 50))
            # Eyes
            draw.point((ax+8, ay+8), fill=(0,0,0))
            draw.point((ax+16, ay+8), fill=(0,0,0))
            
        # Draw Bullets
        for b in self.bullets:
            bx, by = b["x"] * self.block_size, b["y"] * self.block_size
            color = (255, 255, 0) if b["dir"] == -1 else (255, 100, 100)
            draw.rectangle([bx+10, by+6, bx+14, by+18], fill=color)

        if self.state == "game_over":
             # draw game over
             draw.text((w//2-30, h//2), "GAME OVER", fill=(255, 255, 255))
             
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class SpaceInvadersView(discord.ui.View):
    def __init__(self, game, interaction, cog):
        super().__init__(timeout=120)
        self.game = game
        self.original_interaction = interaction
        self.cog = cog
        self.message = None

    async def update_board(self, interaction=None):
        file = discord.File(self.game.render(), filename="invaders.png")
        desc = f"Score: {self.game.score} | Level: {self.game.level}"
        
        if self.game.state == "game_over":
             desc += "\n**GAME OVER**"
             self.clear_items()
             b_restart = discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.success, custom_id="restart")
             b_restart.callback = self.restart_callback
             self.add_item(b_restart)
             b_menu = discord.ui.Button(label="🏠 Menu", style=discord.ButtonStyle.secondary, custom_id="menu")
             b_menu.callback = self.menu_callback
             self.add_item(b_menu)
             
             if _arc_mg:
                 try:
                     _arc_mg(self.game.user_id, 'invaders', 'loss', self.game.score)
                 except Exception: pass

        embed = discord.Embed(title="👾 Space Invaders Arcade", description=desc, color=discord.Color.dark_blue())
        embed.set_image(url="attachment://invaders.png")
        
        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        else:
            await self.original_interaction.response.send_message(embed=embed, file=file, view=self)
            self.message = await self.original_interaction.original_response()

    async def check_auth(self, interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return False
        return True
    
    async def restart_callback(self, interaction):
         if not await self.check_auth(interaction): return
         await self.cog.start_invaders(interaction)

    async def menu_callback(self, interaction):
         if not await self.check_auth(interaction): return
         await self.cog.show_arcade_menu(interaction)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, row=0)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move_player(-1)
        await self.update_board(interaction)

    @discord.ui.button(label="🔫 SHOOT", style=discord.ButtonStyle.danger, row=0)
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.shoot()
        await self.update_board(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, row=0)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move_player(1)
        await self.update_board(interaction)

class PongGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.width = 600
        self.height = 400
        self.paddle_h = 60
        self.paddle_w = 10
        self.ball_size = 10
        
        self.p1_y = self.height // 2 - self.paddle_h // 2
        self.ai_y = self.height // 2 - self.paddle_h // 2
        
        self.ball_x = self.width // 2
        self.ball_y = self.height // 2
        self.ball_dx = 15 # Speed
        self.ball_dy = random.choice([-10, 10])
        
        self.score_p1 = 0
        self.score_ai = 0
        self.state = "playing"

    def move_player(self, dy):
        self.p1_y = max(0, min(self.height - self.paddle_h, self.p1_y + dy))
        self.update_game()

    def update_game(self):
        # Move Ball
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        # Wall Collision (Top/Bottom)
        if self.ball_y <= 0 or self.ball_y >= self.height - self.ball_size:
            self.ball_dy *= -1
            
        # Paddle Collision
        # P1 (Left)
        if self.ball_x <= 20 + self.paddle_w:
            if self.p1_y < self.ball_y + self.ball_size and self.p1_y + self.paddle_h > self.ball_y:
                self.ball_dx *= -1
                self.ball_dx += 2 # Speed up
            elif self.ball_x < 0:
                self.score_ai += 1
                self.reset_ball()
        
        # AI (Right)
        if self.ball_x >= self.width - 20 - self.paddle_w - self.ball_size:
            if self.ai_y < self.ball_y + self.ball_size and self.ai_y + self.paddle_h > self.ball_y:
                self.ball_dx *= -1
                self.ball_dx -= 2 # Speed up (negative)
            elif self.ball_x > self.width:
                self.score_p1 += 1
                self.reset_ball()
                
        # AI Movement
        # Simple tracking with error/speed limit
        target_y = self.ball_y - self.paddle_h // 2
        if target_y > self.ai_y:
            self.ai_y += min(20, target_y - self.ai_y)
        elif target_y < self.ai_y:
            self.ai_y -= min(20, self.ai_y - target_y)
        self.ai_y = max(0, min(self.height - self.paddle_h, self.ai_y))
        
        # Win Condition
        if self.score_p1 >= 5: self.state = "win"
        elif self.score_ai >= 5: self.state = "game_over"

    def reset_ball(self):
        self.ball_x = self.width // 2
        self.ball_y = self.height // 2
        self.ball_dx = random.choice([-15, 15]) 
        self.ball_dy = random.choice([-10, 10])

    def render(self):
        img = Image.new('RGB', (self.width, self.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Center Line
        for y in range(0, self.height, 40):
            draw.rectangle([self.width//2 - 2, y, self.width//2 + 2, y + 20], fill=(100, 100, 100))
            
        # Draw Paddles
        draw.rectangle([20, self.p1_y, 20 + self.paddle_w, self.p1_y + self.paddle_h], fill=(50, 255, 50))
        draw.rectangle([self.width - 20 - self.paddle_w, self.ai_y, self.width - 20, self.ai_y + self.paddle_h], fill=(255, 50, 50))
        
        # Draw Ball
        draw.rectangle([self.ball_x, self.ball_y, self.ball_x + self.ball_size, self.ball_y + self.ball_size], fill=(255, 255, 255))
        
        # Scores
        draw.text((self.width//4, 20), str(self.score_p1), fill=(255, 255, 255), font=None)
        draw.text((3*self.width//4, 20), str(self.score_ai), fill=(255, 255, 255), font=None)
        
        if self.state != "playing":
            text = "YOU WIN!" if self.state == "win" else "YOU LOSE!"
            draw.text((self.width//2 - 30, self.height//2), text, fill=(255, 255, 0))

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class PongView(discord.ui.View):
    def __init__(self, game, interaction, cog):
        super().__init__(timeout=120)
        self.game = game
        self.original_interaction = interaction
        self.cog = cog
        self.message = None

    async def update_board(self, interaction=None):
        file = discord.File(self.game.render(), filename="pong.png")
        desc = f"Player: {self.game.score_p1} | AI: {self.game.score_ai}"
        
        if self.game.state != "playing":
             self.clear_items()
             b_restart = discord.ui.Button(label="🔄 Restart", style=discord.ButtonStyle.success, custom_id="restart")
             b_restart.callback = self.restart_callback
             self.add_item(b_restart)
             b_menu = discord.ui.Button(label="🏠 Menu", style=discord.ButtonStyle.secondary, custom_id="menu")
             b_menu.callback = self.menu_callback
             self.add_item(b_menu)
             
             if self.game.state == "win":
                 if _arc_mg:
                     try:
                         _arc_mg(self.game.user_id, 'pong', 'win', 300)
                         _arc_inc(self.game.user_id, 'arcade_wins')
                     except Exception: pass
        
        embed = discord.Embed(title="🏓 Pong Arcade", description=desc, color=discord.Color.dark_grey())
        embed.set_image(url="attachment://pong.png")
        
        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        else:
            await self.original_interaction.response.send_message(embed=embed, file=file, view=self)
            self.message = await self.original_interaction.original_response()

    async def check_auth(self, interaction):
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return False
        return True

    async def restart_callback(self, interaction):
        if not await self.check_auth(interaction): return
        await self.cog.start_pong(interaction)

    async def menu_callback(self, interaction):
        if not await self.check_auth(interaction): return
        await self.cog.show_arcade_menu(interaction)

    @discord.ui.button(label="⬆️", style=discord.ButtonStyle.primary, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move_player(-30)
        await self.update_board(interaction)

    @discord.ui.button(label="⬇️", style=discord.ButtonStyle.primary, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_auth(interaction): return
        self.game.move_player(30)
        await self.update_board(interaction)

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
        await self.cog.start_snake(interaction)

    @discord.ui.button(label="🧱 Tetris", style=discord.ButtonStyle.primary, row=1)
    async def tetris(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.start_tetris(interaction)

    @discord.ui.button(label="👾 Space Invaders", style=discord.ButtonStyle.secondary, row=2)
    async def space(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.start_invaders(interaction)
        
    @discord.ui.button(label="🏓 Pong", style=discord.ButtonStyle.secondary, row=2)
    async def pong(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.start_pong(interaction)


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

    async def start_bomb(self, interaction: discord.Interaction):
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


    async def start_snake(self, interaction: discord.Interaction):
        """Snake game - New Visual Version"""
        game = SnakeGame(interaction.user.id)
        view = SnakeView(game, interaction, self)
        await view.update_board(interaction)
        
        if _arc_inc:
            try:
                _arc_inc(interaction.user.id, 'arcade_played')
            except Exception: pass

    async def start_tetris(self, interaction: discord.Interaction):
        """Tetris game"""
        game = TetrisGame(interaction.user.id)
        # Assuming TetrisGame and TetrisView are defined similarly
        view = TetrisView(game, interaction, self)
        await view.update_board(interaction)
        
        if _arc_inc:
            try:
                _arc_inc(interaction.user.id, 'arcade_played')
            except Exception: pass

    async def start_invaders(self, interaction: discord.Interaction):
        """Space Invaders game"""
        game = SpaceInvadersGame(interaction.user.id)
        view = SpaceInvadersView(game, interaction, self)
        await view.update_board(interaction)
        
        if _arc_inc:
            try:
                _arc_inc(interaction.user.id, 'arcade_played')
            except Exception: pass

    async def start_pong(self, interaction: discord.Interaction):
        """Pong game"""
        game = PongGame(interaction.user.id)
        view = PongView(game, interaction, self)
        await view.update_board(interaction)
        
        if _arc_inc:
            try:
                _arc_inc(interaction.user.id, 'arcade_played')
            except Exception: pass

async def setup(bot):
    await bot.add_cog(ArcadeGames(bot))
