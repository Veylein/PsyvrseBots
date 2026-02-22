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

    async def start_bomb(self, interaction: discord.Interaction):
        await self.arcade_bombdefuse_action(interaction)
    
    async def arcade_bombdefuse_action(self, interaction: discord.Interaction):
        """Bomb defuser game"""
        wires = ["🔴", "🔵", "🟢", "🟡", "⚪", "🟠"]
        num_wires = random.randint(4, 6)
        bomb_wires = random.sample(wires, num_wires)
        correct_wire = random.choice(bomb_wires)
        
        # Generate clues
        clues = []
        if correct_wire in ["🔴", "🟠"]:
            clues.append("The correct wire is a warm color")
        else:
            clues.append("The correct wire is a cool color")
        
        if bomb_wires.index(correct_wire) < len(bomb_wires) // 2:
            clues.append("Cut one of the first wires")
        else:
            clues.append("Cut one of the last wires")
        
        game_id = f"{interaction.guild.id}_{interaction.user.id}_bomb"
        self.active_games[game_id] = {
            "wires": bomb_wires,
            "correct": correct_wire,
            "attempts": 3,
            "clues_shown": 1
        }
        
        wire_display = " ".join([f"{i+1}️⃣ {w}" for i, w in enumerate(bomb_wires)])
        
        embed = discord.Embed(
            title="💣 BOMB DEFUSAL",
            description=f"**⏰ BOMB ACTIVE ⏰**\n\n"
                       f"{wire_display}\n\n"
                       f"**Clue:** {clues[0]}\n\n"
                       f"Cut the correct wire!\n"
                       f"Type the wire number (1-{num_wires})\n\n"
                       f"**Attempts: 3** | React 🔍 for another clue",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🔍")
        
        def check_reaction(reaction, user):
            return user.id == interaction.user.id and str(reaction.emoji) == "🔍"
        
        def check_message(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        while game_id in self.active_games:
            game = self.active_games[game_id]
            
            done, pending = await asyncio.wait([
                asyncio.create_task(self.bot.wait_for('reaction_add', check=check_reaction, timeout=45.0)),
                asyncio.create_task(self.bot.wait_for('message', check=check_message, timeout=45.0))
            ], return_when=asyncio.FIRST_COMPLETED)
            
            for task in pending:
                task.cancel()
            
            try:
                result = done.pop().result()
                
                if isinstance(result, tuple):  # Reaction - show clue
                    if game["clues_shown"] < len(clues):
                        await interaction.followup.send(f"🔍 **Clue:** {clues[game['clues_shown']]}")
                        game["clues_shown"] += 1
                    else:
                        await interaction.followup.send("🔍 No more clues!")
                
                else:  # Message - wire cut attempt
                    try:
                        choice = int(result.content)
                        if 1 <= choice <= len(game["wires"]):
                            chosen_wire = game["wires"][choice - 1]
                            
                            if chosen_wire == game["correct"]:
                                reward = game["attempts"] * 200
                                embed = discord.Embed(
                                    title="✅ BOMB DEFUSED!",
                                    description=f"You cut the {chosen_wire} wire!\n\n"
                                               f"**+{reward} PsyCoins!** 🪙",
                                    color=discord.Color.green()
                                )
                                await result.reply(embed=embed)
                                if _arc_mg:
                                    try:
                                        _arc_mg(interaction.user.id, 'bombdefuse', 'win', reward)
                                        _arc_inc(interaction.user.id, 'arcade_wins')
                                    except Exception:
                                        pass
                                # Chance to award a difficult TCG card for bomb defuse win
                                if tcg_manager:
                                    try:
                                        awarded = tcg_manager.award_for_game_event(str(result.author.id), 'difficult')
                                        if awarded:
                                            names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                                            await result.reply(f"🎴 Bonus TCG reward: {', '.join(names)}")
                                    except Exception:
                                        pass
                                del self.active_games[game_id]
                                break
                            else:
                                game["attempts"] -= 1
                                if game["attempts"] <= 0:
                                    embed = discord.Embed(
                                        title="💥 BOOM!",
                                        description=f"The bomb exploded!\n\n"
                                                   f"Correct wire was {game['correct']}",
                                        color=discord.Color.dark_red()
                                    )
                                    await result.reply(embed=embed)
                                    if _arc_mg:
                                        try:
                                            _arc_mg(interaction.user.id, 'bombdefuse', 'loss', 0)
                                        except Exception:
                                            pass
                                    del self.active_games[game_id]
                                    break
                                else:
                                    await result.reply(f"❌ Wrong wire! **{game['attempts']} attempts left!**")
                        else:
                            await result.reply(f"❌ Choose 1-{len(game['wires'])}")
                    except ValueError:
                        await result.reply("❌ Type a number!")
            
            except asyncio.TimeoutError:
                if game_id in self.active_games:
                    embed = discord.Embed(
                        title="💥 TIMEOUT - BOOM!",
                        description=f"You ran out of time!\n\nCorrect wire: {game['correct']}",
                        color=discord.Color.dark_red()
                    )
                    await interaction.followup.send(embed=embed)
                    del self.active_games[game_id]
                break

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
