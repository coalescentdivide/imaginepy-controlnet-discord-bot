import asyncio
import io
import os
import random
import re

import discord
import httpx
from colorama import Back, Fore
from colorama import Style as s
from discord import Activity, ActivityType, Embed, File
from discord.ext import commands

from dotenv import load_dotenv
from imaginepy import AsyncImagine, Mode, Model, Style, utils
from buttons import RemixMenu


load_dotenv()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.remove_command('help')
task_queue = asyncio.Queue()
queue_counter = 0
default_negative = os.environ.get("DEFAULT_NEGATIVE", "glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry")

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
        'seed': random_seed()
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
                model_str = arg.lower()
                if model_str == "random":
                    parsed_args[current_key] = random_model()
                else:
                    parsed_args[current_key] = Model[model_str.upper()]
            elif current_key == 'control':
                control_str = arg.lower()
                if control_str == "random":
                    parsed_args[current_key] = random_control()
                else:
                    parsed_args[current_key] = Mode[control_str.upper()]
            elif current_key == 'style':
                style_str = arg.lower()
                if style_str == "random":
                    parsed_args[current_key] = random_style()
                else:
                    parsed_args[current_key] = Style[style_str.upper()]
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
        parsed_args['negative'] = default_negative
    return parsed_args


def get_args(message_content: str, embed_field_values: dict, embed_footer_text: str) -> dict:
    args = {}
    mappings = {
        'control': r'⚙️`([a-zA-Z0-9_]+)`',
        'model': r'💾`([a-zA-Z0-9_]+)`',
        'scale': r'⚖️`([\d.]+)`',
        'strength': r'💪`([\d.]+)`',
        'style': r'🎨`([a-zA-Z0-9_]+)`',
        'seed': r'🌱`(\d+)`',
        'negative': r'Negative Prompt:\n([^\n]+)'
    }
    for key, regex in mappings.items():
        match = re.search(regex, message_content)
        if match:
            args[key] = match.group(1)
    for value in embed_field_values.values():
        match = re.search(r'\[Original\]\((.+)\)', value)
        if match:
            args['original_image'] = match.group(1)
            break
    args['prompt'] = embed_footer_text
    if 'style' in args and args['style'] != "NO_STYLE":
        style_object = Style[args['style'].upper()]
        style_value = style_object.value[3]
        if style_value is not None:
            args['prompt'] = args['prompt'].replace(style_value, '').strip()
    return args


def random_model():
    return random.choice(list(Model))
def random_control():
    return random.choice(list(Mode))
def random_style():
    return random.choice(list(Style))
def random_seed():
    return str(random.randint(1, 9999999999))

def get_style_name(style_str):
    try:
        style_name = style_str.upper()
        if style_name in Style.__members__:
            return style_name.lower()
        else:
            return 'no_style'
    except KeyError:
        return 'no_style'


async def queue():
    global queue_counter
    while True:
        task = await task_queue.get()
        func, ctx, args = task
        try:
            await func(ctx, *args)
        except Exception as e:
            print(f"{Fore.RED}{s.BRIGHT}Error processing task: {e}{s.RESET_ALL}")
        finally:
            task_queue.task_done()
            queue_counter -= 1


