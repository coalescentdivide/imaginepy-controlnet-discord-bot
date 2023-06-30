import asyncio
import io
import os
import random

import discord
import httpx
from colorama import Back, Fore
from colorama import Style as s
from discord import Activity, ActivityType, Embed, File
from discord.ext import commands
from dotenv import load_dotenv

from imaginepy import AsyncImagine, Mode, Model, Style, utils

load_dotenv()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.remove_command('help')
task_queue = asyncio.Queue()
queue_counter = 0


def parse_arguments(command_args: str):
    args = command_args.split()
    parsed_args = {
        'prompt': '',
        'model': Model.V3,
        'negative': None,
        'strength': 0,
        'scale': 7.5,
        'control': Mode.CANNY,
        'style': Style.NO_STYLE,
        'seed': str(random.randint(1, 9999999999))
    }
    current_key = 'prompt'
    for arg in args:
        if arg.startswith('--'):
            current_key = arg[2:]
        else:
            if current_key == 'scale':
                try:
                    parsed_args[current_key] = utils.get_cfg(float(arg))
                except ValueError:
                    raise ValueError(f"Invalid scale. Range: 0.0-16.0")
            elif current_key == 'strength':
                try:
                    parsed_args[current_key] = utils.get_strength(int(arg))
                except ValueError:
                    raise ValueError(f"Invalid strength. Must be an integer between 0-100")
            elif current_key == 'model':
                parsed_args[current_key] = Model[arg.upper()]
            elif current_key == 'control':
                parsed_args[current_key] = Mode[arg.upper()]
            elif current_key == 'style':
                style_str = arg.upper()
                if style_str == "RANDOM":
                    random_style = random.choice(list(Style))
                    while random_style == Style.RANDOM:
                        random_style = random.choice(list(Style))
                    parsed_args[current_key] = random_style
                else:
                    parsed_args[current_key] = Style[style_str]
            elif current_key == 'seed':
                try:
                    parsed_args[current_key] = int(arg)
                except ValueError:
                    raise ValueError(f"Invalid seed value: {arg}")
            else:
                if parsed_args[current_key] is None:
                    parsed_args[current_key] = arg
                else:
                    parsed_args[current_key] += ' ' + arg
    if parsed_args['negative'] is None:
        parsed_args['negative'] = 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry'
    return parsed_args



async def queue():
    global queue_counter
    while True:
        func, ctx, command_args = await task_queue.get()
        try:
            await func(ctx, command_args)
        except Exception as e:
            print(f"{Fore.RED}{s.BRIGHT}Error processing task: {e}{s.RESET_ALL}")
        finally:
            task_queue.task_done()
            queue_counter -= 1


@bot.event
async def on_ready():
    print(f"{Fore.CYAN}{bot.user} has connected to Discord!{s.RESET_ALL}")
    await bot.change_presence(activity=Activity(type=ActivityType.watching, name="for !remix + image"))
    bot.loop.create_task(queue())

@bot.command()
async def styles(ctx):
    models = "\n".join(f"{model.name}" for model in Model)
    styles = "\n".join(f"{style.name}" for style in Style)
    await ctx.send(f"Available models:\n```\n{models}\n```\n\nAvailable styles:\n```\n{styles}\n```")

@bot.command()
async def remix(ctx, *, command_args: str = ""):
    global queue_counter
    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0]
    elif ctx.message.reference and ctx.message.reference.resolved.attachments:
        image = ctx.message.reference.resolved.attachments[0] 
    if not image:
        example_model = random.choice(list(Model)).name.lower()
        example_control = random.choice(list(Mode)).name.lower()
        example_style = random.choice(list(Style)).name.lower()
        embed = Embed(title="Use with an image attachment or reply to an image", description="!remix [optional prompt] [optional arguments]\n`!styles` will show all available models and styles")        
        embed.add_field(name="🖌️ Use a style or choose a random one (optional):", value="`--style random`\n", inline=False)
        embed.add_field(name="💾 Change model (optional):", value="`--model lyriel`", inline=False)
        embed.add_field(name="⚙️ Set the control model:\n", value="`--control depth`\n`--control canny`\n`--control line_art`\n`--control scribble`\n`--control pose`", inline=False)
        embed.add_field(name="❌ Choose a negative prompt (optional):", value="`--negative ugly`\n", inline=False)
        embed.add_field(name="⚖️ Change the guidance scale. Higher values increase the strength of your prompt. (Range: 0.0-10.0)", value="`--scale 8`\n", inline=False)
        embed.add_field(name="💪 Change the strength of the image to be remixed. Higher values change the image less. (Range: 0-100)", value="`--strength 50`\n", inline=False)
        embed.add_field(name="Example", value=f"`!remix cat --control {example_control} --model {example_model} --negative dog --style {example_style} --strength 10 --scale 8 --seed 12345`\n", inline=False)
        embed.add_field(name="", value=f"🔗[Github](https://github.com/coalescentdivide/imaginepy-controlnet-discord-bot/tree/main)", inline=False)
        embed.set_footer(text="Made by Trypsky")
        await ctx.send(embed=embed)
    else:
        await task_queue.put((queue_remix, ctx, command_args))
        queue_counter += 1
        print(f"{Fore.BLUE}{s.BRIGHT}Queue size: {queue_counter}{s.RESET_ALL}")

