import requests
import json
import xml
from bs4 import BeautifulSoup
from pylatexenc.latex2text import LatexNodes2Text


class PubMedHelper:
    def __init__(self):
        self.CONST_QUERY_RESULTS=100
        self.CONST_FETCH_URL='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        self.CONST_SEARCH_URL='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'


    def search_pubmed(self, params):
        base_url = self.CONST_SEARCH_URL
        full_url = base_url + '?' + '&'.join([f'{key}={value}' for key, value in params.items()])
        response = requests.get(full_url)
        return response.json()

    def get_article_ids(self,json_response):
        return json_response['esearchresult']['idlist']

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

class PubMedParser:
    '''Load and parse the xml data from the API'''
    def __init__(self , source):
        self.ListOfArticles = list()
        self.ListOfBibtex = list()

        self.xml_data = source

    def parse_article_info(self):
        '''
        author, list of authors, journal, article title, abstract, doi,year, volume
        '''
        soup = BeautifulSoup(self.xml_data ,features="xml")
        articles_info = []
        for i , article in enumerate(soup.find_all('PubmedArticle')):
            article_info = {}
            if article.find('ArticleTitle') is not None:
                article_info['Title'] = article.find('ArticleTitle').text

            if article.find('Abstract') is not None:
                article_info['abstract'] = article.find('Abstract').text

            if article.find('ElocationID') is not None:
                article_info['Doi'] = article.find('ElocationID').text

            if article.find('AuthorList').find('ForeName') is not None:
                foreName = article.find('AuthorList').find('ForeName').text
            else:
                foreName = ''
            
            if article.find('AuthorList').find('LastName') is not None:
                lastName = article.find('AuthorList').find('LastName').text
            else:
                lastName = ''

            article_info['FirstAuthor'] = foreName + ' ' + lastName

            if article.find('AuthorList') is not None:
                Authors = [author for author in article.find('AuthorList').find_all('Author')]
                author_list = []
                for author in Authors:
                    if author.find('ForeName') is not None:
                        foreName = author.find('ForeName').text
                    else:
                        foreName = ''
                    if author.find('LastName') is not None:
                        lastName = author.find('LastName').text
                    else:
                        lastName = ''
                    author = foreName + ' ' + lastName
                    author_list.append(author)
                article_info['authors'] = author_list
                article_info['author_count'] = len(author_list)   

            if article.find('Title') is not None:
                article_info['Journal'] = article.find('Title').text

            if article.find('Volume') is not None:
                article_info['Volume'] = article.find('Volume').text

            if article.find('Year') is not None:
                article_info['Year'] = article.find('Year').text
            
            article_info['Bibtex'] = self.convertToBibtex(article_info)

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


def main():
    Helper = PubMedHelper()
    
    # Search for articles
    params = {'db': 'pubmed', 'term': 'covid', 'retmax': Helper.CONST_QUERY_RESULTS, 'retmode': 'json'}
    json_response = Helper.search_pubmed(params)
    article_ids = Helper.get_article_ids(json_response)
    Helper.apiToFile(json_response, 'search.json', 'json')

    # Fetch articles info
    response = Helper.fetch_articles_info(article_ids, 'abstract' , 'xml')
    Helper.apiToFile(response, 'articles.json', 'xml')

    Parser = PubMedParser(response)
    # Parse articles info
    Parser.parse_article_info()
    Parser.writeBibtex('articles.txt')
        
if __name__ == "__main__":
    main()