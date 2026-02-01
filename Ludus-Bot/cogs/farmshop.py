import discord
from discord.ext import commands
from discord import app_commands
import os
import json

class FarmShop(commands.Cog):
    """Simple farm shop: buy seeds and create/list personal seed listings."""

    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.shops_file = os.path.join(data_dir, "shops.json")
        self.shops = self.load_shops()

    def load_shops(self):
        if os.path.exists(self.shops_file):
            try:
                with open(self.shops_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_shops(self):
        try:
            with open(self.shops_file, 'w') as f:
                json.dump(self.shops, f, indent=2)
        except Exception as e:
            print(f"Error saving shops: {e}")

    @app_commands.command(name="farmshop", description="Farm shop: buy seeds, create/list shops")
    @app_commands.choices(action=[
        app_commands.Choice(name="Buy Seed", value="buyseed"),
        app_commands.Choice(name="Create Listing", value="create"),
        app_commands.Choice(name="List Shops", value="list"),
        app_commands.Choice(name="Buy Listing", value="buylisting"),
    ])
    @app_commands.describe(crop="Crop id (e.g., wheat, corn)", quantity="Quantity (for seeds or listing)", price="Price per unit (for listing)")
    async def farmshop(self, interaction: discord.Interaction, action: app_commands.Choice[str], crop: str = None, quantity: int = 1, price: int = 0):
        await interaction.response.defer()
        action_value = action.value if isinstance(action, app_commands.Choice) else action

        farming_cog = self.bot.get_cog("Farming")
        economy = self.bot.get_cog("Economy")

        if action_value == "buyseed":
            if not farming_cog:
                await interaction.followup.send("Farming system not available.", ephemeral=True)
                return
            if not economy:
                await interaction.followup.send("Economy system not available.", ephemeral=True)
                return
            crop_id = (crop or "").lower()
            if crop_id not in farming_cog.manager.crops:
                await interaction.followup.send(f"Unknown crop: {crop}", ephemeral=True)
                return
            qty = max(1, quantity)
            seed_cost = farming_cog.manager.crops[crop_id]["seed_cost"] * qty
            if economy.get_balance(interaction.user.id) < seed_cost:
                await interaction.followup.send(f"Not enough PsyCoins to buy {qty} {crop_id} seeds (cost: {seed_cost}).", ephemeral=True)
                return
            economy.remove_coins(interaction.user.id, seed_cost)
            farming_cog.manager.add_seeds(interaction.user.id, crop_id, qty)
            await interaction.followup.send(f"Purchased {qty} x {crop_id} seeds for {seed_cost} PsyCoins.")
            return

        if action_value == "create":
            # Create a personal listing (owner must have seeds to list)
            if not farming_cog:
                await interaction.followup.send("Farming system not available.", ephemeral=True)
                return
            crop_id = (crop or "").lower()
            if crop_id not in farming_cog.manager.crops:
                await interaction.followup.send(f"Unknown crop: {crop}", ephemeral=True)
                return
            qty = max(1, quantity)
            # Check user has seeds
            if farming_cog.manager.get_seed_count(interaction.user.id, crop_id) < qty:
                await interaction.followup.send(f"You don't have {qty} {crop_id} seeds to list.", ephemeral=True)
                return
            # Remove seeds from user and create listing
            farming_cog.manager.remove_seeds(interaction.user.id, crop_id, qty)
            listing = {
                "id": len(self.shops) + 1,
                "owner": str(interaction.user.id),
                "crop": crop_id,
                "quantity": qty,
                "price": max(1, price)
            }
            self.shops.append(listing)
            self.save_shops()
            await interaction.followup.send(f"Created listing #{listing['id']}: {qty} x {crop_id} @ {listing['price']} PsyCoins each.")
            return

        if action_value == "list":
            if not self.shops:
                await interaction.followup.send("No listings available.", ephemeral=True)
                return
            lines = []
            for s in self.shops[-20:]:
                owner = await self.bot.fetch_user(int(s['owner']))
                lines.append(f"#{s['id']}: {s['quantity']} x {s['crop']} @ {s['price']} each — seller: {owner.display_name}")
            await interaction.followup.send("\n".join(lines))
            return

        if action_value == "buylisting":
            # Here, 'crop' param is used as listing id
            try:
                listing_id = int((crop or "0"))
            except Exception:
                await interaction.followup.send("Specify listing id in the `crop` field to buy from. Example: /farmshop action:buylisting crop:1 quantity:2", ephemeral=True)
                return
            listing = next((l for l in self.shops if l['id'] == listing_id), None)
            if not listing:
                await interaction.followup.send("Listing not found.", ephemeral=True)
                return
            qty = max(1, quantity)
            if qty > listing['quantity']:
                await interaction.followup.send(f"Seller only has {listing['quantity']} units.", ephemeral=True)
                return
            total = listing['price'] * qty
            if not economy:
                await interaction.followup.send("Economy system not available.", ephemeral=True)
                return
            if economy.get_balance(interaction.user.id) < total:
                await interaction.followup.send(f"Not enough PsyCoins (need {total}).", ephemeral=True)
                return
            # Transfer coins
            economy.remove_coins(interaction.user.id, total)
            economy.add_coins(int(listing['owner']), total, "farmshop_sale")
            # Transfer seeds to buyer
            if farming_cog:
                farming_cog.manager.add_seeds(interaction.user.id, listing['crop'], qty)
            listing['quantity'] -= qty
            if listing['quantity'] <= 0:
                self.shops = [s for s in self.shops if s['id'] != listing_id]
            self.save_shops()
            await interaction.followup.send(f"Purchased {qty} x {listing['crop']} for {total} PsyCoins from listing #{listing_id}.")
            return

async def setup(bot):
    await bot.add_cog(FarmShop(bot))
