# FARMING SYSTEM EXPANSION
# Add these methods to the Simulations class

async def farm_water_action(self, interaction: discord.Interaction, plot: int = None):
    """Water crops"""
    farm = self.get_farm(interaction.user.id)
    
    if not farm["plots"]:
        await interaction.response.send_message("❌ No crops planted!", ephemeral=True)
        return
    
    water_cost = 1
    if farm["water_level"] < water_cost:
        await interaction.response.send_message(
            f"❌ Not enough water! You have {farm['water_level']} 💧\n"
            "💡 Buy a bucket or sprinkler from `/farm shop`!",
            ephemeral=True
        )
        return
    
    # Water all plots or specific plot
    watered = []
    if plot:
        if str(plot) in farm["plots"]:
            farm["plots"][str(plot)]["watered"] = True
            watered.append(plot)
            farm["water_level"] -= water_cost
        else:
            await interaction.response.send_message(f"❌ No crop in plot {plot}!", ephemeral=True)
            return
    else:
        for plot_num in farm["plots"]:
            if farm["water_level"] >= water_cost:
                farm["plots"][plot_num]["watered"] = True
                watered.append(plot_num)
                farm["water_level"] -= water_cost
    
    self.save_data()
    
    embed = discord.Embed(
        title="💧 Crops Watered!",
        description=f"Watered {len(watered)} plots!\n"
                   f"Remaining water: {farm['water_level']} 💧\n\n"
                   f"Watered crops grow faster!",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed)

async def farm_shop_action(self, interaction: discord.Interaction, item: str = None):
    """Shop for tools and animals"""
    if not item:
        # Show shop catalog
        embed = discord.Embed(
            title="🏪 Farm Shop",
            description="Buy tools, equipment, and animals!\nUse `/farm shop item:<name>` to purchase",
            color=discord.Color.gold()
        )
        
        # Tools
        tools_list = "\n".join([
            f"**{key}**: {data['name']} - {data['cost']} 🌾"
            for key, data in list(self.tools.items())[:6]
        ])
        embed.add_field(name="🔧 Tools & Equipment", value=tools_list, inline=False)
        
        # Animals  
        animals_list = "\n".join([
            f"**{key}**: {data['name']} - {data['cost']} 🌾"
            for key, data in list(self.animals.items())[:6]
        ])
        embed.add_field(name="🐔 Animals", value=animals_list, inline=False)
        
        await interaction.response.send_message(embed=embed)
        return
    
    # Purchase item
    item = item.lower().replace(" ", "_")
    farm = self.get_farm(interaction.user.id)
    
    # Check if it's a tool
    if item in self.tools:
        tool_data = self.tools[item]
        
        # Check if already owned
        if item in farm["tools"]:
            await interaction.response.send_message(f"❌ You already own {tool_data['name']}!", ephemeral=True)
            return
        
        # Check Farm Tokens
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            user_id = str(interaction.user.id)
            farm_tokens = economy_cog.economy_data.get(user_id, {}).get("farm_tokens", 0)
            
            if farm_tokens < tool_data["cost"]:
                await interaction.response.send_message(
                    f"❌ Need {tool_data['cost']} 🌾 Farm Tokens!\nYou have: {farm_tokens} 🌾",
                    ephemeral=True
                )
                return
            
            # Purchase
            economy_cog.economy_data[user_id]["farm_tokens"] -= tool_data["cost"]
            economy_cog.economy_dirty = True
            await economy_cog.save_economy()
        
        farm["tools"].append(item)
        self.save_data()
        
        await interaction.response.send_message(
            f"✅ Purchased {tool_data['name']} for {tool_data['cost']} 🌾!",
        )
    
    # Check if it's an animal
    elif item in self.animals:
        animal_data = self.animals[item]
        
        # Check Farm Tokens
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            user_id = str(interaction.user.id)
            farm_tokens = economy_cog.economy_data.get(user_id, {}).get("farm_tokens", 0)
            
            if farm_tokens < animal_data["cost"]:
                await interaction.response.send_message(
                    f"❌ Need {animal_data['cost']} 🌾 Farm Tokens!\nYou have: {farm_tokens} 🌾",
                    ephemeral=True
                )
                return
            
            # Purchase
            economy_cog.economy_data[user_id]["farm_tokens"] -= animal_data["cost"]
            economy_cog.economy_dirty = True
            await economy_cog.save_economy()
        
        # Add animal
        animal_id = len(farm["animals"]) + 1
        farm["animals"][str(animal_id)] = {
            "type": item,
            "last_fed": datetime.now().isoformat(),
            "last_produced": datetime.now().isoformat(),
            "health": 100
        }
        self.save_data()
        
        await interaction.response.send_message(
            f"✅ Purchased {animal_data['name']} for {animal_data['cost']} 🌾!\n"
            f"Remember to feed it regularly!",
        )
    else:
        await interaction.response.send_message("❌ Invalid item!", ephemeral=True)

