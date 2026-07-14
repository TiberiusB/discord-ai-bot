

# Write to be deleted
ToDo: What to forget about a user? Can we just delete the data bu keep a trace of the user name, duration of activity?  

# members identity management
If member changes name on server, the bot monitors server changes of members and associates the new member identity on the server with the old. If Members have more than one identity, members or admins can ask the bot to associate the names. The name of members on the server can be a list with one or more than one names. This may require a function, a / call to the bot to perform this activity / change in the database.  

# Governance
ToDo: The bot can suggest to server admins by DM to ban or suspend a member, with resons related to social norms and based on guardrails.  


# Bot communicatin strategy
ToDo: Create a file in memory that explains how Discord works, functionality, and what the role of the Bot allows it to do. This file will be used by the Bot to decide how to act, ex. create a new thread, use @everyone, use emogi, ignor the slow mode, etc. This file wopuld be initialized when we launch the Bot, by cheching all affordances on Discord, listing them and associating communication strategy. 
Schedule scan of capabilities, in case the roles for the Bot are changed by admins, update this file and update communication strategy communication for the bot. 

ToDo: 
- Bot has the ability to create threads in allowawed channels.
- Bot has Ability to create surveys.
- Bot can use Discord's soundbord and send sounds.

# texty to speach in channels
ToDo: integrate ability to set tts: true in a message payload, so that a Discord client can listen to a synthesized voice. ex. 

POST /channels/{channel.id}/messages
{
  "content": "Bonjour, c'est Tramice721.",
  "tts": true
}

with With discord.py our project uses discord.py==2.7.1, the equivalent is: 

await channel.send("Bonjour, c'est Tramice721.", tts=True)

or for slash commands:
await interaction.followup.send("Bonjour...", tts=True)

Interaction responses also support a tts field in the callback payload.

# Coordination
Bot can create events on Discord, for example the weekly game. 