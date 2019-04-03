"""
Authors:
    Alex3142
    two other team members

Simple web crawler that collects web pages by following links between those web pages

Python version: 3.x
"""

import urllib.robotparser

from bs4 import BeautifulSoup
from urllib3 import PoolManager
import certifi 

import argparse
import csv
import time
import pandas as pd

"""
Queue code used from berkley pacman http://ai.berkeley.edu/project_overview.html
"""

class Queue:
    "A container with a first-in-first-out (FIFO) queuing policy."
    def __init__(self, fileName = None):
        
        self.list = []
        
        if fileName is not None:
            
            with open(fileName, 'r') as f:
                reader = csv.reader(f)
                your_list = list(reader)
             
            newList = []
            for item in your_list:
                newList.append(item[0])
                
            for item in reversed(newList):
                self.list.append(item)
            
        

    def push(self,item):
        "Enqueue the 'item' into the queue"
        self.list.insert(0,item)

    def pop(self):
        """
          Dequeue the earliest enqueued item still in the queue. This
          operation removes the item from the queue.
        """
        return self.list.pop()

    def isEmpty(self):
        "Returns true if the queue is empty"
        return len(self.list) == 0
    
    def printToFile(self, fileName):
        """
          This function prints the items of the queue to a csv file
        """
        
        if 'csv' not in fileName:
            fileName = fileName +'.csv'
            
        queueDF = pd.DataFrame(self.list)
        
        queueDF.to_csv(fileName, index = False, header = False)


def getHTML(url):
    """
    Input: url - URL (string) of the web site from which you want to get the HTML file

    Output: soup - HTML file of the web site specified in the URL input
    """
    
    # To make requests to multiple hosts taking care of maintaining the pools
    http = PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())

    # Get get the HTML page of the URL
    response = http.request("GET", url) 

    # Query the URL and pulling data out of HTML 
    soup = BeautifulSoup(response.data,"lxml")

    return soup


def FindLinks(thisSoup, pageName):
    """
    Input: thisSoup - HTML from which we want to extract the links
           pageName - Url associated with the HTML

    Output: List of the links contained in the HTML
    """
    linkListRaw= []
    linkListProcessed = []

    for link in thisSoup.findAll('a'):
        linkListRaw.append(link.get('href'))
    
    for item in linkListRaw:
        
        if item is not None:

            # For some reason occasionally we can get 'None' this seems odd behavior by beautiful soup...
            if len(item)> 1:
                # This stops something like / or # being presented as a link (which happened in testing)
                
                if item[0]  == '/':
                       # This ensures that relative references are encluded in their entireity 
                       linkListProcessed.append(pageName + item)
                elif not (item [0] == '#') :
                    # Otherwise if it is a complete link then return it uchanged 
                    # note, we ignore links that start with a hash
                    # these proved to be links to a specific section of the current page
                    # and thus are not of interest
                    linkListProcessed.append(item)
    
    return linkListProcessed
    


def main(websiteQueue, thisRobotParser, ITERATION_LIMIT = 10):
    """
    Input: websiteQueue - Queue (FIFO) which contains all the webpages to be analyzed
           thisRoboParser - Parser used to verify if we can crawler the URL

    Output (shell): URL crwaled and number of URL added to the queu to be anaylized
    """

    # Avoid crawler multiple times the same URL
    urlAlreadyVisited = {}

    # Set number of iterations (to avoid infinite loop)
    nIterations = 1

    
    while (not websiteQueue.isEmpty()) and nIterations <= ITERATION_LIMIT:

        # Obtain from the queue an URL to analyse
        thisWebsite = websiteQueue.pop()
        print("Analysing the web: ", thisWebsite )
    
        # Sets the URL referring to a robots.txt file
        thisRobotParser.set_url(thisWebsite)
        # Reads the robots.txt from URL and feeds it to the parser.
        thisRobotParser.read()
            
        
        """
        Maybe, this doesn't look very clean but we think this will be faster than 
        searchng a list of websites when the website list gets extremely long
        """
        #Check it is a no visited webpage
        try:
            urlAlreadyVisited[thisWebsite]

        except KeyError:
            # Returns True if the useragent is allowed to fetch the url according to robots.txt file
            
            try:
            
                if thisRobotParser.can_fetch("*", thisWebsite):
    
                    # Obtain the HTML
                    htmlSoup = getHTML(thisWebsite)
                   
                    # Obtain the URLs from the HTML
                    linkList = FindLinks(htmlSoup,thisWebsite)
                    print("Number of links added to be analyzed: " + str(len(linkList))+ "\n")
                    
                    # Add links to website queue
                    [websiteQueue.push(item) for item in linkList]
    
                    # Add the URL to the already visited list and add html as string as value
                    urlAlreadyVisited[thisWebsite] = str(htmlSoup)
                    
            except UnicodeDecodeError:
                # we had issues with decode errors (especially and stragely with robots.txt)
                # this prevents the tool falling over from these errors and informs the user of the issue
                print("decoding error with %s will not crawl this site." % thisWebsite)
            # Increase the counter
            nIterations += 1

    return urlAlreadyVisited, websiteQueue


if __name__ == "__main__":
    

    description = """Runs a web scraper """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-f','--file', nargs='*',
                        help='file to be processed')
    parser.add_argument('-l', '--link', nargs='?',
                        help='plain text input to be processed')
    parser.add_argument('-i', '--iters', nargs='?',
                        help='number of links to follow')
    
    args = parser.parse_args()

    #if the script has been run from cmd then
    # print output to files
    printToFile = False
    
    if args.iters:
        nLinks = int(args.iters)
    else:
        nLinks = 10
        
    
    if args.file:
        linkQueue = Queue(args.file[0])
        printToFile = True
    elif args.link:
         # Initialization of the queue 
        linkQueue = Queue()
        
        # Initial link to be crawled (different examples)
        linkQueue.push(args.link[0:])
        printToFile = True
    else:
        # Initialization of the queue 
        linkQueue = Queue()
        
        # Initial link to be crawled (different examples)
        linkQueue.push("https://www.telegraph.co.uk")
            
    # Initalization of the robots.txt parser
    rp = urllib.robotparser.RobotFileParser()
    
    #run the webscrawler
    
    urlAlreadyVisited, websiteQueue = main(linkQueue, rp, nLinks)
    
    
    # if the tool has been run from cmd save the output to a file
    if printToFile:
        
        # append date and time to the file names so they are easy to find
        # and do not overwite
        timestr = time.strftime("%Y_%m_%d-%H_%M_%S")
        
        crawlerFileName = 'crawler' + timestr + '.txt'
        
        queueFileName = 'queue'+ timestr
        
        # queue object has a printing method
        websiteQueue.printToFile(queueFileName)
        
        # dictionary required explicit code:
        # myabe not the best way of printing the 
        # dictionary, maybe could improve or picke object
        # if needed in future
        with open(crawlerFileName, 'w') as f:
            for key, value in urlAlreadyVisited.items():
                try:
                    f.write('%s:%s\n' % (key, value))
                except UnicodeEncodeError:
                    f.write('%s:%s\n' % (key, "UnicodeEncodeError"))
                    
                
                
                
                
                
                
                
                
