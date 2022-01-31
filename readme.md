# FAQ

## This bot is hosted on my personal laptop, so don't expect the bot to be available 24/7

You can expect this bot to be available from 3PM-12AM

1- Why would I need this? I can already get notifications from the moodle website.

You wouldn't believe how bloated the university website is. Through special means, I can cache the content gotten from the university website and send it to you ~ 10x faster even in the worst case. Also, this is more than just a fast way to get notifications because this bot automatically reminds you of exams and other notifications that are a week away from their deadlines. That alone is enough to justify using (or even making) this bot.

2 - How do I use this?

Here is every command I have implemented so far, aliases are another way to execute commands.

For example, sending h or help to the group chat will execute the help command.

Aliases : 'h'
help :
Displays relevant help text.

Aliases : 'notifications', 'i'
important_notifications :
Returns notifications representing exams, quizzes, exam deadlines, labs, etc.. in no particular order.
If you want to filter notifications by type, call the search function with an argument.

Aliases : 'links', 'l'
meeting_links :
A convenience function to send the zoom/teams meeting links of every subject in a text file.

Aliases : 'r'
remind :
Sends notifications that are at most 1 week away from their deadline.

Aliases : 'commands', 'c'
show_commands :
Displays every available command and its description.

Alternatively, type commands or c to show the list of available commands.

3 - This feature isn't working, when will you fix it?

I'll try my best to have my code working in the little amount of time that I have. However, you can expect me to be free in the weekends, so contact me at mys239@student.bau.edu.lb via outlook if it is urgent, but please post logs with your help request if possible.

4 - Do you accept feature requests?

Absolutely, the more challenging and fun the better. I don't know what more you could do with a bot like this, but if you have any ideas let me know.

5 - How can I contribute?

All of the code I use is freely available in this repository, make sure to send me a pull request if you feel the need to change anything, see the section below for building and setting up an instance of this bot.

## Contributing

### Legend

R : Required
RF : A file that will be required for the bot to continue working
O : Optional file

### List of Files

R - setup.md : How else would you read this?

R - *.py : This means that all files ending with .py are required (*except the idle.py file, see the comments below)

R - creds.txt : this file will be created automatically via a guided dialog upon execution of the setup script.

R - logs.log : you would think that this is just a log file, but it apparently automatically executes my code (?????). I don't know why either, just keep it.

RF - results\* : this means any file ending beginning with "results" will be required to keep this bot operational.

RF - mappings.json : this file is responsible for translating course codes into human readable subject names. You can ,however, update this in case you have different subjects or are reading this in your second year (this program absolutely doesn't care what year we're in, but it may need to be updated from time to time)

O - courses.json : this is just a temporary file to extract the info necessary to make the mappings.json file.

O - requirements.txt : this file is used for developing purposes and can be safely ignored, you may want to keep this file if you want to run this program as a python script.

O - \*test\* : All files beginning or ending with test are only required for development purposes.

O\* -idle.py : this file is technically not required, but if you want to use this as a telegram bot, you should probably not delete this.

o - LICENSE : Yeet this to the moon, go nuts.

### How To Host This Bot

If you ever want to host this bot for contribution (or independent development purposes), a guided init.py helper will display a dialogue to fill the required data for you.

NOTE: This is currently not possible at the moment, but it should be in the near future.
