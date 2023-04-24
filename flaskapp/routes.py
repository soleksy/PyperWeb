import sqlalchemy
import asyncio , httpx


from .APIS.ARXIV.ArxivClasses import ArxivHelper,ArxivParser
from .APIS.HEP.HepClasses import HepHelper ,  HepParser
from .APIS.PUBMED.PubmedClasses import PubmedHelper , PubmedParser

from sqlalchemy import create_engine

from .constants import  ITEMS_PER_PAGE , NUMOFARTICLES

from flask import render_template ,redirect,url_for,request ,session
from flaskapp import app, db
from flaskapp.forms import InfoForm
from flaskapp.models import Article , User

from datetime import datetime

def sortByDateAscending(list):
    return sorted(list,key=lambda x:x['FullDate'] , reverse=False)

def sortByDateDescending(list):
    return sorted(list,key=lambda x:x['FullDate'] , reverse=True)

def filterArticles(list):
    articleFilter = dict()
    newArticleList = []
    
    for article in list:
        if article.get('Doi'):
            if articleFilter.get(article['Doi']):
                continue
            else:
                articleFilter[article['Doi']] = True
                newArticleList.append(article)
        elif article.get('eprint'):
            if articleFilter.get(article['eprint']):
                continue       
            else:
                articleFilter[article['eprint']] = True
                newArticleList.append(article)
        else:
            if article.get('Title'):
                if article.get('Year'):
                    if articleFilter.get(article['Title']):
                        if articleFilter.get(article['Year']):
                            if articleFilter.get(article['Title']).get('Year') == article['Year']:
                                continue
                            else:
                                articleFilter[article['Title']] = {'Year':article['Year']}
                                newArticleList.append(article)
                        else:
                            articleFilter[article['Title']] = {'Year':article['Year']}
                            newArticleList.append(article)
                    else:
                        articleFilter[article['Title']] = {'Year':article['Year']}
                        newArticleList.append(article)
                else:
                    articleFilter[article['Title']] = {'Year':None}
                    newArticleList.append(article)
            else:
                continue
    return newArticleList
                        
async def retrieveData(url : str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url,timeout=100)
        await client.aclose()
    return resp

def clearData(session):
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        session.execute(table.delete())
    session.commit()

def checkTableExistance(tableName):
    engine = create_engine("sqlite:////tmp/test.db")
    if sqlalchemy.inspect(engine).has_table(tableName):
        return True
    else:
        return False

@app.before_request
def before_request():

    if 'user_id' not in session:
        # Create a new user and store it in the database
        new_user = User(username='Bob')
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
    
    
@app.route('/' , methods=['GET' ,'POST'])
def indexPage():
    
    sessionID = session['user_id']
    
    if request.method == "POST":
        session['FILTERS'] = False
        searchQuery = request.form["searchText"]
        emptyCheck = searchQuery.replace(" ", "")
        if emptyCheck == "":
            error = "You have submited an empty query"
            session['SEARCH'] = True
            return redirect(url_for('errorPage' , error=error))
        
        PUBMED = request.form.get('pubmed')
        if PUBMED == None:
            PUBMED = False
        else:
            PUBMED = True

        ARXIV = request.form.get('arxiv')
        if ARXIV == None:
            ARXIV = False
        else:
            ARXIV = True

        HEP = request.form.get('hep')
        if HEP == None:
            HEP = False
        else:
            HEP = True
            
        if not (ARXIV or HEP or PUBMED):
            error =  "You didn't select any databse to search"
        count_articles = Article.query.filter(Article.user_id == sessionID).count()
        if count_articles != 0:
            localArticles = Article.query.filter(Article.user_id == sessionID)
        
            localArticles.delete()
            db.session.commit()

        if 'SEARCH_QUERY' in session:
            if session['SEARCH_QUERY'] != searchQuery:
                session['SEARCH_QUERY'] = searchQuery
                session['SEARCH'] = True
            else:
                session['SEARCH'] = False
        else:
            session['SEARCH_QUERY'] = searchQuery
            session['SEARCH'] = True
        
        session['HEP'] = HEP
        session['ARXIV'] = ARXIV
        session['PUBMED'] = PUBMED

        
        return redirect(url_for('processData',searchQuery=searchQuery,page=1,sessionID=sessionID))
    else:
        searchQuery = session.get('SEARCH_QUERY' , " ")
        return render_template('index.html' , searchQuery=searchQuery)
    
    

