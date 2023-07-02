
# imaginepy-controlnet-discord-bot

Rremix images as a discord bot. No hardware required. utilizes a slightly modified version of [Imaginepy](https://github.com/ItsCEED/Imaginepy)

## Prerequisites

Python (3.9 or 3.10 is recommended)

## Discord Bot setup

##### 1. Create your bot at https://discord.com/developers/applications
##### 2. Go to the Bot tab and click "Add Bot" and give it a name
##### 3. Click "Reset Token" to get your Discord Bot Token for the .env file.
##### 4. Disable "Public Bot".
##### 5. Under "Privileged Gateway Intents" enable "Presence Intent", "Server Member Intent" and "Message Content Intent".
##### 6. Go to the OAuth2 tab and select URL generator. Under Scopes check bot, then in the permissions check Send Messages, Embed Links and Read Message History. (You can also choose these permissions for specific channels only later.) Use the generated URL to invite the bot to your server.

### Installation

1. In a terminal window, clone the repository
   ```
   git clone https://github.com/coalescentdivide/imaginepy-controlnet-discord-bot.git
   ```
   and navigate to the directory:
   ```
   cd imaginepy-controlnet-discord-bot
   ````

3. Create a virtual environment:
   ```
   python -m venv venv
   ````

4. Activate the environment:

   - On Windows:
     ```
     venv\Scripts\activate
     ```

   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

5. Install the required packages:
   ```
   pip install -r requirements.txt
   ````

6. Copy and rename .env.example to .env and add your Discord bot token

7. Run the `main.py` script:
   ```
   python main.py
   ```


# Usage

To use the bot, you need an image to start with. You can either attach an image to a message or reply to a message containing an image. Then, type the `!remix` command followed by your prompt:

```
!remix your prompt
```

## Optional Parameters for the !remix command:

You can customize the output of the `!remix` command by adding optional parameters. Here's a list of available parameters and their usage:

### 1. Scale (range: 0.0-16.0)

Adjust the scale of the output by adding `--scale` followed by a number between 0.0 and 16.0.

Example:

```
!remix your prompt --scale 8
```

### 2. Negative prompt

You can choose a negative prompt, but it is optional. A default negative prompt is provided

### 3. Control Model

Choose a control model to influence the output. The available control models are `depth`, `scribble`, `pose`, and `canny`. Add `--control` followed by the desired control model.

### 4. Style

Apply a specific style to the output by using the `--style` parameter followed by a style name. To view the full list of available styles, type `!styles`.

### 5. Seed

The seed used for the generation.


Example:

![image](https://github.com/coalescentdivide/imaginepy-controlnet-discord-bot/assets/6615163/dfda2d0e-389b-469b-9216-4cf8785895cd)

