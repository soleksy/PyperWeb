import json
from urllib.request import urlopen
from pylatexenc.latex2text import LatexNodes2Text
from datetime import datetime
import orjson
import xmltodict
from bs4 import BeautifulSoup

class HepHelper:
    def __init__(self,numOfArticles):
        self.CONST_QUERY_RESULTS = str(numOfArticles)

    def hepUrlEncode(self, string):
        encode_list = [(" ", "%20"), (":", "%3A"), ("/", "%2" + "F")]
        for el1, el2 in encode_list:
            string = string.replace(el1, el2)
        return string

    def hepUrlGenerator(self, command_string):
        
        url = "https://inspirehep.net/api/literature?sort=mostarticled&page=1&q=" + command_string + "&of=recjson" + \
            "&fields=titles,citation_count,first_author,dois,publication_info,collaborations,arxiv_eprints,number_of_pages,volume,author_count,abstracts,recid,earliest_date&size=" + \
            self.CONST_QUERY_RESULTS + '&sort=mostrecent'
        return url

    def getSource(self, url):
        with urlopen(url) as resp:
            source = resp.read().decode('utf-8')
            return source

    def writeToJson(self, source, filename):

        data = json.loads(source)
        with open(filename, 'w') as f:
            string = json.dumps(data, indent=2)
            f.write(string)