@app.route('/process/data/query=<searchQuery>/<sessionID>')
async def processData(searchQuery,sessionID):

    sessionID = session['user_id']
    articles = []
    arxiv = session.get('ARXIV', None)
    hep = session.get('HEP', None)
    pubmed = session.get('PUBMED', None)

    arxivArticleList = []
    hepArticleList = []
    pubmedArticleList = []
    
    dbToSearch = []
    listOfApiCalls = []
    index = 0

    if arxiv:
        arxivHelper = ArxivHelper(NUMOFARTICLES)
        url = arxivHelper.allParamSearch(searchQuery)
        listOfApiCalls.append(retrieveData(url))
        
    if hep:
        hepHelper = HepHelper(NUMOFARTICLES)
        url = hepHelper.hepUrlGenerator(searchQuery)
        listOfApiCalls.append(retrieveData(url))

    if pubmed:
        pubmedHelper = PubmedHelper(NUMOFARTICLES)
        url = pubmedHelper.pubmedURLGenerator(searchQuery)
        listOfApiCalls.append(retrieveData(url))

    async with httpx.AsyncClient() as client:
        dbToSearch = await asyncio.gather(
            *listOfApiCalls
        )
        await client.aclose()


    if arxiv:
        arxivParser = ArxivParser(dbToSearch[index].content)
        arxivParser.standardizeXml()
        arxivParser.parseXML()
        arxivArticleList = arxivParser.ListOfArticles
        index += 1
    if hep:
        hepParser = HepParser(dbToSearch[index].content)
        hepParser.parseXml()
        hepArticleList = hepParser.ListOfArticles
        index += 1
    if pubmed:
        pubmedParser = PubmedParser(dbToSearch[index].content)
        pubmedParser.parseArticleInfo()
        pubmedArticleList = pubmedParser.ListOfArticles
        index += 1

    articles = filterArticles(hepArticleList + arxivArticleList + pubmedArticleList)
    
    if len(articles) == 0:
        error = "No results for the submited query"
        session['SEARCH'] = True
        return redirect(url_for('errorPage',error=error))
    else:
        articleList = []
        for article in articles:
            
            date = datetime.strptime(article.get('FullDate'), '%Y-%m-%d')

            articleList.append(Article(title=article.get('Title'), description=article.get('Summary'), source=article.get('DB')
                                    ,firstAuthor=article.get('FirstAuthor'), yearPublished=article.get('Year'),
                                    numberOfAuthors=article.get('AuthorCount'),journal=article.get('Journal'),
                                    volume=article.get('Volume'),pages=article.get('Pages'),DOI=article.get('Doi'),
                                    eprint=article.get('Eprint'),bibtex=article.get('Bibtex'),link = article.get('Link') ,fullDate = date ,user_id=sessionID))
        db.session.bulk_save_objects([Article for Article in articleList])
        db.session.commit()

        page = request.args.get('page',1,type=int)
        articles = Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
    return redirect (url_for('searchResults' ,page=page,searchQuery=searchQuery))