async def remix_from_interaction(interaction: discord.Interaction, command_args: str, interaction_user: discord.User, message_id):
    ctx = await bot.get_context(interaction.message)
    ctx.interaction_user = interaction_user
    global queue_counter
    await task_queue.put((queue_remix, ctx, (command_args, message_id)))
    queue_counter += 1
    print(f"{Fore.BLUE}{s.BRIGHT}Queue size: {queue_counter}{s.RESET_ALL}")



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


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        await interaction.response.defer(ephemeral=False)
        channel = interaction.channel
        bot_message = await channel.fetch_message(interaction.message.id)            
        message_content = bot_message.content
        embed_field_values = None
        image = None
        
        if bot_message.embeds:
            embed_footer_text = bot_message.embeds[0].footer.text
            embed_fields = bot_message.embeds[0].fields
            embed_field_values = {field.name: field.value for field in embed_fields}
        else:
            print("Error: Embed not found in the message.")
            return
        args = get_args(message_content, embed_field_values, embed_footer_text)

        if 'original_image' in args:
            message_id = int(args['original_image'].split('/')[-1])
            message = await channel.fetch_message(message_id)
            if message.attachments:
                image = message.attachments[0]

        if interaction.data["custom_id"] == "remix_button":
            await interaction.followup.send(content="Remixing", ephemeral=True)  
            args['seed'] = random_seed()
            command_args = f"{args['prompt']} --model {args.get('model', 'V3')} --control {args.get('control', 'canny')} --negative {args.get('negative', default_negative)} --scale {args.get('scale', '7.5')} --style {args.get('style', 'no_style')} --strength {args.get('strength', '0')} --seed {args.get('seed', '42')}"
            await remix_from_interaction(interaction, command_args, interaction.user, message_id)

        elif interaction.data["custom_id"] == "random_style_button":
            await interaction.followup.send(content="Remixing with random style", ephemeral=True)     
            args['style'] = random_style().name
            command_args = f"{args['prompt']} --model {args.get('model', 'V3')} --control {args.get('control', 'canny')} --negative {args.get('negative', 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry')} --scale {args.get('scale', '7.5')} --style {args.get('style', 'no_style')} --strength {args.get('strength', '0')} --seed {args.get('seed', '42')}"
            await remix_from_interaction(interaction, command_args, interaction.user, message_id)

        elif interaction.data["custom_id"] == "random_model_button":
            await interaction.followup.send(content="Remixing with random model", ephemeral=True)      
            args['model'] = random_model().name
            command_args = f"{args['prompt']} --model {args.get('model', 'V3')} --control {args.get('control', 'canny')} --negative {args.get('negative', 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry')} --scale {args.get('scale', '7.5')} --style {args.get('style', 'no_style')} --strength {args.get('strength', '0')} --seed {args.get('seed', '42')}"
            await remix_from_interaction(interaction, command_args, interaction.user, message_id)

        elif interaction.data["custom_id"] == "control_model_select":
            control_model = interaction.data["values"][0]
            await interaction.followup.send(content=f"Remixing with {control_model} control model", ephemeral=True)
            args['control'] = Mode[control_model].name
            command_args = f"{args['prompt']} --model {args.get('model', 'V3')} --control {args.get('control', 'canny')} --negative {args.get('negative', 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry')} --scale {args.get('scale', '7.5')} --style {args.get('style', 'no_style')} --strength {args.get('strength', '0')} --seed {args.get('seed', '42')}"
            await remix_from_interaction(interaction, command_args, interaction.user, message_id)

        elif interaction.data["custom_id"] == "model_select":
            model = interaction.data["values"][0]
            await interaction.followup.send(content=f"Remixing with {model}", ephemeral=True)
            args['model'] = Model[model].name
            command_args = f"{args['prompt']} --model {args.get('model', 'V3')} --control {args.get('control', 'canny')} --negative {args.get('negative', 'glitch,deformed,lowres,bad anatomy,bad hands,text,error,missing fingers,cropped,jpeg artifacts,signature,watermark,username,blurry')} --scale {args.get('scale', '7.5')} --style {args.get('style', 'no_style')} --strength {args.get('strength', '0')} --seed {args.get('seed', '42')}"
            await remix_from_interaction(interaction, command_args, interaction.user, message_id)


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
        if ctx.message.reference:
            message_id = ctx.message.reference.message_id
        else:
            message_id = ctx.message.id
        await task_queue.put((queue_remix, ctx, (command_args, message_id)))
        queue_counter += 1
        print(f"{Fore.BLUE}{s.BRIGHT}Queue size: {queue_counter}{s.RESET_ALL}")


async def queue_remix(ctx, command_args: str, message_id: int):
    author = ctx.interaction_user if hasattr(ctx, 'interaction_user') else ctx.author
    print(f"{Fore.RED}{s.BRIGHT}{author.name}{s.RESET_ALL} is remixing an image")
    image = None
    message = await ctx.channel.fetch_message(message_id)
    if len(message.attachments) > 0:
        image = await message.attachments[0].read()
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
                        concise_prompt = generated_prompt.split(',', 1)[0]
                        args['prompt'] = concise_prompt
                    except asyncio.TimeoutError:
                        args['prompt'] = "amazing"
                remixed_image = await asyncio.wait_for(imagine.controlnet(content=image, prompt=args['prompt'], model=args['model'], mode=args['control'], negative=args['negative'], cfg=args['scale'], style=args['style'], strength=args['strength'], seed=args['seed']), timeout=15)
                info = f"🧠{author.mention}⚙️`{args['control'].name.lower()}`💾`{args['model'].name.lower()}`⚖️`{args['scale']}`💪`{args['strength']}`🎨`{args['style'].name.lower()}`🌱`{args['seed']}`"
                combined_prompt = f"{args['prompt']} {args['style'].value[3]}" if args['style'].value[3] is not None else args['prompt']
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
                original_image = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{message_id}"
                embed = Embed()
                embed.add_field(name="", value=f"[Original]({original_image})", inline=False)
                embed.set_footer(text=prompt)
                await ctx.send(content=f"{info}\n\n", file=file, embed=embed, view=RemixMenu(ctx, args))
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