async def farm_animals_action(self, interaction: discord.Interaction):
    """View animals"""
    farm = self.get_farm(interaction.user.id)
    
    if not farm["animals"]:
        embed = discord.Embed(
            title="🐔 Your Animals",
            description="You don't have any animals yet!\n\n"
                       "Buy animals from `/farm shop`",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="🐔 Your Animals",
        description=f"Total Animals: {len(farm['animals'])}",
        color=discord.Color.orange()
    )
    
    for animal_id, animal in farm["animals"].items():
        animal_data = self.animals[animal["type"]]
        last_fed = datetime.fromisoformat(animal["last_fed"])
        hours_since_fed = (datetime.now() - last_fed).total_seconds() / 3600
        
        status = "😊 Happy" if hours_since_fed < 24 else "😢 Hungry"
        
        embed.add_field(
            name=f"#{animal_id}: {animal_data['name']}",
            value=f"Health: {animal['health']}%\n"
                  f"Status: {status}\n"
                  f"Produces: {animal_data['product']}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

async def farm_feed_action(self, interaction: discord.Interaction):
    """Feed all animals"""
    farm = self.get_farm(interaction.user.id)
    
    if not farm["animals"]:
        await interaction.response.send_message("❌ No animals to feed!", ephemeral=True)
        return
    
    # Calculate total feed cost
    total_cost = sum(self.animals[a["type"]]["feed_cost"] for a in farm["animals"].values())
    
    # Check Farm Tokens
    economy_cog = self.bot.get_cog("Economy")
    if economy_cog:
        user_id = str(interaction.user.id)
        farm_tokens = economy_cog.economy_data.get(user_id, {}).get("farm_tokens", 0)
        
        if farm_tokens < total_cost:
            await interaction.response.send_message(
                f"❌ Need {total_cost} 🌾 to feed all animals!\nYou have: {farm_tokens} 🌾",
                ephemeral=True
            )
            return
        
        # Feed animals
        economy_cog.economy_data[user_id]["farm_tokens"] -= total_cost
        economy_cog.economy_dirty = True
        await economy_cog.save_economy()
    
    # Update animals
    for animal in farm["animals"].values():
        animal["last_fed"] = datetime.now().isoformat()
        animal["health"] = min(100, animal["health"] + 20)
    
    self.save_data()
    
    await interaction.response.send_message(
        f"✅ Fed {len(farm['animals'])} animals for {total_cost} 🌾!\n"
        f"Animals are now healthy and producing!"
    )

async def farm_collect_action(self, interaction: discord.Interaction):
    """Collect animal products"""
    farm = self.get_farm(interaction.user.id)
    
    if not farm["animals"]:
        await interaction.response.send_message("❌ No animals!", ephemeral=True)
        return
    
    collected = []
    total_value = 0
    
    for animal_id, animal in farm["animals"].items():
        animal_data = self.animals[animal["type"]]
        last_produced = datetime.fromisoformat(animal["last_produced"])
        minutes_since = (datetime.now() - last_produced).total_seconds() / 60
        
        if minutes_since >= animal_data["produce_time"]:
            # Check if fed recently
            last_fed = datetime.fromisoformat(animal["last_fed"])
            hours_since_fed = (datetime.now() - last_fed).total_seconds() / 3600
            
            if hours_since_fed > 24:
                continue  # Hungry animals don't produce
            
            product = animal_data["product"]
            value = animal_data["product_value"]
            
            farm["animal_products"][product] = farm["animal_products"].get(product, 0) + 1
            total_value += value
            collected.append(f"{product} (+{value} 🌾)")
            
            animal["last_produced"] = datetime.now().isoformat()
    
    if not collected:
        await interaction.response.send_message(
            "❌ No products ready!\n\n"
            "Make sure animals are:\n"
            "1. Fed recently (< 24 hours)\n"
            f"2. Past production time",
            ephemeral=True
        )
        return
    
    self.save_data()
    
    # Give Farm Tokens
    farm_tokens = total_value // 10
    economy_cog = self.bot.get_cog("Economy")
    if economy_cog:
        user_id = str(interaction.user.id)
        economy_cog.economy_data[user_id]["farm_tokens"] = economy_cog.economy_data[user_id].get("farm_tokens", 0) + farm_tokens
        economy_cog.economy_dirty = True
        await economy_cog.save_economy()
    
    embed = discord.Embed(
        title="📦 Products Collected!",
        description="\n".join(collected) + f"\n\n**Earned:** {farm_tokens} 🌾 Farm Tokens!",
        color=discord.Color.gold()
    )
    
    await interaction.response.send_message(embed=embed)

async def farm_upgrade_action(self, interaction: discord.Interaction):
    """Upgrade farm"""
    farm = self.get_farm(interaction.user.id)
    
    # Calculate upgrade cost
    current_plots = farm["max_plots"]
    upgrade_cost = current_plots * 100
    
    embed = discord.Embed(
        title="⬆️ Farm Upgrades",
        description=f"**Current Max Plots:** {current_plots}\n"
                   f"**Upgrade to:** {current_plots + 3} plots\n"
                   f"**Cost:** {upgrade_cost} 🌾 Farm Tokens",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Your Stats",
        value=f"Level: {farm['level']}\n"
              f"XP: {farm['xp']}\n"
              f"Tools: {len(farm['tools'])}\n"
              f"Animals: {len(farm['animals'])}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

async def farm_stats_action(self, interaction: discord.Interaction):
    """View farm statistics"""
    farm = self.get_farm(interaction.user.id)
    
    # Calculate stats
    total_harvests = sum(farm["inventory"].values())
    total_animals = len(farm["animals"])
    total_tools = len(farm["tools"])
    
    # Get Farm Tokens
    economy_cog = self.bot.get_cog("Economy")
    farm_tokens = 0
    if economy_cog:
        user_id = str(interaction.user.id)
        farm_tokens = economy_cog.economy_data.get(user_id, {}).get("farm_tokens", 0)
    
    embed = discord.Embed(
        title=f"📊 {interaction.user.display_name}'s Farm Stats",
        color=discord.Color.green()
    )
    
    embed.add_field(name="🌾 Level", value=str(farm["level"]), inline=True)
    embed.add_field(name="⭐ XP", value=str(farm["xp"]), inline=True)
    embed.add_field(name="🌾 Farm Tokens", value=str(farm_tokens), inline=True)
    embed.add_field(name="🚜 Plots", value=f"{len(farm['plots'])}/{farm['max_plots']}", inline=True)
    embed.add_field(name="🔧 Tools", value=str(total_tools), inline=True)
    embed.add_field(name="🐔 Animals", value=str(total_animals), inline=True)
    embed.add_field(name="📦 Inventory", value=str(total_harvests) + " items", inline=True)
    embed.add_field(name="💧 Water", value=str(farm["water_level"]), inline=True)
    embed.add_field(name="🌸 Season", value=self.seasons[farm["season"]]["name"], inline=True)
    
    await interaction.response.send_message(embed=embed)
