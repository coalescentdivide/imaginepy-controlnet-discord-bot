import asyncio
import io
import os
import random

import aiohttp
from colorama import Fore, Back, Style as s
import discord
from discord import Embed, File
from discord.ext import commands
from dotenv import load_dotenv
from imaginepy import AsyncImagine, Control, Style


def parse_arguments(command_args: str):
    args = command_args.split()
    parsed_args = {
        'prompt': '',
        'negative': 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry',
        'scale': 7.5,
        'control': Control.DEPTH,
        'style': Style.IMAGINE_V1,
        'seed': str(random.randint(1, 9999999999)),
    }
    current_key = 'prompt'
    for arg in args:
        if arg.startswith('--'):
            current_key = arg[2:]
        else:
            if current_key == 'scale':
                parsed_args[current_key] = float(arg)
            elif current_key == 'control':
                parsed_args[current_key] = Control[arg.upper()]
            elif current_key == 'style':
                parsed_args[current_key] = Style[arg.upper()]
            else:
                if parsed_args[current_key] is None:
                    parsed_args[current_key] = arg
                else:
                    parsed_args[current_key] += ' ' + arg
    return parsed_args

load_dotenv()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def controls(ctx):
    controls = "\n".join(f"{control.name}" for control in Control)
    await ctx.send(f"Available control values:\n```\n{controls}\n```")

@bot.command()
async def styles(ctx):
    styles = "\n".join(f"{style.name}" for style in Style)
    await ctx.send(f"Available styles:\n```\n{styles}\n```")

@bot.command()
async def remix(ctx, *, command_args: str):
    print(f"{ctx.author.name} remixing an image")
    image = None
    if ctx.message.reference and ctx.message.reference.resolved:
        replied_message = ctx.message.reference.resolved
        if len(replied_message.attachments) > 0:
            image = await replied_message.attachments[0].read()
    elif len(ctx.message.attachments) > 0:
        image = await ctx.message.attachments[0].read()
    if image:
        imagine = AsyncImagine()
    else:
        await ctx.send("Error: No image found in the message or the replied message. Please attach an image to your message or reply to a message with an image.")
        return
    try:
        args = parse_arguments(command_args)
        retries = 1
        backoff_factor = 2
        wait_time = retries * backoff_factor
        while retries <= 3:
            try:
                remixed_image = await asyncio.wait_for(imagine.controlnet(image=image, prompt=args['prompt'], control=args['control'], negative=args['negative'], cfg=args['scale'], style=args['style'], seed=args['seed']), timeout=10)
                info = f"⚙️{args['control'].name} ⚖️{args['scale']} 🎨{args['style'].name} 🌱{args['seed']}"
                combined_prompt = f"{args['prompt']} {args['style'].value[3]}" if {args['style'].value[3]} is None else args['prompt']
                prompt = f"Prompt:\n{combined_prompt}\n\nNegative Prompt:\n{args['negative'] or 'None'}"
                file = File(fp=io.BytesIO(remixed_image), filename="remixed_image.png")
                embed = Embed()
                embed.set_author(name=info)
                embed.set_image(url=f"attachment://{file.filename}")
                embed.set_footer(text=prompt)
                await ctx.send(embed=embed, file=file)
                print(f"{Fore.GREEN}Successfully processed image!{s.RESET_ALL}\n"
                    f"{Fore.YELLOW}Prompt:{s.RESET_ALL} {Back.WHITE}{Fore.BLACK}{combined_prompt}{s.RESET_ALL}\n"
                    f"{Fore.YELLOW}Negative:{s.RESET_ALL} {Back.WHITE}{Fore.RED}{args['negative']}{s.RESET_ALL}\n"
                    f"{Fore.YELLOW}Seed:{s.RESET_ALL} {args['seed']}\n"
                    f"{Fore.YELLOW}Control:{s.RESET_ALL} {args['control'].name}\n"
                    f"{Fore.YELLOW}Style:{s.RESET_ALL} {args['style'].name}")
                break
            except aiohttp.ClientResponseError as e:
                print(f"Error {e.status}: {e.message}. Retry attempt {retries}. Retrying in {wait_time} seconds...")
                if retries < 3:
                    await asyncio.sleep(wait_time)
                    retries += 1
            except asyncio.TimeoutError:
                print(f"Timeout Error: Retry attempt {retries}. Retrying in {wait_time} seconds...")
                if retries < 3:
                    await asyncio.sleep(wait_time)
                    retries += 1
                else:
                    await ctx.send(f"Error: {e.status} {e.message}. Try again later")
                    break
    except Exception as e:
        print(type(e), e)
    finally:
        if imagine:
            await imagine.close()

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
