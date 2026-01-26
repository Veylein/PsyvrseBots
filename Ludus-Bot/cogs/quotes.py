import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import textwrap

class Quotes(commands.Cog):
    """Generate quote images from messages"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="makequote", aliases=["createquote"])
    async def make_quote(self, ctx):
        """📸 Create a quote image from a replied message"""
        
        # Check if this is a reply
        if not ctx.message.reference:
            await ctx.send("❌ You need to **reply** to a message to create a quote!\n"
                          "💡 Reply to any message and type `L!makequote`")
            return
        
        # Get the referenced message
        try:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except:
            await ctx.send("❌ Couldn't fetch the replied message!")
            return
        
        # Check if message has content
        if not replied_msg.content:
            await ctx.send("❌ That message has no text content!")
            return
        
        await ctx.send("🎨 Generating quote image...")
        
        # Generate the quote image
        image_bytes = await self.generate_quote_image(
            replied_msg.author,
            replied_msg.content,
            replied_msg.created_at
        )
        
        # Send the image
        file = discord.File(fp=image_bytes, filename="quote.png")
        embed = discord.Embed(
            title="💬 Quote Generated",
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://quote.png")
        embed.set_footer(text=f"Quoted by {ctx.author.name}")
        
        await ctx.send(file=file, embed=embed)
    
    async def generate_quote_image(self, user, text, timestamp):
        """Generate a quote image with user avatar and text"""
        
        # Image dimensions
        width = 800
        padding = 40
        avatar_size = 100
        
        # Download user avatar
        async with aiohttp.ClientSession() as session:
            async with session.get(str(user.display_avatar.url)) as resp:
                avatar_data = await resp.read()
        
        avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
        avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        
        # Make avatar circular
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_img.putalpha(mask)
        
        # Wrap text
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            font_username = ImageFont.truetype("arialbd.ttf", 28)
            font_date = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()
            font_username = ImageFont.load_default()
            font_date = ImageFont.load_default()
        
        # Wrap text to fit width
        max_chars = 60
        wrapped_text = textwrap.fill(text, width=max_chars)
        
        # Calculate height needed
        temp_img = Image.new('RGBA', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        text_bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=10)
        text_height = text_bbox[3] - text_bbox[1]
        
        height = padding * 4 + avatar_size + text_height + 60
        
        # Create the image
        img = Image.new('RGBA', (width, height), color=(47, 49, 54, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw background card
        card_color = (54, 57, 63, 255)
        draw.rounded_rectangle(
            [(padding, padding), (width - padding, height - padding)],
            radius=20,
            fill=card_color
        )
        
        # Paste avatar
        avatar_x = padding + 20
        avatar_y = padding + 20
        img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)
        
        # Draw username
        username_x = avatar_x + avatar_size + 20
        username_y = avatar_y + 15
        draw.text((username_x, username_y), user.display_name, 
                 fill=(255, 255, 255, 255), font=font_username)
        
        # Draw timestamp
        time_str = timestamp.strftime("%b %d, %Y at %I:%M %p")
        draw.text((username_x, username_y + 35), time_str, 
                 fill=(153, 170, 181, 255), font=font_date)
        
        # Draw quote text
        text_y = avatar_y + avatar_size + 30
        draw.multiline_text((padding + 30, text_y), wrapped_text, 
                          fill=(220, 221, 222, 255), font=font, spacing=10)
        
        # Draw accent line
        accent_color = (88, 101, 242, 255)  # Discord blurple
        draw.rectangle([(padding + 15, text_y), (padding + 20, text_y + text_height)], 
                      fill=accent_color)
        
        # Convert to bytes
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        return output

async def setup(bot):
    await bot.add_cog(Quotes(bot))
