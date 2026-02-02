import discord
from discord.ext import commands
import json
import os
from typing import Optional, Literal
import random
import asyncio
from datetime import datetime

class Owner(commands.Cog):
    """Secret owner-only commands for bot management and fun"""
    
    def __init__(self, bot):
        self.bot = bot
        self.owner_ids = bot.owner_ids
        
        print(f"[OWNER COG] Initialized with owner_ids: {self.owner_ids}")
        
        # Funny responses for secret commands
        self.god_mode_responses = [
            "🌟 You feel the power of the gods flowing through you...",
            "⚡ Reality bends to your will...",
            "👑 All shall bow before your might!",
            "🔮 The cosmos aligns in your favor...",
            "💫 Transcendence achieved!"
        ]
        
        self.chaos_responses = [
            "🌪️ CHAOS UNLEASHED!",
            "💥 The universe trembles!",
            "🎭 Reality is what you make it!",
            "🎪 Let the games begin!",
            "🎲 Rolling the cosmic dice..."
        ]

    async def cog_check(self, ctx):
        """Global check - only allow owners"""
        user_id = None
        if hasattr(ctx, 'author'):
            user_id = ctx.author.id
        elif hasattr(ctx, 'user'):
            user_id = ctx.user.id
        
        is_owner = user_id in self.owner_ids
        print(f"[OWNER COG] cog_check: user_id={user_id}, owner_ids={self.owner_ids}, is_owner={is_owner}")
        
        return is_owner
    
    # ==================== TEST COMMAND ====================
    
    @commands.command(name="ownertest")
    async def ownertest(self, ctx):
        """Test if owner commands are working"""
        print(f"[OWNER COG] ownertest called by {ctx.author.id}")
        await ctx.send(f"✅ Owner commands are working!\n**Your ID:** {ctx.author.id}\n**Owner IDs:** {self.owner_ids}")
    
    @commands.command(name="fishing_tournament")
    async def fishing_tournament_owner(self, ctx, mode: str = "biggest", duration: int = 5):
        """Owner-only: Start a fishing tournament
        
        Usage: L!fishing_tournament <mode> <duration>
        Modes: biggest, most, rarest
        Duration: 1-30 minutes
        """
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        mode = mode.lower()
        if mode not in ["biggest", "most", "rarest"]:
            return await ctx.send("❌ Invalid mode! Use: biggest, most, or rarest")
        
        if duration < 1 or duration > 30:
            return await ctx.send("❌ Duration must be between 1-30 minutes!")
        
        # Check if tournament already running
        guild_id = str(ctx.guild.id)
        if guild_id in getattr(fishing_cog, 'active_tournaments', {}):
            return await ctx.send("❌ A tournament is already running in this server!")
        
        # Get configured tournament channel
        guild_config = fishing_cog.get_guild_config(ctx.guild.id)
        tournament_channel_id = guild_config.get("tournament_channel")
        
        if not tournament_channel_id:
            return await ctx.send("❌ No tournament channel configured! Admin must set it first using `L!fishtournament_channel #channel`")
        
        tournament_channel = self.bot.get_channel(tournament_channel_id)
        if not tournament_channel:
            return await ctx.send("❌ Tournament channel not found! Ask admin to reconfigure it.")
        
        # Start tournament via fishing cog
        await fishing_cog.start_random_tournament(ctx.guild.id, tournament_channel_id, mode=mode, duration=duration)
        
        mode_names = {
            "biggest": "🏆 Biggest Fish",
            "most": "📊 Most Fish",
            "rarest": "✨ Rarest Fish"
        }
        await ctx.send(f"✅ Tournament started in {tournament_channel.mention}!\n"
                      f"**Mode:** {mode_names.get(mode, mode)}\n"
                      f"**Duration:** {duration} minutes")
    
    @commands.command(name="serverlist")
    async def serverlist(self, ctx):
        """Owner-only: List Discord servers the bot is in"""
        if getattr(ctx, 'author', None) and ctx.author.id not in self.owner_ids:
            return await ctx.send("❌ You must be a bot owner to use this command!")
        guilds_info = []
        for g in self.bot.guilds:
            try:
                member_count = g.member_count
            except Exception:
                member_count = "?"

            invite_url = None
            try:
                invites = await g.invites()
                if invites:
                    invites_sorted = sorted(invites, key=lambda i: (i.max_age or 0, i.uses or 0))
                    invite_url = getattr(invites_sorted[0], 'url', str(invites_sorted[0]))
            except Exception:
                invite_url = None

            guilds_info.append({
                "name": g.name,
                "id": g.id,
                "members": member_count,
                "invite": invite_url,
            })

        if not guilds_info:
            return await ctx.send("No guilds found.")

        per_page = 20
        pages = [guilds_info[i:i+per_page] for i in range(0, len(guilds_info), per_page)]
        total = len(pages)
        for idx, page in enumerate(pages, start=1):
            embed = discord.Embed(title=f"Server list — page {idx}/{total}", color=discord.Color.blurple())
            for gi in page:
                name = gi.get("name") or "(unknown)"
                if len(name) > 250:
                    name = name[:247] + "..."
                invite = gi.get("invite") or "N/A"
                embed.add_field(
                    name=name,
                    value=f"ID: {gi.get('id')}\nMembers: {gi.get('members')}\nInvite: {invite}",
                    inline=False,
                )
            await ctx.send(embed=embed)
    
    # ==================== ECONOMY MANAGEMENT ====================

    @commands.command(name="godmode")
    async def godmode(self, ctx):
        """Secret god mode - max out your stats"""
        print(f"[OWNER COG] godmode command called by {ctx.author.id}")
        
        # CRITICAL: Check if user is bot owner (cog_check handles this, but double-check)
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED godmode attempt by {ctx.author.id}")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Max out owner's economy
        economy_cog.economy_data[str(ctx.author.id)] = {
            "balance": 999999999,
            "total_earned": 999999999,
            "total_spent": 999999999,
            "last_daily": None,
            "daily_streak": 999,
            "active_boosts": {}
        }
        economy_cog.save_economy()
        
        # Give all items
        for item_id in economy_cog.shop_items.keys():
            economy_cog.add_item(ctx.author.id, item_id, 99)
        
        await ctx.send(random.choice(self.god_mode_responses))
        embed = discord.Embed(
            title="👑 GOD MODE ACTIVATED",
            description=f"**Balance:** 999,999,999 PsyCoins\n**Streak:** 999 days\n**Items:** ALL (x99)",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @commands.command(name="setcoins")
    async def setcoins(self, ctx, member: discord.Member, amount: int):
        """Set someone's PsyCoin balance"""
        
        # CRITICAL: Check if user is bot owner (cog_check handles this, but double-check)
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED setcoins attempt by {ctx.author.id}")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        user_key = str(member.id)
        economy_cog.get_balance(member.id)  # Ensure user exists
        economy_cog.economy_data[user_key]["balance"] = amount
        economy_cog.save_economy()
        
        await ctx.send(f"💰 Set {member.mention}'s balance to **{amount:,} PsyCoins**")

    @commands.command(name="addcoins")
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        """Add PsyCoins to someone's balance"""
        
        # CRITICAL: Check if user is bot owner (cog_check handles this, but double-check)
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED addcoins attempt by {ctx.author.id}")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        economy_cog.add_coins(member.id, amount, "owner_grant")
        new_balance = economy_cog.get_balance(member.id)
        
        await ctx.send(f"💸 Added **{amount:,} PsyCoins** to {member.mention}\nNew balance: **{new_balance:,}**")

    @commands.command(name="removecoins")
    async def removecoins(self, ctx, member: discord.Member, amount: int):
        """Remove PsyCoins from someone's balance"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        success = economy_cog.remove_coins(member.id, amount)
        new_balance = economy_cog.get_balance(member.id)
        
        if success:
            await ctx.send(f"💸 Removed **{amount:,} PsyCoins** from {member.mention}\nNew balance: **{new_balance:,}**")
        else:
            await ctx.send(f"❌ {member.mention} doesn't have enough coins! Current balance: **{new_balance:,}**")

    @commands.command(name="resetcoins")
    async def resetcoins(self, ctx, member: discord.Member):
        """Reset someone's economy data"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        user_key = str(member.id)
        if user_key in economy_cog.economy_data:
            del economy_cog.economy_data[user_key]
            economy_cog.save_economy()
        
        await ctx.send(f"🔄 Reset {member.mention}'s economy data to defaults")

    @commands.command(name="giveitem")
    async def giveitem(self, ctx, member: discord.Member, item_id: str, quantity: int = 1):
        """Give an item to someone"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        if item_id not in economy_cog.shop_items:
            await ctx.send(f"❌ Invalid item ID! Available items: {', '.join(economy_cog.shop_items.keys())}")
            return
        
        economy_cog.add_item(member.id, item_id, quantity)
        item_name = economy_cog.shop_items[item_id]["name"]
        
        await ctx.send(f"🎁 Gave **{quantity}x {item_name}** to {member.mention}")

    @commands.command(name="give_tc")
    async def give_tc(self, ctx, member: discord.Member, *, card_query: str):
        """Owner-only: give a TCG card by name or id to a member."""
        # Try legacy TCG cog first, then fallback to psyvrse_tcg inventory
        tcg = self.bot.get_cog('TCG')
        if tcg:
            try:
                cid = tcg._find_card_by_name_or_id(card_query)
                if not cid:
                    return await ctx.send('Card not found.')
                tcg.manager.award_card(str(member.id), cid, 1)
                return await ctx.send(f'Gave 1x {cid} to {member.mention}')
            except Exception:
                pass

        # Fallback: psyvrse_tcg
        try:
            from cogs import psyvrse_tcg
            # simple resolver: exact crafted id, numeric seed, or search crafted by name
            q = card_query.strip()
            # crafted id
            if q.upper().startswith('C') and psyvrse_tcg.inventory.get_crafted(q):
                cid = q
            else:
                # numeric id
                try:
                    n = int(q)
                    if 0 <= n < psyvrse_tcg.TOTAL_CARD_POOL:
                        cid = str(n)
                    else:
                        cid = None
                except Exception:
                    cid = None
                # search crafted names if not numeric
                if not cid:
                    for k,v in psyvrse_tcg.inventory.crafted.items():
                        if q.lower() in (v.get('name','').lower()):
                            cid = k
                            break
            if not cid:
                return await ctx.send('Card not found.')
            psyvrse_tcg.inventory.add_card(member.id, cid)
            return await ctx.send(f'Gave 1x {cid} to {member.mention}')
        except Exception:
            return await ctx.send('TCG cog not loaded.')

    @commands.command(name="remove_tc")
    async def remove_tc(self, ctx, member: discord.Member, *, card_query: str):
        """Owner-only: remove a TCG card by name or id from a member."""
        # Try legacy TCG cog first, then fallback to psyvrse_tcg inventory
        tcg = self.bot.get_cog('TCG')
        if tcg:
            try:
                cid = tcg._find_card_by_name_or_id(card_query)
                if not cid:
                    return await ctx.send('Card not found.')
                ok = tcg.manager.remove_card(str(member.id), cid, 1)
                if not ok:
                    return await ctx.send('Member does not have that card.')
                return await ctx.send(f'Removed 1x {cid} from {member.mention}')
            except Exception:
                pass

        # Fallback: psyvrse_tcg
        try:
            from cogs import psyvrse_tcg
            q = card_query.strip()
            if q.upper().startswith('C') and psyvrse_tcg.inventory.get_crafted(q):
                cid = q
            else:
                try:
                    n = int(q)
                    if 0 <= n < psyvrse_tcg.TOTAL_CARD_POOL:
                        cid = str(n)
                    else:
                        cid = None
                except Exception:
                    cid = None
                if not cid:
                    for k,v in psyvrse_tcg.inventory.crafted.items():
                        if q.lower() in (v.get('name','').lower()):
                            cid = k
                            break
            if not cid:
                return await ctx.send('Card not found.')
            ok = psyvrse_tcg.inventory.remove_card(member.id, cid)
            if not ok:
                return await ctx.send('Member does not have that card.')
            return await ctx.send(f'Removed 1x {cid} from {member.mention}')
        except Exception:
            return await ctx.send('TCG cog not loaded.')

    # ==================== BOT STATUS & PRESENCE ====================

    @commands.command(name="status")
    async def change_status(self, ctx, status_type: str, *, text: str):
        """Change bot status (playing/watching/listening/competing)"""
        status_types = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing
        }
        
        if status_type.lower() not in status_types:
            await ctx.send(f"❌ Invalid status type! Use: {', '.join(status_types.keys())}")
            return
        
        activity = discord.Activity(type=status_types[status_type.lower()], name=text)
        await self.bot.change_presence(activity=activity)
        
        await ctx.send(f"✅ Status changed to: **{status_type.title()}** {text}")

    @commands.command(name="presence")
    async def change_presence(self, ctx, status: str):
        """Change bot online status (online/idle/dnd/invisible)"""
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        
        if status.lower() not in status_map:
            await ctx.send(f"❌ Invalid status! Use: {', '.join(status_map.keys())}")
            return
        
        await self.bot.change_presence(status=status_map[status.lower()])
        await ctx.send(f"✅ Presence changed to: **{status}**")

    @commands.command(name="nickname")
    async def change_nickname(self, ctx, *, nickname: str = None):
        """Change bot's nickname in this server"""
        try:
            await ctx.guild.me.edit(nick=nickname)
            if nickname:
                await ctx.send(f"✅ Nickname changed to: **{nickname}**")
            else:
                await ctx.send("✅ Nickname reset to default")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change my nickname!")

    # ==================== FUN CHAOS COMMANDS ====================

    @commands.command(name="raincoins")
    async def raincoins(self, ctx, amount: int = 1000):
        """Make it rain coins for everyone online"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        online_members = [m for m in ctx.guild.members if not m.bot and m.status != discord.Status.offline]
        
        for member in online_members:
            economy_cog.add_coins(member.id, amount, "coin_rain")
        
        await ctx.send(f"💸💸💸 **IT'S RAINING COINS!** 💸💸💸\n**{amount:,} PsyCoins** given to {len(online_members)} online members!")

    @commands.command(name="chaos")
    async def chaos_mode(self, ctx):
        """Activate CHAOS MODE - random rewards for everyone"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        await ctx.send(random.choice(self.chaos_responses))
        
        members = [m for m in ctx.guild.members if not m.bot]
        rewards = []
        
        for member in members:
            # Random reward between 100-10000
            reward = random.randint(100, 10000)
            economy_cog.add_coins(member.id, reward, "chaos_mode")
            
            # Random chance for items
            if random.random() < 0.3:  # 30% chance
                item_id = random.choice(list(economy_cog.shop_items.keys()))
                economy_cog.add_item(member.id, item_id, 1)
                rewards.append(f"{member.mention}: {reward:,} coins + item!")
            else:
                rewards.append(f"{member.mention}: {reward:,} coins")
        
        # Send in chunks to avoid message limit
        chunk_size = 10
        for i in range(0, len(rewards), chunk_size):
            chunk = rewards[i:i+chunk_size]
            await ctx.send("\n".join(chunk))
        
        await ctx.send("🎭 **CHAOS MODE COMPLETE!**")

    @commands.command(name="spinlottery")
    async def run_lottery(self, ctx, prize: int = 50000):
        """Run a lottery - pick a random winner (owner command to avoid conflict with lottery.py)"""
        members = [m for m in ctx.guild.members if not m.bot]
        winner = random.choice(members)
        
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(winner.id, prize, "lottery_win")
        
        embed = discord.Embed(
            title="🎰 LOTTERY WINNER! 🎰",
            description=f"🎉 Congratulations {winner.mention}!\n\nYou won **{prize:,} PsyCoins**!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=winner.display_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name="cursed")
    async def cursed_message(self, ctx):
        """Send a cursed/haunted message"""
        cursed_messages = [
            "H̴̡̢̳̠̻̰̲̼̦̱̻̥̮͎̳̠̱̙͌̓̂̌̏ͅE̷̡͚̭͔͎̮̞̩͕̮̙͆̎͒̾̈́̎̾̏ͅ ̸̨̧̛̹̲̳̰̰̜̼̗̟̻̈́͑̓̆̄C̴̡̧̛͚̲̭̞̳̫̝̦̦̔̍̾̋̈́͐͛̿́̍̕͜͝O̴̧̨̫̩̺͓̫̙̦̜̹̊̑͛̐̀̾̅̿̅̆̚͝M̸̧̢̠̘̜̤̫̮͉̫̞̟̎̾̈́̌̍̏̂̿Ę̷̧̛̜̦̯̗̝̦̜̠̈́̍̀̍͋̐̈́̕͝S̶̡̛̻͈̥͎̱͎̯̫͐̽̊͊͆͜",
            "T̶̢̛̤͖͔̳̟͖̹̜̀̔͌̆̇̚͜h̷̢̹͉͖̞̻̦̪̪̰͌̓̍̃̿͂̌͘͝ę̷̣̭̝̫̜̱̱͚̀́͂̃̈̃̈́̚͝ ̵̧͕͙̼̲̳̗̣͚̈́̈́̄̿͘͠v̴̢̧̱̺̬̞̜͈̄͂̂̓̂́̕͠͝ͅo̵̧̢̗͍͎̰͉̠̹̔̏̿̃̑̓̎͘͜ḯ̵̧̢̛̻̮͕̤̲͙̞̋̏̎̚͝d̴̢̗̬͚̰̱̥̗̏̀̀̐̈́̍͘͝ ̴̦̹̟͈̺̙̝͍͐̔̈́͑̃̽̚͝w̶̢̛̗̪̟̝̜̮͚̤̓̋͗͊̑̌̒͘a̸̢̟͕̠̭̪̳͑̎̏̀̊͊̈́͘t̶̢̹̱͎̼̝̫̱̐̏̌̐̓̈́̑̈́c̷̡̨̬̰̪̖͎̼̦͋̀̈́̍̇̊̌̚h̶̨̨̲̜̘͈̪̮̺̔͑̄͑̿̆͝ė̶̡̛̛͔͎̺̪̻̰͖̀̊̈́̓̕͘s̶̨̖͕̥̮̟̣͖̈́̈́͒̍͒́̚͝",
            "Y̷̢̨̱̹͕̱̹̦̌̊̀͜o̶̧̦̪̤͇̺̥͂̈̈́͗̚͜u̴͓̝̬̦̪̱̞͐̈́̍̈́̂̚͝ ̴̢̛̗̺̘̜̺̞̟͆̋̐̓̐͑c̸͕̻̥͓͌̈́̀́̅͝ą̶̯̰̫͇̦̐̌͘n̸̢̢̛̰̟̪̖̯̏̾̎̒̿̕'̴̡̛̱̣̲͉̫̘̈́͋͐̓̽͝ť̶̨̮̹͈̱͎̱̍̾͋͌̚ ̵̧̨̭̻̰͉͍̅̌̋͐̽͜͠ę̷̺͔̹͎̹̱̈s̶̨̛̲̱͔̼̱̦̎̀̊̈́̚c̴̥̪̫̈́̅̄̀̌̚ǎ̸̧̡̻̯̦̘̇͗͒̈́̕͠p̷̧̪͚̬̳̞̓̅̎͗̂͠ę̸̮͕̳̝͙̜̈́̐͌̓̉̀͝",
            "🕷️ T̵̢̢̛̝͍͇͕̪̳͎̯̠͓̤͙̝̮̍͑̐̋͗̔̑͋͐̕͝h̸̨̧̢̛̯͈̖̥͈̞̣̩͌̏̿̐̿̾͗̇̑̒̚͘͝͝e̵̡̝̞̤̰͙̣̦̠̰͉̿̈́̀̐̊̄͝ ̸̨̛̼̫̼̳̦̲̠͈̻̖͙͕̬̐̅͆̊̍̇̅̚̕s̴̛̩̝̗̩͔̼̣̺̫̦̉͐̓̇̈̀̎̄͊̿̚̕͜͝p̴̧̛̘̤͕̣̱̰̺̝͙̟̐̋̈̀̈́̍̾̀̓̆͌̕i̵̪̇̀̌̓̍̋́̓̎̂͝͝d̷̨̛̩̫̙̞̬̠͔͍̖̖̱̙̻̊̓͌̍̑̑̌̍̒͐͆͆͘͘͜ę̷̢̡̖͙̝̻̼̘͔̀̾͐̎̿͗̕͜͝r̸̨̲̘̬͙̦̠͊̊͋͜͝s̴̨̧̧̡̱̹̮̘̼͈͌̈́̓̾̾̕͝ ̴̣̙̪̭̝̱͉̀̾̌̈́͒͂̄͐̄̚͜a̵̧̡̛̘̱̣͚̻̩͕͌̑̀̽̊̈́̕͠r̴̳̳͙̫̺͕͓̻̙̈́̒̈̿̎̉̈́̓̓̈ę̴̡̢̧̢̙͈̥̹̺̥̺͓̉̒͘͜͝ ̴̡̤̖̙̞̻̪̬̫̪̦͚̐͂́c̵̡̧̨͇̭̙̘̗̊̍̉̀̒͑̕͜o̷̡̭͇̮̺͕̫̗̹̊̓͛͒̇̽̓̕̚m̴̧̛̛̖̙̪͊̇̈́̈́̐͌̕͘͝͝ͅi̴̢̺͇̹̜͈̳̗͕̊̿͋̂̒̓̈́͛͌̃́̚͝ň̴̨̡̮̗̪̞͎̰͈̺̗̑͆̈́̀͒͂́̍̌̚͝g̴̲̼̼̦͉̞̹̤͋̋̔̃̇̓̇̕ 🕷️",
            "Ỉ̷̡̦̫͚̼̰͍̗̐̋̓͌͌̓͋̊̂͘͝'̶̡̧̯̙͕̗̹̳̯̻̩̃͆͑̈͛͑̂̽̓̂̕͝m̶̛̻͕̞̗̭̪̣̰͉̂̆́͆̓̈́̋̀̈́̓̕͠ ̸̢̡͎̺̬̤̩̙̰̰̝̗̎͐̌̍̈́̕͝ẁ̷̨̛̛͔̻̪̳͎̳̘̬̻̈́̽̄͑́̊̈́̒̚͜͝a̴̡͇̻̹̞̱̠̤̞̱͇̦̐̅͋͑̒͗̕͜͠t̶̨̛̠̰̖͚̫̩̙̠̀̍̌͂͗̂̀̾c̶̡̘̝̩̖̈́̾͆̍̂̑̒͊̀̾̾̚͜͝h̷̝̼͙̺̮̩̮̪̓̆͋͛̚̚͝i̴̧̞̙̩̟̣̘̋n̵̜̜̗̥̔͑̅́̚͜g̵̨̛̯̱̦̺̫̫͈͕̜̼̦̈̑̓̿͗̈́̕͠͝"
        ]
        
        await ctx.send(random.choice(cursed_messages))
        await asyncio.sleep(1)
        await ctx.send("Just kidding! 😈")

    @commands.command(name="countset")
    async def count_set(self, ctx, number: int):
        """Set the current counting number (owner only)"""
        if number < 0:
            await ctx.send("❌ Number must be 0 or greater!")
            return
        
        counting_cog = self.bot.get_cog("Counting")
        if not counting_cog:
            await ctx.send("❌ Counting system not loaded!")
            return
        
        guild_id = str(ctx.guild.id)
        
        # Check if counting is set up
        if guild_id not in counting_cog.count_data:
            await ctx.send("❌ Counting game is not set up in this server! Use `L!counting` first.")
            return
        
        # Set the count
        counting_cog.count_data[guild_id]["current_count"] = number
        counting_cog.count_data[guild_id]["last_user"] = None  # Reset last user
        counting_cog.save_data()
        
        embed = discord.Embed(
            title="🔢 Count Updated!",
            description=f"The counting game has been set to **{number:,}**\n\nNext number expected: **{number + 1:,}**",
            color=discord.Color.green()
        )
        
        counting_channel_id = counting_cog.count_data[guild_id].get("channel")
        if counting_channel_id:
            counting_channel = ctx.guild.get_channel(counting_channel_id)
            if counting_channel:
                embed.add_field(name="Channel", value=counting_channel.mention, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="spawn")
    async def spawn_boss(self, ctx):
        """Spawn a 'raid boss' event"""
        bosses = [
            {"name": "🐉 Ancient Dragon", "hp": 10000, "reward": 5000},
            {"name": "👾 Cyber Demon", "hp": 15000, "reward": 7500},
            {"name": "🦑 Kraken", "hp": 20000, "reward": 10000},
            {"name": "👹 Demon Lord", "hp": 25000, "reward": 15000},
            {"name": "🌟 Celestial Being", "hp": 30000, "reward": 20000}
        ]
        
        boss = random.choice(bosses)
        
        embed = discord.Embed(
            title="⚔️ RAID BOSS SPAWNED! ⚔️",
            description=f"**{boss['name']}** has appeared!\n\n"
                       f"**HP:** {boss['hp']:,}\n"
                       f"**Reward:** {boss['reward']:,} PsyCoins\n\n"
                       f"React with ⚔️ to join the battle!",
            color=discord.Color.red()
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚔️")
        
        await asyncio.sleep(30)  # Wait 30 seconds for reactions
        
        message = await ctx.channel.fetch_message(message.id)
        reaction = discord.utils.get(message.reactions, emoji="⚔️")
        
        if reaction and reaction.count > 1:  # Minus the bot's reaction
            users = [user async for user in reaction.users() if not user.bot]
            
            # Calculate reward split
            reward_per_user = boss['reward'] // len(users)
            
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                for user in users:
                    economy_cog.add_coins(user.id, reward_per_user, "raid_boss")
            
            embed = discord.Embed(
                title="🎉 BOSS DEFEATED! 🎉",
                description=f"**{len(users)} heroes** defeated {boss['name']}!\n\n"
                           f"Each warrior received **{reward_per_user:,} PsyCoins**!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"💀 {boss['name']} escaped! No one joined the battle...")

    # ==================== SERVER MANAGEMENT ====================

    @commands.command(name="purge")
    async def purge_messages(self, ctx, amount: int = 10):
        """Delete messages in current channel"""
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for command message
        
        msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(name="announce")
    async def announce(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send an announcement to a channel"""
        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"From: {ctx.author.display_name}")
        
        await channel.send(embed=embed)
        await ctx.send(f"✅ Announcement sent to {channel.mention}")

    @commands.command(name="dm")
    async def dm_user(self, ctx, member: discord.Member, *, message: str):
        """DM a specific user"""
        try:
            await member.send(message)
            await ctx.send(f"✅ DM sent to {member.mention}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot DM {member.mention} - they have DMs disabled")

    @commands.command(name="stats")
    async def ludus_stats(self, ctx, action: str = "view"):
        """Show detailed bot statistics with live updates
        
        Usage:
        L!stats - View current stats
        L!stats update - Force update and recalculate all stats
        """
        
        if action.lower() == "update":
            # Force recalculation
            msg = await ctx.send("🔄 Updating all statistics...")
            
            # Log the update
            logger = self.bot.get_cog("BotLogger")
            if logger:
                await logger.log_owner_command(ctx, "stats update", "Recalculating all bot statistics")
            
            await msg.edit(content="✅ Statistics updated!")
        
        # Calculate comprehensive stats
        embed = discord.Embed(
            title="📊 LUDUS BOT STATISTICS",
            description="**Real-time bot analytics and metrics**",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        
        # ===== SERVER STATS =====
        total_members = sum(g.member_count for g in self.bot.guilds)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)
        
        server_stats = (f"**Servers:** {len(self.bot.guilds):,}\n"
                       f"**Total Users:** {total_members:,}\n"
                       f"**Channels:** {total_channels:,}\n"
                       f"**Latency:** {round(self.bot.latency * 1000)}ms")
        
        embed.add_field(name="🌐 Server Stats", value=server_stats, inline=True)
        
        # ===== COMMAND STATS =====
        total_commands = len(self.bot.commands) + len(self.bot.tree.get_commands())
        
        command_stats = (f"**Prefix Commands:** {len(self.bot.commands)}\n"
                        f"**Slash Commands:** {len(self.bot.tree.get_commands())}\n"
                        f"**Total:** {total_commands}\n"
                        f"**Cogs Loaded:** {len(self.bot.cogs)}")
        
        embed.add_field(name="⚙️ Commands", value=command_stats, inline=True)
        
        # ===== ECONOMY STATS =====
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            total_users = len(economy_cog.economy_data)
            total_coins = sum(data.get("balance", 0) for data in economy_cog.economy_data.values())
            avg_coins = total_coins // total_users if total_users > 0 else 0
            
            # Get top 3 richest users
            top_users = sorted(
                economy_cog.economy_data.items(),
                key=lambda x: x[1].get("balance", 0),
                reverse=True
            )[:3]
            
            economy_stats = (f"**Total Users:** {total_users:,}\n"
                           f"**Total Coins:** {total_coins:,} 💰\n"
                           f"**Average Balance:** {avg_coins:,}\n"
                           f"**Richest Users:**")
            
            for idx, (user_id, data) in enumerate(top_users, 1):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    economy_stats += f"\n{idx}. {user.name}: {data.get('balance', 0):,}"
                except:
                    economy_stats += f"\n{idx}. User {user_id}: {data.get('balance', 0):,}"
            
            embed.add_field(name="💰 Economy", value=economy_stats, inline=False)
        
        # ===== ACTIVITY STATS =====
        # Games played
        total_games = 0
        minigames_cog = self.bot.get_cog("Minigames")
        leaderboard_cog = self.bot.get_cog("LeaderboardManager")
        
        if leaderboard_cog and hasattr(leaderboard_cog, 'stats'):
            for category_stats in leaderboard_cog.stats.values():
                for server_stats_data in category_stats.values():
                    total_games += server_stats_data.get("plays", 0)
        
        # Leveling stats
        leveling_cog = self.bot.get_cog("Leveling")
        total_levels = 0
        if leveling_cog and hasattr(leveling_cog, 'levels'):
            total_levels = sum(data.get("level", 0) for data in leveling_cog.levels.values())
        
        # Pets stats
        pets_cog = self.bot.get_cog("Pets")
        total_pets = 0
        if pets_cog and hasattr(pets_cog, 'pets_data'):
            total_pets = len([p for p in pets_cog.pets_data.values() if p.get("pet")])
        
        activity_stats = (f"**Games Played:** {total_games:,}\n"
                         f"**Total Levels:** {total_levels:,}\n"
                         f"**Pets Adopted:** {total_pets:,}")
        
        embed.add_field(name="🎮 Activity", value=activity_stats, inline=True)
        
        # ===== GLOBAL EVENTS =====
        global_events_cog = self.bot.get_cog("GlobalEvents")
        if global_events_cog and hasattr(global_events_cog, 'active_events'):
            active_events = len(global_events_cog.active_events)
            events_list = ", ".join(global_events_cog.active_events.keys()) if active_events > 0 else "None"
            
            events_stats = (f"**Active Events:** {active_events}\n"
                          f"**Types:** {events_list}")
            
            embed.add_field(name="🌍 Global Events", value=events_stats, inline=True)
        
        # ===== GLOBAL LEADERBOARD =====
        global_lb_cog = self.bot.get_cog("GlobalLeaderboard")
        if global_lb_cog and hasattr(global_lb_cog, 'data'):
            servers_ranked = len([s for s, d in global_lb_cog.consents.items() if d.get("enabled", False)])
            
            # Calculate top server
            if global_lb_cog.data:
                top_server_id = max(
                    global_lb_cog.data.keys(),
                    key=lambda x: global_lb_cog.calculate_server_score(x)
                )
                top_score = global_lb_cog.calculate_server_score(top_server_id)
                try:
                    top_guild = self.bot.get_guild(int(top_server_id))
                    top_name = top_guild.name if top_guild else f"Server {top_server_id}"
                except:
                    top_name = f"Server {top_server_id}"
            else:
                top_name = "None"
                top_score = 0
            
            global_stats = (f"**Servers Ranked:** {servers_ranked}\n"
                          f"**Top Server:** {top_name}\n"
                          f"**Top Score:** {top_score:,}")
            
            embed.add_field(name="🏆 Global Rankings", value=global_stats, inline=True)
        
        # ===== MULTIPLAYER GAMES =====
        multiplayer_cog = self.bot.get_cog("MultiplayerGames")
        if multiplayer_cog and hasattr(multiplayer_cog, 'active_lobbies'):
            active_lobbies = len(multiplayer_cog.active_lobbies)
            
            mp_stats = f"**Active Games:** {active_lobbies}"
            
            embed.add_field(name="🎮 Multiplayer", value=mp_stats, inline=True)
        
        # ===== FISHING & FARMING =====
        fishing_cog = self.bot.get_cog("FishingAkinatorFun")
        if fishing_cog and hasattr(fishing_cog, 'fishing_data'):
            total_fish = sum(len(data.get("fish", {})) for data in fishing_cog.fishing_data.values())
            total_fishers = len(fishing_cog.fishing_data)
            
            fishing_stats = (f"**Total Fishers:** {total_fishers:,}\n"
                           f"**Fish Caught:** {total_fish:,}")
            
            embed.add_field(name="🎣 Fishing", value=fishing_stats, inline=True)
        
        simulations_cog = self.bot.get_cog("Simulations")
        if simulations_cog and hasattr(simulations_cog, 'farms'):
            total_farmers = len(simulations_cog.farms)
            total_crops = sum(
                len([p for p in farm.get("plots", {}).values() if p.get("crop")])
                for farm in simulations_cog.farms.values()
            )
            
            farming_stats = (f"**Total Farmers:** {total_farmers:,}\n"
                           f"**Crops Planted:** {total_crops:,}")
            
            embed.add_field(name="🌾 Farming", value=farming_stats, inline=True)
        
        embed.set_footer(text=f"Updated by {ctx.author.name}" if action.lower() == "update" else "Use L!stats update to refresh")
        
        await ctx.send(embed=embed)

    @commands.command(name="update")
    async def update_command(self, ctx, system: str = None):
        """Update various systems (Owner only)"""
        if not system:
            await ctx.send("❌ Please specify what to update: `L!update global` or `L!update stats`")
            return
        
        if system.lower() == "global":
            # Update global leaderboard
            global_cog = self.bot.get_cog("GlobalLeaderboard")
            if not global_cog:
                await ctx.send("❌ Global Leaderboard cog not found!")
                return
            
            # Log the update
            logger_cog = self.bot.get_cog("BotLogger")
            if logger_cog:
                await logger_cog.log_owner_command(
                    ctx.author,
                    "L!update global",
                    f"Manual global leaderboard recalculation"
                )
            
            # Recalculate all server scores
            updated_count = 0
            for guild in self.bot.guilds:
                guild_id = str(guild.id)
                
                # Check consent
                if guild_id not in global_cog.consents or not global_cog.consents[guild_id].get("enabled", False):
                    continue
                
                # Calculate score
                score = global_cog.calculate_server_score(guild_id)
                
                # Ensure server data exists
                if guild_id not in global_cog.data:
                    global_cog.data[guild_id] = {
                        "games_played": 0,
                        "tasks_completed": 0,
                        "events_participated": 0,
                        "coins_earned": 0,
                        "messages_sent": 0,
                        "members_active": 0
                    }
                
                # Update timestamp
                global_cog.data[guild_id]["last_updated"] = datetime.utcnow().isoformat()
                updated_count += 1
            
            global_cog.save_data()
            
            embed = discord.Embed(
                title="✅ Global Leaderboard Updated",
                description=f"Recalculated scores for **{updated_count} servers**\n\n"
                           f"Updated by: {ctx.author.mention}\n"
                           f"Timestamp: <t:{int(datetime.utcnow().timestamp())}:F>",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        
        elif system.lower() == "stats":
            # Redirect to L!stats update
            await ctx.invoke(self.bot.get_command('stats'), action="update")
        
        else:
            await ctx.send(f"❌ Unknown system: `{system}`\nAvailable: `global`, `stats`")

    # ==================== DEBUG COMMANDS ====================

    @commands.command(name="eval")
    async def eval_code(self, ctx, *, code: str):
        """Evaluate Python code (DANGEROUS - Owner only)"""
        try:
            # Remove code block formatting if present
            if code.startswith("```python"):
                code = code[9:-3]
            elif code.startswith("```"):
                code = code[3:-3]
            
            result = eval(code)
            
            embed = discord.Embed(
                title="✅ Evaluation Result",
                description=f"```python\n{result}\n```",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Evaluation Error",
                description=f"```python\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="reload")
    async def reload_cog(self, ctx, cog_name: str):
        """Reload a specific cog"""
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Reloaded cog: **{cog_name}**")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload **{cog_name}**: {str(e)}")

    @commands.command(name="reloadall")
    async def reload_all(self, ctx):
        """Reload all cogs"""
        success = []
        failed = []
        
        for cog_name in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(cog_name)
                success.append(cog_name.split('.')[-1])
            except Exception as e:
                failed.append(f"{cog_name.split('.')[-1]}: {str(e)}")
        
        embed = discord.Embed(title="🔄 Reload Results", color=discord.Color.blue())
        
        if success:
            embed.add_field(name="✅ Success", value="\n".join(success), inline=False)
        if failed:
            embed.add_field(name="❌ Failed", value="\n".join(failed), inline=False)
        
        await ctx.send(embed=embed)

    # ==================== FUN TROLL COMMANDS ====================

    @commands.command(name="hack")
    async def fake_hack(self, ctx, member: discord.Member):
        """Fake 'hack' a user (just for fun)"""
        messages = [
            f"🔓 Accessing {member.mention}'s account...",
            "📡 Connecting to mainframe...",
            "💾 Downloading data...",
            "🔐 Bypassing security...",
            "⚠️ FIREWALL DETECTED!",
            "🛡️ Deploying countermeasures...",
            "✅ Access granted!",
            f"📊 {member.display_name}'s secrets:\n"
            f"```\n"
            f"Favorite Game: {random.choice(['Tic-Tac-Toe', 'Connect 4', 'Wordle', 'Typing Race'])}\n"
            f"Lucky Number: {random.randint(1, 100)}\n"
            f"Secret Wish: More PsyCoins\n"
            f"Hidden Talent: Being awesome\n"
            f"```"
        ]
        
        msg = await ctx.send("Initiating hack sequence...")
        
        for message in messages:
            await asyncio.sleep(2)
            await msg.edit(content=message)
        
        await asyncio.sleep(3)
        await ctx.send(f"{member.mention} You've been hacked! 😈\n(Just kidding, all your data is safe! 😄)")

    @commands.command(name="roastme")
    async def ultimate_roast(self, ctx):
        """Get the ultimate roast"""
        roasts = [
            "You're so powerful, even the bot fears you... just kidding, you're still a potato. 🥔",
            "I'd call you a tool, but even tools have uses.",
            "You're proof that even gods can make mistakes.",
            "Your code is like your personality - full of bugs.",
            "You're the human equivalent of a participation trophy.",
            "If you were a spice, you'd be flour.",
            "You're the reason the gene pool needs a lifeguard."
        ]
        
        await ctx.send(f"{ctx.author.mention}\n{random.choice(roasts)}")

    @commands.command(name="vibecheck", aliases=["vc"])
    async def vibe_check(self, ctx, member: Optional[discord.Member] = None):
        """Check someone's vibe"""
        target = member or ctx.author
        
        vibes = [
            ("✨ IMMACULATE", "10/10", discord.Color.gold()),
            ("🔥 FIRE", "9/10", discord.Color.orange()),
            ("😎 COOL", "8/10", discord.Color.blue()),
            ("👍 GOOD", "7/10", discord.Color.green()),
            ("😐 MID", "5/10", discord.Color.greyple()),
            ("😬 SUS", "3/10", discord.Color.red()),
            ("💀 FAILED", "0/10", discord.Color.dark_red())
        ]
        
        vibe, score, color = random.choice(vibes)
        
        embed = discord.Embed(
            title="🌊 VIBE CHECK 🌊",
            description=f"{target.mention}\n\n**Status:** {vibe}\n**Score:** {score}",
            color=color
        )
        
        await ctx.send(embed=embed)

    # ==================== HELP COMMAND ====================

    @commands.command(name="ownerhelp")
    async def owner_help(self, ctx):
        """Show all secret owner commands"""
        embed = discord.Embed(
            title="👑 Secret Owner Commands",
            description="Commands only you can use!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Economy Management",
            value="```\n"
                  "L!godmode - Max out your stats\n"
                  "L!setcoins @user <amount> - Set balance\n"
                  "L!addcoins @user <amount> - Add coins\n"
                  "L!removecoins @user <amount> - Remove coins\n"
                  "L!resetcoins @user - Reset economy data\n"
                  "L!giveitem @user <item_id> [qty] - Give items\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🤖 Bot Status",
            value="```\n"
                  "L!status <type> <text> - Change activity\n"
                  "L!presence <status> - Change online status\n"
                  "L!nickname <name> - Change bot nickname\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Fun & Chaos",
            value="```\n"
                  "L!raincoins [amount] - Give everyone coins\n"
                  "L!chaos - Random rewards for all\n"
                  "L!lottery [prize] - Random winner\n"
                  "L!cursed - Send cursed message\n"
                  "L!spawn - Spawn raid boss\n"
                  "L!hack @user - Fake hack (fun)\n"
                  "L!roastme - Ultimate roast\n"
                  "L!vibe [@user] - Vibe check\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🎣 Fishing Management",
            value="```\n"
                  "L!fishing_tournament <mode> <mins> - Start tournament\n"
                  "  Modes: biggest, most, rarest\n"
                  "  Duration: 1-30 minutes\n"
                  "Note: Random tournaments spawn automatically every 2-4h\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Server Management",
            value="```\n"
                  "L!purge [amount] - Delete messages\n"
                  "L!announce <#channel> <msg> - Send announcement\n"
                  "L!dm @user <message> - DM a user\n"
                  "L!stats - Bot statistics\n"
                  "L!stats update - Refresh bot stats\n"
                  "L!update global - Update global leaderboard\n"
                  "L!update stats - Update bot stats\n"
                  "L!countset <number> - Set counting number\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Debug",
            value="```\n"
                  "L!eval <code> - Evaluate Python code\n"
                  "L!reload <cog> - Reload specific cog\n"
                  "L!reloadall - Reload all cogs\n"
                  "```",
            inline=False
        )
        
        embed.set_footer(text="These commands are secret! Use them wisely 😈")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Owner(bot))
