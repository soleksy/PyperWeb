import requests
import json
import xml
from bs4 import BeautifulSoup


class PubMedHelper:
    def __init__(self):
        self.CONST_QUERY_RESULTS=20
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

    def parse_article_info(self, xml_data):
        soup = BeautifulSoup(xml_data ,features="xml")
        articles_info = []
        for i , article in enumerate(soup.find_all('PubmedArticle')):
            article_info = {}
            if article.find('ArticleTitle') is not None:
                article_info['title'] = article.find('ArticleTitle').text

            if article.find('ElocationID') is not None:
                article_info['doi'] = article.find('ElocationID').text
            if article.find('AuthorList').find('ForeName') is not None:
                foreName = article.find('AuthorList').find('ForeName').text
            else:
                foreName = ''
            
            if article.find('AuthorList').find('LastName') is not None:
                lastName = article.find('AuthorList').find('LastName').text
            else:
                lastName = ''

            article_info['first_author'] = foreName + ' ' + lastName

            if article.find('Title') is not None:
                article_info['journal_title'] = article.find('Title').text
            if article.find('Year') is not None:
                article_info['year_published'] = article.find('Year').text
                
            articles_info.append(article_info)
        return articles_info

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

    # Parse articles info
    articles_info = Helper.parse_article_info(response)
    for article in articles_info:
        print(article.get('title'))

if __name__ == "__main__":
    main()