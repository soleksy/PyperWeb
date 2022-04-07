from re import search
from flask import Flask , render_template ,redirect,url_for,request ,session
from flaskapp import app, db
from flaskapp.forms import InfoForm
from flaskapp.models import Article
from sqlalchemy import delete
from .APIS.ARXIV.ArxivClasses import ArxivHelper,ArxivParser
from .APIS.HEP.HepClasses import HepHelper ,  HepParser
import asyncio , httpx
from .constants import SIZE , ITEMS_PER_PAGE 
from sqlalchemy import create_engine
import sqlalchemy

import threading

sem = threading.Semaphore()


sessionID = 0
sessionController = dict()


def updateArticleList(listOfArticles):    
    global articles
    articles = listOfArticles

def sortByDateAscending(list):
    return sorted(list,key=lambda x:x['Year'] , reverse=False)

def sortByDateDescending(list):
    return sorted(list,key=lambda x:x['Year'] , reverse=True)

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


    
@app.route('/' , methods=['GET' ,'POST'])
def indexPage():
    global sessionID
            
    if not checkTableExistance("Article"):
            db.create_all()
            
    if request.method == "POST":
        
        searchQuery = request.form["searchText"]
        
        
        if searchQuery == "":
            error = "Apparently you have submited an empty query"
            return redirect(url_for('errorPage' , error=error))
        
            
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
            
        if not (ARXIV or HEP):
            error =  "You didn't select a database to process your query"
            return redirect(url_for('errorPage',error=error))
        
        sem.acquire()
        if 'SESSION_ID' in session:
            seshhh = int(session.get('SESSION_ID'))
            articleess = Article.query.filter(Article.sessionID == seshhh)
            articleess.delete()
            db.session.commit()
            
            sessionID = sessionID + 1
            session['SESSION_ID'] = sessionID 
        else:
            sessionID = sessionID + 1
            session['SESSION_ID'] = sessionID 
        sem.release()
        
        if 'SEARCH_QUERY' in session:
            if session['SEARCH_QUERY'] != searchQuery:
                session['SEARCH_QUERY'] == searchQuery
                session['SEARCH'] = True
            else:
                session['SEARCH'] = False
        else:
            session['SEARCH_QUERY'] == searchQuery
            session['SEARCH'] = True
        
        
        session['HEP'] = HEP
        session['ARXIV'] = ARXIV

        
        return redirect(url_for('processData',searchQuery=searchQuery,page=1,sessionID=sessionID))
    else:
        text = session.get('QUERYTEXT' , " ")
        return render_template('index.html' , text=text)
    
    

@app.route('/process/data/query=<searchQuery>/<sessionID>')
async def processData(searchQuery,sessionID):
    
    articles = []
    arxiv = session.get('ARXIV', None)
    hep = session.get('HEP', None)

    arxivArticleList = []
    hepArticleList = []
    
    dbToSearch = []
    listOfApiCalls = []
    index = 0
    form = InfoForm()
    
    startDate = None
    endDate = None
        
    if arxiv:
        arxivHelper = ArxivHelper()
        url = arxivHelper.allParamSearch(searchQuery)
        listOfApiCalls.append(retrieveData(url))
            
    if hep:
        hepHelper = HepHelper()
        url = hepHelper.hepUrlGenerator(searchQuery)
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
        hepParser.parseJsonFile()
        hepArticleList = hepParser.ListOfArticles
        index += 1
        
    
    session['ARTICLES'] = (sortByDateDescending(filterArticles(hepArticleList + arxivArticleList)))
    articles = session['ARTICLES']
    
    if len(articles) == 0:
        session['ERROR'] = "No results for the submited query"
        return redirect(url_for('errorPage'))
    else:
        if not checkTableExistance("Article"):
            db.create_all()
        
        for article in articles:
            db.session.add(Article(title=article.get('Title'), description=article.get('Summary'), source=article.get('DB')
                                    ,firstAuthor=article.get('FirstAuthor'), yearPublished=article.get('Year'),
                                    numberOfAuthors=article.get('AuthorCount'),journal=article.get('Journal'),
                                    volume=article.get('Volume'),pages=article.get('Pages'),DOI=article.get('Doi'),
                                    eprint=article.get('Eprint'),bibtex=article.get('Bibtex'),sessionID=sessionID))
        db.session.commit()

        page = request.args.get('page',1,type=int)
        articles = Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
    return redirect (url_for('searchResults' ,page=page,results=articles ,searchQuery=searchQuery,form=form,startDate=startDate,endDate=endDate))
    
