from urllib.request import urlopen
import requests
import os
from xml.etree.ElementTree import fromstring, ElementTree



class ArxivHelper:
    data = ""
    def __init__(self):
        self.CONST_QUERY_RESULTS = "100"

    def url_encode(self, string):
        encode_list = [(" ", "%20"), (":", "%3A"), ("/", "%2" + "F")]
        for el1, el2 in encode_list:
            string = string.replace(el1, el2)
        return string

    def paramsToUrl(self, params):
        base_url = "http://export.arxiv.org/api/query?search_query="

        for i, (el1, el2) in enumerate(params):
            base_url += el1 + "%3A" + el2
            if i != len(params) - 1:
                base_url += "%20AND%20"

        base_url += "&max_results=" + self.CONST_QUERY_RESULTS
        base_url += "&sortBy=relevance&sortOrder=ascending"
        return base_url

    def allParamSearch(self, query):
        query = self.url_encode(query)
        return "http://export.arxiv.org/api/query?search_query=all:" + query + "&max_results=" + self.CONST_QUERY_RESULTS + "&sortBy=relevance"

    def apiToFile(self, url, file_name):
        r = requests.get(url)
        with open(file_name, 'w') as f_in:
            f_in.write(r.content.decode('utf-8'))
    def apiToString(self,url):
        r = requests.get(url)
        return r.content.decode('utf-8')

