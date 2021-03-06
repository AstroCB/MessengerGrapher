"""
This script parses the messages found in the exported data dump from Facebook
into a pickled format that is used by the graphing script.
"""

import pickle as pkl
from collections import namedtuple
from datetime import datetime
import json
from urllib.request import urlopen
import os
from bs4 import BeautifulSoup
from userinfo import ME, API_KEY

if os.path.isfile("name_to_sex.pkl"):
    # Cache this data to avoid making requests to the API if possible
    name_to_sex = pkl.load(open("name_to_sex.pkl", 'rb'))
else:
    name_to_sex = {}

def get_sex(name):
    """
    Guess the gender of the sender based on gender-api.
    """
    if len(name.split(" ")) != 1:
        name = name.split(" ")[0]

    url = "https://gender-api.com/get?key=" + API_KEY + "&name=" + name

    try:
        response = urlopen(url)
        decoded = response.read().decode('utf-8')
        data = json.loads(decoded)

        return data["gender"]
    except Exception:
        return "unknown"

Message = namedtuple("Message", ['person', 'sent_by_me', 'timestamp', 'sex'])
                            # types: str,      bool,         datetime,     str
messages = []

START = len("Participants: ") # Prefix to strip from beginning of header

for convo_file in os.listdir("messages"): # Iterate through each conversation file
    try:
        soup = BeautifulSoup(open("messages/{}".format(convo_file),
                                  encoding='utf8').read(), 'html.parser')
    except IsADirectoryError: # Messages folder contains multimedia subdirectories
        continue
    thread = soup.find('div', class_="thread")

    # Extract participants from header
    header = thread.contents[1]
    try:
        people = list(map(str.strip, header[START:].split(',')))
    except TypeError:
        # If TypeError occurs here, it's a message request – skip it
        continue

    if len(people) > 1: # Skip group chats
        continue

    person = people[0] # Other person in the convo

    # Iterate through each message in the conversation and append its info
    for item in thread.contents[2:]:
        if item.name == "div" and item["class"][0] == "message":
            datestring = item.contents[0].contents[1].contents[0]

            try:
                timestamp = datetime.strptime(datestring, '%A, %B %d, %Y at %I:%M%p')
            except ValueError:
                from dateutil.parser import parse
                timestamp = ' '.join(datestring.split()[-1]) # remove timezone
                timestamp = parse(datestring)

            person_sending = item.contents[0].contents[0].contents[0]
            sent_by_me = (person_sending == ME)

            sex = "unknown"
            if person in name_to_sex:
                sex = name_to_sex[person]
            else:
                sex = get_sex(person)
                name_to_sex[person] = sex

            messages.append(Message(person, sent_by_me, timestamp, sex))

pkl.dump(messages, open("messages.pkl", "wb"))
pkl.dump(name_to_sex, open("name_to_sex.pkl", 'wb'))
