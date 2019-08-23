import requests
import json
import csv
import getpass
import os
import sys
from datetime import date

from requests.auth import HTTPBasicAuth


# Admin account should be used to be able to access all boards
# Main problem to tackle is to figure out why this program returns more cards than leankit, changing the results
# The cards all end before the end date, so there may be a bug from LeanKit, or in the API.

# Retrieve account name from user
Account_Name = input("Account Name: ")

# API to call Cycle Time/Lead Time
Speed_API = "https://{}.leankit.com/io/reporting/speed".format(Account_Name)

# Input from user for authentication
email = input("LeanKit Email: ")
try:
    password = getpass.getpass()
except Exception as error:
    print('ERROR', error)

req = requests.sessions.session()

# token for access to leankit
body = {
	"email": email,
	"accountName": Account_Name,
	"password": password
}
headers = {'content-type': 'application/json', 'Cache-Control': 'no-cache', "Pragma": "no-cache"}
reply = req.post("https://{}.leankit.com/io/reporting/auth".format(Account_Name), data=json.dumps(
            body), headers=headers)
content = reply._content
content_json = json.loads(content.decode('utf8'))
token = content_json["token"]

# Decode UTF-8 bytes to Unicode
content_json = content.decode('utf8')

# Get all cards from LeanKit to compare
card_response = req.get("https://{}.leankit.com/io/reporting/export/cards?token={}".format(Account_Name,
        token), auth=HTTPBasicAuth(email, password), headers={'Cache-Control': 'no-cache', "Pragma": "no-cache"})
cardsInfo = card_response._content.decode('utf8')

# save cardsInfo as out.csv
with open('out.csv', 'w') as f:
    print(cardsInfo, file=f)

# remove empty lines from file
readFile = open("out.csv")
lines = readFile.readlines()
readFile.close()
w = open("out.csv", 'w')
w.writelines([item for item in lines[:-2]])
w.close()

# function to find the start lanes, returning them as a list
def find_lead_time(cards):

    cardsFound = 0
    newCards = json.loads(cards)

    total_time = 0
    lead_time = 0
     
    # # line[0] = CardID
    # # line[15] = Creation date
    # # line[19] = Finish date

    with open('out.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        # Go through the saved cards
        for line in csv_reader:
        	# Go through the cards returned from Speed API
            for card in newCards:
            	# If the card has been found
                if (line[0] == card['cardId']):
                	# Some cards don't have a finish date or start date for no apparent reason
                    if (not((line[19][:4] == '') or line[15][:4] == '')):
                        cardsFound += 1

                        # Finding start and end dates from string
                        start_year, start_month, start_day = (
                            float(line[15][:4]), float(line[15][5:7]), float(line[15][8:10]))
                        end_year, end_month, end_day = (
                            float(line[19][:4]), float(line[19][5:7]), float(line[19][8:10]))

                        # Converting difference to days
                        f_date = date(int(start_year), int(start_month), int(start_day))
                        l_date = date(int(end_year), int(end_month), int(end_day))
                        delta = l_date - f_date
                        total_time += float(delta.days)

        # If cards have been found
        if (not(cardsFound == 0)):
        	# calculate lead time
            lead_time = int(total_time)/int(cardsFound)
            print("Leadtime in days:", lead_time)
            print("")
            return lead_time
        else:
            return 0
    

# Input from user to specify duration
startDate = input("Please enter the start date, e.g: 2019-07-01:\n")
endDate = input("Please enter the end date, e.g: 2019-08-01:\n")

# Retrieve all boards from LeanKit
response = req.get("https://{}.leankit.com/kanban/api/boards".format(
    Account_Name), auth=HTTPBasicAuth(email, password), headers={'Cache-Control': 'no-cache', "Pragma": "no-cache"})
feedback = response._content.decode('utf8')
replyData = json.loads(feedback)["ReplyData"][0]

# Loop through all boards and retrieve Id
boardIds = []
for board in replyData:
    boardIds.append(board["Id"])

start_lanes = []
end_lanes = []
lead_times = []

# Go through each boardId and find lead time
for i in boardIds:
    req.cookies.clear()
    # Retrieve board information per boardID
    response = req.get("https://{}.leankit.com/kanban/api/board/{}/GetBoardIdentifiers".format(Account_Name, i), auth=HTTPBasicAuth(email, password), headers={'Cache-Control': 'no-cache', "Pragma": "no-cache"})
    feedback = json.loads(response._content.decode('utf8'))
    replyData = feedback['ReplyData'][0]
    replyCode = feedback['ReplyCode']
    print("Boardid: " , i , "ReplyCode: " , replyCode)
    if (replyCode == 200): #check if we have access to the boards
        for lane in replyData["Lanes"]: #looping through all lanes
            if (lane["LaneType"] == 3): # Checking if it is a finish lane
                end_lanes.append(lane["Id"]) # Add to finish lanes
            else:
                start_lanes.append(lane["Id"]) # Add to state lanes

        # Speed data to be sent
        speed_data = {
            "boardId": i,
            "startLanes": start_lanes,
            "finishLanes": end_lanes,
            "startDate": startDate,
            "endDate": endDate,
            "timeOffset": -60 # Always used in LeanKit Speed API call
        }

        headers = {'content-type': 'application/json', 'Cache-Control': 'no-cache', "Pragma": "no-cache"}
        # Get speed data from LeanKit
        response = requests.post(Speed_API, data=json.dumps(
            speed_data), headers=headers, auth=HTTPBasicAuth(email, password))
        content = response._content
    
        # Decode UTF-8 bytes to Unicode
        content_json = content.decode('utf8')
        if (response.status_code == 200): #If the Speed API call was successful
            # Find lead time and save results to array
            lead_times.append(
                {
                    "boardId": i,
                    "leadTime": find_lead_time(content_json)
                }
            )

# save lead times array as json file
with open('lead_times.json', 'w') as f:
    print(json.dumps(lead_times), file=f)
print(json.dumps(lead_times))