class ArxivParser:

    def __init__(self, contents):
        self.ListOfArticles = list()
        self.contents = contents

    def getComment(self,entry):
        if entry.find('comment') is not None:
            comment = entry.find('comment').text
        else:
            comment = None
        return comment

    def getJournal(self, entry):
        if entry.find('journal_ref') is not None:
            journal = entry.find('journal_ref').text
        else:
            journal = None
        return journal

    def getDoi(self, entry):
        if entry.find('doi') is not None:
            doi = entry.find('doi').text
        else:
            doi = None
        return doi
    
    def getAuthors(self, entry):
        authorList = entry.findall('author')
        firstAuthor= authorList[0].find('name').text
        return firstAuthor

    def getEprint(self, entry):
        if entry.find('id').text is not None:
            ID = entry.find('id').text
            ID = ID[:-2]  
        else:
            ID= None

        return ID

    def getTitle(self, entry):
        if entry.find('title').text is not None:
            title = entry.find('title').text     
        else:
            title= None
        return title

    def getDatePublished(self, entry):
        if entry.find('published').text is not None:
            published = int(entry.find('published').text.split("-", 1)[0])    
        else:
            published=0
        return published 

    def getLastUpdate(self, entry):
        if entry.find('updated').text is not None:
            updated = entry.find('updated').text
        else:
            updated = None
        
        return updated

    def getSummary(self,entry):
        if entry.find('summary').text is not None:
            summary = entry.find('summary').text
        else:
            summary = None
        return summary

    def getID(self,entry):
        if entry.find('id').text is not None:
            id = entry.find('id').text
        else:
            id = None
        return id

    def parseXML(self):
        singleArticle = dict()
        tree = ElementTree(fromstring(self.contents))
        root = tree.getroot()
        entries = root.findall('entry')

        for entry in entries:
            singleArticle['Journal'] = self.getJournal(entry)
            singleArticle['Doi'] = self.getDoi(entry)
            singleArticle['FirstAuthor'] = self.getAuthors(entry)
            singleArticle['Eprint'] = self.getEprint(entry)
            singleArticle['AuthorCount'] = len(self.getAuthors(entry))
            singleArticle['Title'] = self.getTitle(entry)
            singleArticle['Year'] = self.getDatePublished(entry)
            singleArticle['LastUpdate']= self.getLastUpdate(entry)


            comment = self.getComment(entry)
            if comment is None:
                numberOfPages = None
            else:
                pagesOccurence = comment.find('pages')
                if pagesOccurence-3 == -1:
                    numberOfPages = comment[pagesOccurence-2:pagesOccurence]
                else:
                    numberOfPages = comment[pagesOccurence-3:pagesOccurence]

            singleArticle['Comment'] = self.getComment(entry)
            singleArticle['Pages'] = numberOfPages


            singleArticle['Summary'] = self.getSummary(entry)
            singleArticle['Source'] = self.getID(entry) 
            singleArticle['Bibtex'] = self.convertToBibtex(singleArticle)
            singleArticle['DB'] = "https://arxiv.org/"

            self.ListOfArticles.append(singleArticle.copy())
            singleArticle.clear()


    def convertToBibtex(self,article):  
        singleBibtex = dict()

        header = "@article{ " + str(article['FirstAuthor']) + ":" + str(article['Year']).split("-", 1)[0]
        author = str("author = { " + article['FirstAuthor'])
        singleBibtex['header'] = header
        singleBibtex['author'] = author

        if article.get("Title") is not None:
            title = article["Title"]
            singleBibtex['title'] = "title = { " + title
        if article.get("Journal") is not None:
            journal = article["Journal"]
            singleBibtex['journal'] = "journal = { " + journal
        if article.get("Year") is not 0:
            year = str(article['Year']).split("-", 1)[0]
            singleBibtex['year'] = "year = { " + year 
        if article.get("Eprint") is not None:
            eprint = article["Eprint"]
            if 'http://arxiv.org/abs/physics/' in eprint:
                singleBibtex['eprint'] = "eprint = { " + eprint.strip('http://arxiv.org/abs/physics/')
            else:
                singleBibtex['eprint'] = "eprint = { " + eprint.strip('http://arxiv.org/abs/')

        if article.get("Comment") is not None:
            comment = article["Comment"]
            pagesOccurence = comment.find('pages')
            if pagesOccurence-3 == -1:
                numberOfPages = comment[pagesOccurence-2:pagesOccurence]
            else:
                numberOfPages = comment[pagesOccurence-3:pagesOccurence]
            singleBibtex['pages'] = "pages = { " + numberOfPages

        return singleBibtex


    def writeData(self, filename):
        with open(filename, 'w') as f:
            for article in self.ListOfArticles:
                f.write(str(article['FirstAuthor']) + ": \n " )
                f.write(str(article['Year']) + ": \n ")
                f.write(str(article['LastUpdate']) + ": \n ")
                f.write(str(article['Title']) + ": \n ")
                f.write(str(article['Eprint']) + ": \n ")
                f.write(str(article['Doi']) + ": \n ")
                f.write(str(article['Journal']) + ": \n ")
                f.write(str(article['AuthorCount']) + ": \n ")
                f.write(str(article['Summary']) + ": \n ")
                f.write(str(article['Source']) + ": \n ")
                f.write("\n")
            f.write('\n')

    def writeBibtex(self, filename):
        bibtexList = []
        for article in self.ListOfArticles:
            bibtexList.append(self.convertToBibtex(article))
        
        with open(filename, 'w') as f:
            for article in bibtexList:
                for k,v in article.items():
                    f.write( v + " } " + "\n")
                f.write("\n")

    def show(self):
        for dic in self.ListOfArticles:
            print("\n")
            for el in dic:
                print(el + ": " + str(dic[el]))

    def standardizeXml(self):
        if type(self.contents) is not str:
            self.contents = self.contents.decode("utf-8")
        self.contents = self.contents.replace(' xmlns="http://www.w3.org/2005/Atom"', '')
        self.contents = self.contents.replace(
            ' xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"', '')
        self.contents = self.contents.replace('opensearch:', '')
        self.contents = self.contents.replace('arxiv:', '')
        self.contents = self.contents.replace(
            ' xmlns:arxiv="http://arxiv.org/schemas/atom"', '')

    def filterRange(self, range):
        temp_list = list()
        year = 0
        status = ''
        try:
            if range[0] == '-':
                status = 'till'
                year = int(range[1:])
            elif range[0] == '+':
                status = 'after'
                year = int(range[1:])
            else:
                status = 'between'
                year1 = int(range[0:4])
                year2 = int(range[5:9])

            for dic in self.ListOfArticles:
                full_date = dic['Date_Published']
                date = int(full_date[:4])
                if status == 'till':
                    if date <= year:
                        temp_list.append(dic)
                elif status == 'after':
                    if date >= year:
                        temp_list.append(dic)
                else:
                    if date >= year1 and date <= year2:
                        temp_list.append(dic)
            self.ListOfArticles = temp_list
        except BaseException:
            print("Error while parsing range expression try ./pyper.py ARXIV -h for more information on available range formats")
            return -1

    def sortBy(self, value):
        if value == 'authors':
            self.ListOfArticles = sorted(
                self.ListOfArticles,
                key=lambda x: x['Num_Of_Authors'],
                reverse=True)
        elif value == 'published':
            self.ListOfArticles = sorted(
                self.ListOfArticles,
                key=lambda x: x['Date_Published'])
        elif value == 'updated':
            self.ListOfArticles = sorted(
                self.ListOfArticles,
                key=lambda x: x['Last_Update'],
                reverse=True)