@app.route('/search_results/query=<searchQuery>' , methods=['GET' ,'POST'])
def searchResults(searchQuery):
    
    page = request.args.get('page',1,type=int)
    
    localArticles = Article.query.filter(Article.sessionID==int(session['SESSION_ID'])).paginate(page=page,per_page=ITEMS_PER_PAGE)
    
    form = InfoForm()
    #IF AN ARTICLE HAS BEEN CHOSEN
    if request.method == "POST":
        articleID = request.form.get("info")
        page = request.args.get('page',1,type=int)
        return redirect(url_for('articlePage',articleID=articleID,page=page,searchQuery=searchQuery))
        
    #IF FILTERS WERE APPLIED
    elif form.validate_on_submit():
        session['FILTERS'] = True
        tempStartDate = startDate
        tempEndDate = endDate
        startDate = form.startDate.data.strftime("%m/%d/%Y")
        endDate = form.endDate.data.strftime("%m/%d/%Y")
        startYear = int(form.startDate.data.strftime("%Y"))
        endYear = int(form.endDate.data.strftime("%Y"))
        
        session['FILTERED_ARTICLES'] = Article.query.filter(Article.yearPublished<=endYear,Article.yearPublished>=startYear).paginate(page=1,per_page=ITEMS_PER_PAGE)
    
        if len(articles.items)  == 0:
            startDate = tempStartDate
            endDate = tempEndDate
            return render_template('search_results.html' , searchQuery=searchQuery, results=localArticles,form=form,startDate=startDate,endDate=endDate)


    #SEARCH RESULT REFRESHED
    else:
        filters = session.get('FILTERS', None)
        if filters:            
            return render_template('search_results.html' ,  results=localArticles, searchQuery=searchQuery ,form=form,startDate=startDate,endDate=endDate)
        
        
        if session["SEARCH"] == False:
            startDate = None
            endDate = None
            
            page = request.args.get('page',1,type=int)
            articles = Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
            return render_template('search_results.html' ,results=localArticles  ,searchQuery=searchQuery, form=form,startDate=startDate,endDate=endDate)
        else:
            startDate = None
            endDate = None
            
            page = request.args.get('page',1,type=int)
            articles = Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
            return render_template('search_results.html' ,results=localArticles  ,searchQuery=searchQuery, form=form,startDate=startDate,endDate=endDate)


@app.route('/search_result/reset')
def resetFilters():
    session["FILTERS"] = False
    text = session.get("QUERYTEXT" , None)
    
    return redirect(url_for('searchResults',txt=text,page=1,results=articles))

@app.route('/search_results/id=<articleID>/page=<page>')
def articlePage(articleID,page):
    page=int(page)
    sessionID = int(session.get('SESSION_ID'))
    localArticles = Article.query.filter(Article.sessionID==sessionID).paginate(page=page,per_page=ITEMS_PER_PAGE)
    
    filters = session.get('FILTERS', None)
    filteredArticleList = session.get('FILTERED_ARTICLES',None)
    if filters:
        article = filteredArticleList.items[int(articleID)]
        bibtex = filteredArticleList.items[int(articleID)].bibtex
    else:
        article = localArticles.items[int(articleID)]
        bibtex = localArticles.items[int(articleID)].bibtex

    searchQuery = session['SEARCH_QUERY']
    return render_template('article.html' , bibtex=bibtex, article=article , ArticleID=articleID, searchQuery=searchQuery, page=page)


@app.route('/api/state/change/<parameter>' , methods=['GET' ,'POST'])
def changeState(parameter):
    global articles
    return 200
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/redirect/error<error>' , methods=['GET','POST'])
def errorPage(error):
    return render_template('error.html',error=error)