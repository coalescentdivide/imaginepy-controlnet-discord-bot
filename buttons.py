import discord
from discord.ui import Button, Select, View

class RemixButton(Button):
    def __init__(self, ctx, command_args):
        emoji = "🌱"
        super().__init__(style=discord.ButtonStyle.secondary, label="ReMix", emoji=emoji, custom_id="remix_button")
        self.ctx = ctx
        self.command_args = command_args

class RandomStyleButton(Button):
    def __init__(self, ctx, command_args):
        emoji = "🎨"
        super().__init__(style=discord.ButtonStyle.secondary, label="ReStyle", emoji=emoji, custom_id="random_style_button")
        self.ctx = ctx
        self.command_args = command_args

class ControlModelSelect(Select):
    def __init__(self, ctx, command_args):
        options = [
            discord.SelectOption(label="Canny", value="CANNY", description="Uses canny edge detection for remix"),
            discord.SelectOption(label="Depth", value="DEPTH", description="Uses depth map for remix"),
            discord.SelectOption(label="Lineart", value="LINEART", description="Convert to lineart for remix"),
            discord.SelectOption(label="Scribble", value="SCRIBBLE", description="Remix scribble drawings to art"),
            discord.SelectOption(label="Pose", value="POSE", description="Uses human pose skeleton for remix")
        ]
        super().__init__(custom_id="control_model_select", options=options, placeholder="Choose how to remix (control model)")
        self.ctx = ctx
        self.command_args = command_args

class ModelSelect(Select):
    def __init__(self, ctx, command_args):
        options = [
            discord.SelectOption(label="v4_1", value="V4_1"),
            discord.SelectOption(label="v4_beta", value="V4_BETA"),
            discord.SelectOption(label="creative", value="CREATIVE"),
            discord.SelectOption(label="v3", value="V3"),
            discord.SelectOption(label="v1", value="V1"),
            discord.SelectOption(label="portrait", value="PORTRAIT"),
            discord.SelectOption(label="realistic", value="REALISTIC"),
            discord.SelectOption(label="anime", value="ANIME"),
            discord.SelectOption(label="deliberate", value="DELIBERATE"),
            discord.SelectOption(label="majic_mix", value="MAJIC_MIX"),
            discord.SelectOption(label="disney", value="DISNEY"),
            discord.SelectOption(label="orange_mix", value="ORANGE_MIX"),
            discord.SelectOption(label="lyriel", value="LYRIEL"),
            discord.SelectOption(label="rpg", value="RPG")
        ]
        super().__init__(custom_id="model_select", options=options, placeholder="Choose a model to use for the remix")
        self.ctx = ctx
        self.command_args = command_args

class StrengthSelect(Select):
    def __init__(self, ctx, command_args):
        options = [
            discord.SelectOption(
                label=str(i),
                value=str(i),
                description=f"Max change to original" if i == 0 else
                f"No change to original" if i == 100 else
                f""
            )
            for i in range(0, 101, 10)
        ]
        super().__init__(custom_id="strength_select", options=options, placeholder="Set original image strength (0-100)")
        self.ctx = ctx
        self.command_args = command_args


class RemixMenu(View):
    def __init__(self, ctx, command_args):
        super().__init__()
        self.add_item(ControlModelSelect(ctx, command_args))
        self.add_item(ModelSelect(ctx, command_args))
        self.add_item(StrengthSelect(ctx, command_args))
        self.add_item(RemixButton(ctx, command_args))
        self.add_item(RandomStyleButton(ctx, command_args))