@app.route('/search_results/query=<searchQuery>/page=<page>', methods=['GET' ,'POST'])
def searchResults(searchQuery,page):
    
    sessionID = session['user_id']
    page = int(page)
    localArticles = Article.query.filter(Article.user_id==session['user_id']).paginate(page=page,per_page=ITEMS_PER_PAGE)
    
    form = InfoForm()

    startDate = None
    endDate = None


    #IF FILTERS WERE APPLIED
    if form.validate_on_submit():
        session['FILTERS'] = True
        
        session['DATE_START'] = form.startDate.data.strftime("%Y/%m/%d")
        session['DATE_END'] = form.endDate.data.strftime("%Y/%m/%d")

        session['START_YEAR'] = datetime.strptime(session['DATE_START'], "%Y/%m/%d")
        session['END_YEAR'] = datetime.strptime(session['DATE_END'], "%Y/%m/%d")
              
        filteredArticles = Article.query.filter(Article.fullDate>=session.get('START_YEAR'),Article.fullDate<=session.get('END_YEAR'),Article.user_id == sessionID).paginate(page=1,per_page=ITEMS_PER_PAGE)
    
        if len(filteredArticles.items) == 0:
            error = "No results for the submited date range"
            session['FILTERS'] = False
            return redirect(url_for('errorPage' , error=error))
        else:
            return render_template('search_results.html' ,  results=filteredArticles, searchQuery=searchQuery ,form=form,startDate=session['DATE_START'],endDate=session['DATE_END'],page=1)
    
    #IF AN ARTICLE HAS BEEN CHOSEN
    elif request.method == "POST":
        articleID = request.form.get("info")
        page = int(request.form.get("currentPage"))
        return redirect(url_for('articlePage',articleID=articleID,page=page))

    #SEARCH RESULT REFRESHED
    else:
        filters = session.get('FILTERS', None)
        if filters:
            filteredArticles = Article.query.filter(Article.fullDate>=session.get('START_YEAR'),Article.fullDate<=session.get('END_YEAR'),Article.user_id == sessionID).paginate(page=page,per_page=ITEMS_PER_PAGE) 
            return render_template('search_results.html' ,  results=filteredArticles, searchQuery=searchQuery ,form=form,startDate=session['DATE_START'],endDate=session['DATE_END'])
        
        if session['SEARCH'] == False:
            startDate = None
            endDate = None
            page = request.args.get('page',1,type=int)
            return render_template('search_results.html' ,results=localArticles  ,searchQuery=searchQuery, form=form,startDate=startDate,endDate=endDate,page=page)
        else:
            startDate = None
            endDate = None
            page = request.args.get('page',1,type=int)
            return render_template('search_results.html' ,results=localArticles  ,searchQuery=searchQuery, form=form,startDate=startDate,endDate=endDate , page=page)


@app.route('/search_result/reset')
def resetFilters():
    session["FILTERS"] = False
    searchQuery = session.get("SEARCH_QUERY" , None)
    
    return redirect(url_for('searchResults',searchQuery=searchQuery,page=1))

@app.route('/search_results/id=<articleID>/page=<page>')
def articlePage(articleID,page):

    filters = session.get('FILTERS' , None)
    sessionID = session['user_id']
    localArticles = Article.query.filter(Article.user_id==sessionID).paginate(page=int(page),per_page=ITEMS_PER_PAGE)
    
    if filters:
        filteredArticleList = Article.query.filter(Article.fullDate>=session.get('START_YEAR'),Article.fullDate<=session.get('END_YEAR'),Article.user_id == sessionID).paginate(page=int(page),per_page=ITEMS_PER_PAGE)
    if filters:
        article = filteredArticleList.items[int(articleID)]
        bibtex = filteredArticleList.items[int(articleID)].bibtex
    else:
        article = localArticles.items[int(articleID)]
        bibtex = localArticles.items[int(articleID)].bibtex

    searchQuery = session['SEARCH_QUERY']
    return render_template('article.html' , bibtex=bibtex, article=article , ArticleID=articleID, searchQuery=searchQuery, page=page)


@app.route('/api/state/change' , methods=['GET' ,'POST'])
async def getBibtex():
    sessionID = session['user_id']
    localArticles = Article.query.filter(Article.user_id==sessionID).all()
    listOfArticleIndexes = list()

    if request.method == 'POST':
        data = request.json

        fileString=""
        for article in localArticles:
            if data.get(str(article.id)) == True:
                listOfArticleIndexes.append(article.id)
        
        for article in localArticles:
            if article.id in listOfArticleIndexes:
                for key in article.bibtex.keys():
                    if key == list(article.bibtex.keys())[0]:
                        fileString += str(article.bibtex[key]+",")
                        fileString += ('\n')
                    elif key != list(article.bibtex.keys())[-1]:
                       fileString +=str(article.bibtex[key]+" },")
                       fileString += ('\n')
                    else:
                        fileString += str(article.bibtex[key]+" },\n}")
                        fileString += ('\n')
                fileString+=('\n')

        return fileString
    else:
        return '200'
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/redirect/error<error>' , methods=['GET','POST'])
def errorPage(error):
    toBeSearched = session.get('SEARCH')
    searchQuery = session.get('SEARCH_QUERY')
    
    return render_template('error.html',error=error,toBeSearched=toBeSearched,searchQuery=searchQuery)