class HepParser:

    def __init__(self, source):
        
        self.ListOfArticles = list()
        self.ListOfBibtex = list()

        json_data = orjson.loads(source)
        data = {'root': json_data}
        xmlSource = xmltodict.unparse(data)
        self.xmlSOURCE = xmlSource

        soup = BeautifulSoup(xmlSource, 'lxml')
        root = soup.find('hits')
        self.data = root


    def writeToXML(self, filename):
        with open(filename, 'w') as f:
            f.write(self.xmlSOURCE )

    def parseXml(self):
        singleArticle = dict()
        for i , article in enumerate(self.data.find_all('hits')):

            metadata = article.find('metadata')
            publication_info = metadata.find('publication_info')

            #getFistAuthor

            firstAuthor = metadata.find('first_author')
            if firstAuthor is not None:
                singleArticle['FirstAuthor'] = firstAuthor.find('full_name').text
            else:
                singleArticle['FirstAuthor'] = None

            #getAuthorCount

            authorCount = metadata.find('author_count')
            if authorCount is not None:
                singleArticle['AuthorCount'] = int(authorCount.text)
            else:
                singleArticle['AuthorCount'] = None


            #getTitle

            titles = metadata.find('titles')
            if titles is not None:
                singleArticle['Title'] = titles.find('title').text
            else:
                singleArticle['Title'] = None

            #getDoi
            dois = metadata.find('dois')
            if dois is not None:
                singleArticle['Doi'] = dois.find('value').text
            else:
                singleArticle['Doi'] = None
            
            #getCollaboration
            collaborations = metadata.find('collaborations')
            if collaborations is not None:
                if isinstance(collaborations, list):
                    collaborations = "".join([collaboration.find('value').text for collaboration in collaborations])
                    singleArticle['Collaboration'] = collaborations
                else:
                    singleArticle['Collaboration'] = collaborations.find('value').text
            else:
                singleArticle['Collaboration'] = None

            #getPages
            pages = metadata.find('number_of_pages')
            if pages is not None:
                singleArticle['Pages'] = pages.text
            else:
                singleArticle['Pages'] = None
            

            #get Journal and Year
            if publication_info is not None:
                if isinstance(publication_info, list):

                    journalTitle = publication_info[0].find('journal_title')
                    year = publication_info[0].find('year')
                    volume = publication_info[0].find('volume')

                    if journalTitle is not None:
                        singleArticle['Journal'] = journalTitle.text
                    else:
                        singleArticle['Journal'] = None

                    if year is not None:
                        singleArticle['Year'] = year.text
                    else:
                        singleArticle['Year'] = 0

                    if volume is not None:
                            singleArticle['Volume'] = volume.text
                    else:
                        singleArticle['Volume'] = None

                else:
                    journalTitle = publication_info.find('journal_title')
                    year = publication_info.find('year')
                    volume = publication_info.find('volume')

                    if journalTitle is not None:
                        singleArticle['Journal'] = journalTitle.text
                    else:
                        singleArticle['Journal'] = None
                        
                    if year is not None:
                        singleArticle['Year'] = year.text
                    else:
                        singleArticle['Year'] = 0

                    if volume is not None:
                            singleArticle['Volume'] = volume.text
                    else:
                        singleArticle['Volume'] = None
            else:
                journalTitle = None
                year = None
                volume = None



            #getEprint
            eprint = metadata.find('arxiv_eprints')
            if eprint is not None:
                singleArticle['Eprint'] = eprint.find('value').text
            else:
                singleArticle['Eprint'] = None
            
            #getAbstract
            abstracts = metadata.find('abstracts')
            if abstracts is not None:
                if isinstance(abstracts,list):
                    if abstracts[0].find('value') is not None:
                        singleArticle['Summary'] = abstracts[0].find('value').text
                    else:
                        singleArticle['Summary'] = None
                else:
                    singleArticle['Summary'] = abstracts.find('value').text
            else:
                singleArticle['Summary'] = None
            
            #getCitationCount
            citationCount = metadata.find('citation_count')
            if citationCount is not None:
                singleArticle['CitationCount'] = citationCount.text
            else:
                singleArticle['CitationCount'] = 0
            #getID & Source
            id = metadata.find('id')
            if id is not None:
                singleArticle['Source'] = f'https://inspirehep.net/literature/{id.text}'
            #getRecid & Link 
            recid = metadata.find('control_number')
            if recid is not None:
                singleArticle['Link'] = f'https://inspirehep.net/record/{str(recid.text)}'

            #fullDate
            earliestDate = metadata.find('earliest_date')
            if earliestDate is not None:
                date = earliestDate.text
                
                if len(date) == 4:
                     date += "-01-01"
                elif len(date) == 7:
                     date += "-01"

                date = datetime.strptime(date, "%Y-%m-%d")
                date = date.strftime("%Y-%m-%d")
                singleArticle['FullDate'] = date
            else:
                singleArticle['FullDate'] = None


            singleArticle['Bibtex'] = self.convertToBibtex(singleArticle)
            singleArticle['DB'] = "https://inspirehep.net/"
            self.ListOfArticles.append(singleArticle.copy())
            singleArticle.clear()
    def convertToBibtex(self,article):
        singleBibtex = dict()

        if article.get('FirstAuthor') is None:
            if article.get("AuthorCount") is not None:
                if article.get("Year") != 0:  
                    header =  "@article{ " + "Coauthored by " +  str(article.get("AuthorCount")) + " authors" + ":" + str(article['Year'])
                else:
                    header = "@article{ " + "Coauthored by " +  str(article.get("AuthorCount")) + " authors"
            else:
                    if article.get("Year") != 0:  
                        header = "@article{ "+ "Anonymous" + ":" + str(article['Year'])
                    else:
                        header = "@article{ "+ "Anonymous"
        else:
            if article.get("Year") != 0: 
                header = "@article{ "+ article.get("FirstAuthor") + ":" + str(article['Year'])
            else:
                header = "@article{ "+ article.get("FirstAuthor")

        singleBibtex['header'] = header

        if article.get('FirstAuthor') is not  None:
            if article.get("AuthorCount") is not None:
                if article.get("AuthorCount") == 1:
                    author = "author = { " + str(article['FirstAuthor'])
                else:
                    author = "author = { " + str(article['FirstAuthor']) + " and " +str(article['AuthorCount'] - 1) + " others"
            else:
                author = "author = { " + str(article['FirstAuthor'])
        else:
            if article.get("AuthorCount") is not None:
                author = "Coauthored by " +  str(article.get("AuthorCount")) + " authors"
            else:
                author = "Anonymous"

        singleBibtex['author'] = author

        if article.get('Title') is not None:
            title = "title = { " + LatexNodes2Text().latex_to_text(str(article['Title']))
            singleBibtex['title'] = title
        
        if article.get('Year') != 0:
            year = "year = { " + str(article['Year'])
            singleBibtex['year'] = year

        if article.get('Journal') is not None:
            journal = "journal = { " + str(article['Journal'])
            singleBibtex['journal'] = journal
    
        
        if article.get('Volume') is not None:
            volume = "volume = { " + str(article['Volume'])
            singleBibtex['volume'] = volume
        
        if article.get('Pages') is not None:
            pages = "pages = { " + str(article['Pages'])
            singleBibtex['pages'] = pages
        
        if article.get('Collaboration') is not None:
            collaboration = "collaboration = { " + str(article['Collaboration'])
            singleBibtex['collaboration'] = collaboration
        
        if article.get('Doi') is not None:
            doi = "doi = { " + str(article['Doi'])
            singleBibtex['doi'] = doi
        
        if article.get('Eprint') is not None:
            eprint = "eprint = { " + str(article['Eprint'])
            singleBibtex['eprint'] = eprint


        return singleBibtex



    

    def show(self):
        for dic in self.ListOfArticles:
            print("\n")
            for el in dic:
                print(el + ": " + str(dic[el]))

    def sortBy(self, value):
        if value == 'authors':
            self.ListOfArticles = sorted(
                self.ListOfArticles,
                key=lambda x: x['Num_Of_Authors'],
                reverse=True)
        elif value == 'date':
            self.ListOfArticles = sorted(
                self.ListOfArticles,
                key=lambda x: x['Creation_date'])
        elif value == 'citations':
            self.ListOfArticles = sorted(
                self.ListOfArticles,
                key=lambda x: x['Citations'],
                reverse=True)
                
    def writeBibtex(self, filename):
        bibtexList = []
        for article in self.ListOfArticles:
            bibtexList.append(self.convertToBibtex(article))
        

        with open(filename, 'w') as f:
            for article in bibtexList:
                for k,v in article.items():
                    f.write(v +" }" + "\n")
                f.write('\n')


    def writeData(self, filename):
        items = []
        with open(filename, 'w') as f:
            for dic in self.ListOfArticles:
                items = dic.items()
                for el in items:
                    if type(el[1]) == list:
                        f.write(str(el[0] + ":\n"))
                        for x in el[1]:
                            f.write(str(x)+" ,")
                        f.write('\n\n')
                    else:
                        f.write(str(el[0]) + ": \n" + str(el[1]))
                        f.write('\n\n')
                f.write('\n\n')
                
