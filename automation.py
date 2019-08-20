import requests
import json
import csv
import getpass
import os
import sys
from datetime import date

from requests.auth import HTTPBasicAuth

# Retrieve account name from user
Account_Name = input("Account Name: ")

Speed_API = "https://{}.leankit.com/io/reporting/speed".format(Account_Name)

# Input from user for authentication
email = input("LeanKit Email: ")
try:
    password = getpass.getpass()
except Exception as error:
    print('ERROR', error)

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg1MzE5ODc3NCIsIm5hbWUiOiJBZGFtLlNhZGlxQHJicy5jb20iLCJlbWFpbCI6IkFkYW0uU2FkaXFAcmJzLmNvbSIsIm9yZ0lkIjoiNTMyOTE0NDgyIiwiY2FjaGVFeHBpcmF0aW9uIjoxNDQwLCJleHAiOjE1NjQ2NjAzNTksImlzcyI6ImxlYW5raXQtcmVwb3J0aW5nLWFwaSIsImF1ZCI6ImxlYW5raXQtcmVwb3J0aW5nLWFwaSIsImlhdCI6MTU2NDA1NTU1OX0.fBc-tboIMcAniXSS0nx7UHauQdhTGr9P9nUmW4oog60"

req = requests.sessions.session()

card_response = req.get("https://{}.leankit.com/io/reporting/export/cards?token={}".format(Account_Name,
        token), auth=HTTPBasicAuth(email, password), headers={'Cache-Control': 'no-cache'})

cardsInfo = card_response._content.decode('utf8')

# save cardsInfo as out.csv
with open('out.csv', 'w') as f:
    print(cardsInfo, file=f)

## remove empty lines from file
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

    total_years = 0
    total_months = 0
    total_days = 0

    total_time = 0
    lead_time = 0
    
    # # line[0] = CardID
    # # line[15] = Creation date
    # # line[19] = Finish date

    # #pragma ompd
    with open('out.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        for line in csv_reader:
            for card in newCards:
                if (line[0] == card['cardId']):
                    if (not((line[19][:4] == '') or line[15][:4] == '')):
                        cardsFound += 1
                        print(line)
                        print(line[19])
                        print(line[15])
                        years_diff = float(line[19][:4]) - float(line[15][:4])
                        months_diff = float(line[19][5:7]) - float(line[15][5:7])
                        days_diff = float(line[19][9:10]) - float(line[15][8:10])

                        start_year, start_month, start_day = (
                            float(line[15][:4]), float(line[15][5:7]), float(line[15][8:10]))
                        end_year, end_month, end_day = (
                            float(line[19][:4]), float(line[19][5:7]), float(line[19][8:10]))

                        total_years += years_diff
                        total_months += months_diff
                        total_days += days_diff

                        # Converting difference to days
                        f_date = date(int(start_year), int(start_month), int(start_day))
                        l_date = date(int(end_year), int(end_month), int(end_day))
                        delta = l_date - f_date
                        total_time += float(delta.days)

        if (not(cardsFound == 0)):
            lead_time = int(total_time)/int(cardsFound)
            print(total_time, cardsFound)
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
    Account_Name), auth=HTTPBasicAuth(email, password), headers={'Cache-Control': 'no-cache'})
feedback = response._content.decode('utf8')
replyData = json.loads(feedback)["ReplyData"][0]
boardIds = []

# Loop through all boards and retrieve Id
for board in replyData:
    boardIds.append(board["Id"])

start_lanes = []
end_lanes = []
lead_times = []

# Go through each boardId and find lead time
for i in boardIds:
    req.cookies.clear()
    # Retrieve board information
    response = req.get("https://{}.leankit.com/kanban/api/board/{}/GetBoardIdentifiers".format(Account_Name, i), auth=HTTPBasicAuth(email, password), headers={'Cache-Control': 'no-cache'})
    feedback = json.loads(response._content.decode('utf8'))
    replyData = feedback['ReplyData'][0]
    replyCode = feedback['ReplyCode']
    if (replyCode == 200): #check if we have access to the boards
        for lane in replyData["Lanes"]: #looping through all lanes
            if (lane["LaneClassType"] == 2): # Checking if it is a finish lane
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
        "timeOffset": 0
    }

    headers = {'content-type': 'application/json', 'Cache-Control': 'no-cache'}
    # Get speed data from LeanKit
    response = requests.post(Speed_API, data=json.dumps(
        speed_data), headers=headers, auth=HTTPBasicAuth(email, password))
    content = response._content
    
    # Decode UTF-8 bytes to Unicode
    content_json = content.decode('utf8')
    if (response.status_code == 200):
        # Find lead time and save results to array
        lead_times.append(
            {
                "boardId:": i,
                "leadTime": find_lead_time(content_json)
            }
        )
    else:
        print(response)

# save lead times array as json file
with open('lead_times.json', 'w') as f:
    print(lead_times, file=f)
print(lead_times)
