import asyncio
import io
import os
import random
import httpx
from colorama import Fore, Back, Style as s
import discord
from discord import Embed, File
from discord.ext import commands
from dotenv import load_dotenv
from imaginepy import AsyncImagine, Mode, Style

load_dotenv()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.remove_command('help')
task_queue = asyncio.Queue()
queue_counter = 0

def parse_arguments(command_args: str):
    args = command_args.split()
    parsed_args = {
        'prompt': '',
        'negative': None,
        'scale': 7.5,
        'control': Mode.DEPTH,
        'style': Style.NO_STYLE,
        'seed': str(random.randint(1, 9999999999))
    }
    current_key = 'prompt'
    for arg in args:
        if arg.startswith('--'):
            current_key = arg[2:]
        else:
            if current_key == 'scale':
                parsed_args[current_key] = float(arg)
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


async def worker():
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
    bot.loop.create_task(worker())

@bot.command()
async def styles(ctx):
    styles = "\n".join(f"{style.name}" for style in Style)
    await ctx.send(f"Available styles:\n```\n{styles}\n```")

@bot.command()
async def remix(ctx, *, command_args: str = None):
    global queue_counter
    if command_args is None:
        example_control = random.choice(list(Mode)).name.lower()
        example_style = random.choice(list(Style)).name.lower()
        embed = Embed(title="Use with an image attachment or reply to an image", description="!remix [prompt] [optional arguments]")
        embed.add_field(name="🎨 See the full style list", value="`!styles`", inline=False)
        embed.add_field(name="⚙️ Choose the control model (depth, canny, scribble, pose, line_art)", value="`--control depth`", inline=False)
        embed.add_field(name="❌ Choose a negative prompt (optional)", value="--negative promptgoeshere", inline=False)
        embed.add_field(name="⚖️ Change the guidance scale (0-16)", value="--scale 8", inline=False)
        embed.add_field(name="🖌️ Use a style or choose random", value="`--style random`", inline=False)        
        embed.add_field(name="Example", value=f"`!remix cat --control {example_control} --negative dog --style {example_style} --scale 8 --seed 12345`", inline=False)
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
    if image:
        imagine = AsyncImagine()
    else:
        await ctx.send("Error: No image found in the message or the replied message. Please attach an image to your message or reply to a message with an image.")
        return

    MAX_CONNECTION_RETRIES = 3
    MAX_SESSION_RETRIES = 2
    BACKOFF_FACTOR = 2
    session_retries = 0

    while session_retries < MAX_SESSION_RETRIES:
        connection_retries = 0
        success = False
        while connection_retries < MAX_CONNECTION_RETRIES:
            try:
                args = parse_arguments(command_args)
                remixed_image = await asyncio.wait_for(imagine.controlnet(content=image, prompt=args['prompt'], mode=args['control'], negative=args['negative'], cfg=args['scale'], style=args['style'], seed=args['seed']), timeout=15)
                info = f"⚙️{args['control'].name} ⚖️{args['scale']} 🎨{args['style'].name} 🌱{args['seed']}"
                combined_prompt = f"{args['prompt']} {args['style'].value[3]}" if args['style'].value[3] is not None else args['prompt']
                prompt = f"Prompt:\n{combined_prompt}\n\nNegative Prompt:\n{args['negative'] or 'None'}"
                file = File(fp=io.BytesIO(remixed_image), filename="remixed_image.png")
                embed = Embed()
                embed.set_author(name=info)
                embed.set_image(url=f"attachment://{file.filename}")
                embed.set_footer(text=prompt)
                await ctx.send(embed=embed, file=file)
                print(f"{Fore.GREEN}Successfully processed image with the following settings:{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Prompt:{s.RESET_ALL} {Back.WHITE}{Fore.BLACK}{combined_prompt}{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Negative:{s.RESET_ALL} {Back.WHITE}{Fore.RED}{args['negative']}{s.RESET_ALL}\n"
                      f"{Fore.YELLOW}Seed:{s.RESET_ALL} {args['seed']}\n"
                      f"{Fore.YELLOW}Control:{s.RESET_ALL} {args['control'].name}\n"
                      f"{Fore.YELLOW}Style:{s.RESET_ALL} {args['style'].name}")
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