async def queue_remix(ctx, command_args: str):
    print(f"User {Fore.RED}{s.BRIGHT}{ctx.author.name}{s.RESET_ALL} remixing an image")
    image = None
    if ctx.message.reference and ctx.message.reference.resolved:
        replied_message = ctx.message.reference.resolved
        if len(replied_message.attachments) > 0:
            image = await replied_message.attachments[0].read()
    elif len(ctx.message.attachments) > 0:
        image = await ctx.message.attachments[0].read()
    imagine = AsyncImagine()

    MAX_CONNECTION_RETRIES = 3
    MAX_SESSION_RETRIES = 2
    BACKOFF_FACTOR = 2
    session_retries = 0

    while session_retries < MAX_SESSION_RETRIES:
        connection_retries = 0
        success = False

        while connection_retries < MAX_CONNECTION_RETRIES:
            try:
                args = None
                try:
                    args = parse_arguments(command_args)
                except ValueError as ve:
                    await ctx.send(str(ve))
                    return
                if not args['prompt'] and image:
                    try:
                        print(f"{Fore.WHITE}{Back.MAGENTA}No prompt found. Interrogating Image...{s.RESET_ALL}")
                        generated_prompt = await asyncio.wait_for(imagine.interrogator(content=image), timeout=10)
                        first_block = generated_prompt.split(',', 1)[0]
                        args['prompt'] = first_block
                    except asyncio.TimeoutError:
                        args['prompt'] = "amazing"
                remixed_image = await asyncio.wait_for(imagine.controlnet(content=image, prompt=args['prompt'], model=args['model'], mode=args['control'], negative=args['negative'], cfg=args['scale'], style=args['style'], strength=args['strength'], seed=args['seed']), timeout=15)
                info = f"🧠{ctx.author.mention}⚙️`{args['control'].name.lower()}`💾`{args['model'].name.lower()}`⚖️`{args['scale']}`💪`{args['strength']}`🎨`{args['style'].name.lower()}`🌱`{args['seed']}`"
                combined_prompt = f"{args['prompt']} {args['style'].value[3]}" if args['style'].value[3] is not None else args['prompt']                
                default_negative = 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry'
                if args['negative'] != default_negative:
                    prompt = f"{combined_prompt}\n\nNegative Prompt:\n{args['negative']}"
                else:
                    prompt = f"\n{combined_prompt}"
                print(f"{Fore.GREEN}Successfully processed image with the following settings:{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Prompt: {s.RESET_ALL}{Back.WHITE}{Fore.BLACK}{combined_prompt}{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Negative: {s.RESET_ALL}{Fore.RED}{args['negative']}{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Model: {s.RESET_ALL}{args['model'].name}{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Seed: {s.RESET_ALL}{args['seed']}\n"
                      f"{Fore.YELLOW}Strength: {s.RESET_ALL}{args['strength']}\n"
                      f"{Fore.YELLOW}Control: {s.RESET_ALL}{args['control'].name}\n"
                      f"{Fore.YELLOW}Style: {s.RESET_ALL}{args['style'].name}")             
                file = File(fp=io.BytesIO(remixed_image), filename="remixed_image.png")
                embed = Embed()
                embed.set_footer(text=prompt)
                await ctx.send(content=f"{info}\n\n", file=file, embed=embed)
                success = True
                break
            except httpx.HTTPStatusError as e:
                print(f"{Fore.RED}{s.DIM}Client Response Error {e.response.status_code}: {e.response.text}. Retrying...{s.RESET_ALL}")
            except asyncio.TimeoutError:
                print(f"{Fore.RED}{s.DIM}Timeout Error: Retrying...{s.RESET_ALL}")
            except Exception as e:
                print(type(e), e)
                
            connection_retries += 1
            if connection_retries < MAX_CONNECTION_RETRIES:
                await asyncio.sleep(BACKOFF_FACTOR ** connection_retries)
        if success:
            break

        session_retries += 1
        if session_retries < MAX_SESSION_RETRIES:
            if imagine:
                await imagine.close()
                await asyncio.sleep(BACKOFF_FACTOR ** session_retries)
                imagine = AsyncImagine()

    if not success:
        await ctx.send("Please try again later.")
    if imagine:
        await imagine.close()

bot.run(os.getenv("DISCORD_TOKEN"))
