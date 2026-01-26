with open('cogs/psyvrse_tcg.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find first occurrence of setup function
first_setup_pos = content.find('async def setup(bot):')

if first_setup_pos != -1:
    # Keep everything before setup, then add clean setup
    clean_content = content[:first_setup_pos] + 'async def setup(bot):\n    await bot.add_cog(PsyverseTCG(bot))\n'
    
    with open('cogs/psyvrse_tcg.py', 'w', encoding='utf-8') as f:
        f.write(clean_content)
    
    print(f"✅ File cleaned! Removed {len(content) - len(clean_content)} characters of duplicate code")
else:
    print("❌ Setup function not found!")
