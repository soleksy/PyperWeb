from flask import Flask , render_template ,redirect,url_for,request ,session
from flaskapp import app, db
from flaskapp.forms import InfoForm
from flaskapp.models import Article
from .APIS.ARXIV.ArxivClasses import ArxivHelper,ArxivParser
from .APIS.HEP.HepClasses import HepHelper ,  HepParser
import asyncio , httpx
from .constants import SIZE , ITEMS_PER_PAGE 
from sqlalchemy import create_engine
import sqlalchemy


articles = [] # stores list entities
filteredArticleList = [] # stores articles post filters
visibleArticles = [] # stores articles that are being displayed atm

searchController = 0 # controlls whether the initial search was processed
searched = False #?
page = 0 # basic controlling attribute
startDate = None # controlls the filters
endDate = None # controlls the filters



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
    
@app.route('/redirect/error' , methods=['GET','POST'])
def errorPage():
    error_msg = session.get('ERROR', None)
    return render_template('error.html',error=error_msg)
    
    
@app.route('/' , methods=['GET' ,'POST'])
def indexPage():
    global searchController
    if request.method == "POST":
        searchController = 1
        text = request.form["searchText"]
        
        if text == "":
            text = " "
            session['ERROR'] = "Apparently you have submited an empty query"
            return redirect(url_for('errorPage'))
        
            
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
            session['ERROR'] = "You didn't select a database to process your query"
            return redirect(url_for('errorPage'))
        
        session['QUERYTEXT'] = text
        session['HEP'] = HEP
        session['ARXIV'] = ARXIV
        session['FILTERS'] = False
        
        return redirect(url_for('searchResults',txt=text,page=1))
    else:
        text = session.get('QUERYTEXT' , " ")
        return render_template('index.html' , text=text)
    
@app.route('/search_results/query<txt>' , methods=['GET' ,'POST'])
async def searchResults(txt):

    global searchController
    global startDate
    global endDate
    
    global articles #original search
    global filteredArticleList #post filter
    global visibleArticles #articles being displayed
    global searched

    arxiv = session.get('ARXIV', None)
    hep = session.get('HEP', None)
    filters = session.get('FILTERS' , None)
    arxivArticleList = []
    hepArticleList = []
    
    dbToSearch = []
    listOfApiCalls = []
    index = 0
    form = InfoForm()
    
    #1 IF SEARCH QUERY HAS TO BE PROCESSED BY APIS
    if searchController == 1:
        searchController = 0
        
        searched = False
        startDate = None
        endDate = None
        
        if arxiv:
            arxivHelper = ArxivHelper()
            url = arxivHelper.allParamSearch(txt)
            listOfApiCalls.append(retrieveData(url))
                
        if hep :
            hepHelper = HepHelper()
            url = hepHelper.hepUrlGenerator(txt)
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

        
    
        updateArticleList(sortByDateDescending(filterArticles(hepArticleList + arxivArticleList)))
        
        if len(articles) == 0:
            session['searchURL'] = None
        else:
            if checkTableExistance("Article"):
                clearData(db.session)
            else:
                db.create_all()
            
            for article in articles:
                db.session.add(Article(title=article.get('Title'), description=article.get('Summary'), source=article.get('DB')
                                       ,firstAuthor=article.get('FirstAuthor'), yearPublished=article.get('Year'),
                                       numberOfAuthors=article.get('AuthorCount'),journal=article.get('Journal'),
                                       volume=article.get('Volume'),pages=article.get('Pages'),DOI=article.get('Doi'),
                                       eprint=article.get('eprint'),bibtex=article.get('Bibtex'),isSelected=False))
            db.session.commit()
            session['searchURL'] = f"/search_results/query{txt}"
            
            page = request.args.get('page',1,type=int)
            articles= Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
        return render_template('search_results.html' ,page=page,results=articles  ,txt=txt, form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        
    
  
    #IF FILTERS WERE APPLIED
    elif form.validate_on_submit():
        session['FILTERS'] = True
        tempStartDate = startDate
        tempEndDate = endDate
        startDate = form.startDate.data.strftime("%m/%d/%Y")
        endDate = form.endDate.data.strftime("%m/%d/%Y")
        startYear = int(form.startDate.data.strftime("%Y"))
        endYear = int(form.endDate.data.strftime("%Y"))
        
        articles = Article.query.filter(Article.yearPublished<=endYear,Article.yearPublished>=startYear).paginate(page=1,per_page=ITEMS_PER_PAGE)
        filteredArticleList = articles
        
        
        if len(articles.items)  == 0:
            startDate = tempStartDate
            endDate = tempEndDate
            return render_template('search_results.html' , txt=txt, results=articles , form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        else:
            searched = True
            return render_template('search_results.html' ,results=articles,txt=txt, form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
    
    #IF AN ARTICLE HAS BEEN CHOSEN
    elif request.method == "POST":
        articleID = request.form.get("info")
        return redirect(url_for('articlePage',id = articleID))
    #SEARCH RESULT REFRESHED
    else:
        filters = session.get('FILTERS', None)
        if filters:            
            return render_template('search_results.html' ,  results=filteredArticleList, txt=txt ,form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        
        if(searchController == 0):
            startDate = None
            endDate = None
            
            page = request.args.get('page',1,type=int)
            articles = Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
            return render_template('search_results.html' ,results=articles  ,txt=txt, form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
            


@app.route('/search_result/reset')
def resetFilters():
    session["FILTERS"] = False
    text = session.get("QUERYTEXT" , None)
    
    return redirect(url_for('searchResults',txt=text,page=1,results=articles))
@app.route('/search_results/<id>')

def articlePage(id):
    global articles
    global filteredArticleList
    global searched
    filters = session.get('FILTERS', None)
    
    if filters:
        article = filteredArticleList.items[int(id)]
        bibtex = filteredArticleList.items[int(id)].bibtex
    else:
        article = articles.items[int(id)]
        bibtex = articles.items[int(id)].bibtex

    return render_template('article.html' , bibtex=bibtex, article=article ,searchURL=session.get('searchURL'),)


@app.route('/api/state/change/<parameter>' , methods=['GET' ,'POST'])
def changeState(parameter):
    global articles
    print(parameter)
    
    return 200
    
@app.route('/about')
def about():
    return render_template('about.html')
