import requests
import json
from bs4 import BeautifulSoup
from pylatexenc.latex2text import LatexNodes2Text
from datetime import datetime

class PubmedHelper:
    def __init__(self , numOfArticles):
        self.CONST_QUERY_RESULTS=numOfArticles
        self.CONST_FETCH_URL='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        self.CONST_SEARCH_URL='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'

    def search_pubmed(self, params):
        base_url = self.CONST_SEARCH_URL
        full_url = base_url + '?' + '&'.join([f'{key}={value}' for key, value in params.items()])
        response = requests.get(full_url)
        try:
            return response.json()
        except json.JSONDecodeError:
            print("Failed to decode JSON from response")
            print("Response content:", response.text)
            return None

    def get_article_ids(self,json_response):
        return json_response['esearchresult']['idlist']

    
    def pubmedURLGenerator(self,query):
        params = {'db': 'pubmed', 'term': query, 'retmax': self.CONST_QUERY_RESULTS, 'sort': 'relevance', 'retmode': 'json'}
        json_response = self.search_pubmed(params)
        article_ids = self.get_article_ids(json_response)
        fetch_params = {'db': 'pubmed', 'id': ','.join(article_ids), 'rettype': 'abstract', 'retmode': 'xml' }
        base_url = self.CONST_FETCH_URL
        full_url = base_url + '?' + '&'.join([f'{key}={value}' for key, value in fetch_params.items()])

        return full_url

    def fetch_articles_info(self, article_ids, rettype , retmode) :
        base_url = self.CONST_FETCH_URL
        params = {'db': 'pubmed', 'id': ','.join(article_ids), 'rettype': rettype, 'retmode': retmode}
        full_url = base_url + '?' + '&'.join([f'{key}={value}' for key, value in params.items()])
        response = requests.get(full_url)
        
        return response.text

    def apiToFile(self,response , filename , retmode):
        with open(filename, 'w') as outfile:
            if retmode == 'json':
                json.dump(response, outfile)
            elif retmode == 'xml':
                outfile.write(response)

class PubmedParser:
    '''Load and parse the xml data from the API'''
    def __init__(self , source):
        self.ListOfArticles = list()
        self.ListOfBibtex = list()

        self.xml_data = source
    def parseDate(self,article):
        '''
        Parse the date and return a list of dates
        '''
        Month_Map = {
        'Jan': '01',
        'Feb': '02',
        'Mar': '03',
        'Apr': '04',
        'May': '05',
        'Jun': '06',
        'Jul': '07',
        'Aug': '08',
        'Sep': '09',
        'Oct': '10',
        'Nov': '11',
        'Dec': '12'
    }
        if article.find('PubDate').find('Year') is None:
            if article.find('DateCompleted').find('Year') is None:
                return None
            else:
                year = article.find('DateCompleted').find('Year').text
                month = article.find('DateCompleted').find('Month').text
                day = article.find('DateCompleted').find('Day').text
                fullDate = year + '-' + month + '-' + day
        
        else:
            year = article.find('PubDate').find('Year')
            if year is not None:
                year = year.text

            month = article.find('PubDate').find('Month')
            if month is not None:
                month = month.text

            day = article.find('PubDate').find('Day')
            if day is not None:
                day = day.text

            fullDate = ''
            if year == None:
                year = None
            else:
                fullDate += year

                if month == None:
                    fullDate += '-01-01'
                else:
                    fullDate += '-' + Month_Map[month]
                    if day == None:
                        fullDate += '-01'
                    else:
                        fullDate += '-' + day
        
        if fullDate == '':
            return None
        elif fullDate == None:
            return None

        else:
            date = datetime.strptime(fullDate, '%Y-%m-%d')
            dateStr = date.strftime('%Y-%m-%d')
            return dateStr

    def parseArticleInfo(self):
        '''
        author, list of authors, journal, article title, abstract, doi,year, volume
        '''
        soup = BeautifulSoup(self.xml_data ,features="xml")
        for i , article in enumerate(soup.find_all('PubmedArticle')):
            article_info = {}

            articleTitle = article.find('ArticleTitle')
            if articleTitle is not None:
                article_info['Title'] = articleTitle.text
            
            abstract = article.find('Abstract')
            if abstract is not None:
                article_info['Summary'] = abstract.text
            else:
                article_info['Summary'] = ''

            doi = article.find('ELocationID' , {'EIdType': 'doi'})
            if doi is not None:
                article_info['Doi'] = doi.text


            link = article.find('ArticleId' ,{'IdType': "pubmed"})
            if link is not None:
                ArticleID = link.text
                article_info['Link'] = "https://www.ncbi.nlm.nih.gov/pubmed/" + ArticleID

            authorList = article.find('AuthorList')
            
            if authorList is None:
                article_info['FirstAuthor'] = ''
            else:
                foreName = authorList.find('ForeName')

                if foreName is not None:
                    foreName = foreName.text
                else:
                    foreName = ''
                lastName = authorList.find('LastName')

                if lastName is not None:
                    lastName = lastName.text
                else:
                    lastName = ''

                article_info['FirstAuthor'] = foreName + ' ' + lastName
            


            if authorList is not None:
                Authors = [author for author in article.find('AuthorList').find_all('Author')]
                author_list = []
                for author in Authors:
                    authorForeName = author.find('ForeName')
                    if authorForeName is not None:
                        foreName = authorForeName.text
                    else:
                        foreName = ''
                    authorLastName = author.find('LastName')
                    if authorLastName is not None:
                        lastName = authorLastName.text
                    else:
                        lastName = ''
                    author = foreName + ' ' + lastName
                    author_list.append(author)
                article_info['authors'] = author_list
                article_info['author_count'] = len(author_list)
               
            journal = article.find('Title')
            if journal is not None:
                article_info['Journal'] = journal.text

            volume=article.find('Volume')
            if volume is not None:
                article_info['Volume'] = volume.text
            
            year = article.find('Year')
            if year is not None:
                article_info['Year'] = int(year.text)

            fullDate = self.parseDate(article)
            article_info['FullDate'] = fullDate
            
            article_info['Bibtex'] = self.convertToBibtex(article_info)
            article_info['DB'] = "https://www.ncbi.nlm.nih.gov/"
            self.ListOfArticles.append(article_info)


        '''return a list of dictionaries containing the bibtex for each article'''
    def convertToBibtex(self,article):
        singleBibtex = dict()
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
        
        if article.get('Doi') is not None:
            doi = "doi = { " + str(article['Doi'])
            singleBibtex['doi'] = doi
        
        if article.get('Eprint') is not None:
            eprint = "eprint = { " + str(article['Eprint'])
            singleBibtex['eprint'] = eprint

        return singleBibtex

    def writeBibtex(self, filename):
        bibtexList = []
        for article in self.ListOfArticles:
            bibtexList.append(self.convertToBibtex(article))
        

        with open(filename, 'w') as f:
            for article in bibtexList:
                for k,v in article.items():
                    f.write(v +" }" + "\n")
                f.write('\n')