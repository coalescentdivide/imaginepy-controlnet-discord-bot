
# imaginepy-controlnet-discord-bot

Rremix images as a discord bot. No hardware required. utilizes a slightly modified version of [Imaginepy](https://github.com/ItsCEED/Imaginepy)

### Prerequisites

Python (3.9 or 3.10 is recommended)

### Discord Bot setup

##### 1. Create your bot at https://discord.com/developers/applications
##### 2. Go to the Bot tab and click "Add Bot" and give it a name
##### 3. Click "Reset Token" to get your Discord Bot Token for the .env file.
##### 4. Disable "Public Bot".
##### 5. Enable "Message Content Intent" under "Privileged Gateway Intents".
##### 6. Go to the OAuth2 tab and select URL generator. Under Scopes check bot, then in the permissions check Send Messages and Embed Links. Use the generated URL to invite the bot to your server.

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ````

2. Create a virtual environment:
   ```
   python -m venv venv
   ````

3. Activate the environment:

   - On Windows:
     ```
     venv\Scripts\activate
     ```

   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ````

5. Copy and rename .env.example to .env and add your Discord bot token

6. Run the `main.py` script:
   ```
   python main.py
   ```
