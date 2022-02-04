import json
from re import S
from urllib.request import urlopen
from collections import defaultdict
from pylatexenc.latex2text import LatexNodes2Text

class HepHelper:
    def __init__(self):
        self.CONST_QUERY_RESULTS = "100"

    def hepUrlEncode(self, string):
        encode_list = [(" ", "%20"), (":", "%3A"), ("/", "%2" + "F")]
        for el1, el2 in encode_list:
            string = string.replace(el1, el2)
        return string

    def hepUrlGenerator(self, command_string):
        
        url = "https://inspirehep.net/api/literature?sort=mostarticled&page=1&q=" + command_string + "&of=recjson" + \
            "&fields=titles,citation_count,first_author,dois,publication_info,collaborations,arxiv_eprints,number_of_pages,volume,author_count,abstracts&size=" + \
            self.CONST_QUERY_RESULTS
        return url

    def getSource(self, url):
        with urlopen(url) as resp:
            source = resp.read().decode('utf-8')

            self.writeToJson(source, "data/HEP_OUTPUT.json")

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

        self.data = json.loads(source)
        self.data = self.data["hits"]["hits"]

    def getAuthor(self,dic):
        if dic['metadata'].get('first_author') is not None:
            author = dic['metadata']['first_author'].get('full_name')
        else:
            author = None
        return author

    def getAuthorCount(self,dic):
        if dic['metadata'].get('author_count') is not None:
            authorCount = dic['metadata']['author_count']
        else:
            authorCount = None;
        return authorCount
    def getCitationCount(self,dic):
        if(dic['metadata'].get('citation_count') is None):
            citationCount = 0
        else:
            citationCount = dic['metadata']['citation_count']

    def getJournal(self,dic):
        if dic['metadata'].get('publication_info') is None:
            journal = None
        elif isinstance(dic['metadata']['publication_info'], list):
            if dic['metadata']['publication_info'][0].get("journal_title") is None:
                journal = None
            else:
                journal = dic['metadata']['publication_info'][0]["journal_title"]


        elif dic['metadata']['publication_info'].get("journal_title") is None:
                journal = None
        else:
                journal = dic['metadata']['publication_info']["journal_title"]

        return journal
    
    def getTitle(self,dic):
        if dic['metadata'].get('titles') is not None:
            title = dic['metadata']['titles'][0]['title']
        else:
            title = None
        return title
    
    def getAbstract(self,dic):
        if dic['metadata'].get('abstracts') is None:
            abstract = None
        elif isinstance(dic['metadata']['abstracts'], list):
            if dic['metadata']['abstracts'][0].get("value") is None:
                abstract = None
            else:
                abstract = dic['metadata']['abstracts'][0]['value']
        else:
            abstract = dic['metadata']['abstracts']['value']
        return abstract

    def getDoi(self,dic):
        if dic['metadata'].get('dois') is not None:
                Doi = dic['metadata']['dois'][0]['value']
        else:
            Doi = None
        return Doi
    def getYear(self,dic):
        if dic['metadata'].get('publication_info') is not None:
            if(type(dic["metadata"]['publication_info'])) == list:
                    year = dic["metadata"]['publication_info'][0].get("year")
            else:
                year = dic["metadata"]['publication_info'].get("year")
        else:
            year = 0
        return year
        
    
    def getCollaboration(self,dic):
        if dic['metadata'].get('collaborations') is None:
            collaboration = None
        elif isinstance(dic['metadata']['collaborations'], list):
            collaboration = ""
            for el in dic['metadata']['collaborations']:
                collaboration += el['value'] + " "
        else:
            collaboration = dic['metadata']['collaborations']['value']

        return collaboration


    def getPages(self,dic):
        if dic['metadata'].get('number_of_pages') is None:
            pages = None
        else:
            pages = dic['metadata']['number_of_pages']
        return pages

    def getVolume(self,dic):
        if dic['metadata'].get('publication_info') is None:
            volume = None
        else:
            volume = dic['metadata']['publication_info'][0].get("journal_volume")
        return volume

    def getEprint(self,dic):
        if dic['metadata'].get('arxiv_eprints') is None:
            eprint = None
        else:
            eprint = dic['metadata']['arxiv_eprints'][0].get("value")

        return eprint

    def getID(self,dic):
        if dic['metadata'].get('id') is None:
            id = None
        else:
            id = dic['metadata']['id']
        return id

    
    def parseJsonFile(self):
        singleArticle = dict()
         
        for dic in self.data:
        
            author = self.getAuthor(dic)
            authorCount = self.getAuthorCount(dic)
            journal = self.getJournal(dic)
            title = self.getTitle(dic)
            year = self.getYear(dic)
            doi = self.getDoi(dic)
            collaboration = self.getCollaboration(dic)
            pages = self.getPages(dic)
            volume = self.getVolume(dic)
            eprint = self.getEprint(dic)
            abstract = self.getAbstract(dic)       
            id = self.getID(dic)     
            citationCount=self.getCitationCount(dic)


            if author is not None:
                singleArticle['FirstAuthor'] = author
            else:
                singleArticle['FirstAuthor'] = None
            if authorCount is not None:
                singleArticle['AuthorCount'] = authorCount
            if journal is not None:
                singleArticle['Journal'] = journal
            if title is not None:
                singleArticle['Title'] = LatexNodes2Text().latex_to_text(title)
            if year is not None:
                singleArticle['Year'] = int(year)
            else:
                singleArticle['Year'] = 0
            if doi is not None:
                singleArticle['Doi'] = doi
            if collaboration is not None:
                singleArticle['Collaboration'] = collaboration
            if pages is not None:
                singleArticle['Pages'] = pages
            if volume is not None:
                singleArticle['Volume'] = volume
            if eprint is not None:
                singleArticle['Eprint'] = eprint
            if abstract is not None:
                singleArticle['Summary'] = LatexNodes2Text().latex_to_text(abstract)
            if id is not None:
                singleArticle['Source'] = f'https://inspirehep.net/literature/{id}'
            if citationCount is not None:
                singleArticle['CitationCount'] = citationCount

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
                
