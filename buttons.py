import discord
from discord.ui import Button, Select, View

class RemixButton(Button):
    def __init__(self, ctx, command_args):
        emoji = "🌱"
        super().__init__(style=discord.ButtonStyle.secondary, label="Random Seed", emoji=emoji, custom_id="remix_button")
        self.ctx = ctx
        self.command_args = command_args

class RandomStyleButton(Button):
    def __init__(self, ctx, command_args):
        emoji = "🎨"
        super().__init__(style=discord.ButtonStyle.secondary, label="Random Style", emoji=emoji, custom_id="random_style_button")
        self.ctx = ctx
        self.command_args = command_args

class RandomModelButton(Button):
    def __init__(self, ctx, command_args):
        emoji = "💾"
        super().__init__(style=discord.ButtonStyle.secondary, label="Random Model", emoji=emoji, custom_id="random_model_button")
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


class RemixMenu(View):
    def __init__(self, ctx, command_args):
        super().__init__()
        self.add_item(RemixButton(ctx, command_args))
        self.add_item(RandomStyleButton(ctx, command_args))
        #self.add_item(RandomModelButton(ctx, command_args)) Uncomment to enable
        self.add_item(ControlModelSelect(ctx, command_args))
